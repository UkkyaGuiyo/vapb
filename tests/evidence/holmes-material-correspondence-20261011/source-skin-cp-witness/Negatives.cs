using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using Unity.Collections;

// Focused controls on the same native consumer and captured CP witness, no purchased fixtures.
public static class HolmesCpNegatives {
 [Serializable] class Entry {public string control,first_rejection;}
 [Serializable] class Results {public string status="PASS";public Entry[] checks;}
 [Serializable] class Marker {public Vector2[] cp_marker;public string[] bone_receipts;}
 static object Get(object o,string k)=>o.GetType().GetField(k).GetValue(o);
 static void Set(object o,string k,object v)=>o.GetType().GetField(k).SetValue(o,v);
 static object Call(Type f,string name,params object[] args)=>f.GetMethod(name,BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,args);
 public static void Run(Type f,string path,string work,object task,GameObject sourceRoot,SkinnedMeshRenderer target,object witness,object source,object edited,string editPath){
  var results=new List<Entry>();
  Action<string,string,Action> reject=(label,expected,action)=>{string error="ACCEPTED";try{action();}catch(Exception e){while(e is TargetInvocationException&&e.InnerException!=null)e=e.InnerException;error=e.Message;}if(error!=expected)throw new Exception(label+": expected "+expected+", got "+error);results.Add(new Entry{control=label,first_rejection=error});};
  Func<object> fresh=()=>((Array)Get(Call(f,"ReadManifest",path),"reference_rebind_tasks")).GetValue(0);
  Action<string,string,Action<object>,string> taskBad=(label,expected,mutate,method)=>{var t=fresh();mutate(t);reject(label,expected,()=>Call(f,method,t));};
  Call(f,"ValidateWeightData",task);results.Add(new Entry{control="no_parent_weight_context",first_rejection="ACCEPTED_VALID"});
  var parentTask=fresh();var pt=f.GetNestedType("ParentTransformMapping",BindingFlags.NonPublic);var parent=Activator.CreateInstance(pt,true);
  Set(parent,"source_model_uid","999001");Set(parent,"edited_transform_realization_id","synthetic-parent");Set(parentTask,"source_model_uids",((string[])Get(parentTask,"source_model_uids")).Concat(new[]{"999001"}).ToArray());Set(parentTask,"parent_transform_mapping",parent);
  Call(f,"ValidateTask",parentTask);Call(f,"ValidateWeightData",parentTask);results.Add(new Entry{control="parent_present_context_regression",first_rejection="ACCEPTED_VALID_CONTEXT_ONLY"});
  Set(parentTask,"weight_transport",null);reject("parent_present_missing_weight","EXPORTED_WEIGHT_DATA_MISSING",()=>Call(f,"ValidateTask",parentTask));
  foreach(string kind in new[]{"RESTORE_MODEL_SKIN_VARIANT_V1","RESTORE_DIRECT_SKIN_VARIANT_V1"})taskBad(kind,"WEIGHT_TRANSPORT_CONTEXT_UNSUPPORTED",t=>Set(t,"kind",kind),"ValidateTask");
  taskBad("cp_row_missing","EXPORTED_WEIGHT_CONTEXT_UNSUPPORTED",t=>{var d=Get(t,"weight_transport");var rows=(Array)Get(d,"points");var smaller=Array.CreateInstance(rows.GetType().GetElementType(),rows.Length-1);Array.Copy(rows,smaller,smaller.Length);Set(d,"points",smaller);},"ValidateWeightData");
  taskBad("cp_row_duplicate","EXPORTED_WEIGHT_DATA_INVALID",t=>{var rows=(Array)Get(Get(t,"weight_transport"),"points");Set(rows.GetValue(0),"cp",(int)Get(rows.GetValue(1),"cp"));},"ValidateWeightData");
  taskBad("cp_row_unknown","EXPORTED_WEIGHT_DATA_INVALID",t=>Set(((Array)Get(Get(t,"weight_transport"),"points")).GetValue(0),"cp",999),"ValidateWeightData");
  taskBad("expected_weight_one_bit","EXPORTED_WEIGHT_DATA_INVALID",t=>{var p=((Array)Get(Get(t,"weight_transport"),"points")).GetValue(0);((int[])Get(p,"expected_bits"))[0]^=1;},"ValidateWeightData");
  taskBad("bone_mapping_duplicate","BONE_MAPPING_INVALID",t=>{var b=(Array)Get(t,"bone_mappings");Set(b.GetValue(0),"source_model_uid",Get(b.GetValue(1),"source_model_uid"));},"ValidateTask");
  foreach(string field in new[]{"source_model_sha256","model_sha256"})taskBad(field,"SOURCE_HASH_OR_PATH_MISMATCH",t=>Set(t,field,new string('0',64)),"CheckSourceHashes");
  foreach(string label in new[]{"material_unknown_provider","material_guid_fileid_mix"}){
   var t=fresh();var b=((Array)Get(t,"material_bindings")).GetValue(0);if(label=="material_unknown_provider")Set(b,"guid",new string('f',32));else Set(b,"file_id","2100001");
   string identity="MODEL_SKIN_MATERIAL_V1:"+Get(b,"guid")+":"+Get(b,"file_id");using(var sha=System.Security.Cryptography.SHA256.Create())Set(b,"transport_id","VAPB-MAT-"+BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(identity))).Replace("-","").ToLowerInvariant().Substring(0,32));
   reject(label,"MATERIAL_TRANSPORT_UNRESOLVED",()=>Call(f,"ResolveMaterialBindings",t));
  }
  var editRoot=AssetDatabase.LoadAssetAtPath<GameObject>(editPath);var native=(SkinnedMeshRenderer)Get(edited,"renderer");var originalRoot=native.rootBone;
  try{native.rootBone=native.bones.First(b=>b!=originalRoot);reject("root_bone_wrong","EDITED_ROOT_INVALID",()=>Call(f,"ResolveEdited",task,editPath,witness,source));}finally{native.rootBone=originalRoot;}
  var clone=UnityEngine.Object.Instantiate(sourceRoot);try{var skin=clone.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();Call(f,"ValidateSourceModelReplacementScope",clone,skin);
   var unknown=clone.AddComponent<BoxCollider>();reject("unknown_component","SOURCE_COMPONENT_SCOPE_UNSUPPORTED",()=>Call(f,"ValidateSourceModelReplacementScope",clone,skin));UnityEngine.Object.DestroyImmediate(unknown);
   var cloth=skin.gameObject.AddComponent<Cloth>();reject("cloth","CLOTH_INDEX_STATE_UNSUPPORTED",()=>Call(f,"ValidateSourceModelReplacementScope",clone,skin));UnityEngine.Object.DestroyImmediate(cloth);
   var extra=new GameObject("shared-mesh-control");extra.transform.SetParent(clone.transform,false);extra.AddComponent<SkinnedMeshRenderer>().sharedMesh=skin.sharedMesh;reject("shared_mesh_second_renderer","SOURCE_RENDERER_SCOPE_UNSUPPORTED",()=>Call(f,"ValidateSourceModelReplacementScope",clone,skin));
  }finally{UnityEngine.Object.DestroyImmediate(clone);}
  var originalMesh=(Mesh)Get(edited,"mesh");var changed=UnityEngine.Object.Instantiate(originalMesh);
  try{Set(edited,"mesh",changed);var poses=changed.bindposes;poses[0].m00+=.01f;changed.bindposes=poses;reject("bindpose","EDITED_REST_MISMATCH",()=>Call(f,"CheckSkinCompatibility",witness,target,edited,source,false));changed.bindposes=originalMesh.bindposes;
   var zeros=new Vector3[changed.vertexCount];changed.AddBlendShapeFrame("negative-shape",100,zeros,zeros,zeros);reject("shape","MODEL_SKIN_SHAPE_KEYS_UNSUPPORTED",()=>Call(f,"CheckSkinCompatibility",witness,target,edited,source,false));
  }finally{Set(edited,"mesh",originalMesh);UnityEngine.Object.DestroyImmediate(changed);}
  var observed=JsonUtility.FromJson<Marker>(File.ReadAllText(Directory.GetFiles(work,"weight-observation-*.json").First()));
  var weightRoot=new GameObject("captured-weight-control");var weightMesh=UnityEngine.Object.Instantiate(originalMesh);var weightSkin=weightRoot.AddComponent<SkinnedMeshRenderer>();weightSkin.sharedMesh=weightMesh;
  try{var markerType=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbRealizationMarker")).Single(t=>t!=null);var bones=new Transform[observed.bone_receipts.Length];for(int i=0;i<bones.Length;i++){var go=new GameObject("captured-bone");go.transform.SetParent(weightRoot.transform,false);bones[i]=go.transform;Set(go.AddComponent(markerType),"boneRealizationId",observed.bone_receipts[i]);}weightSkin.bones=bones;
   weightMesh.SetUVs(1,observed.cp_marker.ToList());Call(f,"CheckWeightRepresentation",task,weightSkin);
   weightMesh.SetUVs(1,new List<Vector2>());reject("cp_marker_missing","EXPORTED_CP_MARKER_MISSING",()=>Call(f,"CheckWeightRepresentation",task,weightSkin));
   var uv=(Vector2[])observed.cp_marker.Clone();uv[0].x=999;weightMesh.SetUVs(1,uv.ToList());reject("cp_marker_unknown","EXPORTED_CP_MARKER_INVALID",()=>Call(f,"CheckWeightRepresentation",task,weightSkin));
   uv=(Vector2[])observed.cp_marker.Clone();int zero=Array.FindIndex(uv,x=>x.x==1);uv[zero].x=2;weightMesh.SetUVs(1,uv.ToList());reject("cp_marker_duplicate_lost_coverage","EXPORTED_CP_COVERAGE_CHANGED",()=>Call(f,"CheckWeightRepresentation",task,weightSkin));weightMesh.SetUVs(1,observed.cp_marker.ToList());
   using(var counts=originalMesh.GetBonesPerVertex())using(var weights=originalMesh.GetAllBoneWeights()){var modified=new NativeArray<BoneWeight1>(weights,Allocator.Temp);try{var value=modified[0];int bits=BitConverter.ToInt32(BitConverter.GetBytes(value.weight),0)^1;value.weight=BitConverter.ToSingle(BitConverter.GetBytes(bits),0);modified[0]=value;weightMesh.SetBoneWeights(counts,modified);reject("native_weight_one_bit","EXPORTED_WEIGHT_REPRESENTATION_CHANGED",()=>Call(f,"CheckWeightRepresentation",task,weightSkin));weightMesh.SetBoneWeights(counts,weights);}finally{modified.Dispose();}}
   Set(bones[0].GetComponent(markerType),"boneRealizationId",observed.bone_receipts[1]);Set(bones[1].GetComponent(markerType),"boneRealizationId",observed.bone_receipts[0]);reject("bone_receipt_swap","EXPORTED_WEIGHT_REPRESENTATION_CHANGED",()=>Call(f,"CheckWeightRepresentation",task,weightSkin));
  }finally{UnityEngine.Object.DestroyImmediate(weightRoot);UnityEngine.Object.DestroyImmediate(weightMesh);}
  var spare=new List<Vector2>();originalMesh.GetUVs(1,spare);try{originalMesh.SetUVs(1,Enumerable.Repeat(Vector2.zero,originalMesh.vertexCount).ToList());reject("occupied_spare_uv","EXPORTED_WEIGHT_UV_OCCUPIED",()=>Call(f,"ValidateExportedWeightTransport",task,editPath,edited));}finally{originalMesh.SetUVs(1,spare);}
  // No-witness differing layout still rejects through ResolvePrepared; no Variant write.
  var missing=fresh();Set(missing,"weight_transport",null);var prepared=Call(f,"PrepareWitness",missing);reject("different_layout_no_witness","SOURCE_MODEL_INDEX_LAYOUT_CHANGED",()=>Call(f,"ResolvePrepared",prepared,sourceRoot));
  File.WriteAllText(Path.Combine(work,"negative-checks.json"),JsonUtility.ToJson(new Results{checks=results.ToArray()},true));
 }
}
