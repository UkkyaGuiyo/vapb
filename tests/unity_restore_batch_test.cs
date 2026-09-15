using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class UnityRestoreBatchTest
{
    public static void Run()
    {
        try
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            const string fbxPath = "Assets/TestAvatar.fbx";
            const string materialPath = "Assets/OriginalBody.mat";
            EnsureMaterial(materialPath, "Body");
            EnsureMaterial("Assets/AmbiguousOne.mat", "Ambiguous");
            EnsureMaterial("Assets/AmbiguousTwo.mat", "Ambiguous");
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);

            Material original = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (original == null)
                throw new Exception("Original test Material did not import");

            string materialFile = ProjectAssetToDiskPath(materialPath);
            string materialMeta = materialFile + ".meta";
            byte[] materialBefore = File.ReadAllBytes(materialFile);
            byte[] materialMetaBefore = File.ReadAllBytes(materialMeta);
            string template = File.ReadAllText(ProjectAssetToDiskPath("Assets/TestAvatar.materialmap.json"));
            string guid = AssetDatabase.AssetPathToGUID(materialPath);

            WriteManifest(template, guid, materialPath, "Body");
            Debug.Log("UNITY_TEST_GUID=" + guid + " PATH=" + AssetDatabase.GUIDToAssetPath(guid));
            Debug.Log("UNITY_TEST_MANIFEST=" + File.ReadAllText(ProjectAssetToDiskPath("Assets/TestAvatar.materialmap.json")));
            Assert(UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "GUID restore failed");
            AssertMappedTo(fbxPath, original);
            int materialCountAfterFirst = AssetDatabase.FindAssets("t:Material").Length;

            Assert(UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "Idempotent restore failed");
            Assert(AssetDatabase.FindAssets("t:Material").Length == materialCountAfterFirst, "Material count changed on repeat restore");
            AssertMappedTo(fbxPath, original);

            RemoveBodyRemap(fbxPath);
            WriteManifest(template, "00000000000000000000000000000000", materialPath, "Body");
            Assert(UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "Path fallback restore failed");
            AssertMappedTo(fbxPath, original);

            RemoveBodyRemap(fbxPath);
            File.WriteAllText(
                ProjectAssetToDiskPath("Assets/TestAvatar.materialmap.json"),
                template.Replace("\"schema_version\": 1", "\"schema_version\": 99"));
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            Assert(!UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "Invalid schema was accepted");

            WriteManifest(template, "missing-guid", "Assets/Missing.mat", "Missing");
            Assert(!UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "Missing material was incorrectly resolved");

            WriteManifest(template, "", "", "Ambiguous");
            Assert(!UnityPackageBlenderMaterialRestore.RestoreAtPath(fbxPath), "Ambiguous material was incorrectly resolved");

            Assert(ByteArraysEqual(materialBefore, File.ReadAllBytes(materialFile)), "Original .mat changed");
            Assert(ByteArraysEqual(materialMetaBefore, File.ReadAllBytes(materialMeta)), "Original .mat.meta changed");
            Debug.Log("UNITY_RESTORE_BATCH_OK");
            EditorApplication.Exit(0);
        }
        catch (Exception exception)
        {
            Debug.LogException(exception);
            EditorApplication.Exit(1);
        }
    }

    private static void EnsureMaterial(string path, string name)
    {
        Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null)
        {
            material = new Material(Shader.Find("Standard"));
            AssetDatabase.CreateAsset(material, path);
        }
        material.name = name;
        EditorUtility.SetDirty(material);
        AssetDatabase.SaveAssets();
    }

    private static void WriteManifest(string template, string guid, string path, string name)
    {
        string content = template
            .Replace("\"unity_material_guid\": \"PLACEHOLDER\"", "\"unity_material_guid\": \"" + guid + "\"")
            .Replace("\"unity_material_path\": \"PLACEHOLDER_PATH\"", "\"unity_material_path\": \"" + path + "\"")
            .Replace("\"unity_material_name\": \"PLACEHOLDER_NAME\"", "\"unity_material_name\": \"" + name + "\"");
        File.WriteAllText(ProjectAssetToDiskPath("Assets/TestAvatar.materialmap.json"), content);
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
    }

    private static void RemoveBodyRemap(string fbxPath)
    {
        AssetImporter importer = AssetImporter.GetAtPath(fbxPath);
        importer.RemoveRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "Body"));
        importer.SaveAndReimport();
    }

    private static void AssertMappedTo(string fbxPath, Material expected)
    {
        AssetImporter importer = AssetImporter.GetAtPath(fbxPath);
        foreach (var pair in importer.GetExternalObjectMap())
        {
            if (pair.Value == expected)
                return;
        }
        throw new Exception("FBX importer external object map did not contain the original Material");
    }

    private static string ProjectAssetToDiskPath(string assetPath)
    {
        string relative = assetPath.Substring("Assets".Length).TrimStart('/', '\\');
        return Path.Combine(Application.dataPath, relative);
    }

    private static bool ByteArraysEqual(byte[] first, byte[] second)
    {
        if (first.Length != second.Length)
            return false;
        for (int index = 0; index < first.Length; index++)
        {
            if (first[index] != second[index])
                return false;
        }
        return true;
    }

    private static void Assert(bool condition, string message)
    {
        if (!condition)
            throw new Exception(message);
    }
}
