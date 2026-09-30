// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Formats.Fbx.Exporter;
using UnityEngine;

// Isolated public-fixture characterization. No production asset writes.
public static class VapbGeometryAbcd
{
    const string ModelPath = "Assets/VapbGeometry/Model.fbx";
    static string Project => Path.GetDirectoryName(Application.dataPath);
    static int warnings, errors;
    [Serializable] public class Marker { public int uv_channel, control_point_count; }
    [Serializable] public class Manifest { public string source_fbx_sha256, source_meta_sha256, stamped_fbx_sha256; public Marker[] meshes; }
    [Serializable] public class UV { public int channel; public Vector4[] values; }
    [Serializable] public class Submesh { public string topology; public int[] indices; }
    [Serializable] public class Shape { public string name; public int index, frame; public float weight; public Vector3[] delta_positions, delta_normals, delta_tangents; }
    [Serializable] public class Weight { public int vertex, bone; public float weight; }
    [Serializable] public class Bone { public int index; public string path, export_label; public float[] local_to_world; }
    [Serializable] public class Row
    {
        public string guid, local_id, renderer_path, renderer_type, renderer_name;
        public int vertex_count, marker_channel, marker_invalid_count;
        public string[] material_export_labels;
        public Vector3[] positions, world_positions, normals, world_normals, baked_world_positions, baked_world_normals;
        public Vector3[] baked_true_world_positions, baked_true_world_normals, cpu_weighted_world_positions;
        public int cpu_invalid_influence_count;
        public Vector3 renderer_lossy_scale;
        public Vector4[] tangents;
        public UV[] uv_channels; public Submesh[] submeshes; public int[] triangles, vertex_control_point_indices;
        public Shape[] shape_frames; public Weight[] bone_weights; public Bone[] bones;
        public float[] bindposes, renderer_local_to_world, shape_weights;
        public Bounds bounds;
    }
    [Serializable] public class Capture
    { public string schema="vapb-geometry-abcd-public-api-1", label, editor_version, input_sha256, input_meta_sha256; public Row[] meshes; }
    [Serializable] public class Status
    { public string schema="vapb-geometry-abcd-status-1", status="UNFINISHED", editor_version, exporter_version; public int warnings, errors; public string c_unmarked_sha256, c_stamped_sha256; }
    [Serializable] public class ImportWeightSettings { public string skin_weights;public float min_bone_weight;public int max_bones_per_vertex; }
    [Serializable] public class WeightControlStatus
    {public string status="UNFINISHED",editor_version,input_sha256;public int warnings,errors;public ImportWeightSettings original,min_zero_assigned,min_zero,custom_zero_assigned,custom_zero,epsilon_assigned,epsilon,restored;public bool settings_restored,meta_bytes_restored,input_unchanged;}
    static ImportWeightSettings WeightSettings(ModelImporter importer) {return new ImportWeightSettings {skin_weights=importer.skinWeights.ToString(),min_bone_weight=importer.minBoneWeight,max_bones_per_vertex=importer.maxBonesPerVertex};}
    static void ReimportSettings(ModelImporter importer) {importer.SaveAndReimport();AssetDatabase.ImportAsset(ModelPath,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);}
    static string Hash(string path) { using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    static float[] Matrix(Matrix4x4 m) { var a=new float[16]; for(int i=0;i<16;i++) a[i]=m[i]; return a; }
    static string Hierarchy(Transform t, Transform root) { if(t==null) return null; if(t==root) return "0"; return Hierarchy(t.parent,root)+"/"+t.GetSiblingIndex(); }
    static void Logs(string message,string stack,LogType type) { if(type==LogType.Warning) warnings++; if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert) errors++; }
    static GameObject Import(string path, string meta)
    {
        File.Copy(path,Path.Combine(Project,ModelPath),true);
        if(meta!=null) File.Copy(meta,Path.Combine(Project,ModelPath+".meta"),true);
        AssetDatabase.ImportAsset(ModelPath,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
        var asset=AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if(asset==null) throw new InvalidOperationException("IMPORT_FAILED");
        return asset;
    }
    static Capture Observe(GameObject asset,string label,Manifest manifest)
    {
        var instance=UnityEngine.Object.Instantiate(asset); instance.name=asset.name;
        try
        {
            var rows=new List<Row>();
            foreach(var renderer in instance.GetComponentsInChildren<Renderer>(true))
            {
                var skin=renderer as SkinnedMeshRenderer;
                var filter=renderer.GetComponent<MeshFilter>();
                Mesh mesh=skin!=null?skin.sharedMesh:filter!=null?filter.sharedMesh:null;
                if(mesh==null) continue;
                if(skin!=null) for(int s=0;s<mesh.blendShapeCount;s++) skin.SetBlendShapeWeight(s,0);
                if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out string guid,out long id)) throw new InvalidOperationException("IDENTITY_FAILED");
                var r=new Row { guid=guid,local_id=id.ToString(),renderer_path=Hierarchy(renderer.transform,instance.transform),renderer_type=renderer.GetType().Name,
                    material_export_labels=renderer.sharedMaterials.Select(m=>m!=null&&m.name.StartsWith("VAPB-EXP-MAT-")?m.name:null).ToArray(),
                    renderer_name=renderer.name,renderer_lossy_scale=renderer.transform.lossyScale,vertex_count=mesh.vertexCount,positions=mesh.vertices,normals=mesh.normals,tangents=mesh.tangents,bounds=mesh.bounds,
                    renderer_local_to_world=Matrix(renderer.localToWorldMatrix),triangles=mesh.triangles,marker_channel=manifest.meshes.Single().uv_channel };
                r.world_positions=r.positions.Select(v=>renderer.transform.TransformPoint(v)).ToArray();
                var normalMatrix=renderer.localToWorldMatrix.inverse.transpose;
                r.world_normals=r.normals.Select(v=>normalMatrix.MultiplyVector(v).normalized).ToArray();
                if(skin!=null) {var baked=new Mesh(); try {skin.BakeMesh(baked,false); r.baked_world_positions=baked.vertices.Select(v=>renderer.transform.TransformPoint(v)).ToArray(); r.baked_world_normals=baked.normals.Select(v=>normalMatrix.MultiplyVector(v).normalized).ToArray(); skin.BakeMesh(baked,true);r.baked_true_world_positions=baked.vertices.Select(v=>renderer.transform.TransformPoint(v)).ToArray();r.baked_true_world_normals=baked.normals.Select(v=>normalMatrix.MultiplyVector(v).normalized).ToArray();} finally {UnityEngine.Object.DestroyImmediate(baked);} }
                else {r.baked_world_positions=r.world_positions; r.baked_world_normals=r.world_normals;r.baked_true_world_positions=r.world_positions;r.baked_true_world_normals=r.world_normals;}
                var uvs=new List<UV>(); for(int channel=0;channel<8;channel++) { var values=new List<Vector4>(); mesh.GetUVs(channel,values); uvs.Add(new UV {channel=channel,values=values.ToArray()}); }
                r.uv_channels=uvs.ToArray();
                r.vertex_control_point_indices=new int[mesh.vertexCount]; var marker=uvs[r.marker_channel].values;
                for(int i=0;i<mesh.vertexCount;i++) { int cp=-1; if(marker.Length==mesh.vertexCount) { float v=marker[i].x; if(!float.IsNaN(v)&&!float.IsInfinity(v)&&v==Mathf.Round(v)&&v>=1&&v<=manifest.meshes.Single().control_point_count&&Mathf.Abs(marker[i].y-.375f)<1e-6f) cp=(int)v-1; } r.vertex_control_point_indices[i]=cp; if(cp<0)r.marker_invalid_count++; }
                r.submeshes=Enumerable.Range(0,mesh.subMeshCount).Select(s=>new Submesh {topology=mesh.GetTopology(s).ToString(),indices=mesh.GetIndices(s)}).ToArray();
                var shapes=new List<Shape>(); for(int c=0;c<mesh.blendShapeCount;c++) for(int f=0;f<mesh.GetBlendShapeFrameCount(c);f++) { var frame=new Shape {name=mesh.GetBlendShapeName(c),index=c,frame=f,weight=mesh.GetBlendShapeFrameWeight(c,f),delta_positions=new Vector3[mesh.vertexCount],delta_normals=new Vector3[mesh.vertexCount],delta_tangents=new Vector3[mesh.vertexCount]}; mesh.GetBlendShapeFrameVertices(c,f,frame.delta_positions,frame.delta_normals,frame.delta_tangents); shapes.Add(frame); }
                r.shape_frames=shapes.ToArray(); r.shape_weights=skin==null?new float[0]:Enumerable.Range(0,mesh.blendShapeCount).Select(s=>skin.GetBlendShapeWeight(s)).ToArray();
                var weights=new List<Weight>(); var counts=mesh.GetBonesPerVertex(); var all=mesh.GetAllBoneWeights(); int offset=0;
                try {for(int v=0;v<counts.Length;v++) for(int b=0;b<counts[v];b++) {var w=all[offset++]; weights.Add(new Weight {vertex=v,bone=w.boneIndex,weight=w.weight}); } if(offset!=all.Length) throw new InvalidOperationException("WEIGHT_CURSOR_MISMATCH");}
                finally {counts.Dispose();all.Dispose();}
                r.bone_weights=weights.ToArray(); r.bindposes=mesh.bindposes.SelectMany(Matrix).ToArray();
                r.cpu_weighted_world_positions=skin==null?r.world_positions:new Vector3[mesh.vertexCount];
                if(skin!=null) {var bindposes=mesh.bindposes;var bones=skin.bones;foreach(var w in weights) {if(w.bone<0||w.bone>=bones.Length||w.bone>=bindposes.Length||bones[w.bone]==null) {r.cpu_invalid_influence_count++;continue;} r.cpu_weighted_world_positions[w.vertex]+=w.weight*(bones[w.bone].localToWorldMatrix*bindposes[w.bone]).MultiplyPoint3x4(r.positions[w.vertex]);} }
                r.bones=skin==null?new Bone[0]:skin.bones.Select((b,i)=>new Bone {index=i,path=Hierarchy(b,instance.transform),export_label=b==null?null:b.name,local_to_world=b==null?new float[0]:Matrix(b.localToWorldMatrix)}).ToArray();
                rows.Add(r);
            }
            if(rows.Count==0) throw new InvalidOperationException("NO_MESH");
            return new Capture {label=label,editor_version=Application.unityVersion,input_sha256=Hash(Path.Combine(Project,ModelPath)),input_meta_sha256=Hash(Path.Combine(Project,ModelPath+".meta")),meshes=rows.ToArray()};
        }
        finally {UnityEngine.Object.DestroyImmediate(instance);}
    }
    static void Save(GameObject asset,string label,Manifest m) { File.WriteAllText(Path.Combine(Project,label+".json"),JsonUtility.ToJson(Observe(asset,label,m),true)); }
    static void Export(GameObject asset,string label)
    {
        var instance=UnityEngine.Object.Instantiate(asset); instance.name=asset.name;
        try {foreach(var skin in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true)) for(int i=0;i<skin.sharedMesh.blendShapeCount;i++) skin.SetBlendShapeWeight(i,0);
            var options=new ExportModelOptions {ExportFormat=ExportFormat.Binary};
            if(ModelExporter.ExportObject(Path.Combine(Project,label+".fbx"),instance,options)==null) throw new InvalidOperationException("EXPORT_FAILED"); }
        finally {UnityEngine.Object.DestroyImmediate(instance);}
    }
    public static void RunAC()
    {
        var status=new Status {editor_version=Application.unityVersion}; Application.logMessageReceived+=Logs;
        try
        {
            if(Application.unityVersion!="2022.3.22f1") throw new InvalidOperationException("EDITOR_VERSION_MISMATCH");
            status.exporter_version=UnityEditor.PackageManager.PackageInfo.FindForAssembly(typeof(ModelExporter).Assembly).version;
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project,"ControlPointManifest.json")));
            string source=Path.Combine(Project,"Source.fbx"), meta=source+".meta", stamped=Path.Combine(Project,"Stamped.fbx");
            if(Hash(source)!=m.source_fbx_sha256||Hash(meta)!=m.source_meta_sha256||Hash(stamped)!=m.stamped_fbx_sha256) throw new InvalidOperationException("INPUT_HASH_MISMATCH");
            var asset=Import(source,meta); Save(asset,"A_unmarked",m); Export(asset,"C_unmarked");
            asset=Import(stamped,meta); Save(asset,"A_stamped",m); Export(asset,"C_stamped");
            status.c_unmarked_sha256=Hash(Path.Combine(Project,"C_unmarked.fbx")); status.c_stamped_sha256=Hash(Path.Combine(Project,"C_stamped.fbx"));
            status.status="CAPTURED";
        }
        catch(Exception ex) {status.status=ex is InvalidOperationException?ex.Message:"CAPTURE_FAILED";}
        finally {status.warnings=warnings;status.errors=errors; File.WriteAllText(Path.Combine(Project,"UnityACStatus.json"),JsonUtility.ToJson(status,true)); EditorApplication.Exit(status.status=="CAPTURED"?0:1);}
    }
    public static void RunACCapturesOnly()
    {
        var status=new Status {editor_version=Application.unityVersion}; Application.logMessageReceived+=Logs;
        try {if(Application.unityVersion!="2022.3.22f1") throw new InvalidOperationException("EDITOR_VERSION_MISMATCH");
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project,"ControlPointManifest.json")));
            string source=Path.Combine(Project,"Source.fbx"),meta=source+".meta",stamped=Path.Combine(Project,"Stamped.fbx");
            if(Hash(source)!=m.source_fbx_sha256||Hash(meta)!=m.source_meta_sha256||Hash(stamped)!=m.stamped_fbx_sha256) throw new InvalidOperationException("INPUT_HASH_MISMATCH");
            Save(Import(source,meta),"A_unmarked",m); Save(Import(stamped,meta),"A_stamped",m);status.status="CAPTURED";
        }
        catch(Exception ex) {status.status=ex is InvalidOperationException?ex.Message:"CAPTURE_FAILED";}
        finally {status.warnings=warnings;status.errors=errors;File.WriteAllText(Path.Combine(Project,"UnityACCapturesOnlyStatus.json"),JsonUtility.ToJson(status,true));EditorApplication.Exit(status.status=="CAPTURED"?0:1);}
    }
    public static void RunD()
    {
        var status=new Status {editor_version=Application.unityVersion}; Application.logMessageReceived+=Logs;
        try { if(Application.unityVersion!="2022.3.22f1") throw new InvalidOperationException("EDITOR_VERSION_MISMATCH");
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project,"ControlPointManifest.json")));
            foreach(string label in new[]{"D0","D1"}) {var asset=Import(Path.Combine(Project,label+".fbx"),null);Save(asset,label,m);} status.status="CAPTURED"; }
        catch(Exception ex) {status.status=ex is InvalidOperationException?ex.Message:"CAPTURE_FAILED";}
        finally {status.warnings=warnings;status.errors=errors;File.WriteAllText(Path.Combine(Project,"UnityDStatus.json"),JsonUtility.ToJson(status,true));EditorApplication.Exit(status.status=="CAPTURED"?0:1);}
    }
    public static void RunCReimport()
    {
        var status=new Status {editor_version=Application.unityVersion}; Application.logMessageReceived+=Logs;
        try { if(Application.unityVersion!="2022.3.22f1") throw new InvalidOperationException("EDITOR_VERSION_MISMATCH");
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project,"ControlPointManifest.json")));
            var exported=JsonUtility.FromJson<Status>(File.ReadAllText(Path.Combine(Project,"UnityACStatus.json")));
            string unmarked=Path.Combine(Project,"C_unmarked.fbx"), stamped=Path.Combine(Project,"C_stamped.fbx");
            if(Hash(unmarked)!=exported.c_unmarked_sha256||Hash(stamped)!=exported.c_stamped_sha256) throw new InvalidOperationException("C_HASH_MISMATCH");
            status.exporter_version=exported.exporter_version; status.c_unmarked_sha256=Hash(unmarked);status.c_stamped_sha256=Hash(stamped);
            string meta=Path.Combine(Project,"Source.fbx.meta");
            Save(Import(unmarked,meta),"C_Unity_unmarked",m); Save(Import(stamped,meta),"C_Unity_stamped",m); status.status="CAPTURED";
        }
        catch(Exception ex) {status.status=ex is InvalidOperationException?ex.Message:"CAPTURE_FAILED";}
        finally {status.warnings=warnings;status.errors=errors;File.WriteAllText(Path.Combine(Project,"UnityCReimportStatus.json"),JsonUtility.ToJson(status,true));EditorApplication.Exit(status.status=="CAPTURED"?0:1);}
    }
    public static void RunWeightControl()
    {
        var status=new WeightControlStatus {editor_version=Application.unityVersion};Application.logMessageReceived+=Logs;
        string metaPath=Path.Combine(Project,ModelPath+".meta"),input=Path.Combine(Project,"D1.fbx");byte[] originalMeta=null;
        try {if(Application.unityVersion!="2022.3.22f1") throw new InvalidOperationException("EDITOR_VERSION_MISMATCH");
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Project,"ControlPointManifest.json")));
            Import(input,null);originalMeta=File.ReadAllBytes(metaPath);status.input_sha256=Hash(input);
            var importer=(ModelImporter)AssetImporter.GetAtPath(ModelPath);status.original=WeightSettings(importer);
            importer.minBoneWeight=0;status.min_zero_assigned=WeightSettings(importer);ReimportSettings(importer);status.min_zero=WeightSettings((ModelImporter)AssetImporter.GetAtPath(ModelPath));Save(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath),"D1_min_zero",m);
            importer=(ModelImporter)AssetImporter.GetAtPath(ModelPath);importer.skinWeights=ModelImporterSkinWeights.Custom;importer.minBoneWeight=0;status.custom_zero_assigned=WeightSettings(importer);ReimportSettings(importer);status.custom_zero=WeightSettings((ModelImporter)AssetImporter.GetAtPath(ModelPath));File.Copy(metaPath,Path.Combine(Project,"WeightControlApplied.meta"),true);Save(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath),"D1_no_trim",m);
            if(status.custom_zero.min_bone_weight>0) {importer=(ModelImporter)AssetImporter.GetAtPath(ModelPath);importer.minBoneWeight=1e-8f;status.epsilon_assigned=WeightSettings(importer);ReimportSettings(importer);status.epsilon=WeightSettings((ModelImporter)AssetImporter.GetAtPath(ModelPath));File.Copy(metaPath,Path.Combine(Project,"WeightControlEpsilonApplied.meta"),true);Save(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath),"D1_threshold_1e8",m);}
            status.status="CAPTURED";
        }
        catch(Exception ex) {status.status=ex is InvalidOperationException?ex.Message:"CAPTURE_FAILED";}
        finally {try {if(originalMeta!=null) {File.WriteAllBytes(metaPath,originalMeta);AssetDatabase.ImportAsset(ModelPath,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);status.restored=WeightSettings((ModelImporter)AssetImporter.GetAtPath(ModelPath));status.settings_restored=JsonUtility.ToJson(status.original)==JsonUtility.ToJson(status.restored);status.meta_bytes_restored=File.ReadAllBytes(metaPath).SequenceEqual(originalMeta);status.input_unchanged=Hash(input)==status.input_sha256;if(!status.settings_restored||!status.meta_bytes_restored||!status.input_unchanged)status.status="RESTORE_FAILED";}else status.status="RESTORE_UNAVAILABLE";}catch{status.status="RESTORE_FAILED";}
            status.warnings=warnings;status.errors=errors;File.WriteAllText(Path.Combine(Project,"UnityWeightControlStatus.json"),JsonUtility.ToJson(status,true));EditorApplication.Exit(status.status=="CAPTURED"?0:1);}
    }
}
