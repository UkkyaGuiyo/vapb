// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Separate public-API observation during the stamped revision. Does not extend v1 witness schema.
public static class VapbHierarchyBoneObservation
{
    [Serializable] private sealed class Identity
    {
        public string model_uid;
        public string transform_local_id;
        public string game_object_local_id; public string parent_transform_local_id; public string parent_model_uid; public Vector3 world_origin; public float[] local_to_world_matrix;
    }
    [Serializable] private sealed class RendererRow
    {
        public string renderer_model_uid;
        public string renderer_local_id;
        public string mesh_local_id;
        public Identity root_bone;
        public Identity[] ordered_bones; public int bindpose_count; public Vector3[] baked_world_vertices; public Vector3[] baked_world_triangle_corners;
    }
    [Serializable] private sealed class Observation
    {
        public string schema_version = "vapb-hierarchy-bone-public-api-observation-1";
        public string status = "UNKNOWN";
        public string unity_version;
        public string model_guid;
        public string source_fbx_sha256;
        public string source_meta_sha256;
        public RendererRow[] skinned_renderers; public Identity[] model_frames;
    }
    private static string Id(UnityEngine.Object asset, string guid)
    {
        if (asset == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset,
            out string actualGuid, out long id) || actualGuid != guid || id == 0)
            throw new InvalidOperationException("OBJECT_ID_UNAVAILABLE");
        return id.ToString(CultureInfo.InvariantCulture);
    }
    private static string Uid(Transform transform)
    {
        if (transform == null) throw new InvalidOperationException("ROOT_BONE_UNAVAILABLE");
        VapbSourceBoneMarker[] markers = transform.GetComponents<VapbSourceBoneMarker>();
        if (markers.Length != 1 || !long.TryParse(markers[0].sourceModelUid,
            NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out long uid) || uid == 0)
            throw new InvalidOperationException("BONE_MARKER_UNAVAILABLE");
        return uid.ToString(CultureInfo.InvariantCulture);
    }
    private static Identity Bone(Transform transform, string guid)
    {
        return new Identity { model_uid = Uid(transform), transform_local_id = Id(transform, guid),
            game_object_local_id = Id(transform.gameObject, guid), parent_transform_local_id = transform.parent == null ? "0" : Id(transform.parent, guid), parent_model_uid = ParentUid(transform.parent), world_origin = transform.position, local_to_world_matrix = Matrix(transform.localToWorldMatrix) };
    }
    private static string ParentUid(Transform parent) { if (parent == null) return "NONE"; VapbSourceBoneMarker[] markers = parent.GetComponents<VapbSourceBoneMarker>(); return markers.Length == 1 ? Uid(parent) : "UNKNOWN"; }
    public static void Capture(byte[] original, byte[] originalMeta)
    {
        string path = VapbBoneWitnessPostprocessor.ModelPath;
        string guid = AssetDatabase.AssetPathToGUID(path);
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (model == null || Application.unityVersion != "2022.3.22f1")
            throw new InvalidOperationException("MODEL_IMPORT_MISSING");
        var rows = new List<RendererRow>();
        var frames = new List<Identity>();
        foreach (VapbSourceBoneMarker marker in model.GetComponentsInChildren<VapbSourceBoneMarker>(true))
            frames.Add(Bone(marker.transform, guid));
        foreach (SkinnedMeshRenderer renderer in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            Transform[] bones = renderer.bones;
            var ordered = new Identity[bones.Length];
            for (int i = 0; i < bones.Length; i++) ordered[i] = Bone(bones[i], guid);
            rows.Add(new RendererRow { renderer_model_uid = Uid(renderer.transform),
                renderer_local_id = Id(renderer, guid), mesh_local_id = Id(renderer.sharedMesh, guid),
                root_bone = Bone(renderer.rootBone, guid), ordered_bones = ordered, bindpose_count = renderer.sharedMesh.bindposes.Length, baked_world_vertices = Bake(renderer), baked_world_triangle_corners = BakeCorners(renderer) });
        }
        if (rows.Count == 0) throw new InvalidOperationException("SKIN_OBSERVATION_EMPTY");
        var report = new Observation { status = "OBSERVED_STAMPED_PENDING_CONTROL_REPORT",
            unity_version = Application.unityVersion, model_guid = guid,
            source_fbx_sha256 = Hash(original), source_meta_sha256 = Hash(originalMeta),
            skinned_renderers = rows.ToArray(), model_frames = frames.ToArray() };
        File.WriteAllText(Path.Combine(Path.GetDirectoryName(Application.dataPath), "VapbHierarchyBoneObservation.json"),
            JsonUtility.ToJson(report, true));
    }
    private static Vector3[] BakeCorners(SkinnedMeshRenderer skin) { Vector3[] vertices = Bake(skin); int[] triangles = skin.sharedMesh.triangles; Vector3[] corners = new Vector3[triangles.Length]; for (int i = 0; i < triangles.Length; i++) corners[i] = vertices[triangles[i]]; return corners; }
    private static Vector3[] Bake(SkinnedMeshRenderer skin) { var mesh = new Mesh(); try { skin.BakeMesh(mesh, true); Vector3[] vertices = mesh.vertices; for (int i = 0; i < vertices.Length; i++) vertices[i] = skin.transform.TransformPoint(vertices[i]); return vertices; } finally { UnityEngine.Object.DestroyImmediate(mesh); } }
    private static float[] Matrix(Matrix4x4 matrix) { var values = new float[16]; for (int i = 0; i < 16; i++) values[i] = matrix[i]; return values; }
    private static string Hash(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
}
