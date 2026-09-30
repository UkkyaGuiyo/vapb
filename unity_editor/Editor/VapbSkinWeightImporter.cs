// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// First-party public API helper. Only exact generated Skin revisions opt in.
public sealed class VapbSkinWeightImporter : AssetPostprocessor
{
    [Serializable] private sealed class Policy { public int version; public string model_guid, model_sha256; }
    public override int GetPostprocessOrder() { return 1000; }
    private void OnPreprocessModel()
    {
        string guid = AssetDatabase.AssetPathToGUID(assetPath);
        if(String.IsNullOrEmpty(guid)) return;
        string policyPath = "Assets/VAPBExport/SkinWeightPolicy_" + guid + ".json";
        if(!File.Exists(policyPath)) return;
        Policy policy = JsonUtility.FromJson<Policy>(File.ReadAllText(policyPath));
        string digest;
        using(var sha = SHA256.Create())
            digest = BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(assetPath))).Replace("-", "").ToLowerInvariant();
        if(policy == null || policy.version != 1 || policy.model_guid != guid || policy.model_sha256 != digest)
            throw new InvalidOperationException("VAPB_SKIN_WEIGHT_REVISION_MISMATCH");
        var importer = (ModelImporter)assetImporter;
        importer.skinWeights = ModelImporterSkinWeights.Custom;
        importer.maxBonesPerVertex = 255;
        // The post-import getter clamps to .001 in 2022.3.22f1. Set at this stage
        // on every import; stored .meta or a setter after import is insufficient.
        importer.minBoneWeight = 0;
    }
}
