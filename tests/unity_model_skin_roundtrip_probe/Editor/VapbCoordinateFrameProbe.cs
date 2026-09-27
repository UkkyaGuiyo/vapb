using System;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using Unity.Collections;
using UnityEditor;
using UnityEngine;

// Public synthetic FBX coordinate-frame observation. No asset writes.
public static class VapbCoordinateFrameProbe
{
    private const string AssetPath = "Assets/VapbCoordinateFrame/Input.fbx";
    private const string ResultName = "VapbCoordinateFrameSnapshot.json";

    [Serializable] private sealed class Snapshot
    {
        public bool pass, fbx_unchanged, meta_unchanged, hashes_unchanged, unit_root, finite_world_positions;
        public string error, unity_version, source_asset_guid, asset_guid, mesh_file_id, source_sha256;
        public string fbx_sha256_before, fbx_sha256_after;
        public string meta_sha256_before, meta_sha256_after;
        public int renderer_count, bone_count, vertex_count;
        public float importer_file_scale, importer_global_scale;
        public bool importer_use_file_scale, importer_bake_axis_conversion;
        public Vector3 root_position, root_scale;
        public Quaternion root_rotation;
        public float[] renderer_world_matrix;
        public Vector3[] source_local_vertices, world_positions;
    }

    public static void Run()
    {
        var result = new Snapshot { error = "UNEXPECTED_EXCEPTION", unity_version = Application.unityVersion };
        try
        {
            string diskPath = Path.Combine(Application.dataPath, "VapbCoordinateFrame/Input.fbx");
            if (!File.Exists(diskPath) || !File.Exists(diskPath + ".meta"))
                throw new InvalidOperationException("INPUT_MISSING");
            result.fbx_sha256_before = Hash(diskPath);
            result.meta_sha256_before = Hash(diskPath + ".meta");
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(AssetPath);
            if (root == null) throw new InvalidOperationException("MODEL_UNAVAILABLE");
            SkinnedMeshRenderer[] renderers = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            result.renderer_count = renderers.Length;
            if (renderers.Length != 1 || renderers[0].sharedMesh == null)
                throw new InvalidOperationException("RENDERER_INVALID");
            SkinnedMeshRenderer skin = renderers[0];
            result.bone_count = skin.bones.Length;
            if (result.bone_count != 1) throw new InvalidOperationException("BONES_INVALID");
            result.root_position = root.transform.localPosition;
            result.root_rotation = root.transform.localRotation;
            result.root_scale = root.transform.localScale;
            result.unit_root = Approximately(result.root_position, Vector3.zero) &&
                Approximately(result.root_scale, Vector3.one) &&
                Quaternion.Angle(result.root_rotation, Quaternion.identity) < 0.001f;
            string meshGuid;
            long meshId;
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.sharedMesh, out meshGuid, out meshId) ||
                AssetDatabase.AssetPathToGUID(AssetPath) != meshGuid)
                throw new InvalidOperationException("MESH_ID_INVALID");
            result.source_asset_guid = meshGuid;
            result.asset_guid = meshGuid;
            result.mesh_file_id = meshId.ToString(CultureInfo.InvariantCulture);
            var importer = AssetImporter.GetAtPath(AssetPath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("MODEL_IMPORTER_MISSING");
            result.importer_file_scale = importer.fileScale;
            result.importer_global_scale = importer.globalScale;
            result.importer_use_file_scale = importer.useFileScale;
            result.importer_bake_axis_conversion = importer.bakeAxisConversion;
            using (Mesh.MeshDataArray data = MeshUtility.AcquireReadOnlyMeshData(skin.sharedMesh))
            using (var vertices = new NativeArray<Vector3>(data[0].vertexCount, Allocator.Temp))
            {
                data[0].GetVertices(vertices);
                result.source_local_vertices = vertices.ToArray();
            }
            result.vertex_count = result.source_local_vertices.Length;
            if (result.vertex_count == 0) throw new InvalidOperationException("VERTICES_MISSING");
            Matrix4x4 matrix = skin.localToWorldMatrix;
            result.renderer_world_matrix = Matrix(matrix);
            result.world_positions = new Vector3[result.vertex_count];
            result.finite_world_positions = true;
            for (int i = 0; i < result.vertex_count; i++)
            {
                result.world_positions[i] = matrix.MultiplyPoint3x4(result.source_local_vertices[i]);
                result.finite_world_positions &= Finite(result.world_positions[i]);
            }
            result.fbx_sha256_after = Hash(diskPath);
            result.meta_sha256_after = Hash(diskPath + ".meta");
            result.fbx_unchanged = result.fbx_sha256_before == result.fbx_sha256_after;
            result.meta_unchanged = result.meta_sha256_before == result.meta_sha256_after;
            result.hashes_unchanged = result.fbx_unchanged && result.meta_unchanged;
            result.source_sha256 = result.fbx_sha256_after;
            result.pass = result.finite_world_positions && result.hashes_unchanged;
            result.error = result.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error)
        {
            result.pass = false;
            result.error = error is InvalidOperationException &&
                (error.Message == "INPUT_MISSING" || error.Message == "MODEL_UNAVAILABLE" ||
                 error.Message == "RENDERER_INVALID" || error.Message == "BONES_INVALID" ||
                 error.Message == "MESH_ID_INVALID" || error.Message == "VERTICES_MISSING") ?
                error.Message : "UNEXPECTED_EXCEPTION";
        }
        string resultPath = Path.Combine(Path.GetDirectoryName(Application.dataPath), ResultName);
        try { File.WriteAllText(resultPath, JsonUtility.ToJson(result, true)); }
        catch { result.pass = false; }
        EditorApplication.Exit(result.pass ? 0 : 1);
    }

    private static bool Approximately(Vector3 left, Vector3 right)
    { return (left - right).sqrMagnitude < 1e-10f; }
    private static bool Finite(Vector3 value)
    {
        return !float.IsNaN(value.x) && !float.IsNaN(value.y) && !float.IsNaN(value.z) &&
            !float.IsInfinity(value.x) && !float.IsInfinity(value.y) && !float.IsInfinity(value.z);
    }
    private static float[] Matrix(Matrix4x4 value)
    {
        var result = new float[16];
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++)
                result[row * 4 + column] = value[row, column];
        return result;
    }
    private static string Hash(string path)
    {
        using (var sha = SHA256.Create())
        using (var stream = File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }
}
