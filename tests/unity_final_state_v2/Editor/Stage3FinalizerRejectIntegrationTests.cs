// SPDX-License-Identifier: MIT
// Public synthetic integration tests for pre-save Apply rejection boundaries.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

[Parallelizable(ParallelScope.None)]
public sealed class Stage3FinalizerRejectIntegrationTests
{
    private const string RootEnvironment = "VAPB_STAGE3_TEST_ROOT";
    private const string RootMarker = ".vapb-stage3-owned-test-root";
    private const string TargetMarker = ".vapb-disposable-unity-test-project";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string FaultManifestPrefix = "Assets/VAPBExport/Stage3Reject_";
    private const string VariantPrefix = "Assets/VAPBExport/EditedVariant_Stage3Reject_";
    private static readonly string[] PriorVariants = {
        "Assets/VAPBExport/EditedVariant_Stage3V7_20261004.prefab",
        "Assets/VAPBExport/EditedVariant_Stage3V8_20261004.prefab",
        "Assets/VAPBExport/EditedVariant_Stage3V9_20261004.prefab",
        "Assets/VAPBExport/EditedVariant_Stage3V10_20261004.prefab"
    };

    [Test]
    public void ApplyRejectsWellFormedWrongSourceHashBeforeWitness()
    {
        RunRejectCase("SourceHash", "SOURCE_HASH_OR_PATH_MISMATCH", (json, variant) =>
        {
            string changed = ReplaceSingleField(json, "source_model_sha256", new string('0', 64));
            return SetVariantPath(changed, variant);
        }, false);
    }

    [Test]
    public void ApplyRejectsUnknownEditedBoneReceiptAfterWitnessRestore()
    {
        string editedModelPath = EditedModelPathFromManifest();
        string missingReceipt = "00000000-0000-4000-8000-00000000f001";
        string selectedReceipt = SelectExistingNonRootReceipt(editedModelPath);
        Assert.AreNotEqual(missingReceipt, selectedReceipt);

        RunRejectCase("EditedBoneReceipt", "EDITED_BONES_INVALID", (json, variant) =>
        {
            string changed = ReplaceFirstExactFieldValue(json, "edited_bone_realization_id",
                selectedReceipt, missingReceipt);
            return SetVariantPath(changed, variant);
        }, true);
    }

    private static void RunRejectCase(string label, string reason,
        Func<string, string, string> mutate, bool expectWitness)
    {
        Assert.AreEqual("2022.3.22f1", Application.unityVersion);
        string projectRoot = ProjectRoot();
        string testRoot = TestRoot();
        string expectedTarget = Path.Combine(testRoot, "TargetProject");
        Assert.AreEqual(Path.GetFullPath(expectedTarget), Path.GetFullPath(projectRoot),
            "Unity must be running the TargetProject under the owned run root.");
        Assert.IsTrue(File.Exists(Path.Combine(testRoot, RootMarker)), "owned run-root marker missing");
        Assert.AreEqual("VAPB_STAGE3_OWNED_TEST_ROOT_V1",
            File.ReadAllText(Path.Combine(testRoot, RootMarker)).Trim());
        Assert.IsTrue(File.Exists(Path.Combine(projectRoot, TargetMarker)), "disposable TargetProject marker missing");
        AssertNoReparsePoint(projectRoot);

        string faultManifest = FaultManifestPrefix + label + "_20261004.json";
        string variant = VariantPrefix + label + "_20261004.prefab";
        AssertPathAbsent(faultManifest);
        AssertVariantAbsent(variant);
        Assert.IsTrue(AssetDatabase.IsValidFolder("Assets/VAPBExport"), "VAPBExport folder missing");

        string[] before = Inventory();
        string[] evidenceBefore = EvidenceInventory();
        string canonical = File.ReadAllText(Disk(ManifestPath), Encoding.UTF8);
        string faultJson = mutate(canonical, variant);
        Assert.AreNotEqual(canonical, faultJson, "fault manifest must differ from canonical input");

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Disk(faultManifest)));
            using (var stream = new FileStream(Disk(faultManifest), FileMode.CreateNew, FileAccess.Write))
            {
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.Write(faultJson);
            }
            AssetDatabase.ImportAsset(faultManifest, ImportAssetOptions.ForceSynchronousImport);
            Assert.IsNotNull(AssetDatabase.LoadAssetAtPath<TextAsset>(faultManifest), "owned manifest copy was not imported");
            var protectedPaths = ProtectedPathsFromManifest();
            Dictionary<string, PathState> protectedBefore = CaptureStates(protectedPaths);
            PathState faultBefore = CaptureState(faultManifest);
            string[] inventoryBeforeApply = Inventory();
            string[] evidenceBeforeApply = EvidenceInventory();
            Assert.AreNotEqual("<absent>", faultBefore.payloadHash);
            Assert.AreNotEqual("<absent>", faultBefore.metaHash);

            Stage3RejectWitnessImportObserver.Reset(AssetDatabase.GUIDToAssetPath(FieldValue(canonical, "source_model_guid")));
            var messages = new List<string>();
            Application.LogCallback callback = (condition, stack, type) => messages.Add(condition);
            Application.logMessageReceived += callback;
            bool applied;
            try
            {
                LogAssert.Expect(LogType.Error, "VAPB_MODEL_SKIN_VARIANT_REJECTED=" + reason);
                MethodInfo apply = Finalizer().GetMethod("Apply", BindingFlags.Public | BindingFlags.Static);
                Assert.IsNotNull(apply, "public Finalizer.Apply(string) missing");
                applied = (bool)apply.Invoke(null, new object[] { faultManifest });
            }
            finally { Application.logMessageReceived -= callback; }

            Assert.IsFalse(applied, "fault manifest must be rejected");
            Assert.IsFalse(messages.Any(message => message.StartsWith(
                "VAPB_MODEL_SKIN_VARIANT_APPLIED=", StringComparison.Ordinal)), "Apply success log must not occur");
            CollectionAssert.Contains(messages, "VAPB_MODEL_SKIN_VARIANT_REJECTED=" + reason);
            if (expectWitness)
            {
                Assert.AreEqual(1, Stage3RejectWitnessImportObserver.WitnessTaggedImports,
                    "receipt fault must have one source witness import");
                string[] expectedHashes = {
                    FieldValue(canonical, "witness_noop_sha256"),
                    FieldValue(canonical, "witness_sha256"),
                    FieldValue(canonical, "source_model_sha256"),
                    FieldValue(canonical, "source_model_sha256")
                };
                CollectionAssert.AreEqual(expectedHashes, Stage3RejectWitnessImportObserver.SourceImportHashes,
                    "source import bytes must follow noop, witness, original restore, original metadata restore");
            }
            else
            {
                Assert.AreEqual(0, Stage3RejectWitnessImportObserver.WitnessTaggedImports,
                    "source hash mismatch must reject before witness import");
                Assert.AreEqual(0, Stage3RejectWitnessImportObserver.SourceImportHashes.Count,
                    "source hash mismatch must reject before any source import");
            }

            PathState variantAfterApply = CaptureState(variant);
            TestContext.WriteLine(label + " unexpectedVariantPayload=" + variantAfterApply.payloadHash +
                " meta=" + variantAfterApply.metaHash + " guid=" + variantAfterApply.guid +
                " loaded=" + variantAfterApply.loaded);
            AssertVariantAbsent(variant);
            AssertStatesEqual(protectedBefore, CaptureStates(protectedPaths));
            AssertStateEqual(faultBefore, CaptureState(faultManifest));
            CollectionAssert.AreEqual(inventoryBeforeApply, Inventory(),
                "Apply must not change existing Assets entries or create assets before rejection");
            CollectionAssert.AreEqual(evidenceBeforeApply, EvidenceInventory(),
                "Apply must leave V7-V10 result/evidence JSON unchanged");
            TestContext.WriteLine("V7ResultJson=" + EvidenceInventory().FirstOrDefault(line =>
                line.StartsWith("VapbModelSkinTopologyBoundaryReplacementV7Result.json ", StringComparison.Ordinal)) +
                "; V7VariantPrefab=" + (File.Exists(Disk(PriorVariants[0])) ? "present" : "absent"));
            TestContext.WriteLine(label + " rejected=" + reason + " witnessTaggedImports=" +
                Stage3RejectWitnessImportObserver.WitnessTaggedImports + " existingAssetsUnchanged=true variantAbsent=true");
        }
        finally
        {
            DeleteOwnedManifest(faultManifest);
            DeleteOwnedVariant(variant);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            CollectionAssert.AreEqual(before, Inventory(),
                "test cleanup must restore the complete pre-test Assets inventory");
            CollectionAssert.AreEqual(evidenceBefore, EvidenceInventory(),
                "test cleanup must leave all V7-V10 result/evidence JSON unchanged");
            AssertVariantAbsent(variant);
            Stage3RejectWitnessImportObserver.Reset(null);
        }
    }

    private static Type Finalizer()
    {
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type type = assembly.GetType("VapbModelSkinFinalizer", false);
            if (type != null) return type;
        }
        Assert.Fail("VapbModelSkinFinalizer is not loaded in an Editor assembly");
        return null;
    }

    private static string EditedModelPathFromManifest()
    {
        string json = File.ReadAllText(Disk(ManifestPath), Encoding.UTF8);
        string guid = FieldValue(json, "model_guid");
        string path = AssetDatabase.GUIDToAssetPath(guid);
        Assert.IsTrue(path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase), "edited model GUID must resolve to FBX");
        return path;
    }

    private static string SelectExistingNonRootReceipt(string editedPath)
    {
        string json = File.ReadAllText(Disk(ManifestPath), Encoding.UTF8);
        var receipts = FieldMatches(json, "edited_bone_realization_id").Select(m => m.Groups[2].Value).ToArray();
        Assert.Greater(receipts.Length, 0, "fixture needs at least one bone mapping");
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(editedPath);
        Assert.IsNotNull(model, "edited FBX must already be imported");
        SkinnedMeshRenderer[] renderers = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        Assert.AreEqual(1, renderers.Length, "the bounded synthetic fixture expects one edited skinned renderer");
        SkinnedMeshRenderer renderer = renderers[0];
        Type markerType = AppDomain.CurrentDomain.GetAssemblies()
            .Select(assembly => assembly.GetType("VapbRealizationMarker", false)).FirstOrDefault(type => type != null);
        Assert.IsNotNull(markerType, "VapbRealizationMarker is not loaded");
        FieldInfo receiptField = markerType.GetField("boneRealizationId", BindingFlags.Public | BindingFlags.Instance);
        Assert.IsNotNull(receiptField, "boneRealizationId field missing");
        Transform[] bones = renderer.bones;
        foreach (string receipt in receipts)
        {
            foreach (Transform bone in bones)
            {
                if (bone == null || bone == renderer.rootBone) continue;
                Component marker = bone.GetComponent(markerType);
                if (marker != null && String.Equals((string)receiptField.GetValue(marker), receipt,
                    StringComparison.Ordinal))
                {
                    TestContext.WriteLine("selected nonroot receipt=" + receipt);
                    return receipt;
                }
            }
        }
        Assert.Fail("no manifest receipt maps to an existing nonroot renderer bone");
        return null;
    }

    private static Dictionary<string, string> ProtectedPathsFromManifest()
    {
        string json = File.ReadAllText(Disk(ManifestPath), Encoding.UTF8);
        var paths = new HashSet<string>(StringComparer.Ordinal) { ManifestPath };
        foreach (string field in new[] { "source_model_guid", "model_guid", "prefab_guid" })
        {
            string path = AssetDatabase.GUIDToAssetPath(FieldValue(json, field));
            Assert.IsFalse(String.IsNullOrEmpty(path), field + " must resolve to an existing asset");
            paths.Add(path);
        }
        foreach (string field in new[] { "witness_noop_path", "witness_path" })
            paths.Add(FieldValue(json, field));
        foreach (string path in PriorVariants) paths.Add(path);
        return paths.ToDictionary(path => path, path => path, StringComparer.Ordinal);
    }

    private static string FieldValue(string json, string field)
    {
        MatchCollection matches = FieldMatches(json, field);
        Assert.AreEqual(1, matches.Count, "expected one JSON field: " + field);
        return matches[0].Groups[2].Value;
    }

    private static MatchCollection FieldMatches(string json, string field)
    {
        string pattern = "(\"" + Regex.Escape(field) + "\"\\s*:\\s*\")([^\"]*)(\")";
        return Regex.Matches(json, pattern);
    }

    private static string ReplaceSingleField(string json, string field, string replacement)
    {
        MatchCollection matches = FieldMatches(json, field);
        Assert.AreEqual(1, matches.Count, "expected one JSON field to replace: " + field);
        Assert.AreNotEqual(matches[0].Groups[2].Value, replacement, "replacement must differ from source value");
        Match match = matches[0];
        Group value = match.Groups[2];
        return json.Substring(0, value.Index) + replacement + json.Substring(value.Index + value.Length);
    }

    private static string ReplaceFirstExactFieldValue(string json, string field, string oldValue, string replacement)
    {
        MatchCollection matches = FieldMatches(json, field);
        Assert.GreaterOrEqual(matches.Count, 1, "field missing: " + field);
        Assert.IsTrue(matches.Cast<Match>().Any(match => match.Groups[2].Value == oldValue),
            "selected real receipt missing from fault manifest");
        Assert.IsFalse(matches.Cast<Match>().Any(match => match.Groups[2].Value == replacement),
            "fault receipt must be unique");
        Match match = matches.Cast<Match>().First(item => item.Groups[2].Value == oldValue);
        Group value = match.Groups[2];
        return json.Substring(0, value.Index) + replacement + json.Substring(value.Index + value.Length);
    }

    private static string SetVariantPath(string json, string variant)
    { return ReplaceSingleField(json, "variant_path", variant); }

    private static string ProjectRoot()
    { return Directory.GetParent(Path.GetFullPath(Application.dataPath)).FullName; }

    private static string TestRoot()
    {
        string raw = Environment.GetEnvironmentVariable(RootEnvironment);
        Assert.IsFalse(String.IsNullOrWhiteSpace(raw), "VAPB_STAGE3_TEST_ROOT must point to the owned Stage3 run root");
        return Path.GetFullPath(raw).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
    }

    private static string Disk(string projectRelativePath)
    {
        Assert.IsTrue(projectRelativePath == "Assets" || projectRelativePath.StartsWith("Assets/", StringComparison.Ordinal));
        Assert.IsFalse(projectRelativePath.Contains(".."));
        return Path.GetFullPath(Path.Combine(ProjectRoot(), projectRelativePath.Replace('/', Path.DirectorySeparatorChar)));
    }

    private static string[] Inventory()
    {
        string root = Disk("Assets");
        return Directory.GetFiles(root, "*", SearchOption.AllDirectories)
            .OrderBy(path => path, StringComparer.Ordinal)
            .Select(path => path.Substring(root.Length + 1).Replace('\\', '/') + " " + Sha(path)).ToArray();
    }

    private static string[] EvidenceInventory()
    {
        string root = ProjectRoot();
        return new[] { 7, 8, 9, 10 }.SelectMany(version =>
                Directory.GetFiles(root, "VapbModelSkinTopologyBoundaryReplacementV" + version + "*.json",
                    SearchOption.TopDirectoryOnly))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
            .Select(path => Path.GetFileName(path) + " " + Sha(path)).ToArray();
    }

    private static void AssertNoReparsePoint(string path)
    {
        var components = new Stack<string>();
        for (string current = Path.GetFullPath(path); !String.IsNullOrEmpty(current); current = Path.GetDirectoryName(current))
            components.Push(current);
        while (components.Count != 0)
            Assert.IsFalse((File.GetAttributes(components.Pop()) & FileAttributes.ReparsePoint) != 0,
                "owned TargetProject path contains a reparse point");
    }

    private static void AssertPathAbsent(string path)
    {
        Assert.IsFalse(File.Exists(Disk(path)) || Directory.Exists(Disk(path)) ||
            File.Exists(Disk(path + ".meta")) || Directory.Exists(Disk(path + ".meta")) ||
            AssetDatabase.LoadMainAssetAtPath(path) != null || !String.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(path)),
            "test-owned path already exists: " + path);
    }

    private static void AssertVariantAbsent(string path) { AssertPathAbsent(path); }

    private sealed class PathState
    {
        public string payloadHash;
        public string metaHash;
        public string guid;
        public bool loaded;
    }

    private static Dictionary<string, PathState> CaptureStates(Dictionary<string, string> paths)
    { return paths.Values.ToDictionary(path => path, CaptureState, StringComparer.Ordinal); }

    private static PathState CaptureState(string path)
    {
        string disk = Disk(path);
        string meta = disk + ".meta";
        return new PathState {
            payloadHash = File.Exists(disk) ? Sha(disk) : "<absent>",
            metaHash = File.Exists(meta) ? Sha(meta) : "<absent>",
            guid = AssetDatabase.AssetPathToGUID(path),
            loaded = AssetDatabase.LoadMainAssetAtPath(path) != null
        };
    }

    private static void AssertStatesEqual(Dictionary<string, PathState> before, Dictionary<string, PathState> after)
    {
        CollectionAssert.AreEquivalent(before.Keys, after.Keys);
        foreach (string path in before.Keys) AssertStateEqual(before[path], after[path], path);
    }

    private static void AssertStateEqual(PathState before, PathState after, string label = "asset")
    {
        Assert.AreEqual(before.payloadHash, after.payloadHash, label + " payload");
        Assert.AreEqual(before.metaHash, after.metaHash, label + " .meta");
        Assert.AreEqual(before.guid, after.guid, label + " GUID");
        Assert.AreEqual(before.loaded, after.loaded, label + " AssetDatabase presence");
    }

    private static string Sha(string path)
    {
        using (SHA256 hash = SHA256.Create())
        using (FileStream stream = File.OpenRead(path))
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }

    private static void DeleteOwnedManifest(string path)
    {
        Assert.IsTrue(path.StartsWith(FaultManifestPrefix, StringComparison.Ordinal), "refusing non-owned manifest cleanup");
        Assert.IsTrue(path.EndsWith(".json", StringComparison.OrdinalIgnoreCase));
        string full = Disk(path);
        AssetDatabase.DeleteAsset(path);
        if (File.Exists(full)) File.Delete(full);
        if (File.Exists(full + ".meta")) File.Delete(full + ".meta");
    }

    private static void DeleteOwnedVariant(string path)
    {
        Assert.IsTrue(path.StartsWith(VariantPrefix, StringComparison.Ordinal), "refusing non-owned Variant cleanup");
        Assert.IsTrue(path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase));
        string full = Disk(path);
        AssetDatabase.DeleteAsset(path);
        if (File.Exists(full)) File.Delete(full);
        if (File.Exists(full + ".meta")) File.Delete(full + ".meta");
    }
}

// Observes the Finalizer's narrowly tagged witness import without changing the FBX or importer.
public sealed class Stage3RejectWitnessImportObserver : AssetPostprocessor
{
    public static int WitnessTaggedImports { get; private set; }
    public static readonly List<string> SourceImportHashes = new List<string>();
    public static string ExpectedSourcePath { get; private set; }
    public static void Reset(string sourcePath)
    {
        WitnessTaggedImports = 0;
        SourceImportHashes.Clear();
        ExpectedSourcePath = sourcePath;
    }

    private void OnPreprocessModel()
    {
        if (String.Equals(assetPath, ExpectedSourcePath, StringComparison.Ordinal))
        {
            string absolute = Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                assetPath.Replace('/', Path.DirectorySeparatorChar));
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(absolute))
                SourceImportHashes.Add(BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant());
        }
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type finalizer = assembly.GetType("VapbModelSkinFinalizer", false);
            MethodInfo witness = finalizer == null ? null : finalizer.GetMethod("IsWitnessImport",
                BindingFlags.NonPublic | BindingFlags.Static);
            if (witness != null && (bool)witness.Invoke(null, new object[] { assetPath }))
            {
                WitnessTaggedImports++;
                return;
            }
        }
    }
}

