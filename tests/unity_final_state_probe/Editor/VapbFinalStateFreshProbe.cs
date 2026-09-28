using System;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Public-only fresh Unity project acceptance for replacement Mesh + selected Material.
[InitializeOnLoad]
public static class VapbFinalStateFreshProbe
{
    private const string Phase = "VAPB_FINAL_STATE_PHASE";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string export_object_id;
        public string model_guid;
        public string prefab_path;
        public MaterialRecord[] materials;
    }
    [Serializable] private sealed class MaterialRecord { public string guid; }

    static VapbFinalStateFreshProbe()
    {
        AssetDatabase.importPackageCompleted += OnComplete;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }

    public static void Run()
    {
        try
        {
            string path = Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                "Output.unitypackage");
            if (Application.unityVersion != "2022.3.22f1" || !File.Exists(path))
                throw new InvalidOperationException("FRESH_ENVIRONMENT_MISSING");
            SessionState.SetString(Phase, "importing");
            AssetDatabase.ImportPackage(path, false);
        }
        catch (Exception error) { Fail(error.Message); }
    }

    public static void RunMutations()
    {
        string project = Directory.GetParent(Application.dataPath).FullName;
        string manifestFile = Path.Combine(Application.dataPath, "VAPBExport/manifest.json");
        string originalManifest = File.ReadAllText(manifestFile);
        Manifest manifest = JsonUtility.FromJson<Manifest>(originalManifest);
        Task task = manifest.reference_rebind_tasks[0];
        string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
        string modelFile = Path.Combine(project, modelPath.Replace('/', Path.DirectorySeparatorChar));
        byte[] originalModel = File.ReadAllBytes(modelFile);
        string prefabFile = Path.Combine(project,
            task.prefab_path.Replace('/', Path.DirectorySeparatorChar));
        byte[] prefabBefore = File.ReadAllBytes(prefabFile);
        try
        {
            foreach (string mode in new[] { "missing", "duplicate", "renamed" })
            {
                byte[] mutant = File.ReadAllBytes(Path.Combine(project, "Mutant_" + mode + ".fbx"));
                string hash;
                using (SHA256 sha = SHA256.Create())
                    hash = BitConverter.ToString(sha.ComputeHash(mutant)).Replace("-", "").ToLowerInvariant();
                string oldHash = JsonUtility.FromJson<HashManifest>(originalManifest)
                    .reference_rebind_tasks[0].model_sha256;
                File.WriteAllBytes(modelFile, mutant);
                File.WriteAllText(manifestFile, originalManifest.Replace(oldHash, hash));
                AssetDatabase.ImportAsset(ManifestPath, ImportAssetOptions.ForceUpdate);
                AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceUpdate);
                bool accepted = VapbFinalStateFinalizer.Apply(ManifestPath);
                if (accepted != (mode == "renamed"))
                    throw new InvalidOperationException("OBJECT_ID_CONTROL_" + mode);
                Restore(modelFile, originalModel, manifestFile, originalManifest, modelPath);
            }
            int slotStart = originalManifest.IndexOf("\"material_slots\":[{\"export_material_id\":\"",
                StringComparison.Ordinal);
            if (slotStart < 0) throw new InvalidOperationException("SLOT_MANIFEST_MISSING");
            int slotIdAt = originalManifest.IndexOf("VAPB-MAT-", slotStart, StringComparison.Ordinal);
            string materialId = originalManifest.Substring(slotIdAt, 41);
            string unknownId = "VAPB-MAT-00000000000000000000000000000000";
            string missingMat = originalManifest.Remove(slotIdAt, materialId.Length)
                .Insert(slotIdAt, unknownId);
            File.WriteAllText(manifestFile, missingMat);
            AssetDatabase.ImportAsset(ManifestPath, ImportAssetOptions.ForceUpdate);
            if (VapbFinalStateFinalizer.Apply(ManifestPath))
                throw new InvalidOperationException("MISSING_MAT_ID_ACCEPTED");
            File.WriteAllText(manifestFile, originalManifest.Replace("\"slot_index\":0", "\"slot_index\":99"));
            AssetDatabase.ImportAsset(ManifestPath, ImportAssetOptions.ForceUpdate);
            if (VapbFinalStateFinalizer.Apply(ManifestPath))
                throw new InvalidOperationException("BAD_SLOT_ACCEPTED");
            Restore(modelFile, originalModel, manifestFile, originalManifest, modelPath);
            string matPath = AssetDatabase.GUIDToAssetPath(task.materials[0].guid);
            string matFile = Path.Combine(project, matPath.Replace('/', Path.DirectorySeparatorChar));
            byte[] matData = File.ReadAllBytes(matFile);
            byte[] matMeta = File.ReadAllBytes(matFile + ".meta");
            try
            {
                if (!AssetDatabase.DeleteAsset(matPath))
                    throw new InvalidOperationException("MATERIAL_DELETE_FAILED");
                if (VapbFinalStateFinalizer.Apply(ManifestPath))
                    throw new InvalidOperationException("MISSING_MATERIAL_ACCEPTED");
            }
            finally
            {
                File.WriteAllBytes(matFile, matData);
                File.WriteAllBytes(matFile + ".meta", matMeta);
                AssetDatabase.ImportAsset(matPath, ImportAssetOptions.ForceUpdate);
            }
            if (!Same(prefabBefore, File.ReadAllBytes(prefabFile)) ||
                !VapbFinalStateFinalizer.Apply(ManifestPath))
                throw new InvalidOperationException("RESTORE_OR_PREFAB_CHANGED");
            Debug.Log("VAPB_FINAL_STATE_MUTATIONS_PASS");
            EditorApplication.Exit(0);
        }
        catch (Exception error)
        {
            Debug.LogError("VAPB_FINAL_STATE_MUTATIONS_FAIL=" + error.Message);
            EditorApplication.Exit(1);
        }
        finally { Restore(modelFile, originalModel, manifestFile, originalManifest, modelPath); }
    }

    [Serializable] private sealed class HashManifest { public HashTask[] reference_rebind_tasks; }
    [Serializable] private sealed class HashTask { public string model_sha256; }
    private static void Restore(string modelFile, byte[] modelBytes, string manifestFile,
        string manifestText, string modelPath)
    {
        File.WriteAllBytes(modelFile, modelBytes);
        File.WriteAllText(manifestFile, manifestText);
        AssetDatabase.ImportAsset(ManifestPath, ImportAssetOptions.ForceUpdate);
        AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceUpdate);
    }
    private static bool Same(byte[] left, byte[] right)
    {
        if (left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }

    private static void OnComplete(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "completed");
        EditorApplication.delayCall += ValidateImported;
    }
    private static void OnFailed(string name, string reason)
    { if (SessionState.GetString(Phase, "") == "importing") Fail("IMPORT_FAILED"); }
    private static void OnCancelled(string name)
    { if (SessionState.GetString(Phase, "") == "importing") Fail("IMPORT_CANCELLED"); }

    public static void ValidateImported()
    {
        if (SessionState.GetString(Phase, "") != "completed") return;
        SessionState.SetString(Phase, "validating");
        try
        {
            string json = File.ReadAllText(Path.Combine(Application.dataPath,
                "VAPBExport/manifest.json"));
            Manifest manifest = JsonUtility.FromJson<Manifest>(json);
            if (manifest.reference_rebind_tasks.Length != 1)
                throw new InvalidOperationException("TASK_COUNT");
            Task task = manifest.reference_rebind_tasks[0];
            if (!VapbFinalStateFinalizer.Apply(ManifestPath))
                throw new InvalidOperationException("APPLY_FAILED");
            if (!VapbFinalStateFinalizer.Apply(ManifestPath))
                throw new InvalidOperationException("IDEMPOTENCE_FAILED");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(task.prefab_path);
            if (prefab == null) throw new InvalidOperationException("PREFAB_MISSING");
            VapbExportObjectMarker[] markers = prefab.GetComponentsInChildren<VapbExportObjectMarker>(true);
            if (markers.Length != 1 || markers[0].exportObjectId != task.export_object_id)
                throw new InvalidOperationException("PREFAB_EXPORT_ID");
            MeshFilter filter = markers[0].GetComponent<MeshFilter>();
            MeshRenderer renderer = markers[0].GetComponent<MeshRenderer>();
            if (filter == null || filter.sharedMesh == null ||
                filter.sharedMesh.vertexCount != 24 || filter.sharedMesh.uv.Length != 24 ||
                renderer == null || renderer.sharedMaterials.Length != 1)
                throw new InvalidOperationException("REPLACEMENT_MESH_INVALID");
            string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            if (modelPath != "Assets/VAPBExport/Generated_" +
                    task.export_object_id.Substring("VAPB-OBJ-".Length) + ".fbx")
                throw new InvalidOperationException("NEW_MODEL_GUID_INVALID");
            Material material = renderer.sharedMaterial;
            if (material == null ||
                AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(material)) != task.materials[0].guid ||
                material.mainTexture == null)
                throw new InvalidOperationException("MATERIAL_TEXTURE_INVALID");
            if (AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/VapbFinalState" }).Length != 0 ||
                AssetDatabase.FindAssets("t:Model", new[] { "Assets/VapbFinalState" }).Length != 0)
                throw new InvalidOperationException("SOURCE_ASSET_LEAKED");
            SessionState.SetString(Phase, "");
            Debug.Log("VAPB_FINAL_STATE_FRESH_PASS");
            EditorApplication.Exit(0);
        }
        catch (Exception error) { Fail(error.Message); }
    }

    private static void Fail(string reason)
    {
        SessionState.SetString(Phase, "");
        Debug.LogError("VAPB_FINAL_STATE_FRESH_FAIL=" + reason);
        EditorApplication.Exit(1);
    }
}
