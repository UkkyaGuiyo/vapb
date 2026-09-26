using System;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Synthetic public-API fixture for a model instance inside a Prefab Variant.
public static class VapbModelInstanceFixture
{
    private const string Folder = "Assets/VapbModelInstance";
    private const string ModelPath = Folder + "/Input.fbx";
    private const string OtherModelPath = Folder + "/Other.fbx";
    private const string BasePath = Folder + "/Base.prefab";
    private const string VariantPath = Folder + "/Variant.prefab";

    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool package_exists;
        public bool variant_asset_type;
        public bool distinct_model_guids;
        public bool base_source_is_input;
        public bool variant_source_is_input;
        public int model_renderers;
        public int model_skins;
        public int model_bones;
        public int base_renderers;
        public int base_skins;
        public int base_bones;
        public int base_source_hops;
        public int base_instance_documents;
        public int base_direct_renderer_documents;
        public int variant_renderers;
        public int variant_skins;
        public int variant_bones;
        public int variant_source_hops;
        public int variant_instance_documents;
        public int variant_direct_renderer_documents;
    }

    public static void Prepare()
    {
        PrepareWithSkinCount(1);
    }

    public static void PrepareTwoSkins()
    {
        PrepareWithSkinCount(2);
    }

    private static void PrepareWithSkinCount(int expectedSkins)
    {
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        try
        {
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(OtherModelPath, ImportAssetOptions.ForceUpdate);
            report.distinct_model_guids = AssetDatabase.AssetPathToGUID(ModelPath) !=
                AssetDatabase.AssetPathToGUID(OtherModelPath);
            if (!report.distinct_model_guids ||
                AssetDatabase.LoadAssetAtPath<GameObject>(OtherModelPath) == null)
                throw new InvalidOperationException("SECOND_MODEL_UNAVAILABLE");
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            SkinnedMeshRenderer modelSkin = RepresentativeSkin(model, expectedSkins);
            if (modelSkin == null || modelSkin.sharedMesh == null || modelSkin.bones.Length < 2)
                throw new InvalidOperationException("INPUT_MODEL_UNSUPPORTED");
            report.model_renderers = CountRenderers(model);
            report.model_skins = CountSkins(model);
            report.model_bones = modelSkin.bones.Length;

            GameObject baseRoot = new GameObject("SyntheticBase");
            try
            {
                GameObject modelInstance = PrefabUtility.InstantiatePrefab(model) as GameObject;
                if (modelInstance == null)
                    throw new InvalidOperationException("MODEL_INSTANCE_FAILED");
                modelInstance.transform.SetParent(baseRoot.transform, false);
                if (PrefabUtility.SaveAsPrefabAsset(baseRoot, BasePath) == null)
                    throw new InvalidOperationException("BASE_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(baseRoot); }

            GameObject baseAsset = AssetDatabase.LoadAssetAtPath<GameObject>(BasePath);
            if (baseAsset == null)
                throw new InvalidOperationException("BASE_UNAVAILABLE");
            GameObject baseInstance = PrefabUtility.InstantiatePrefab(baseAsset) as GameObject;
            if (baseInstance == null)
                throw new InvalidOperationException("BASE_INSTANCE_FAILED");
            try
            {
                if (PrefabUtility.SaveAsPrefabAsset(baseInstance, VariantPath) == null)
                    throw new InvalidOperationException("VARIANT_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(baseInstance); }

            GameObject variant = AssetDatabase.LoadAssetAtPath<GameObject>(VariantPath);
            SkinnedMeshRenderer baseSkin = RepresentativeSkin(baseAsset, expectedSkins);
            SkinnedMeshRenderer variantSkin = RepresentativeSkin(variant, expectedSkins);
            if (baseSkin == null || variantSkin == null)
                throw new InvalidOperationException("PREFAB_SKIN_UNAVAILABLE");
            report.variant_asset_type = PrefabUtility.GetPrefabAssetType(variant) == PrefabAssetType.Variant;
            report.base_renderers = CountRenderers(baseAsset);
            report.base_skins = CountSkins(baseAsset);
            report.base_bones = baseSkin.bones.Length;
            report.base_source_hops = SourceHops(baseSkin);
            report.base_source_is_input = SourceLeafPath(baseSkin) == ModelPath;
            report.variant_renderers = CountRenderers(variant);
            report.variant_skins = CountSkins(variant);
            report.variant_bones = variantSkin.bones.Length;
            report.variant_source_hops = SourceHops(variantSkin);
            report.variant_source_is_input = SourceLeafPath(variantSkin) == ModelPath;
            report.base_instance_documents = DocumentCount(BasePath, 1001);
            report.base_direct_renderer_documents = DocumentCount(BasePath, 23) + DocumentCount(BasePath, 137);
            report.variant_instance_documents = DocumentCount(VariantPath, 1001);
            report.variant_direct_renderer_documents = DocumentCount(VariantPath, 23) + DocumentCount(VariantPath, 137);

            AssetDatabase.ExportPackage(new[] { BasePath, VariantPath, ModelPath, OtherModelPath },
                ProjectFile("Source.unitypackage"), ExportPackageOptions.IncludeDependencies);
            report.package_exists = File.Exists(ProjectFile("Source.unitypackage"));
            report.pass = report.package_exists && report.variant_asset_type && report.distinct_model_guids &&
                report.base_source_is_input && report.variant_source_is_input &&
                report.model_renderers == expectedSkins && report.model_skins == expectedSkins && report.model_bones >= 2 &&
                report.base_renderers == expectedSkins && report.base_skins == expectedSkins && report.base_bones == report.model_bones &&
                report.variant_renderers == expectedSkins && report.variant_skins == expectedSkins && report.variant_bones == report.model_bones &&
                report.base_source_hops == 1 && report.variant_source_hops == 2 &&
                report.base_instance_documents >= 1 && report.variant_instance_documents >= 1 &&
                report.base_direct_renderer_documents == 0 && report.variant_direct_renderer_documents == 0;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    private static SkinnedMeshRenderer RepresentativeSkin(GameObject root, int expectedSkins)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] renderers = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        // Fixture summary selection only; never a production identity join.
        return renderers.Length == expectedSkins ? renderers[0] : null;
    }

    private static int CountRenderers(GameObject root)
    {
        return root == null ? 0 : root.GetComponentsInChildren<Renderer>(true).Length;
    }

    private static int CountSkins(GameObject root)
    {
        return root == null ? 0 : root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length;
    }

    private static int SourceHops(UnityEngine.Object asset)
    {
        int count = 0;
        for (UnityEngine.Object current = asset; current != null && count < 16; )
        {
            UnityEngine.Object source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (source == null || source == current) break;
            count++;
            current = source;
        }
        return count;
    }

    private static string SourceLeafPath(UnityEngine.Object asset)
    {
        UnityEngine.Object current = asset;
        for (int depth = 0; current != null && depth < 16; depth++)
        {
            UnityEngine.Object source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (source == null || source == current) break;
            current = source;
        }
        return current == null ? "" : AssetDatabase.GetAssetPath(current);
    }

    private static int DocumentCount(string assetPath, int classId)
    {
        string text = File.ReadAllText(AssetFile(assetPath));
        return Regex.Matches(text, @"(?m)^--- !u!" + classId + @" &").Count;
    }

    private static string AssetFile(string path)
    {
        return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar));
    }

    private static string ProjectFile(string name)
    {
        return Path.Combine(Path.GetDirectoryName(Application.dataPath), name);
    }

    private static string SafeError(Exception error)
    {
        if (error is InvalidOperationException)
        {
            switch (error.Message)
            {
                case "INPUT_MODEL_UNSUPPORTED": case "MODEL_INSTANCE_FAILED": case "BASE_SAVE_FAILED":
                case "BASE_UNAVAILABLE": case "BASE_INSTANCE_FAILED": case "VARIANT_SAVE_FAILED":
                case "PREFAB_SKIN_UNAVAILABLE": case "SECOND_MODEL_UNAVAILABLE": return error.Message;
            }
        }
        return error.GetType().Name;
    }

    private static void Finish(Report report)
    {
        try { File.WriteAllText(ProjectFile("VapbModelInstanceFixtureResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_MODEL_INSTANCE_FIXTURE_PASS" : "VAPB_MODEL_INSTANCE_FIXTURE_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
