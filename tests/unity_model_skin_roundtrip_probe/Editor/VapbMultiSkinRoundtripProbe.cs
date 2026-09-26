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
    [Serializable] private sealed class ExpectedBindings
    {
        public string prefab_guid, prefab_source_sha256, source_model_guid, source_model_sha256;
        public ExpectedRow[] rows;
    }
    [Serializable] private sealed class ExpectedRow
    { public string realization_id, model_guid, renderer_file_id, source_mesh_file_id; }
    private sealed class RendererState
    {
        public string rendererId, meshGuid, meshId, meshFileHash, rootId;
        public string[] boneIds, materialIds;
        public bool enabled;
    }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool imported, bad_second_rejected_before_save, original_unchanged;
        public bool first_apply, one_linked_variant, two_exact_edited_skins;
        public bool both_geometry_changed, geometry_matches_edited_models;
        public bool bones_and_materials_preserved, sibling_state_preserved;
        public bool all_renderer_ids_once, untouched_siblings_preserved, no_unexpected_overrides;
        public bool external_expectations_used, task_specific_source_pairs_proven, swapped_expectations_rejected;
        public bool second_apply_unchanged;
        public int selected_skin_count, original_renderer_count, untouched_sibling_count;
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
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
            if (manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 2)
                throw new InvalidOperationException("SOURCE_OR_TASK_INVALID");
            Task[] tasks = manifest.reference_rebind_tasks;
            string infoPath = ProjectFile("MultiSkinSourceInfo.json");
            bool generatedInfo = !File.Exists(infoPath);
            SourceInfo info = File.Exists(infoPath) ?
                JsonUtility.FromJson<SourceInfo>(File.ReadAllText(infoPath)) :
                GenerateSourceInfo(tasks, infoPath);
            if (info == null || info.skins == null || info.skins.Length < 2)
                throw new InvalidOperationException("SOURCE_OR_TASK_INVALID");
            if (tasks[0].kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" ||
                tasks[1].kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" ||
                tasks[0].variant_path != tasks[1].variant_path ||
                tasks[0].prefab_guid != info.prefab_guid || tasks[1].prefab_guid != info.prefab_guid ||
                tasks[0].source_model_guid != info.source_model_guid ||
                tasks[1].source_model_guid != info.source_model_guid ||
                tasks[0].model_guid == tasks[1].model_guid ||
                tasks[0].realization_id == tasks[1].realization_id)
                throw new InvalidOperationException("TASK_IDENTITY_INVALID");
            string expectedPath = ProjectFile("ExpectedMultiSkinBindings.json");
            bool expectedFileExists = File.Exists(expectedPath);
            if ((generatedInfo || info.skins.Length != 2) && !expectedFileExists)
                throw new InvalidOperationException("EXPECTED_BINDINGS_MISSING");
            ExpectedBindings expected = expectedFileExists ?
                JsonUtility.FromJson<ExpectedBindings>(File.ReadAllText(expectedPath)) : null;
            if (expectedFileExists && expected == null)
                throw new InvalidOperationException("EXPECTED_BINDINGS_INVALID");
            report.external_expectations_used = expected != null;
            if (expected != null && !ValidExpectedBindings(expected, tasks, info))
                throw new InvalidOperationException("EXPECTED_BINDINGS_INVALID");
            string variantPath = tasks[0].variant_path;
            string prefabPath = AssetDatabase.GUIDToAssetPath(info.prefab_guid);
            string sourcePath = AssetDatabase.GUIDToAssetPath(info.source_model_guid);
            GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (source == null || sourcePath == "" || AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath) == null)
                throw new InvalidOperationException("SOURCE_MISSING");
            report.imported = true;
            report.original_renderer_count = source.GetComponentsInChildren<Renderer>(true).Length;
            if (report.original_renderer_count > 2 && expected == null)
                throw new InvalidOperationException("EXPECTED_BINDINGS_MISSING");
            Dictionary<string, RendererState> baseline = CaptureRenderers(source);
            if (baseline.Count != report.original_renderer_count)
                throw new InvalidOperationException("SOURCE_RENDERER_UNSUPPORTED");
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
            var seenRenderers = new HashSet<string>();
            var observedPairs = new Dictionary<string, SkinInfo>();
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
            report.untouched_siblings_preserved = true;
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
                    rendererGuid != info.prefab_guid)
                    throw new InvalidOperationException("MESH_ID_INVALID");
                string rendererKey = Key(rendererGuid, rendererId);
                if (!baseline.TryGetValue(rendererKey, out RendererState baselineRow) ||
                    !seenRenderers.Add(rendererKey) || baselineRow.meshGuid != originalGuid ||
                    baselineRow.meshId != Id(originalMeshId) ||
                    !SameStringArrays(baselineRow.materialIds, MaterialIds(edited.sharedMaterials)) ||
                    baselineRow.enabled != edited.enabled)
                    throw new InvalidOperationException("RENDERER_BASELINE_MISMATCH");
                bool bonesPreserved = baselineRow.rootId == CorrespondingId(edited.rootBone) &&
                    SameStringArrays(baselineRow.boneIds, CorrespondingBoneIds(edited.bones));
                Task task = null;
                foreach (Task candidate in tasks)
                    if (candidate.model_guid == editedGuid) task = candidate;
                if (task == null)
                {
                    report.untouched_sibling_count++;
                    report.untouched_siblings_preserved &= editedGuid == baselineRow.meshGuid &&
                        Id(editedMeshId) == baselineRow.meshId && bonesPreserved &&
                        Hash(Disk(AssetDatabase.GUIDToAssetPath(baselineRow.meshGuid))) == baselineRow.meshFileHash;
                    continue;
                }
                if (originalGuid != info.source_model_guid || rendererGuid != info.prefab_guid || !bonesPreserved)
                    report.bones_and_materials_preserved = false;
                SkinInfo row = null;
                foreach (SkinInfo candidate in info.skins)
                    if (candidate.renderer_file_id == Id(rendererId) &&
                        candidate.source_mesh_file_id == Id(originalMeshId)) row = candidate;
                if (row == null || !matchedRows.Add(row.renderer_file_id))
                    throw new InvalidOperationException("SOURCE_RENDERER_MISMATCH");
                if (observedPairs.ContainsKey(task.realization_id))
                    throw new InvalidOperationException("TASK_PAIR_DUPLICATE");
                observedPairs.Add(task.realization_id, row);
                if (expected != null && !MatchesExpected(FindExpected(expected, task), row))
                    throw new InvalidOperationException("TASK_EXPECTED_PAIR_MISMATCH");
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
                if (edited.bones.Length != row.bones.Length)
                    report.bones_and_materials_preserved = false;
            }
            report.all_renderer_ids_once = seenRenderers.Count == baseline.Count;
            report.task_specific_source_pairs_proven = expected != null &&
                observedPairs.Count == 2 &&
                MatchesExpected(expected.rows[0], observedPairs[expected.rows[0].realization_id]) &&
                MatchesExpected(expected.rows[1], observedPairs[expected.rows[1].realization_id]);
            report.swapped_expectations_rejected = expected != null && observedPairs.Count == 2 &&
                !MatchesExpected(expected.rows[0], observedPairs[expected.rows[1].realization_id]) &&
                !MatchesExpected(expected.rows[1], observedPairs[expected.rows[0].realization_id]);
            report.no_unexpected_overrides = OnlyExpectedOverrides(variant, source, matchedRows, info.prefab_guid);
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
                report.sibling_state_preserved && report.all_renderer_ids_once &&
                report.untouched_siblings_preserved && report.no_unexpected_overrides &&
                (expected == null || (report.task_specific_source_pairs_proven && report.swapped_expectations_rejected)) &&
                report.untouched_sibling_count == report.original_renderer_count - 2 &&
                report.second_apply_unchanged;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error)
        {
            report.error = error is InvalidOperationException &&
                Regex.IsMatch(error.Message, "^[A-Z_]+$") ? error.Message : "UNEXPECTED_EXCEPTION";
        }
        Finish(report);
    }

    private static SourceInfo GenerateSourceInfo(Task[] tasks, string path)
    {
        if (tasks[0].prefab_guid != tasks[1].prefab_guid ||
            tasks[0].source_model_guid != tasks[1].source_model_guid ||
            tasks[0].prefab_source_sha256 != tasks[1].prefab_source_sha256 ||
            tasks[0].source_model_sha256 != tasks[1].source_model_sha256)
            throw new InvalidOperationException("SOURCE_SCOPE_INVALID");
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
            AssetDatabase.GUIDToAssetPath(tasks[0].prefab_guid));
        if (prefab == null) throw new InvalidOperationException("SOURCE_MISSING");
        var rows = new List<SkinInfo>();
        foreach (SkinnedMeshRenderer skin in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (skin.sharedMesh == null ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.sharedMesh,
                    out string meshGuid, out long meshId) ||
                meshGuid != tasks[0].source_model_guid) continue;
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin,
                    out string rendererGuid, out long rendererId) ||
                rendererGuid != tasks[0].prefab_guid || skin.rootBone == null)
                throw new InvalidOperationException("SOURCE_RENDERER_UNSUPPORTED");
            var row = new SkinInfo { renderer_file_id = Id(rendererId),
                source_mesh_file_id = Id(meshId),
                root_bone_target_transform_file_id = ObjectId(skin.rootBone),
                bones = new BoneInfo[skin.bones.Length] };
            for (int i = 0; i < skin.bones.Length; i++)
                row.bones[i] = new BoneInfo { target_transform_file_id = ObjectId(skin.bones[i]) };
            rows.Add(row);
        }
        if (rows.Count < 2) throw new InvalidOperationException("SOURCE_SKINS_MISSING");
        var info = new SourceInfo { prefab_guid = tasks[0].prefab_guid,
            prefab_source_sha256 = tasks[0].prefab_source_sha256,
            source_model_guid = tasks[0].source_model_guid,
            source_model_sha256 = tasks[0].source_model_sha256, skins = rows.ToArray() };
        File.WriteAllText(path, JsonUtility.ToJson(info, true));
        return info;
    }

    private static Dictionary<string, RendererState> CaptureRenderers(GameObject prefab)
    {
        var result = new Dictionary<string, RendererState>(StringComparer.Ordinal);
        var meshHashes = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (Renderer renderer in prefab.GetComponentsInChildren<Renderer>(true))
        {
            SkinnedMeshRenderer skin = renderer as SkinnedMeshRenderer;
            if (skin == null || skin.sharedMesh == null || skin.rootBone == null || skin.bones == null)
                throw new InvalidOperationException("SOURCE_RENDERER_UNSUPPORTED");
            string meshPath = AssetDatabase.GetAssetPath(skin.sharedMesh);
            if (String.IsNullOrEmpty(meshPath) || !meshPath.StartsWith("Assets/", StringComparison.Ordinal))
                throw new InvalidOperationException("SOURCE_MESH_UNSUPPORTED");
            if (!meshHashes.TryGetValue(meshPath, out string fileHash))
            {
                fileHash = Hash(Disk(meshPath));
                meshHashes.Add(meshPath, fileHash);
            }
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin,
                    out string rendererGuid, out long rendererId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.sharedMesh,
                    out string meshGuid, out long meshId))
                throw new InvalidOperationException("SOURCE_ID_UNAVAILABLE");
            var row = new RendererState { rendererId = Key(rendererGuid, rendererId),
                meshGuid = meshGuid, meshId = Id(meshId), meshFileHash = fileHash,
                rootId = ObjectKey(skin.rootBone), boneIds = new string[skin.bones.Length],
                materialIds = MaterialIds(skin.sharedMaterials), enabled = skin.enabled };
            for (int i = 0; i < skin.bones.Length; i++) row.boneIds[i] = ObjectKey(skin.bones[i]);
            if (result.ContainsKey(row.rendererId))
                throw new InvalidOperationException("SOURCE_RENDERER_AMBIGUOUS");
            result.Add(row.rendererId, row);
        }
        return result;
    }

    private static bool OnlyExpectedOverrides(GameObject variant, GameObject source,
        HashSet<string> selectedRendererIds, string prefabGuid)
    {
        if (PrefabUtility.GetAddedComponents(variant).Count != 0 ||
            PrefabUtility.GetRemovedComponents(variant).Count != 0 ||
            PrefabUtility.GetAddedGameObjects(variant).Count != 0 ||
            PrefabUtility.GetRemovedGameObjects(variant).Count != 0) return false;
        PropertyModification[] modifications = PrefabUtility.GetPropertyModifications(variant);
        if (modifications == null) return false;
        foreach (PropertyModification mod in modifications)
        {
            if (mod == null || mod.target == null || String.IsNullOrEmpty(mod.propertyPath)) return false;
            bool selectedBinding = mod.target is SkinnedMeshRenderer skin &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin,
                    out string guid, out long id) && guid == prefabGuid &&
                selectedRendererIds.Contains(Id(id)) &&
                (mod.propertyPath == "m_Mesh" || mod.propertyPath == "m_Bones.Array.size" ||
                 mod.propertyPath.StartsWith("m_Bones.Array.data[", StringComparison.Ordinal));
            bool rootDefault = PrefabUtility.IsDefaultOverride(mod) &&
                (mod.target == source || mod.target == source.transform);
            if (!selectedBinding && !rootDefault) return false;
        }
        return true;
    }

    private static string ObjectKey(UnityEngine.Object value)
    {
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value,
                out string guid, out long id) || id == 0)
            throw new InvalidOperationException("SOURCE_ID_UNAVAILABLE");
        return Key(guid, id);
    }
    private static string ObjectId(UnityEngine.Object value)
    {
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value,
                out string guid, out long id) || id == 0)
            throw new InvalidOperationException("SOURCE_ID_UNAVAILABLE");
        return Id(id);
    }
    private static string CorrespondingId(Transform value)
    {
        Transform source = value == null ? null :
            PrefabUtility.GetCorrespondingObjectFromSource(value) as Transform;
        return source == null ? "" : ObjectKey(source);
    }
    private static string[] CorrespondingBoneIds(Transform[] bones)
    {
        if (bones == null) return new string[0];
        var result = new string[bones.Length];
        for (int i = 0; i < bones.Length; i++) result[i] = CorrespondingId(bones[i]);
        return result;
    }
    private static string[] MaterialIds(Material[] materials)
    {
        var result = new string[materials.Length];
        for (int i = 0; i < materials.Length; i++)
            result[i] = materials[i] == null ? "null" : ObjectKey(materials[i]);
        return result;
    }
    private static bool SameStringArrays(string[] left, string[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static string Key(string guid, long id) { return guid + ":" + Id(id); }

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
    private static ExpectedRow FindExpected(ExpectedBindings expected, Task task)
    {
        foreach (ExpectedRow row in expected.rows)
            if (row.realization_id == task.realization_id && row.model_guid == task.model_guid)
                return row;
        return null;
    }
    private static bool MatchesExpected(ExpectedRow expected, SkinInfo observed)
    {
        return expected != null && observed != null &&
            expected.renderer_file_id == observed.renderer_file_id &&
            expected.source_mesh_file_id == observed.source_mesh_file_id;
    }
    private static bool ValidExpectedBindings(ExpectedBindings expected, Task[] tasks, SourceInfo info)
    {
        if (expected == null || expected.rows == null || expected.rows.Length != 2 ||
            expected.prefab_guid != info.prefab_guid ||
            expected.prefab_source_sha256 != info.prefab_source_sha256 ||
            expected.source_model_guid != info.source_model_guid ||
            expected.source_model_sha256 != info.source_model_sha256 ||
            expected.rows[0] == null || expected.rows[1] == null ||
            expected.rows[0].realization_id == expected.rows[1].realization_id ||
            expected.rows[0].model_guid == expected.rows[1].model_guid ||
            expected.rows[0].renderer_file_id == expected.rows[1].renderer_file_id)
            return false;
        foreach (Task task in tasks)
        {
            ExpectedRow row = FindExpected(expected, task);
            if (row == null) return false;
            bool inSource = false;
            foreach (SkinInfo sourceRow in info.skins)
                if (MatchesExpected(row, sourceRow)) inSource = true;
            if (!inSource || !CandidateIncludes(task, new SkinInfo {
                    renderer_file_id = row.renderer_file_id,
                    source_mesh_file_id = row.source_mesh_file_id })) return false;
        }
        return true;
    }
    private static Dictionary<string, Vector3[]> ReadSourceVertices(string sourcePath, SourceInfo info)
    {
        byte[] meta = File.ReadAllBytes(Disk(sourcePath) + ".meta");
        try
        {
            var wanted = new HashSet<string>(StringComparer.Ordinal);
            foreach (SkinInfo row in info.skins) wanted.Add(row.source_mesh_file_id);
            if (wanted.Count < 2) throw new InvalidOperationException("SOURCE_MESH_MISSING");
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
                if (wanted.Contains(Id(id)) && !result.ContainsKey(Id(id)))
                    result.Add(Id(id), mesh.vertices);
            }
            if (result.Count != wanted.Count) throw new InvalidOperationException("SOURCE_MESH_MISSING");
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
