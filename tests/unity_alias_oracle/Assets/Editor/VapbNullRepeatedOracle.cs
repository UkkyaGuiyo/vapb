// Public synthetic nested Prefab with two occurrences of one source Renderer.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable] public sealed class VapbRepeatedResult {
    public string unityVersion;
    public string pairGuid;
    public string sourceGuid;
    public string sourceRendererFileId;
    public string meshGuid;
    public string meshFileId;
    public int rendererCount;
    public bool sameSourceRenderer;
    public bool sameMesh;
    public bool distinctInstanceRoots;
    public int materialASlots;
    public bool materialA;
    public int nullSlots;
    public bool explicitNull;
    public Vector3 materialALocalPosition;
    public Vector3 nullLocalPosition;
}

public static class VapbNullRepeatedOracle {
    const string PairPath = "Assets/Oracle/Null_TwoInstances.prefab";
    const string SourcePath = "Assets/Oracle/Null_Source.prefab";

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var resultPath = Environment.GetEnvironmentVariable("VAPB_PAIR_RESULT_OUTPUT");
            var packagePath = Environment.GetEnvironmentVariable("VAPB_PAIR_PACKAGE_OUTPUT");
            if (String.IsNullOrEmpty(resultPath) || String.IsNullOrEmpty(packagePath))
                throw new InvalidOperationException("Output required");
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(SourcePath);
            var baseMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Oracle/Materials/Base.mat");
            if (source == null || baseMaterial == null)
                throw new InvalidOperationException("Public source assets missing");
            var pair = new GameObject("Null_TwoInstances");
            try {
                var a = (GameObject)PrefabUtility.InstantiatePrefab(source);
                var b = (GameObject)PrefabUtility.InstantiatePrefab(source);
                a.transform.SetParent(pair.transform, false);
                b.transform.SetParent(pair.transform, false);
                a.transform.localPosition = new Vector3(-1, 0, 0);
                b.transform.localPosition = new Vector3(1, 0, 0);
                PrefabUtility.RecordPrefabInstancePropertyModifications(a.transform);
                PrefabUtility.RecordPrefabInstancePropertyModifications(b.transform);
                var bRenderer = b.GetComponent<MeshRenderer>();
                bRenderer.sharedMaterials = new Material[] { null };
                PrefabUtility.RecordPrefabInstancePropertyModifications(bRenderer);
                if (PrefabUtility.SaveAsPrefabAsset(pair, PairPath) == null)
                    throw new InvalidOperationException("Pair save failed");
            } finally {
                Object.DestroyImmediate(pair);
            }
            AssetDatabase.ImportAsset(PairPath, ImportAssetOptions.ForceUpdate);
            var loaded = PrefabUtility.LoadPrefabContents(PairPath);
            try {
                var renderers = loaded.GetComponentsInChildren<MeshRenderer>(true);
                if (renderers.Length != 2) throw new InvalidOperationException("Renderer count mismatch");
                var materialRenderer = renderers.Single(item => item.sharedMaterials.Length == 1 &&
                    item.sharedMaterials[0] == baseMaterial);
                var nullRenderer = renderers.Single(item => item.sharedMaterials.Length == 1 &&
                    item.sharedMaterials[0] == null);
                var materialSource = PrefabUtility.GetCorrespondingObjectFromSource(materialRenderer);
                var nullSource = PrefabUtility.GetCorrespondingObjectFromSource(nullRenderer);
                var materialMesh = materialRenderer.GetComponent<MeshFilter>().sharedMesh;
                var nullMesh = nullRenderer.GetComponent<MeshFilter>().sharedMesh;
                string sourceGuid;
                long sourceId;
                string meshGuid;
                long meshId;
                if (materialSource == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(materialSource, out sourceGuid, out sourceId)
                    || materialMesh == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(materialMesh, out meshGuid, out meshId))
                    throw new InvalidOperationException("Source identity unavailable");
                var result = new VapbRepeatedResult {
                    unityVersion = Application.unityVersion,
                    pairGuid = AssetDatabase.AssetPathToGUID(PairPath),
                    sourceGuid = sourceGuid,
                    sourceRendererFileId = sourceId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    meshGuid = meshGuid,
                    meshFileId = meshId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    rendererCount = renderers.Length,
                    sameSourceRenderer = materialSource == nullSource,
                    sameMesh = materialMesh == nullMesh,
                    distinctInstanceRoots = PrefabUtility.GetNearestPrefabInstanceRoot(materialRenderer) !=
                        PrefabUtility.GetNearestPrefabInstanceRoot(nullRenderer),
                    materialASlots = materialRenderer.sharedMaterials.Length,
                    materialA = materialRenderer.sharedMaterials[0] == baseMaterial,
                    nullSlots = nullRenderer.sharedMaterials.Length,
                    explicitNull = nullRenderer.sharedMaterials[0] == null,
                    materialALocalPosition = materialRenderer.transform.localPosition,
                    nullLocalPosition = nullRenderer.transform.localPosition,
                };
                if (result.sourceGuid != AssetDatabase.AssetPathToGUID(SourcePath)
                    || !result.sameSourceRenderer || !result.sameMesh || !result.distinctInstanceRoots
                    || !result.materialA || !result.explicitNull)
                    throw new InvalidOperationException("Repeated source observation failed");
                File.WriteAllText(resultPath, JsonUtility.ToJson(result, true));
            } finally {
                PrefabUtility.UnloadPrefabContents(loaded);
            }
            AssetDatabase.ExportPackage(new [] {
                "Assets/Oracle/Model.fbx", "Assets/Oracle/Materials/Base.mat",
                SourcePath, PairPath
            }, packagePath, ExportPackageOptions.Default);
            Debug.Log("VAPB_NULL_REPEATED_PASS");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_NULL_REPEATED_FAIL " + error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }
}
