using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
// Existing geometry observer/CPU equation, one frozen active two-Shape owned case.
public static class HolmesActiveShapeBakeProbe {
 [Serializable] class Task {public string model_guid,source_model_guid,variant_path;}
 [Serializable] class Manifest {public Task[] reference_rebind_tasks;}
 [Serializable] class Matrix {public float[] values;}
 [Serializable] class FileRow {public string path,before,after;}
 [Serializable] class Report {public string instruction_id="HOLMES-20261012-12",status="FAIL",error,unity_version,package_sha256,finalizer_sha256,mesh_guid,mesh_file_id,mesh_asset_sha256;public bool assets_bytes_preserved;public float[] shape_weights,renderer_local_to_world;public Vector3[] positions,effective_positions,cpu_weighted_world_positions,baked_true_world_positions,baked_false_world_positions;public Matrix[] bone_matrices,bindposes;public FileRow[] protected_files;}
 static string Arg(string k){var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,k);return i<0?"":a[i+1];}
 static string Hash(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant();}
 static float[] M(Matrix4x4 m){return Enumerable.Range(0,16).Select(i=>m[i]).ToArray();}
 public static void Run(){var r=new Report{unity_version=Application.unityVersion};GameObject instance=null;Mesh baked=null;
 try {
  var t=JsonUtility.FromJson<Manifest>(File.ReadAllText("Assets/VAPBExport/manifest.json")).reference_rebind_tasks.Single();
  var asset=AssetDatabase.LoadAssetAtPath<GameObject>(t.variant_path);if(asset==null)throw new Exception("FrozenVariantMissing");
  var original=asset.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
  var paths=new[]{AssetDatabase.GUIDToAssetPath(t.source_model_guid),AssetDatabase.GUIDToAssetPath(t.model_guid),t.variant_path}.Concat(original.sharedMaterials.Select(AssetDatabase.GetAssetPath)).Distinct().SelectMany(p=>new[]{p,p+".meta"}).ToArray();
  r.protected_files=paths.Select(p=>new FileRow{path=p,before=Hash(p)}).ToArray();
  r.package_sha256=Hash(Arg("-deformPackage"));r.finalizer_sha256=Hash("Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs");
  instance=UnityEngine.Object.Instantiate(asset);instance.name=asset.name;
  var skin=instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var mesh=skin.sharedMesh;
  r.shape_weights=Enumerable.Range(0,mesh.blendShapeCount).Select(skin.GetBlendShapeWeight).ToArray();
  if(!r.shape_weights.SequenceEqual(new[]{100f,0f})||skin.bones.Length!=2)throw new Exception("FrozenActiveStateChanged");
  if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out r.mesh_guid,out long id))throw new Exception("MeshIdentityMissing");r.mesh_file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture);r.mesh_asset_sha256=Hash(AssetDatabase.GetAssetPath(mesh));
  r.positions=mesh.vertices;r.effective_positions=(Vector3[])r.positions.Clone();
  for(int s=0;s<mesh.blendShapeCount;s++){if(mesh.GetBlendShapeFrameCount(s)!=1||mesh.GetBlendShapeFrameWeight(s,0)!=100f)throw new Exception("FrozenFrameChanged");var delta=new Vector3[mesh.vertexCount];var normal=new Vector3[mesh.vertexCount];var tangent=new Vector3[mesh.vertexCount];mesh.GetBlendShapeFrameVertices(s,0,delta,normal,tangent);for(int v=0;v<mesh.vertexCount;v++)r.effective_positions[v]+=delta[v]*(r.shape_weights[s]/100f);}
  r.renderer_local_to_world=M(skin.transform.localToWorldMatrix);r.bone_matrices=skin.bones.Select(x=>new Matrix{values=M(x.localToWorldMatrix)}).ToArray();r.bindposes=mesh.bindposes.Select(x=>new Matrix{values=M(x)}).ToArray();
  r.cpu_weighted_world_positions=new Vector3[mesh.vertexCount];var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();int offset=0;
  try{if(counts.Length!=mesh.vertexCount)throw new Exception("WeightCountMismatch");for(int v=0;v<mesh.vertexCount;v++){if(counts[v]==0)throw new Exception("MissingInfluence");for(int j=0;j<counts[v];j++){var q=weights[offset++];if(q.boneIndex<0||q.boneIndex>=skin.bones.Length||float.IsNaN(q.weight)||float.IsInfinity(q.weight)||q.weight<=0)throw new Exception("InvalidInfluence");r.cpu_weighted_world_positions[v]+=q.weight*(skin.bones[q.boneIndex].localToWorldMatrix*mesh.bindposes[q.boneIndex]).MultiplyPoint3x4(r.effective_positions[v]);}}if(offset!=weights.Length)throw new Exception("WeightCursorMismatch");}finally{counts.Dispose();weights.Dispose();}
  baked=new Mesh{hideFlags=HideFlags.HideAndDontSave};
  skin.BakeMesh(baked,true);r.baked_true_world_positions=baked.vertices.Select(skin.transform.TransformPoint).ToArray();
  skin.BakeMesh(baked,false);r.baked_false_world_positions=baked.vertices.Select(skin.transform.TransformPoint).ToArray();
  if(r.baked_true_world_positions.Length!=mesh.vertexCount||r.baked_false_world_positions.Length!=mesh.vertexCount)throw new Exception("BakedCountMismatch");
  foreach(var p in r.protected_files)p.after=Hash(p.path);r.assets_bytes_preserved=r.protected_files.All(p=>p.before==p.after);if(!r.assets_bytes_preserved)throw new Exception("ProtectedAssetChanged");r.status="OBSERVED";
 }catch(Exception ex){r.error=ex.ToString();}
 finally{if(baked!=null)UnityEngine.Object.DestroyImmediate(baked);if(instance!=null)UnityEngine.Object.DestroyImmediate(instance);}
 File.WriteAllText(Path.Combine(Arg("-deformWork"),"native.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="FAIL"?1:0);
 }
}
