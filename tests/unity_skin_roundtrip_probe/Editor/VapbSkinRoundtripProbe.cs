using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbSkinRoundtripProbe
{
    private const string Folder = "Assets/VapbSkinRoundtrip";
    private const string Input = Folder + "/Input.fbx";
    private const string Prefab = Folder + "/Avatar.prefab";
    private const string MaterialPath = Folder + "/Original.mat";
    private const string Manifest = "Assets/VAPBExport/manifest.json";
    private const string Phase = "VAPB_SKIN_ROUNDTRIP_PHASE";
    private const string ImportStart = "VAPB_SKIN_ROUNDTRIP_IMPORT_START";

    [Serializable] private sealed class BoneInfo
    {
        public string name; // Synthetic fixture display aid only; production never joins by name.
        public string target_transform_file_id;
    }
    [Serializable] private sealed class SourceInfo
    {
        public string prefab_guid;
        public string renderer_file_id;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string source_mesh_file_id;
        public string material_guid;
        public string material_file_id;
        public string root_bone_target_transform_file_id;
        public BoneInfo[] bones;
        public string original_vertex_checksum;
        public string original_weight_checksum;
        public int original_vertex_count;
    }
    [Serializable] private sealed class OutputManifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string model_guid;
        public string realization_id;
        public BoneTask[] bones;
        public string root_bone_target_transform_file_id;
    }
    [Serializable] private sealed class BoneTask
    {
        public string edited_bone_realization_id;
        public string target_transform_file_id;
    }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string phase;
        public string error;
        public bool packageImported;
        public bool firstApply;
        public bool editedMesh;
        public bool changedVertices;
        public bool changedWeights;
        public bool boneIdsPreserved;
        public bool materialsPreserved;
        public bool sourceModelUnchanged;
        public bool unrelatedStatePreserved;
        public bool expectedDeformation;
        public float deformationMaxError;
        public float deformationMaxExpected;
        public float deformationMaxObserved;
        public int deformationWeightedVertices;
        public bool secondApply;
        public bool secondApplyUnchanged;
        public bool invalidMappingRejected;
        public bool invalidMappingUnchanged;
        public int boneCount;
        public int vertexCount;
    }

    static VapbSkinRoundtripProbe()
    {
        AssetDatabase.importPackageCompleted += OnImportCompleted;
        AssetDatabase.importPackageFailed += OnImportFailed;
        AssetDatabase.importPackageCancelled += OnImportCancelled;
        EditorApplication.update += CheckTimeout;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }

    private static void OnImportCompleted(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "completed");
        EditorApplication.delayCall += ValidateImported;
    }
    private static void OnImportFailed(string name, string error)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_FAILED" });
    }
    private static void OnImportCancelled(string name)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_CANCELLED" });
    }
    private static void CheckTimeout()
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        float started = SessionState.GetFloat(ImportStart, 0f);
        if (started > 0f && EditorApplication.timeSinceStartup - started > 180f)
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_TIMEOUT" });
    }

    public static void Prepare()
    {
        var report = new Report { phase = "prepare", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            AssetDatabase.ImportAsset(Input, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
            SkinnedMeshRenderer imported = SingleSkin(model);
            if (imported == null || imported.sharedMesh == null || imported.bones.Length < 2 ||
                imported.rootBone == null)
                throw new InvalidOperationException("INPUT_SKIN_UNSUPPORTED");
            Shader shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidOperationException("STANDARD_SHADER_MISSING");
            Material material = new Material(shader) { name = "SkinOriginal" };
            AssetDatabase.CreateAsset(material, MaterialPath);
            GameObject instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
            if (instance == null) throw new InvalidOperationException("MODEL_INSTANCE_FAILED");
            try
            {
                PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                instance.name = "Avatar";
                SkinnedMeshRenderer skin = SingleSkin(instance);
                if (skin == null || skin.bones.Length != imported.bones.Length)
                    throw new InvalidOperationException("UNPACK_SKIN_UNSUPPORTED");
                skin.sharedMaterials = new[] { material };
                GameObject sentinel = new GameObject("UnrelatedSentinel");
                sentinel.transform.SetParent(instance.transform, false);
                sentinel.transform.localPosition = new Vector3(4f, 5f, 6f);
                if (PrefabUtility.SaveAsPrefabAsset(instance, Prefab) == null)
                    throw new InvalidOperationException("PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer renderer = SingleSkin(prefab);
            if (renderer == null || renderer.sharedMesh == null)
                throw new InvalidOperationException("PREFAB_SKIN_UNSUPPORTED");
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string prefabGuid, out long rendererId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.sharedMesh, out string modelGuid, out long meshId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId) ||
                modelGuid != AssetDatabase.AssetPathToGUID(Input))
                throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
            var bones = new BoneInfo[renderer.bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                Transform bone = renderer.bones[i];
                if (bone == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(bone, out string guid, out long id) ||
                    guid != prefabGuid)
                    throw new InvalidOperationException("BONE_ID_UNAVAILABLE");
                bones[i] = new BoneInfo { name = bone.name, target_transform_file_id = Id(id) };
            }
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rootBone, out string rootGuid, out long rootId) ||
                rootGuid != prefabGuid)
                throw new InvalidOperationException("ROOT_ID_UNAVAILABLE");
            var info = new SourceInfo
            {
                prefab_guid = prefabGuid,
                renderer_file_id = Id(rendererId),
                prefab_source_sha256 = FileHash(AssetFile(Prefab)),
                source_model_guid = modelGuid,
                source_model_sha256 = FileHash(AssetFile(Input)),
                source_mesh_file_id = Id(meshId),
                material_guid = materialGuid,
                material_file_id = Id(materialId),
                root_bone_target_transform_file_id = Id(rootId),
                bones = bones,
                original_vertex_checksum = VertexChecksum(renderer.sharedMesh),
                original_weight_checksum = WeightChecksum(renderer.sharedMesh),
                original_vertex_count = renderer.sharedMesh.vertexCount
            };
            File.WriteAllText(ProjectFile("SourceInfo.json"), JsonUtility.ToJson(info, true));
            AssetDatabase.ExportPackage(new[] { Input, Prefab, MaterialPath }, ProjectFile("Source.unitypackage"),
                ExportPackageOptions.IncludeDependencies);
            report.pass = File.Exists(ProjectFile("Source.unitypackage"));
            report.error = report.pass ? "NONE" : "PACKAGE_MISSING";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    public static void Validate()
    {
        try
        {
            if (!File.Exists(ProjectFile("SourceInfo.json")) || !File.Exists(ProjectFile("Output.unitypackage")))
                throw new FileNotFoundException();
            SessionState.SetString(Phase, "importing");
            SessionState.SetFloat(ImportStart, (float)EditorApplication.timeSinceStartup);
            AssetDatabase.ImportPackage(ProjectFile("Output.unitypackage"), false);
        }
        catch (Exception error) { Finish(new Report { phase = "validate", error = SafeError(error) }); }
    }

    private static void ValidateImported()
    {
        if (SessionState.GetString(Phase, "") != "completed") return;
        SessionState.SetString(Phase, "validating");
        var report = new Report { phase = "validate", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            SourceInfo info = JsonUtility.FromJson<SourceInfo>(File.ReadAllText(ProjectFile("SourceInfo.json")));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            report.packageImported = AssetDatabase.LoadAssetAtPath<TextAsset>(Manifest) != null;
            if (!report.packageImported) throw new InvalidOperationException("MANIFEST_NOT_IMPORTED");
            OutputManifest output = JsonUtility.FromJson<OutputManifest>(File.ReadAllText(AssetFile(Manifest)));
            if (output == null || output.reference_rebind_tasks == null || output.reference_rebind_tasks.Length != 1 ||
                output.reference_rebind_tasks[0].kind != "REBIND_SKINNED_RENDERER_V1" ||
                output.reference_rebind_tasks[0].bones == null ||
                (output.reference_rebind_tasks[0].bones.Length != info.bones.Length &&
                 output.reference_rebind_tasks[0].bones.Length != info.bones.Length + 1))
                throw new InvalidOperationException("OUTPUT_TASK_INVALID");
            Task task = output.reference_rebind_tasks[0];
            report.firstApply = VapbReferenceFinalizer.Apply(Manifest);
            if (!report.firstApply) throw new InvalidOperationException("FIRST_APPLY_FAILED");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer skin = SingleSkin(prefab);
            Mesh mesh = skin == null ? null : skin.sharedMesh;
            report.boneCount = skin == null ? 0 : skin.bones.Length;
            report.vertexCount = mesh == null ? 0 : mesh.vertexCount;
            report.editedMesh = mesh != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string meshGuid, out long meshId) &&
                meshGuid == task.model_guid && meshId != 0;
            report.changedVertices = mesh != null && VertexChecksum(mesh) != info.original_vertex_checksum;
            report.changedWeights = mesh != null && WeightChecksum(mesh) != info.original_weight_checksum;
            report.boneIdsPreserved = skin != null && skin.bones.Length == info.bones.Length &&
                task.root_bone_target_transform_file_id == info.root_bone_target_transform_file_id;
            if (report.boneIdsPreserved)
            {
                var mapping = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (BoneTask row in task.bones)
                    mapping.Add(row.edited_bone_realization_id, row.target_transform_file_id);
                GameObject editedModel = AssetDatabase.LoadAssetAtPath<GameObject>(
                    AssetDatabase.GUIDToAssetPath(task.model_guid));
                SkinnedMeshRenderer editedSkin = SingleSkin(editedModel);
                report.boneIdsPreserved &= editedSkin != null && editedSkin.bones.Length == skin.bones.Length;
                for (int i = 0; i < skin.bones.Length; i++)
                {
                    Transform bone = skin.bones[i];
                    Transform editedBone = editedSkin == null || i >= editedSkin.bones.Length ? null : editedSkin.bones[i];
                    string marker = editedBone == null ? null :
                        editedBone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
                    report.boneIdsPreserved &= bone != null &&
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(bone, out string guid, out long id) &&
                        guid == info.prefab_guid && marker != null &&
                        mapping.TryGetValue(marker, out string targetId) && Id(id) == targetId;
                }
                report.boneIdsPreserved &= skin.rootBone != null &&
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.rootBone, out string rootGuid, out long rootId) &&
                    rootGuid == info.prefab_guid && Id(rootId) == info.root_bone_target_transform_file_id;
            }
            report.materialsPreserved = skin != null && skin.sharedMaterials.Length == 1 &&
                skin.sharedMaterials[0] != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.sharedMaterials[0], out string matGuid, out long matId) &&
                matGuid == info.material_guid && Id(matId) == info.material_file_id;
            report.sourceModelUnchanged = FileHash(AssetFile(Input)) == info.source_model_sha256;
            Transform sentinel = prefab == null ? null : prefab.transform.Find("UnrelatedSentinel");
            report.unrelatedStatePreserved = prefab != null && prefab.name == "Avatar" && sentinel != null &&
                sentinel.localPosition == new Vector3(4f, 5f, 6f);
            report.expectedDeformation = skin != null && DeformsWithWeights(prefab, skin, report);
            byte[] first = File.ReadAllBytes(AssetFile(Prefab));
            report.secondApply = VapbReferenceFinalizer.Apply(Manifest);
            report.secondApplyUnchanged = report.secondApply && Equal(first, File.ReadAllBytes(AssetFile(Prefab)));
            string text = File.ReadAllText(AssetFile(Manifest));
            string impossible = "9223372036854775806";
            if (info.bones[0].target_transform_file_id == impossible) impossible = "9223372036854775805";
            string bad = Regex.Replace(text, "\"target_transform_file_id\"\\s*:\\s*\"" +
                Regex.Escape(task.bones[0].target_transform_file_id) + "\"",
                "\"target_transform_file_id\":\"" + impossible + "\"", RegexOptions.None,
                TimeSpan.FromSeconds(1));
            if (bad == text) throw new InvalidOperationException("BONE_ID_NOT_IN_MANIFEST");
            string negative = "Assets/VAPBExport/negative-skin-probe.json";
            File.WriteAllText(AssetFile(negative), bad);
            AssetDatabase.ImportAsset(negative, ImportAssetOptions.ForceUpdate);
            try
            {
                report.invalidMappingRejected = !VapbReferenceFinalizer.Apply(negative);
                report.invalidMappingUnchanged = Equal(first, File.ReadAllBytes(AssetFile(Prefab)));
            }
            finally { AssetDatabase.DeleteAsset(negative); }
            report.pass = report.packageImported && report.firstApply && report.editedMesh &&
                report.changedVertices && report.changedWeights && report.boneIdsPreserved &&
                report.materialsPreserved && report.sourceModelUnchanged && report.unrelatedStatePreserved &&
                report.expectedDeformation && report.secondApply && report.secondApplyUnchanged &&
                report.invalidMappingRejected && report.invalidMappingUnchanged;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    private static bool DeformsWithWeights(GameObject prefab, SkinnedMeshRenderer assetSkin, Report report)
    {
        GameObject instance = UnityEngine.Object.Instantiate(prefab);
        Mesh before = new Mesh();
        Mesh after = new Mesh();
        try
        {
            SkinnedMeshRenderer skin = SingleSkin(instance);
            if (skin == null || skin.bones.Length < 2) return false;
            int leafIndex = skin.bones.Length - 1;
            Transform leaf = skin.bones[leafIndex];
            if (leaf == null) return false;
            skin.BakeMesh(before, true);
            Vector3 original = leaf.localPosition;
            Vector3 oldWorld = leaf.position;
            leaf.localPosition = original + new Vector3(0.2f, 0f, 0f);
            Vector3 localDisplacement = skin.transform.worldToLocalMatrix.MultiplyVector(leaf.position - oldWorld);
            skin.BakeMesh(after, true);
            var counts = assetSkin.sharedMesh.GetBonesPerVertex();
            var weights = assetSkin.sharedMesh.GetAllBoneWeights();
            try
            {
                if (before.vertexCount != after.vertexCount || before.vertexCount != counts.Length) return false;
                int offset = 0;
                bool affected = false;
                Vector3[] a = before.vertices, b = after.vertices;
                for (int vertex = 0; vertex < counts.Length; vertex++)
                {
                    float influence = 0f;
                    for (int i = 0; i < counts[vertex]; i++)
                        if (weights[offset + i].boneIndex == leafIndex)
                            influence += weights[offset + i].weight;
                    offset += counts[vertex];
                    Vector3 expected = localDisplacement * influence;
                    Vector3 observed = b[vertex] - a[vertex];
                    report.deformationMaxError = Mathf.Max(report.deformationMaxError,
                        (observed - expected).magnitude);
                    report.deformationMaxExpected = Mathf.Max(report.deformationMaxExpected, expected.magnitude);
                    report.deformationMaxObserved = Mathf.Max(report.deformationMaxObserved, observed.magnitude);
                    if (influence > 0.01f)
                    {
                        report.deformationWeightedVertices++;
                        affected |= observed.magnitude > 0.001f;
                    }
                }
                return affected && report.deformationMaxError <= 0.005f;
            }
            finally { counts.Dispose(); weights.Dispose(); }
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(before);
            UnityEngine.Object.DestroyImmediate(after);
            UnityEngine.Object.DestroyImmediate(instance);
        }
    }

    private static SkinnedMeshRenderer SingleSkin(GameObject root)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] values = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        return values.Length == 1 ? values[0] : null;
    }
    private static string VertexChecksum(Mesh mesh)
    {
        using (SHA256 sha = SHA256.Create())
        using (MemoryStream memory = new MemoryStream())
        using (BinaryWriter writer = new BinaryWriter(memory))
        {
            foreach (Vector3 value in mesh.vertices)
            { writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); }
            writer.Flush();
            return Convert.ToBase64String(sha.ComputeHash(memory.ToArray()));
        }
    }
    private static string WeightChecksum(Mesh mesh)
    {
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            using (SHA256 sha = SHA256.Create())
            using (MemoryStream memory = new MemoryStream())
            using (BinaryWriter writer = new BinaryWriter(memory))
            {
                for (int i = 0; i < counts.Length; i++) writer.Write(counts[i]);
                for (int i = 0; i < weights.Length; i++)
                { writer.Write(weights[i].boneIndex); writer.Write(weights[i].weight); }
                writer.Flush();
                return Convert.ToBase64String(sha.ComputeHash(memory.ToArray()));
            }
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }
    private static string Id(long value) { return value.ToString(CultureInfo.InvariantCulture); }
    private static string FileHash(string path)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static bool Equal(byte[] a, byte[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }
    private static string ProjectFile(string name)
    { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }
    private static string AssetFile(string path)
    { return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string SafeError(Exception error)
    {
        if (error is InvalidOperationException)
        {
            switch (error.Message)
            {
                case "INPUT_SKIN_UNSUPPORTED": case "STANDARD_SHADER_MISSING": case "MODEL_INSTANCE_FAILED":
                case "UNPACK_SKIN_UNSUPPORTED": case "PREFAB_SAVE_FAILED": case "PREFAB_SKIN_UNSUPPORTED":
                case "ASSET_ID_UNAVAILABLE": case "BONE_ID_UNAVAILABLE": case "ROOT_ID_UNAVAILABLE":
                case "MANIFEST_NOT_IMPORTED": case "OUTPUT_TASK_INVALID": case "FIRST_APPLY_FAILED":
                case "BONE_ID_NOT_IN_MANIFEST": return error.Message;
            }
        }
        return error.GetType().Name;
    }
    private static void Finish(Report report)
    {
        SessionState.SetString(Phase, "");
        try { File.WriteAllText(ProjectFile("VapbSkinRoundtripResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_SKIN_ROUNDTRIP_PASS" : "VAPB_SKIN_ROUNDTRIP_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
