// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Exact package public Skin slot observation; IDs are identities, positions are diagnostics.
[InitializeOnLoad]
public static class VapbHierarchyPackageSkinObservation
{
    private const string Phase = "VAPB_HIERARCHY_PACKAGE_SKIN_PHASE";
    [Serializable] private sealed class Identity { public string guid, local_id, global_id; }
    [Serializable] private sealed class Bone { public Identity transform, parent; public Vector3 world_origin; }
    [Serializable] private sealed class Skin
    {
        public Identity renderer, owner, mesh;
        public Bone root_bone;
        public Bone[] ordered_bones;
        public int bindpose_count;
        public Vector3[] baked_world_vertices; public Vector3[] baked_world_triangle_corners;
    }
    [Serializable] private sealed class Report
    {
        public string status = "OBSERVED_PUBLIC_API";
        public string unity_version;
        public Identity selected_prefab;
        public int node_count;
        public Skin[] skinned_renderers;
    }
    static VapbHierarchyPackageSkinObservation()
    {
        AssetDatabase.importPackageCompleted += Complete;
        AssetDatabase.importPackageFailed += Failed;
        if (SessionState.GetString(Phase, "") == "ready") EditorApplication.delayCall += Capture;
    }
    public static void Run()
    {
        SessionState.SetString(Phase, "importing");
        AssetDatabase.ImportPackage(Path.Combine(Path.GetDirectoryName(Application.dataPath), "ExactPackage.unitypackage"), false);
    }
    private static void Complete(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "ready");
        EditorApplication.delayCall += Capture;
    }
    private static void Failed(string name, string reason) { Fail(); }
    private static Identity Id(UnityEngine.Object asset)
    {
        if (asset == null) return null;
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id) || id == 0)
            throw new InvalidOperationException("OBJECT_ID_UNAVAILABLE");
        return new Identity { guid = guid, local_id = id.ToString(CultureInfo.InvariantCulture),
            global_id = GlobalObjectId.GetGlobalObjectIdSlow(asset).ToString() };
    }
    private static Bone ObserveBone(Transform transform)
    { return transform == null ? null : new Bone { transform = Id(transform), parent = Id(transform.parent), world_origin = transform.position }; }
    public static void Capture()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        { EditorApplication.delayCall += Capture; return; }
        if (SessionState.GetString(Phase, "") != "ready") return;
        SessionState.SetString(Phase, "capturing");
        try
        {
            string prefabPath = Environment.GetEnvironmentVariable("VAPB_HIERARCHY_SELECTED_PREFAB_PATH");
            if (string.IsNullOrEmpty(prefabPath)) prefabPath = "Assets/VapbHierarchy/Majun.prefab";
            if (!prefabPath.StartsWith("Assets/", StringComparison.Ordinal) || prefabPath.Contains(".."))
                throw new InvalidOperationException("SELECTED_PREFAB_PATH_INVALID");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null) throw new InvalidOperationException("PREFAB_MISSING");
            var rows = new List<Skin>();
            foreach (SkinnedMeshRenderer skin in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                string modelPath = AssetDatabase.GetAssetPath(skin.sharedMesh);
                var importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
                if (importer == null) throw new InvalidOperationException("MODEL_IMPORT_MISSING");
                // Enable reading solely on the isolated diagnostic copy; original package is immutable.
                if (!importer.isReadable) { importer.isReadable = true; importer.SaveAndReimport(); }
                Transform[] bones = skin.bones;
                var ordered = new Bone[bones.Length];
                for (int i = 0; i < bones.Length; i++) ordered[i] = ObserveBone(bones[i]);
                var baked = new Mesh();
                Vector3[] vertices;
                try { skin.BakeMesh(baked, true); vertices = baked.vertices; for (int i = 0; i < vertices.Length; i++) vertices[i] = skin.transform.TransformPoint(vertices[i]); }
                finally { UnityEngine.Object.DestroyImmediate(baked); }
                rows.Add(new Skin { renderer = Id(skin), owner = Id(skin.transform), mesh = Id(skin.sharedMesh),
                    root_bone = ObserveBone(skin.rootBone), ordered_bones = ordered,
                    bindpose_count = skin.sharedMesh.bindposes.Length, baked_world_vertices = vertices,
                    baked_world_triangle_corners = skin.sharedMesh.triangles.Select(index => vertices[index]).ToArray() });
            }
            var report = new Report { unity_version = Application.unityVersion, selected_prefab = Id(prefab),
                node_count = prefab.GetComponentsInChildren<Transform>(true).Length, skinned_renderers = rows.ToArray() };
            MethodInfo observe = typeof(VapbHierarchyOracle).GetMethod("Observe", BindingFlags.NonPublic | BindingFlags.Static);
            if (observe == null) throw new InvalidOperationException("PUBLIC_ORACLE_OBSERVER_MISSING");
            VapbHierarchyOracle.Node[] nodes = prefab.GetComponentsInChildren<Transform>(true)
                .Select(t => (VapbHierarchyOracle.Node)observe.Invoke(null, new object[] { t })).ToArray();
            if (nodes.Select(n => n.transform.globalId).Distinct().Count() != nodes.Length)
                throw new InvalidOperationException("OCCURRENCE_IDENTITY_DUPLICATE");
            var oracle = new VapbHierarchyOracle.Report { unityVersion = Application.unityVersion, nodes = nodes,
                nodeCount = nodes.Length, parentEdges = nodes.Count(n => n.parentTransform != null),
                rendererOwners = nodes.Sum(n => n.renderers.Length),
                skinBones = nodes.Sum(n => n.renderers.Sum(r => r.bones.Length)),
                repeatedInstances = nodes.Where(n => n.sourceChain.Length > 0)
                    .GroupBy(n => n.sourceChain[0].globalId).Where(g => g.Count() > 1).Sum(g => g.Count()) };
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(Application.dataPath), "unity_oracle.json"), JsonUtility.ToJson(oracle, true));
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(Application.dataPath), "VapbHierarchyPackageSkinObservation.json"), JsonUtility.ToJson(report, true));
            SessionState.SetString(Phase, "");
            Debug.Log("VAPB_HIERARCHY_PACKAGE_SKIN_PASS");
            EditorApplication.Exit(0);
        }
        catch { Fail(); }
    }
    private static void Fail()
    {
        SessionState.SetString(Phase, "");
        Debug.LogError("VAPB_HIERARCHY_PACKAGE_SKIN_FAIL");
        EditorApplication.Exit(1);
    }
}
