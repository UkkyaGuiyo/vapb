using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Runner-owned new static model only. No Scene, Prefab or source fixture writes.
public static class HolmesTopologyCapture
{
    const string Asset = "Assets/HolmesTopologyBoundary/MixedFour.fbx";
    [Serializable] class Ref { public string guid, file_id; }
    [Serializable] class Group { public string topology; public int index_count, base_vertex; public int[] indices; }
    [Serializable] class Snapshot
    {
        public string unity_version, fbx_sha256, fbx_sha256_after, meta_sha256, meta_sha256_after, policy;
        public bool keep_quads, apply_base_vertex;
        public Ref mesh, renderer;
        public Ref[] materials;
        public Group[] groups;
        public Vector2[] uv;
        public Vector3[] vertices, normals;
    }
    static string Hash(string path)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    static Ref Reference(UnityEngine.Object obj)
    {
        if (obj == null) return new Ref { guid = "", file_id = "NULL" };
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out string guid, out long id)) throw new Exception("identity unavailable");
        return new Ref { guid = guid, file_id = id.ToString(System.Globalization.CultureInfo.InvariantCulture) };
    }
    static void Exclusive(string path, string content)
    {
        using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write))
        using (var writer = new StreamWriter(stream)) writer.Write(content);
    }
    public static void Run()
    {
        string[] args = Environment.GetCommandLineArgs();
        string work = args[Array.IndexOf(args, "-holmesTopologyWork") + 1];
        try
        {
            string expected = Hash(Path.Combine(work, "MixedFour.fbx"));
            if (Hash(Asset) != expected) throw new Exception("staged bytes differ");
            AssetDatabase.ImportAsset(Asset, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            var importer = (ModelImporter)AssetImporter.GetAtPath(Asset);
            foreach (bool keep in new[] { false, true })
            {
                importer.keepQuads = keep;
                importer.SaveAndReimport(); // OFF normalized before capture, then only keepQuads toggled.
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(Asset);
                var renderer = model.GetComponentsInChildren<MeshRenderer>(true).Single();
                var mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
                var snapshot = new Snapshot {
                    unity_version = Application.unityVersion, fbx_sha256 = Hash(Asset), meta_sha256 = Hash(Asset + ".meta"),
                    policy = EditorJsonUtility.ToJson(importer), keep_quads = importer.keepQuads, apply_base_vertex = true,
                    mesh = Reference(mesh), renderer = Reference(renderer), materials = renderer.sharedMaterials.Select(Reference).ToArray(),
                    uv = mesh.uv, vertices = mesh.vertices, normals = mesh.normals,
                    groups = Enumerable.Range(0, mesh.subMeshCount).Select(sub => {
                        int baseVertex = (int)mesh.GetBaseVertex(sub);
                        int[] indices = mesh.GetIndices(sub, true);
                        if (!indices.SequenceEqual(mesh.GetIndices(sub, false).Select(index => index + baseVertex)))
                            throw new Exception("applyBaseVertex API crosscheck differs");
                        return new Group { topology = mesh.GetTopology(sub).ToString(), indices = indices,
                            index_count = (int)mesh.GetIndexCount(sub), base_vertex = baseVertex };
                    }).ToArray()
                };
                snapshot.fbx_sha256_after = Hash(Asset); snapshot.meta_sha256_after = Hash(Asset + ".meta");
                if (snapshot.fbx_sha256 != expected || snapshot.fbx_sha256_after != expected || snapshot.meta_sha256 != snapshot.meta_sha256_after)
                    throw new Exception("input changed during capture");
                Exclusive(Path.Combine(work, keep ? "ON.json" : "OFF.json"), JsonUtility.ToJson(snapshot, true));
                File.Copy(Asset + ".meta", Path.Combine(work, keep ? "ON.fbx.meta" : "OFF.fbx.meta"), false);
            }
            EditorApplication.Exit(0);
        }
        catch (Exception error)
        {
            Exclusive(Path.Combine(work, "native-error.txt"), error.ToString());
            EditorApplication.Exit(1);
        }
    }
}
