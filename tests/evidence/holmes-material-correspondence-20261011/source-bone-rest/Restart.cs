using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
public static class HolmesSourceRestRestart {
 [Serializable]class Task{public string variant_path;}
 [Serializable]class Manifest{public Task[] reference_rebind_tasks;}
 [Serializable]class Report{public string instruction_id="HOLMES-20261012-15-RESTART",status="FAIL",error,unity_version;public bool apply,variant_bytes_unchanged,variant_meta_unchanged,variant_semantics_unchanged,all_existing_files_unchanged;public int protected_file_count;public Vector3 bounds_center_before,bounds_extent_before,bounds_center_after,bounds_extent_after;}
 static string Arg(string n){var a=Environment.GetCommandLineArgs();return a[Array.IndexOf(a,n)+1];}
 static string H(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p)));}
 public static void Run(){var r=new Report{unity_version=Application.unityVersion};try{
  string manifest="Assets/VAPBExport/manifest.json",variant=JsonUtility.FromJson<Manifest>(File.ReadAllText(manifest)).reference_rebind_tasks.Single().variant_path;
  var capture=typeof(HolmesSourceRestConsumer).GetMethod("Capture",BindingFlags.NonPublic|BindingFlags.Static);
  var v=AssetDatabase.LoadAssetAtPath<GameObject>(variant);string sem=JsonUtility.ToJson(capture.Invoke(null,new object[]{v})),bytes=H(variant),meta=H(variant+".meta");var skin=v.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();r.bounds_center_before=skin.localBounds.center;r.bounds_extent_before=skin.localBounds.extents;
  var paths=new[]{"Assets","Packages","ProjectSettings"}.SelectMany(p=>Directory.GetFiles(p,"*",SearchOption.AllDirectories)).ToArray();var hashes=paths.Select(H).ToArray();r.protected_file_count=paths.Length;
  r.apply=VapbModelSkinFinalizer.Apply(manifest);
  v=AssetDatabase.LoadAssetAtPath<GameObject>(variant);skin=v.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();r.bounds_center_after=skin.localBounds.center;r.bounds_extent_after=skin.localBounds.extents;
  r.variant_bytes_unchanged=bytes==H(variant);r.variant_meta_unchanged=meta==H(variant+".meta");r.variant_semantics_unchanged=sem==JsonUtility.ToJson(capture.Invoke(null,new object[]{v}));r.all_existing_files_unchanged=hashes.SequenceEqual(paths.Select(H));
  if(!r.apply||!r.variant_bytes_unchanged||!r.variant_meta_unchanged||!r.variant_semantics_unchanged||!r.all_existing_files_unchanged||r.bounds_center_before!=r.bounds_center_after||r.bounds_extent_before!=r.bounds_extent_after)throw new Exception("RestartPersistenceMismatch");
  HolmesSourceRestGeometry.Capture();r.status="PASS";
 }catch(Exception e){r.error=e.ToString();}
 File.WriteAllText(Path.Combine(Arg("-freshWork"),"restart.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="PASS"?0:1);
 }
}
