// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
using System;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Copy only this script into an empty project. Product helpers arrive in Output.unitypackage.
[InitializeOnLoad]
public static class VapbPhase2FreshProbe
{
    private const string Phase = "VAPB_PHASE2_FRESH_PHASE";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string export_object_id;
        public string model_guid;
        public string prefab_path;
    }
    // Expected.json is supplied independently from the original input fixture.
    // Local IDs are decimal strings, preserving signed 64-bit values.
    [Serializable] private sealed class Expected
    {
        public string material_guid;
        public string material_file_id;
        public string shader_guid;
        public string shader_file_id;
        public string texture_guid;
        public string texture_file_id;
        public string source_material_sha256;
    }

    static VapbPhase2FreshProbe()
    {
        AssetDatabase.importPackageCompleted += OnComplete;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }

    private static string Project { get { return Directory.GetParent(Application.dataPath).FullName; } }
    private static string Disk(string assetPath)
    {
        Require(!string.IsNullOrEmpty(assetPath) && assetPath.StartsWith("Assets/", StringComparison.Ordinal)
            && !assetPath.Contains("..") && !assetPath.Contains("\\"), "ASSET_PATH");
        return Path.Combine(Project, assetPath.Replace('/', Path.DirectorySeparatorChar));
    }

    public static void Run()
    {
        try
        {
            Require(Application.unityVersion == "2022.3.22f1", "VERSION");
            ReadExpected();
            string package = Path.Combine(Project, "Output.unitypackage");
            Require(File.Exists(package), "PACKAGE_MISSING");
            SessionState.SetString(Phase, "importing");
            AssetDatabase.ImportPackage(package, false);
        }
        catch { Fail("START"); }
    }

    public static void Diagnose()
    {
        try
        {
            Expected expected = ReadExpected();
            Material material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(expected.material_guid));
            string texturePath = AssetDatabase.GUIDToAssetPath(expected.texture_guid);
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(texturePath))
                if (AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id))
                    Debug.Log("VAPB_PHASE2_TEXTURE_ASSET=" + asset.GetType().Name + ":" + id + ":" + (guid == expected.texture_guid));
            foreach (string property in new[] { "_MainTex", "_FutureTexture" })
            {
                Texture texture = material.GetTexture(property);
                bool exists = texture != null;
                long id = 0;
                string guid = "";
                if (exists) AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out guid, out id);
                Debug.Log("VAPB_PHASE2_TEXTURE_BINDING=" + property + ":" + material.HasProperty(property)
                    + ":" + exists + ":" + id + ":" + (guid == expected.texture_guid));
            }
            EditorApplication.Exit(0);
        }
        catch { Fail("DIAGNOSE"); }
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
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        {
            EditorApplication.delayCall += ValidateImported;
            return;
        }
        SessionState.SetString(Phase, "validating");
        try
        {
            ValidatePositive();
            SessionState.SetString(Phase, "");
            Debug.Log("VAPB_PHASE2_FRESH_PASS");
            EditorApplication.Exit(0);
        }
        catch { Fail("VALIDATION"); }
    }

    private static Expected ReadExpected()
    {
        Expected expected = JsonUtility.FromJson<Expected>(File.ReadAllText(Path.Combine(Project, "Expected.json")));
        Require(expected != null && !string.IsNullOrEmpty(expected.material_guid)
            && !string.IsNullOrEmpty(expected.shader_guid) && !string.IsNullOrEmpty(expected.texture_guid)
            && expected.source_material_sha256 != null && expected.source_material_sha256.Length == 64,
            "EXPECTED_MISSING");
        ParseId(expected.material_file_id);
        ParseId(expected.shader_file_id);
        ParseId(expected.texture_file_id);
        return expected;
    }

    private static Task ReadTask()
    {
        Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
        Require(manifest != null && manifest.reference_rebind_tasks != null
            && manifest.reference_rebind_tasks.Length == 1 && manifest.reference_rebind_tasks[0] != null,
            "TASK_COUNT");
        return manifest.reference_rebind_tasks[0];
    }

    private static bool Apply()
    {
        Type helper = null;
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type candidate = assembly.GetType("VapbFinalStateFinalizer", false);
            if (candidate == null) continue;
            Require(helper == null, "HELPER_DUPLICATE");
            helper = candidate;
        }
        Require(helper != null, "PRODUCT_HELPER_MISSING");
        MethodInfo method = helper.GetMethod("Apply", BindingFlags.Public | BindingFlags.Static,
            null, new[] { typeof(string) }, null);
        Require(method != null && method.ReturnType == typeof(bool), "PRODUCT_APPLY_MISSING");
        return (bool)method.Invoke(null, new object[] { ManifestPath });
    }

    private static void ValidatePositive()
    {
        Require(Application.unityVersion == "2022.3.22f1", "VERSION");
        Expected expected = ReadExpected();
        Task task = ReadTask();
        string materialFile = Disk(AssetDatabase.GUIDToAssetPath(expected.material_guid));
        byte[] materialBytes = File.ReadAllBytes(materialFile);
        byte[] materialMeta = File.ReadAllBytes(materialFile + ".meta");
        Require(Hash(materialBytes) == expected.source_material_sha256, "SOURCE_MATERIAL_HASH");
        Require(Apply(), "APPLY_FAILED");
        byte[] prefabBytes = File.ReadAllBytes(Disk(task.prefab_path));
        Require(Apply(), "SECOND_APPLY_FAILED");
        Require(Same(prefabBytes, File.ReadAllBytes(Disk(task.prefab_path))), "PREFAB_CHANGED");
        Require(Same(materialBytes, File.ReadAllBytes(materialFile))
            && Same(materialMeta, File.ReadAllBytes(materialFile + ".meta")), "SOURCE_MATERIAL_CHANGED");

        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(task.prefab_path);
        Require(prefab != null, "PREFAB_MISSING");
        Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
        MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true);
        Require(renderers.Length == 1 && renderers[0] is MeshRenderer && filters.Length == 1
            && filters[0].gameObject == renderers[0].gameObject && renderers[0].sharedMaterials.Length == 1,
            "PREFAB_STRUCTURE");
        Mesh mesh = filters[0].sharedMesh;
        Require(mesh != null && mesh.vertexCount == 24 && mesh.uv.Length == 24
            && mesh.subMeshCount == 1 && mesh.triangles.Length == 36, "CUBE_MESH_UV");
        string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
        Require(!string.IsNullOrEmpty(task.export_object_id)
            && task.export_object_id.StartsWith("VAPB-OBJ-", StringComparison.Ordinal)
            && modelPath == "Assets/VAPBExport/Generated_" + task.export_object_id.Substring(9) + ".fbx"
            && AssetDatabase.GetAssetPath(mesh) == modelPath, "NEW_MODEL");
        Material material = renderers[0].sharedMaterial;
        Identity(material, expected.material_guid, expected.material_file_id);
        Identity(material.shader, expected.shader_guid, expected.shader_file_id);
        Require(material.shader.name != "Standard" && !ShaderUtil.ShaderHasError(material.shader), "SHADER_ERROR");
        foreach (string property in new[] { "_MainTex", "_FutureTexture" })
        {
            Require(material.HasProperty(property), "TEXTURE_PROPERTY");
            Identity(material.GetTexture(property), expected.texture_guid, expected.texture_file_id);
        }
    }

    // Optional separate executeMethod after the positive run; never repairs product state.
    public static void RunDependenciesNegative()
    {
        try
        {
            ValidatePositive();
            Expected expected = ReadExpected();
            Task task = ReadTask();
            byte[] prefab = File.ReadAllBytes(Disk(task.prefab_path));
            foreach (string guid in new[] { expected.texture_guid, expected.shader_guid })
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                string file = Disk(path);
                byte[] asset = File.ReadAllBytes(file);
                byte[] meta = File.ReadAllBytes(file + ".meta");
                try
                {
                    Require(AssetDatabase.DeleteAsset(path), "DEPENDENCY_DELETE");
                    Require(!Apply(), "MISSING_DEPENDENCY_ACCEPTED");
                    Require(Same(prefab, File.ReadAllBytes(Disk(task.prefab_path))), "NEGATIVE_PREFAB_CHANGED");
                }
                finally
                {
                    File.WriteAllBytes(file, asset);
                    File.WriteAllBytes(file + ".meta", meta);
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                }
            }
            ValidatePositive();
            Require(Same(prefab, File.ReadAllBytes(Disk(task.prefab_path))), "RESTORE_PREFAB_CHANGED");
            Debug.Log("VAPB_PHASE2_DEPENDENCIES_NEGATIVE_PASS");
            EditorApplication.Exit(0);
        }
        catch
        {
            Debug.LogError("VAPB_PHASE2_DEPENDENCIES_NEGATIVE_FAIL");
            EditorApplication.Exit(1);
        }
    }

    private static void Identity(UnityEngine.Object asset, string guid, string fileId)
    {
        Require(asset != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset,
            out string actualGuid, out long actualId) && actualGuid == guid && actualId == ParseId(fileId),
            "ASSET_IDENTITY");
    }
    private static long ParseId(string value)
    {
        Require(long.TryParse(value, out long id), "EXPECTED_FILE_ID");
        return id;
    }
    private static string Hash(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
    private static bool Same(byte[] left, byte[] right)
    {
        if (left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static void Require(bool condition, string code)
    { if (!condition) throw new InvalidOperationException(code); }
    private static void Fail(string code)
    {
        SessionState.SetString(Phase, "");
        Debug.LogError("VAPB_PHASE2_FRESH_FAIL=" + code);
        EditorApplication.Exit(1);
    }
}
