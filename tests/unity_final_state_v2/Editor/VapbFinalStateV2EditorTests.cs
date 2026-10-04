using System;
using System.IO;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

public sealed class VapbFinalStateV2EditorTests
{
    private static Type Finalizer
    {
        get
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType("VapbFinalStateFinalizer", false);
                if (type != null) return type;
            }
            throw new AssertionException("VapbFinalStateFinalizer was not compiled into an Editor assembly");
        }
    }

    private static string Id(char value) { return "VAPB-MAT-" + new string(value, 32); }

    private static string Record(char value)
    {
        return "{\"export_material_id\":\"" + Id(value) + "\",\"guid\":\"" +
            new string(value, 32) + "\",\"file_id\":\"4800000\",\"asset_sha256\":\"" +
            new string('e', 64) + "\",\"shader\":{\"classification\":\"UNITY_BUILTIN\"},\"textures\":[]}";
    }

    private static string Records(params char[] values)
    {
        string[] records = new string[values.Length];
        for (int i = 0; i < values.Length; i++) records[i] = Record(values[i]);
        return "[" + string.Join(",", records) + "]";
    }

    private static string Slots(params char[] values)
    {
        string[] slots = new string[values.Length];
        for (int i = 0; i < values.Length; i++)
            slots[i] = "{\"slot_index\":\"" + i.ToString(System.Globalization.CultureInfo.InvariantCulture) +
                "\",\"export_material_id\":\"" + Id(values[i]) + "\"}";
        return "[" + string.Join(",", slots) + "]";
    }

    private static object Task(string declarations, string slots)
    {
        return ParseTask("\"material_transport_version\":2,", declarations, slots);
    }

    private static object TaskWithoutTransportVersion(string declarations, string slots)
    {
        return ParseTask("", declarations, slots);
    }

    private static object ParseTask(string transportVersionField, string declarations, string slots)
    {
        Type taskType = Finalizer.GetNestedType("Task", BindingFlags.NonPublic);
        string json = "{\"kind\":\"BUILD_EXPORTED_STATIC_V2\"," + transportVersionField +
            "\"export_object_id\":\"VAPB-OBJ-" + new string('c', 32) + "\"," +
            "\"model_guid\":\"" + new string('d', 32) + "\",\"model_sha256\":\"" +
            new string('e', 64) + "\",\"prefab_path\":\"Assets/VAPBExport/Generated_" +
            new string('c', 32) + ".prefab\",\"materials\":" + declarations +
            ",\"material_slots\":" + slots + "}";
        return JsonUtility.FromJson(json, taskType);
    }

    private static int[] Resolve(object task, string[] labels, int subMeshCount)
    {
        MethodInfo method = Finalizer.GetMethod("ResolveNativeMaterialOrder",
            BindingFlags.NonPublic | BindingFlags.Static);
        return (int[])method.Invoke(null, new object[] { task, labels, subMeshCount });
    }

    private static void Validate(object task)
    {
        Finalizer.GetMethod("ValidateV2Task", BindingFlags.NonPublic | BindingFlags.Static)
            .Invoke(null, new[] { task });
    }

    private static void AssertRejected(Action action, string expectedReason)
    {
        TargetInvocationException exception = Assert.Throws<TargetInvocationException>(() => action());
        Assert.IsInstanceOf<InvalidOperationException>(exception.InnerException);
        Assert.AreEqual(expectedReason, exception.InnerException.Message);
    }

    private const string DisposableProjectMarker = ".vapb-disposable-unity-test-project";

    private static string[] V1ApplyPaths(string projectRoot)
    {
        string manifest = Path.Combine(projectRoot, "Assets", "VAPBExport", "manifest.json");
        string prefab = Path.Combine(projectRoot, "Assets", "VAPBExport", "Generated_" +
            new string('c', 32) + ".prefab");
        return new[] { manifest, manifest + ".meta", prefab, prefab + ".meta" };
    }

    private static System.Collections.Generic.Dictionary<string, byte[]> CaptureFiles(string[] paths)
    {
        var result = new System.Collections.Generic.Dictionary<string, byte[]>();
        foreach (string path in paths) result.Add(path, File.Exists(path) ? File.ReadAllBytes(path) : null);
        return result;
    }

    private static System.Collections.Generic.Dictionary<string, string> HashFiles(string[] paths)
    {
        var result = new System.Collections.Generic.Dictionary<string, string>();
        foreach (string path in paths)
        {
            if (!File.Exists(path)) { result.Add(path, "<absent>"); continue; }
            using (var sha = System.Security.Cryptography.SHA256.Create())
                result.Add(path, BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))));
        }
        return result;
    }

    private static void RestoreFiles(System.Collections.Generic.Dictionary<string, byte[]> snapshots)
    {
        foreach (var snapshot in snapshots)
        {
            if (snapshot.Value == null)
            {
                if (File.Exists(snapshot.Key)) File.Delete(snapshot.Key);
            }
            else
            {
                Directory.CreateDirectory(Path.GetDirectoryName(snapshot.Key));
                File.WriteAllBytes(snapshot.Key, snapshot.Value);
            }
        }
    }

    private static void AssertHashesEqual(
        System.Collections.Generic.Dictionary<string, string> expected,
        System.Collections.Generic.Dictionary<string, string> actual)
    {
        foreach (string path in expected.Keys) Assert.AreEqual(expected[path], actual[path], path);
    }

    [Test]
    public void MapsNativePermutationByExactIdentityLabel()
    {
        object task = Task(Records('a', 'b', 'c'), Slots('a', 'b', 'c'));
        Assert.AreEqual(new[] { 2, 0, 1 }, Resolve(task, new[] { Id('c'), Id('a'), Id('b') }, 3));
    }

    [Test]
    public void AcceptsRepeatedLabelOnlyAtExactMultiplicity()
    {
        object task = Task(Records('a', 'b'), Slots('a', 'a', 'b'));
        Assert.AreEqual(new[] { 1, 0, 0 }, Resolve(task, new[] { Id('b'), Id('a'), Id('a') }, 3));
        AssertRejected(() => Resolve(task, new[] { Id('b'), Id('a'), Id('b') }, 3),
            "NATIVE_MATERIAL_MULTIPLICITY_MISMATCH");
    }

    [TestCase(null)]
    [TestCase("")]
    [TestCase("Renamed")]
    [TestCase("VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.001")]
    [TestCase("VAPB-MAT-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")]
    public void RejectsNullMissingRenamedSuffixedOrUnknownNativeLabels(string badLabel)
    {
        object task = Task(Records('a'), Slots('a'));
        AssertRejected(() => Resolve(task, new[] { badLabel }, 1), "NATIVE_MATERIAL_LABEL_INVALID");
    }

    [Test]
    public void RejectsCollapsedSubmeshCountBeforeMapping()
    {
        object task = Task(Records('a', 'b'), Slots('a', 'b'));
        AssertRejected(() => Resolve(task, new[] { Id('a') }, 1),
            "NATIVE_MATERIAL_CARDINALITY_MISMATCH");
    }

    [TestCase("[{\"slot_index\":\"0\",\"export_material_id\":\"VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"},{\"slot_index\":\"2\",\"export_material_id\":\"VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}]")]
    [TestCase("[{\"slot_index\":\"0\",\"export_material_id\":\"VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"},{\"slot_index\":\"0\",\"export_material_id\":\"VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}]")]
    [TestCase("[{\"slot_index\":\"0\",\"export_material_id\":\"VAPB-MAT-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\"}]")]
    public void RejectsNoncontiguousDuplicateOrUndeclaredSlots(string slotJson)
    {
        object task = Task(Records('a'), slotJson);
        AssertRejected(() => Validate(task), "MATERIAL_SLOT_INVALID");
    }

    [Test]
    public void RejectsUnusedMaterialDeclarationAndDuplicateIds()
    {
        object unused = Task(Records('a', 'b'), Slots('a'));
        object duplicate = Task(Records('a', 'a'), Slots('a'));
        AssertRejected(() => Validate(unused), "MATERIAL_DECLARATION_UNUSED");
        AssertRejected(() => Validate(duplicate), "MATERIAL_DECLARATION_INVALID");
    }

    [Test]
    public void RejectsMissingTransportVersion()
    {
        object task = TaskWithoutTransportVersion(Records('a'), Slots('a'));
        AssertRejected(() => Validate(task), "TASK_UNSUPPORTED");
    }

    [Test]
    public void AllowsDifferentExportIdsToResolveToSameUnityIdentity()
    {
        string records = "[" + Record('a') + "," + Record('b').Replace(
            "\"guid\":\"" + new string('b', 32) + "\"",
            "\"guid\":\"" + new string('a', 32) + "\"") + "]";
        Validate(Task(records, Slots('a', 'b')));
    }

    [Test]
    public void AcceptsCanonicalSlotIndex()
    {
        Assert.DoesNotThrow(() => Validate(Task(Records('a'), Slots('a'))));
    }

    // Raw numeric-token coercion and duplicate-key handling require separate Unity characterization tests.
    [TestCase(null)]
    [TestCase("")]
    [TestCase("00")]
    [TestCase("+0")]
    [TestCase("-0")]
    [TestCase("0.0")]
    [TestCase("0e0")]
    [TestCase(" 0")]
    public void RejectsMissingNullOrNoncanonicalSlotIndex(string index)
    {
        string value = index == null ? "null" : "\"" + index + "\"";
        object task = Task(Records('a'), "[{\"slot_index\":" + value +
            ",\"export_material_id\":\"" + Id('a') + "\"}]");
        AssertRejected(() => Validate(task), "MATERIAL_SLOT_INVALID");
    }

    [Test]
    public void RejectsMissingSlotIndex()
    {
        object task = Task(Records('a'), "[{\"export_material_id\":\"" + Id('a') + "\"}]");
        AssertRejected(() => Validate(task), "MATERIAL_SLOT_INVALID");
    }
    [Test]
    public void V1ApplyExposesActionableReexportResultBeforeAssetResolution()
    {
        // Destructive manifest import is permitted only in a disposable project carrying this marker.
        string projectRoot = Directory.GetParent(Application.dataPath).FullName;
        Assert.IsTrue(File.Exists(Path.Combine(projectRoot, DisposableProjectMarker)),
            "Create " + DisposableProjectMarker + " only in a throwaway Unity test project.");
        const string path = "Assets/VAPBExport/manifest.json";
        string diskPath = Path.Combine(projectRoot, path.Replace('/', Path.DirectorySeparatorChar));
        string[] protectedPaths = V1ApplyPaths(projectRoot);
        var originalFiles = CaptureFiles(protectedPaths);
        var originalHashes = HashFiles(protectedPaths);
        string log = null;
        Application.LogCallback handler = (condition, stack, type) => { if (condition.Contains("FINAL_STATE_REEXPORT_REQUIRED")) log = condition; };
        bool subscribed = false;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(diskPath));
            File.WriteAllText(diskPath, "{\"schema_version\":\"vapb-export-manifest-1\",\"reference_rebind_tasks\":[{\"kind\":\"BUILD_EXPORTED_STATIC_V1\"}]}");
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var beforeApplyHashes = HashFiles(protectedPaths);
            Application.logMessageReceived += handler;
            subscribed = true;
            LogAssert.Expect(LogType.Error,
                "VAPB_FINAL_STATE_REJECTED=FINAL_STATE_REEXPORT_REQUIRED: This package predates material identity transport. Re-export the final-state package from Blender, then import the new package. Existing assets were not rewritten.");
            bool applied = (bool)Finalizer.GetMethod("Apply", BindingFlags.Public | BindingFlags.Static)
                .Invoke(null, new object[] { path });
            Assert.IsFalse(applied);
            Assert.AreEqual("FINAL_STATE_REEXPORT_REQUIRED",
                Finalizer.GetProperty("LastResult", BindingFlags.Public | BindingFlags.Static).GetValue(null));
            StringAssert.Contains("Re-export the final-state package from Blender", log);
            AssertHashesEqual(beforeApplyHashes, HashFiles(protectedPaths));
        }
        finally
        {
            if (subscribed) Application.logMessageReceived -= handler;
            RestoreFiles(originalFiles);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            AssertHashesEqual(originalHashes, HashFiles(protectedPaths));
        }
    }
}
