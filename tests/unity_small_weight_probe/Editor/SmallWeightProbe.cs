// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
using Unity.Collections;

public sealed class SmallWeightPreprocess : AssetPostprocessor
{
    internal static bool apply;
    internal static float requested;
    internal static float preprocessGetter;
    void OnPreprocessModel() {
        if(!assetPath.StartsWith("Assets/Ladder")) return;
        var i=(ModelImporter)assetImporter;
        i.animationType=ModelImporterAnimationType.Generic; i.isReadable=true;
        i.optimizeMeshVertices=false; i.optimizeMeshPolygons=false; i.weldVertices=false;
        i.extraUserProperties=new[]{"_vapb_weight_bone_id","_vapb_weight_mesh_id"};
        if(apply) { i.skinWeights=ModelImporterSkinWeights.Custom; i.maxBonesPerVertex=2; i.minBoneWeight=requested; }
        preprocessGetter=i.minBoneWeight;
    }
    void OnPostprocessGameObjectWithUserProperties(GameObject obj,string[] names,object[] values) {
        if(!assetPath.StartsWith("Assets/Ladder")) return;
        for(int n=0;n<names.Length;n++) {
            if(names[n]!="_vapb_weight_bone_id" && names[n]!="_vapb_weight_mesh_id") continue;
            var marker=obj.GetComponent<WeightMarker>()??obj.AddComponent<WeightMarker>();
            if(names[n]=="_vapb_weight_bone_id") marker.boneLabel=Convert.ToString(values[n]);
            else marker.meshLabel=Convert.ToString(values[n]);
        }
    }
}
public static class SmallWeightProbe
{
    [Serializable] public class Influence { public int bone; public string label; public float weight; }
    [Serializable] public class Vertex { public int vertex,cp; public Influence[] influences; public float sum; public Vector3 position,baked,raw_cpu; }
    [Serializable] public class RawWeight { public int cp; public float weight; }
    [Serializable] public class Cluster { public string bone_label; public RawWeight[] weights; }
    [Serializable] public class Source { public int cp_count; public string fbx_sha256; public Cluster[] clusters; }
    [Serializable] public class Capture { public string name,mode,hash,mesh_guid,mesh_id,mesh_label; public float requested,assigned,getter,preprocess; public string stored; public Vertex[] vertices; public string[] bones; public int bindposes,shapes,submeshes; }
    [Serializable] public class Report { public string version,status; public Capture[] cases; public int errors,warnings; public bool source_unchanged; }
    static string Project=>Path.GetDirectoryName(Application.dataPath);
    static string Hash(string p) { using(var s=SHA256.Create()) return BitConverter.ToString(s.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant(); }
    static Capture Observe(string path,string name,string mode,float requested,float assigned) {
        var asset=AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var skins=asset.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        if(skins.Length!=1) throw new Exception("WRONG_MESH_SCOPE");
        var s=skins[0]; if(s.GetComponent<WeightMarker>()?.meshLabel!="WEIGHT-MESH-0") throw new Exception("MESH_LABEL_UNPROVEN");
        var mesh=s.sharedMesh;
        var labels=s.bones.Select(b=>b.GetComponent<WeightMarker>()?.boneLabel).ToArray();
        if(labels.Length!=2 || labels.Distinct().Count()!=2 || labels.Any(b=>b==null)) throw new Exception("BONE_LABEL_UNPROVEN");
        var raw=JsonUtility.FromJson<Source>(File.ReadAllText(Path.Combine(Project,"Source.json")));
        if(raw.fbx_sha256!=Hash(Path.Combine(Project,path))) throw new Exception("STALE_FBX_HASH");
        if(raw.cp_count<=0) throw new Exception("CP_COUNT_UNPROVEN");
        var counts=mesh.GetBonesPerVertex(); var weights=mesh.GetAllBoneWeights(); var uv=mesh.uv; var positions=mesh.vertices;
        var vertices=new List<Vertex>(); int offset=0;
        for(int v=0;v<mesh.vertexCount;v++) {
            int cp=(int)Math.Round(uv[v].x)-1;
            if(cp<0||cp>=raw.cp_count||Math.Abs(uv[v].x-(cp+1))>1e-5||Math.Abs(uv[v].y-.375)>1e-5) throw new Exception("CP_MAPPING_UNPROVEN");
            var list=new List<Influence>(); for(int n=0;n<counts[v];n++) {var w=weights[offset++];list.Add(new Influence {bone=w.boneIndex,label=labels[w.boneIndex],weight=w.weight});}
            vertices.Add(new Vertex {vertex=v,cp=cp,influences=list.ToArray(),sum=list.Sum(w=>w.weight),position=positions[v]});
        }
        counts.Dispose(); weights.Dispose();
        var instance=UnityEngine.Object.Instantiate(asset); var live=instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
        var low=live.bones.Single(b=>b.GetComponent<WeightMarker>()?.boneLabel=="WEIGHT-BONE-0");
        low.position+=new Vector3(.5f,0,0);
        var baked=new Mesh();live.BakeMesh(baked,true);
        foreach(var v in vertices) {
            v.baked=live.transform.TransformPoint(baked.vertices[v.vertex]);
            Vector3 expected=Vector3.zero;
            foreach(var cluster in raw.clusters) {
                int bone=Array.IndexOf(labels,cluster.bone_label); if(bone<0)throw new Exception("RAW_BONE_UNPROVEN");
                float w=cluster.weights.Where(row=>row.cp==v.cp).Sum(row=>row.weight);
                expected+=live.bones[bone].localToWorldMatrix.MultiplyPoint3x4(mesh.bindposes[bone].MultiplyPoint3x4(positions[v.vertex]))*w;
            }
            v.raw_cpu=expected;
        }
        UnityEngine.Object.DestroyImmediate(baked);UnityEngine.Object.DestroyImmediate(instance);
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out string guid,out long id);
        var i=(ModelImporter)AssetImporter.GetAtPath(path);
        string meta=File.ReadAllText(Path.Combine(Project,path+".meta"));
        var stored=Regex.Match(meta,@"minBoneWeight:\s*([^\r\n]+)");
        return new Capture {name=name,mode=mode,requested=requested,assigned=assigned,getter=i.minBoneWeight,preprocess=SmallWeightPreprocess.preprocessGetter,
            stored=stored.Success?stored.Groups[1].Value:"UNSET",hash=Hash(Path.Combine(Project,path)),mesh_guid=guid,mesh_id=id.ToString(),mesh_label=s.GetComponent<WeightMarker>().meshLabel,vertices=vertices.ToArray(),bones=labels,
            bindposes=mesh.bindposes.Length,shapes=mesh.blendShapeCount,submeshes=mesh.subMeshCount};
    }
    public static void Run() {
        var report=new Report {version=Application.unityVersion,status="FAIL"}; var all=new List<Capture>();
        string source=Path.Combine(Project,"Ladder.fbx"),hash=Hash(source);
        Application.logMessageReceived+=(m,s,t)=> {if(t==LogType.Warning)report.warnings++; if(t==LogType.Error||t==LogType.Exception||t==LogType.Assert)report.errors++;};
        try {
            if(Application.unityVersion!="2022.3.22f1") throw new Exception("WRONG_UNITY_VERSION");
            float[] ladder={0f,1e-8f,.0001f,.0005f,.000999f,.001f,.001001f};
            foreach(string mode in new[]{"save","sync","pre"}) foreach(float request in ladder) {
                string name=mode+"_"+all.Count,path="Assets/Ladder"+all.Count+".fbx";
                SmallWeightPreprocess.apply=mode=="pre";SmallWeightPreprocess.requested=request;
                File.Copy(source,Path.Combine(Project,path)); AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
                var i=(ModelImporter)AssetImporter.GetAtPath(path); float assigned=i.minBoneWeight;
                if(mode!="pre") { i.skinWeights=ModelImporterSkinWeights.Custom;i.maxBonesPerVertex=2;i.minBoneWeight=request;assigned=i.minBoneWeight;
                    if(mode=="save")i.SaveAndReimport();else {AssetDatabase.WriteImportSettingsIfDirty(path);AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);} }
                all.Add(Observe(path,name,mode,request,assigned));
            }
            SmallWeightPreprocess.apply=false;
            foreach(string mode in new[]{"default","standard","custom_default"}) {
                string path="Assets/Ladder"+all.Count+".fbx";File.Copy(source,Path.Combine(Project,path));AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
                var i=(ModelImporter)AssetImporter.GetAtPath(path);
                if(mode!="default") {i.skinWeights=mode=="standard"?ModelImporterSkinWeights.Standard:ModelImporterSkinWeights.Custom;i.SaveAndReimport();}
                all.Add(Observe(path,mode,mode,i.minBoneWeight,i.minBoneWeight));
            }
            report.source_unchanged=Hash(source)==hash;report.status="PASS";
        } catch(Exception e) { Debug.LogException(e); }
        report.cases=all.ToArray();File.WriteAllText(Path.Combine(Project,"Result.json"),JsonUtility.ToJson(report,true));
        Debug.Log("SMALL_WEIGHT_"+report.status);EditorApplication.Exit(report.status=="PASS"?0:1);
    }
    public static void MetaControl() {
        var all=new List<Capture>();
        try {
            SmallWeightPreprocess.apply=false;
            string source=Path.Combine(Project,"Ladder.fbx");
            string meta=File.ReadAllText(Path.Combine(Project,"Assets/Ladder14.fbx.meta"));
            string path="Assets/LadderMetaFirst"+Guid.NewGuid().ToString("N")+".fbx";
            meta=Regex.Replace(meta,@"guid: [0-9a-f]{32}","guid: "+Guid.NewGuid().ToString("N"));
            File.WriteAllText(Path.Combine(Project,path+".meta"),meta);File.Copy(source,Path.Combine(Project,path));
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"meta_first","meta",0,0));
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"meta_reimport","meta",0,0));
            // Reapply at preprocess of the same importer with its clamped getter.
            SmallWeightPreprocess.apply=true;SmallWeightPreprocess.requested=0;
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"pre_reimport","pre",0,0));
            File.WriteAllText(Path.Combine(Project,"MetaResult.json"),JsonUtility.ToJson(new Report {version=Application.unityVersion,status="PASS",cases=all.ToArray()},true));
            Debug.Log("SMALL_WEIGHT_META_PASS");EditorApplication.Exit(0);
        } catch(Exception e) {Debug.LogException(e);EditorApplication.Exit(1);}
    }
    public static void ProductionControl() {
        var all=new List<Capture>();
        try {
            SmallWeightPreprocess.apply=false;
            string source=Path.Combine(Project,"Ladder.fbx"),path="Assets/LadderProduction"+Guid.NewGuid().ToString("N")+".fbx";
            File.Copy(source,Path.Combine(Project,path));AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"without_policy","production",0,0));
            string guid=AssetDatabase.AssetPathToGUID(path);
            Directory.CreateDirectory("Assets/VAPBExport");
            string policyPath="Assets/VAPBExport/SkinWeightPolicy_"+guid+".json";
            File.WriteAllText(policyPath,"{\"version\":1,\"model_guid\":\""+guid+"\",\"model_sha256\":\""+Hash(source)+"\"}");
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"production_policy","production",0,0));
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            all.Add(Observe(path,"production_reimport","production",0,0));
            File.WriteAllText(Path.Combine(Project,"ProductionResult.json"),JsonUtility.ToJson(new Report {version=Application.unityVersion,status="PASS",cases=all.ToArray()},true));
            Debug.Log("SMALL_WEIGHT_PRODUCTION_PASS");EditorApplication.Exit(0);
        } catch(Exception e) {Debug.LogException(e);EditorApplication.Exit(1);}
    }
    public static void PolicyNegative() {
        int rejected=0;
        Application.logMessageReceived+=(m,s,t)=>{if(m.Contains("VAPB_SKIN_WEIGHT_REVISION_MISMATCH"))rejected++;};
        var previous=JsonUtility.FromJson<Report>(File.ReadAllText(Path.Combine(Project,"ProductionResult.json")));
        string guid=previous.cases[1].mesh_guid,path=AssetDatabase.GUIDToAssetPath(guid);
        string policy="Assets/VAPBExport/SkinWeightPolicy_"+guid+".json",original=File.ReadAllText(policy);
        try {
            File.WriteAllText(policy,original.Replace(Hash(Path.Combine(Project,path)),new string('0',64)));
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
        } finally {
            File.WriteAllText(policy,original);
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
        }
        var capture=Observe(path,"after_negative_restore","production",0,0);
        File.WriteAllText(Path.Combine(Project,"PolicyNegative.json"),JsonUtility.ToJson(new Report {status=rejected>0?"REJECTED":"FALSE_PASS",errors=rejected,cases=new[]{capture}},true));
        EditorApplication.Exit(rejected>0?0:1);
    }

    // One source identity observation through the existing product witness.
    [Serializable] private sealed class RootTask {
        public string kind, source_model_guid, source_model_sha256, source_model_uid, source_geometry_uid;
        public string[] source_model_uids;
    }
    [Serializable] private sealed class RootGate {
        public RootTask task;
        public string source_path, source_meta_sha256, noop_sha256, witness_sha256;
    }
    [Serializable] public sealed class RootRow {
        public string guid, uid, parent_guid, parent_uid;
        public long id, parent_id;
    }
    [Serializable] public sealed class RootReport {
        public string version, status, error, source_hash;
        public bool root_null, source_bytes_restored, source_meta_restored, root_reference_stable;
        public RootRow root;
        public RootRow[] bones;
    }
    private static RootRow RootReference(Transform transform, string sourceGuid,
        Dictionary<string,long> uidToId) {
        if(transform==null) return null;
        if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(transform,out string guid,out long id)
            || guid!=sourceGuid || id==0) throw new Exception("ROOT_TRANSFORM_ID_UNPROVEN");
        string[] uids=uidToId.Where(p=>p.Value==id).Select(p=>p.Key).ToArray();
        if(uids.Length!=1) throw new Exception("ROOT_UID_UNPROVEN");
        var row=new RootRow {guid=guid,id=id,uid=uids[0]};
        if(transform.parent!=null) {
            if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(transform.parent,out string pg,out long pi)
                || pg!=sourceGuid || pi==0) throw new Exception("ROOT_PARENT_ID_UNPROVEN");
            string[] puids=uidToId.Where(p=>p.Value==pi).Select(p=>p.Key).ToArray();
            if(puids.Length!=1) throw new Exception("ROOT_PARENT_UID_UNPROVEN");
            row.parent_guid=pg;row.parent_id=pi;row.parent_uid=puids[0];
        }
        return row;
    }
    public static void RootIdentityControl() {
        var report=new RootReport {version=Application.unityVersion,status="FAIL"};
        string[] args=Environment.GetCommandLineArgs();
        int index=Array.IndexOf(args,"-vapbRootGate");
        string folder=index>=0 && index+1<args.Length ? args[index+1] : null;
        try {
            if(folder==null || Application.unityVersion!="2022.3.22f1") throw new Exception("ROOT_GATE_INVALID");
            var gate=JsonUtility.FromJson<RootGate>(File.ReadAllText(Path.Combine(folder,"RootGate.json")));
            string source=AssetDatabase.GUIDToAssetPath(gate.task.source_model_guid);
            if(source!=gate.source_path || Hash(Path.Combine(Project,source))!=gate.task.source_model_sha256
                || Hash(Path.Combine(Project,source+".meta"))!=gate.source_meta_sha256
                || Hash(Path.Combine(folder,"Noop.fbx"))!=gate.noop_sha256
                || Hash(Path.Combine(folder,"Witness.fbx"))!=gate.witness_sha256)
                throw new Exception("ROOT_GATE_REVISION_MISMATCH");
            byte[] original=File.ReadAllBytes(Path.Combine(Project,source));
            byte[] meta=File.ReadAllBytes(Path.Combine(Project,source+".meta"));
            var before=AssetDatabase.LoadAssetAtPath<GameObject>(source).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            bool rootNull=before.rootBone==null;
            long rootId=0;
            if(!rootNull) AssetDatabase.TryGetGUIDAndLocalFileIdentifier(before.rootBone,out string bg,out rootId);
            var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic;
            Type taskType=typeof(VapbModelSkinFinalizer).GetNestedType("Task",flags);
            object task=JsonUtility.FromJson(JsonUtility.ToJson(gate.task),taskType);
            var witness=typeof(VapbModelSkinFinalizer).GetMethod("RunWitness",flags|System.Reflection.BindingFlags.Static);
            object result=witness.Invoke(null,new object[]{source,task,original,meta,
                File.ReadAllBytes(Path.Combine(folder,"Noop.fbx")),File.ReadAllBytes(Path.Combine(folder,"Witness.fbx"))});
            var uidToId=(Dictionary<string,long>)result.GetType().GetField("transformIds",flags|System.Reflection.BindingFlags.Instance).GetValue(result);
            var skin=AssetDatabase.LoadAssetAtPath<GameObject>(source).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            report.root_null=skin.rootBone==null;
            report.root=RootReference(skin.rootBone,gate.task.source_model_guid,uidToId);
            report.bones=skin.bones.Select(b=>RootReference(b,gate.task.source_model_guid,uidToId)).ToArray();
            report.root_reference_stable=rootNull==report.root_null && (rootNull || rootId==report.root.id);
            report.source_bytes_restored=File.ReadAllBytes(Path.Combine(Project,source)).SequenceEqual(original);
            report.source_meta_restored=File.ReadAllBytes(Path.Combine(Project,source+".meta")).SequenceEqual(meta);
            report.source_hash=gate.task.source_model_sha256;
            if(!report.root_reference_stable || !report.source_bytes_restored || !report.source_meta_restored)
                throw new Exception("ROOT_SOURCE_RESTORE_FAILED");
            report.status="OBSERVED";
        } catch(Exception e) {report.error=e.GetBaseException().Message;Debug.LogException(e);}
        if(folder!=null) File.WriteAllText(Path.Combine(folder,"RootResult.json"),JsonUtility.ToJson(report,true));
        Debug.Log("VAPB_ROOT_IDENTITY_"+report.status);
        EditorApplication.Exit(report.status=="OBSERVED"?0:1);
    }
}
