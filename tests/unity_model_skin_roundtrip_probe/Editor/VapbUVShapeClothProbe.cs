using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Public synthetic negative control: temporarily add per-vertex Cloth state, then restore bytes.
public static class VapbUVShapeClothProbe
{
    [Serializable] private class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private class Task { public string prefab_guid, prefab_source_sha256, variant_path; }
    [Serializable] private class Report
    {
        public bool pass;
        public string error;
        public bool clothAdded, clothRejected, variantUnchanged, prefabRestored, testAssetRemoved;
    }
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string NegativePath = "Assets/VAPBExport/ClothNegativeManifest.json";
    private static bool rejectedForCloth;
    private static void ObserveLog(string condition, string stack, LogType type)
    {
        if (condition == "VAPB_MODEL_SKIN_VARIANT_REJECTED=CLOTH_INDEX_STATE_UNSUPPORTED")
            rejectedForCloth = true;
    }
    private static string Disk(string path) => Path.Combine(Directory.GetParent(Application.dataPath).FullName,
        path.Replace('/', Path.DirectorySeparatorChar));
    private static string Hash(byte[] bytes)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
    public static void Run()
    {
        var report = new Report();
        string prefabPath = null;
        byte[] original = null, originalMeta = null, variantBytes = null, variantMeta = null;
        bool listenerAttached = false;
        try
        {
            string originalText = File.ReadAllText(Disk(ManifestPath));
            Task task = JsonUtility.FromJson<Manifest>(originalText).reference_rebind_tasks.Single();
            prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            if (String.IsNullOrEmpty(prefabPath) || AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path) == null ||
                File.Exists(Disk(NegativePath)) || File.Exists(Disk(NegativePath) + ".meta"))
                throw new InvalidOperationException("FIXTURE_UNAVAILABLE");
            original = File.ReadAllBytes(Disk(prefabPath));
            originalMeta = File.ReadAllBytes(Disk(prefabPath) + ".meta");
            variantBytes = File.ReadAllBytes(Disk(task.variant_path));
            variantMeta = File.ReadAllBytes(Disk(task.variant_path) + ".meta");
            if (Hash(original) != task.prefab_source_sha256)
                throw new InvalidOperationException("FIXTURE_SOURCE_CHANGED");
            GameObject contents = PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                SkinnedMeshRenderer skin = contents.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                if (skin.GetComponent<Cloth>() != null) throw new InvalidOperationException("CLOTH_ALREADY_PRESENT");
                skin.gameObject.AddComponent<Cloth>();
                if (PrefabUtility.SaveAsPrefabAsset(contents, prefabPath) == null)
                    throw new InvalidOperationException("CLOTH_SAVE_FAILED");
            }
            finally { PrefabUtility.UnloadPrefabContents(contents); }
            AssetDatabase.ImportAsset(prefabPath, ImportAssetOptions.ForceUpdate);
            report.clothAdded = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath)
                .GetComponentsInChildren<Cloth>(true).Length == 1;
            string newHash = Hash(File.ReadAllBytes(Disk(prefabPath)));
            if (!report.clothAdded || newHash == task.prefab_source_sha256 ||
                originalText.Split(new[] { task.prefab_source_sha256 }, StringSplitOptions.None).Length < 2)
                throw new InvalidOperationException("CLOTH_SAVE_UNVERIFIED");
            File.WriteAllText(Disk(NegativePath),
                originalText.Replace(task.prefab_source_sha256, newHash));
            AssetDatabase.ImportAsset(NegativePath, ImportAssetOptions.ForceUpdate);
            rejectedForCloth = false;
            Application.logMessageReceived += ObserveLog;
            listenerAttached = true;
            bool applied = VapbModelSkinFinalizer.Apply(NegativePath);
            Application.logMessageReceived -= ObserveLog;
            listenerAttached = false;
            report.clothRejected = !applied && rejectedForCloth;
            report.variantUnchanged = variantBytes.SequenceEqual(File.ReadAllBytes(Disk(task.variant_path))) &&
                variantMeta.SequenceEqual(File.ReadAllBytes(Disk(task.variant_path) + ".meta"));
        }
        catch (Exception error)
        {
            report.error = error is InvalidOperationException &&
                (error.Message == "FIXTURE_UNAVAILABLE" || error.Message == "FIXTURE_SOURCE_CHANGED" ||
                 error.Message == "CLOTH_ALREADY_PRESENT" || error.Message == "CLOTH_SAVE_FAILED" ||
                 error.Message == "CLOTH_SAVE_UNVERIFIED") ? error.Message : "UNEXPECTED_EXCEPTION";
        }
        finally
        {
            if (listenerAttached) Application.logMessageReceived -= ObserveLog;
            try
            {
                if (prefabPath != null && original != null && originalMeta != null)
                {
                    File.WriteAllBytes(Disk(prefabPath), original);
                    File.WriteAllBytes(Disk(prefabPath) + ".meta", originalMeta);
                    AssetDatabase.ImportAsset(prefabPath, ImportAssetOptions.ForceUpdate);
                    report.prefabRestored = original.SequenceEqual(File.ReadAllBytes(Disk(prefabPath))) &&
                        originalMeta.SequenceEqual(File.ReadAllBytes(Disk(prefabPath) + ".meta"));
                }
                if (File.Exists(Disk(NegativePath)) || File.Exists(Disk(NegativePath) + ".meta"))
                    AssetDatabase.DeleteAsset(NegativePath);
                report.testAssetRemoved = !File.Exists(Disk(NegativePath)) &&
                    !File.Exists(Disk(NegativePath) + ".meta");
            }
            catch { report.error = "RESTORE_FAILED"; }
        }
        report.pass = report.clothAdded && report.clothRejected && report.variantUnchanged &&
            report.prefabRestored && report.testAssetRemoved;
        try
        {
            File.WriteAllText(Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                "UVShapeClothResult.json"), JsonUtility.ToJson(report, true));
        }
        catch { EditorApplication.Exit(1); return; }
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
