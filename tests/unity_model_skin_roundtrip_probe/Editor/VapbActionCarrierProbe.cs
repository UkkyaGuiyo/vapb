// SPDX-License-Identifier: MIT
// Copyright (c) 2026 VAPB contributors
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// One owned carrier measurement, using the existing source witness contract.
public sealed class VapbActionCarrierProbeImporter : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject node, string[] names, object[] values)
    {
        if (assetPath != VapbActionCarrierProbe.CarrierPath) return;
        for (int i=0;i<names.Length;i++)
        {
            if (names[i]!="_vapb_fbx_bone_realization_id" && names[i]!="_vapb_fbx_realization_id") continue;
            string value=values[i] as string;
            if (String.IsNullOrEmpty(value)) continue;
            var marker=node.GetComponent<VapbRealizationMarker>() ?? node.AddComponent<VapbRealizationMarker>();
            if(names[i]=="_vapb_fbx_bone_realization_id") marker.boneRealizationId=value;
            else marker.realizationId=value;
        }
    }
}

public static class VapbActionCarrierProbe
{
    public const string CarrierPath="Assets/VapbActionCarrierProbeOwned/Carrier.fbx";
    [Serializable] public sealed class Bone { public string edited_bone_realization_id,source_model_uid; }
    [Serializable] public sealed class Config { public string task_json,source_model_guid,source_model_sha256; public Bone[] bone_mappings; public string[] animated_bone_realization_ids; public float[] frames; public float fps; }
    [Serializable] public sealed class Result {
        public bool pass, source_identity_resolved,one_take,unique_markers,local_rest_basis_equal,independent_clip_created;
        public string error,clip_path,take_name; public int curves,total_bones,authored_bones,ignored_constant_curves;
        public float max_local_rest_difference,max_local_pose_difference; public string[] binding_paths;
    }
    private const BindingFlags Flags=BindingFlags.Static|BindingFlags.NonPublic;
    private static string Argument(string name) { string[] a=Environment.GetCommandLineArgs(); int i=Array.IndexOf(a,name); if(i<0||i+1>=a.Length) throw new InvalidOperationException("MISSING_ARGUMENT:"+name); return a[i+1]; }
    private static string Disk(string path) { return Path.Combine(Directory.GetParent(Application.dataPath).FullName,path); }
    private static Matrix4x4 Local(Transform t) { return Matrix4x4.TRS(t.localPosition,t.localRotation,t.localScale); }
    private static float Difference(Matrix4x4 a,Matrix4x4 b) { float d=0; for(int i=0;i<16;i++) { if(float.IsNaN(a[i])||float.IsNaN(b[i])) return float.PositiveInfinity; d=Mathf.Max(d,Mathf.Abs(a[i]-b[i])); } return d; }
    private static bool Constant(AnimationCurve c) { if(c==null||c.length==0)return false; foreach(Keyframe k in c.keys) if(k.value!=c.keys[0].value) return false; return true; }

    public static void Run()
    {
        var result=new Result(); AnimationClip independent=null; GameObject sourceCopy=null,carrierCopy=null;
        try
        {
            Config config=JsonUtility.FromJson<Config>(File.ReadAllText(Argument("-vapbCarrierConfig")));
            Type finalizer=typeof(VapbModelSkinFinalizer), taskType=finalizer.GetNestedType("Task",BindingFlags.NonPublic);
            object task=JsonUtility.FromJson(config.task_json,taskType);
            object plan=finalizer.GetMethod("PrepareWitness",Flags).Invoke(null,new[]{task});
            object witness=plan.GetType().GetField("witness").GetValue(plan);
            var ids=(Dictionary<string,long>)witness.GetType().GetField("transformIds").GetValue(witness);
            GameObject source=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(config.source_model_guid));
            if(source==null) throw new InvalidOperationException("SOURCE_ROOT_MISSING");
            var targets=new Dictionary<string,Transform>();
            foreach(Bone row in config.bone_mappings)
            {
                if(!ids.TryGetValue(row.source_model_uid,out long id)) throw new InvalidOperationException("SOURCE_UID_MISSING");
                Transform found=null;
                foreach(Transform t in source.GetComponentsInChildren<Transform>(true))
                    if(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(t,out string guid,out long local) && guid==config.source_model_guid && local==id)
                    { if(found!=null)throw new InvalidOperationException("SOURCE_UID_AMBIGUOUS"); found=t; }
                if(found==null) throw new InvalidOperationException("SOURCE_BONE_MISSING");
                targets.Add(row.edited_bone_realization_id,found);
            }
            result.source_identity_resolved=true; result.total_bones=targets.Count;
            ModelImporter importer=AssetImporter.GetAtPath(CarrierPath) as ModelImporter;
            if(importer==null)throw new InvalidOperationException("CARRIER_MISSING");
            importer.importAnimation=true; importer.animationType=ModelImporterAnimationType.Legacy;
            importer.animationCompression=ModelImporterAnimationCompression.Off;
            importer.optimizeGameObjects=false; importer.SaveAndReimport();
            ModelImporterClipAnimation[] takes=importer.defaultClipAnimations;
            if(takes.Length!=1)throw new InvalidOperationException("TAKE_NOT_UNIQUE");
            result.one_take=true; result.take_name=takes[0].name;
            AnimationClip take=null;
            foreach(UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(CarrierPath))
                if(asset is AnimationClip c && c.name==takes[0].name)
                { if(take!=null)throw new InvalidOperationException("CLIP_NOT_UNIQUE"); take=c; }
            if(take==null)throw new InvalidOperationException("TAKE_CLIP_MISSING");
            if(AnimationUtility.GetObjectReferenceCurveBindings(take).Length!=0)throw new InvalidOperationException("OBJECT_CURVES_UNSUPPORTED");
            GameObject carrier=AssetDatabase.LoadAssetAtPath<GameObject>(CarrierPath);
            var transported=new Dictionary<string,Transform>();
            foreach(VapbRealizationMarker marker in carrier.GetComponentsInChildren<VapbRealizationMarker>(true))
                if(!String.IsNullOrEmpty(marker.boneRealizationId)) transported.Add(marker.boneRealizationId,marker.transform);
            if(transported.Count!=targets.Count)throw new InvalidOperationException("BONE_MARKERS_INCOMPLETE");
            result.unique_markers=true;
            foreach(var row in targets)
            {
                if(!transported.ContainsKey(row.Key)) throw new InvalidOperationException("BONE_MARKER_MISSING");
                result.max_local_rest_difference=Mathf.Max(result.max_local_rest_difference,Difference(Local(row.Value),Local(transported[row.Key])));
            }
            result.local_rest_basis_equal=result.max_local_rest_difference<0.00001f;
            if(!result.local_rest_basis_equal) throw new InvalidOperationException("CARRIER_TARGET_LOCAL_REST_BASIS_DIFFERS");
            var authored=new HashSet<string>(config.animated_bone_realization_ids,StringComparer.Ordinal);
            result.authored_bones=authored.Count;
            var paths=new Dictionary<string,string>(StringComparer.Ordinal); var targetPaths=new Dictionary<string,string>(StringComparer.Ordinal);
            foreach(string id in authored)
            {
                if(!targets.ContainsKey(id)||!transported.ContainsKey(id))throw new InvalidOperationException("AUTHORED_BONE_MISSING");
                string path=AnimationUtility.CalculateTransformPath(targets[id],source.transform);
                int count=0; foreach(Transform t in source.GetComponentsInChildren<Transform>(true)) if(AnimationUtility.CalculateTransformPath(t,source.transform)==path)count++;
                if(count!=1) throw new InvalidOperationException("TARGET_PATH_AMBIGUOUS");
                paths.Add(AnimationUtility.CalculateTransformPath(transported[id],carrier.transform),path); targetPaths.Add(id,path);
            }
            independent=new AnimationClip { name="OwnedEditedAction",legacy=false,frameRate=config.fps };
            var addresses=new HashSet<string>(StringComparer.Ordinal);
            foreach(EditorCurveBinding binding in AnimationUtility.GetCurveBindings(take))
            {
                AnimationCurve curve=AnimationUtility.GetEditorCurve(take,binding);
                if(!paths.TryGetValue(binding.path,out string targetPath))
                { if(!Constant(curve))throw new InvalidOperationException("UNEXPECTED_MOTION_BINDING"); result.ignored_constant_curves++; continue; }
                if(binding.type!=typeof(Transform)||!System.Text.RegularExpressions.Regex.IsMatch(binding.propertyName,@"^(m_LocalPosition\.[xyz]|m_LocalRotation\.[xyzw]|m_LocalScale\.[xyz]|localEulerAnglesRaw\.[xyz])$"))
                    throw new InvalidOperationException("CHANNEL_UNSUPPORTED:"+binding.propertyName);
                EditorCurveBinding mapped=binding; mapped.path=targetPath;
                if(!addresses.Add(mapped.path+":"+mapped.propertyName))throw new InvalidOperationException("BINDING_AMBIGUOUS");
                AnimationUtility.SetEditorCurve(independent,mapped,curve); result.curves++;
            }
            if(result.curves==0)throw new InvalidOperationException("NO_AUTHORED_CURVES");
            result.binding_paths=new string[targetPaths.Count]; targetPaths.Values.CopyTo(result.binding_paths,0);
            sourceCopy=UnityEngine.Object.Instantiate(source); carrierCopy=UnityEngine.Object.Instantiate(carrier);
            foreach(float fraction in new[]{0f,0.5f,1f})
            {
                float time=take.length*fraction;
                take.SampleAnimation(carrierCopy,time); independent.SampleAnimation(sourceCopy,time);
                foreach(string id in authored)
                {
                    Transform a=sourceCopy.transform.Find(targetPaths[id]);
                    Transform b=carrierCopy.transform.Find(AnimationUtility.CalculateTransformPath(transported[id],carrier.transform));
                    result.max_local_pose_difference=Mathf.Max(result.max_local_pose_difference,Difference(Local(a),Local(b)));
                }
            }
            if(result.max_local_pose_difference>=0.00001f)throw new InvalidOperationException("REMAPPED_POSE_DIFFERS");
            result.clip_path="Assets/VapbActionCarrierProbeOwned/Independent.anim";
            if(File.Exists(Disk(result.clip_path))||File.Exists(Disk(result.clip_path)+".meta"))throw new InvalidOperationException("CLIP_PATH_OCCUPIED");
            AssetDatabase.CreateAsset(independent,result.clip_path); independent=null; AssetDatabase.SaveAssets();
            result.independent_clip_created=true; result.pass=true;
        }
        catch(Exception e) { result.error=e is TargetInvocationException && e.InnerException!=null ? e.InnerException.Message : e.Message; }
        finally {
            if(sourceCopy!=null)UnityEngine.Object.DestroyImmediate(sourceCopy); if(carrierCopy!=null)UnityEngine.Object.DestroyImmediate(carrierCopy);
            if(independent!=null)UnityEngine.Object.DestroyImmediate(independent);
            File.WriteAllText(Argument("-vapbCarrierResult"),JsonUtility.ToJson(result,true));
            Debug.Log("VAPB_ACTION_CARRIER_NATIVE="+result.pass+" rest_difference="+result.max_local_rest_difference+" error="+result.error);
            EditorApplication.Exit(result.pass?0:1);
        }
    }
}