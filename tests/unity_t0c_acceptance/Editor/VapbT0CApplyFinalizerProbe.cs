using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>Runs the package's explicit ModelSkin finalizer on a disposable T0-C target.</summary>
public static class VapbT0CApplyFinalizerProbe
{
    private const string ExpectedPackageSha256 = "20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string ResultFileName = "VAPB_T0C_FinalizerApply_Result.json";

    [Serializable]
    private sealed class Manifest { public Task[] reference_rebind_tasks; }

    [Serializable]
    private sealed class Task
    {
        public string source_model_guid;
        public string source_model_sha256;
        public string model_guid;
        public string model_sha256;
        public string variant_path;
    }

    [Serializable]
    private sealed class Result
    {
        public string status = "FAIL";
        public string error;
        public string unity_version;
        public string package_sha256;
        public string manifest_sha256;
        public string source_model_guid;
        public string source_model_sha256_before;
        public string source_model_sha256_after;
        public string source_meta_sha256_before;
        public string source_meta_sha256_after;
        public string edited_model_guid;
        public string edited_model_sha256_before;
        public string edited_model_sha256_after;
        public string edited_meta_sha256_before;
        public string edited_meta_sha256_after;
        public string variant_path;
        public bool variant_absent_before_apply;
        public bool apply_returned_true;
        public bool variant_created;
        public bool source_files_restored;
    }

    public static void ApplyImportedManifest()
    {
        var result = new Result { unity_version = Application.unityVersion };
        string resultPath = Path.Combine(Directory.GetParent(Application.dataPath).FullName, ResultFileName);
        if (File.Exists(resultPath) || Directory.Exists(resultPath))
            throw new InvalidOperationException("Refusing to overwrite an existing Finalizer result");
        try
        {
            var packagePath = Environment.GetEnvironmentVariable("VAPB_T0C_PACKAGE");
            if (String.IsNullOrWhiteSpace(packagePath) || !File.Exists(packagePath))
                throw new InvalidOperationException("VAPB_T0C_PACKAGE is missing or not a file");
            result.package_sha256 = HashFile(packagePath);
            if (result.package_sha256 != ExpectedPackageSha256)
                throw new InvalidOperationException("Package SHA differs from the pinned T1 export");
            result.manifest_sha256 = HashFile(Disk(ManifestPath));

            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
            if (manifest == null || manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length != 1)
                throw new InvalidOperationException("Expected exactly one manifest rebind task");
            var task = manifest.reference_rebind_tasks[0];
            if (task == null || String.IsNullOrEmpty(task.source_model_guid) || String.IsNullOrEmpty(task.model_guid) ||
                String.IsNullOrEmpty(task.variant_path) || !task.variant_path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal))
                throw new InvalidOperationException("Manifest task identity or owned Variant path is invalid");

            result.source_model_guid = task.source_model_guid;
            result.edited_model_guid = task.model_guid;
            result.variant_path = task.variant_path;
            string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
            string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            if (String.IsNullOrEmpty(sourcePath) || String.IsNullOrEmpty(editedPath))
                throw new InvalidOperationException("Source or edited model GUID is not imported");
            if (HashFile(Disk(sourcePath)) != task.source_model_sha256 ||
                HashFile(Disk(editedPath)) != task.model_sha256)
                throw new InvalidOperationException("Imported source or edited model bytes differ from manifest");

            string variantDisk = Disk(task.variant_path);
            string variantFullPath = Path.GetFullPath(variantDisk);
            string exportFullPath = Path.GetFullPath(Disk("Assets/VAPBExport")) + Path.DirectorySeparatorChar;
            if (!variantFullPath.StartsWith(exportFullPath, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Variant destination escapes the package export folder");
            result.variant_absent_before_apply = !File.Exists(variantDisk) && !File.Exists(variantDisk + ".meta") &&
                !Directory.Exists(variantDisk) && !Directory.Exists(variantDisk + ".meta");
            if (!result.variant_absent_before_apply)
                throw new InvalidOperationException("Refusing to apply into an occupied Variant destination");

            result.source_model_sha256_before = HashFile(Disk(sourcePath));
            result.source_meta_sha256_before = HashFile(Disk(sourcePath) + ".meta");
            result.edited_model_sha256_before = HashFile(Disk(editedPath));
            result.edited_meta_sha256_before = HashFile(Disk(editedPath) + ".meta");
            result.apply_returned_true = VapbModelSkinFinalizer.Apply(ManifestPath);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            result.source_model_sha256_after = HashFile(Disk(sourcePath));
            result.source_meta_sha256_after = HashFile(Disk(sourcePath) + ".meta");
            result.edited_model_sha256_after = HashFile(Disk(editedPath));
            result.edited_meta_sha256_after = HashFile(Disk(editedPath) + ".meta");
            result.source_files_restored = result.source_model_sha256_before == result.source_model_sha256_after &&
                result.source_meta_sha256_before == result.source_meta_sha256_after;
            result.variant_created = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path) != null;
            if (!result.apply_returned_true)
                throw new InvalidOperationException("VapbModelSkinFinalizer.Apply returned false");
            if (!result.source_files_restored || !result.variant_created)
                throw new InvalidOperationException("Apply did not restore source bytes or create the expected Variant");
            result.status = "PASS";
            result.error = "NONE";
        }
        catch (Exception error)
        {
            result.error = error.GetType().Name + ": " + error.Message;
        }

        using (var stream = new FileStream(resultPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
            writer.Write(JsonUtility.ToJson(result, true));
        Debug.Log("VAPB_T0C_FINALIZER_APPLY_" + result.status + " " + JsonUtility.ToJson(result));
        if (result.status != "PASS")
            throw new InvalidOperationException(result.error ?? "T0-C Finalizer Apply probe failed");
    }

    private static string Disk(string assetPath)
    {
        if (String.IsNullOrEmpty(assetPath) || !assetPath.StartsWith("Assets/", StringComparison.Ordinal))
            throw new InvalidOperationException("Expected an Assets path");
        return Path.Combine(Directory.GetParent(Application.dataPath).FullName,
            assetPath.Replace('/', Path.DirectorySeparatorChar));
    }

    private static string HashFile(string path)
    {
        if (!File.Exists(path)) throw new FileNotFoundException("Expected file is missing", path);
        using (var sha = SHA256.Create())
        using (var stream = File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }
}
