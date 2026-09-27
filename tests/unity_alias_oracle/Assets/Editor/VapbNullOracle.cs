// Public synthetic explicit-null Material override, authored by Unity 2022.3.22f1.
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable] public sealed class VapbNullResult {
    public string unityVersion;
    public int sourceSlots;
    public bool sourceHasMaterial;
    public int variantSlots;
    public bool variantIsNull;
    public int nullModifications;
}

public static class VapbNullOracle {
    const string SourcePath = "Assets/Oracle/Null_Source.prefab";
    const string VariantPath = "Assets/Oracle/Null_Override.prefab";

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var output = Environment.GetEnvironmentVariable("VAPB_NULL_OUTPUT");
            if (string.IsNullOrEmpty(output)) throw new InvalidOperationException("Output required");
            var baseMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Oracle/Materials/Base.mat");
            if (baseMaterial == null) throw new InvalidOperationException("Public base Material missing");
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Oracle/NullMesh.asset");
            if (mesh == null) {
                mesh = new Mesh { name = "NullMesh" };
                mesh.vertices = new[] { Vector3.zero, Vector3.right, Vector3.up };
                mesh.triangles = new[] { 0, 1, 2 };
                AssetDatabase.CreateAsset(mesh, "Assets/Oracle/NullMesh.asset");
            }

            var source = new GameObject("Null_Source");
            source.AddComponent<MeshFilter>().sharedMesh = mesh;
            source.AddComponent<MeshRenderer>().sharedMaterial = baseMaterial;
            var sourceAsset = PrefabUtility.SaveAsPrefabAsset(source, SourcePath);
            Object.DestroyImmediate(source);
            if (sourceAsset == null) throw new InvalidOperationException("Source save failed");

            var instance = (GameObject)PrefabUtility.InstantiatePrefab(sourceAsset);
            var renderer = instance.GetComponent<MeshRenderer>();
            renderer.sharedMaterials = new Material[] { null };
            PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            if (PrefabUtility.SaveAsPrefabAsset(instance, VariantPath) == null)
                throw new InvalidOperationException("Variant save failed");
            Object.DestroyImmediate(instance);
            AssetDatabase.ImportAsset(SourcePath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(VariantPath, ImportAssetOptions.ForceUpdate);

            var expandedSource = PrefabUtility.LoadPrefabContents(SourcePath);
            var expandedVariant = PrefabUtility.LoadPrefabContents(VariantPath);
            var result = new VapbNullResult { unityVersion = Application.unityVersion };
            try {
                var baseSlots = expandedSource.GetComponent<MeshRenderer>().sharedMaterials;
                var variantSlots = expandedVariant.GetComponent<MeshRenderer>().sharedMaterials;
                result.sourceSlots = baseSlots.Length;
                result.sourceHasMaterial = baseSlots.Length == 1 && baseSlots[0] == baseMaterial;
                result.variantSlots = variantSlots.Length;
                result.variantIsNull = variantSlots.Length == 1 && variantSlots[0] == null;
                var modifications = PrefabUtility.GetPropertyModifications(expandedVariant);
                if (modifications != null)
                    foreach (var modification in modifications)
                        if (modification.propertyPath == "m_Materials.Array.data[0]" &&
                            modification.objectReference == null) result.nullModifications++;
            } finally {
                PrefabUtility.UnloadPrefabContents(expandedVariant);
                PrefabUtility.UnloadPrefabContents(expandedSource);
            }
            File.WriteAllText(output, JsonUtility.ToJson(result, true));
            if (result.sourceSlots != 1 || !result.sourceHasMaterial ||
                result.variantSlots != 1 || !result.variantIsNull || result.nullModifications != 1)
                throw new InvalidOperationException("Explicit-null observations failed");
            Debug.Log("VAPB_NULL_OK source_slot=1 variant_null=1 modification=1");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_NULL_FAIL " + error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }
}
