// Public synthetic source-default, partial-override and transformed-parent oracle.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable]
public sealed class VapbTransformResult {
    public string unityVersion;
    public string sourceGuid;
    public string pairGuid;
    public string meshGuid;
    public string meshFileId;
    public float[] sourceLocal;
    public float[] parentLocal;
    public float[] aLocal;
    public float[] bLocal;
    public float[] aWorld;
    public float[] bWorld;
}

public static class VapbTransformOracle {
    const string SourcePath = "Assets/Oracle/Transform_Source.prefab";
    const string PairPath = "Assets/Oracle/Transform_TwoInstances.prefab";

    static float[] Flat(Matrix4x4 matrix) {
        var result = new float[16];
        for (var row = 0; row < 4; row++)
            for (var col = 0; col < 4; col++)
                result[row * 4 + col] = matrix[row, col];
        return result;
    }

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var resultPath = Environment.GetEnvironmentVariable("VAPB_TRANSFORM_RESULT_OUTPUT");
            var packagePath = Environment.GetEnvironmentVariable("VAPB_TRANSFORM_PACKAGE_OUTPUT");
            if (String.IsNullOrEmpty(resultPath) || String.IsNullOrEmpty(packagePath))
                throw new InvalidOperationException("Output required");
            var prior = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Oracle/Null_Source.prefab");
            if (prior == null) throw new InvalidOperationException("Public source missing");
            var mesh = prior.GetComponent<MeshFilter>().sharedMesh;
            var material = prior.GetComponent<MeshRenderer>().sharedMaterial;
            if (mesh == null || material == null) throw new InvalidOperationException("Public resources missing");
            string meshGuid;
            long meshId;
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out meshGuid, out meshId))
                throw new InvalidOperationException("Mesh identity missing");

            var source = new GameObject("Transform_Source");
            try {
                source.AddComponent<MeshFilter>().sharedMesh = mesh;
                source.AddComponent<MeshRenderer>().sharedMaterial = material;
                source.transform.localPosition = new Vector3(0.25f, -0.5f, 0.75f);
                source.transform.localRotation = Quaternion.Euler(15f, 30f, -10f);
                source.transform.localScale = new Vector3(1.2f, 0.8f, -1.1f);
                if (PrefabUtility.SaveAsPrefabAsset(source, SourcePath) == null)
                    throw new InvalidOperationException("Source save failed");
            } finally { Object.DestroyImmediate(source); }

            var sourceAsset = AssetDatabase.LoadAssetAtPath<GameObject>(SourcePath);
            var pair = new GameObject("Transform_TwoInstances");
            try {
                pair.transform.localPosition = new Vector3(2f, -1f, 3f);
                pair.transform.localRotation = Quaternion.Euler(0f, 20f, 10f);
                pair.transform.localScale = new Vector3(1.5f, 0.7f, 1.1f);
                var a = (GameObject)PrefabUtility.InstantiatePrefab(sourceAsset);
                var b = (GameObject)PrefabUtility.InstantiatePrefab(sourceAsset);
                a.transform.SetParent(pair.transform, false);
                b.transform.SetParent(pair.transform, false);
                a.transform.localPosition = new Vector3(10f, -0.5f, 0.75f);
                b.transform.localRotation = Quaternion.Euler(-12f, 35f, 22f);
                b.transform.localScale = new Vector3(1.2f, 1.4f, -1.1f);
                PrefabUtility.RecordPrefabInstancePropertyModifications(a.transform);
                PrefabUtility.RecordPrefabInstancePropertyModifications(b.transform);
                b.GetComponent<MeshRenderer>().sharedMaterials = new Material[] { null };
                PrefabUtility.RecordPrefabInstancePropertyModifications(b.GetComponent<MeshRenderer>());
                if (PrefabUtility.SaveAsPrefabAsset(pair, PairPath) == null)
                    throw new InvalidOperationException("Pair save failed");
            } finally { Object.DestroyImmediate(pair); }

            AssetDatabase.ImportAsset(PairPath, ImportAssetOptions.ForceUpdate);
            var loaded = PrefabUtility.LoadPrefabContents(PairPath);
            try {
                var renderers = loaded.GetComponentsInChildren<MeshRenderer>(true);
                if (renderers.Length != 2) throw new InvalidOperationException("Renderer count mismatch");
                var a = renderers.Single(item => item.sharedMaterials.Length == 1 && item.sharedMaterials[0] == material);
                var b = renderers.Single(item => item.sharedMaterials.Length == 1 && item.sharedMaterials[0] == null);
                if (PrefabUtility.GetCorrespondingObjectFromSource(a) !=
                    PrefabUtility.GetCorrespondingObjectFromSource(b))
                    throw new InvalidOperationException("Source Renderer mismatch");
                var result = new VapbTransformResult {
                    unityVersion = Application.unityVersion,
                    sourceGuid = AssetDatabase.AssetPathToGUID(SourcePath),
                    pairGuid = AssetDatabase.AssetPathToGUID(PairPath),
                    meshGuid = meshGuid,
                    meshFileId = meshId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    sourceLocal = Flat(Matrix4x4.TRS(sourceAsset.transform.localPosition,
                        sourceAsset.transform.localRotation, sourceAsset.transform.localScale)),
                    parentLocal = Flat(loaded.transform.localToWorldMatrix),
                    aLocal = Flat(Matrix4x4.TRS(a.transform.localPosition, a.transform.localRotation, a.transform.localScale)),
                    bLocal = Flat(Matrix4x4.TRS(b.transform.localPosition, b.transform.localRotation, b.transform.localScale)),
                    aWorld = Flat(a.transform.localToWorldMatrix),
                    bWorld = Flat(b.transform.localToWorldMatrix),
                };
                File.WriteAllText(resultPath, JsonUtility.ToJson(result, true));
            } finally { PrefabUtility.UnloadPrefabContents(loaded); }
            AssetDatabase.ExportPackage(new[] {
                "Assets/Oracle/Model.fbx", "Assets/Oracle/Materials/Base.mat", SourcePath, PairPath
            }, packagePath, ExportPackageOptions.Default);
            Debug.Log("VAPB_TRANSFORM_ORACLE_PASS");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_TRANSFORM_ORACLE_FAIL " + error.GetType().Name + " " + error.Message);
            EditorApplication.Exit(1);
        }
    }
}
