using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
public static class HolmesAuthoredRepeat {
 [Serializable] class Task {public string variant_path,source_model_guid,model_guid;}
 [Serializable] class Manifest {public Task[] reference_rebind_tasks;}
 [Serializable] class Result {public string status="FAIL",error,before_variant_sha256,after_variant_sha256,before_semantic_sha256,after_semantic_sha256;public bool apply,variant_bytes_unchanged,variant_meta_unchanged,variant_semantics_unchanged,source_material_manifest_files_unchanged;}
 static string Hash(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
 static string H(string p)=>Hash(File.ReadAllBytes(p));
 static string Arg(string k){var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,k);return a[i+1];}
 static string Snapshot(string path){var type=typeof(HolmesAuthoredWeightConsumer);var method=type.GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic);return JsonUtility.ToJson(method.Invoke(null,new object[]{AssetDatabase.LoadAssetAtPath<GameObject>(path)}));}
 public static void Run(){var r=new Result();try{
  const string manifest="Assets/VAPBExport/manifest.json";var t=JsonUtility.FromJson<Manifest>(File.ReadAllText(manifest)).reference_rebind_tasks.Single();
  string source=AssetDatabase.GUIDToAssetPath(t.source_model_guid),edit=AssetDatabase.GUIDToAssetPath(t.model_guid);
  var skin=AssetDatabase.LoadAssetAtPath<GameObject>(t.variant_path).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
  string[] paths=new[]{manifest,source,source+".meta",edit,edit+".meta"}.Concat(skin.sharedMaterials.SelectMany(m=>new[]{AssetDatabase.GetAssetPath(m),AssetDatabase.GetAssetPath(m)+".meta"})).Distinct().ToArray();
  var hashes=paths.Select(H).ToArray();string meta=H(t.variant_path+".meta"),before=Snapshot(t.variant_path);r.before_variant_sha256=H(t.variant_path);r.before_semantic_sha256=Hash(System.Text.Encoding.UTF8.GetBytes(before));
  r.apply=VapbModelSkinFinalizer.Apply(manifest);
  string after=Snapshot(t.variant_path);r.after_variant_sha256=H(t.variant_path);r.after_semantic_sha256=Hash(System.Text.Encoding.UTF8.GetBytes(after));
  r.variant_bytes_unchanged=r.before_variant_sha256==r.after_variant_sha256;r.variant_meta_unchanged=meta==H(t.variant_path+".meta");r.variant_semantics_unchanged=before==after;r.source_material_manifest_files_unchanged=hashes.SequenceEqual(paths.Select(H));
  if(!r.apply||!r.variant_bytes_unchanged||!r.variant_meta_unchanged||!r.variant_semantics_unchanged||!r.source_material_manifest_files_unchanged)throw new Exception("REAPPLY_MUTATION");r.status="PASS";
 }catch(Exception e){r.error=e.ToString();}File.WriteAllText(Path.Combine(Arg("-freshWork"),"repeat-invariance.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="PASS"?0:1);}
}
