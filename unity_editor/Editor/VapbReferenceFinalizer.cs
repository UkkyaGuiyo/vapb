// SPDX-License-Identifier: MIT
/*
MIT License

Copyright (c) 2026 UkkyaGuiyo and VAPB contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public sealed class VapbRealizationPostprocessor : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject gameObject, string[] names, object[] values)
    {
        if (names == null || values == null || names.Length != values.Length ||
            !VapbReferenceFinalizer.IsAuthorizedModel(assetPath))
            return;
        for (int i = 0; i < names.Length; i++)
        {
            if (!(values[i] is string id))
                continue;
            bool mesh = names[i] == "_vapb_fbx_realization_id" &&
                VapbReferenceFinalizer.IsAuthorizedRealization(assetPath, id);
            bool bone = names[i] == "_vapb_fbx_bone_realization_id" &&
                VapbReferenceFinalizer.IsAuthorizedBone(assetPath, id);
            if (!mesh && !bone)
                continue;
            VapbRealizationMarker marker = gameObject.GetComponent<VapbRealizationMarker>();
            if (marker == null)
                marker = gameObject.AddComponent<VapbRealizationMarker>();
            if (mesh) marker.realizationId = id;
            if (bone) marker.boneRealizationId = id;
        }
    }
}

public static class VapbReferenceFinalizer
{
    private static readonly HashSet<string> KnownErrors = new HashSet<string>(StringComparer.Ordinal)
    {
        "MODEL_UNAVAILABLE", "DUPLICATE_TARGET", "PREFAB_UNAVAILABLE", "TARGET_STRUCTURE_UNSUPPORTED",
        "PREFAB_SAVE_FAILED", "MANIFEST_UNAVAILABLE", "MANIFEST_UNSUPPORTED", "TASK_UNSUPPORTED",
        "MATERIAL_ID_INVALID", "NESTED_OR_AMBIGUOUS_TARGET", "TARGET_NOT_FOUND",
        "MODEL_STRUCTURE_UNSUPPORTED", "MODEL_MESH_MISSING", "REALIZATION_NOT_FOUND",
        "MATERIAL_NOT_FOUND", "MATERIAL_AMBIGUOUS", "LOCAL_ID_INVALID",
        "MODEL_HASH_MISMATCH", "STALE_PREFAB_SOURCE", "INCONSISTENT_PREFAB_SOURCE", "UNSAVED_PREFAB_CHANGES",
        "SOURCE_MODEL_UNAVAILABLE", "SOURCE_MODEL_HASH_MISMATCH", "SOURCE_MESH_MISMATCH",
        "BONE_TARGET_INVALID", "BONE_MAPPING_INVALID", "BONE_MARKER_MISSING", "BONE_REST_MISMATCH",
        "SKIN_WEIGHTS_INVALID", "SKIN_ROOT_INVALID"
    };
    [Serializable] private sealed class Manifest
    {
        public string schema_version;
        public Task[] reference_rebind_tasks;
    }

    [Serializable] private sealed class Task
    {
        public string kind;
        public string prefab_guid;
        public string variant_path;
        public string renderer_file_id;
        public string model_guid;
        public string model_sha256;
        public string prefab_source_sha256;
        public string realization_id;
        public int renderer_class_id;
        public MaterialId[] materials;
        public string source_model_guid;
        public string source_model_sha256;
        public string source_mesh_file_id;
        public BoneId[] bones;
        public string[] source_bone_transform_file_ids;
        public string root_bone_target_transform_file_id;
    }

    [Serializable] private sealed class BoneId
    {
        public string edited_bone_realization_id;
        public string target_transform_file_id;
    }

    [Serializable] private sealed class MaterialId
    {
        public string guid;
        public string file_id;
    }

    private sealed class Binding
    {
        public MeshFilter filter;
        public MeshRenderer renderer;
        public SkinnedMeshRenderer skin;
        public Mesh mesh;
        public Material[] materials;
        public Transform[] bones;
        public Transform rootBone;
    }

    private sealed class PrefabPlan
    {
        public string path;
        public GameObject contents;
        public readonly List<Binding> bindings = new List<Binding>();
        public byte[] originalBytes;
        public string sourceHash;
    }

    [MenuItem("Tools/VAPB/Apply Selected Export Manifest")]
    private static void ApplySelected()
    {
        // Batch callers use Apply directly; this menu is an explicit user action.
        if (Application.isBatchMode) return;
        string path = AssetDatabase.GetAssetPath(Selection.activeObject);
        if (VapbModelSkinFinalizer.Handles(path))
        {
            VapbImportAssistant.Show(path);
            return;
        }
        var outputs = new HashSet<string>(StringComparer.Ordinal);
        var targets = new HashSet<string>(StringComparer.Ordinal);
        bool variant = VapbModelSkinFinalizer.Handles(path);
        try
        {
            Manifest manifest = ReadManifest(path);
            if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
                manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length == 0)
                throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
            if (!variant) ValidateTaskSyntax(manifest);
            foreach (Task task in manifest.reference_rebind_tasks)
            {
                if (task == null) throw new InvalidOperationException("TASK_UNSUPPORTED");
                string target = AssetDatabase.GUIDToAssetPath(
                    task.kind == "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1" ? task.source_model_guid : task.prefab_guid);
                if (string.IsNullOrEmpty(target)) throw new InvalidOperationException("PREFAB_UNAVAILABLE");
                targets.Add(target);
                if (variant)
                {
                    if ((task.kind != "RESTORE_MODEL_SKIN_VARIANT_V1" &&
                         task.kind != "RESTORE_DIRECT_SKIN_VARIANT_V1" &&
                         task.kind != "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1") ||
                        string.IsNullOrEmpty(task.variant_path) ||
                        !task.variant_path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal) ||
                        !task.variant_path.EndsWith(".prefab", StringComparison.Ordinal) ||
                        task.variant_path.Contains("..") || task.variant_path.Contains("\\"))
                        throw new InvalidOperationException("TASK_UNSUPPORTED");
                    outputs.Add(task.variant_path);
                }
                else outputs.Add(target);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("VAPB_FINALIZER_CONFIRMATION_REJECTED=" + exception.Message);
            EditorUtility.DisplayDialog("VAPB：適用できません",
                "対象の編集データを確認できませんでした。詳細はConsoleを確認してください。", "閉じる");
            return;
        }
        // This fallback describes the operation; full identity/dependency checks
        // remain in Apply. Do not label this limited inspection a preflight pass.
        string message = "VAPBの編集データを検出しました。\n\n対象：\n" +
            string.Join("\n", new List<string>(targets).ToArray()) +
            "\n\n" + (variant ? "編集Mesh/Skinを別のPrefab Variantに接続します。元のPrefabを保持します。" :
                "対象PrefabのMesh/SkinとMaterial参照を更新します。対象Prefab自体を保存します。") +
            "\nBone/rootBoneの再接続を含む参照と編集範囲は、適用時に既存Finalizerで検証します。" +
            "\n\n保存先：\n" + string.Join("\n", new List<string>(outputs).ToArray()) +
            "\n\n適用前の全検証は未実施です。未対応の編集や参照不一致は適用時に拒否されます。";
        if (!EditorUtility.DisplayDialog("VAPB：編集内容を適用", message, "適用", "キャンセル")) return;
        if (!Apply(path))
        {
            Debug.LogError("VAPB_FINALIZER_FAILED");
            EditorUtility.DisplayDialog("VAPB：適用できませんでした",
                "Finalizerが適用を拒否しました。詳細はConsoleを確認してください。", "閉じる");
            return;
        }
        foreach (string output in outputs)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(output);
            if (prefab == null) continue;
            Selection.activeObject = prefab;
            EditorGUIUtility.PingObject(prefab);
            break;
        }
        EditorUtility.DisplayDialog("VAPB：適用結果",
            "適用処理が完了しました。\n保存先：\n" + string.Join("\n", new List<string>(outputs).ToArray()) +
            "\n\nPrefabを開いて編集内容を確認してください。対応範囲は書き出した編集データに限られます。", "閉じる");
    }

    [MenuItem("Tools/VAPB/Apply Selected Export Manifest", true)]
    private static bool CanApplySelected()
    {
        return Selection.activeObject is TextAsset &&
            IsManifestPath(AssetDatabase.GetAssetPath(Selection.activeObject));
    }

    public static bool Apply(string manifestAssetPath)
    {
        if (VapbModelSkinFinalizer.Handles(manifestAssetPath))
            return VapbModelSkinFinalizer.Apply(manifestAssetPath);
        var plans = new Dictionary<string, PrefabPlan>(StringComparer.Ordinal);
        try
        {
            Manifest manifest = ReadManifest(manifestAssetPath);
            ValidateTaskSyntax(manifest);
            // Import may have seen the model before the manifest. Reimport now that
            // authorization is available so its persistent marker is materialized.
            var modelGuids = new HashSet<string>(StringComparer.Ordinal);
            foreach (Task task in manifest.reference_rebind_tasks)
                modelGuids.Add(task.model_guid);
            foreach (Task task in manifest.reference_rebind_tasks)
            {
                if (task.kind != "REBIND_SKINNED_RENDERER_V1")
                    continue;
                string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
                if (string.IsNullOrEmpty(sourcePath) || !sourcePath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("SOURCE_MODEL_UNAVAILABLE");
                if (!FileHash(ToDiskPath(sourcePath)).Equals(task.source_model_sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("SOURCE_MODEL_HASH_MISMATCH");
            }
            foreach (string guid in modelGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path) || !path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) ||
                    !IsAuthorizedModel(path))
                    throw new InvalidOperationException("MODEL_UNAVAILABLE");
                string actualHash = FileHash(ToDiskPath(path));
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task.model_guid == guid && !actualHash.Equals(task.model_sha256, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidOperationException("MODEL_HASH_MISMATCH");
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }

            var identities = new HashSet<string>(StringComparer.Ordinal);
            foreach (Task task in manifest.reference_rebind_tasks)
            {
                long rendererId = ParseLocalId(task.renderer_file_id);
                string key = task.prefab_guid + ":" + rendererId.ToString(CultureInfo.InvariantCulture);
                if (!identities.Add(key))
                    throw new InvalidOperationException("DUPLICATE_TARGET");
                string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
                if (string.IsNullOrEmpty(prefabPath) || !prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("PREFAB_UNAVAILABLE");
                if (!plans.TryGetValue(prefabPath, out PrefabPlan plan))
                {
                    plan = new PrefabPlan { path = prefabPath };
                    plan.contents = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                    if (plan.contents == null)
                        throw new InvalidOperationException("PREFAB_UNAVAILABLE");
                    plan.sourceHash = task.prefab_source_sha256;
                    foreach (Transform transform in plan.contents.GetComponentsInChildren<Transform>(true))
                    {
                        if (EditorUtility.IsDirty(transform.gameObject))
                            throw new InvalidOperationException("UNSAVED_PREFAB_CHANGES");
                        foreach (Component component in transform.GetComponents<Component>())
                            if (component != null && EditorUtility.IsDirty(component))
                                throw new InvalidOperationException("UNSAVED_PREFAB_CHANGES");
                    }
                    plans.Add(prefabPath, plan);
                }
                else if (!plan.sourceHash.Equals(task.prefab_source_sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("INCONSISTENT_PREFAB_SOURCE");
                Material[] materials = ResolveMaterials(task.materials);
                if (task.kind == "REBIND_DIRECT_RENDERER_V1")
                {
                    MeshRenderer target = ResolveTarget<MeshRenderer>(plan.contents, task.prefab_guid, rendererId);
                    MeshFilter filter = target.GetComponent<MeshFilter>();
                    if (filter == null || target.GetComponents<Renderer>().Length != 1)
                        throw new InvalidOperationException("TARGET_STRUCTURE_UNSUPPORTED");
                    Mesh mesh = ResolveModelMesh(task);
                    plan.bindings.Add(new Binding { filter = filter, renderer = target, mesh = mesh, materials = materials });
                }
                else
                {
                    SkinnedMeshRenderer target = ResolveTarget<SkinnedMeshRenderer>(plan.contents, task.prefab_guid, rendererId);
                    if (target.GetComponents<Renderer>().Length != 1)
                        throw new InvalidOperationException("TARGET_STRUCTURE_UNSUPPORTED");
                    Binding binding = ResolveSkinBinding(plan.contents, task, target, materials);
                    plan.bindings.Add(binding);
                }
            }

            // All targets and references are resolved before any prefab is changed.
            foreach (PrefabPlan plan in plans.Values)
            {
                plan.originalBytes = File.ReadAllBytes(ToDiskPath(plan.path));
                bool needsChange = false;
                foreach (Binding binding in plan.bindings)
                    if (NeedsChange(binding))
                        needsChange = true;
                if (needsChange && !HashBytes(plan.originalBytes).Equals(plan.sourceHash, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("STALE_PREFAB_SOURCE");
            }
            var saved = new List<PrefabPlan>();
            try
            {
                foreach (PrefabPlan plan in plans.Values)
                {
                    // Cover exceptions during property mutation as well as save.
                    saved.Add(plan);
                    bool changed = false;
                    foreach (Binding binding in plan.bindings)
                    {
                        if (binding.skin != null)
                        {
                            bool bindingChanged = false;
                            if (binding.skin.sharedMesh != binding.mesh)
                            {
                                binding.skin.sharedMesh = binding.mesh;
                                bindingChanged = true;
                            }
                            if (!SameBones(binding.skin.bones, binding.bones))
                            {
                                binding.skin.bones = binding.bones;
                                bindingChanged = true;
                            }
                            if (binding.skin.rootBone != binding.rootBone)
                            {
                                binding.skin.rootBone = binding.rootBone;
                                bindingChanged = true;
                            }
                            if (!SameMaterials(binding.skin.sharedMaterials, binding.materials))
                            {
                                binding.skin.sharedMaterials = binding.materials;
                                bindingChanged = true;
                            }
                            if (bindingChanged)
                            {
                                EditorUtility.SetDirty(binding.skin);
                                changed = true;
                            }
                        }
                        else
                        {
                            if (binding.filter.sharedMesh != binding.mesh)
                            {
                                binding.filter.sharedMesh = binding.mesh;
                                EditorUtility.SetDirty(binding.filter);
                                changed = true;
                            }
                            if (!SameMaterials(binding.renderer.sharedMaterials, binding.materials))
                            {
                                binding.renderer.sharedMaterials = binding.materials;
                                EditorUtility.SetDirty(binding.renderer);
                                changed = true;
                            }
                        }
                    }
                    if (!changed)
                        continue;
                    GameObject result = PrefabUtility.SavePrefabAsset(plan.contents);
                    if (result == null)
                        throw new InvalidOperationException("PREFAB_SAVE_FAILED");
                }
            }
            catch
            {
                foreach (PrefabPlan plan in saved)
                {
                    File.WriteAllBytes(ToDiskPath(plan.path), plan.originalBytes);
                    AssetDatabase.ImportAsset(plan.path, ImportAssetOptions.ForceUpdate);
                }
                throw;
            }
            Debug.Log("VAPB_FINALIZER_APPLIED=" + manifest.reference_rebind_tasks.Length);
            return true;
        }
        catch (Exception exception)
        {
            string code = exception is InvalidOperationException && KnownErrors.Contains(exception.Message)
                ? exception.Message : "UNEXPECTED_EXCEPTION";
            Debug.LogError("VAPB_FINALIZER_REJECTED=" + code);
            return false;
        }
    }

    private static Manifest ReadManifest(string path)
    {
        if (!IsManifestPath(path) || AssetDatabase.LoadAssetAtPath<TextAsset>(path) == null)
            throw new InvalidOperationException("MANIFEST_UNAVAILABLE");
        return JsonUtility.FromJson<Manifest>(File.ReadAllText(ToDiskPath(path)));
    }

    private static void ValidateTaskSyntax(Manifest manifest)
    {
        if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
            manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length == 0)
            throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
        foreach (Task task in manifest.reference_rebind_tasks)
        {
            if (task == null || (task.kind != "REBIND_DIRECT_RENDERER_V1" && task.kind != "REBIND_SKINNED_RENDERER_V1") ||
                task.renderer_class_id != (task.kind == "REBIND_DIRECT_RENDERER_V1" ? 23 : 137) ||
                !ValidGuid(task.prefab_guid) || !ValidGuid(task.model_guid) ||
                !ValidSha256(task.model_sha256) || !ValidSha256(task.prefab_source_sha256) ||
                string.IsNullOrEmpty(task.realization_id) || task.materials == null)
                throw new InvalidOperationException("TASK_UNSUPPORTED");
            ParseLocalId(task.renderer_file_id);
            if (task.kind == "REBIND_SKINNED_RENDERER_V1")
            {
                if (!ValidGuid(task.source_model_guid) || !ValidSha256(task.source_model_sha256) ||
                    task.source_model_guid == task.model_guid || task.bones == null || task.bones.Length == 0 ||
                    task.source_bone_transform_file_ids == null ||
                    task.source_bone_transform_file_ids.Length == 0)
                    throw new InvalidOperationException("TASK_UNSUPPORTED");
                ParseLocalId(task.source_mesh_file_id);
                ParseLocalId(task.root_bone_target_transform_file_id);
                var edited = new HashSet<string>(StringComparer.Ordinal);
                var targets = new HashSet<long>();
                foreach (BoneId bone in task.bones)
                {
                    if (bone == null || string.IsNullOrEmpty(bone.edited_bone_realization_id) ||
                        !edited.Add(bone.edited_bone_realization_id) ||
                        !targets.Add(ParseLocalId(bone.target_transform_file_id)))
                        throw new InvalidOperationException("BONE_MAPPING_INVALID");
                }
                var sourceTargets = new HashSet<long>();
                foreach (string sourceId in task.source_bone_transform_file_ids)
                    if (!sourceTargets.Add(ParseLocalId(sourceId)))
                        throw new InvalidOperationException("BONE_MAPPING_INVALID");
                long rootTarget = ParseLocalId(task.root_bone_target_transform_file_id);
                if (!targets.Contains(rootTarget))
                    throw new InvalidOperationException("SKIN_ROOT_INVALID");
                sourceTargets.Add(rootTarget);
                if (!sourceTargets.SetEquals(targets))
                    throw new InvalidOperationException("BONE_MAPPING_INVALID");
            }
            foreach (MaterialId material in task.materials)
                if (material != null && (!ValidGuid(material.guid) || ParseLocalId(material.file_id) == 0))
                    throw new InvalidOperationException("MATERIAL_ID_INVALID");
        }
    }

    private static T ResolveTarget<T>(GameObject contents, string guid, long localId) where T : Renderer
    {
        T result = null;
        foreach (T renderer in contents.GetComponentsInChildren<T>(true))
        {
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string sourceGuid, out long sourceId) ||
                sourceGuid != guid || sourceId != localId)
                continue;
            if (PrefabUtility.IsPartOfPrefabInstance(renderer) || result != null)
                throw new InvalidOperationException("NESTED_OR_AMBIGUOUS_TARGET");
            result = renderer;
        }
        if (result == null)
            throw new InvalidOperationException("TARGET_NOT_FOUND");
        return result;
    }

    private static Transform ResolveBoneTarget(GameObject contents, string guid, long localId)
    {
        Transform result = null;
        foreach (Transform transform in contents.GetComponentsInChildren<Transform>(true))
        {
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(transform, out string foundGuid, out long foundId) ||
                foundGuid != guid || foundId != localId)
                continue;
            if (PrefabUtility.IsPartOfPrefabInstance(transform) || result != null)
                throw new InvalidOperationException("BONE_TARGET_INVALID");
            result = transform;
        }
        if (result == null)
            throw new InvalidOperationException("BONE_TARGET_INVALID");
        return result;
    }

    private static Mesh ResolveModelMesh(Task task)
    {
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
        if (model == null)
            throw new InvalidOperationException("MODEL_UNAVAILABLE");
        Mesh found = null;
        foreach (VapbRealizationMarker marker in model.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if (marker.realizationId != task.realization_id)
                continue;
            if (found != null || marker.GetComponents<Renderer>().Length != 1 ||
                marker.GetComponent<MeshRenderer>() == null || marker.GetComponents<MeshFilter>().Length != 1)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
            found = marker.GetComponent<MeshFilter>().sharedMesh;
            if (found == null)
                throw new InvalidOperationException("MODEL_MESH_MISSING");
        }
        if (found == null)
            throw new InvalidOperationException("REALIZATION_NOT_FOUND");
        return found;
    }

    private static Binding ResolveSkinBinding(GameObject contents, Task task, SkinnedMeshRenderer target,
                                               Material[] materials)
    {
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
        if (model == null)
            throw new InvalidOperationException("MODEL_UNAVAILABLE");
        SkinnedMeshRenderer edited = null;
        foreach (VapbRealizationMarker marker in model.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if (marker.realizationId != task.realization_id)
                continue;
            if (edited != null || marker.GetComponents<Renderer>().Length != 1)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
            edited = marker.GetComponent<SkinnedMeshRenderer>();
            if (edited == null || edited.sharedMesh == null)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
        }
        if (edited == null)
            throw new InvalidOperationException("REALIZATION_NOT_FOUND");
        Mesh mesh = edited.sharedMesh;
        Mesh sourceMesh = ResolveSourceMesh(task);
        Transform[] editedBones = edited.bones;
        if (editedBones == null || editedBones.Length != task.source_bone_transform_file_ids.Length ||
            mesh.bindposes.Length != editedBones.Length || sourceMesh.bindposes.Length != editedBones.Length ||
            !SameBlendShapeLayout(sourceMesh, mesh))
            throw new InvalidOperationException("BONE_MAPPING_INVALID");
        Transform[] targetBones = new Transform[editedBones.Length];
        var mapping = new Dictionary<string, long>(StringComparer.Ordinal);
        foreach (BoneId bone in task.bones)
            mapping.Add(bone.edited_bone_realization_id, ParseLocalId(bone.target_transform_file_id));
        var markerCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (VapbRealizationMarker marker in model.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if (string.IsNullOrEmpty(marker.boneRealizationId)) continue;
            if (!markerCounts.ContainsKey(marker.boneRealizationId)) markerCounts.Add(marker.boneRealizationId, 0);
            markerCounts[marker.boneRealizationId]++;
        }
        var seenEditedBones = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < editedBones.Length; i++)
        {
            Transform bone = editedBones[i];
            string id = bone == null ? null : bone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
            if (id == null || !seenEditedBones.Add(id) || !mapping.TryGetValue(id, out long targetId) ||
                !markerCounts.TryGetValue(id, out int count) || count != 1)
                throw new InvalidOperationException("BONE_MARKER_MISSING");
            targetBones[i] = ResolveBoneTarget(contents, task.prefab_guid, targetId);
        }
        Transform root = ResolveBoneTarget(contents, task.prefab_guid,
            ParseLocalId(task.root_bone_target_transform_file_id));
        string rootMarker = edited.rootBone == null ? null :
            edited.rootBone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
        if (rootMarker == null || !mapping.TryGetValue(rootMarker, out long mappedRoot) ||
            mappedRoot != ParseLocalId(task.root_bone_target_transform_file_id) ||
            !markerCounts.TryGetValue(rootMarker, out int rootCount) || rootCount != 1)
            throw new InvalidOperationException("SKIN_ROOT_INVALID");
        seenEditedBones.Add(rootMarker);
        if (seenEditedBones.Count != mapping.Count)
            throw new InvalidOperationException("BONE_MAPPING_INVALID");
        bool alreadyApplied = target.sharedMesh == mesh && SameBones(target.bones, targetBones) && target.rootBone == root;
        if (!alreadyApplied)
        {
            Mesh old = target.sharedMesh;
            if (old != sourceMesh)
                throw new InvalidOperationException("SOURCE_MESH_MISMATCH");
            Transform[] existing = target.bones;
            if (existing == null || existing.Length != task.source_bone_transform_file_ids.Length ||
                target.rootBone != root)
                throw new InvalidOperationException("BONE_TARGET_INVALID");
            for (int i = 0; i < existing.Length; i++)
                if (existing[i] != ResolveBoneTarget(contents, task.prefab_guid,
                    ParseLocalId(task.source_bone_transform_file_ids[i])) ||
                    !SameMatrix(sourceMesh.bindposes[i], existing[i].worldToLocalMatrix *
                        target.transform.localToWorldMatrix, 0.001f))
                    throw new InvalidOperationException("BONE_TARGET_INVALID");
        }
        Matrix4x4[] bindposes = mesh.bindposes;
        for (int i = 0; i < targetBones.Length; i++)
        {
            Matrix4x4 expected = targetBones[i].worldToLocalMatrix * target.transform.localToWorldMatrix;
            if (!SameMatrix(bindposes[i], expected, 0.001f))
                throw new InvalidOperationException("BONE_REST_MISMATCH");
        }
        ValidateWeights(mesh, targetBones.Length);
        return new Binding { skin = target, mesh = mesh, materials = materials,
                             bones = targetBones, rootBone = root };
    }

    private static Mesh ResolveSourceMesh(Task task)
    {
        string path = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
        long requiredId = ParseLocalId(task.source_mesh_file_id);
        Mesh found = null;
        foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
        {
            if (!(asset is Mesh mesh) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long id) ||
                guid != task.source_model_guid || id != requiredId)
                continue;
            if (found != null) throw new InvalidOperationException("SOURCE_MESH_MISMATCH");
            found = mesh;
        }
        if (found == null) throw new InvalidOperationException("SOURCE_MESH_MISMATCH");
        return found;
    }

    private static bool SameBlendShapeLayout(Mesh source, Mesh edited)
    {
        if (source.blendShapeCount != edited.blendShapeCount) return false;
        for (int shape = 0; shape < source.blendShapeCount; shape++)
        {
            if (source.GetBlendShapeName(shape) != edited.GetBlendShapeName(shape) ||
                source.GetBlendShapeFrameCount(shape) != edited.GetBlendShapeFrameCount(shape)) return false;
            for (int frame = 0; frame < source.GetBlendShapeFrameCount(shape); frame++)
                if (Mathf.Abs(source.GetBlendShapeFrameWeight(shape, frame) -
                              edited.GetBlendShapeFrameWeight(shape, frame)) > 0.0001f) return false;
        }
        return true;
    }

    private static bool SameMatrix(Matrix4x4 a, Matrix4x4 b, float tolerance)
    {
        for (int i = 0; i < 16; i++)
            if (float.IsNaN(a[i]) || float.IsInfinity(a[i]) ||
                float.IsNaN(b[i]) || float.IsInfinity(b[i]) || Mathf.Abs(a[i] - b[i]) > tolerance)
                return false;
        return true;
    }

    private static void ValidateWeights(Mesh mesh, int boneCount)
    {
        try
        {
            var perVertex = mesh.GetBonesPerVertex();
            var weights = mesh.GetAllBoneWeights();
            try
            {
                if (perVertex.Length != mesh.vertexCount)
                    throw new InvalidOperationException("SKIN_WEIGHTS_INVALID");
                int offset = 0;
                for (int vertex = 0; vertex < perVertex.Length; vertex++)
                {
                    int count = perVertex[vertex];
                    if (count == 0 || offset + count > weights.Length)
                        throw new InvalidOperationException("SKIN_WEIGHTS_INVALID");
                    float sum = 0f;
                    for (int i = 0; i < count; i++)
                    {
                        var weight = weights[offset + i];
                        if (weight.boneIndex < 0 || weight.boneIndex >= boneCount ||
                            float.IsNaN(weight.weight) || float.IsInfinity(weight.weight) || weight.weight <= 0f)
                            throw new InvalidOperationException("SKIN_WEIGHTS_INVALID");
                        sum += weight.weight;
                    }
                    if (Mathf.Abs(sum - 1f) > 0.01f)
                        throw new InvalidOperationException("SKIN_WEIGHTS_INVALID");
                    offset += count;
                }
                if (offset != weights.Length)
                    throw new InvalidOperationException("SKIN_WEIGHTS_INVALID");
            }
            finally { perVertex.Dispose(); weights.Dispose(); }
        }
        catch (InvalidOperationException) { throw; }
        catch (Exception) { throw new InvalidOperationException("SKIN_WEIGHTS_INVALID"); }
    }

    private static Material[] ResolveMaterials(MaterialId[] ids)
    {
        var result = new Material[ids.Length];
        for (int i = 0; i < ids.Length; i++)
        {
            if (ids[i] == null)
                continue;
            long localId = ParseLocalId(ids[i].file_id);
            string path = AssetDatabase.GUIDToAssetPath(ids[i].guid);
            if (string.IsNullOrEmpty(path))
                throw new InvalidOperationException("MATERIAL_NOT_FOUND");
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
            {
                if (!(asset is Material material) ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id) ||
                    guid != ids[i].guid || id != localId)
                    continue;
                if (result[i] != null)
                    throw new InvalidOperationException("MATERIAL_AMBIGUOUS");
                result[i] = material;
            }
            if (result[i] == null)
                throw new InvalidOperationException("MATERIAL_NOT_FOUND");
        }
        return result;
    }

    private static bool SameMaterials(Material[] a, Material[] b)
    {
        if (a.Length != b.Length)
            return false;
        for (int i = 0; i < a.Length; i++)
            if (a[i] != b[i])
                return false;
        return true;
    }

    private static bool SameBones(Transform[] a, Transform[] b)
    {
        if (a == null || b == null || a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++)
            if (a[i] != b[i]) return false;
        return true;
    }

    private static bool NeedsChange(Binding binding)
    {
        if (binding.skin != null)
            return binding.skin.sharedMesh != binding.mesh || !SameBones(binding.skin.bones, binding.bones) ||
                binding.skin.rootBone != binding.rootBone ||
                !SameMaterials(binding.skin.sharedMaterials, binding.materials);
        return binding.filter.sharedMesh != binding.mesh ||
            !SameMaterials(binding.renderer.sharedMaterials, binding.materials);
    }

    internal static bool IsAuthorizedModel(string modelPath)
    {
        if (string.IsNullOrEmpty(modelPath) || !modelPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
            return false;
        string guid = AssetDatabase.AssetPathToGUID(modelPath);
        if (!ValidGuid(guid))
            return false;
        foreach (string path in ManifestPaths())
        {
            try
            {
                Manifest manifest = ReadManifest(path);
                ValidateTaskSyntax(manifest);
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task != null && (task.kind == "REBIND_DIRECT_RENDERER_V1" ||
                        task.kind == "REBIND_SKINNED_RENDERER_V1") && task.model_guid == guid)
                        return true;
            }
            catch { /* Invalid manifest does not authorize imports. */ }
        }
        return false;
    }

    internal static bool IsAuthorizedRealization(string modelPath, string id)
    {
        if (string.IsNullOrEmpty(id))
            return false;
        string guid = AssetDatabase.AssetPathToGUID(modelPath);
        foreach (string path in ManifestPaths())
        {
            try
            {
                Manifest manifest = ReadManifest(path);
                ValidateTaskSyntax(manifest);
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task != null && (task.kind == "REBIND_DIRECT_RENDERER_V1" ||
                        task.kind == "REBIND_SKINNED_RENDERER_V1") && task.model_guid == guid &&
                        task.realization_id == id)
                        return true;
            }
            catch { /* Invalid manifest does not authorize imports. */ }
        }
        return false;
    }

    internal static bool IsAuthorizedBone(string modelPath, string id)
    {
        if (string.IsNullOrEmpty(id)) return false;
        string guid = AssetDatabase.AssetPathToGUID(modelPath);
        foreach (string path in ManifestPaths())
        {
            try
            {
                Manifest manifest = ReadManifest(path);
                ValidateTaskSyntax(manifest);
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task != null && task.kind == "REBIND_SKINNED_RENDERER_V1" && task.model_guid == guid)
                        foreach (BoneId bone in task.bones)
                            if (bone.edited_bone_realization_id == id) return true;
            }
            catch { /* Invalid manifest does not authorize imports. */ }
        }
        return false;
    }

    private static IEnumerable<string> ManifestPaths()
    {
        const string folder = "Assets/VAPBExport";
        if (!AssetDatabase.IsValidFolder(folder))
            yield break;
        foreach (string guid in AssetDatabase.FindAssets("t:TextAsset", new[] { folder }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (IsManifestPath(path))
                yield return path;
        }
    }

    private static bool IsManifestPath(string path)
    {
        return !string.IsNullOrEmpty(path) && path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal) &&
            path.EndsWith(".json", StringComparison.OrdinalIgnoreCase) && path.IndexOf("..", StringComparison.Ordinal) < 0;
    }

    private static bool ValidGuid(string value)
    {
        if (value == null || value.Length != 32)
            return false;
        foreach (char c in value)
            if (!Uri.IsHexDigit(c))
                return false;
        return true;
    }

    private static bool ValidSha256(string value)
    {
        if (value == null || value.Length != 64)
            return false;
        foreach (char c in value)
            if (!Uri.IsHexDigit(c))
                return false;
        return true;
    }

    private static string FileHash(string path)
    {
        return HashBytes(File.ReadAllBytes(path));
    }

    private static string HashBytes(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }

    private static long ParseLocalId(string value)
    {
        if (string.IsNullOrEmpty(value) || !long.TryParse(value, NumberStyles.AllowLeadingSign,
            CultureInfo.InvariantCulture, out long id) || id == 0)
            throw new InvalidOperationException("LOCAL_ID_INVALID");
        return id;
    }

    private static string ToDiskPath(string assetPath)
    {
        return Path.Combine(Application.dataPath, assetPath.Substring("Assets/".Length).Replace('/', Path.DirectorySeparatorChar));
    }
}
