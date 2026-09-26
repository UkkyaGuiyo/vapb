using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Public synthetic oracle: one skin, at most four influences per vertex, no active blendshapes.
public static class VapbPosedBakeProbe
{
    [Serializable] private class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private class Task { public string prefab_guid, variant_path; }
    [Serializable] private class Report
    {
        public bool pass;
        public string error;
        public bool rootOutsideSlots, posedAgainstBind, bonesPreserved, changedByEdit;
        public int vertices, changedRawVertices;
        public float maxOriginalBakeError, maxVariantBakeError, maxBakedDelta, maxRawDelta;
        public float maxUneditedBakedDelta;
    }
    private static Vector3 Manual(SkinnedMeshRenderer skin, Mesh mesh, int index)
    {
        BoneWeight w = mesh.boneWeights[index];
        Vector3 sum = Vector3.zero;
        int[] ids = { w.boneIndex0, w.boneIndex1, w.boneIndex2, w.boneIndex3 };
        float[] weights = { w.weight0, w.weight1, w.weight2, w.weight3 };
        for (int i = 0; i < 4; i++)
            if (weights[i] != 0f)
                sum += weights[i] * skin.transform.worldToLocalMatrix.MultiplyPoint3x4(
                    skin.bones[ids[i]].localToWorldMatrix.MultiplyPoint3x4(
                        mesh.bindposes[ids[i]].MultiplyPoint3x4(mesh.vertices[index])));
        return sum;
    }
    public static void Run()
    {
        var r = new Report();
        try
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Application.dataPath, "VAPBExport/manifest.json")));
            var task = manifest.reference_rebind_tasks.Single();
            var original = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.prefab_guid))
                .GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path)
                .GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            Mesh a = original.sharedMesh, b = variant.sharedMesh;
            if (a.vertexCount != b.vertexCount || a.boneWeights.Length != a.vertexCount ||
                b.boneWeights.Length != b.vertexCount) throw new InvalidOperationException("MESH_UNREADABLE");
            r.vertices = a.vertexCount;
            r.rootOutsideSlots = Array.IndexOf(original.bones, original.rootBone) < 0;
            r.bonesPreserved = original.rootBone == PrefabUtility.GetCorrespondingObjectFromSource(variant.rootBone)
                && original.bones.Length == variant.bones.Length;
            for (int i = 0; i < original.bones.Length && r.bonesPreserved; i++)
                r.bonesPreserved &= original.bones[i] == PrefabUtility.GetCorrespondingObjectFromSource(variant.bones[i]);
            for (int i = 0; i < original.bones.Length; i++)
            {
                Matrix4x4 current = original.bones[i].worldToLocalMatrix * original.transform.localToWorldMatrix;
                for (int j = 0; j < 16; j++)
                    if (Math.Abs(current[j] - a.bindposes[i][j]) > 0.01f) r.posedAgainstBind = true;
            }
            var bakedA = new Mesh(); var bakedB = new Mesh();
            try
            {
                original.BakeMesh(bakedA);
                variant.BakeMesh(bakedB);
                if (bakedA.vertexCount != a.vertexCount || bakedB.vertexCount != b.vertexCount)
                    throw new InvalidOperationException("BAKE_COUNT_MISMATCH");
                for (int i = 0; i < a.vertexCount; i++)
                {
                    r.maxOriginalBakeError = Math.Max(r.maxOriginalBakeError,
                        (bakedA.vertices[i] - Manual(original, a, i)).magnitude);
                    r.maxVariantBakeError = Math.Max(r.maxVariantBakeError,
                        (bakedB.vertices[i] - Manual(variant, b, i)).magnitude);
                    float bakedDelta = (bakedB.vertices[i] - bakedA.vertices[i]).magnitude;
                    float rawDelta = (b.vertices[i] - a.vertices[i]).magnitude;
                    r.maxBakedDelta = Math.Max(r.maxBakedDelta, bakedDelta);
                    r.maxRawDelta = Math.Max(r.maxRawDelta, rawDelta);
                    if (rawDelta > 0.000001f) r.changedRawVertices++;
                    else r.maxUneditedBakedDelta = Math.Max(r.maxUneditedBakedDelta, bakedDelta);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(bakedA); UnityEngine.Object.DestroyImmediate(bakedB); }
            r.changedByEdit = r.changedRawVertices > 0 && r.maxBakedDelta > 0.000001f &&
                r.maxUneditedBakedDelta < 0.00001f;
            r.pass = r.rootOutsideSlots && r.posedAgainstBind && r.bonesPreserved && r.changedByEdit &&
                r.maxOriginalBakeError < 0.0001f && r.maxVariantBakeError < 0.0001f;
        }
        catch (Exception e)
        {
            r.error = e is InvalidOperationException &&
                (e.Message == "MESH_UNREADABLE" || e.Message == "BAKE_COUNT_MISMATCH") ?
                e.Message : "UNEXPECTED_EXCEPTION";
        }
        try
        {
            File.WriteAllText(Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                "PosedBakeResult.json"), JsonUtility.ToJson(r, true));
        }
        catch { EditorApplication.Exit(1); return; }
        EditorApplication.Exit(r.pass ? 0 : 1);
    }
}
