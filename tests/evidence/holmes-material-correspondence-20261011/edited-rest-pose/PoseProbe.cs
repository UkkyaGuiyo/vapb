using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
// Existing geometry observer/CPU equation, one frozen active two-Shape owned case.
public static class HolmesEditedRestPoseGeometry {
 [Serializable] class Mapping {public string source_model_uid,edited_bone_realization_id;}
 [Serializable] class Pose {public string selected_bone_uid;public float[] delta;}
 [Serializable] class Task {public string model_guid,source_model_guid,variant_path;public Mapping[] bone_mappings;}
 [Serializable] class Manifest {public Task[] reference_rebind_tasks;}
 [Serializable] class Matrix {public float[] values;}
 [Serializable] class FileRow {public string path,before,after;}
 [Serializable] class Report {public string instruction_id="HOLMES-20261012-16",status="FAIL",error,unity_version,package_sha256,finalizer_sha256,mesh_guid,mesh_file_id,mesh_asset_sha256;public string selected_uid;public float local_trs_reconstruction_error,nonzero_native_displacement_m;public float[] bone_world_before,bone_world_after,pose_world_delta,local_pose_matrix;public bool assets_bytes_preserved;public float[] shape_weights,renderer_local_to_world;public Vector3[] positions,effective_positions,cpu_weighted_world_positions,baked_true_world_positions,baked_false_world_positions;public Matrix[] bone_matrices,bindposes;public FileRow[] protected_files;}
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
  r.package_sha256=Hash(Arg("-freshPackage"));r.finalizer_sha256=Hash("Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs");
  instance=UnityEngine.Object.Instantiate(asset);instance.name=asset.name;
  var skin=instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();var mesh=skin.sharedMesh;
  var posedInput=JsonUtility.FromJson<Pose>(File.ReadAllText(Arg("-poseInput")));
  var nativeEdited=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(t.model_guid)).GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
  var mapping=t.bone_mappings.ToDictionary(q=>q.edited_bone_realization_id,q=>q.source_model_uid,StringComparer.Ordinal);
  var uids=nativeEdited.bones.Select(b=>mapping[b.GetComponent<VapbRealizationMarker>().boneRealizationId]).ToArray();
  int selected=Array.IndexOf(uids,posedInput.selected_bone_uid);if(selected<0||uids.Count(x=>x==posedInput.selected_bone_uid)!=1||skin.bones.Length!=uids.Length)throw new Exception("SelectedBoneIdentity");
  r.selected_uid=posedInput.selected_bone_uid;var bone=skin.bones[selected];r.bone_world_before=M(bone.localToWorldMatrix);
  var deltaBlender=new Matrix4x4();if(posedInput.delta.Length!=16)throw new Exception("WorldDeltaLength");for(int i=0;i<16;i++)deltaBlender[i]=posedInput.delta[i];
  var basis=Matrix4x4.identity;basis.m00=-1;basis.m11=0;basis.m12=1;basis.m21=-1;basis.m22=0;
  Matrix4x4 frame=original.transform.localToWorldMatrix*nativeEdited.transform.worldToLocalMatrix;
  Matrix4x4 poseDelta=frame*basis*deltaBlender*basis.inverse*frame.inverse;
  Matrix4x4 desired=poseDelta*bone.localToWorldMatrix,local=bone.parent.worldToLocalMatrix*desired;
  Vector3 position=local.GetColumn(3),scale=local.lossyScale;Quaternion rotation=local.rotation;Matrix4x4 rebuilt=Matrix4x4.TRS(position,rotation,scale);
  r.local_trs_reconstruction_error=Enumerable.Range(0,16).Max(i=>Mathf.Abs(local[i]-rebuilt[i]));if(r.local_trs_reconstruction_error>0.001f||Enumerable.Range(0,16).Any(i=>float.IsNaN(local[i])||float.IsInfinity(local[i])))throw new Exception("PoseLocalTRSUnrepresentable");
  var beforeBake=new Mesh{hideFlags=HideFlags.HideAndDontSave};Vector3[] restWorld;
  try{skin.BakeMesh(beforeBake,true);restWorld=beforeBake.vertices.Select(skin.transform.TransformPoint).ToArray();}finally{UnityEngine.Object.DestroyImmediate(beforeBake);}
  bone.localPosition=position;bone.localRotation=rotation;bone.localScale=scale;
  r.bone_world_after=M(bone.localToWorldMatrix);r.pose_world_delta=M(poseDelta);r.local_pose_matrix=M(local);
  r.shape_weights=Enumerable.Range(0,mesh.blendShapeCount).Select(skin.GetBlendShapeWeight).ToArray();
  if(!r.shape_weights.SequenceEqual(new[]{0f,0f,0f})||skin.bones.Length!=2)throw new Exception("FrozenActiveStateChanged");
  if(!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out r.mesh_guid,out long id))throw new Exception("MeshIdentityMissing");r.mesh_file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture);r.mesh_asset_sha256=Hash(AssetDatabase.GetAssetPath(mesh));
  r.positions=mesh.vertices;r.effective_positions=(Vector3[])r.positions.Clone();
  for(int s=0;s<mesh.blendShapeCount;s++){if(mesh.GetBlendShapeFrameCount(s)!=1||mesh.GetBlendShapeFrameWeight(s,0)!=100f)throw new Exception("FrozenFrameChanged");var delta=new Vector3[mesh.vertexCount];var normal=new Vector3[mesh.vertexCount];var tangent=new Vector3[mesh.vertexCount];mesh.GetBlendShapeFrameVertices(s,0,delta,normal,tangent);for(int v=0;v<mesh.vertexCount;v++)r.effective_positions[v]+=delta[v]*(r.shape_weights[s]/100f);}
  r.renderer_local_to_world=M(skin.transform.localToWorldMatrix);r.bone_matrices=skin.bones.Select(x=>new Matrix{values=M(x.localToWorldMatrix)}).ToArray();r.bindposes=mesh.bindposes.Select(x=>new Matrix{values=M(x)}).ToArray();
  r.cpu_weighted_world_positions=new Vector3[mesh.vertexCount];var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();int offset=0;
  try{if(counts.Length!=mesh.vertexCount)throw new Exception("WeightCountMismatch");for(int v=0;v<mesh.vertexCount;v++){if(counts[v]==0)throw new Exception("MissingInfluence");for(int j=0;j<counts[v];j++){var q=weights[offset++];if(q.boneIndex<0||q.boneIndex>=skin.bones.Length||float.IsNaN(q.weight)||float.IsInfinity(q.weight)||q.weight<=0)throw new Exception("InvalidInfluence");r.cpu_weighted_world_positions[v]+=q.weight*(skin.bones[q.boneIndex].localToWorldMatrix*mesh.bindposes[q.boneIndex]).MultiplyPoint3x4(r.effective_positions[v]);}}if(offset!=weights.Length)throw new Exception("WeightCursorMismatch");}finally{counts.Dispose();weights.Dispose();}
  baked=new Mesh{hideFlags=HideFlags.HideAndDontSave};
  skin.BakeMesh(baked,true);r.baked_true_world_positions=baked.vertices.Select(skin.transform.TransformPoint).ToArray();
  skin.BakeMesh(baked,false);r.baked_false_world_positions=baked.vertices.Select(skin.transform.TransformPoint).ToArray();
  r.nonzero_native_displacement_m=Enumerable.Range(0,restWorld.Length).Max(i=>Vector3.Distance(restWorld[i],r.baked_true_world_positions[i]));if(r.nonzero_native_displacement_m<0.01f)throw new Exception("NonzeroPoseNotObserved");
  if(r.baked_true_world_positions.Length!=mesh.vertexCount||r.baked_false_world_positions.Length!=mesh.vertexCount)throw new Exception("BakedCountMismatch");
  foreach(var p in r.protected_files)p.after=Hash(p.path);r.assets_bytes_preserved=r.protected_files.All(p=>p.before==p.after);if(!r.assets_bytes_preserved)throw new Exception("ProtectedAssetChanged");r.status="OBSERVED";
 }catch(Exception ex){r.error=ex.ToString();}
 finally{if(baked!=null)UnityEngine.Object.DestroyImmediate(baked);if(instance!=null)UnityEngine.Object.DestroyImmediate(instance);}
 File.WriteAllText(Path.Combine(Arg("-freshWork"),"native.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="FAIL"?1:0);
 }
}
