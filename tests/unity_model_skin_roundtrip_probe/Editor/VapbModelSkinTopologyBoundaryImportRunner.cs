using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

// Imports the ordinary Blender output package, then captures a stable post-import
// baseline before the RED probe invokes the product Finalizer.
[InitializeOnLoad]
public static class VapbModelSkinTopologyBoundaryImportRunner
{
    private const string StateKey = "VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_STATE";
    private const string StartKey = "VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_START";
    private const string RootMarker = ".vapb-stage3-owned-test-root";
    private const string SourceMarker = ".vapb-stage3-owned-source-project";
    private const string TargetMarker = ".vapb-disposable-unity-test-project";
    private const string EvidenceName = "TopologyBoundaryImportEvidence.json";
    private const string ResultName = "VapbModelSkinTopologyBoundaryRedResult.json";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string Kind = "RESTORE_MODEL_SKIN_VARIANT_V1";
    private const string ApprovedPackageSha256 = "157eee6379cc435ad9829db2011c1dabeb6f44259d97c385d6e47e3c2db8da73";
    private const string ApprovedInventorySha256 = "e8dd9cec0cdee54eb777c4e3779f47d8347fd620f3e7fe701cf62852a800255f";
    private static bool verificationQueued;

    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class PackageInventory
    { public bool pass; public string package_sha256, task_kind; public int asset_count, task_count; }
    [Serializable] private sealed class Task
    {
        public string kind, prefab_guid, prefab_source_sha256, source_model_guid, source_model_sha256;
        public string model_guid, model_sha256, variant_path, witness_noop_path, witness_path;
        public BoneMapping[] bone_mappings;
    }
    [Serializable] private sealed class BoneMapping
    { public string edited_bone_realization_id, source_model_uid; }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public string package_sha256;
        public string manifest_sha256;
        public string prefab_path, source_model_path, edited_model_path;
        public string source_model_sha256, source_model_meta_sha256;
        public string edited_model_sha256, edited_model_meta_sha256;
        public string prefab_sha256, prefab_meta_sha256;
        public string task_kind;
        public int source_vertices, source_triangles, source_indices, source_bones, source_materials;
        public int final_vertices, final_triangles, final_indices, final_bones, final_materials;
        public int source_shapes, final_shapes;
        public bool source_and_edited_import_settings_stable;
        public bool source_and_edited_assets_match_task_hashes;
        public bool variant_absent;
        public string[] realization_ids;
        public string[] bone_realization_ids;
    }

    static VapbModelSkinTopologyBoundaryImportRunner()
    {
        string state = SessionState.GetString(StateKey, "");
        if (state == "importing") Subscribe();
        else if (state == "verifying" || state == "verify-running")
        {
            if (state == "verify-running") SessionState.SetString(StateKey, "verifying");
            EditorApplication.update -= CheckTimeout;
            EditorApplication.update += CheckTimeout;
            QueueVerificationWhenReady();
        }
    }

    public static void ImportAndCaptureBaseline()
    {
        Report report = new Report { error = "UNEXPECTED_EXCEPTION" };
        string projectRoot = Path.GetFullPath(Path.GetDirectoryName(Application.dataPath));
        string guard = ValidateOwnedTarget(projectRoot);
        if (guard != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=" + guard);
            return;
        }
        try
        {
            string root = Path.GetFullPath(Environment.GetEnvironmentVariable("VAPB_STAGE3_TEST_ROOT"));
            string package = Path.Combine(root, "Output.unitypackage");
            string inventoryFile = Path.Combine(root, "OutputPackageInventory.json");
            if (!File.Exists(package) || HasReparseComponent(package) || Occupied(Path.Combine(projectRoot, EvidenceName)) ||
                Occupied(Path.Combine(projectRoot, ResultName)) || !File.Exists(inventoryFile) ||
                HasReparseComponent(inventoryFile) || HasReparseComponent(inventoryFile + ".meta"))
                throw new InvalidOperationException("OUTPUT_OR_EVIDENCE_PATH_INVALID");
            string packageHash = Hash(package);
            if (packageHash != ApprovedPackageSha256 || Hash(inventoryFile) != ApprovedInventorySha256)
                throw new InvalidOperationException("PACKAGE_OR_INVENTORY_NOT_PARENT_REVIEWED");
            PackageInventory inventory = JsonUtility.FromJson<PackageInventory>(File.ReadAllText(inventoryFile));
            if (inventory == null || !inventory.pass || inventory.asset_count != 12 || inventory.task_count != 1 ||
                inventory.task_kind != Kind || inventory.package_sha256 != packageHash)
                throw new InvalidOperationException("PACKAGE_PREFLIGHT_EVIDENCE_MISMATCH");
            string[] packagePaths = {
                ManifestPath,
                "Assets/VAPBExport/VapbRealizationMarker.cs",
                "Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs",
                "Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs",
                "Assets/VAPBExport/Editor/VapbSkinWeightImporter.cs" };
            foreach (string path in packagePaths)
            {
                string disk = Disk(path);
                if (Occupied(disk) || HasReparseComponent(disk) || HasReparseComponent(disk + ".meta"))
                    throw new InvalidOperationException("PACKAGE_ASSET_PATH_OCCUPIED:" + path);
            }
            report.package_sha256 = packageHash;
            SessionState.SetFloat(StartKey, (float)EditorApplication.timeSinceStartup);
            SessionState.SetString(StateKey, "importing");
            Subscribe();
            AssetDatabase.ImportPackage(package, false);
            Debug.Log("VAPB_MODEL_SKIN_TOPOLOGY_PACKAGE_IMPORT_STARTED sha256=" + report.package_sha256);
            return;
        }
        catch (Exception error) { report.error = error.Message; }
        Finish(report);
    }

    private static void Subscribe()
    {
        AssetDatabase.importPackageCompleted -= OnPackageCompleted;
        AssetDatabase.importPackageFailed -= OnPackageFailed;
        AssetDatabase.importPackageCancelled -= OnPackageCancelled;
        AssetDatabase.importPackageCompleted += OnPackageCompleted;
        AssetDatabase.importPackageFailed += OnPackageFailed;
        AssetDatabase.importPackageCancelled += OnPackageCancelled;
        EditorApplication.update -= CheckTimeout;
        EditorApplication.update += CheckTimeout;
    }
    private static void OnPackageCompleted(string name)
    {
        if (SessionState.GetString(StateKey, "") != "importing") return;
        if (ValidateCurrentTarget() != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=OWNERSHIP_CHANGED_DURING_IMPORT");
            return;
        }
        SessionState.SetString(StateKey, "verifying");
        QueueVerificationWhenReady();
    }
    private static void OnPackageFailed(string name, string error)
    {
        if (SessionState.GetString(StateKey, "") == "importing")
        {
            if (ValidateCurrentTarget() != null)
            {
                Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=OWNERSHIP_CHANGED_DURING_IMPORT");
                return;
            }
            Finish(new Report { error = "PACKAGE_IMPORT_FAILED:" + error });
        }
    }
    private static void OnPackageCancelled(string name)
    {
        if (SessionState.GetString(StateKey, "") == "importing")
        {
            if (ValidateCurrentTarget() != null)
            {
                Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=OWNERSHIP_CHANGED_DURING_IMPORT");
                return;
            }
            Finish(new Report { error = "PACKAGE_IMPORT_CANCELLED" });
        }
    }
    private static void CheckTimeout()
    {
        string state = SessionState.GetString(StateKey, "");
        if (state != "importing" && state != "verifying" && state != "verify-running") return;
        if (ValidateCurrentTarget() != null)
        {
            EditorApplication.update -= CheckTimeout;
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=OWNERSHIP_CHANGED_DURING_IMPORT");
            return;
        }
        float started = SessionState.GetFloat(StartKey, 0f);
        if (started > 0f && EditorApplication.timeSinceStartup - started > 180f)
            Finish(new Report { error = state == "importing" ? "PACKAGE_IMPORT_TIMEOUT" : "PACKAGE_VERIFY_TIMEOUT" });
    }

    private static void QueueVerificationWhenReady()
    {
        EditorApplication.update -= WaitForVerificationReady;
        EditorApplication.update += WaitForVerificationReady;
    }

    private static void WaitForVerificationReady()
    {
        if (SessionState.GetString(StateKey, "") != "verifying")
        {
            EditorApplication.update -= WaitForVerificationReady;
            return;
        }
        if (ValidateCurrentTarget() != null)
        {
            EditorApplication.update -= WaitForVerificationReady;
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=OWNERSHIP_CHANGED_DURING_VERIFY");
            return;
        }
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || verificationQueued) return;
        verificationQueued = true;
        EditorApplication.update -= WaitForVerificationReady;
        EditorApplication.delayCall += VerifyImportedPackage;
    }

    private static void VerifyImportedPackage()
    {
        verificationQueued = false;
        if (SessionState.GetString(StateKey, "") != "verifying") return;
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        {
            QueueVerificationWhenReady();
            return;
        }
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        string projectRoot = Path.GetFullPath(Path.GetDirectoryName(Application.dataPath));
        string guard = ValidateOwnedTarget(projectRoot);
        if (guard != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=" + guard);
            return;
        }
        try
        {
            SessionState.SetString(StateKey, "verify-running");
            string root = Path.GetFullPath(Environment.GetEnvironmentVariable("VAPB_STAGE3_TEST_ROOT"));
            string package = Path.Combine(root, "Output.unitypackage");
            string manifestFile = Disk(ManifestPath);
            if (!File.Exists(package) || !File.Exists(manifestFile) || HasReparseComponent(manifestFile) ||
                HasReparseComponent(manifestFile + ".meta"))
                throw new InvalidOperationException("IMPORTED_MANIFEST_MISSING_OR_UNSAFE");
            report.package_sha256 = Hash(package);
            report.manifest_sha256 = Hash(manifestFile);
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(manifestFile));
            if (manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 1 || manifest.reference_rebind_tasks[0] == null)
                throw new InvalidOperationException("TASK_CARDINALITY_INVALID");
            Task task = manifest.reference_rebind_tasks[0];
            report.task_kind = task.kind;
            if (task.kind != Kind || task.bone_mappings == null || task.bone_mappings.Length != 2)
                throw new InvalidOperationException("NORMAL_MODEL_SKIN_TASK_REQUIRED");
            report.prefab_path = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            report.source_model_path = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
            report.edited_model_path = AssetDatabase.GUIDToAssetPath(task.model_guid);
            if (!OwnedAssetPath(task.variant_path) || !OwnedAssetPath(report.prefab_path) || !OwnedAssetPath(report.source_model_path) ||
                !OwnedAssetPath(report.edited_model_path))
                throw new InvalidOperationException("TASK_ASSET_PATH_INVALID");
            string prefabFile = Disk(report.prefab_path), sourceFile = Disk(report.source_model_path),
                editedFile = Disk(report.edited_model_path);
            if (!File.Exists(prefabFile) || !File.Exists(sourceFile) || !File.Exists(editedFile) ||
                new[] { prefabFile, sourceFile, editedFile, prefabFile + ".meta", sourceFile + ".meta",
                    editedFile + ".meta" }.Any(HasReparseComponent))
                throw new InvalidOperationException("TASK_ASSET_MISSING_OR_UNSAFE");
            if (Hash(prefabFile) != task.prefab_source_sha256 || Hash(sourceFile) != task.source_model_sha256 ||
                Hash(editedFile) != task.model_sha256)
                throw new InvalidOperationException("TASK_ASSET_HASH_MISMATCH");

            ModelImporter sourceImporter = AssetImporter.GetAtPath(report.source_model_path) as ModelImporter;
            ModelImporter editedImporter = AssetImporter.GetAtPath(report.edited_model_path) as ModelImporter;
            if (sourceImporter == null || editedImporter == null)
                throw new InvalidOperationException("MODEL_IMPORTER_MISSING");
            ConfigureImporter(sourceImporter);
            sourceImporter = AssetImporter.GetAtPath(report.source_model_path) as ModelImporter;
            editedImporter = AssetImporter.GetAtPath(report.edited_model_path) as ModelImporter;
            if (sourceImporter == null || editedImporter == null)
                throw new InvalidOperationException("MODEL_IMPORTER_MISSING_AFTER_SOURCE_REIMPORT");
            if (sourceImporter.isReadable != editedImporter.isReadable ||
                sourceImporter.materialName != editedImporter.materialName ||
                sourceImporter.weldVertices != editedImporter.weldVertices ||
                sourceImporter.optimizeMeshVertices != editedImporter.optimizeMeshVertices ||
                sourceImporter.optimizeMeshPolygons != editedImporter.optimizeMeshPolygons)
                ConfigureImporter(editedImporter);
            sourceImporter = AssetImporter.GetAtPath(report.source_model_path) as ModelImporter;
            editedImporter = AssetImporter.GetAtPath(report.edited_model_path) as ModelImporter;
            report.source_and_edited_import_settings_stable = MatchingImportSettings(sourceImporter) &&
                MatchingImportSettings(editedImporter);
            if (!report.source_and_edited_import_settings_stable)
                throw new InvalidOperationException("MODEL_IMPORT_SETTINGS_MISMATCH");
            AssetDatabase.ImportAsset(report.source_model_path,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.ImportAsset(report.edited_model_path,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            sourceImporter = AssetImporter.GetAtPath(report.source_model_path) as ModelImporter;
            editedImporter = AssetImporter.GetAtPath(report.edited_model_path) as ModelImporter;
            report.source_and_edited_import_settings_stable = MatchingImportSettings(sourceImporter) &&
                MatchingImportSettings(editedImporter);

            report.source_model_sha256 = Hash(sourceFile);
            report.source_model_meta_sha256 = Hash(sourceFile + ".meta");
            report.edited_model_sha256 = Hash(editedFile);
            report.edited_model_meta_sha256 = Hash(editedFile + ".meta");
            report.prefab_sha256 = Hash(prefabFile);
            report.prefab_meta_sha256 = Hash(prefabFile + ".meta");
            report.source_and_edited_assets_match_task_hashes = report.source_model_sha256 == task.source_model_sha256 &&
                report.edited_model_sha256 == task.model_sha256 && report.prefab_sha256 == task.prefab_source_sha256;
            GameObject sourceRoot = AssetDatabase.LoadAssetAtPath<GameObject>(report.source_model_path);
            GameObject editedRoot = AssetDatabase.LoadAssetAtPath<GameObject>(report.edited_model_path);
            GameObject prefabRoot = AssetDatabase.LoadAssetAtPath<GameObject>(report.prefab_path);
            SkinnedMeshRenderer sourceSkin = SingleSkin(sourceRoot), editedSkin = SingleSkin(editedRoot),
                prefabSkin = SingleSkin(prefabRoot);
            if (sourceSkin == null || editedSkin == null || prefabSkin == null ||
                sourceSkin.sharedMesh == null || editedSkin.sharedMesh == null ||
                sourceSkin.bones == null || editedSkin.bones == null)
                throw new InvalidOperationException("IMPORTED_SKIN_MISSING");
            report.source_vertices = sourceSkin.sharedMesh.vertexCount;
            report.source_triangles = TriangleCount(sourceSkin.sharedMesh);
            report.source_indices = IndexCount(sourceSkin.sharedMesh);
            report.source_bones = sourceSkin.bones.Length;
            report.source_materials = sourceSkin.sharedMaterials.Length;
            report.source_shapes = sourceSkin.sharedMesh.blendShapeCount;
            report.final_vertices = editedSkin.sharedMesh.vertexCount;
            report.final_triangles = TriangleCount(editedSkin.sharedMesh);
            report.final_indices = IndexCount(editedSkin.sharedMesh);
            report.final_bones = editedSkin.bones.Length;
            report.final_materials = editedSkin.sharedMaterials.Length;
            report.final_shapes = editedSkin.sharedMesh.blendShapeCount;
            report.realization_ids = editedRoot.GetComponentsInChildren<MonoBehaviour>(true)
                .Where(component => component != null && component.GetType().FullName == "VapbRealizationMarker")
                .Select(component => (string)component.GetType().GetField("realizationId").GetValue(component))
                .Where(value => !String.IsNullOrEmpty(value)).Distinct().ToArray();
            report.bone_realization_ids = editedRoot.GetComponentsInChildren<MonoBehaviour>(true)
                .Where(component => component != null && component.GetType().FullName == "VapbRealizationMarker")
                .Select(component => (string)component.GetType().GetField("boneRealizationId").GetValue(component))
                .Where(value => !String.IsNullOrEmpty(value)).Distinct().OrderBy(value => value, StringComparer.Ordinal).ToArray();
            report.variant_absent = !Occupied(Disk(task.variant_path));
            if (report.source_vertices != 4 || report.source_triangles != 2 || report.source_indices != 6 ||
                report.source_bones != 2 || report.source_materials != 1 || report.source_shapes != 0 ||
                report.final_vertices != 6 || report.final_triangles != 2 || report.final_indices != 6 ||
                report.final_bones != 2 || report.final_materials != 1 || report.final_shapes != 0 ||
                report.realization_ids.Length != 1 || report.bone_realization_ids.Length != 2 ||
                !report.source_and_edited_import_settings_stable || !report.source_and_edited_assets_match_task_hashes ||
                !report.variant_absent)
                throw new InvalidOperationException("POST_IMPORT_BASELINE_MISMATCH");
            report.pass = true;
            report.error = "NONE";
        }
        catch (Exception error) { report.error = error.Message; }
        Finish(report);
    }

    private static void ConfigureImporter(ModelImporter importer)
    {
        bool changed = false;
        if (!importer.isReadable) { importer.isReadable = true; changed = true; }
        if (importer.materialName != ModelImporterMaterialName.BasedOnMaterialName)
        { importer.materialName = ModelImporterMaterialName.BasedOnMaterialName; changed = true; }
        if (importer.weldVertices) { importer.weldVertices = false; changed = true; }
        if (importer.optimizeMeshVertices) { importer.optimizeMeshVertices = false; changed = true; }
        if (importer.optimizeMeshPolygons) { importer.optimizeMeshPolygons = false; changed = true; }
        if (changed) importer.SaveAndReimport();
    }
    private static bool MatchingImportSettings(ModelImporter importer) => importer != null && importer.isReadable &&
        importer.materialName == ModelImporterMaterialName.BasedOnMaterialName && !importer.weldVertices &&
        !importer.optimizeMeshVertices && !importer.optimizeMeshPolygons;
    private static void Finish(Report report)
    {
        string projectRoot = Path.GetFullPath(Path.GetDirectoryName(Application.dataPath));
        string guard = ValidateOwnedTarget(projectRoot);
        if (guard != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BLOCKED=" + guard);
            return;
        }
        string reportFile = Path.Combine(projectRoot, EvidenceName);
        AssetDatabase.importPackageCompleted -= OnPackageCompleted;
        AssetDatabase.importPackageFailed -= OnPackageFailed;
        AssetDatabase.importPackageCancelled -= OnPackageCancelled;
        EditorApplication.update -= CheckTimeout;
        EditorApplication.update -= WaitForVerificationReady;
        SessionState.SetString(StateKey, "finished");
        try
        {
            byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true));
            using (var stream = new FileStream(reportFile, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                stream.Write(bytes, 0, bytes.Length);
        }
        catch (Exception error) { report.pass = false; report.error = "EVIDENCE_WRITE_FAILED:" + error.Message; }
        Debug.Log(report.pass ? "VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BASELINE_PASS" :
            "VAPB_MODEL_SKIN_TOPOLOGY_IMPORT_BASELINE_FAIL=" + report.error);
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
    private static string ValidateOwnedTarget(string projectRoot)
    {
        string raw = Environment.GetEnvironmentVariable("VAPB_STAGE3_TEST_ROOT");
        if (String.IsNullOrWhiteSpace(raw)) return "TEST_ROOT_ENV_MISSING";
        string root = Path.GetFullPath(raw), target = Path.Combine(root, "TargetProject");
        if (!String.Equals(projectRoot, target, StringComparison.OrdinalIgnoreCase)) return "TARGET_NOT_DIRECT_OWNED_CHILD";
        if (new[] { root, target, Path.Combine(root, RootMarker), Path.Combine(root, "SourceProject", SourceMarker),
                Path.Combine(target, TargetMarker), Disk("Assets") }.Any(HasReparseComponent))
            return "OWNED_PATH_REPARSE_POINT";
        if (!File.Exists(Path.Combine(root, RootMarker)) || !File.Exists(Path.Combine(root, "SourceProject", SourceMarker)) ||
            !File.Exists(Path.Combine(target, TargetMarker)) ||
            File.ReadAllText(Path.Combine(root, RootMarker)).Trim() != "VAPB_STAGE3_OWNED_TEST_ROOT_V1" ||
            File.ReadAllText(Path.Combine(root, "SourceProject", SourceMarker)).Trim() != "VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1")
            return "OWNERSHIP_MARKER_INVALID";
        if (!File.ReadAllText(Path.Combine(root, "SourceProject", "ProjectSettings", "ProjectVersion.txt"))
                .Contains("m_EditorVersion: 2022.3.22f1") ||
            !File.ReadAllText(Path.Combine(target, "ProjectSettings", "ProjectVersion.txt"))
                .Contains("m_EditorVersion: 2022.3.22f1")) return "UNITY_VERSION_MISMATCH";
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
    private static string ValidateCurrentTarget() => ValidateOwnedTarget(
        Path.GetFullPath(Path.GetDirectoryName(Application.dataPath)));
    private static bool OwnedAssetPath(string path) => !String.IsNullOrEmpty(path) &&
        path.StartsWith("Assets/", StringComparison.Ordinal) && path.IndexOf('\\') < 0 &&
        path.IndexOf(':') < 0 && !Path.IsPathRooted(path) &&
        !path.Split('/').Any(part => part == ".." || part == "." || part.Length == 0);
    private static string Disk(string path) => Path.GetFullPath(Path.Combine(Application.dataPath,
        path.StartsWith("Assets/", StringComparison.Ordinal) ? path.Substring(7).Replace('/', Path.DirectorySeparatorChar) : ""));
    private static bool Occupied(string path) => File.Exists(path) || Directory.Exists(path) ||
        File.Exists(path + ".meta") || Directory.Exists(path + ".meta");
    private static SkinnedMeshRenderer SingleSkin(GameObject root)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] skins = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        return skins.Length == 1 ? skins[0] : null;
    }
    private static int TriangleCount(Mesh mesh) => mesh.subMeshCount == 1 &&
        mesh.GetTopology(0) == MeshTopology.Triangles ? (int)(mesh.GetIndexCount(0) / 3) : -1;
    private static int IndexCount(Mesh mesh) => mesh.subMeshCount == 1 ? (int)mesh.GetIndexCount(0) : -1;
    private static string Hash(string path)
    {
        using (SHA256 hash = SHA256.Create())
            return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static bool HasReparseComponent(string path)
    {
        string full = Path.GetFullPath(path), volume = Path.GetPathRoot(full), current = volume;
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
