using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
public static class HolmesAuthoredOneBit {
 [Serializable] class Result {public string status,control="expected_weight_one_bit",first_rejection,manifest_before_sha256,manifest_after_sha256;public bool accepted,variant_unchanged,source_manifest_unchanged;}
 static string Hash(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant();}
 public static void Run(Type f,string path,string work,string variant){
  const string control="Assets/VAPBExport/AuthoredWeightOneBit.json";
  if(File.Exists(control))throw new Exception("NegativeOutputOccupied");
  string text=File.ReadAllText(path);var pattern=new Regex("(\"expected_bits\"\\s*:\\s*\\[\\s*)1059061760");
  if(pattern.Matches(text).Count!=1)throw new Exception("NegativeExpectedCPNotUnique");
  string beforeVariant=Hash(variant),beforeManifest=Hash(path);
  var errors=new System.Collections.Generic.List<string>();Application.LogCallback log=(msg,stack,type)=>{if(type==LogType.Error||type==LogType.Exception)errors.Add(msg);};
  var r=new Result{manifest_before_sha256=beforeManifest};
  try{File.WriteAllText(control,pattern.Replace(text,m=>m.Groups[1].Value+"1059061761",1));AssetDatabase.ImportAsset(control,ImportAssetOptions.ForceSynchronousImport);Application.logMessageReceived+=log;
   r.accepted=(bool)f.GetMethod("Apply").Invoke(null,new object[]{control});
  }finally{Application.logMessageReceived-=log;AssetDatabase.DeleteAsset(control);}
  r.first_rejection=errors.Single();r.manifest_after_sha256=Hash(path);r.source_manifest_unchanged=beforeManifest==r.manifest_after_sha256;r.variant_unchanged=beforeVariant==Hash(variant);
  if(r.accepted||r.first_rejection!="VAPB_MODEL_SKIN_VARIANT_REJECTED=EXPORTED_WEIGHT_DATA_INVALID"||!r.variant_unchanged||!r.source_manifest_unchanged)throw new Exception("OneBitSafetyRefusalFailed");
  r.status="PASS";File.WriteAllText(Path.Combine(work,"negative.json"),JsonUtility.ToJson(r,true));
 }
}
