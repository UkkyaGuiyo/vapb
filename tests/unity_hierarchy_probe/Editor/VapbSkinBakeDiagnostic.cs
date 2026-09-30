// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

// Measurement controls only; no cross-runtime identity or production state mutation.
public static class VapbSkinBakeDiagnostic
{
    [Serializable] private sealed class Identity { public string guid, local_id, global_id; }
    [Serializable] private sealed class SkinRef { public Identity mesh; }
    [Serializable] private sealed class PackageObservation { public SkinRef[] skinned_renderers; }
    [Serializable] private sealed class Measure
    {
        public string provenance;
        public Vector3 renderer_lossy_scale;
        public Vector3[] mesh_vertices;
        public Vector3[] bake_default_world;
        public Vector3[] bake_false_world;
        public Vector3[] bake_true_world;
        public Vector3[] cpu_weighted_world;
        public Bounds renderer_bounds;
        public Matrix4x4 renderer_local_to_world;
        public Matrix4x4[] bone_local_to_world;
        public Matrix4x4[] bindposes;
    }
    [Serializable] private sealed class Report { public Measure[] observations; }
    public static void Run()
    {
        try
        {
            string project = Path.GetDirectoryName(Application.dataPath);
            PackageObservation source = JsonUtility.FromJson<PackageObservation>(File.ReadAllText(Path.Combine(project, "VapbHierarchyPackageSkinObservation.json")));
            string modelPath = AssetDatabase.GUIDToAssetPath(source.skinned_renderers[0].mesh.guid);
            ModelImporter importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException();
            if (!importer.isReadable) { importer.isReadable = true; importer.SaveAndReimport(); }
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/VapbHierarchy/Majun.prefab");
            var rows = new List<Measure>();
            foreach (var item in new[] { model, prefab })
            {
                string scope = item == model ? "SOURCE_MODEL" : "SELECTED_PREFAB";
                foreach (SkinnedMeshRenderer skin in item.GetComponentsInChildren<SkinnedMeshRenderer>(true)) rows.Add(Capture(skin, scope + "_ASSET"));
                GameObject instance = UnityEngine.Object.Instantiate(item);
                try
                {
                    instance.transform.position = item.transform.position;
                    instance.transform.rotation = item.transform.rotation;
                    instance.transform.localScale = item.transform.localScale;
                    foreach (SkinnedMeshRenderer skin in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true)) rows.Add(Capture(skin, scope + "_SCENE_INSTANCE"));
                }
                finally { UnityEngine.Object.DestroyImmediate(instance); }
            }
            File.WriteAllText(Path.Combine(project, "VapbSkinBakeDiagnostic.json"), JsonUtility.ToJson(new Report { observations = rows.ToArray() }, true));
            Debug.Log("VAPB_SKIN_BAKE_DIAGNOSTIC_PASS");
            EditorApplication.Exit(0);
        }
        catch { Debug.LogError("VAPB_SKIN_BAKE_DIAGNOSTIC_FAIL"); EditorApplication.Exit(1); }
    }
    private static Vector3[] Bake(SkinnedMeshRenderer skin, int mode)
    {
        var baked = new Mesh();
        try
        {
            if (mode == 0) skin.BakeMesh(baked); else skin.BakeMesh(baked, mode == 2);
            Vector3[] points = baked.vertices;
            for (int i = 0; i < points.Length; i++) points[i] = skin.transform.TransformPoint(points[i]);
            return points;
        }
        finally { UnityEngine.Object.DestroyImmediate(baked); }
    }
    private static Measure Capture(SkinnedMeshRenderer skin, string provenance)
    {
        Mesh mesh = skin.sharedMesh;
        Vector3[] vertices = mesh.vertices;
        Matrix4x4[] bindposes = mesh.bindposes;
        Transform[] bones = skin.bones;
        var matrices = new Matrix4x4[bones.Length];
        for (int i = 0; i < bones.Length; i++) matrices[i] = bones[i].localToWorldMatrix;
        var weighted = new Vector3[vertices.Length];
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            int cursor = 0;
            for (int v = 0; v < vertices.Length; v++)
                for (int n = 0; n < counts[v]; n++)
                {
                    var influence = weights[cursor++];
                    weighted[v] += influence.weight * (matrices[influence.boneIndex] * bindposes[influence.boneIndex]).MultiplyPoint3x4(vertices[v]);
                }
            if (cursor != weights.Length) throw new InvalidOperationException();
        }
        finally { counts.Dispose(); weights.Dispose(); }
        return new Measure { provenance = provenance, renderer_lossy_scale = skin.transform.lossyScale,
            mesh_vertices = vertices, bake_default_world = Bake(skin, 0), bake_false_world = Bake(skin, 1),
            bake_true_world = Bake(skin, 2), cpu_weighted_world = weighted, renderer_bounds = skin.bounds,
            renderer_local_to_world = skin.localToWorldMatrix, bone_local_to_world = matrices, bindposes = bindposes };
    }
}
