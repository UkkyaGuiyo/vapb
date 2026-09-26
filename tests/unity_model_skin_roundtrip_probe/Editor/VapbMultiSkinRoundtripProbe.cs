using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Bounded public two-direct-skin restoration check. No names identify assets.
[InitializeOnLoad]
public static class VapbMultiSkinRoundtripProbe
{
    private const string Phase = "VAPB_MULTI_SKIN_PHASE";
    private const string Started = "VAPB_MULTI_SKIN_STARTED";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind, prefab_guid, prefab_source_sha256, source_model_guid;
        public string source_model_sha256, model_guid, model_sha256, variant_path;
        public string realization_id;
        public Candidate[] renderer_candidates;
    }
    [Serializable] private sealed class Candidate
    { public string renderer_file_id, source_mesh_file_id; }
    [Serializable] private sealed class SourceInfo
    {
        public string prefab_guid, prefab_source_sha256, source_model_guid;
        public string source_model_sha256, material_guid, material_file_id;
        public SkinInfo[] skins;
    }
    [Serializable] private sealed class SkinInfo
    {
        public string renderer_file_id, source_mesh_file_id;
        public string root_bone_target_transform_file_id;
        public BoneInfo[] bones;
    }
    [Serializable] private sealed class BoneInfo { public string target_transform_file_id; }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool imported, bad_second_rejected_before_save, original_unchanged;
        public bool first_apply, one_linked_variant, two_exact_edited_skins;
        public bool both_geometry_changed, geometry_matches_edited_models;
        public bool bones_and_materials_preserved, sibling_state_preserved;
        public bool second_apply_unchanged;
        public int selected_skin_count, original_renderer_count;
    }

    static VapbMultiSkinRoundtripProbe()
    {
        AssetDatabase.importPackageCompleted += OnComplete;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        EditorApplication.update += Timeout;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }
    public static void Validate()
    {
        try
        {
            string package = ProjectFile("Output.unitypackage");
            if (!File.Exists(package)) throw new InvalidOperationException("PACKAGE_MISSING");
            SessionState.SetString(Phase, "importing");
            SessionState.SetFloat(Started, (float)EditorApplication.timeSinceStartup);
            AssetDatabase.ImportPackage(package, false);
        }
        catch { Finish(new Report { error = "PACKAGE_IMPORT_START_FAILED" }); }
    }
    public static void RunImported() { ValidateImported(); }
    private static void OnComplete(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "completed");
        EditorApplication.delayCall += ValidateImported;
    }
    private static void OnFailed(string name, string error)
    { if (SessionState.GetString(Phase, "") == "importing") Finish(new Report { error = "PACKAGE_IMPORT_FAILED" }); }
    private static void OnCancelled(string name)
    { if (SessionState.GetString(Phase, "") == "importing") Finish(new Report { error = "PACKAGE_IMPORT_CANCELLED" }); }
    private static void Timeout()
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        float started = SessionState.GetFloat(Started, 0);
        if (started > 0 && EditorApplication.timeSinceStartup - started > 180)
            Finish(new Report { error = "PACKAGE_IMPORT_TIMEOUT" });
    }

    private static void ValidateImported()
    {
        if (SessionState.GetString(Phase, "") != "completed" && SessionState.GetString(Phase, "") != "") return;
        SessionState.SetString(Phase, "validating");
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        try
        {
            SourceInfo info = JsonUtility.FromJson<SourceInfo>(File.ReadAllText(ProjectFile("MultiSkinSourceInfo.json")));
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
            if (info == null || info.skins == null || info.skins.Length != 2 ||
                manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 2)
                throw new InvalidOperationException("SOURCE_OR_TASK_INVALID");
            Task[] tasks = manifest.reference_rebind_tasks;
            if (tasks[0].kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" ||
                tasks[1].kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" ||
                tasks[0].variant_path != tasks[1].variant_path ||
                tasks[0].prefab_guid != info.prefab_guid || tasks[1].prefab_guid != info.prefab_guid ||
                tasks[0].model_guid == tasks[1].model_guid ||
                tasks[0].realization_id == tasks[1].realization_id)
                throw new InvalidOperationException("TASK_IDENTITY_INVALID");
            string variantPath = tasks[0].variant_path;
            string prefabPath = AssetDatabase.GUIDToAssetPath(info.prefab_guid);
            string sourcePath = AssetDatabase.GUIDToAssetPath(info.source_model_guid);
            GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (source == null || sourcePath == "" || AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath) == null)
                throw new InvalidOperationException("SOURCE_MISSING");
            report.imported = true;
            report.original_renderer_count = source.GetComponentsInChildren<Renderer>(true).Length;
            report.original_unchanged = Hash(Disk(prefabPath)) == info.prefab_source_sha256 &&
                Hash(Disk(sourcePath)) == info.source_model_sha256;
            if (!report.original_unchanged || AssetDatabase.LoadAssetAtPath<GameObject>(variantPath) != null)
                throw new InvalidOperationException("SOURCE_OR_VARIANT_DRIFT");
            Dictionary<string, Vector3[]> originalVertices = ReadSourceVertices(sourcePath, info);
            report.bad_second_rejected_before_save = BadSecondTaskRejected(variantPath);
            if (!report.bad_second_rejected_before_save)
                throw new InvalidOperationException("BAD_SECOND_ACCEPTED");
            report.first_apply = VapbModelSkinFinalizer.Apply(ManifestPath);
            if (!report.first_apply) throw new InvalidOperationException("FIRST_APPLY_FAILED");
            GameObject variant = AssetDatabase.LoadAssetAtPath<GameObject>(variantPath);
            source = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            report.one_linked_variant = variant != null &&
                PrefabUtility.GetPrefabAssetType(variant) == PrefabAssetType.Variant &&
                PrefabUtility.GetCorrespondingObjectFromSource(variant) == source;
            if (!report.one_linked_variant) throw new InvalidOperationException("VARIANT_INVALID");
            var editedGuids = new HashSet<string>();
            var matchedRows = new HashSet<string>();
            report.bones_and_materials_preserved = true;
            report.both_geometry_changed = true;
            report.geometry_matches_edited_models = true;
            report.sibling_state_preserved =
                variant.GetComponentsInChildren<Transform>(true).Length ==
                source.GetComponentsInChildren<Transform>(true).Length &&
                variant.GetComponentsInChildren<Renderer>(true).Length == report.original_renderer_count;
            foreach (Transform transform in variant.GetComponentsInChildren<Transform>(true))
            {
                Transform original = PrefabUtility.GetCorrespondingObjectFromSource(transform) as Transform;
                if (original == null || transform.localPosition != original.localPosition ||
                    transform.localRotation != original.localRotation || transform.localScale != original.localScale)
                    report.sibling_state_preserved = false;
            }
            foreach (Renderer renderer in variant.GetComponentsInChildren<Renderer>(true))
            {
                Renderer original = PrefabUtility.GetCorrespondingObjectFromSource(renderer) as Renderer;
                if (original == null || renderer.GetType() != original.GetType() ||
                    !SameMaterials(renderer.sharedMaterials, original.sharedMaterials))
                    throw new InvalidOperationException("RENDERER_STATE_CHANGED");
                var edited = renderer as SkinnedMeshRenderer;
                var originalSkin = original as SkinnedMeshRenderer;
                if (edited == null || originalSkin == null || edited.sharedMesh == null ||
                    originalSkin.sharedMesh == null) throw new InvalidOperationException("SKIN_MISSING");
                string originalGuid, editedGuid, rendererGuid;
                long originalMeshId, rendererId, editedMeshId;
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(originalSkin.sharedMesh,
                        out originalGuid, out originalMeshId) ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(originalSkin,
                        out rendererGuid, out rendererId) ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(edited.sharedMesh,
                        out editedGuid, out editedMeshId) ||
                    originalGuid != info.source_model_guid || rendererGuid != info.prefab_guid)
                    throw new InvalidOperationException("MESH_ID_INVALID");
                SkinInfo row = null;
                foreach (SkinInfo candidate in info.skins)
                    if (candidate.renderer_file_id == Id(rendererId) &&
                        candidate.source_mesh_file_id == Id(originalMeshId)) row = candidate;
                if (row == null || !matchedRows.Add(row.renderer_file_id))
                    throw new InvalidOperationException("SOURCE_RENDERER_MISMATCH");
                Task task = null;
                foreach (Task candidate in tasks)
                    if (candidate.model_guid == editedGuid) task = candidate;
                if (task == null || !editedGuids.Add(editedGuid) ||
                    Hash(Disk(AssetDatabase.GUIDToAssetPath(editedGuid))) != task.model_sha256 ||
                    !CandidateIncludes(task, row))
                    throw new InvalidOperationException("EDITED_MODEL_MISMATCH");
                GameObject editedModel = AssetDatabase.LoadAssetAtPath<GameObject>(
                    AssetDatabase.GUIDToAssetPath(editedGuid));
                bool foundInEditedModel = false;
                if (editedModel != null)
                    foreach (SkinnedMeshRenderer editedSource in
                        editedModel.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                        if (editedSource.sharedMesh == edited.sharedMesh) foundInEditedModel = true;
                report.geometry_matches_edited_models &= foundInEditedModel;
                Vector3[] before = originalVertices[row.source_mesh_file_id];
                Vector3[] after = edited.sharedMesh.vertices;
                float extent = originalSkin.sharedMesh.bounds.extents.magnitude;
                float threshold = Mathf.Max(0.0000001f, extent * 0.000001f);
                report.both_geometry_changed &= DifferentVertices(before, after, threshold);
                report.selected_skin_count++;
                if (edited.rootBone == null ||
                    PrefabUtility.GetCorrespondingObjectFromSource(edited.rootBone) != originalSkin.rootBone ||
                    edited.bones.Length != originalSkin.bones.Length || edited.bones.Length != row.bones.Length)
                    report.bones_and_materials_preserved = false;
                else for (int i = 0; i < edited.bones.Length; i++)
                    if (PrefabUtility.GetCorrespondingObjectFromSource(edited.bones[i]) != originalSkin.bones[i])
                        report.bones_and_materials_preserved = false;
            }
            report.two_exact_edited_skins = report.selected_skin_count == 2 && matchedRows.Count == 2 && editedGuids.Count == 2;
            string firstHash = Hash(Disk(variantPath));
            bool second = VapbModelSkinFinalizer.Apply(ManifestPath);
            report.second_apply_unchanged = second && firstHash == Hash(Disk(variantPath));
            report.original_unchanged &= Hash(Disk(prefabPath)) == info.prefab_source_sha256 &&
                Hash(Disk(sourcePath)) == info.source_model_sha256;
            report.pass = report.imported && report.bad_second_rejected_before_save &&
                report.original_unchanged && report.first_apply && report.one_linked_variant &&
                report.two_exact_edited_skins && report.bones_and_materials_preserved &&
                report.both_geometry_changed && report.geometry_matches_edited_models &&
                report.sibling_state_preserved && report.second_apply_unchanged;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error)
        {
            report.error = error is InvalidOperationException ? error.Message : "UNEXPECTED_EXCEPTION";
        }
        Finish(report);
    }

    private static bool BadSecondTaskRejected(string variantPath)
    {
        string file = Disk(ManifestPath);
        byte[] original = File.ReadAllBytes(file);
        byte[] meta = File.ReadAllBytes(file + ".meta");
        try
        {
            string json = File.ReadAllText(file);
            MatchCollection arrays = Regex.Matches(json, "\\\"renderer_candidates\\\"\\s*:\\s*\\[");
            if (arrays.Count != 2) throw new InvalidOperationException("NEGATIVE_SETUP_INVALID");
            int start = arrays[1].Index + arrays[1].Length;
            int end = -1;
            int depth = 1;
            for (int i = start; i < json.Length; i++)
            {
                if (json[i] == '[') depth++;
                if (json[i] == ']' && --depth == 0) { end = i; break; }
            }
            if (end <= start) throw new InvalidOperationException("NEGATIVE_SETUP_INVALID");
            string candidates = json.Substring(start, end - start);
            string damaged = Regex.Replace(candidates, "(\\\"renderer_file_id\\\"\\s*:\\s*\\\")-?[0-9]+(\\\")", "${1}0${2}");
            if (damaged == candidates) throw new InvalidOperationException("NEGATIVE_SETUP_INVALID");
            File.WriteAllText(file, json.Substring(0, start) + damaged + json.Substring(end));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            bool rejected = !VapbModelSkinFinalizer.Apply(ManifestPath);
            return rejected && AssetDatabase.LoadAssetAtPath<GameObject>(variantPath) == null &&
                !File.Exists(Disk(variantPath));
        }
        finally
        {
            File.WriteAllBytes(file, original);
            File.WriteAllBytes(file + ".meta", meta);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }
    }
    private static bool CandidateIncludes(Task task, SkinInfo row)
    {
        if (task.renderer_candidates == null) return false;
        foreach (Candidate candidate in task.renderer_candidates)
            if (candidate.renderer_file_id == row.renderer_file_id &&
                candidate.source_mesh_file_id == row.source_mesh_file_id) return true;
        return false;
    }
    private static Dictionary<string, Vector3[]> ReadSourceVertices(string sourcePath, SourceInfo info)
    {
        byte[] meta = File.ReadAllBytes(Disk(sourcePath) + ".meta");
        try
        {
            ModelImporter importer = AssetImporter.GetAtPath(sourcePath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("SOURCE_IMPORTER_MISSING");
            if (!importer.isReadable)
            {
                importer.isReadable = true;
                importer.SaveAndReimport();
            }
            var result = new Dictionary<string, Vector3[]>();
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(sourcePath))
            {
                Mesh mesh = asset as Mesh;
                if (mesh == null) continue;
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long id) ||
                    guid != info.source_model_guid) continue;
                foreach (SkinInfo row in info.skins)
                    if (row.source_mesh_file_id == Id(id) && !result.ContainsKey(row.source_mesh_file_id))
                        result.Add(row.source_mesh_file_id, mesh.vertices);
            }
            if (result.Count != 2) throw new InvalidOperationException("SOURCE_MESH_MISSING");
            return result;
        }
        finally
        {
            File.WriteAllBytes(Disk(sourcePath) + ".meta", meta);
            AssetDatabase.ImportAsset(sourcePath,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            byte[] restored = File.ReadAllBytes(Disk(sourcePath) + ".meta");
            if (restored.Length != meta.Length) throw new InvalidOperationException("SOURCE_META_DRIFT");
            for (int i = 0; i < restored.Length; i++)
                if (restored[i] != meta[i]) throw new InvalidOperationException("SOURCE_META_DRIFT");
        }
    }
    private static bool DifferentVertices(Vector3[] before, Vector3[] after, float threshold)
    {
        if (before == null || after == null || before.Length != after.Length || before.Length == 0)
            return false;
        float max = 0;
        for (int i = 0; i < before.Length; i++)
            max = Mathf.Max(max, (before[i] - after[i]).magnitude);
        return max > threshold;
    }
    private static bool SameMaterials(Material[] left, Material[] right)
    {
        if (left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static string Id(long value) { return value.ToString(CultureInfo.InvariantCulture); }
    private static string Hash(string file)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(file))).Replace("-", "").ToLowerInvariant();
    }
    private static string Disk(string path)
    { return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string ProjectFile(string name)
    { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }
    private static void Finish(Report report)
    {
        SessionState.SetString(Phase, "");
        try { File.WriteAllText(ProjectFile("VapbMultiSkinRoundtripResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_MULTI_SKIN_PASS" : "VAPB_MULTI_SKIN_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
