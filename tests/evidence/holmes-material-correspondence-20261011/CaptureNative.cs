using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Private runner stages copies first; no Scene or source package writes.
public static class RealDependencyBootstrap
{
    const string Source = "Assets/PublicMaterialSource/Input.fbx";
    const string Prefab = "Assets/PublicMaterialSource/Direct.prefab";
    static string Work;
    [Serializable] class Ref { public string guid, file_id; }
    [Serializable] class Remap { public string name, type, assembly; public Ref target; }
    [Serializable] class Context
    {
        public string unity_version, fbx_sha, meta_sha, fbx_sha_after, meta_sha_after;
        public string prefab_sha, prefab_meta_sha, renderer_guid, renderer_file_id, error;
        public Ref mesh;
        public Ref[] materials, model_materials;
        public bool same_model_mesh, get_triangles_matches_mesh_data;
        public bool weld_vertices, optimize_vertices, optimize_polygons;
        public string compression, index_format, import_normals, import_tangents;
        public Remap[] external_remaps;
        public string serialized_model_importer;
    }
    static Ref Reference(UnityEngine.Object obj)
    {
        if (obj == null) return new Ref { guid = "", file_id = "NULL" };
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out string guid, out long id))
            throw new Exception("identity unavailable");
        return new Ref { guid = guid, file_id = id.ToString(System.Globalization.CultureInfo.InvariantCulture) };
    }
    static string Hash(string path)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    static void ExclusiveJson(string path, string contents)
    {
        using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write))
        using (var writer = new StreamWriter(stream)) writer.Write(contents);
    }
    public static void Run()
    {
        string[] args = Environment.GetCommandLineArgs();
        Work = args[Array.IndexOf(args, "-vapbHolmesWork") + 1];
        try
        {
            if (Hash(Source) != "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5" ||
                Hash(Source + ".meta") != "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d")
                throw new Exception("staged original revision differs");
            foreach (string name in new[] { "R", "A", "B" })
            {
                var r = new Context();
                string input = Path.Combine(Work, "cases", name + ".fbx");
                string expected = Hash(input);
                File.Copy(input, Source, true); // source is the runner-owned staged copy
                AssetDatabase.ImportAsset(Source, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                r.unity_version = Application.unityVersion;
                r.fbx_sha = Hash(Source); r.meta_sha = Hash(Source + ".meta");
                if (r.fbx_sha != expected || r.meta_sha != "ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d")
                    throw new Exception("case import revision mismatch");
                r.prefab_sha = Hash(Prefab); r.prefab_meta_sha = Hash(Prefab + ".meta");
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(Source);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
                var skin = prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                var source = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                r.mesh = Reference(skin.sharedMesh);
                var owner = Reference(skin); r.renderer_guid = owner.guid; r.renderer_file_id = owner.file_id;
                r.same_model_mesh = skin.sharedMesh == source.sharedMesh;
                if (!r.same_model_mesh) throw new Exception("Prefab/model Mesh differs");
                r.materials = skin.sharedMaterials.Select(Reference).ToArray();
                r.model_materials = source.sharedMaterials.Select(Reference).ToArray();
                var importer = (ModelImporter)AssetImporter.GetAtPath(Source);
                r.weld_vertices = importer.weldVertices;
                r.optimize_vertices = importer.optimizeMeshVertices; r.optimize_polygons = importer.optimizeMeshPolygons;
                r.compression = importer.meshCompression.ToString(); r.index_format = importer.indexFormat.ToString();
                r.import_normals = importer.importNormals.ToString(); r.import_tangents = importer.importTangents.ToString();
                r.serialized_model_importer = EditorJsonUtility.ToJson(importer);
                r.external_remaps = importer.GetExternalObjectMap().Select(pair => new Remap {
                    name = pair.Key.name, type = pair.Key.type.ToString(), assembly = pair.Key.type.Assembly.GetName().Name,
                    target = Reference(pair.Value) }).ToArray();
                string coordinate = Path.Combine(Work, name + "-coordinate.json");
                if (File.Exists(coordinate)) throw new Exception("occupied coordinate output");
                VapbHolmesCoordinateProbe.Capture(coordinate);
                // Literal source Mesh.GetTriangles cross-check against the reused MeshData capture.
                var captured = JsonUtility.FromJson<TriangleSnapshot>(File.ReadAllText(coordinate));
                r.get_triangles_matches_mesh_data = Enumerable.Range(0, skin.sharedMesh.subMeshCount)
                    .All(sub => skin.sharedMesh.GetTriangles(sub).SequenceEqual(captured.source_submeshes[sub].indices));
                if (!r.get_triangles_matches_mesh_data) throw new Exception("GetTriangles differs from MeshData");
                r.fbx_sha_after = Hash(Source); r.meta_sha_after = Hash(Source + ".meta");
                if (r.fbx_sha_after != r.fbx_sha || r.meta_sha_after != r.meta_sha) throw new Exception("case input changed during capture");
                ExclusiveJson(Path.Combine(Work, name + "-context.json"), JsonUtility.ToJson(r, true));
            }
            EditorApplication.Exit(0);
        }
        catch (Exception error)
        {
            ExclusiveJson(Path.Combine(Work, "native-error.txt"), error.ToString());
            EditorApplication.Exit(1);
        }
    }
    [Serializable] class TriangleGroup { public int[] indices; }
    [Serializable] class TriangleSnapshot { public TriangleGroup[] source_submeshes; }
}
