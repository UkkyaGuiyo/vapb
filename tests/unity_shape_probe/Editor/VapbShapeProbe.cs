// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Unity channel indices are scoped to the exact Mesh asset revision. Names are diagnostics.
[InitializeOnLoad]
public static class VapbShapeProbe
{
    const string Phase = "VAPB_SHAPE_PROBE_PHASE";
    static string ModelPath { get { return SelectedPath("VAPB_SHAPE_MODEL_PATH", "Assets/VapbShape/Model.fbx"); } }
    static string PrefabPath { get { return SelectedPath("VAPB_SHAPE_SELECTED_PREFAB_PATH", "Assets/VapbShape/ShapeOccurrences.prefab"); } }
    static string SelectedPath(string variable, string fallback)
    {
        string path = Environment.GetEnvironmentVariable(variable);
        if (string.IsNullOrEmpty(path)) path = fallback;
        if (!path.StartsWith("Assets/", StringComparison.Ordinal) || path.Contains("..")) throw new InvalidOperationException("ASSET_PATH_INVALID");
        return path;
    }
    [Serializable] public sealed class Identity { public string guid, local_id; }
    [Serializable] public sealed class Frame
    {
        public int frame_index; public float frame_weight;
        public string delta_signature;
        public Vector3[] delta_vertices, delta_normals, delta_tangents;
    }
    [Serializable] public sealed class Channel
    { public int channel_index; public string diagnostic_name; public Frame[] frames; }
    [Serializable] public sealed class MeshRow
    { public Identity mesh; public int vertex_count; public Vector3[] vertices; public Channel[] channels; }
    [Serializable] public sealed class RendererRow
    {
        public Identity renderer, mesh, owner_transform, root_bone;
        public Identity[] ordered_bones;
        public float[] current_weights, serialized_weights;
        public Vector3[] baked_world_vertices;
    }
    [Serializable] public sealed class Report
    {
        public string schema = "vapb-shape-public-api-observation-1";
        public string status = "OBSERVED_PUBLIC_API", unity_version;
        public string package_sha256, source_fbx_sha256, source_meta_sha256, selected_prefab_path;
        public Identity selected_prefab;
        public MeshRow[] meshes;
        public RendererRow[] source_renderers, prefab_renderers;
        public bool source_revision_unchanged;
        public bool include_frame_deltas;
        public string channel_bridge = "UNITY_MESH_INDEX_ONLY_RAW_FBX_BRIDGE_UNPROVEN";
    }
    static string Project { get { return Path.GetDirectoryName(Application.dataPath); } }
    static VapbShapeProbe()
    {
        AssetDatabase.importPackageCompleted += Imported;
        AssetDatabase.importPackageFailed += (name, reason) => Fail("PACKAGE_IMPORT_FAILED");
        if (SessionState.GetString(Phase, "") == "oracle_ready") EditorApplication.delayCall += Capture;
    }
    public static void Create()
    {
        try
        {
            var importer = AssetImporter.GetAtPath(ModelPath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("MODEL_IMPORT_MISSING");
            importer.isReadable = true; importer.importBlendShapes = true; importer.SaveAndReimport();
            byte[] fbx = File.ReadAllBytes(Path.Combine(Project, ModelPath));
            byte[] meta = File.ReadAllBytes(Path.Combine(Project, ModelPath + ".meta"));
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            var original = source.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            if (original.sharedMesh.blendShapeCount != 3) throw new InvalidOperationException("THREE_CHANNEL_FIXTURE_REQUIRED");
            var root = new GameObject("ShapeOccurrences");
            try
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(source);
                instance.transform.SetParent(root.transform, false);
                PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                var first = instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                float[] firstWeights = { 25, 60, 0 }, secondWeights = { 75, 0, 35 };
                for (int i = 0; i < 3; i++) first.SetBlendShapeWeight(i, firstWeights[i]);
                var secondOwner = new GameObject("SecondRendererOccurrence");
                secondOwner.transform.SetParent(first.transform.parent, false);
                secondOwner.transform.localPosition = first.transform.localPosition;
                secondOwner.transform.localRotation = first.transform.localRotation;
                secondOwner.transform.localScale = first.transform.localScale;
                var second = secondOwner.AddComponent<SkinnedMeshRenderer>();
                second.sharedMesh = first.sharedMesh; second.bones = first.bones; second.rootBone = first.rootBone;
                second.sharedMaterials = first.sharedMaterials; second.localBounds = first.localBounds;
                for (int i = 0; i < 3; i++) second.SetBlendShapeWeight(i, secondWeights[i]);
                if (Environment.GetEnvironmentVariable("VAPB_SHAPE_TRUNCATE_WEIGHTS") == "1")
                {
                    SetStoredWeightCount(first, 1);
                    SetStoredWeightCount(second, 0);
                }
                if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) != null) throw new InvalidOperationException("OUTPUT_OCCUPIED");
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            if (Hash(fbx) != FileHash(ModelPath) || Hash(meta) != FileHash(ModelPath + ".meta")) throw new InvalidOperationException("SOURCE_REVISION_CHANGED");
            string output = Path.Combine(Project, "ShapeOccurrences.unitypackage");
            if (File.Exists(output)) throw new InvalidOperationException("OUTPUT_OCCUPIED");
            AssetDatabase.ExportPackage("Assets/VapbShape", output, ExportPackageOptions.Recurse | ExportPackageOptions.IncludeDependencies);
            File.WriteAllBytes(Path.Combine(Project, "Source.fbx"), fbx);
            File.WriteAllBytes(Path.Combine(Project, "Source.fbx.meta"), meta);
            File.Copy(output, Path.Combine(Project, "ExactPackage.unitypackage"));
            WriteObservation("FixtureShapeObservation.json");
            Debug.Log("VAPB_SHAPE_CREATE_PASS"); EditorApplication.Exit(0);
        }
        catch (Exception error) { Fail(error is InvalidOperationException ? error.Message : "CREATE_FAILED"); }
    }
    public static void Run()
    {
        SessionState.SetString(Phase, "oracle_importing");
        AssetDatabase.ImportPackage(Path.Combine(Project, "ExactPackage.unitypackage"), false);
    }
    static void Imported(string name)
    {
        if (SessionState.GetString(Phase, "") != "oracle_importing") return;
        SessionState.SetString(Phase, "oracle_ready"); EditorApplication.delayCall += Capture;
    }
    static void Capture()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating) { EditorApplication.delayCall += Capture; return; }
        if (SessionState.GetString(Phase, "") != "oracle_ready") return;
        SessionState.SetString(Phase, "capturing");
        try { WriteObservation("UnityShapeObservation.json"); SessionState.SetString(Phase, ""); Debug.Log("VAPB_SHAPE_ORACLE_PASS"); EditorApplication.Exit(0); }
        catch (Exception error) { Fail(error is InvalidOperationException ? error.Message : "OBSERVATION_FAILED"); }
    }
    static Identity Id(UnityEngine.Object value)
    {
        if (value == null) return null;
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string guid, out long id) || id == 0) throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
        return new Identity { guid = guid, local_id = id.ToString(CultureInfo.InvariantCulture) };
    }
    static MeshRow ObserveMesh(Mesh mesh)
    {
        var channels = new List<Channel>();
        for (int c = 0; c < mesh.blendShapeCount; c++)
        {
            var frames = new List<Frame>();
            for (int f = 0; f < mesh.GetBlendShapeFrameCount(c); f++)
            {
                var vertices = new Vector3[mesh.vertexCount]; var normals = new Vector3[mesh.vertexCount]; var tangents = new Vector3[mesh.vertexCount];
                mesh.GetBlendShapeFrameVertices(c, f, vertices, normals, tangents);
                bool include = Environment.GetEnvironmentVariable("VAPB_SHAPE_INCLUDE_FRAME_DELTAS") != "0";
                frames.Add(new Frame { frame_index = f, frame_weight = mesh.GetBlendShapeFrameWeight(c, f),
                    delta_signature = DeltaSignature(vertices, normals, tangents),
                    delta_vertices = include ? vertices : null, delta_normals = include ? normals : null, delta_tangents = include ? tangents : null });
            }
            channels.Add(new Channel { channel_index = c, diagnostic_name = mesh.GetBlendShapeName(c), frames = frames.ToArray() });
        }
        return new MeshRow { mesh = Id(mesh), vertex_count = mesh.vertexCount, vertices = mesh.vertices, channels = channels.ToArray() };
    }
    static RendererRow ObserveRenderer(SkinnedMeshRenderer skin)
    {
        var weights = Enumerable.Range(0, skin.sharedMesh.blendShapeCount).Select(skin.GetBlendShapeWeight).ToArray();
        var serialized = new SerializedObject(skin).FindProperty("m_BlendShapeWeights");
        if (serialized == null || !serialized.isArray) throw new InvalidOperationException("SERIALIZED_WEIGHTS_UNAVAILABLE");
        var stored = Enumerable.Range(0, serialized.arraySize).Select(i => serialized.GetArrayElementAtIndex(i).floatValue).ToArray();
        var baked = new Mesh(); Vector3[] world;
        try { skin.BakeMesh(baked, true); world = baked.vertices.Select(skin.transform.TransformPoint).ToArray(); }
        finally { UnityEngine.Object.DestroyImmediate(baked); }
        return new RendererRow { renderer = Id(skin), mesh = Id(skin.sharedMesh), owner_transform = Id(skin.transform), root_bone = Id(skin.rootBone), ordered_bones = skin.bones.Select(Id).ToArray(), current_weights = weights, serialized_weights = stored, baked_world_vertices = world };
    }
    static void SetStoredWeightCount(SkinnedMeshRenderer skin, int count)
    {
        var serialized = new SerializedObject(skin);
        var weights = serialized.FindProperty("m_BlendShapeWeights");
        if (weights == null || !weights.isArray) throw new InvalidOperationException("SERIALIZED_WEIGHTS_UNAVAILABLE");
        weights.arraySize = count;
        serialized.ApplyModifiedPropertiesWithoutUndo();
    }
    static void WriteObservation(string file)
    {
        byte[] original = File.ReadAllBytes(Path.Combine(Project, "Source.fbx")), meta = File.ReadAllBytes(Path.Combine(Project, "Source.fbx.meta"));
        if (Hash(original) != FileHash(ModelPath) || Hash(meta) != FileHash(ModelPath + ".meta")) throw new InvalidOperationException("EXACT_SOURCE_REVISION_MISMATCH");
        var source = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath); var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        var skins = prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        if (skins.Length == 0) throw new InvalidOperationException("PREFAB_SKIN_MISSING");
        var sourceSkins = source.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        var meshes = sourceSkins.Select(skin => skin.sharedMesh).Concat(skins.Select(skin => skin.sharedMesh)).Distinct().Select(ObserveMesh).ToArray();
        var report = new Report { unity_version = Application.unityVersion, package_sha256 = Hash(File.ReadAllBytes(Path.Combine(Project, "ExactPackage.unitypackage"))), source_fbx_sha256 = Hash(original), source_meta_sha256 = Hash(meta), selected_prefab_path = PrefabPath, selected_prefab = Id(prefab), meshes = meshes, source_renderers = sourceSkins.Select(ObserveRenderer).ToArray(), prefab_renderers = skins.Select(ObserveRenderer).ToArray(), source_revision_unchanged = true,
            include_frame_deltas = Environment.GetEnvironmentVariable("VAPB_SHAPE_INCLUDE_FRAME_DELTAS") != "0" };
        File.WriteAllText(Path.Combine(Project, file), JsonUtility.ToJson(report, true));
    }
    static string FileHash(string path) { return Hash(File.ReadAllBytes(Path.Combine(Project, path))); }
    static string DeltaSignature(params Vector3[][] arrays)
    {
        using (var stream = new MemoryStream()) using (var writer = new BinaryWriter(stream))
        {
            foreach (var vectors in arrays) { writer.Write(vectors.Length); foreach (var v in vectors) { writer.Write(v.x); writer.Write(v.y); writer.Write(v.z); } }
            writer.Flush(); return Hash(stream.ToArray());
        }
    }
    static string Hash(byte[] bytes) { using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    static void Fail(string code) { SessionState.SetString(Phase, ""); Debug.LogError("VAPB_SHAPE_PROBE_FAIL " + code); EditorApplication.Exit(1); }
}
