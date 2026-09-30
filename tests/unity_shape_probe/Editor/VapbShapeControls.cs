// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Separate diagnostic copy only. Marker labels establish an experimental UID correspondence;
// ordinary channel labels, ordering and candidate counts do not establish cross-runtime identity.
public static class VapbShapeControls
{
    const string ModelPath = "Assets/VapbShape/Model.fbx";
    [Serializable] sealed class Channel
    { public int channel_index, frame_count; public float[] frame_weights; public string channel_uid, diagnostic_name, frame_signature; }
    [Serializable] sealed class MeshSnapshot
    { public string mesh_guid, mesh_local_id, geometry_signature; public Channel[] channels; }
    [Serializable] sealed class Snapshot { public MeshSnapshot[] meshes; }
    [Serializable] sealed class Result
    {
        public string schema = "vapb-shape-channel-control-2", error = "UNFINISHED";
        public string source_fbx_sha256, source_meta_sha256, noop_fbx_sha256, marked_fbx_sha256;
        public bool pass, noop_equivalent, marked_equivalent, restored_equivalent, marker_unique;
        public bool source_fbx_restored, source_meta_restored;
        public Snapshot original, noop, marked, restored;
    }
    static string Project { get { return Path.GetDirectoryName(Application.dataPath); } }
    public static void Run()
    {
        var result = new Result();
        byte[] source = File.ReadAllBytes(Path.Combine(Project, "Source.fbx"));
        byte[] meta = File.ReadAllBytes(Path.Combine(Project, "Source.fbx.meta"));
        result.source_fbx_sha256 = Hash(source); result.source_meta_sha256 = Hash(meta);
        try
        {
            Import(source, meta); result.original = Observe();
            byte[] noop = File.ReadAllBytes(Path.Combine(Project, "ShapeNoop.fbx")); result.noop_fbx_sha256 = Hash(noop);
            Import(noop, meta); result.noop = Observe();
            result.noop_equivalent = Equivalent(result.original, result.noop);
            byte[] marked = File.ReadAllBytes(Path.Combine(Project, "ShapeMarked.fbx")); result.marked_fbx_sha256 = Hash(marked);
            Import(marked, meta); result.marked = Observe();
            result.marked_equivalent = Equivalent(result.original, result.marked);
            var markedChannels = result.marked.meshes.SelectMany(mesh => mesh.channels).ToArray();
            result.marker_unique = markedChannels.Length > 0 && markedChannels.All(c => c.channel_uid != null)
                && markedChannels.Select(c => c.channel_uid).Distinct().Count() == markedChannels.Length;
            result.error = "NONE";
        }
        catch { result.error = "CONTROL_FAILED"; }
        finally
        {
            try
            {
                Import(source, meta); result.restored = Observe();
                result.restored_equivalent = Equivalent(result.original, result.restored);
                result.source_fbx_restored = Hash(File.ReadAllBytes(Path.Combine(Project, ModelPath))) == result.source_fbx_sha256;
                result.source_meta_restored = Hash(File.ReadAllBytes(Path.Combine(Project, ModelPath + ".meta"))) == result.source_meta_sha256;
            }
            catch { result.error = "RESTORE_FAILED"; }
            result.pass = result.error == "NONE" && result.noop_equivalent && result.marked_equivalent
                && result.restored_equivalent && result.marker_unique && result.source_fbx_restored && result.source_meta_restored;
            File.WriteAllText(Path.Combine(Project, "UnityShapeChannelControls.json"), JsonUtility.ToJson(result, true));
            Debug.Log(result.pass ? "VAPB_SHAPE_CONTROLS_PASS" : "VAPB_SHAPE_CONTROLS_FAIL"); EditorApplication.Exit(result.pass ? 0 : 1);
        }
    }
    static void Import(byte[] bytes, byte[] meta)
    {
        File.WriteAllBytes(Path.Combine(Project, ModelPath), bytes);
        File.WriteAllBytes(Path.Combine(Project, ModelPath + ".meta"), meta);
        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
    }
    static Snapshot Observe()
    {
        var meshes = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Mesh>().Select(ObserveMesh).ToArray();
        if (meshes.Length == 0) throw new InvalidOperationException("MESH_UNAVAILABLE");
        Index(meshes); // Reject duplicate exact identities before any comparison.
        return new Snapshot { meshes = meshes };
    }
    static MeshSnapshot ObserveMesh(Mesh mesh)
    {
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long localId) || localId == 0)
            throw new InvalidOperationException("MESH_ID_UNAVAILABLE");
        var channels = Enumerable.Range(0, mesh.blendShapeCount).Select(index => {
            string name = mesh.GetBlendShapeName(index);
            var marker = Regex.Match(name, @"(?:^|\.)VAPB_SHAPE_UID_([0-9]+)$");
            string signature = Signature(writer => {
                writer.Write(mesh.GetBlendShapeFrameCount(index));
                for (int frame = 0; frame < mesh.GetBlendShapeFrameCount(index); frame++)
                {
                    writer.Write(mesh.GetBlendShapeFrameWeight(index, frame));
                    var positions = new Vector3[mesh.vertexCount]; var normals = new Vector3[mesh.vertexCount]; var tangents = new Vector3[mesh.vertexCount];
                    mesh.GetBlendShapeFrameVertices(index, frame, positions, normals, tangents);
                    Vectors(writer, positions); Vectors(writer, normals); Vectors(writer, tangents);
                }
            });
            int frameCount = mesh.GetBlendShapeFrameCount(index);
            return new Channel { channel_index = index, frame_count = frameCount,
                frame_weights = Enumerable.Range(0, frameCount).Select(frame => mesh.GetBlendShapeFrameWeight(index, frame)).ToArray(),
                diagnostic_name = name, channel_uid = marker.Success ? marker.Groups[1].Value : null, frame_signature = signature };
        }).ToArray();
        return new MeshSnapshot { mesh_guid = guid, mesh_local_id = localId.ToString(CultureInfo.InvariantCulture), channels = channels,
            geometry_signature = Signature(writer => { Vectors(writer, mesh.vertices); writer.Write(mesh.triangles.Length); foreach (int index in mesh.triangles) writer.Write(index); }) };
    }
    static bool Equivalent(Snapshot left, Snapshot right)
    {
        if (left == null || right == null) return false;
        var expected = Index(left.meshes); var actual = Index(right.meshes);
        if (expected.Count != actual.Count) return false;
        foreach (var pair in expected)
        {
            if (!actual.TryGetValue(pair.Key, out MeshSnapshot mesh)) return false;
            if (pair.Value.geometry_signature != mesh.geometry_signature
                || !pair.Value.channels.Select(c => c.frame_signature).SequenceEqual(mesh.channels.Select(c => c.frame_signature))) return false;
        }
        return true;
    }
    static Dictionary<string, MeshSnapshot> Index(MeshSnapshot[] meshes)
    {
        var result = new Dictionary<string, MeshSnapshot>();
        foreach (var mesh in meshes) result.Add(mesh.mesh_guid + ":" + mesh.mesh_local_id, mesh);
        return result;
    }
    static void Vectors(BinaryWriter writer, Vector3[] vectors)
    { writer.Write(vectors.Length); foreach (var v in vectors) { writer.Write(v.x); writer.Write(v.y); writer.Write(v.z); } }
    static string Signature(Action<BinaryWriter> write)
    { using (var stream = new MemoryStream()) { using (var writer = new BinaryWriter(stream)) { write(writer); writer.Flush(); return Hash(stream.ToArray()); } } }
    static string Hash(byte[] bytes)
    { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
}
