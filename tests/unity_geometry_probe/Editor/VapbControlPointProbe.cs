// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// UV values are explicit source-index markers, never coordinate or label matching.
public static class VapbControlPointProbe
{
    const string ModelPath = "Assets/VapbGeometry/Model.fbx";
    [Serializable] public sealed class Marker
    { public string mesh_guid, mesh_local_id, geometry_uid; public int control_point_count, uv_channel; }
    [Serializable] public sealed class Manifest
    { public string source_fbx_sha256, source_meta_sha256, noop_fbx_sha256, stamped_fbx_sha256; public Marker[] meshes; }
    [Serializable] public sealed class MeshRow
    {
        public string mesh_guid, mesh_local_id, geometry_uid, base_signature, shape_signature, original_uv_signature;
        public int vertex_count;
        public int marker_uv_count, marker_nonfinite_count, marker_fractional_count, marker_sentinel_mismatch_count, marker_out_of_range_count;
        public int observed_control_point_count;
        public int[] missing_control_point_indices;
        public int[] vertex_control_point_indices, triangle_vertex_indices, triangle_control_point_indices;
        public bool marker_valid, negative_duplicate_rejected, negative_out_of_range_rejected;
        public bool observed_vertex_map_valid, raw_source_cp_complete, negative_observed_set_removal_rejected;
    }
    [Serializable] public sealed class Result
    {
        public string schema = "vapb-control-point-public-api-1", error = "UNFINISHED";
        public string source_fbx_sha256, source_meta_sha256, noop_fbx_sha256, stamped_fbx_sha256;
        public bool pass, noop_equivalent, stamped_equivalent, restored_equivalent, source_fbx_restored, source_meta_restored;
        public MeshRow[] original, noop, stamped, restored;
    }
    static string Project { get { return Path.GetDirectoryName(Application.dataPath); } }
    public static void Run()
    {
        var result = new Result();
        var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project, "ControlPointManifest.json")));
        byte[] source = File.ReadAllBytes(Path.Combine(Project, "Source.fbx")), meta = File.ReadAllBytes(Path.Combine(Project, "Source.fbx.meta"));
        result.source_fbx_sha256 = Hash(source); result.source_meta_sha256 = Hash(meta);
        try
        {
            if (Hash(source) != manifest.source_fbx_sha256 || Hash(meta) != manifest.source_meta_sha256) throw new InvalidOperationException();
            byte[] noop = File.ReadAllBytes(Path.Combine(Project, "Noop.fbx")), stamped = File.ReadAllBytes(Path.Combine(Project, "Stamped.fbx"));
            result.noop_fbx_sha256 = Hash(noop); result.stamped_fbx_sha256 = Hash(stamped);
            if (Hash(noop) != manifest.noop_fbx_sha256 || Hash(stamped) != manifest.stamped_fbx_sha256) throw new InvalidOperationException();
            Import(source, meta); result.original = Observe(manifest, false);
            Import(noop, meta); result.noop = Observe(manifest, false); result.noop_equivalent = Same(result.original, result.noop);
            Import(stamped, meta); result.stamped = Observe(manifest, true); result.stamped_equivalent = Same(result.original, result.stamped);
            result.error = "NONE";
        }
        catch { result.error = "CONTROL_FAILED"; }
        finally
        {
            try
            {
                Import(source, meta); result.restored = Observe(manifest, false); result.restored_equivalent = Same(result.original, result.restored);
                result.source_fbx_restored = Hash(File.ReadAllBytes(Path.Combine(Project, ModelPath))) == manifest.source_fbx_sha256;
                result.source_meta_restored = Hash(File.ReadAllBytes(Path.Combine(Project, ModelPath + ".meta"))) == manifest.source_meta_sha256;
            }
            catch { result.error = "RESTORE_FAILED"; }
            result.pass = result.error == "NONE" && result.noop_equivalent && result.stamped_equivalent && result.restored_equivalent
                && result.source_fbx_restored && result.source_meta_restored && result.stamped.All(r => r.marker_valid && r.negative_duplicate_rejected && r.negative_out_of_range_rejected);
            File.WriteAllText(Path.Combine(Project, "UnityControlPointBridge.json"), JsonUtility.ToJson(result, true));
            Debug.Log(result.pass ? "VAPB_CONTROL_POINT_PASS" : "VAPB_CONTROL_POINT_FAIL"); EditorApplication.Exit(result.pass ? 0 : 1);
        }
    }
    static void Import(byte[] bytes, byte[] meta)
    {
        File.WriteAllBytes(Path.Combine(Project, ModelPath), bytes); File.WriteAllBytes(Path.Combine(Project, ModelPath + ".meta"), meta);
        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
    }
    static MeshRow[] Observe(Manifest manifest, bool stamped)
    {
        var markers = manifest.meshes.ToDictionary(m => m.mesh_guid + ":" + m.mesh_local_id);
        var rows = new List<MeshRow>();
        foreach (Mesh mesh in AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Mesh>())
        {
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long localId)) throw new InvalidOperationException();
            string id = localId.ToString(CultureInfo.InvariantCulture);
            if (!markers.TryGetValue(guid + ":" + id, out Marker marker)) throw new InvalidOperationException();
            if (!stamped)
            {
                var spare = new List<Vector4>(); mesh.GetUVs(marker.uv_channel, spare);
                if (spare.Count != 0) throw new InvalidOperationException(); // Never overwrite importer-generated or existing UV data.
            }
            var row = new MeshRow { mesh_guid = guid, mesh_local_id = id, geometry_uid = marker.geometry_uid, vertex_count = mesh.vertexCount,
                base_signature = Signature(writer => {
                    Vectors(writer, mesh.vertices); Vectors(writer, mesh.normals); Vectors(writer, mesh.tangents);
                    writer.Write(mesh.subMeshCount); for (int s = 0; s < mesh.subMeshCount; s++) { writer.Write((int)mesh.GetTopology(s)); Integers(writer, mesh.GetIndices(s)); }
                    foreach (var matrix in mesh.bindposes) for (int i = 0; i < 16; i++) writer.Write(matrix[i]);
                    foreach (var weight in mesh.boneWeights) { writer.Write(weight.boneIndex0); writer.Write(weight.boneIndex1); writer.Write(weight.boneIndex2); writer.Write(weight.boneIndex3); writer.Write(weight.weight0); writer.Write(weight.weight1); writer.Write(weight.weight2); writer.Write(weight.weight3); }
                }),
                original_uv_signature = Signature(writer => { for (int channel = 0; channel < 8; channel++) if (channel != marker.uv_channel) { var uv = new List<Vector4>(); mesh.GetUVs(channel, uv); Vectors(writer, uv.ToArray()); } }),
                shape_signature = Signature(writer => { writer.Write(mesh.blendShapeCount); for (int c = 0; c < mesh.blendShapeCount; c++) { writer.Write(mesh.GetBlendShapeName(c)); writer.Write(mesh.GetBlendShapeFrameCount(c)); for (int f = 0; f < mesh.GetBlendShapeFrameCount(c); f++) { writer.Write(mesh.GetBlendShapeFrameWeight(c, f)); var v = new Vector3[mesh.vertexCount]; var n = new Vector3[mesh.vertexCount]; var t = new Vector3[mesh.vertexCount]; mesh.GetBlendShapeFrameVertices(c, f, v, n, t); Vectors(writer,v); Vectors(writer,n); Vectors(writer,t); } } }) };
            if (stamped)
            {
                var uv = new List<Vector2>(); mesh.GetUVs(marker.uv_channel, uv);
                Diagnose(row, uv, marker.control_point_count);
                row.raw_source_cp_complete = row.missing_control_point_indices.Length == 0;
                row.marker_valid = Decode(uv, mesh.vertexCount, marker.control_point_count, out int[] cp);
                row.observed_vertex_map_valid = DecodeObserved(uv, mesh.vertexCount, marker.control_point_count, out int[] observed);
                if (row.observed_vertex_map_valid)
                {
                    cp = observed;
                    row.vertex_control_point_indices = cp; row.triangle_vertex_indices = mesh.triangles;
                    row.triangle_control_point_indices = mesh.triangles.Select(index => cp[index]).ToArray();
                    var invalid = uv.ToArray(); invalid[0].x = marker.control_point_count + 1;
                    row.negative_out_of_range_rejected = !DecodeObserved(invalid, mesh.vertexCount, marker.control_point_count, out _);
                    // Remove every marker for one CP. Unity vertex splits may legitimately repeat one CP;
                    // a duplicate source marker must leave a CP absent under this full-coverage contract.
                    var duplicate = uv.ToArray(); int first = cp[0], other = cp.First(value => value != first);
                    for (int i = 0; i < cp.Length; i++) if (cp[i] == first) duplicate[i].x = other + 1;
                    if (row.marker_valid) row.negative_duplicate_rejected = !Decode(duplicate, mesh.vertexCount, marker.control_point_count, out _);
                    var observedSet = new HashSet<int>(cp);
                    row.negative_observed_set_removal_rejected = !DecodeObserved(duplicate, mesh.vertexCount, marker.control_point_count, out int[] negative)
                        || !observedSet.SetEquals(negative);
                }
            }
            rows.Add(row);
        }
        if (rows.Count != markers.Count || rows.Select(r => r.mesh_guid + ":" + r.mesh_local_id).Distinct().Count() != rows.Count) throw new InvalidOperationException();
        return rows.ToArray();
    }
    static bool Decode(IList<Vector2> uv, int vertices, int points, out int[] result)
    {
        result = null;
        if (!DecodeObserved(uv, vertices, points, out int[] values)) return false;
        if (new HashSet<int>(values).Count != points) return false;
        result = values; return true;
    }
    static bool DecodeObserved(IList<Vector2> uv, int vertices, int points, out int[] result)
    {
        result = null; if (uv.Count != vertices || vertices == 0) return false;
        var values = new int[vertices];
        for (int i = 0; i < vertices; i++)
        {
            float value = uv[i].x;
            if (float.IsNaN(value) || float.IsInfinity(value) || value != Mathf.Round(value) || value < 1 || value > points || uv[i].y != .375f) return false;
            values[i] = (int)value - 1;
        }
        result = values; return true;
    }
    static void Diagnose(MeshRow row, IList<Vector2> uv, int points)
    {
        row.marker_uv_count = uv.Count;
        var coverage = new HashSet<int>();
        foreach (var marker in uv)
        {
            if (float.IsNaN(marker.x) || float.IsInfinity(marker.x) || float.IsNaN(marker.y) || float.IsInfinity(marker.y)) { row.marker_nonfinite_count++; continue; }
            bool fractional = marker.x != Mathf.Round(marker.x), sentinel = marker.y != .375f, outside = marker.x < 1 || marker.x > points;
            if (fractional) row.marker_fractional_count++;
            if (sentinel) row.marker_sentinel_mismatch_count++;
            if (outside) row.marker_out_of_range_count++;
            if (!fractional && !sentinel && !outside) coverage.Add((int)marker.x - 1);
        }
        row.observed_control_point_count = coverage.Count;
        row.missing_control_point_indices = Enumerable.Range(0, points).Where(index => !coverage.Contains(index)).ToArray();
    }
    static bool Same(MeshRow[] left, MeshRow[] right)
    {
        if (left == null || right == null) return false;
        var expected = left.ToDictionary(r => r.mesh_guid + ":" + r.mesh_local_id);
        var actual = right.ToDictionary(r => r.mesh_guid + ":" + r.mesh_local_id);
        return expected.Count == actual.Count && expected.All(pair => actual.TryGetValue(pair.Key, out MeshRow row)
            && pair.Value.base_signature == row.base_signature && pair.Value.shape_signature == row.shape_signature && pair.Value.original_uv_signature == row.original_uv_signature);
    }
    static void Integers(BinaryWriter writer, int[] values) { writer.Write(values.Length); foreach (var v in values) writer.Write(v); }
    static void Vectors(BinaryWriter writer, Vector3[] values) { writer.Write(values.Length); foreach (var v in values) { writer.Write(v.x); writer.Write(v.y); writer.Write(v.z); } }
    static void Vectors(BinaryWriter writer, Vector4[] values) { writer.Write(values.Length); foreach (var v in values) { writer.Write(v.x); writer.Write(v.y); writer.Write(v.z); writer.Write(v.w); } }
    static string Signature(Action<BinaryWriter> write) { using (var stream = new MemoryStream()) using (var writer = new BinaryWriter(stream)) { write(writer); writer.Flush(); return Hash(stream.ToArray()); } }
    static string Hash(byte[] bytes) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
}
