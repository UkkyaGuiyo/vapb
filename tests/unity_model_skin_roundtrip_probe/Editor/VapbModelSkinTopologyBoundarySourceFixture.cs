using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

// Builds the smallest normal model-Skin source package around the Blender FBX.
// The model prefab instance stays nested so the regular exporter emits a task
// with a real prefab-to-FBX instance edge.
public static class VapbModelSkinTopologyBoundarySourceFixture
{
    private const string Folder = "Assets/VapbSkinRoundtrip";
    private const string Input = Folder + "/Input.fbx";
    private const string Prefab = Folder + "/Avatar.prefab";
    private const string MaterialPath = Folder + "/Original.mat";
    private const string RootMarker = ".vapb-stage3-owned-test-root";
    private const string SourceMarker = ".vapb-stage3-owned-source-project";
    private const string EvidenceName = "TopologyBoundarySourceFixtureEvidence.json";
    private const string PackageName = "Source.unitypackage";

    [Serializable]
    private sealed class Report
    {
        public bool pass;
        public string error;
        public string input_guid;
        public string prefab_guid;
        public string material_guid;
        public string input_sha256;
        public string input_meta_sha256;
        public string prefab_sha256;
        public string prefab_meta_sha256;
        public string package_sha256;
        public string importer_settings;
        public int vertex_count;
        public int face_count;
        public int index_count;
        public int bone_count;
        public int material_count;
        public int submesh_count;
        public int blend_shape_count;
        public bool nested_model_instance;
        public string[] component_types;
    }

    public static void Prepare()
    {
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        string projectRoot = Path.GetFullPath(Path.GetDirectoryName(Application.dataPath));
        string evidenceFile = Path.Combine(projectRoot, EvidenceName);
        string guard = ValidateOwnedSource(projectRoot);
        if (guard != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_SOURCE_FIXTURE_BLOCKED=" + guard);
            return;
        }
        try
        {
            string inputFile = Disk(Input);
            string prefabFile = Disk(Prefab);
            string materialFile = Disk(MaterialPath);
            string packageFile = Path.Combine(projectRoot, PackageName);
            if (!File.Exists(inputFile) || !File.Exists(inputFile + ".meta") ||
                HasReparseComponent(inputFile) || HasReparseComponent(inputFile + ".meta"))
                throw new InvalidOperationException("SYNTHETIC_INPUT_FBX_MISSING_OR_UNSAFE");
            if (Occupied(prefabFile) || Occupied(materialFile) || Occupied(packageFile) ||
                Occupied(evidenceFile))
                throw new InvalidOperationException("SOURCE_FIXTURE_OUTPUT_OCCUPIED");

            AssetDatabase.ImportAsset(Input, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            ModelImporter importer = AssetImporter.GetAtPath(Input) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("INPUT_MODEL_IMPORTER_MISSING");
            importer.isReadable = true;
            importer.materialName = ModelImporterMaterialName.BasedOnMaterialName;
            importer.weldVertices = false;
            importer.optimizeMeshVertices = false;
            importer.optimizeMeshPolygons = false;
            importer.importAnimation = false;
            importer.SaveAndReimport();

            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
            SkinnedMeshRenderer imported = SingleSkin(model);
            if (imported == null || imported.sharedMesh == null || imported.bones == null ||
                imported.bones.Length != 2 || imported.rootBone == null)
                throw new InvalidOperationException("SOURCE_SKIN_LAYOUT_UNEXPECTED");
            Mesh mesh = imported.sharedMesh;
            report.vertex_count = mesh.vertexCount;
            report.face_count = TriangleCount(mesh);
            report.index_count = IndexCount(mesh);
            report.bone_count = imported.bones.Length;
            report.submesh_count = mesh.subMeshCount;
            report.blend_shape_count = mesh.blendShapeCount;
            report.importer_settings = "isReadable=true;materialName=BasedOnMaterialName;" +
                "weldVertices=false;optimizeMeshVertices=false;optimizeMeshPolygons=false;importAnimation=false";
            if (report.vertex_count != 4 || report.face_count != 2 || report.index_count != 6 ||
                mesh.subMeshCount != 1 || mesh.bindposes.Length != 2 || mesh.blendShapeCount != 0)
                throw new InvalidOperationException("SOURCE_MESH_CONTRACT_MISMATCH");

            Shader shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidOperationException("STANDARD_SHADER_MISSING");
            Material material = new Material(shader) { name = "TopologyBoundaryStandard" };
            AssetDatabase.CreateAsset(material, MaterialPath);

            GameObject root = new GameObject("TopologyBoundaryRoot");
            GameObject instance = null;
            try
            {
                instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
                if (instance == null) throw new InvalidOperationException("MODEL_PREFAB_INSTANCE_MISSING");
                instance.name = "SyntheticSkinInstance";
                instance.transform.SetParent(root.transform, false);
                SkinnedMeshRenderer instanceSkin = SingleSkin(instance);
                if (instanceSkin == null) throw new InvalidOperationException("INSTANCE_SKIN_MISSING");
                instanceSkin.sharedMaterials = new[] { material };
                if (PrefabUtility.SaveAsPrefabAsset(root, Prefab) == null)
                    throw new InvalidOperationException("SOURCE_PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer prefabSkin = SingleSkin(prefab);
            if (prefabSkin == null || prefabSkin.sharedMaterials.Length != 1 ||
                prefabSkin.sharedMaterials[0] == null || prefabSkin.sharedMesh == null ||
                prefabSkin.sharedMesh.vertexCount != 4 ||
                PrefabUtility.GetCorrespondingObjectFromSource(prefabSkin) == null)
                throw new InvalidOperationException("NESTED_SOURCE_PREFAB_CONTRACT_MISMATCH");
            report.material_count = prefabSkin.sharedMaterials.Length;
            Component[] components = prefab.GetComponentsInChildren<Component>(true);
            if (components.Any(component => component == null))
                throw new InvalidOperationException("SOURCE_MISSING_COMPONENT_UNSUPPORTED");
            report.component_types = components
                .Where(component => component != null).Select(component => component.GetType().FullName)
                .Distinct().OrderBy(type => type, StringComparer.Ordinal).ToArray();
            if (report.component_types.Any(type => type != "UnityEngine.Transform" &&
                type != "UnityEngine.SkinnedMeshRenderer"))
                throw new InvalidOperationException("SOURCE_COMPONENT_SCOPE_UNSUPPORTED");
            report.nested_model_instance = true;

            AssetDatabase.SaveAssets();
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(model, out report.input_guid, out long ignoredModelId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(prefab, out report.prefab_guid, out long ignoredPrefabId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out report.material_guid, out long ignoredMaterialId))
                throw new InvalidOperationException("SOURCE_ASSET_GUID_UNAVAILABLE");
            report.input_sha256 = Hash(inputFile);
            report.input_meta_sha256 = Hash(inputFile + ".meta");
            report.prefab_sha256 = Hash(prefabFile);
            report.prefab_meta_sha256 = Hash(prefabFile + ".meta");
            AssetDatabase.ExportPackage(new[] { Input, Prefab, MaterialPath }, packageFile,
                ExportPackageOptions.IncludeDependencies);
            if (!File.Exists(packageFile)) throw new InvalidOperationException("SOURCE_PACKAGE_MISSING");
            report.package_sha256 = Hash(packageFile);
            report.pass = true;
            report.error = "NONE";
        }
        catch (Exception error) { report.error = error.Message; }

        try
        {
            byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true));
            using (var stream = new FileStream(evidenceFile, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                stream.Write(bytes, 0, bytes.Length);
        }
        catch (Exception error)
        {
            report.pass = false;
            report.error = "SOURCE_EVIDENCE_WRITE_FAILED:" + error.Message;
        }
        Debug.Log(report.pass ? "VAPB_MODEL_SKIN_TOPOLOGY_SOURCE_FIXTURE_PASS" :
            "VAPB_MODEL_SKIN_TOPOLOGY_SOURCE_FIXTURE_FAIL=" + report.error);
        EditorApplication.Exit(report.pass ? 0 : 1);
    }

    private static string ValidateOwnedSource(string projectRoot)
    {
        string raw = Environment.GetEnvironmentVariable("VAPB_STAGE3_TEST_ROOT");
        if (String.IsNullOrWhiteSpace(raw)) return "TEST_ROOT_ENV_MISSING";
        string root = Path.GetFullPath(raw);
        string source = Path.Combine(root, "SourceProject");
        if (!String.Equals(projectRoot, source, StringComparison.OrdinalIgnoreCase))
            return "SOURCE_NOT_DIRECT_OWNED_CHILD";
        if (HasReparseComponent(root) || HasReparseComponent(source) || HasReparseComponent(Disk("Assets")) ||
            HasReparseComponent(Path.Combine(root, RootMarker)) ||
            HasReparseComponent(Path.Combine(source, SourceMarker))) return "OWNED_PATH_REPARSE_POINT";
        string targetMarker = Path.Combine(root, "TargetProject", ".vapb-disposable-unity-test-project");
        if (!File.Exists(Path.Combine(root, RootMarker)) || !File.Exists(Path.Combine(source, SourceMarker)) ||
            !File.Exists(targetMarker) ||
            File.ReadAllText(Path.Combine(root, RootMarker)).Trim() != "VAPB_STAGE3_OWNED_TEST_ROOT_V1" ||
            File.ReadAllText(Path.Combine(source, SourceMarker)).Trim() != "VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1")
            return "OWNERSHIP_MARKER_INVALID";
        string sourceVersion = Path.Combine(source, "ProjectSettings", "ProjectVersion.txt");
        string targetVersion = Path.Combine(root, "TargetProject", "ProjectSettings", "ProjectVersion.txt");
        if (!File.Exists(sourceVersion) || !File.Exists(targetVersion) ||
            !File.ReadAllText(sourceVersion).Contains("m_EditorVersion: 2022.3.22f1") ||
            !File.ReadAllText(targetVersion).Contains("m_EditorVersion: 2022.3.22f1"))
            return "UNITY_VERSION_MISMATCH";
        string current = root;
        while (!String.IsNullOrEmpty(current))
        {
            if (Directory.Exists(Path.Combine(current, ".git")) || File.Exists(Path.Combine(current, ".git")))
                return "TEST_ROOT_INSIDE_GIT_CHECKOUT";
            DirectoryInfo parent = Directory.GetParent(current);
            current = parent == null ? null : parent.FullName;
        }
        return null;
    }

    private static string Disk(string assetPath) => Path.GetFullPath(Path.Combine(
        Application.dataPath, assetPath == "Assets" ? "" : assetPath.Substring(7).Replace('/', Path.DirectorySeparatorChar)));
    private static bool Occupied(string path) => File.Exists(path) || Directory.Exists(path) ||
        File.Exists(path + ".meta") || Directory.Exists(path + ".meta");
    private static SkinnedMeshRenderer SingleSkin(GameObject root)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] rows = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        return rows.Length == 1 ? rows[0] : null;
    }
    private static int TriangleCount(Mesh mesh) => mesh.subMeshCount == 1 &&
        mesh.GetTopology(0) == MeshTopology.Triangles ? (int)(mesh.GetIndexCount(0) / 3) : -1;
    private static int IndexCount(Mesh mesh) => mesh.subMeshCount == 1 ? (int)mesh.GetIndexCount(0) : -1;
    private static string Hash(string path)
    {
        using (SHA256 hash = SHA256.Create())
            return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-", "");
    }
    private static bool HasReparseComponent(string path)
    {
        string full = Path.GetFullPath(path), volume = Path.GetPathRoot(full);
        string current = volume;
        foreach (string part in full.Substring(volume.Length).Split(Path.DirectorySeparatorChar,
            Path.AltDirectorySeparatorChar))
        {
            if (String.IsNullOrEmpty(part)) continue;
            current = Path.Combine(current, part);
            if ((File.Exists(current) || Directory.Exists(current)) &&
                (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) return true;
        }
        return false;
    }
}
