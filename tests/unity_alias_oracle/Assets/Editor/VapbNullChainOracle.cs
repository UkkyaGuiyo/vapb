// Public synthetic, read-only Unity 2022.3.22f1 source-chain observation.
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable] public sealed class VapbNullChainResult {
    public string unityVersion;
    public string variantGuid;
    public string sourceGuid;
    public string immediateRendererGuid;
    public string immediateRendererFileId;
    public string originalRendererGuid;
    public string originalRendererFileId;
    public string sourceOwnerGuid;
    public string sourceOwnerFileId;
    public string meshGuid;
    public string meshFileId;
    public string modelAssetPath;
    public string nearestInstanceAssetPath;
    public string rendererType;
    public int finalSlotCount;
    public bool finalNull;
    public Vector3 localPosition;
    public Quaternion localRotation;
    public Vector3 localScale;
}

public static class VapbNullChainOracle {
    const string VariantPath = "Assets/Oracle/Null_Override.prefab";
    const string SourcePath = "Assets/Oracle/Null_Source.prefab";

    static void Identity(Object value, out string guid, out string fileId) {
        long signedId;
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out guid, out signedId))
            throw new InvalidOperationException("Asset identity unavailable");
        fileId = signedId.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var output = Environment.GetEnvironmentVariable("VAPB_CHAIN_OUTPUT");
            if (String.IsNullOrEmpty(output)) throw new InvalidOperationException("Output required");
            var root = PrefabUtility.LoadPrefabContents(VariantPath);
            try {
                var renderer = root.GetComponent<MeshRenderer>();
                var filter = root.GetComponent<MeshFilter>();
                if (renderer == null || filter == null || filter.sharedMesh == null)
                    throw new InvalidOperationException("Expanded Renderer/Mesh missing");
                var immediate = PrefabUtility.GetCorrespondingObjectFromSource(renderer);
                var original = PrefabUtility.GetCorrespondingObjectFromOriginalSource(renderer);
                if (immediate == null || original == null)
                    throw new InvalidOperationException("Prefab Renderer source missing");
                var result = new VapbNullChainResult {
                    unityVersion = Application.unityVersion,
                    variantGuid = AssetDatabase.AssetPathToGUID(VariantPath),
                    sourceGuid = AssetDatabase.AssetPathToGUID(SourcePath),
                    modelAssetPath = AssetDatabase.GetAssetPath(filter.sharedMesh),
                    nearestInstanceAssetPath = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(renderer),
                    rendererType = renderer.GetType().Name,
                    finalSlotCount = renderer.sharedMaterials.Length,
                    finalNull = renderer.sharedMaterials.Length == 1 && renderer.sharedMaterials[0] == null,
                    localPosition = root.transform.localPosition,
                    localRotation = root.transform.localRotation,
                    localScale = root.transform.localScale,
                };
                Identity(immediate, out result.immediateRendererGuid, out result.immediateRendererFileId);
                Identity(original, out result.originalRendererGuid, out result.originalRendererFileId);
                Identity(original.gameObject, out result.sourceOwnerGuid, out result.sourceOwnerFileId);
                Identity(filter.sharedMesh, out result.meshGuid, out result.meshFileId);
                if (result.immediateRendererGuid != result.sourceGuid ||
                    result.originalRendererGuid != result.sourceGuid ||
                    result.meshGuid != AssetDatabase.AssetPathToGUID(result.modelAssetPath) ||
                    !result.finalNull)
                    throw new InvalidOperationException("Public source-chain mismatch");
                File.WriteAllText(output, JsonUtility.ToJson(result, true));
                Debug.Log("VAPB_NULL_CHAIN_PASS");
            } finally {
                PrefabUtility.UnloadPrefabContents(root);
            }
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_NULL_CHAIN_FAIL " + error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }
}
