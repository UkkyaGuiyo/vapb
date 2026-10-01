// SPDX-License-Identifier: GPL-3.0-or-later
// Public API evidence only. Run explicitly after package and declared SDK import.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public static class VapbModelBoundedSkinCapture
{
    const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] public class Manifest { public Task[] reference_rebind_tasks; public Dependency[] external_dependencies; }
    [Serializable] public class Dependency { public string kind, guid, file_id; }
    [Serializable] public class Task {
        public string kind, variant_path, model_guid, model_sha256, prefab_guid,
            prefab_source_sha256, source_model_guid, source_model_sha256, realization_id;
        public Mapping[] bone_mappings; public Candidate[] renderer_candidates;
    }
    [Serializable] public class Mapping { public string edited_bone_realization_id, source_model_uid; }
    [Serializable] public class Candidate {
        public string renderer_file_id, root_bone_transform_file_id;
        public string[] bone_transform_file_ids;
    }
    [Serializable] public class InputLock {
        public string expected_renderer_file_id, expected_owner_file_id, source_package_sha256,
            occurrence_id, blender_capture_sha256, output_sha256;
        public int cp_channel;
    }
    [Serializable] public class Bone {
        public int index; public string export_label, source_model_uid, target_file_id,
            parent_target_file_id, parent_export_label;
    }
    [Serializable] public class Weight { public int vertex, bone; public float weight; }
    [Serializable] public class UV { public int channel; public Vector4[] values; }
    [Serializable] public class Submesh { public int[] indices; }
    [Serializable] public class Row {
        public string guid, local_id, renderer_file_id, owner_file_id, root_bone_id,
            root_bone_export_label, root_bone_source_model_uid;
        public string[] ordered_bone_uids, ordered_target_ids;
        public int marker_invalid_count, shape_count;
        public int[] vertex_control_point_indices, triangles;
        public Vector3[] world_positions, world_normals;
        public float[] renderer_local_to_world;
        public UV[] uv_channels; public Submesh[] submeshes; public Bone[] bones;
        public Weight[] bone_weights; public string[] material_guids, material_file_ids;
    }
    [Serializable] public class Node {
        public string game_object_id, parent_game_object_id, transform_id, parent_transform_id,
            source_guid, source_game_object_id, source_transform_id, instance_guid, prefab_instance_file_id;
    }
    [Serializable] public class HierarchyBridge { public string output_sha256, prefab_source_sha256; public Node[] nodes; }
    [Serializable] public class Report {
        public string version, package_sha256, blender_capture_sha256, output_sha256,
            fbx_sha256, prefab_source_sha256, realization_id, occurrence_id,
            first_variant_sha256, repeated_variant_sha256, deformation_status = "UNMEASURED";
        public bool first_apply, second_apply, repeated_capture_equal, second_apply_unchanged,
            originals_unchanged, siblings_preserved, component_node_counts_unchanged;
        public int first_node_count, repeated_node_count, first_component_count, repeated_component_count;
        public int declared_script_refs, resolved_script_refs, missing_scripts;
        public Row first, repeated; public Node[] hierarchy;
    }
    static string Project => Path.GetDirectoryName(Application.dataPath);
    static string Hash(string path) { using (var sha = SHA256.Create()) return
        BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    static void Need(bool value, string code) { if (!value) throw new InvalidOperationException(code); }
    static string Id(UnityEngine.Object obj, string expectedGuid) {
        Need(obj != null, "NULL_EXACT_ID");
        Need(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out string guid, out long id)
            && guid == expectedGuid && id != 0, "EXACT_ID_UNAVAILABLE");
        return id.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }
    static T Source<T>(T obj) where T : UnityEngine.Object {
        var source = PrefabUtility.GetCorrespondingObjectFromSource(obj);
        Need(source != null, "SOURCE_CORRESPONDENCE_MISSING"); return source;
    }
    static SkinnedMeshRenderer Target(GameObject variant, SkinnedMeshRenderer original) =>
        variant.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single(s =>
            PrefabUtility.GetCorrespondingObjectFromSource(s) == original);
    static Node ObserveNode(Transform transform, string rootGuid) {
        var node = new Node { game_object_id = Id(transform.gameObject, rootGuid), transform_id = Id(transform, rootGuid),
            parent_game_object_id = transform.parent == null ? null : Id(transform.parent.gameObject, rootGuid),
            parent_transform_id = transform.parent == null ? null : Id(transform.parent, rootGuid) };
        var sourceTransform = PrefabUtility.GetCorrespondingObjectFromSource(transform);
        var sourceObject = PrefabUtility.GetCorrespondingObjectFromSource(transform.gameObject);
        if (sourceTransform != null && sourceObject != null &&
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sourceTransform, out string transformGuid, out long transformId) &&
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sourceObject, out string objectGuid, out long objectId)) {
            Need(transformGuid == objectGuid, "SOURCE_NODE_GUID_MISMATCH");
            node.source_guid = transformGuid; node.source_transform_id = transformId.ToString(System.Globalization.CultureInfo.InvariantCulture);
            node.source_game_object_id = objectId.ToString(System.Globalization.CultureInfo.InvariantCulture);
        }
        var handle = PrefabUtility.GetPrefabInstanceHandle(transform.gameObject);
        if (handle != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(handle, out string instanceGuid, out long instanceId)) {
            node.instance_guid = instanceGuid; node.prefab_instance_file_id = instanceId.ToString(System.Globalization.CultureInfo.InvariantCulture);
        }
        return node;
    }
    public static void CaptureHierarchyBridge() {
        try {
            var task = JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath)).reference_rebind_tasks.Single();
            var input = JsonUtility.FromJson<InputLock>(File.ReadAllText(Path.Combine(Project, "InputLock.json")));
            string path = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            Need(Hash(path) == task.prefab_source_sha256 && Hash(Path.Combine(Project, "Output.unitypackage")) == input.output_sha256,
                "HIERARCHY_BRIDGE_REVISION_MISMATCH");
            var original = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var bridge = new HierarchyBridge { output_sha256 = input.output_sha256, prefab_source_sha256 = task.prefab_source_sha256,
                nodes = original.GetComponentsInChildren<Transform>(true).Select(t => ObserveNode(t, task.prefab_guid)).ToArray() };
            File.WriteAllText(Path.Combine(Project, "ModelHierarchyBridge.json"), JsonUtility.ToJson(bridge, true));
            EditorApplication.Exit(0);
        } catch (Exception error) { Debug.LogError("VAPB_HIERARCHY_BRIDGE_FAILED=" + error.Message); EditorApplication.Exit(1); }
    }
    static bool Siblings(GameObject variant, GameObject original, SkinnedMeshRenderer selected) {
        var sources = original.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        var targets = variant.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        if (sources.Length != targets.Length) return false;
        foreach (var source in sources) {
            var target = Target(variant, source);
            if (source == selected) continue;
            if (target.sharedMesh != source.sharedMesh ||
                PrefabUtility.GetCorrespondingObjectFromSource(target.rootBone) != source.rootBone ||
                target.bones.Length != source.bones.Length ||
                !target.sharedMaterials.SequenceEqual(source.sharedMaterials)) return false;
            for (int i = 0; i < source.bones.Length; i++)
                if (PrefabUtility.GetCorrespondingObjectFromSource(target.bones[i]) != source.bones[i]) return false;
        }
        return true;
    }
    static Row Observe(Task task, InputLock input, SkinnedMeshRenderer original, GameObject variant) {
        var target = Target(variant, original);
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
        var native = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single(s =>
            s.GetComponent<VapbRealizationMarker>()?.realizationId == task.realization_id);
        var mesh = native.sharedMesh;
        Need(mesh != null && target.sharedMesh == mesh, "FINALIZER_MESH_BRIDGE_MISMATCH");
        Need(mesh.blendShapeCount == 0, "SHAPE_SCOPE_UNSUPPORTED");
        Need(native.bones.Length == target.bones.Length, "BONE_COUNT_MISMATCH");
        var mapping = task.bone_mappings.ToDictionary(b => b.edited_bone_realization_id, b => b.source_model_uid);
        var receipts = model.GetComponentsInChildren<VapbRealizationMarker>(true);
        var candidate = task.renderer_candidates.Single(c => c.renderer_file_id == input.expected_renderer_file_id);
        var bones = native.bones.Select((b, i) => {
            string label = b.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
            Need(!String.IsNullOrEmpty(label) && mapping.ContainsKey(label), "BONE_RECEIPT_MISSING");
            Need(receipts.Count(m => m.boneRealizationId == label) == 1, "BONE_RECEIPT_AMBIGUOUS");
            var source = Source(target.bones[i]);
            return new Bone { index = i, export_label = label, source_model_uid = mapping[label],
                target_file_id = Id(source, task.prefab_guid),
                parent_target_file_id = source.parent == null ? null : Id(source.parent, task.prefab_guid),
                parent_export_label = b.parent == null ? null : b.parent.GetComponent<VapbRealizationMarker>()?.boneRealizationId };
        }).ToArray();
        Need(bones.Select(b => b.export_label).Distinct().Count() == bones.Length, "BONE_RECEIPT_AMBIGUOUS");
        Need(new HashSet<string>(bones.Select(b => b.target_file_id)).SetEquals(candidate.bone_transform_file_ids),
            "TARGET_BONE_SET_MISMATCH");
        Need(Id(Source(target.rootBone), task.prefab_guid) == candidate.root_bone_transform_file_id,
            "TARGET_ROOT_MISMATCH");
        var uv = new List<UV>();
        for (int i = 0; i < 8; i++) { var values = new List<Vector4>(); mesh.GetUVs(i, values);
            uv.Add(new UV { channel = i, values = values.ToArray() }); }
        Need(input.cp_channel >= 0 && input.cp_channel < 8 && uv[input.cp_channel].values.Length == mesh.vertexCount,
            "CP_CHANNEL_INVALID");
        var cps = uv[input.cp_channel].values.Select(v => v.y == .375f && v.x >= 1 &&
            v.x <= Int32.MaxValue && v.x == Mathf.Round(v.x) ? (int)v.x - 1 : -1).ToArray();
        Need(cps.All(v => v >= 0), "CP_MARKER_INVALID");
        var weights = new List<Weight>(); var counts = mesh.GetBonesPerVertex(); var all = mesh.GetAllBoneWeights(); int offset = 0;
        try { for (int v = 0; v < counts.Length; v++) for (int i = 0; i < counts[v]; i++) {
            var w = all[offset++]; weights.Add(new Weight { vertex = v, bone = w.boneIndex, weight = w.weight }); } }
        finally { counts.Dispose(); all.Dispose(); }
        string rootLabel = native.rootBone == null ? null : native.rootBone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
        string rootUid = rootLabel != null && mapping.ContainsKey(rootLabel) ? mapping[rootLabel] : null;
        if (rootLabel != null) Need(rootUid != null && receipts.Count(m => m.boneRealizationId == rootLabel) == 1,
            "ROOT_RECEIPT_INVALID");
        var matrix = new float[16]; for (int i = 0; i < 16; i++) matrix[i] = native.localToWorldMatrix[i];
        var normalMatrix = native.localToWorldMatrix.inverse.transpose;
        return new Row { guid = task.model_guid, local_id = Id(mesh, task.model_guid),
            renderer_file_id = Id(Source(target), task.prefab_guid), owner_file_id = Id(Source(target.gameObject), task.prefab_guid),
            root_bone_id = Id(Source(target.rootBone), task.prefab_guid), root_bone_export_label = rootLabel,
            root_bone_source_model_uid = rootUid, bones = bones,
            ordered_bone_uids = bones.Select(b => b.source_model_uid).ToArray(),
            ordered_target_ids = bones.Select(b => b.target_file_id).ToArray(), bone_weights = weights.ToArray(),
            vertex_control_point_indices = cps, marker_invalid_count = cps.Count(v => v < 0), triangles = mesh.triangles,
            world_positions = mesh.vertices.Select(v => native.transform.TransformPoint(v)).ToArray(),
            world_normals = mesh.normals.Select(v => normalMatrix.MultiplyVector(v).normalized).ToArray(),
            renderer_local_to_world = matrix, uv_channels = uv.ToArray(),
            submeshes = Enumerable.Range(0, mesh.subMeshCount).Select(i => new Submesh { indices = mesh.GetIndices(i) }).ToArray(),
            material_guids = target.sharedMaterials.Select(m => AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(m))).ToArray(),
            material_file_ids = target.sharedMaterials.Select(m => m == null ? "0" :
                Id(m, AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(m)))).ToArray(),
            shape_count = mesh.blendShapeCount };
    }
    public static void Write() {
        Need(Application.unityVersion == "2022.3.22f1", "UNSUPPORTED_VERSION");
        var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
        var task = manifest.reference_rebind_tasks.Single();
        Need(task.kind == "RESTORE_DIRECT_SKIN_VARIANT_V1", "UNSUPPORTED_TASK_KIND");
        var input = JsonUtility.FromJson<InputLock>(File.ReadAllText(Path.Combine(Project, "InputLock.json")));
        Need(!String.IsNullOrEmpty(input.source_package_sha256) && !String.IsNullOrEmpty(input.occurrence_id), "INPUT_LOCK_INVALID");
        Need(Hash(Path.Combine(Project, "BoundedBlender.json")) == input.blender_capture_sha256, "STALE_BLENDER_CAPTURE");
        Need(Hash(Path.Combine(Project, "Output.unitypackage")) == input.output_sha256, "OUTPUT_REVISION_MISMATCH");
        string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
        string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
        string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
        Need(Hash(prefabPath) == task.prefab_source_sha256 && Hash(sourcePath) == task.source_model_sha256
            && Hash(editedPath) == task.model_sha256, "SOURCE_REVISION_MISMATCH");
        var original = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        var originalSkin = original.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single(s =>
            Id(s, task.prefab_guid) == input.expected_renderer_file_id);
        Need(Id(originalSkin.gameObject, task.prefab_guid) == input.expected_owner_file_id, "OWNER_MISMATCH");
        task.renderer_candidates.Single(c => c.renderer_file_id == input.expected_renderer_file_id);
        var report = new Report { version = Application.unityVersion, package_sha256 = input.source_package_sha256,
            blender_capture_sha256 = input.blender_capture_sha256, output_sha256 = input.output_sha256,
            fbx_sha256 = Hash(editedPath), prefab_source_sha256 = Hash(prefabPath),
            realization_id = task.realization_id, occurrence_id = input.occurrence_id,
            hierarchy = original.GetComponentsInChildren<Transform>(true).Select(t => ObserveNode(t, task.prefab_guid)).ToArray() };
        foreach (var transform in original.GetComponentsInChildren<Transform>(true))
            report.missing_scripts += GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject);
        foreach (var dependency in manifest.external_dependencies ?? new Dependency[0]) {
            if (dependency.kind != "UNITY_SCRIPT") continue;
            report.declared_script_refs++;
            string path = AssetDatabase.GUIDToAssetPath(dependency.guid);
            if (!String.IsNullOrEmpty(path) && AssetDatabase.LoadAllAssetsAtPath(path).OfType<MonoScript>().Any(script =>
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(script, out string guid, out long id) &&
                guid == dependency.guid && id.ToString(System.Globalization.CultureInfo.InvariantCulture) == dependency.file_id))
                report.resolved_script_refs++;
        }
        Need(report.declared_script_refs == report.resolved_script_refs && report.missing_scripts == 0,
            "SCRIPT_PROVIDER_NOT_RESOLVED");
        report.first_apply = VapbModelSkinFinalizer.Apply(ManifestPath);
        Need(report.first_apply, "FIRST_APPLY_FAILED");
        var variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
        Need(variant != null && PrefabUtility.GetPrefabAssetType(variant) == PrefabAssetType.Variant &&
            PrefabUtility.GetCorrespondingObjectFromSource(variant) == original, "VARIANT_SOURCE_MISMATCH");
        report.first = Observe(task, input, originalSkin, variant);
        report.first_variant_sha256 = Hash(task.variant_path);
        report.first_node_count = variant.GetComponentsInChildren<Transform>(true).Length;
        report.first_component_count = variant.GetComponentsInChildren<Component>(true).Length;
        Need(Siblings(variant, original, originalSkin), "SIBLING_CHANGED");
        report.second_apply = VapbModelSkinFinalizer.Apply(ManifestPath);
        Need(report.second_apply, "SECOND_APPLY_FAILED");
        variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
        report.repeated = Observe(task, input, originalSkin, variant);
        report.repeated_variant_sha256 = Hash(task.variant_path);
        report.repeated_node_count = variant.GetComponentsInChildren<Transform>(true).Length;
        report.repeated_component_count = variant.GetComponentsInChildren<Component>(true).Length;
        report.component_node_counts_unchanged = report.first_node_count == report.repeated_node_count &&
            report.first_component_count == report.repeated_component_count;
        report.repeated_capture_equal = JsonUtility.ToJson(report.first) == JsonUtility.ToJson(report.repeated);
        report.second_apply_unchanged = report.first_variant_sha256 == report.repeated_variant_sha256;
        report.siblings_preserved = Siblings(variant, original, originalSkin);
        report.originals_unchanged = Hash(prefabPath) == task.prefab_source_sha256 && Hash(sourcePath) == task.source_model_sha256 &&
            Hash(editedPath) == task.model_sha256;
        Need(report.component_node_counts_unchanged && report.repeated_capture_equal && report.second_apply_unchanged &&
            report.siblings_preserved && report.originals_unchanged, "REPEATED_OR_PRESERVATION_MISMATCH");
        File.WriteAllText(Path.Combine(Project, "ModelBoundedUnity.json"), JsonUtility.ToJson(report, true));
    }
    public static void Run() {
        try { Write(); EditorApplication.Exit(0); }
        catch (Exception error) {
            Debug.LogError("VAPB_BOUNDED_CAPTURE_FAILED=" + error.Message);
            EditorApplication.Exit(1);
        }
    }
}
