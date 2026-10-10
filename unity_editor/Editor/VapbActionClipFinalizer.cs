// SPDX-License-Identifier: MIT
// Copyright (c) 2026 VAPB contributors
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

public sealed class VapbActionClipPostprocessor : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject node, string[] names, object[] values)
    { VapbModelSkinFinalizer.MarkActionCarrierNode(assetPath, node, names, values); }
}

public static partial class VapbModelSkinFinalizer
{
    [Serializable] private sealed class ActionClipRecipe
    {
        public int version;
        public string carrier_guid, carrier_sha256, output_path;
        public string[] animated_bone_realization_ids;
        public float fps, duration;
    }
    private static string actionImportPath;
    private static HashSet<string> actionImportBones;
    internal static void MarkActionCarrierNode(string path, GameObject node, string[] names, object[] values)
    {
        if (path != actionImportPath || actionImportBones == null || names == null || values == null || names.Length != values.Length) return;
        for (int i=0;i<names.Length;i++)
        {
            string value=values[i] as string;
            bool bone=names[i]=="_vapb_fbx_bone_realization_id" && actionImportBones.Contains(value ?? "");
            bool root=names[i]=="_vapb_fbx_realization_id" && value=="VAPB-ActionRoot";
            if (!bone && !root) continue;
            var marker=node.GetComponent<VapbRealizationMarker>() ?? node.AddComponent<VapbRealizationMarker>();
            if(bone) marker.boneRealizationId=value; else marker.realizationId=value;
        }
    }
    private static void ValidateActionRecipe(Task task)
    {
        ActionClipRecipe data=task.action_clip;
        if(data==null) return;
        if(data.version!=1 || !CanonicalGuid(data.carrier_guid) || !ValidSha(data.carrier_sha256) ||
           data.carrier_guid==task.source_model_guid || data.carrier_guid==task.model_guid ||
           data.output_path!="Assets/VAPBExport/EditedAction_"+data.carrier_guid+".anim" ||
           !Finite(data.fps) || data.fps<=0 || !Finite(data.duration) || data.duration<=0 ||
           data.animated_bone_realization_ids==null || data.animated_bone_realization_ids.Length==0 || task.bone_mappings==null)
            Reject("ACTION_RECIPE_INVALID");
        var seen=new HashSet<string>(StringComparer.Ordinal);
        foreach(string id in data.animated_bone_realization_ids)
            if(String.IsNullOrEmpty(id) || !seen.Add(id) || !Array.Exists(task.bone_mappings,b=>b!=null && b.edited_bone_realization_id==id))
                Reject("ACTION_BONE_SCOPE_INVALID");
    }
    private static string ActionInstructions(Task[] tasks)
    {
        string output="";
        foreach(Task task in tasks) if(task.action_clip!=null)
            output+="\nIndependent Clip: "+task.action_clip.output_path+"\nPlayback root: root GameObject of "+task.variant_path+" (manual assignment; Controller unchanged)";
        return output;
    }
    private static Matrix4x4 ActionLocal(Transform t) { return Matrix4x4.TRS(t.localPosition,t.localRotation,t.localScale); }
    private static bool ActionLocalEqual(Transform a,Transform b)
    {
        Matrix4x4 x=ActionLocal(a),y=ActionLocal(b);
        for(int i=0;i<16;i++) if(!Finite(x[i]) || !Finite(y[i]) || Mathf.Abs(x[i]-y[i])>=0.00001f) return false;
        return true;
    }
    private static string ActionParent(Transform t, Dictionary<string,Transform> map)
    { foreach(var row in map) if(t.parent==row.Value) return row.Key; return null; }
    private static bool StaticActionCurve(AnimationCurve curve)
    {
        if(curve==null || curve.length==0) return false;
        foreach(Keyframe k in curve.keys)
            if(!Finite(k.value) || k.value!=curve.keys[0].value || k.inTangent!=0f || k.outTangent!=0f) return false;
        return true;
    }
    private static AnimationClip PrepareActionClip(PreparedTask plan,GameObject original)
    {
        var data=plan.task.action_clip; if(data==null) return null;
        string path=AssetDatabase.GUIDToAssetPath(data.carrier_guid);
        if(path!="Assets/VAPBExport/ActionCarrier_"+data.carrier_guid+".fbx" ||
           !FileHash(Disk(path)).Equals(data.carrier_sha256,StringComparison.OrdinalIgnoreCase)) Reject("ACTION_CARRIER_HASH_OR_PATH_MISMATCH");
        var importer=AssetImporter.GetAtPath(path) as ModelImporter;
        if(importer==null) Reject("ACTION_CARRIER_UNAVAILABLE");
        if(!importer.useFileScale || importer.globalScale!=1f || importer.bakeAxisConversion) Reject("ACTION_CARRIER_UNITS_UNSUPPORTED");
        actionImportPath=path; actionImportBones=new HashSet<string>(StringComparer.Ordinal);
        foreach(BoneMapping row in plan.task.bone_mappings) actionImportBones.Add(row.edited_bone_realization_id);
        try { importer.importAnimation=true; importer.animationType=ModelImporterAnimationType.Legacy;
            importer.animationCompression=ModelImporterAnimationCompression.Off; importer.optimizeGameObjects=false;
            importer.SaveAndReimport(); }
        finally { actionImportPath=null; actionImportBones=null; }
        if(importer.defaultClipAnimations.Length!=1) Reject("ACTION_TAKE_NOT_UNIQUE");
        AnimationClip take=null;
        foreach(UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
            if(asset is AnimationClip clip && clip.name==importer.defaultClipAnimations[0].name)
            { if(take!=null) Reject("ACTION_CLIP_NOT_UNIQUE"); take=clip; }
        if(take==null || !Finite(take.length) || Mathf.Abs(take.length-data.duration)>0.0001f ||
           AnimationUtility.GetObjectReferenceCurveBindings(take).Length!=0 || AnimationUtility.GetAnimationEvents(take).Length!=0)
            Reject("ACTION_TAKE_UNSUPPORTED");
        var carrier=AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if(carrier==null) Reject("ACTION_CARRIER_UNAVAILABLE");
        var transported=new Dictionary<string,Transform>(StringComparer.Ordinal);
        int roots=0;
        foreach(var marker in carrier.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if(marker.realizationId=="VAPB-ActionRoot") roots++;
            if(String.IsNullOrEmpty(marker.boneRealizationId)) continue;
            if(transported.ContainsKey(marker.boneRealizationId)) Reject("ACTION_BONE_MARKER_AMBIGUOUS");
            transported.Add(marker.boneRealizationId,marker.transform);
        }
        if(roots!=1 || transported.Count!=plan.task.bone_mappings.Length) Reject("ACTION_CARRIER_MARKERS_INVALID");
        var targets=new Dictionary<string,Transform>(StringComparer.Ordinal);
        foreach(var row in plan.task.bone_mappings)
        {
            if(!transported.ContainsKey(row.edited_bone_realization_id) || !plan.source.bonesByUid.TryGetValue(row.source_model_uid,out Transform target))
                Reject("ACTION_TARGET_BONE_MISSING");
            targets.Add(row.edited_bone_realization_id,plan.source.bonesByUid[row.source_model_uid]);
        }
        foreach(var row in targets)
        {
            if(!ActionLocalEqual(row.Value,transported[row.Key])) Reject("ACTION_LOCAL_REST_DIFFERS");
            if(ActionParent(row.Value,targets)!=ActionParent(transported[row.Key],transported)) Reject("ACTION_PARENT_DIFFERS");
        }
        var paths=new Dictionary<string,string>(StringComparer.Ordinal);
        foreach(string id in data.animated_bone_realization_ids)
        {
            string target=AnimationUtility.CalculateTransformPath(targets[id],original.transform);
            int count=0; foreach(Transform t in original.GetComponentsInChildren<Transform>(true))
                if(AnimationUtility.CalculateTransformPath(t,original.transform)==target)count++;
            if(count!=1 || String.IsNullOrEmpty(target)) Reject("ACTION_TARGET_PATH_AMBIGUOUS");
            string source=AnimationUtility.CalculateTransformPath(transported[id],carrier.transform);
            if(paths.ContainsKey(source)) Reject("ACTION_CARRIER_PATH_AMBIGUOUS");
            paths.Add(source,target);
        }
        var result=new AnimationClip {name="VAPB Edited Bone Action",legacy=false,frameRate=data.fps};
        GameObject a=null,b=null; bool prepared=false;
        try
        {
            var addresses=new HashSet<string>(StringComparer.Ordinal); var bound=new HashSet<string>(StringComparer.Ordinal);
            foreach(EditorCurveBinding binding in AnimationUtility.GetCurveBindings(take))
            {
                var curve=AnimationUtility.GetEditorCurve(take,binding);
                if(!paths.TryGetValue(binding.path,out string target))
                { if(!StaticActionCurve(curve)) Reject("ACTION_UNEXPECTED_MOTION_BINDING"); continue; }
                if(binding.type!=typeof(Transform) || !Regex.IsMatch(binding.propertyName,@"^(m_LocalPosition\.[xyz]|m_LocalRotation\.[xyzw]|m_LocalScale\.[xyz]|localEulerAnglesRaw\.[xyz])$")) Reject("ACTION_CHANNEL_UNSUPPORTED");
                foreach(Keyframe key in curve.keys) if(!Finite(key.time) || !Finite(key.value) || Single.IsNaN(key.inTangent) || Single.IsNaN(key.outTangent)) Reject("ACTION_CURVE_VALUES_INVALID");
                var mapped=binding; mapped.path=target;
                if(!addresses.Add(target+":"+mapped.propertyName)) Reject("ACTION_BINDING_AMBIGUOUS");
                AnimationUtility.SetEditorCurve(result,mapped,curve); bound.Add(binding.path);
            }
            if(bound.Count!=paths.Count) Reject("ACTION_AUTHORED_BINDINGS_MISSING");
            a=UnityEngine.Object.Instantiate(original); b=UnityEngine.Object.Instantiate(carrier);
            foreach(float fraction in new[]{0f,0.5f,1f})
            {
                take.SampleAnimation(b,take.length*fraction); result.SampleAnimation(a,take.length*fraction);
                foreach(var row in paths) if(!ActionLocalEqual(a.transform.Find(row.Value),b.transform.Find(row.Key))) Reject("ACTION_REMAPPED_POSE_DIFFERS");
            }
            AnimationClip existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(data.output_path);
            if(File.Exists(Disk(data.output_path)) || File.Exists(Disk(data.output_path)+".meta") || existing!=null)
            { if(existing==null || !SameActionClip(existing,result)) Reject("ACTION_CLIP_PATH_OCCUPIED"); }
            prepared=true; return result;
        }
        finally { if(a!=null)UnityEngine.Object.DestroyImmediate(a); if(b!=null)UnityEngine.Object.DestroyImmediate(b); if(!prepared)UnityEngine.Object.DestroyImmediate(result); }
    }
    private static bool SameActionClip(AnimationClip a, AnimationClip b)
    {
        if(a.legacy || a.frameRate!=b.frameRate || AnimationUtility.GetObjectReferenceCurveBindings(a).Length!=0 || AnimationUtility.GetAnimationEvents(a).Length!=0) return false;
        var x=AnimationUtility.GetCurveBindings(a); var y=AnimationUtility.GetCurveBindings(b); if(x.Length!=y.Length)return false;
        foreach(var binding in y)
        {
            var ac=AnimationUtility.GetEditorCurve(a,binding);var bc=AnimationUtility.GetEditorCurve(b,binding);
            if(ac==null || ac.length!=bc.length || ac.preWrapMode!=bc.preWrapMode || ac.postWrapMode!=bc.postWrapMode) return false;
            var ak=ac.keys;var bk=bc.keys;for(int i=0;i<ak.Length;i++) if(!ak[i].Equals(bk[i]))return false;
        }
        return true;
    }
    private static void ApplyVariantWithActionClips(List<PreparedTask> plans,GameObject original)
    {
        var clips=new Dictionary<PreparedTask,AnimationClip>();var paths=new HashSet<string>(StringComparer.Ordinal);
        var created=new List<string>(); string variant=plans[0].task.variant_path;
        bool existingVariant=File.Exists(Disk(variant)) || File.Exists(Disk(variant)+".meta"); bool saved=false,complete=false;
        try
        {
            foreach(var plan in plans) if(plan.task.action_clip!=null)
            { if(!paths.Add(plan.task.action_clip.output_path)) Reject("ACTION_OUTPUT_PATH_DUPLICATE"); clips.Add(plan,PrepareActionClip(plan,original)); }
            SaveVariant(plans,original); saved=true;
            foreach(var row in clips)
            {
                string path=row.Key.task.action_clip.output_path;
                if(AssetDatabase.LoadAssetAtPath<AnimationClip>(path)==null)
                { created.Add(path); AssetDatabase.CreateAsset(row.Value,path); }
                AssetDatabase.SaveAssets();
                if(!SameActionClip(AssetDatabase.LoadAssetAtPath<AnimationClip>(path),row.Value)) Reject("ACTION_CLIP_RELOAD_DIFFERS");
                Debug.Log("VAPB_INDEPENDENT_ACTION_CLIP="+path+" PLAYBACK_ROOT="+variant+" MANUAL_ASSIGNMENT_REQUIRED");
            }
            complete=true;
        }
        finally
        {
            if(!complete) { foreach(string path in created) AssetDatabase.DeleteAsset(path); if(saved && !existingVariant) AssetDatabase.DeleteAsset(variant); }
            foreach(var clip in clips.Values) if(!AssetDatabase.Contains(clip)) UnityEngine.Object.DestroyImmediate(clip);
        }
    }
}