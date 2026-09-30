// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// The FBX user-property callback is a documented public ModelImporter hook.
public sealed class VapbExportObjectPostprocessor : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject gameObject,
        string[] names, object[] values)
    {
        if (names == null || values == null || names.Length != values.Length)
            return;
        for (int i = 0; i < names.Length; i++)
        {
            if (names[i] != "_vapb_export_object_id" || !(values[i] is string id))
                continue;
            if (!VapbFinalStateFinalizer.IsAuthorizedExportObject(assetPath, id)) continue;
            if (gameObject.GetComponent<MeshRenderer>() == null ||
                gameObject.GetComponent<MeshFilter>() == null)
                continue;
            VapbExportObjectMarker marker = gameObject.GetComponent<VapbExportObjectMarker>();
            if (marker == null) marker = gameObject.AddComponent<VapbExportObjectMarker>();
            marker.exportObjectId = id;
        }
    }
}

public static class VapbFinalStateFinalizer
{
    public static string LastResult { get; private set; } = "NOT_RUN";
    [Serializable] public sealed class ReferenceResult
    {
        public string reference_id;
        public string kind;
        public string guid;
        public string file_id;
        public string status;
    }
    public static ReferenceResult[] LastReferences { get; private set; } = new ReferenceResult[0];
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string TaskKind = "BUILD_EXPORTED_STATIC_V1";
    [Serializable] private sealed class Manifest
    {
        public string schema_version;
        public Task[] reference_rebind_tasks;
    }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string export_object_id;
        public string model_guid;
        public string model_sha256;
        public string prefab_path;
        public MaterialRecord[] materials;
        public SlotRecord[] material_slots;
    }
    [Serializable] private sealed class MaterialRecord
    {
        public string export_material_id;
        public string guid;
        public string file_id;
        public string asset_sha256;
        public ShaderRecord shader;
        public TextureRecord[] textures;
    }
    [Serializable] private sealed class ShaderRecord
    {
        public string classification;
        public string guid;
        public string file_id;
        public string reference_id;
        public string kind;
        public string status;
    }
    [Serializable] private sealed class TextureRecord
    {
        public string property_name;
        public string guid;
        public string file_id;
    }
    [Serializable] private sealed class SlotRecord
    {
        public int slot_index;
        public string export_material_id;
    }

    [MenuItem("Tools/VAPB/Build Final State Prefab")]
    private static void ApplySelected()
    {
        string path = AssetDatabase.GetAssetPath(Selection.activeObject);
        if (!Apply(path) && LastResult != "PARTIAL") Debug.LogError("VAPB_FINAL_STATE_FAILED");
    }

    [MenuItem("Tools/VAPB/Build Final State Prefab", true)]
    private static bool CanApplySelected()
    {
        return Selection.activeObject is TextAsset &&
            AssetDatabase.GetAssetPath(Selection.activeObject) == ManifestPath;
    }

    private static string DiskPath(string assetPath)
    {
        if (!assetPath.StartsWith("Assets/", StringComparison.Ordinal) ||
            assetPath.Contains("..") || assetPath.Contains("\\"))
            throw new InvalidOperationException("UNSAFE_ASSET_PATH");
        return Path.Combine(Directory.GetParent(Application.dataPath).FullName,
            assetPath.Replace('/', Path.DirectorySeparatorChar));
    }

    private static string HashFile(string assetPath)
    {
        using (var sha = SHA256.Create())
        using (var stream = File.OpenRead(DiskPath(assetPath)))
        {
            var result = new StringBuilder(64);
            foreach (byte value in sha.ComputeHash(stream)) result.Append(value.ToString("x2"));
            return result.ToString();
        }
    }

    private static Task ReadTask(string manifestPath)
    {
        if (manifestPath != ManifestPath || AssetDatabase.LoadAssetAtPath<TextAsset>(manifestPath) == null)
            throw new InvalidOperationException("MANIFEST_UNAVAILABLE");
        Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(DiskPath(manifestPath)));
        if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
            manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length != 1)
            throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
        Task task = manifest.reference_rebind_tasks[0];
        if (task == null || task.kind != TaskKind ||
            !Regex.IsMatch(task.export_object_id ?? "", @"^VAPB-OBJ-[0-9a-f]{32}$") ||
            !Regex.IsMatch(task.model_guid ?? "", @"^[0-9a-f]{32}$") ||
            !Regex.IsMatch(task.model_sha256 ?? "", @"^[0-9a-f]{64}$") ||
            task.prefab_path != "Assets/VAPBExport/Generated_" +
                task.export_object_id.Substring("VAPB-OBJ-".Length) + ".prefab" ||
            task.materials == null || task.materials.Length == 0 ||
            task.material_slots == null || task.material_slots.Length == 0)
            throw new InvalidOperationException("TASK_UNSUPPORTED");
        return task;
    }

    internal static bool IsAuthorizedExportObject(string modelPath, string exportId)
    {
        try
        {
            Task task = ReadTask(ManifestPath);
            return task.export_object_id == exportId &&
                AssetDatabase.GUIDToAssetPath(task.model_guid) == modelPath &&
                HashFile(modelPath) == task.model_sha256;
        }
        catch { return false; }
    }

    private static Material[] ResolveMaterials(Task task, List<ReferenceResult> references)
    {
        var byId = new Dictionary<string, Material>(StringComparer.Ordinal);
        foreach (MaterialRecord record in task.materials)
        {
            if (record == null ||
                !Regex.IsMatch(record.export_material_id ?? "", @"^VAPB-MAT-[0-9a-f]{32}$") ||
                !Regex.IsMatch(record.guid ?? "", @"^[0-9a-f]{32}$") ||
                !long.TryParse(record.file_id, out long fileId) || !byId.TryAdd(record.export_material_id, null))
                throw new InvalidOperationException("MATERIAL_ID_INVALID");
            string path = AssetDatabase.GUIDToAssetPath(record.guid);
            if (string.IsNullOrEmpty(path) || !path.EndsWith(".mat", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("MATERIAL_NOT_FOUND");
            Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material,
                    out string actualGuid, out long actualId) || actualGuid != record.guid || actualId != fileId)
                throw new InvalidOperationException("MATERIAL_ID_MISMATCH");
            ValidateDependencies(record, material, path, references);
            byId[record.export_material_id] = material;
        }
        var result = new Material[task.material_slots.Length];
        var used = new HashSet<int>();
        foreach (SlotRecord slot in task.material_slots)
        {
            if (slot == null || slot.slot_index < 0 || slot.slot_index >= result.Length ||
                !used.Add(slot.slot_index) || !byId.TryGetValue(slot.export_material_id ?? "", out Material material))
                throw new InvalidOperationException("MATERIAL_SLOT_INVALID");
            result[slot.slot_index] = material;
        }
        if (used.Count != result.Length)
            throw new InvalidOperationException("MATERIAL_SLOT_INVALID");
        return result;
    }

    private static void ValidateDependencies(MaterialRecord record, Material material, string path,
        List<ReferenceResult> references)
    {
        // Older Standard-only recipes had no dependency records. Keep that
        // bounded route; new recipes must pass every explicit identity check.
        if (record.shader == null && record.textures == null && string.IsNullOrEmpty(record.asset_sha256))
        {
            if (material.shader == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material.shader,
                out string legacyGuid, out long legacyId) || legacyGuid != "0000000000000000f000000000000000" || legacyId != 46)
                throw new InvalidOperationException("LEGACY_SHADER_UNSUPPORTED");
            return;
        }
        if (!Regex.IsMatch(record.asset_sha256 ?? "", @"^[0-9a-f]{64}$") ||
            HashFile(path) != record.asset_sha256)
            throw new InvalidOperationException("MATERIAL_REVISION_MISMATCH");
        ShaderRecord shader = record.shader;
        bool missingShader = false;
        if (shader != null && shader.classification == "UNRESOLVED_BUT_PRESERVED")
        {
            if (shader.kind != "SHADER" || shader.status != "UNRESOLVED_BUT_PRESERVED" ||
                !Regex.IsMatch(shader.guid ?? "", @"^[0-9a-f]{32}$") ||
                shader.guid == new string('0', 32) || !long.TryParse(shader.file_id, out long deferredId) || deferredId == 0 ||
                shader.reference_id != ReferenceId(shader.guid, deferredId))
                throw new InvalidOperationException("INVALID_REFERENCE");
            Shader exact = null;
            string providerPath = AssetDatabase.GUIDToAssetPath(shader.guid);
            if (!string.IsNullOrEmpty(providerPath))
                foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(providerPath))
                    if (asset is Shader candidate && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(candidate,
                        out string candidateGuid, out long candidateId) && candidateGuid == shader.guid && candidateId == deferredId)
                    {
                        if (exact != null) throw new InvalidOperationException("AMBIGUOUS_REFERENCE");
                        exact = candidate;
                    }
            missingShader = exact == null;
            if (!missingShader)
            {
                // Reimport reads the preserved serialized reference. Do not
                // regenerate or serialize a replacement Material from preview.
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                if (material.shader != exact || !exact.isSupported || ShaderUtil.ShaderHasError(exact))
                    throw new InvalidOperationException("SHADER_DEPENDENCY_UNRESOLVED");
            }
            references.Add(new ReferenceResult { reference_id = shader.reference_id, kind = shader.kind,
                guid = shader.guid, file_id = shader.file_id,
                status = missingShader ? "EXTERNAL_DEPENDENCY_REQUIRED" : "RESOLVED_IN_UNITY" });
        }
        else if (shader == null || (shader.classification != "UNITY_BUILTIN" &&
                shader.classification != "PACKAGE_PROVIDER") ||
            material.shader == null || !material.shader.isSupported ||
            ShaderUtil.ShaderHasError(material.shader) ||
            !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material.shader, out string guid, out long id) ||
            guid != shader.guid || !long.TryParse(shader.file_id, out long expectedId) || id != expectedId)
            throw new InvalidOperationException("SHADER_DEPENDENCY_UNRESOLVED");
        if (record.textures == null) throw new InvalidOperationException("TEXTURE_DEPENDENCIES_MISSING");
        var properties = new HashSet<string>(StringComparer.Ordinal);
        foreach (TextureRecord reference in record.textures)
        {
            if (reference == null || string.IsNullOrEmpty(reference.property_name) ||
                !properties.Add(reference.property_name) ||
                !Regex.IsMatch(reference.guid ?? "", @"^[0-9a-f]{32}$") ||
                !long.TryParse(reference.file_id, out long textureId))
                throw new InvalidOperationException("TEXTURE_REFERENCE_INVALID");
            string texturePath = AssetDatabase.GUIDToAssetPath(reference.guid);
            Texture found = null;
            if (!string.IsNullOrEmpty(texturePath))
                foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(texturePath))
                    if (asset is Texture texture && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture,
                        out string actualGuid, out long actualId) && actualGuid == reference.guid && actualId == textureId)
                    {
                        if (found != null) throw new InvalidOperationException("TEXTURE_ID_NOT_UNIQUE");
                        found = texture;
                    }
            if (found == null || (!missingShader && material.HasProperty(reference.property_name) &&
                    material.GetTexture(reference.property_name) != found))
                throw new InvalidOperationException("TEXTURE_DEPENDENCY_UNRESOLVED");
            // A saved property absent from this Shader is still retained in
            // the exact source .mat and its Texture asset must resolve.
        }
    }

    private static string ReferenceId(string guid, long fileId)
    {
        using (var sha = SHA256.Create())
        {
            var result = new StringBuilder();
            foreach (byte value in sha.ComputeHash(Encoding.UTF8.GetBytes("SHADER:" + guid + ":" +
                fileId.ToString(System.Globalization.CultureInfo.InvariantCulture)))) result.Append(value.ToString("x2"));
            return "VAPB-REF-" + result.ToString().Substring(0, 32);
        }
    }

    private static bool Finish(List<ReferenceResult> references)
    {
        LastReferences = references.ToArray();
        bool partial = references.Exists(reference => reference.status == "EXTERNAL_DEPENDENCY_REQUIRED");
        LastResult = partial ? "PARTIAL" : "COMPLETE";
        if (partial) Debug.LogWarning("VAPB_FINAL_STATE_PARTIAL=EXTERNAL_DEPENDENCY_REQUIRED MATERIAL=ATTACHED");
        else Debug.Log("VAPB_FINAL_STATE_APPLIED=1");
        return !partial;
    }

    public static bool Apply(string manifestPath)
    {
        LastResult = "REJECTED";
        LastReferences = new ReferenceResult[0];
        try
        {
            Task task = ReadTask(manifestPath);
            string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            if (string.IsNullOrEmpty(modelPath) ||
                !modelPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) ||
                HashFile(modelPath) != task.model_sha256)
                throw new InvalidOperationException("MODEL_REVISION_MISMATCH");
            var references = new List<ReferenceResult>();
            Material[] materials = ResolveMaterials(task, references);
            // The initial package import can precede its manifest. Reimport after
            // authorization so the user-property callback can persist the ID.
            AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null) throw new InvalidOperationException("MODEL_UNAVAILABLE");
            VapbExportObjectMarker[] markers = model.GetComponentsInChildren<VapbExportObjectMarker>(true);
            if (markers.Length != 1 || markers[0].exportObjectId != task.export_object_id)
                throw new InvalidOperationException("EXPORT_OBJECT_ID_NOT_UNIQUE");
            MeshRenderer renderer = markers[0].GetComponent<MeshRenderer>();
            MeshFilter filter = markers[0].GetComponent<MeshFilter>();
            if (renderer == null || filter == null || filter.sharedMesh == null ||
                renderer.sharedMaterials.Length != materials.Length ||
                renderer.GetComponents<Renderer>().Length != 1)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");

            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(task.prefab_path);
            if (existing != null)
            {
                VapbExportObjectMarker[] old = existing.GetComponentsInChildren<VapbExportObjectMarker>(true);
                if (old.Length != 1 || old[0].exportObjectId != task.export_object_id ||
                    old[0].GetComponent<MeshRenderer>() == null ||
                    !SameMaterials(old[0].GetComponent<MeshRenderer>().sharedMaterials, materials))
                    throw new InvalidOperationException("PREFAB_ALREADY_DIFFERS");
                return Finish(references);
            }
            GameObject instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
            if (instance == null) throw new InvalidOperationException("MODEL_INSTANCE_FAILED");
            try
            {
                PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                VapbExportObjectMarker[] targets = instance.GetComponentsInChildren<VapbExportObjectMarker>(true);
                if (targets.Length != 1 || targets[0].exportObjectId != task.export_object_id)
                    throw new InvalidOperationException("INSTANCE_ID_MISMATCH");
                targets[0].GetComponent<MeshRenderer>().sharedMaterials = materials;
                if (PrefabUtility.SaveAsPrefabAsset(instance, task.prefab_path) == null)
                    throw new InvalidOperationException("PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
            return Finish(references);
        }
        catch (Exception exception)
        {
            Debug.LogError("VAPB_FINAL_STATE_REJECTED=" + exception.Message);
            return false;
        }
    }

    private static bool SameMaterials(Material[] left, Material[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++)
            if (left[i] != right[i]) return false;
        return true;
    }
}
