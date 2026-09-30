using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Independent public-API observation; no VAPB parser or expected projection.
public static class VapbHierarchyOracle
{
    const string Folder = "Assets/VapbHierarchy";
    [Serializable] public class Identity
    {
        public string guid, localId, globalId;
    }
    [Serializable] public class Node
    {
        public string diagnosticName;
        public Identity gameObject, transform, parentTransform;
        public Identity[] sourceChain, instanceHandles;
        public Vector3 localPosition, localScale;
        public Quaternion localRotation;
        public float[] worldMatrix;
        public RendererState[] renderers;
    }
    [Serializable] public class RendererState
    {
        public Identity component, owner, mesh, rootBone;
        public Identity[] bones;
    }
    [Serializable] public class Report
    {
        public string unityVersion;
        public int nodeCount, parentEdges, rendererOwners, skinBones, repeatedInstances;
        public Node[] nodes;
    }
    static Identity Id(UnityEngine.Object obj)
    {
        if (obj == null) return null;
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out string guid, out long localId))
            throw new InvalidOperationException("Persistent public API identity unavailable");
        return new Identity { guid = guid, localId = localId.ToString(System.Globalization.CultureInfo.InvariantCulture),
            globalId = GlobalObjectId.GetGlobalObjectIdSlow(obj).ToString() };
    }
    static Identity[] Sources(UnityEngine.Object obj)
    {
        var result = new List<Identity>();
        var seen = new HashSet<string>();
        while ((obj = PrefabUtility.GetCorrespondingObjectFromSource(obj)) != null)
        {
            Identity id = Id(obj);
            if (!seen.Add(id.globalId)) throw new InvalidOperationException("Source chain cycle");
            result.Add(id);
        }
        return result.ToArray();
    }
    static Node Observe(Transform t)
    {
        var handles = new List<Identity>();
        for (Transform ancestor = t; ancestor != null; ancestor = ancestor.parent)
            if (PrefabUtility.IsAnyPrefabInstanceRoot(ancestor.gameObject))
                handles.Add(Id(PrefabUtility.GetPrefabInstanceHandle(ancestor.gameObject)));
        return new Node {
            diagnosticName = t.name, gameObject = Id(t.gameObject), transform = Id(t),
            parentTransform = Id(t.parent), sourceChain = Sources(t.gameObject), instanceHandles = handles.ToArray(),
            localPosition = t.localPosition, localRotation = t.localRotation, localScale = t.localScale,
            worldMatrix = Enumerable.Range(0, 16).Select(i => t.localToWorldMatrix[i]).ToArray(),
            renderers = t.GetComponents<Renderer>().Select(r => {
                var skin = r as SkinnedMeshRenderer;
                var filter = r.GetComponent<MeshFilter>();
                return new RendererState { component = Id(r), owner = Id(t.gameObject),
                    mesh = Id(skin != null ? skin.sharedMesh : filter != null ? filter.sharedMesh : null),
                    rootBone = Id(skin != null ? skin.rootBone : null),
                    bones = skin != null ? skin.bones.Select(Id).ToArray() : new Identity[0] };
            }).ToArray()
        };
    }
    public static void Run()
    {
        try
        {
            string output = Environment.GetEnvironmentVariable("VAPB_HIERARCHY_OUTPUT");
            if (string.IsNullOrEmpty(output)) throw new InvalidOperationException("Missing output directory");
            Directory.CreateDirectory(output);
            AssetDatabase.Refresh();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Folder + "/Model.fbx");
            if (model == null) throw new InvalidOperationException("Generate synthetic Model.fbx first");
            var native = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(native, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            var skin = native.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var root = new GameObject("Majun");
            native.transform.SetParent(root.transform, false);
            native.name = "Armature";
            skin.transform.SetParent(root.transform, true);
            skin.name = "Body";
            var head = new GameObject("Head"); head.transform.SetParent(root.transform, false);
            foreach (string label in new[] { "Face", "Hair" })
                new GameObject(label).transform.SetParent(head.transform, false);
            // Attachment is selected by authoritative skin bone order, not name.
            if (skin.bones.Length != 2 || skin.bones[1].parent != skin.bones[0])
                throw new InvalidOperationException("Synthetic skin fixture must have an ordered two-bone chain");
            new GameObject("Attachment").transform.SetParent(skin.bones[1], false);
            var accessory = new GameObject("AccessorySource");
            var accessoryAsset = PrefabUtility.SaveAsPrefabAsset(accessory, Folder + "/Accessory.prefab");
            UnityEngine.Object.DestroyImmediate(accessory);
            foreach (string label in new[] { "AccessoryLeft", "AccessoryRight" })
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(accessoryAsset);
                instance.name = label; instance.transform.SetParent(root.transform, false);
            }
            PrefabUtility.SaveAsPrefabAsset(root, Folder + "/Majun.prefab");
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            var saved = AssetDatabase.LoadAssetAtPath<GameObject>(Folder + "/Majun.prefab");
            Node[] nodes = saved.GetComponentsInChildren<Transform>(true).Select(Observe).ToArray();
            if (nodes.Select(n => n.transform.globalId).Distinct().Count() != nodes.Length)
                throw new InvalidOperationException("Ambiguous occurrence identity");
            string accessoryGuid = AssetDatabase.AssetPathToGUID(Folder + "/Accessory.prefab");
            var report = new Report { unityVersion = Application.unityVersion, nodes = nodes,
                nodeCount = nodes.Length, parentEdges = nodes.Count(n => n.parentTransform != null),
                rendererOwners = nodes.Sum(n => n.renderers.Length),
                skinBones = nodes.Sum(n => n.renderers.Sum(r => r.bones.Length)),
                repeatedInstances = nodes.Count(n => n.sourceChain.Any(s => s.guid == accessoryGuid)) };
            if (report.repeatedInstances != 2 || report.rendererOwners != 1 || report.skinBones != 2)
                throw new InvalidOperationException("Synthetic fixture semantic coverage missing");
            File.WriteAllText(Path.Combine(output, "unity_oracle.json"), JsonUtility.ToJson(report, true));
            AssetDatabase.ExportPackage(Folder, Path.Combine(output, "Majun.unitypackage"),
                ExportPackageOptions.Recurse | ExportPackageOptions.IncludeDependencies);
            Debug.Log("VAPB_HIERARCHY_ORACLE_PASS nodes=" + report.nodeCount + " edges=" + report.parentEdges
                + " renderers=" + report.rendererOwners + " bones=" + report.skinBones + " repeated=" + report.repeatedInstances);
            EditorApplication.Exit(0);
        }
        catch (Exception error) { Debug.LogException(error); EditorApplication.Exit(1); }
    }
}
