// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public sealed class NumericWeightPreprocess : AssetPostprocessor
{
    void OnPreprocessModel() {
        if(assetPath!="Assets/Numeric.fbx")return;
        var i=(ModelImporter)assetImporter;i.animationType=ModelImporterAnimationType.Generic;i.isReadable=true;
        i.optimizeMeshVertices=false;i.optimizeMeshPolygons=false;i.weldVertices=false;
        i.extraUserProperties=new[]{"_vapb_weight_bone_id","_vapb_weight_mesh_id"};
    }
    void OnPostprocessGameObjectWithUserProperties(GameObject obj,string[] names,object[] values) {
        if(assetPath!="Assets/Numeric.fbx")return;
        for(int i=0;i<names.Length;i++) {
            if(names[i]!="_vapb_weight_bone_id" && names[i]!="_vapb_weight_mesh_id")continue;
            var m=obj.GetComponent<WeightMarker>()??obj.AddComponent<WeightMarker>();
            if(names[i]=="_vapb_weight_bone_id")m.boneLabel=Convert.ToString(values[i]);else m.meshLabel=Convert.ToString(values[i]);
        }
    }
}
public static class WeightNumericProbe
{
    [Serializable] public class Weight {public int bone,order;public string label;public float value;public uint bits;}
    [Serializable] public class Basis {public string label;public Vector3 rest,posed;}
    [Serializable] public class Vertex {public int vertex,cp;public Weight[] weights;public double sum64;public float sum32;public Vector3 rest,posed;public Basis[] basis;}
    [Serializable] public class Capture {public string hash,guid,id,mesh_label;public Vertex[] vertices;public string[] bones;public int max_bones;public float getter;}
    [Serializable] public class Source {public string fbx_sha256;public int cp_count;}
    [Serializable] public class Report {public string status="FAIL",version;public int errors,warnings;public Capture first,repeated;public bool input_unchanged;}
    const string Asset="Assets/Numeric.fbx";
    static string Project=>Path.GetDirectoryName(Application.dataPath);
    static string Hash(string p) {using(var s=SHA256.Create())return BitConverter.ToString(s.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant();}
    static Capture Observe(Source source) {
        var asset=AssetDatabase.LoadAssetAtPath<GameObject>(Asset);var instance=UnityEngine.Object.Instantiate(asset);
        var skin=instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var mesh=skin.sharedMesh;
        if(skin.GetComponent<WeightMarker>()?.meshLabel!="WEIGHT-MESH-0")throw new Exception("WRONG_MESH");
        var labels=skin.bones.Select(b=>b.GetComponent<WeightMarker>()?.boneLabel).ToArray();
        if(labels.Length!=4||labels.Any(l=>l==null)||labels.Distinct().Count()!=4)throw new Exception("BONE_ID_UNPROVEN");
        var rows=new List<Vertex>();var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();int offset=0;
        var rest=new Mesh();var posed=new Mesh();
        try {
            skin.BakeMesh(rest,true);var positions=mesh.vertices;
            var restBasis=skin.bones.Select((b,i)=>positions.Select(p=>(b.localToWorldMatrix*mesh.bindposes[i]).MultiplyPoint3x4(p)).ToArray()).ToArray();
            for(int i=0;i<skin.bones.Length;i++) {
                if(!Int32.TryParse(labels[i].Substring("WEIGHT-BONE-".Length),out int n))throw new Exception("BONE_LABEL_INVALID");
                skin.bones[i].position+=new Vector3(-(n+1)*.125f,0,0);
            }
            skin.BakeMesh(posed,true);
            var posedBasis=skin.bones.Select((b,i)=>positions.Select(p=>(b.localToWorldMatrix*mesh.bindposes[i]).MultiplyPoint3x4(p)).ToArray()).ToArray();
            for(int v=0;v<mesh.vertexCount;v++) {
                var uv=mesh.uv[v];int cp=(int)Math.Round(uv.x)-1;
                if(cp<0||cp>=source.cp_count||Math.Abs(uv.x-(cp+1))>1e-5||Math.Abs(uv.y-.375)>1e-5)throw new Exception("CP_MAPPING_UNPROVEN");
                var entries=new List<Weight>();double sum64=0;float sum32=0;
                for(int n=0;n<counts[v];n++) {var w=weights[offset++];entries.Add(new Weight {bone=w.boneIndex,order=n,label=labels[w.boneIndex],value=w.weight,bits=BitConverter.ToUInt32(BitConverter.GetBytes(w.weight),0)});sum64+=w.weight;sum32+=w.weight;}
                rows.Add(new Vertex {vertex=v,cp=cp,weights=entries.ToArray(),sum64=sum64,sum32=sum32,rest=skin.transform.TransformPoint(rest.vertices[v]),posed=skin.transform.TransformPoint(posed.vertices[v]),
                    basis=labels.Select((l,b)=>new Basis {label=l,rest=restBasis[b][v],posed=posedBasis[b][v]}).ToArray()});
            }
        } finally {counts.Dispose();weights.Dispose();UnityEngine.Object.DestroyImmediate(rest);UnityEngine.Object.DestroyImmediate(posed);UnityEngine.Object.DestroyImmediate(instance);}
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out string guid,out long id);
        var importer=(ModelImporter)AssetImporter.GetAtPath(Asset);
        return new Capture {hash=Hash(Asset),guid=guid,id=id.ToString(),mesh_label="WEIGHT-MESH-0",bones=labels,vertices=rows.ToArray(),getter=importer.minBoneWeight,max_bones=importer.maxBonesPerVertex};
    }
    public static void Run() {
        var report=new Report {version=Application.unityVersion};
        Application.logMessageReceived+=(m,s,t)=> {if(t==LogType.Warning)report.warnings++;if(t==LogType.Error||t==LogType.Exception||t==LogType.Assert)report.errors++;};
        try {
            if(Application.unityVersion!="2022.3.22f1")throw new Exception("WRONG_UNITY_VERSION");
            var source=JsonUtility.FromJson<Source>(File.ReadAllText(Path.Combine(Project,"Source.json")));
            string input=Path.Combine(Project,"Ladder.fbx");if(Hash(input)!=source.fbx_sha256)throw new Exception("STALE_FBX");
            if(!File.Exists(Asset))File.Copy(input,Asset);
            AssetDatabase.ImportAsset(Asset,ImportAssetOptions.ForceSynchronousImport);
            string guid=AssetDatabase.AssetPathToGUID(Asset);Directory.CreateDirectory("Assets/VAPBExport");
            File.WriteAllText("Assets/VAPBExport/SkinWeightPolicy_"+guid+".json","{\"version\":1,\"model_guid\":\""+guid+"\",\"model_sha256\":\""+source.fbx_sha256+"\"}");
            AssetDatabase.ImportAsset(Asset,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);report.first=Observe(source);
            AssetDatabase.ImportAsset(Asset,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);report.repeated=Observe(source);
            report.input_unchanged=Hash(input)==source.fbx_sha256;report.status="PASS";
        } catch(Exception e){Debug.LogException(e);}
        File.WriteAllText(Path.Combine(Project,"NumericResult.json"),JsonUtility.ToJson(report,true));Debug.Log("WEIGHT_NUMERIC_"+report.status);EditorApplication.Exit(report.status=="PASS"?0:1);
    }
}
