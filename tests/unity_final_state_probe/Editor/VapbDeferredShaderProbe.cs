// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
using System;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Standalone fresh-project probe. Product helpers arrive ONLY in Output.unitypackage.
[InitializeOnLoad]
public static class VapbDeferredShaderProbe
{
    private const string Phase = "VAPB_DEFERRED_PROBE_PHASE";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task { public string prefab_path; public string model_guid; public string export_object_id; }
    [Serializable] private sealed class Expected
    {
        public string material_guid, material_file_id, shader_guid, shader_file_id;
        public string texture_guid, texture_file_id, source_material_sha256, reference_id;
    }
    static VapbDeferredShaderProbe()
    {
        AssetDatabase.importPackageCompleted += OnComplete;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        string state = SessionState.GetString(Phase, "");
        if (state == "output_ready" || state == "external_ready") EditorApplication.delayCall += Resume;
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
            Require(string.IsNullOrEmpty(AssetDatabase.GUIDToAssetPath(new string('3', 32))), "NOT_FRESH");
            SessionState.SetString(Phase, "output_importing");
            AssetDatabase.ImportPackage(Path.Combine(Project, "Output.unitypackage"), false);
        }
        catch (Exception e) { Fail(Code(e, "START")); }
    }
    private static void OnComplete(string name)
    {
        string state = SessionState.GetString(Phase, "");
        if (state == "output_importing") SessionState.SetString(Phase, "output_ready");
        else if (state == "external_importing") SessionState.SetString(Phase, "external_ready");
        else return;
        EditorApplication.delayCall += Resume;
    }
    private static void OnFailed(string name, string reason) { Fail("IMPORT_FAILED"); }
    private static void OnCancelled(string name) { Fail("IMPORT_CANCELLED"); }
    public static void Resume()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        { EditorApplication.delayCall += Resume; return; }
        string state = SessionState.GetString(Phase, "");
        if (state != "output_ready" && state != "external_ready") return;
        SessionState.SetString(Phase, "validating");
        try
        {
            if (state == "output_ready")
            {
                ValidatePartial();
                Debug.Log("VAPB_DEFERRED_PARTIAL_PASS");
                SessionState.SetString(Phase, "external_importing");
                AssetDatabase.ImportPackage(Path.Combine(Project, "ExternalShader.unitypackage"), false);
            }
            else
            {
                ValidateComplete();
                SessionState.SetString(Phase, "");
                Debug.Log("VAPB_DEFERRED_COMPLETE_PASS");
                EditorApplication.Exit(0);
            }
        }
        catch (Exception e) { Fail(Code(e, "VALIDATION")); }
    }
    private static Expected ReadExpected()
    {
        Expected expected = JsonUtility.FromJson<Expected>(File.ReadAllText(Path.Combine(Project, "Expected.json")));
        Require(expected != null && expected.material_guid == new string('1', 32)
            && expected.texture_guid == new string('2', 32) && expected.shader_guid == new string('3', 32)
            && expected.material_file_id == "2100000" && expected.texture_file_id == "2800000"
            && expected.shader_file_id == "4800000" && expected.source_material_sha256.Length == 64
            && expected.reference_id.StartsWith("VAPB-REF-", StringComparison.Ordinal), "EXPECTED_INVALID");
        return expected;
    }
    private static Task ReadTask()
    {
        Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
        Require(manifest != null && manifest.reference_rebind_tasks != null
            && manifest.reference_rebind_tasks.Length == 1, "TASK_COUNT");
        return manifest.reference_rebind_tasks[0];
    }
    private static Type Helper()
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
        return helper;
    }
    private static object Member(object target, string name)
    {
        Type type = target as Type ?? target.GetType();
        object instance = target is Type ? null : target;
        BindingFlags flags = BindingFlags.Public | (instance == null ? BindingFlags.Static : BindingFlags.Instance);
        FieldInfo field = type.GetField(name, flags);
        if (field != null) return field.GetValue(instance);
        PropertyInfo property = type.GetProperty(name, flags);
        Require(property != null, "PUBLIC_RESULT_API");
        return property.GetValue(instance, null);
    }
    private static void Apply(bool complete)
    {
        Type helper = Helper();
        MethodInfo method = helper.GetMethod("Apply", BindingFlags.Public | BindingFlags.Static,
            null, new[] { typeof(string) }, null);
        Require(method != null && method.ReturnType == typeof(bool), "APPLY_API");
        Require((bool)method.Invoke(null, new object[] { ManifestPath }) == complete, "APPLY_RETURN");
        Require((string)Member(helper, "LastResult") == (complete ? "COMPLETE" : "PARTIAL"), "LAST_RESULT");
        Array references = Member(helper, "LastReferences") as Array;
        Require(references != null && references.Length == 1, "REFERENCE_COUNT");
        object reference = references.GetValue(0);
        Expected expected = ReadExpected();
        Require((string)Member(reference, "reference_id") == expected.reference_id
            && (string)Member(reference, "kind") == "SHADER"
            && (string)Member(reference, "guid") == expected.shader_guid
            && (string)Member(reference, "file_id") == expected.shader_file_id
            && (string)Member(reference, "status") == (complete ? "RESOLVED_IN_UNITY" : "EXTERNAL_DEPENDENCY_REQUIRED"),
            "REFERENCE_RESULT");
    }
    private static Material ValidatePrefab()
    {
        Task task = ReadTask();
        Expected expected = ReadExpected();
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(task.prefab_path);
        Require(prefab != null, "PREFAB_MISSING");
        Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
        MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true);
        Require(renderers.Length == 1 && renderers[0] is MeshRenderer && filters.Length == 1
            && filters[0].gameObject == renderers[0].gameObject && renderers[0].sharedMaterials.Length == 1, "PREFAB_STRUCTURE");
        Mesh mesh = filters[0].sharedMesh;
        Require(mesh != null && mesh.vertexCount == 24 && mesh.uv.Length == 24
            && mesh.triangles.Length == 36 && mesh.subMeshCount == 1, "CUBE_MESH_UV");
        string model = AssetDatabase.GUIDToAssetPath(task.model_guid);
        Require(task.export_object_id.StartsWith("VAPB-OBJ-", StringComparison.Ordinal)
            && model == "Assets/VAPBExport/Generated_" + task.export_object_id.Substring(9) + ".fbx"
            && AssetDatabase.GetAssetPath(mesh) == model, "NEW_MODEL");
        Material material = renderers[0].sharedMaterial;
        Identity(material, expected.material_guid, expected.material_file_id);
        Identity(AssetDatabase.LoadAssetAtPath<Texture2D>(AssetDatabase.GUIDToAssetPath(expected.texture_guid)),
            expected.texture_guid, expected.texture_file_id);
        Require(Hash(File.ReadAllBytes(Disk(AssetDatabase.GUIDToAssetPath(expected.material_guid))))
            == expected.source_material_sha256, "MATERIAL_HASH");
        return material;
    }
    private static void ValidatePartial()
    {
        Expected expected = ReadExpected();
        Require(string.IsNullOrEmpty(AssetDatabase.GUIDToAssetPath(expected.shader_guid)), "SHADER_ALREADY_PRESENT");
        Apply(false);
        ValidatePrefab();
        Task task = ReadTask();
        string prefab = Disk(task.prefab_path);
        SessionState.SetString("VAPB_DEFERRED_PREFAB_HASH", Hash(File.ReadAllBytes(prefab)));
        SessionState.SetString("VAPB_DEFERRED_PREFAB_GUID", AssetDatabase.AssetPathToGUID(task.prefab_path));
        string material = Disk(AssetDatabase.GUIDToAssetPath(expected.material_guid));
        SessionState.SetString("VAPB_DEFERRED_MATERIAL_META", Hash(File.ReadAllBytes(material + ".meta")));
        // Same shader name and useful properties, deliberately wrong GUID: name matching must not resolve it.
        const string wrong = "Assets/VAPBWrong.shader";
        File.WriteAllText(Disk(wrong), "Shader \"VAPB/SyntheticUnlit\" { Properties { _MainTex (\"Main\", 2D) = \"white\" {} _FutureTexture (\"Future\", 2D) = \"white\" {} } SubShader { Pass {} } Fallback Off }");
        File.WriteAllText(Disk(wrong) + ".meta", "fileFormatVersion: 2\nguid: " + new string('4', 32) + "\nShaderImporter:\n  serializedVersion: 2\n");
        AssetDatabase.ImportAsset(wrong, ImportAssetOptions.ForceSynchronousImport);
        Require(AssetDatabase.LoadAssetAtPath<Shader>(wrong) != null, "WRONG_SHADER_IMPORT");
        Apply(false);
        ValidatePrefab();
        Unchanged();
        Require(AssetDatabase.DeleteAsset(wrong), "WRONG_SHADER_DELETE");
        Apply(false);
        Unchanged();
    }
    private static void ValidateComplete()
    {
        Apply(true);
        Material material = ValidatePrefab();
        Expected expected = ReadExpected();
        Identity(material.shader, expected.shader_guid, expected.shader_file_id);
        Require(!ShaderUtil.ShaderHasError(material.shader), "SHADER_ERROR");
        foreach (string property in new[] { "_MainTex", "_FutureTexture" })
        {
            Require(material.HasProperty(property), "TEXTURE_PROPERTY");
            Identity(material.GetTexture(property), expected.texture_guid, expected.texture_file_id);
        }
        Unchanged();
        Apply(true);
        Unchanged();
    }
    private static void Unchanged()
    {
        Task task = ReadTask();
        Expected expected = ReadExpected();
        Require(Hash(File.ReadAllBytes(Disk(task.prefab_path))) == SessionState.GetString("VAPB_DEFERRED_PREFAB_HASH", "")
            && AssetDatabase.AssetPathToGUID(task.prefab_path) == SessionState.GetString("VAPB_DEFERRED_PREFAB_GUID", ""), "PREFAB_CHANGED");
        string material = Disk(AssetDatabase.GUIDToAssetPath(expected.material_guid));
        Require(Hash(File.ReadAllBytes(material)) == expected.source_material_sha256
            && Hash(File.ReadAllBytes(material + ".meta")) == SessionState.GetString("VAPB_DEFERRED_MATERIAL_META", ""), "MATERIAL_CHANGED");
    }
    private static void Identity(UnityEngine.Object asset, string guid, string fileId)
    {
        Require(asset != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset,
            out string actualGuid, out long actualId) && actualGuid == guid && actualId.ToString() == fileId, "ASSET_IDENTITY");
    }
    private static string Hash(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
    private static void Require(bool condition, string code)
    { if (!condition) throw new InvalidOperationException(code); }
    // Only probe-defined fixed codes are surfaced; private exception text is never logged.
    private static string Code(Exception e, string fallback)
    {
        if (e is TargetInvocationException) return "PRODUCT_EXCEPTION";
        if (!(e is InvalidOperationException)) return fallback;
        string code = e.Message;
        foreach (char c in code) if (!(c >= 'A' && c <= 'Z') && c != '_') return fallback;
        return code;
    }
    private static void Fail(string code)
    {
        SessionState.SetString(Phase, "");
        Debug.LogError("VAPB_DEFERRED_FAIL=" + code);
        EditorApplication.Exit(1);
    }
}
