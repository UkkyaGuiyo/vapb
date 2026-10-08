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
    private const string TaskKind = "BUILD_EXPORTED_STATIC_V2";
    private const string ReexportRequiredPrefix = "FINAL_STATE_REEXPORT_REQUIRED:";
    private const string ReexportRequiredMessage = ReexportRequiredPrefix +
        " This package predates material identity transport. Re-export the final-state package from Blender, then import the new package. Existing assets were not rewritten.";
    [Serializable] private sealed class Manifest
    {
        public string schema_version;
        public Task[] reference_rebind_tasks;
    }
    [Serializable] private sealed class Task
    {
        public string kind;
        public int material_transport_version;
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
        public string slot_index;
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
        string json = File.ReadAllText(DiskPath(manifestPath));
        Manifest manifest = JsonUtility.FromJson<Manifest>(json);
        if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
            manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length != 1)
            throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
        Task task = manifest.reference_rebind_tasks[0];
        if (task != null && task.kind == "BUILD_EXPORTED_STATIC_V1")
            throw new InvalidOperationException(ReexportRequiredMessage);
        ValidateV2Task(task);
        return task;
    }

    private static void ValidateV2Task(Task task)
    {
        if (task == null || task.kind != TaskKind || task.material_transport_version != 2 ||
            !Regex.IsMatch(task.export_object_id ?? "", @"\AVAPB-OBJ-[0-9a-f]{32}\z") ||
            !Regex.IsMatch(task.model_guid ?? "", @"\A[0-9a-f]{32}\z") ||
            !Regex.IsMatch(task.model_sha256 ?? "", @"\A[0-9a-f]{64}\z") ||
            task.prefab_path != "Assets/VAPBExport/Generated_" +
                task.export_object_id.Substring("VAPB-OBJ-".Length) + ".prefab" ||
            task.materials == null || task.materials.Length == 0 ||
            task.material_slots == null || task.material_slots.Length == 0)
            throw new InvalidOperationException("TASK_UNSUPPORTED");
        var declared = new HashSet<string>(StringComparer.Ordinal);
        foreach (MaterialRecord record in task.materials)
        {
            if (record == null ||
                !Regex.IsMatch(record.export_material_id ?? "", @"\AVAPB-MAT-[0-9a-f]{32}\z") ||
                !declared.Add(record.export_material_id) ||
                !Regex.IsMatch(record.guid ?? "", @"\A[0-9a-f]{32}\z") ||
                !long.TryParse(record.file_id, out _) ||
                !Regex.IsMatch(record.asset_sha256 ?? "", @"\A[0-9a-f]{64}\z") ||
                record.shader == null || record.textures == null)
                throw new InvalidOperationException("MATERIAL_DECLARATION_INVALID");
        }
        var used = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < task.material_slots.Length; i++)
        {
            SlotRecord slot = task.material_slots[i];
            if (slot == null || slot.slot_index != i.ToString(System.Globalization.CultureInfo.InvariantCulture) ||
                !declared.Contains(slot.export_material_id ?? ""))
                throw new InvalidOperationException("MATERIAL_SLOT_INVALID");
            used.Add(slot.export_material_id);
        }
        if (!used.SetEquals(declared))
            throw new InvalidOperationException("MATERIAL_DECLARATION_UNUSED");
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
                !Regex.IsMatch(record.export_material_id ?? "", @"\AVAPB-MAT-[0-9a-f]{32}\z") ||
                !Regex.IsMatch(record.guid ?? "", @"\A[0-9a-f]{32}\z") ||
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
        var result = new Material[task.materials.Length];
        for (int i = 0; i < task.materials.Length; i++)
            result[i] = byId[task.materials[i].export_material_id];
        return result;
    }

    private static int[] ResolveNativeMaterialOrder(Task task, string[] nativeLabels, int subMeshCount)
    {
        ValidateV2Task(task);
        if (nativeLabels == null || nativeLabels.Length != task.material_slots.Length ||
            nativeLabels.Length != subMeshCount)
            throw new InvalidOperationException("NATIVE_MATERIAL_CARDINALITY_MISMATCH");
        var materialIndexes = new Dictionary<string, int>(StringComparer.Ordinal);
        for (int i = 0; i < task.materials.Length; i++)
            materialIndexes.Add(task.materials[i].export_material_id, i);
        var expectedCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (SlotRecord slot in task.material_slots)
        {
            expectedCounts.TryGetValue(slot.export_material_id, out int count);
            expectedCounts[slot.export_material_id] = count + 1;
        }
        var actualCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        var result = new int[nativeLabels.Length];
        for (int i = 0; i < nativeLabels.Length; i++)
        {
            string label = nativeLabels[i];
            if (!Regex.IsMatch(label ?? "", @"\AVAPB-MAT-[0-9a-f]{32}\z") ||
                !materialIndexes.TryGetValue(label, out result[i]))
                throw new InvalidOperationException("NATIVE_MATERIAL_LABEL_INVALID");
            actualCounts.TryGetValue(label, out int count);
            actualCounts[label] = count + 1;
        }
        if (expectedCounts.Count != actualCounts.Count)
            throw new InvalidOperationException("NATIVE_MATERIAL_MULTIPLICITY_MISMATCH");
        foreach (var expected in expectedCounts)
            if (!actualCounts.TryGetValue(expected.Key, out int count) || count != expected.Value)
                throw new InvalidOperationException("NATIVE_MATERIAL_MULTIPLICITY_MISMATCH");
        return result;
    }

    private static void ValidateDependencies(MaterialRecord record, Material material, string path,
        List<ReferenceResult> references)
    {
        if (record.shader == null || record.textures == null ||
            !Regex.IsMatch(record.asset_sha256 ?? "", @"\A[0-9a-f]{64}\z") ||
            HashFile(path) != record.asset_sha256)
            throw new InvalidOperationException("MATERIAL_REVISION_MISMATCH");
        ShaderRecord shader = record.shader;
        bool missingShader = false;
        if (shader != null && shader.classification == "UNRESOLVED_BUT_PRESERVED")
        {
            if (shader.kind != "SHADER" || shader.status != "UNRESOLVED_BUT_PRESERVED" ||
                !Regex.IsMatch(shader.guid ?? "", @"\A[0-9a-f]{32}\z") ||
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
                !Regex.IsMatch(reference.guid ?? "", @"\A[0-9a-f]{32}\z") ||
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
            Material[] materialsById = ResolveMaterials(task, references);
            // V2 carrier names are the only native identity channel. Persist the
            // importer setting and complete reimport before reading its Mesh.
            ModelImporter importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("MODEL_IMPORTER_UNAVAILABLE");
            importer.materialName = ModelImporterMaterialName.BasedOnMaterialName;
            // Only this hash-validated generated static model uses the export unit policy.
            importer.useFileScale = true;
            importer.SaveAndReimport();
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null) throw new InvalidOperationException("MODEL_UNAVAILABLE");
            VapbExportObjectMarker[] markers = model.GetComponentsInChildren<VapbExportObjectMarker>(true);
            if (markers.Length != 1 || markers[0].exportObjectId != task.export_object_id)
                throw new InvalidOperationException("EXPORT_OBJECT_ID_NOT_UNIQUE");
            MeshRenderer renderer = markers[0].GetComponent<MeshRenderer>();
            MeshFilter filter = markers[0].GetComponent<MeshFilter>();
            if (renderer == null || filter == null || filter.sharedMesh == null ||
                renderer.GetComponents<Renderer>().Length != 1)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
            Material[] nativeMaterials = renderer.sharedMaterials;
            if (nativeMaterials == null) throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
            var nativeLabels = new string[nativeMaterials.Length];
            for (int i = 0; i < nativeMaterials.Length; i++)
            {
                if (nativeMaterials[i] == null)
                    throw new InvalidOperationException("NATIVE_MATERIAL_LABEL_INVALID");
                nativeLabels[i] = nativeMaterials[i].name;
            }
            int[] nativeOrder = ResolveNativeMaterialOrder(task, nativeLabels,
                filter.sharedMesh.subMeshCount);
            var materials = new Material[nativeOrder.Length];
            for (int i = 0; i < nativeOrder.Length; i++)
                materials[i] = materialsById[nativeOrder[i]];

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
            if (exception.Message.StartsWith(ReexportRequiredPrefix, StringComparison.Ordinal))
                LastResult = "FINAL_STATE_REEXPORT_REQUIRED";
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
