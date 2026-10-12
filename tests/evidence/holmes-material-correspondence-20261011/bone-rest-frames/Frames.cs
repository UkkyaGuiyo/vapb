using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
// Read existing imported13 assets only. No import/export, Apply or instance mutation.
public static class HolmesBoneRestFrames {
 [Serializable] class Mapping {public string source_model_uid,edited_bone_realization_id;}
 [Serializable] class Task {public string source_model_guid,model_guid;public Mapping[] bone_mappings;}
 [Serializable] class Manifest {public Task[] reference_rebind_tasks;}
 [Serializable] class Ref {public string guid,file_id;}
 [Serializable] class Bone {public Ref identity,parent;public Vector3 local_position,local_scale;public Quaternion local_rotation;public float[] world,local_matrix,renderer_relative,bindpose;}
 [Serializable] class Skin {public Ref renderer,mesh,root;public float[] renderer_world;public Bone[] bones;}
 [Serializable] class Candidate {public string uid;public int index,parent_index;public bool non_bone_parent_unchanged;public float[] desired_world,local_matrix,reconstructed;public Vector3 position,scale;public Quaternion rotation;public float max_matrix_error,edited_bindpose_max_error;}
 [Serializable] class Report {public string instruction_id="HOLMES-20261012-14",status="FAIL",error,unity_version,source_fbx_sha256,edited_fbx_sha256,fixed13_manifest_sha256;public Skin source,edited;public Candidate[] candidate;}
 static string Arg(string key){var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,key);return i<0?"":a[i+1];}
 static float[] M(Matrix4x4 m){return Enumerable.Range(0,16).Select(i=>m[i]).ToArray();}
 static float Err(Matrix4x4 a,Matrix4x4 b){return Enumerable.Range(0,16).Max(i=>Mathf.Abs(a[i]-b[i]));}
 static string Hash(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant();}
 static Ref Id(UnityEngine.Object o){if(o==null)return null;if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o,out string g,out long i))throw new Exception("MissingIdentity");return new Ref{guid=g,file_id=i.ToString(System.Globalization.CultureInfo.InvariantCulture)};}
 static Skin Capture(SkinnedMeshRenderer s){return new Skin{renderer=Id(s),mesh=Id(s.sharedMesh),root=Id(s.rootBone),renderer_world=M(s.transform.localToWorldMatrix),bones=s.bones.Select((b,i)=>new Bone{identity=Id(b),parent=Id(b.parent),local_position=b.localPosition,local_rotation=b.localRotation,local_scale=b.localScale,local_matrix=M(Matrix4x4.TRS(b.localPosition,b.localRotation,b.localScale)),world=M(b.localToWorldMatrix),renderer_relative=M(s.transform.worldToLocalMatrix*b.localToWorldMatrix),bindpose=M(s.sharedMesh.bindposes[i])}).ToArray()};}
 public static void Run(){var r=new Report{unity_version=Application.unityVersion};try{
  string fixedPath=Arg("-restManifest");r.fixed13_manifest_sha256=Hash(fixedPath);
  var task=JsonUtility.FromJson<Manifest>(File.ReadAllText(fixedPath)).reference_rebind_tasks.Single();
  string sourcePath=AssetDatabase.GUIDToAssetPath(task.source_model_guid),editedPath=AssetDatabase.GUIDToAssetPath(task.model_guid);
  var a=AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
  var b=AssetDatabase.LoadAssetAtPath<GameObject>(editedPath).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
  if(a.bones.Length!=2||b.bones.Length!=2)throw new Exception("FrozenBoneCountChanged");
  r.source=Capture(a);r.edited=Capture(b);r.source_fbx_sha256=Hash(sourcePath);r.edited_fbx_sha256=Hash(editedPath);
  var map=task.bone_mappings.ToDictionary(x=>x.edited_bone_realization_id,x=>x.source_model_uid,StringComparer.Ordinal);
  var uid=b.bones.Select(x=>map[x.GetComponent<VapbRealizationMarker>().boneRealizationId]).ToArray();
  if(uid.Distinct().Count()!=uid.Length)throw new Exception("EditedMappingAmbiguous");
  // Index correspondence was actually validated before the fixed13 rest rejection.
  // Bind this capture to those source/edited identities and hashes in offline judgment.
  var desired=b.bones.Select(x=>a.transform.localToWorldMatrix*b.transform.worldToLocalMatrix*x.localToWorldMatrix).ToArray();
  r.candidate=Enumerable.Range(0,2).Select(i=>{
   int sourceParent=Array.IndexOf(a.bones,a.bones[i].parent),editedParent=Array.IndexOf(b.bones,b.bones[i].parent);
   if(sourceParent!=editedParent)throw new Exception("ParentIndexChanged");
   Matrix4x4 parent=sourceParent<0?a.bones[i].parent.localToWorldMatrix:desired[sourceParent];
   Matrix4x4 local=parent.inverse*desired[i];Vector3 pos=local.GetColumn(3),scale=local.lossyScale;Quaternion rot=local.rotation;
   Matrix4x4 reconstructed=Matrix4x4.TRS(pos,rot,scale);
   return new Candidate{uid=uid[i],index=i,parent_index=sourceParent,non_bone_parent_unchanged=sourceParent<0,desired_world=M(desired[i]),local_matrix=M(local),reconstructed=M(reconstructed),position=pos,scale=scale,rotation=rot,max_matrix_error=Err(local,reconstructed),edited_bindpose_max_error=Err(b.sharedMesh.bindposes[i],b.bones[i].worldToLocalMatrix*b.transform.localToWorldMatrix)};
  }).ToArray();r.status="OBSERVED";
 }catch(Exception e){r.error=e.ToString();}
 File.WriteAllText(Path.Combine(Arg("-freshWork"),"native.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="FAIL"?1:0);
 }
}
