using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
public static class HolmesReturnedAncestry {
 [Serializable] class Task{public string source_model_guid,model_guid,variant_path;}
 [Serializable] class Manifest{public Task[] reference_rebind_tasks;}
 [Serializable] class Ref{public string guid,file_id;}
 [Serializable] class Report{public bool pass,variant_ancestry,source_root_identity,source_bone_identity,source_parent_identity,edited_mesh_identity,materials_identity,assets_unchanged;public Ref root_source;public Ref[] bone_sources,parent_sources;}
 static Ref Id(UnityEngine.Object o){if(o==null)return null;AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o,out string guid,out long id);return new Ref{guid=guid,file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture)};}
 static bool Same(UnityEngine.Object a,UnityEngine.Object b){return JsonUtility.ToJson(Id(a))==JsonUtility.ToJson(Id(b));}
 static UnityEngine.Object Source(UnityEngine.Object o){return PrefabUtility.GetCorrespondingObjectFromSource(o);}
 static string Hash(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p)));}
 public static void Run(){var args=Environment.GetCommandLineArgs();string work=args[Array.IndexOf(args,"-freshWork")+1];var paths=Directory.GetFiles("Assets","*",SearchOption.AllDirectories);var hashes=paths.Select(Hash).ToArray();var t=JsonUtility.FromJson<Manifest>(File.ReadAllText("Assets/VAPBExport/manifest.json")).reference_rebind_tasks.Single();var source=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(t.source_model_guid));var variant=AssetDatabase.LoadAssetAtPath<GameObject>(t.variant_path);var edit=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(t.model_guid));var ss=source.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var vs=variant.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var es=edit.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var r=new Report{variant_ancestry=PrefabUtility.GetPrefabAssetType(variant)==PrefabAssetType.Variant&&Same(Source(variant),source),source_root_identity=Same(Source(vs.rootBone),ss.rootBone),source_bone_identity=vs.bones.Length==ss.bones.Length&&vs.bones.Select((b,i)=>Same(Source(b),ss.bones[i])).All(x=>x),source_parent_identity=vs.bones.Select((b,i)=>Same(Source(b.parent),ss.bones[i].parent)).All(x=>x),edited_mesh_identity=Same(vs.sharedMesh,es.sharedMesh),materials_identity=vs.sharedMaterials.Length==ss.sharedMaterials.Length&&vs.sharedMaterials.Select((m,i)=>Same(m,ss.sharedMaterials[i])).All(x=>x),root_source=Id(Source(vs.rootBone)),bone_sources=vs.bones.Select(b=>Id(Source(b))).ToArray(),parent_sources=vs.bones.Select(b=>Id(Source(b.parent))).ToArray(),assets_unchanged=hashes.SequenceEqual(paths.Select(Hash))};r.pass=r.variant_ancestry&&r.source_root_identity&&r.source_bone_identity&&r.source_parent_identity&&r.edited_mesh_identity&&r.materials_identity&&r.assets_unchanged;File.WriteAllText(Path.Combine(work,"native.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.pass?0:1);}
}
