using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;
public static class HolmesRestControls {
 static object Make(Type f,string n)=>Activator.CreateInstance(f.GetNestedType(n,BindingFlags.NonPublic),true);
 static void Set(object o,string n,object v)=>o.GetType().GetField(n,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(o,v);
 static object Get(object o,string n)=>o.GetType().GetField(n,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).GetValue(o);
 static object Call(Type f,string n,params object[] a){try{return f.GetMethod(n,BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,a);}catch(TargetInvocationException e){throw e.InnerException;}}
 static void Reject(List<string> result,string label,string expected,Action action){try{action();throw new Exception("ControlAccepted:"+label);}catch(Exception e){if(!e.Message.Contains(expected))throw;result.Add(label+":"+expected);}}
 static string Hash(byte[] a){using(var h=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(h.ComputeHash(a)).Replace("-","");}
 public static string[] Run(Type f,string manifest,string variant,string sourcePath,string editedPath,string work){var result=new List<string>();GameObject source=null,edited=null;Mesh mesh=null;
 try{
  source=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath));edited=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(editedPath));
  var a=source.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var b=edited.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();mesh=UnityEngine.Object.Instantiate(b.sharedMesh);b.sharedMesh=mesh;
  string[] uids=Enumerable.Range(0,a.bones.Length).Select(i=>"owned-control-"+i).ToArray();
  var si=Make(f,"SourceIdentity");Set(si,"renderer",a);Set(si,"sourceModel",true);Set(si,"sourceBoneUids",uids);Set(si,"rootUid",uids[Array.IndexOf(a.bones,a.rootBone)]);
  IDictionary map=(IDictionary)Get(si,"bonesByUid");for(int i=0;i<uids.Length;i++)map.Add(uids[i],a.bones[i]);
  var ei=Make(f,"EditedIdentity");Set(ei,"renderer",b);Set(ei,"mesh",mesh);Set(ei,"editedBoneUids",uids);
  if(((Array)Call(f,"PrepareSourceBoneRest",a,ei,si)).Length!=uids.Length)throw new Exception("PositiveRestPreparation");result.Add("positive-rest-preparation");
  var animator=source.AddComponent<Animator>();Reject(result,"source-Animator","SOURCE_COMPONENT_SCOPE_UNSUPPORTED",()=>Call(f,"ValidateSourceModelReplacementScope",source,a));UnityEngine.Object.DestroyImmediate(animator);
  var cloth=b.gameObject.AddComponent<Cloth>();Reject(result,"edited-Cloth","CLOTH_INDEX_STATE_UNSUPPORTED",()=>Call(f,"ValidateSourceModelReplacementScope",edited,b));UnityEngine.Object.DestroyImmediate(cloth);
  var original=mesh.bindposes;var bad=(Matrix4x4[])original.Clone();bad[0].m00+=.01f;mesh.bindposes=bad;
  Reject(result,"invalid-bindpose","EDITED_REST_MISMATCH",()=>Call(f,"PrepareSourceBoneRest",a,ei,si));mesh.bindposes=original;
  Vector3 scale=b.transform.localScale;b.transform.localScale=Vector3.zero;
  Reject(result,"singular-renderer-frame","SOURCE_REST_FRAME_INVALID",()=>Call(f,"PrepareSourceBoneRest",a,ei,si));b.transform.localScale=scale;
  b.transform.localScale=new Vector3(scale.x*2,scale.y,scale.z);mesh.bindposes=b.bones.Select(x=>x.worldToLocalMatrix*b.transform.localToWorldMatrix).ToArray();
  Reject(result,"unrepresentable-rest-TRS","SOURCE_REST_TRS_UNREPRESENTABLE",()=>Call(f,"PrepareSourceBoneRest",a,ei,si));b.transform.localScale=scale;mesh.bindposes=original;
  Matrix4x4 nan=Matrix4x4.identity;nan.m00=float.NaN;
  if((bool)Call(f,"InvertibleRestMatrix",nan)||(bool)Call(f,"InvertibleRestMatrix",Matrix4x4.zero)||!(bool)Call(f,"InvertibleRestMatrix",Matrix4x4.identity))throw new Exception("FiniteInvertibleMatrixControl");result.Add("nonfinite-singular-matrices-refused");
 }finally{if(source!=null)UnityEngine.Object.DestroyImmediate(source);if(edited!=null)UnityEngine.Object.DestroyImmediate(edited);if(mesh!=null)UnityEngine.Object.DestroyImmediate(mesh);}
 foreach(string which in new[]{"managed-bone","unmanaged-renderer"}){
  byte[] original=File.ReadAllBytes(variant),meta=File.ReadAllBytes(variant+".meta");GameObject contents=null;
  try{contents=PrefabUtility.LoadPrefabContents(variant);var skin=contents.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();Transform target=which=="managed-bone"?skin.bones[1]:skin.transform;target.localPosition+=new Vector3(.01f,0,0);PrefabUtility.RecordPrefabInstancePropertyModifications(target);PrefabUtility.SaveAsPrefabAsset(contents,variant);PrefabUtility.UnloadPrefabContents(contents);contents=null;
   byte[] altered=File.ReadAllBytes(variant);var errors=new List<string>();Application.LogCallback log=(m,s,t)=>{if(t==LogType.Error||t==LogType.Exception)errors.Add(m);};Application.logMessageReceived+=log;bool applied;try{applied=(bool)f.GetMethod("Apply").Invoke(null,new object[]{manifest});}finally{Application.logMessageReceived-=log;}
   string expected=which=="managed-bone"?"VARIANT_BONE_REST_CHANGED":"VARIANT_MODIFICATION_UNKNOWN";
   bool correct=errors.Any(x=>x.Contains(expected))||(which=="unmanaged-renderer"&&errors.Any(x=>x.Contains("VARIANT_TRANSFORM_CHANGED")));
   if(applied||!correct||!altered.SequenceEqual(File.ReadAllBytes(variant))||!meta.SequenceEqual(File.ReadAllBytes(variant+".meta")))throw new Exception("TamperControl:"+which+":"+String.Join(";",errors));
   File.WriteAllText(Path.Combine(work,"tamper-"+which+".json"),JsonUtility.ToJson(new Tamper{control=which,apply=false,rejection=errors.ToArray(),altered_bytes_preserved=true,meta_preserved=true,original_hash=Hash(original),altered_hash=Hash(altered)},true));result.Add(which+":"+String.Join(";",errors));
  }finally{if(contents!=null)PrefabUtility.UnloadPrefabContents(contents);File.WriteAllBytes(variant,original);File.WriteAllBytes(variant+".meta",meta);AssetDatabase.ImportAsset(variant,ImportAssetOptions.ForceUpdate);}
 }
 return result.ToArray();
 }
 [Serializable]class Tamper{public string control,original_hash,altered_hash;public bool apply,altered_bytes_preserved,meta_preserved;public string[] rejection;}
}
