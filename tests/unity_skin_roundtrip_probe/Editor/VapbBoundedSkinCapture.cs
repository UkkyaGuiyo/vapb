// SPDX-License-Identifier: GPL-3.0-or-later
// Public API capture for the existing direct confirmed Skin fixture only.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbBoundedSkinCapture
{
    static VapbBoundedSkinCapture() { VapbSkinRoundtripProbe.BoundedCapture = Write; }
    [Serializable] public class Task { public string model_guid, model_sha256, realization_id,
        prefab_guid, renderer_file_id, prefab_source_sha256; }
    [Serializable] public class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] public class Weight { public int vertex, bone; public float weight; }
    [Serializable] public class Bone { public int index; public string export_label, target_file_id; }
    [Serializable] public class UV { public int channel; public Vector4[] values; }
    [Serializable] public class Submesh { public int[] indices; }
    [Serializable] public class Row {
        public string guid, local_id, renderer_file_id, owner_file_id, root_bone_id;
        public int marker_invalid_count;
        public int[] vertex_control_point_indices, triangles;
        public Vector3[] world_positions, world_normals;
        public float[] renderer_local_to_world;
        public UV[] uv_channels; public Submesh[] submeshes; public Bone[] bones;
        public Weight[] bone_weights; public string[] material_guids;
        public int shape_count;
    }
    [Serializable] public class Report { public string version, package_sha256, fbx_sha256,
        prefab_source_sha256, blender_capture_sha256, realization_id; public Row first, repeated; public Node[] hierarchy; }
    [Serializable] public class Node { public string game_object_id, parent_game_object_id; }
    static string Project => Path.GetDirectoryName(Application.dataPath);
    static string Hash(string path) { using(var sha=SHA256.Create()) return
        BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    static string Id(UnityEngine.Object obj, string expectedGuid) {
        if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj,out string guid,out long id)
            || guid!=expectedGuid || id==0) throw new Exception("EXACT_ID_UNAVAILABLE");
        return id.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }
    static Row Observe(Task task) {
        var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.prefab_guid));
        var target=prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true)
            .Single(s=>Id(s,task.prefab_guid)==task.renderer_file_id);
        var model=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
        var native=model.GetComponentsInChildren<SkinnedMeshRenderer>(true)
            .Single(s=>s.GetComponent<VapbRealizationMarker>()?.realizationId==task.realization_id);
        if(target.sharedMesh!=native.sharedMesh) throw new Exception("FINALIZER_MESH_BRIDGE_MISMATCH");
        var mesh=native.sharedMesh;
        if(native.bones.Length!=target.bones.Length) throw new Exception("BONE_COUNT_MISMATCH");
        var bones=native.bones.Select((b,i)=>new Bone {index=i,
            export_label=b.GetComponent<VapbRealizationMarker>()?.boneRealizationId,
            target_file_id=Id(target.bones[i],task.prefab_guid)}).ToArray();
        if(bones.Any(b=>String.IsNullOrEmpty(b.export_label))) throw new Exception("BONE_RECEIPT_MISSING");
        var uv=new List<UV>();
        for(int i=0;i<8;i++) {var values=new List<Vector4>();mesh.GetUVs(i,values);uv.Add(new UV{channel=i,values=values.ToArray()});}
        // CP channel is explicitly supplied by the diagnostic's authored fixture.
        int channel=int.Parse(File.ReadAllText(Path.Combine(Project,"CPChannel.txt")));
        var cps=uv[channel].values.Select(v=>v.y==.375f && v.x>=1 && v.x==Mathf.Round(v.x)?(int)v.x-1:-1).ToArray();
        var weights=new List<Weight>();var counts=mesh.GetBonesPerVertex();var all=mesh.GetAllBoneWeights();int offset=0;
        try {for(int v=0;v<counts.Length;v++) for(int i=0;i<counts[v];i++) {
            var w=all[offset++];weights.Add(new Weight{vertex=v,bone=w.boneIndex,weight=w.weight});}}
        finally {counts.Dispose();all.Dispose();}
        var matrix=new float[16];for(int i=0;i<16;i++)matrix[i]=native.localToWorldMatrix[i];
        return new Row {guid=task.model_guid,local_id=Id(mesh,task.model_guid),
            renderer_file_id=Id(target,task.prefab_guid),owner_file_id=Id(target.gameObject,task.prefab_guid),
            root_bone_id=Id(target.rootBone,task.prefab_guid),bones=bones,bone_weights=weights.ToArray(),
            vertex_control_point_indices=cps,marker_invalid_count=cps.Count(v=>v<0),triangles=mesh.triangles,
            world_positions=mesh.vertices.Select(v=>native.transform.TransformPoint(v)).ToArray(),
            world_normals=new Vector3[0],renderer_local_to_world=matrix,uv_channels=uv.ToArray(),
            submeshes=Enumerable.Range(0,mesh.subMeshCount).Select(i=>new Submesh{indices=mesh.GetIndices(i)}).ToArray(),
            material_guids=target.sharedMaterials.Select(m=>AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(m))).ToArray(),
            shape_count=mesh.blendShapeCount};
    }
    public static void Write() {
        if(Application.unityVersion!="2022.3.22f1") throw new Exception("UNSUPPORTED_VERSION");
        var manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText("Assets/VAPBExport/manifest.json"));
        var task=manifest.reference_rebind_tasks.Single();
        var report=new Report {version=Application.unityVersion,realization_id=task.realization_id,
            package_sha256=Hash(Path.Combine(Project,"Source.unitypackage")),
            fbx_sha256=Hash(AssetDatabase.GUIDToAssetPath(task.model_guid)),
            prefab_source_sha256=task.prefab_source_sha256,
            blender_capture_sha256=Hash(Path.Combine(Project,"BoundedBlender.json")),first=Observe(task)};
        if(report.fbx_sha256!=task.model_sha256) throw new Exception("STALE_FBX");
        var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.prefab_guid));
        report.hierarchy=prefab.GetComponentsInChildren<Transform>(true).Select(t=>new Node {
            game_object_id=Id(t.gameObject,task.prefab_guid),parent_game_object_id=t.parent==null?null:
            Id(t.parent.gameObject,task.prefab_guid)}).ToArray();
        if(!VapbReferenceFinalizer.Apply("Assets/VAPBExport/manifest.json")) throw new Exception("REPEATED_APPLY_FAILED");
        report.repeated=Observe(task);
        File.WriteAllText(Path.Combine(Project,"BoundedUnity.json"),JsonUtility.ToJson(report,true));
    }
    public static void Run() {
        try { Write(); EditorApplication.Exit(0); }
        catch { EditorApplication.Exit(1); }
    }
}
