using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Fresh-project package import and bounded model-instance variant acceptance check.
[InitializeOnLoad]
public static class VapbModelSkinRoundtripProbe
{
    private const string Phase = "VAPB_MODEL_SKIN_ROUNDTRIP_PHASE";
    private const string Started = "VAPB_MODEL_SKIN_ROUNDTRIP_STARTED";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string prefab_guid;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string model_guid;
        public string model_sha256;
        public string variant_path;
        public RendererCandidate[] renderer_candidates;
        public MaterialBinding[] material_bindings;
    }
    [Serializable] private sealed class MaterialBinding { public string guid, file_id; }
    [Serializable] private sealed class RendererCandidate
    {
        public string renderer_file_id;
        public string source_mesh_file_id;
        public string[] bone_transform_file_ids;
    }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool package_imported;
        public bool first_apply;
        public bool variant_created;
        public bool variant_linked;
        public bool edited_mesh_bound;
        public bool originals_unchanged;
        public bool second_apply;
        public bool second_apply_unchanged;
        public bool geometry_changed;
        public bool vertex_layout_changed;
        public bool geometry_matches_edited_model;
        public bool topology_and_weights_valid;
        public bool target_bones_and_root_preserved;
        public bool materials_preserved;
        public bool siblings_preserved;
        public bool extra_component_rejected;
        public bool rejected_variant_unchanged;
        public bool variant_restored_after_negative;
        public bool bad_candidate_rejected;
        public bool bad_candidate_unchanged;
        public bool manifest_restored_after_negative;
        public int selected_skin_count;
        public int sibling_renderer_count;
        public int edited_vertex_count;
        public int edited_bone_count;
        public float max_vertex_delta;
        public float source_bounds_extent;
        public float edited_bounds_extent;
        public float vertex_change_threshold;
        public bool native_geometry_125, native_weights_equal, native_bounds_contain_rest;
        public bool native_geometry_expected_scale;
        public float expected_native_scale;
        public string edited_mesh_guid, edited_mesh_file_id;
        public bool native_material_identity, native_face_membership;
        public string[] material_guid_file_ids;
        public int triangle_count, null_texture_reference_count;
        public Bounds returned_local_bounds;
    }

    static VapbModelSkinRoundtripProbe()
    {
        AssetDatabase.importPackageCompleted += OnComplete;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        EditorApplication.update += Timeout;
        if (SessionState.GetString(Phase, "") == "completed") EditorApplication.delayCall += ValidateImported;
        if (SessionState.GetString(Phase, "") == "assistant") EditorApplication.delayCall += RunAssistant;

    }
    [Serializable] private sealed class AssistantReport
    {
        public bool pass, automatic_window_observed, manual_entry_requested, japanese_title, preflight_ready,
            preflight_assets_unchanged, cancel_assets_unchanged, cancel_recorded,
            manual_menu_reopened, retry_ready, output_created, output_selected,
            applied_recorded, restart_no_prompt, restart_assets_unchanged;
        public string error, action_transport = "Unity Editor API invokes the same UI handlers; no human clicks", identity;
    }
    private static AssistantReport assistantReport;
    private static bool assistantManualOpened;
    private static double assistantStarted;
    private static int assistantStage;
    private static Dictionary<string, string> assistantAssets;
    private const System.Reflection.BindingFlags AssistantFlags =
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
    [MenuItem("Tools/VAPB/Observe Assistant (API probe)")]
    public static void RunAssistant()
    {
        if (Application.isBatchMode) throw new InvalidOperationException("ASSISTANT_REQUIRES_NORMAL_EDITOR");
        SessionState.SetBool("VAPB_ASSISTANT_OBSERVER_STARTED", true);
        EditorApplication.update -= ObserveAssistant;
        Debug.Log("VAPB_ASSISTANT_OBSERVER_START");
        assistantManualOpened = false;
        assistantReport = new AssistantReport(); assistantStarted = EditorApplication.timeSinceStartup;
        assistantStage = Array.IndexOf(Environment.GetCommandLineArgs(), "-vapbAssistantRestart") >= 0 ? 10 : 0;
        assistantReport.manual_entry_requested = Array.IndexOf(Environment.GetCommandLineArgs(), "-vapbAssistantManual") >= 0;

        SessionState.SetString(Phase, "assistant");
        assistantAssets = AssistantAssetSnapshot();
        EditorApplication.update += ObserveAssistant;
    }
    private static EditorWindow AssistantWindow()
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type type = assembly.GetType("VapbImportAssistant");
            if (type == null) continue;
            UnityEngine.Object[] windows = Resources.FindObjectsOfTypeAll(type);
            if (windows.Length > 1) throw new InvalidOperationException("ASSISTANT_WINDOW_DUPLICATED");
            return windows.Length == 0 ? null : windows[0] as EditorWindow;
        }
        return null;
    }
    private static object AssistantEntry(EditorWindow window)
    {
        var entries = window.GetType().GetField("entries", AssistantFlags).GetValue(window) as System.Collections.IList;
        foreach (object entry in entries)
            if ((string)entry.GetType().GetField("path").GetValue(entry) == ManifestPath) return entry;
        throw new InvalidOperationException("ASSISTANT_ENTRY_MISSING");
    }
    private static bool AssistantReady(object entry)
    { return entry.GetType().GetField("error").GetValue(entry) == null && entry.GetType().GetField("inspection").GetValue(entry) != null; }
    private static Dictionary<string, string> AssistantAssetSnapshot()
    {
        var files = new Dictionary<string, string>();
        foreach (string path in Directory.GetFiles(Application.dataPath, "*", SearchOption.AllDirectories)) files[path] = Hash(path);
        return files;
    }
    private static bool AssistantAssetsSame(Dictionary<string, string> before)
    {
        var after = AssistantAssetSnapshot(); if (after.Count != before.Count) return false;
        foreach (var pair in before) if (!after.TryGetValue(pair.Key, out string hash) || hash != pair.Value) return false;
        return true;
    }
    private static bool AssistantState(string identity, string state)
    {
        string file = ProjectFile("Library/VapbApplyAssistant.state");
        return File.Exists(file) && Array.IndexOf(File.ReadAllLines(file), identity + " " + state) >= 0;
    }
    private static void ObserveAssistant()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating ||
            EditorApplication.timeSinceStartup - assistantStarted < 2) return;
        try
        {
            if (EditorApplication.timeSinceStartup - assistantStarted > 120) throw new InvalidOperationException("ASSISTANT_TIMEOUT");
            // CLI executeMethod may precede editor initialization. Request the
            // existing menu once, after the same stable update used for observation.
            if (assistantStage == 0 && assistantReport.manual_entry_requested && !assistantManualOpened)
            {
                assistantManualOpened = true;
                EditorApplication.ExecuteMenuItem("Tools/VAPB/編集内容を確認");
                return;
            }
            EditorWindow window = AssistantWindow();
            if (assistantStage == 10)
            {
                if (EditorApplication.timeSinceStartup - assistantStarted < 8) return;
                assistantReport.restart_no_prompt = window == null;
                assistantReport.restart_assets_unchanged = AssistantAssetsSame(assistantAssets);
                assistantReport.pass = assistantReport.restart_no_prompt && assistantReport.restart_assets_unchanged;
                FinishAssistant(true); return;
            }
            if (window == null)
            {
                if (EditorApplication.timeSinceStartup - assistantStarted > 8) throw new InvalidOperationException("ASSISTANT_AUTOMATIC_WINDOW_MISSING");
                return;
            }
            object entry = AssistantEntry(window);
            if (assistantStage == 0)
            {
                assistantReport.automatic_window_observed = !assistantReport.manual_entry_requested;
                assistantReport.japanese_title = window.titleContent.text == "VAPB：編集内容を確認";
                assistantReport.preflight_ready = AssistantReady(entry);
                if (!assistantReport.preflight_ready) throw new InvalidOperationException("ASSISTANT_PREFLIGHT_REJECTED:" + entry.GetType().GetField("error").GetValue(entry));
                var snapshot = AssistantAssetSnapshot();
                window.GetType().GetMethod("RefreshEntry", AssistantFlags).Invoke(window, new[] { entry });
                assistantReport.preflight_assets_unchanged = AssistantAssetsSame(snapshot);
                assistantReport.identity = (string)entry.GetType().GetField("identity").GetValue(entry);
                window.GetType().GetMethod("CancelEntry", AssistantFlags).Invoke(window, new[] { entry });
                assistantReport.cancel_assets_unchanged = AssistantAssetsSame(snapshot);
                assistantReport.cancel_recorded = AssistantState(assistantReport.identity, "cancelled");
                Selection.activeObject = null;
                assistantReport.manual_menu_reopened = EditorApplication.ExecuteMenuItem("Tools/VAPB/編集内容を確認");
                assistantStage = 1; return;
            }
            if (assistantStage == 1)
            {
                window.GetType().GetMethod("RefreshEntry", AssistantFlags).Invoke(window, new[] { entry });
                assistantReport.retry_ready = AssistantReady(entry);
                if (!assistantReport.retry_ready) throw new InvalidOperationException("ASSISTANT_RETRY_REJECTED");
                object view = entry.GetType().GetField("inspection").GetValue(entry);
                string output = (string)view.GetType().GetField("output").GetValue(view);
                window.GetType().GetMethod("ApplyEntry", AssistantFlags).Invoke(window, new[] { entry });
                assistantReport.output_created = AssetDatabase.LoadAssetAtPath<GameObject>(output) != null;
                assistantReport.output_selected = AssetDatabase.GetAssetPath(Selection.activeObject) == output;
                assistantReport.applied_recorded = AssistantState(assistantReport.identity, "applied");
                window.Close();
                assistantReport.pass = (assistantReport.automatic_window_observed || assistantReport.manual_entry_requested) && assistantReport.japanese_title &&
                    assistantReport.preflight_ready && assistantReport.preflight_assets_unchanged &&
                    assistantReport.cancel_assets_unchanged && assistantReport.cancel_recorded && assistantReport.manual_menu_reopened &&
                    assistantReport.retry_ready && assistantReport.output_created && assistantReport.output_selected && assistantReport.applied_recorded;
                FinishAssistant(false);
            }
        }
        catch (Exception error)
        {
            assistantReport.error = error.InnerException != null ? error.InnerException.Message : error.Message;
            assistantReport.pass = false; FinishAssistant(true);
        }
    }
    private static void FinishAssistant(bool exit)
    {
        EditorApplication.update -= ObserveAssistant;
        File.WriteAllText(ProjectFile(assistantStage == 10 ? "VapbAssistantRestartResult.json" : "VapbAssistantResult.json"), JsonUtility.ToJson(assistantReport, true));
        SessionState.SetString(Phase, "");
        if (exit || !assistantReport.pass) EditorApplication.Exit(assistantReport.pass ? 0 : 1);
        else RunImported(); // Existing geometry/reference acceptance; no parallel runner.
    }

    public static void Validate()
    {
        try
        {
            string package = ProjectFile("Output.unitypackage");
            if (File.Exists(ProjectFile("NativeSkinOutput.unitypackage"))) {
                package = ProjectFile("NativeSkinOutput.unitypackage");
                if (Hash(package) != "d99efbad6090258e910a7b838ab42ab25c66391f25fa06ab19473a799d29a545") throw new InvalidOperationException("PACKAGE_HASH_MISMATCH");
            }
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
        string phase = SessionState.GetString(Phase, "");
        if (phase != "completed" && phase != "") return;
        SessionState.SetString(Phase, "validating");
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        try
        {
            TextAsset manifestAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath);
            report.package_imported = manifestAsset != null;
            if (!report.package_imported) throw new InvalidOperationException("MANIFEST_MISSING");
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
            if (manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 1 ||
                (manifest.reference_rebind_tasks[0].kind != "RESTORE_MODEL_SKIN_VARIANT_V1" &&
                 manifest.reference_rebind_tasks[0].kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" &&
                 manifest.reference_rebind_tasks[0].kind != "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1"))
                throw new InvalidOperationException("TASK_MISSING");
            Task task = manifest.reference_rebind_tasks[0];
            bool native = task.kind == "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1";
            string prefabPath = AssetDatabase.GUIDToAssetPath(native ? task.source_model_guid : task.prefab_guid);
            string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
            string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            report.first_apply = VapbModelSkinFinalizer.Apply(ManifestPath);
            if (!report.first_apply) throw new InvalidOperationException("FIRST_APPLY_FAILED");
            GameObject variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
            GameObject original = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            report.variant_created = variant != null && PrefabUtility.GetPrefabAssetType(variant) == PrefabAssetType.Variant;
            report.variant_linked = report.variant_created &&
                PrefabUtility.GetCorrespondingObjectFromSource(variant) == original;
            GameObject editedModel = AssetDatabase.LoadAssetAtPath<GameObject>(editedPath);
            report.edited_mesh_bound = false;
            SkinnedMeshRenderer selected = null;
            if (variant != null && editedModel != null)
            {
                foreach (SkinnedMeshRenderer skin in variant.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (skin.sharedMesh != null && AssetDatabase.GetAssetPath(skin.sharedMesh) == editedPath)
                    {
                        report.edited_mesh_bound = true;
                        report.selected_skin_count++;
                        selected = skin;
                    }
            }
            if (report.selected_skin_count != 1) throw new InvalidOperationException("SELECTED_SKIN_INVALID");
            SkinnedMeshRenderer originalSkin = PrefabUtility.GetCorrespondingObjectFromSource(selected) as SkinnedMeshRenderer;
            if (originalSkin == null || originalSkin.sharedMesh == null)
                throw new InvalidOperationException("SOURCE_SKIN_INVALID");
            Mesh editedMesh = selected.sharedMesh;
            string meshGuid;
            long sourceMeshId;
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(originalSkin.sharedMesh, out meshGuid,
                out sourceMeshId) || meshGuid != task.source_model_guid || sourceMeshId == 0)
                throw new InvalidOperationException("SOURCE_MESH_ID_INVALID");
            Vector3[] sourceVertices = ReadSourceVertices(sourcePath, task.source_model_guid,
                sourceMeshId, out report.source_bounds_extent, out int[][] sourceIndices);
            variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
            original = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            selected = FindEditedSkin(variant, editedPath);
            originalSkin = PrefabUtility.GetCorrespondingObjectFromSource(selected) as SkinnedMeshRenderer;
            editedMesh = selected.sharedMesh;
            Vector3[] editedVertices = editedMesh.vertices;
            report.edited_vertex_count = editedVertices.Length;
            report.edited_bone_count = selected.bones.Length;
            report.edited_bounds_extent = editedMesh.bounds.extents.magnitude;
            report.geometry_matches_edited_model = ModelContainsMesh(editedModel, editedMesh);
            report.vertex_change_threshold = Mathf.Max(0.0000001f,
                report.source_bounds_extent * 0.000001f);
            report.vertex_layout_changed = sourceVertices.Length != editedVertices.Length;
            report.geometry_changed = DifferentVertices(sourceVertices, editedVertices,
                report.vertex_change_threshold, out report.max_vertex_delta);
            report.topology_and_weights_valid = ValidateMesh(editedMesh, selected.bones.Length);
            report.target_bones_and_root_preserved = BonesPreserved(selected, originalSkin);
            report.materials_preserved = SameMaterials(selected.sharedMaterials, originalSkin.sharedMaterials);
            report.siblings_preserved = SiblingsPreserved(variant, original, selected, ref report.sibling_renderer_count);
            report.originals_unchanged = (native || Hash(Disk(prefabPath)) == task.prefab_source_sha256) &&
                Hash(Disk(sourcePath)) == task.source_model_sha256 &&
                Hash(Disk(editedPath)) == task.model_sha256;
            string firstHash = Hash(Disk(task.variant_path));
            report.second_apply = VapbModelSkinFinalizer.Apply(ManifestPath);
            report.second_apply_unchanged = report.second_apply && firstHash == Hash(Disk(task.variant_path));
            if (native)
            {
                variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
                selected = FindEditedSkin(variant, editedPath);
                originalSkin = PrefabUtility.GetCorrespondingObjectFromSource(selected) as SkinnedMeshRenderer;
                editedMesh = selected.sharedMesh;
                string editedGuid; long editedId;
                bool identity = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(editedMesh, out editedGuid, out editedId);
                report.edited_mesh_guid = editedGuid; report.edited_mesh_file_id = editedId.ToString();
                report.expected_native_scale = Array.IndexOf(Environment.GetCommandLineArgs(), "-vapbNativeUnchanged") >= 0 ? 1f : 1.25f;
                report.native_geometry_expected_scale = sourceVertices.Length == editedVertices.Length;
                for (int i=0; report.native_geometry_expected_scale && i<sourceVertices.Length; i++)
                    report.native_geometry_expected_scale = (editedVertices[i]-sourceVertices[i]*report.expected_native_scale).magnitude <= report.vertex_change_threshold*10;
                report.native_geometry_125 = report.expected_native_scale == 1.25f && report.native_geometry_expected_scale;
                var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
                report.native_weights_equal = (bool)typeof(VapbModelSkinFinalizer).GetMethod("SameSkinInfluences", flags).Invoke(null, new object[] { originalSkin.sharedMesh, editedMesh });
                report.native_material_identity = task.material_bindings != null && task.material_bindings.Length == selected.sharedMaterials.Length;
                var expectedMaterials = new List<string>();
                if(task.material_bindings!=null) foreach(var binding in task.material_bindings) expectedMaterials.Add(binding.guid+":"+binding.file_id);
                report.material_guid_file_ids = new string[selected.sharedMaterials.Length];
                for (int slot=0; slot<selected.sharedMaterials.Length; slot++)
                {
                    Material material = selected.sharedMaterials[slot];
                    string guid; long id;
                    bool known = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out guid, out id);
                    report.material_guid_file_ids[slot]=guid+":"+id.ToString();
                    report.native_material_identity &= known && expectedMaterials.Remove(report.material_guid_file_ids[slot]);
                    foreach(string name in material.GetTexturePropertyNames())
                        if(material.GetTexture(name)==null) report.null_texture_reference_count++;
                }
                report.native_material_identity &= expectedMaterials.Count==0;
                report.native_face_membership=sourceIndices!=null && sourceIndices.Length==editedMesh.subMeshCount && report.materials_preserved;
                for(int sub=0; sub<editedMesh.subMeshCount; sub++)
                {
                    int[] actualIndices=editedMesh.GetIndices(sub);
                    report.triangle_count+=actualIndices.Length/3;
                    if(sourceIndices==null || sub>=sourceIndices.Length || sourceIndices[sub].Length!=actualIndices.Length) { report.native_face_membership=false; continue; }
                    for(int i=0;i<actualIndices.Length;i++) if(actualIndices[i]!=sourceIndices[sub][i]) report.native_face_membership=false;
                }
                report.returned_local_bounds=selected.localBounds;
                report.native_bounds_contain_rest = (bool)typeof(VapbModelSkinFinalizer).GetMethod("BoundsContainsRestMesh", flags).Invoke(null, new object[] { selected, editedMesh, selected.bones, 0.001f });
                report.pass = report.package_imported && report.first_apply && report.variant_created && report.variant_linked &&
                    report.edited_mesh_bound && report.originals_unchanged && report.second_apply_unchanged &&
                    report.geometry_matches_edited_model && report.topology_and_weights_valid && report.target_bones_and_root_preserved &&
                    report.materials_preserved && report.siblings_preserved && report.native_geometry_expected_scale &&
                    report.native_weights_equal && report.native_bounds_contain_rest && report.native_material_identity && report.native_face_membership && identity && editedGuid==task.model_guid && editedGuid!=task.source_model_guid && editedId!=0;
                report.error=report.pass ? "NONE" : "ASSERTION_FAILED";
                Finish(report); return;
            }
            if (task.kind == "RESTORE_DIRECT_SKIN_VARIANT_V1")
                NegativeBadCandidate(task, sourceMeshId, firstHash, report);
            NegativeExtraComponent(task.variant_path, firstHash, report);
            report.pass = report.package_imported && report.first_apply && report.variant_created &&
                report.variant_linked && report.edited_mesh_bound && report.originals_unchanged &&
                report.second_apply && report.second_apply_unchanged &&
                (report.geometry_changed || report.vertex_layout_changed) &&
                report.geometry_matches_edited_model && report.topology_and_weights_valid &&
                report.target_bones_and_root_preserved && report.materials_preserved &&
                report.siblings_preserved && report.extra_component_rejected &&
                report.rejected_variant_unchanged && report.variant_restored_after_negative &&
                (task.kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" ||
                 (report.bad_candidate_rejected && report.bad_candidate_unchanged &&
                  report.manifest_restored_after_negative));
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error)
        {
            report.pass = false;
            report.error = error is InvalidOperationException &&
                (error.Message == "MANIFEST_MISSING" || error.Message == "TASK_MISSING" ||
                 error.Message == "FIRST_APPLY_FAILED" || error.Message == "SELECTED_SKIN_INVALID" ||
                 error.Message == "SOURCE_SKIN_INVALID" || error.Message == "SOURCE_MESH_ID_INVALID" ||
                 error.Message == "SOURCE_IMPORTER_MISSING" || error.Message == "SOURCE_MESH_MISSING" ||
                 error.Message == "SOURCE_META_DRIFT" || error.Message == "SELECTED_SKIN_AMBIGUOUS" ||
                 error.Message == "SELECTED_SKIN_MISSING" || error.Message == "VARIANT_LOAD_FAILED" ||
                 error.Message == "NEGATIVE_SAVE_FAILED" || error.Message == "NEGATIVE_NOT_CHANGED")
                ? error.Message : "UNEXPECTED_EXCEPTION";
        }
        Finish(report);
    }

    private static Vector3[] ReadSourceVertices(string path, string guid, long meshId,
        out float boundsExtent, out int[][] indices)
    {
        boundsExtent = 0; indices = null;
        byte[] meta = File.ReadAllBytes(Disk(path) + ".meta");
        try
        {
            ModelImporter importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("SOURCE_IMPORTER_MISSING");
            if (!importer.isReadable)
            {
                importer.isReadable = true;
                importer.SaveAndReimport();
            }
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
            {
                if (!(asset is Mesh mesh)) continue;
                if (AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string foundGuid, out long foundId) &&
                    foundGuid == guid && foundId == meshId)
                {
                    boundsExtent = mesh.bounds.extents.magnitude;
                    indices = new int[mesh.subMeshCount][];
                    for (int sub=0; sub<indices.Length; sub++) indices[sub]=mesh.GetIndices(sub);
                    return mesh.vertices;
                }
            }
            throw new InvalidOperationException("SOURCE_MESH_MISSING");
        }
        finally
        {
            File.WriteAllBytes(Disk(path) + ".meta", meta);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            if (!EqualBytes(meta, File.ReadAllBytes(Disk(path) + ".meta")))
                throw new InvalidOperationException("SOURCE_META_DRIFT");
        }
    }

    private static SkinnedMeshRenderer FindEditedSkin(GameObject variant, string editedPath)
    {
        SkinnedMeshRenderer result = null;
        foreach (SkinnedMeshRenderer skin in variant.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            if (skin.sharedMesh != null && AssetDatabase.GetAssetPath(skin.sharedMesh) == editedPath)
            {
                if (result != null) throw new InvalidOperationException("SELECTED_SKIN_AMBIGUOUS");
                result = skin;
            }
        if (result == null) throw new InvalidOperationException("SELECTED_SKIN_MISSING");
        return result;
    }

    private static bool ModelContainsMesh(GameObject editedModel, Mesh selected)
    {
        if (editedModel == null || selected == null) return false;
        foreach (SkinnedMeshRenderer skin in editedModel.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            if (skin.sharedMesh == selected) return true;
        return false;
    }

    private static bool DifferentVertices(Vector3[] a, Vector3[] b, float threshold, out float maxDelta)
    {
        maxDelta = 0;
        if (a == null || b == null || a.Length != b.Length || a.Length == 0) return false;
        for (int i = 0; i < a.Length; i++)
            maxDelta = Mathf.Max(maxDelta, (a[i] - b[i]).magnitude);
        return maxDelta > threshold;
    }

    private static bool ValidateMesh(Mesh mesh, int boneCount)
    {
        if (mesh == null || mesh.vertexCount == 0 || boneCount == 0 ||
            mesh.bindposes.Length != boneCount) return false;
        Vector3[] vertices = mesh.vertices;
        if (vertices.Length != mesh.vertexCount) return false;
        foreach (Vector3 vertex in vertices)
            if (!Finite(vertex.x) || !Finite(vertex.y) || !Finite(vertex.z)) return false;
        foreach (Matrix4x4 matrix in mesh.bindposes)
            for (int i = 0; i < 16; i++) if (!Finite(matrix[i])) return false;
        for (int sub = 0; sub < mesh.subMeshCount; sub++)
            foreach (int index in mesh.GetIndices(sub))
                if (index < 0 || index >= mesh.vertexCount) return false;
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            if (counts.Length != vertices.Length) return false;
            int offset = 0;
            for (int vertex = 0; vertex < counts.Length; vertex++)
            {
                int count = counts[vertex];
                if (count == 0 || offset + count > weights.Length) return false;
                float sum = 0;
                for (int i = 0; i < count; i++)
                {
                    var weight = weights[offset + i];
                    if (weight.boneIndex < 0 || weight.boneIndex >= boneCount ||
                        !Finite(weight.weight) || weight.weight <= 0) return false;
                    sum += weight.weight;
                }
                if (Mathf.Abs(sum - 1f) > 0.01f) return false;
                offset += count;
            }
            return offset == weights.Length;
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }

    private static bool BonesPreserved(SkinnedMeshRenderer variant, SkinnedMeshRenderer original)
    {
        if (variant == null || original == null || variant.rootBone == null ||
            PrefabUtility.GetCorrespondingObjectFromSource(variant.rootBone) != original.rootBone ||
            variant.bones.Length != original.bones.Length) return false;
        var sourceBones = new HashSet<Transform>(original.bones);
        foreach (Transform bone in variant.bones)
            if (bone == null || !sourceBones.Remove(PrefabUtility.GetCorrespondingObjectFromSource(bone) as Transform))
                return false;
        return sourceBones.Count == 0;
    }

    private static bool SiblingsPreserved(GameObject variant, GameObject original,
        SkinnedMeshRenderer selected, ref int siblingCount)
    {
        if (variant == null || original == null ||
            variant.GetComponentsInChildren<Transform>(true).Length !=
                original.GetComponentsInChildren<Transform>(true).Length) return false;
        foreach (Transform transform in variant.GetComponentsInChildren<Transform>(true))
        {
            Transform source = PrefabUtility.GetCorrespondingObjectFromSource(transform) as Transform;
            if (source == null || transform.localPosition != source.localPosition ||
                transform.localRotation != source.localRotation || transform.localScale != source.localScale)
                return false;
        }
        Renderer[] renderers = variant.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length != original.GetComponentsInChildren<Renderer>(true).Length) return false;
        foreach (Renderer renderer in renderers)
        {
            Renderer source = PrefabUtility.GetCorrespondingObjectFromSource(renderer) as Renderer;
            if (source == null || renderer.GetType() != source.GetType() ||
                !SameMaterials(renderer.sharedMaterials, source.sharedMaterials)) return false;
            if (renderer == selected) continue;
            siblingCount++;
            if (renderer is SkinnedMeshRenderer skin)
            {
                SkinnedMeshRenderer sourceSkin = (SkinnedMeshRenderer)source;
                if (skin.sharedMesh != sourceSkin.sharedMesh || !BonesPreserved(skin, sourceSkin)) return false;
            }
            else if (renderer is MeshRenderer direct)
            {
                MeshFilter filter = direct.GetComponent<MeshFilter>();
                MeshFilter sourceFilter = source.GetComponent<MeshFilter>();
                if (filter == null || sourceFilter == null || filter.sharedMesh != sourceFilter.sharedMesh)
                    return false;
            }
            else return false;
        }
        return true;
    }

    private static void NegativeBadCandidate(Task task, long sourceMeshId,
        string variantHash, Report report)
    {
        string file = Disk(ManifestPath);
        byte[] original = File.ReadAllBytes(file);
        byte[] meta = File.ReadAllBytes(file + ".meta");
        try
        {
            RendererCandidate selected = null;
            foreach (RendererCandidate candidate in task.renderer_candidates)
                if (candidate.source_mesh_file_id == sourceMeshId.ToString())
                {
                    if (selected != null) throw new InvalidOperationException("SELECTED_SKIN_AMBIGUOUS");
                    selected = candidate;
                }
            if (selected == null || selected.bone_transform_file_ids == null ||
                selected.bone_transform_file_ids.Length == 0 ||
                selected.renderer_file_id == selected.bone_transform_file_ids[0])
                throw new InvalidOperationException("BAD_CANDIDATE_CONTROL_INVALID");
            string json = File.ReadAllText(file);
            string pattern = "\"renderer_file_id\"\\s*:\\s*\"" +
                Regex.Escape(selected.renderer_file_id) + "\"";
            if (Regex.Matches(json, pattern).Count != 1)
                throw new InvalidOperationException("BAD_CANDIDATE_CONTROL_INVALID");
            json = Regex.Replace(json, pattern,
                "\"renderer_file_id\": \"" + selected.bone_transform_file_ids[0] + "\"");
            File.WriteAllText(file, json);
            AssetDatabase.ImportAsset(ManifestPath,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            report.bad_candidate_rejected = !VapbModelSkinFinalizer.Apply(ManifestPath);
            report.bad_candidate_unchanged = Hash(Disk(task.variant_path)) == variantHash;
        }
        finally
        {
            File.WriteAllBytes(file, original);
            File.WriteAllBytes(file + ".meta", meta);
            AssetDatabase.ImportAsset(ManifestPath,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            report.manifest_restored_after_negative = EqualBytes(original, File.ReadAllBytes(file)) &&
                EqualBytes(meta, File.ReadAllBytes(file + ".meta"));
        }
    }

    private static void NegativeExtraComponent(string path, string expectedHash, Report report)
    {
        string file = Disk(path);
        byte[] original = File.ReadAllBytes(file);
        byte[] meta = File.ReadAllBytes(file + ".meta");
        try
        {
            GameObject contents = PrefabUtility.LoadPrefabContents(path);
            if (contents == null) throw new InvalidOperationException("VARIANT_LOAD_FAILED");
            try
            {
                contents.AddComponent<BoxCollider>();
                if (PrefabUtility.SaveAsPrefabAsset(contents, path) == null)
                    throw new InvalidOperationException("NEGATIVE_SAVE_FAILED");
            }
            finally { PrefabUtility.UnloadPrefabContents(contents); }
            string changedHash = Hash(file);
            if (changedHash == expectedHash) throw new InvalidOperationException("NEGATIVE_NOT_CHANGED");
            report.extra_component_rejected = !VapbModelSkinFinalizer.Apply(ManifestPath);
            report.rejected_variant_unchanged = changedHash == Hash(file);
        }
        finally
        {
            File.WriteAllBytes(file, original);
            File.WriteAllBytes(file + ".meta", meta);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            report.variant_restored_after_negative = EqualBytes(original, File.ReadAllBytes(file)) &&
                EqualBytes(meta, File.ReadAllBytes(file + ".meta"));
        }
    }

    private static bool SameMaterials(Material[] a, Material[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }
    private static bool Finite(float value) { return !float.IsNaN(value) && !float.IsInfinity(value); }
    private static bool EqualBytes(byte[] a, byte[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    private static string Disk(string path)
    { return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string ProjectFile(string name)
    { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }
    private static string Hash(string path)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static void Finish(Report report)
    {
        SessionState.SetString(Phase, "");
        try { File.WriteAllText(ProjectFile("VapbModelSkinRoundtripResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_MODEL_SKIN_ROUNDTRIP_PASS" : "VAPB_MODEL_SKIN_ROUNDTRIP_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
