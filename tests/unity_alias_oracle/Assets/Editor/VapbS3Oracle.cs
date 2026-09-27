// Public synthetic S3: Unity authors an override, then removes its source Renderer.
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable] public sealed class VapbS3Result {
    public string unityVersion;
    public int activeBefore;
    public int sourceAfter;
    public int variantAfter;
    public int materialModificationsAfter;
    public bool targetLost;
}

public static class VapbS3Oracle {
    const string SourcePath = "Assets/Oracle/S3_Source.prefab";
    const string VariantPath = "Assets/Oracle/S3_Orphan.prefab";

    static void ObserveFinal(VapbS3Result result) {
        var finalSource = PrefabUtility.LoadPrefabContents(SourcePath);
        var finalVariant = PrefabUtility.LoadPrefabContents(VariantPath);
        try {
            result.sourceAfter = finalSource.GetComponentsInChildren<Renderer>(true).Length;
            result.variantAfter = finalVariant.GetComponentsInChildren<Renderer>(true).Length;
            var modifications = PrefabUtility.GetPropertyModifications(finalVariant);
            if (modifications != null)
                foreach (var modification in modifications)
                    if (modification.propertyPath == "m_Materials.Array.data[0]") {
                        result.materialModificationsAfter++;
                        if (modification.target == null) result.targetLost = true;
                    }
        } finally {
            PrefabUtility.UnloadPrefabContents(finalVariant);
            PrefabUtility.UnloadPrefabContents(finalSource);
        }
    }

    // Read-only check for the Unity-authored Prefabs committed with this oracle.
    public static void VerifyCommitted() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var result = new VapbS3Result { unityVersion=Application.unityVersion };
            ObserveFinal(result);
            if (result.sourceAfter != 0 || result.variantAfter != 0 ||
                result.materialModificationsAfter != 1 || !result.targetLost)
                throw new InvalidOperationException("Committed S3 expectations failed");
            Debug.Log("VAPB_S3_COMMITTED_OK final_renderers=0 retained_modification=1");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_S3_COMMITTED_FAIL " + error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var output = Environment.GetEnvironmentVariable("VAPB_S3_OUTPUT");
            if (string.IsNullOrEmpty(output)) throw new InvalidOperationException("Output required");
            if (AssetDatabase.LoadAssetAtPath<GameObject>(SourcePath) != null ||
                AssetDatabase.LoadAssetAtPath<GameObject>(VariantPath) != null)
                throw new InvalidOperationException("S3 must start without generated Prefabs");
            var baseMaterial = AssetDatabase.LoadAssetAtPath<Material>(
                "Assets/Oracle/Materials/Base.mat");
            var changedMaterial = AssetDatabase.LoadAssetAtPath<Material>(
                "Assets/Oracle/Materials/Changed.mat");
            if (baseMaterial == null || changedMaterial == null)
                throw new InvalidOperationException("Public synthetic Materials missing");

            var source = new GameObject("S3_Source");
            source.AddComponent<MeshFilter>();
            var sourceRenderer = source.AddComponent<MeshRenderer>();
            sourceRenderer.sharedMaterial = baseMaterial;
            var sourceAsset = PrefabUtility.SaveAsPrefabAsset(source, SourcePath);
            Object.DestroyImmediate(source);
            if (sourceAsset == null) throw new InvalidOperationException("Source save failed");

            var instance = (GameObject)PrefabUtility.InstantiatePrefab(sourceAsset);
            var instanceRenderer = instance.GetComponent<MeshRenderer>();
            instanceRenderer.sharedMaterial = changedMaterial;
            PrefabUtility.RecordPrefabInstancePropertyModifications(instanceRenderer);
            var result = new VapbS3Result { unityVersion=Application.unityVersion,
                activeBefore=instance.GetComponentsInChildren<Renderer>(true).Length };
            if (PrefabUtility.SaveAsPrefabAsset(instance, VariantPath) == null)
                throw new InvalidOperationException("Variant save failed");
            Object.DestroyImmediate(instance);

            var loadedSource = PrefabUtility.LoadPrefabContents(SourcePath);
            try {
                var renderer = loadedSource.GetComponent<MeshRenderer>();
                if (renderer == null) throw new InvalidOperationException("Source Renderer missing");
                Object.DestroyImmediate(renderer, true);
                if (PrefabUtility.SaveAsPrefabAsset(loadedSource, SourcePath) == null)
                    throw new InvalidOperationException("Source edit failed");
            } finally { PrefabUtility.UnloadPrefabContents(loadedSource); }
            AssetDatabase.ImportAsset(SourcePath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(VariantPath, ImportAssetOptions.ForceUpdate);

            ObserveFinal(result);
            AssetDatabase.SaveAssets();
            File.WriteAllText(output, JsonUtility.ToJson(result, true));
            if (result.activeBefore != 1 || result.sourceAfter != 0 ||
                result.variantAfter != 0 || result.materialModificationsAfter != 1)
                throw new InvalidOperationException("S3 expectations failed");
            Debug.Log("VAPB_S3_OK active_before=1 final_renderers=0 retained_modification=1");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_S3_FAIL " + error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }
}
