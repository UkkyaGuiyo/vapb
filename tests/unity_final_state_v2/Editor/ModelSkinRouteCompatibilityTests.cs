using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;

public sealed class ModelSkinRouteCompatibilityTests
{
    private const string NormalKind = "RESTORE_MODEL_SKIN_VARIANT_V1";

    [Test]
    public void JsonMissingOptionalReceiptsStayAbsentWhileExplicitObjectsStayPresent()
    {
        Type finalizer = FindFinalizer();
        foreach (string tail in new[] { "", ",\"weight_transport\":null,\"parent_transform_mapping\":null" })
        {
            object parsed = Invoke(finalizer, "ParseManifestJson", "{\"reference_rebind_tasks\":[{\"kind\":\"RESTORE_DIRECT_SKIN_VARIANT_V1\"" + tail + "}]}");
            object task = ((Array)parsed.GetType().GetField("reference_rebind_tasks").GetValue(parsed)).GetValue(0);
            Assert.IsNull(task.GetType().GetField("weight_transport").GetValue(task));
            Assert.IsNull(task.GetType().GetField("parent_transform_mapping").GetValue(task));
        }
        object explicitParsed = Invoke(finalizer, "ParseManifestJson", "{\"reference_rebind_tasks\":[{\"kind\":\"RESTORE_DIRECT_SKIN_VARIANT_V1\",\"weight_transport\":{},\"parent_transform_mapping\":{}}]}");
        object explicitTask = ((Array)explicitParsed.GetType().GetField("reference_rebind_tasks").GetValue(explicitParsed)).GetValue(0);
        Assert.IsNotNull(explicitTask.GetType().GetField("weight_transport").GetValue(explicitTask));
        Assert.IsNotNull(explicitTask.GetType().GetField("parent_transform_mapping").GetValue(explicitTask));
        TargetInvocationException error = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", explicitTask));
        Assert.AreEqual("WEIGHT_TRANSPORT_CONTEXT_UNSUPPORTED", error.InnerException.Message);
    }

    [Test]
    public void SameIndexLayoutWithMatchingShapesKeepsLegacyMultiSkinScope()
    {
        Type finalizer = FindFinalizer();
        Mesh source = TriangleWithShape();
        Mesh same = UnityEngine.Object.Instantiate(source);
        GameObject root = new GameObject("synthetic-same-layout");
        try
        {
            root.AddComponent<BoxCollider>();
            GameObject firstSkin = new GameObject("first-skin");
            firstSkin.transform.SetParent(root.transform, false);
            firstSkin.AddComponent<SkinnedMeshRenderer>();
            GameObject secondSkin = new GameObject("second-skin");
            secondSkin.transform.SetParent(root.transform, false);
            secondSkin.AddComponent<SkinnedMeshRenderer>();
            Assert.AreEqual(2, root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length);

            object layout = CaptureLayout(finalizer, source);
            Assert.IsTrue((bool)Invoke(finalizer, "SameNormalSkinIndexLayout", layout, same));
            Assert.IsFalse((bool)Invoke(finalizer, "RequiresReplacementEligibility", NormalKind, layout, same));
            Assert.IsTrue((bool)Invoke(finalizer, "SameBlendShapes", layout, same));

            IList plans = NewPlans(finalizer, 2, false);
            Invoke(finalizer, "ValidateModelSkinReplacementScope", root, plans);
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(root);
            UnityEngine.Object.DestroyImmediate(source);
            UnityEngine.Object.DestroyImmediate(same);
        }
    }

    [Test]
    public void ChangedIndexLayoutWithShapesDoesNotEnterReplacementEligibility()
    {
        Type finalizer = FindFinalizer();
        Mesh source = TriangleWithShape();
        Mesh changed = UnityEngine.Object.Instantiate(source);
        try
        {
            changed.SetIndices(new[] { 0, 2, 1 }, MeshTopology.Triangles, 0, false);
            object layout = CaptureLayout(finalizer, source);

            Assert.IsFalse((bool)Invoke(finalizer, "SameNormalSkinIndexLayout", layout, changed));
            Assert.IsTrue((bool)Invoke(finalizer, "RequiresReplacementEligibility", NormalKind, layout, changed));
            Assert.IsFalse((bool)Invoke(finalizer, "HasNoBlendShapesForReplacement", layout, changed));
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(source);
            UnityEngine.Object.DestroyImmediate(changed);
        }
    }

    [Test]
    public void ChangedLayoutBatchIsRejectedButLegacyBatchIsNotScopedDown()
    {
        Type finalizer = FindFinalizer();
        GameObject root = new GameObject("synthetic-batch-scope");
        try
        {
            IList legacyPlans = NewPlans(finalizer, 2, false);
            Invoke(finalizer, "ValidateModelSkinReplacementScope", root, legacyPlans);

            IList replacementPlans = NewPlans(finalizer, 2, true);
            TargetInvocationException error = Assert.Throws<TargetInvocationException>(() =>
                Invoke(finalizer, "ValidateModelSkinReplacementScope", root, replacementPlans));
            Assert.AreEqual("MODEL_SKIN_REPLACEMENT_SCOPE_UNSUPPORTED", error.InnerException.Message);
        }
        finally { UnityEngine.Object.DestroyImmediate(root); }
    }

    [Test]
    public void ChangedLayoutScopeRejectsExtraAvatarOrUnknownComponents()
    {
        Type finalizer = FindFinalizer();
        GameObject root = new GameObject("synthetic-replacement-scope");
        try
        {
            root.AddComponent<BoxCollider>();
            IList plans = NewPlans(finalizer, 1, true);
            TargetInvocationException error = Assert.Throws<TargetInvocationException>(() =>
                Invoke(finalizer, "ValidateModelSkinReplacementScope", root, plans));
            Assert.AreEqual("SOURCE_COMPONENT_SCOPE_UNSUPPORTED", error.InnerException.Message);
        }
        finally { UnityEngine.Object.DestroyImmediate(root); }
    }

    [Test]
    public void ChangedLayoutBoundsGuardRejectsNullAndSingularRootBone()
    {
        Type finalizer = FindFinalizer();
        Mesh valid = new Mesh();
        valid.vertices = new[] { Vector3.zero };
        valid.bindposes = new[] { Matrix4x4.identity };
        valid.boneWeights = new[] { new BoneWeight { boneIndex0 = 0, weight0 = 1f } };
        GameObject rendererObject = new GameObject("synthetic-null-root");
        GameObject singularRoot = new GameObject("synthetic-singular-root");
        try
        {
            SkinnedMeshRenderer skin = rendererObject.AddComponent<SkinnedMeshRenderer>();
            skin.rootBone = rendererObject.transform;
            skin.bones = new[] { rendererObject.transform };
            skin.sharedMesh = valid;
            Assert.IsTrue((bool)Invoke(finalizer, "BoundsContainsRestMesh", skin, valid,
                new Transform[] { rendererObject.transform }, 0.001f), "Valid identity-root control must pass.");

            skin.rootBone = null;
            Assert.IsFalse((bool)Invoke(finalizer, "BoundsContainsRestMesh", skin, valid,
                new Transform[] { rendererObject.transform }, 0.001f));

            singularRoot.transform.localScale = new Vector3(0f, 1f, 1f);
            skin.rootBone = singularRoot.transform;
            Assert.IsFalse((bool)Invoke(finalizer, "BoundsContainsRestMesh", skin, valid,
                new Transform[] { singularRoot.transform }, 0.001f));
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(rendererObject);
            UnityEngine.Object.DestroyImmediate(singularRoot);
            UnityEngine.Object.DestroyImmediate(valid);
        }
    }

    [Test]
    public void BoundsToleranceUsesRootLocalUnitsAcrossAllFaces()
    {
        Type finalizer = FindFinalizer();
        Bounds bounds = new Bounds(Vector3.zero, Vector3.one * 2f);
        Vector3[] onFaces = {
            new Vector3(-1f, 0f, 0f), new Vector3(1f, 0f, 0f),
            new Vector3(0f, -1f, 0f), new Vector3(0f, 1f, 0f),
            new Vector3(0f, 0f, -1f), new Vector3(0f, 0f, 1f)
        };
        foreach (Vector3 face in onFaces)
        {
            Assert.IsTrue((bool)Invoke(finalizer, "BoundsContainsPoint", face, bounds, 0.001f));
            Vector3 within = face * 1.0009f;
            Vector3 outside = face * 1.0011f;
            Assert.IsTrue((bool)Invoke(finalizer, "BoundsContainsPoint", within, bounds, 0.001f));
            Assert.IsFalse((bool)Invoke(finalizer, "BoundsContainsPoint", outside, bounds, 0.001f));
        }
        Assert.AreEqual(0.1f, Matrix4x4.Scale(Vector3.one * 100f)
            .MultiplyVector(Vector3.right * 0.001f).magnitude, 0.00001f);
    }

    [Test]
    public void BoundsToleranceIncludesComputedMinAndMaxEdges()
    {
        Type finalizer = FindFinalizer();
        Bounds bounds = new Bounds(Vector3.zero, Vector3.one * 2f);
        const float tolerance = 0.001f;
        Vector3[] exactEdges = {
            new Vector3(bounds.min.x - tolerance, 0f, 0f),
            new Vector3(bounds.max.x + tolerance, 0f, 0f),
            new Vector3(0f, bounds.min.y - tolerance, 0f),
            new Vector3(0f, bounds.max.y + tolerance, 0f),
            new Vector3(0f, 0f, bounds.min.z - tolerance),
            new Vector3(0f, 0f, bounds.max.z + tolerance)
        };
        for (int i = 0; i < exactEdges.Length; i++)
        {
            Vector3 point = exactEdges[i];
            Assert.IsTrue((bool)Invoke(finalizer, "BoundsContainsPoint", point, bounds, tolerance),
                "A point computed by the same min/max +/- tolerance expression must be included; edge=" +
                i + " point=" + point + " x=" + point.x.ToString("R") + " lower=" +
                (bounds.min.x - tolerance).ToString("R") + " rawXLower=" +
                (point.x >= bounds.min.x - tolerance) + " bits=" +
                BitConverter.ToInt32(BitConverter.GetBytes(point.x), 0).ToString("X8"));
        }
        float minX = BitConverter.ToSingle(BitConverter.GetBytes(bounds.min.x - tolerance), 0);
        float maxX = BitConverter.ToSingle(BitConverter.GetBytes(bounds.max.x + tolerance), 0);
        float minY = BitConverter.ToSingle(BitConverter.GetBytes(bounds.min.y - tolerance), 0);
        float maxY = BitConverter.ToSingle(BitConverter.GetBytes(bounds.max.y + tolerance), 0);
        float minZ = BitConverter.ToSingle(BitConverter.GetBytes(bounds.min.z - tolerance), 0);
        float maxZ = BitConverter.ToSingle(BitConverter.GetBytes(bounds.max.z + tolerance), 0);
        Vector3[] immediatelyOutside = {
            new Vector3(AdjacentSingle(minX, false), 0f, 0f),
            new Vector3(AdjacentSingle(maxX, true), 0f, 0f),
            new Vector3(0f, AdjacentSingle(minY, false), 0f),
            new Vector3(0f, AdjacentSingle(maxY, true), 0f),
            new Vector3(0f, 0f, AdjacentSingle(minZ, false)),
            new Vector3(0f, 0f, AdjacentSingle(maxZ, true))
        };
        foreach (Vector3 point in immediatelyOutside)
            Assert.IsFalse((bool)Invoke(finalizer, "BoundsContainsPoint", point, bounds, tolerance),
                "The immediately adjacent single-precision point outside tolerance must be rejected: " + point);
    }

    private static float AdjacentSingle(float value, bool towardPositiveInfinity)
    {
        if (Single.IsNaN(value) || (towardPositiveInfinity && value == Single.PositiveInfinity) ||
            (!towardPositiveInfinity && value == Single.NegativeInfinity)) return value;
        if (value == 0f) return towardPositiveInfinity ? Single.Epsilon : -Single.Epsilon;
        int bits = BitConverter.ToInt32(BitConverter.GetBytes(value), 0);
        bits += ((value > 0f) == towardPositiveInfinity) ? 1 : -1;
        return BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
    }

    [Test]
    public void SourceModelTaskRejectsPrefabEvidenceAndMixedBatch()
    {
        Type finalizer = FindFinalizer();
        Type taskType = finalizer.GetNestedType("Task", BindingFlags.NonPublic);
        object task = Activator.CreateInstance(taskType, true);
        Action<string, object> set = (key, value) => taskType.GetField(key).SetValue(task, value);
        set("kind", "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1");
        set("source_model_guid", new string('a', 32)); set("source_model_sha256", new string('1', 64));
        set("source_model_uid", "101"); set("source_geometry_uid", "202"); set("realization_id", "single-skin");
        set("model_guid", new string('b', 32)); set("model_sha256", new string('2', 64));
        set("witness_noop_sha256", new string('3', 64)); set("witness_sha256", new string('4', 64));
        set("witness_noop_path", "Assets/VAPBExport/noop.bytes"); set("witness_path", "Assets/VAPBExport/witness.bytes");
        set("source_model_uids", new[] { "101", "303" });
        set("instance_edges", Array.CreateInstance(finalizer.GetNestedType("InstanceEdge", BindingFlags.NonPublic), 0));
        Type boneType = finalizer.GetNestedType("BoneMapping", BindingFlags.NonPublic);
        object bone = Activator.CreateInstance(boneType, true);
        boneType.GetField("source_model_uid").SetValue(bone, "303");
        boneType.GetField("edited_bone_realization_id").SetValue(bone, "edited-bone");
        Array bones = Array.CreateInstance(boneType, 1); bones.SetValue(bone, 0); set("bone_mappings", bones);
        string identity = "SOURCE_MODEL_SKIN_V1:" + new string('a', 32) + ":" + new string('1', 64) + ":single-skin";
        string hash;
        using (var sha = System.Security.Cryptography.SHA256.Create())
            hash = BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(identity))).Replace("-", "").ToLowerInvariant();
        set("variant_path", "Assets/VAPBExport/EditedVariant_" + hash + ".prefab");
        Invoke(finalizer, "ValidateTask", task);
        Assert.AreEqual(new string('a', 32), Invoke(finalizer, "SourceRootGuid", task));
        // Parent Object receipt is additive and must not impersonate mesh or Bone roles.
        Type parentType = finalizer.GetNestedType("ParentTransformMapping", BindingFlags.NonPublic);
        object parent = Activator.CreateInstance(parentType, true);
        Action<string, string> setParent = (key, value) => parentType.GetField(key).SetValue(parent, value);
        set("source_model_uids", new[] { "101", "303", "404" });
        setParent("source_model_uid", "404"); setParent("edited_transform_realization_id", "parent-object");
        set("parent_transform_mapping", parent);
        Invoke(finalizer, "ValidateTask", task);
        foreach (string uid in new[] { "101", "303", "405", "0404", "0" })
        {
            setParent("source_model_uid", uid);
            var rejected = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", task));
            Assert.AreEqual("PARENT_TRANSFORM_MAPPING_INVALID", rejected.InnerException.Message);
        }
        setParent("source_model_uid", "404");
        foreach (string receipt in new[] { "single-skin", "edited-bone", "" })
        {
            setParent("edited_transform_realization_id", receipt);
            var rejected = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", task));
            Assert.AreEqual("PARENT_TRANSFORM_MAPPING_INVALID", rejected.InnerException.Message);
        }
        setParent("edited_transform_realization_id", "parent-object");
        set("kind", NormalKind);
        var wrongRoute = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", task));
        Assert.AreEqual("PARENT_TRANSFORM_MAPPING_INVALID", wrongRoute.InnerException.Message);
        set("kind", "RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1");
        set("parent_transform_mapping", null);

        set("prefab_guid", new string('c', 32));
        var error = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", task));
        Assert.AreEqual("SOURCE_MODEL_CONTEXT_INVALID", error.InnerException.Message);
        set("prefab_guid", null);
        Array tasks = Array.CreateInstance(taskType, 2); tasks.SetValue(task, 0); tasks.SetValue(task, 1);
        error = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateBatch", (object)tasks));
        Assert.AreEqual("SOURCE_MODEL_SINGLE_TASK_REQUIRED", error.InnerException.Message);
        set("variant_path", "Assets/VAPBExport/EditedVariant_wrong.prefab");
        error = Assert.Throws<TargetInvocationException>(() => Invoke(finalizer, "ValidateTask", task));
        Assert.AreEqual("SOURCE_MODEL_PATH_INVALID", error.InnerException.Message);
    }

    [Test]
    public void SourceModelInfluencesRejectChangedWeightsAndBoneSlots()
    {
        Type finalizer = FindFinalizer();
        Mesh source = TriangleWithShape(); Mesh edited = UnityEngine.Object.Instantiate(source);
        try
        {
            var weights = new BoneWeight[3];
            for (int i = 0; i < weights.Length; i++)
                weights[i] = new BoneWeight { boneIndex0 = 0, boneIndex1 = 1, weight0 = 0.75f, weight1 = 0.25f };
            source.boneWeights = weights; edited.boneWeights = weights;
            Assert.IsTrue((bool)Invoke(finalizer, "SameSkinInfluences", source, edited));
            weights[0].weight0 = 0.5f; weights[0].weight1 = 0.5f; edited.boneWeights = weights;
            Assert.IsFalse((bool)Invoke(finalizer, "SameSkinInfluences", source, edited));
            weights[0].weight0 = 0.75f; weights[0].weight1 = 0.25f;
            weights[0].boneIndex0 = 1; weights[0].boneIndex1 = 0; edited.boneWeights = weights;
            Assert.IsFalse((bool)Invoke(finalizer, "SameSkinInfluences", source, edited));
        }
        finally { UnityEngine.Object.DestroyImmediate(source); UnityEngine.Object.DestroyImmediate(edited); }
    }

    private static Type FindFinalizer()
    {
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type result = assembly.GetType("VapbModelSkinFinalizer", false);
            if (result != null) return result;
        }
        Assert.Fail("VapbModelSkinFinalizer is not loaded");
        return null;
    }

    private static object CaptureLayout(Type finalizer, Mesh mesh)
    { return Invoke(finalizer, "CaptureLayout", mesh); }

    private static object Invoke(Type type, string name, params object[] args)
    {
        MethodInfo method = type.GetMethod(name, BindingFlags.NonPublic | BindingFlags.Static);
        Assert.IsNotNull(method, "Missing method " + name);
        return method.Invoke(null, args);
    }

    private static IList NewPlans(Type finalizer, int count, bool replacement)
    {
        Type prepared = finalizer.GetNestedType("PreparedTask", BindingFlags.NonPublic);
        Type taskType = finalizer.GetNestedType("Task", BindingFlags.NonPublic);
        Type listType = typeof(List<>).MakeGenericType(prepared);
        IList plans = (IList)Activator.CreateInstance(listType);
        for (int i = 0; i < count; i++)
        {
            object task = Activator.CreateInstance(taskType, true);
            taskType.GetField("kind", BindingFlags.Public | BindingFlags.Instance).SetValue(task, NormalKind);
            object plan = Activator.CreateInstance(prepared, true);
            prepared.GetField("task", BindingFlags.Public | BindingFlags.Instance).SetValue(plan, task);
            prepared.GetField("requiresReplacementEligibility", BindingFlags.Public | BindingFlags.Instance)
                .SetValue(plan, replacement);
            plans.Add(plan);
        }
        return plans;
    }

    private static Mesh TriangleWithShape()
    {
        Mesh mesh = new Mesh();
        Vector3[] vertices = { Vector3.zero, Vector3.right, Vector3.up };
        mesh.vertices = vertices;
        mesh.triangles = new[] { 0, 1, 2 };
        Vector3[] delta = { Vector3.forward, Vector3.forward, Vector3.forward };
        Vector3[] zero = { Vector3.zero, Vector3.zero, Vector3.zero };
        mesh.AddBlendShapeFrame("fixture-shape", 100f, delta, zero, zero);
        return mesh;
    }
}
