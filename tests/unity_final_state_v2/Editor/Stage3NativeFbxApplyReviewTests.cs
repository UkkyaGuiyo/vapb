// Synthetic native-FBX integration candidate for the marked disposable TargetProject.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

[Parallelizable(ParallelScope.None)]
public sealed class Stage3NativeFbxApplyReviewTests
{
 const string TestRootEnvironment="VAPB_STAGE3_TEST_ROOT";
 const string RootMarker=".vapb-stage3-owned-test-root";
 const string RootMarkerValue="VAPB_STAGE3_OWNED_TEST_ROOT_V1";
 const string SourceMarker=".vapb-stage3-owned-source-project";
 const string SourceMarkerValue="VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1";
 const string TargetMarker=".vapb-disposable-unity-test-project";
 static string TestRoot {
  get {
   string raw=Environment.GetEnvironmentVariable(TestRootEnvironment);
   Assert.IsFalse(string.IsNullOrWhiteSpace(raw),"Set VAPB_STAGE3_TEST_ROOT to an explicitly marked disposable run root.");
   string root=Path.GetFullPath(raw).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
   Assert.IsTrue(Directory.Exists(root),"Stage3 test root directory missing");
   AssertNoReparsePoint(root,"test root");
   for(string parent=Path.GetDirectoryName(root);!string.IsNullOrEmpty(parent);parent=Path.GetDirectoryName(parent))
    Assert.IsFalse(File.Exists(Path.Combine(parent,".git"))||Directory.Exists(Path.Combine(parent,".git")),"A test root inside a Git checkout is not allowed.");
   string git=Path.Combine(root,".git");
   Assert.IsFalse(File.Exists(git)||Directory.Exists(git),"A Git checkout cannot be used as the disposable test root.");
   string rootMarker=Path.Combine(root,RootMarker);
   AssertNoReparsePoint(rootMarker,"test-root marker");
   Assert.IsTrue(File.Exists(rootMarker),"Owned Stage3 test-root marker missing");
   Assert.AreEqual(RootMarkerValue,File.ReadAllText(rootMarker).Trim(),"Owned Stage3 test-root marker value");
   string source=Path.Combine(root,"SourceProject"),target=Path.Combine(root,"TargetProject");
   Assert.IsTrue(Directory.Exists(source)&&Directory.Exists(target),"Owned SourceProject/TargetProject missing");
   AssertNoReparsePoint(source,"SourceProject");
   AssertNoReparsePoint(target,"TargetProject");
   Assert.IsTrue(string.Equals(root,Path.GetDirectoryName(Path.GetFullPath(source)),StringComparison.OrdinalIgnoreCase),"SourceProject must be a direct child of the owned run root");
   Assert.IsTrue(string.Equals(root,Path.GetDirectoryName(Path.GetFullPath(target)),StringComparison.OrdinalIgnoreCase),"TargetProject must be a direct child of the owned run root");
   string sourceMarker=Path.Combine(source,SourceMarker);
   AssertNoReparsePoint(sourceMarker,"SourceProject marker");
   Assert.IsTrue(File.Exists(sourceMarker),"Owned Stage3 SourceProject marker missing");
   Assert.AreEqual(SourceMarkerValue,File.ReadAllText(sourceMarker).Trim(),"Owned Stage3 SourceProject marker value");
   string targetMarker=Path.Combine(target,TargetMarker);
   AssertNoReparsePoint(targetMarker,"TargetProject marker");
   Assert.IsTrue(File.Exists(targetMarker),"Disposable TargetProject marker missing");
   return root;
  }
 }
 static void AssertNoReparsePoint(string path,string label){
  string full=Path.GetFullPath(path);
  var chain=new Stack<string>();
  for(string p=full;!string.IsNullOrEmpty(p);p=Path.GetDirectoryName(p))chain.Push(p);
  while(chain.Count>0){
   string part=chain.Pop();
   Assert.IsFalse((File.GetAttributes(part)&FileAttributes.ReparsePoint)!=0,
    label+" path contains a symlink/junction/reparse point: "+part);
  }
 }
 static string TargetRoot=>Path.Combine(TestRoot,"TargetProject");
 static string SourceRoot=>Path.Combine(TestRoot,"SourceProject","Assets","SyntheticMaterialFixture","R2Stage3");

 const string Owned="Assets/VAPBStage3Owned", Manifest="Assets/VAPBExport/manifest.json";
 static string D(string p)=>Path.GetFullPath(Path.IsPathRooted(p)?p:Path.Combine(TargetRoot,p.Replace('/',Path.DirectorySeparatorChar)));
 static string Hash(string p){using(var h=SHA256.Create())using(var f=File.OpenRead(D(p)))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
 static Type Fin=>AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbFinalStateFinalizer",false)).First(t=>t!=null);
 static bool EntryExists(string p)=>File.Exists(D(p))||Directory.Exists(D(p))||File.Exists(D(p+".meta"))||
  Directory.Exists(D(p+".meta"))||AssetDatabase.LoadMainAssetAtPath(p)!=null||AssetDatabase.IsValidFolder(p);
 static string Id(char identity){
  switch(identity){
   case 'A':return "VAPB-MAT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
   case 'B':return "VAPB-MAT-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
   case 'C':return "VAPB-MAT-cccccccccccccccccccccccccccccccc";
   default:throw new ArgumentException("unknown fixture identity");
  }
 }
 static char Identity(string id){foreach(char c in new[]{'A','B','C'})if(id==Id(c))return c;return '?';}
 [Serializable] class M{public string schema_version="vapb-export-manifest-1";public T[] reference_rebind_tasks;}
 [Serializable] class T{public string kind="BUILD_EXPORTED_STATIC_V2";public int material_transport_version=2;public string export_object_id,model_guid,model_sha256,prefab_path;public R[] materials;public S[] material_slots;}
 [Serializable] class R{public string export_material_id,guid,file_id,asset_sha256;public Sh shader;public Tx[] textures=new Tx[0];}
 [Serializable] class Sh{public string classification="UNITY_BUILTIN",guid,file_id;}
 [Serializable] class Tx{public string property_name,guid,file_id;}
 [Serializable] class S{public string slot_index,export_material_id;}

 [TestCase("ABC","Stage3_ABC.fbx","VAPB-OBJ-11111111111111111111111111111111","ABC")]
 [TestCase("ABA","Stage3_ABA.fbx","VAPB-OBJ-22222222222222222222222222222222","ABA")]
 public void ImportAndApply(string key,string file,string objectId,string faceOrder)
 {
  string sourceHash=FixtureHash(key,file,objectId);
  string prefab="Assets/VAPBExport/Generated_"+objectId.Substring(9)+".prefab";
  Assert.AreEqual("2022.3.22f1",Application.unityVersion);
  AssertNoReparsePoint(SourceRoot,"source fixture path");
  AssertNoReparsePoint(D("Assets"),"target Assets path");
  Assert.That(D(Path.Combine(TargetRoot,"Assets")).TrimEnd((char)92),
   Is.EqualTo(D(Application.dataPath).TrimEnd((char)92)).IgnoreCase,"wrong target project");
  Assert.IsTrue(File.Exists(D(Path.Combine(TargetRoot,".vapb-disposable-unity-test-project"))),"disposable project marker missing");
  Assert.IsFalse(EntryExists(Owned),"owned folder/path/meta already exists");
  bool exportFolderExisted=Directory.Exists(D("Assets/VAPBExport"));
  if(exportFolderExisted)AssertNoReparsePoint(D("Assets/VAPBExport"),"existing export folder");
  Assert.IsTrue(!exportFolderExisted||AssetDatabase.IsValidFolder("Assets/VAPBExport"),"export path is not a Unity folder");
  if(!exportFolderExisted)Assert.IsFalse(EntryExists("Assets/VAPBExport"),"orphan export folder entry");
  Assert.IsFalse(EntryExists(Manifest),"fixed manifest payload/meta/asset occupied");
  Assert.IsFalse(EntryExists(prefab),"expected prefab payload/meta/directory/asset occupied");
  var before=Inventory();var made=new List<string>();
  try{
   Directory.CreateDirectory(D(Owned));made.Add(Owned);AssetDatabase.Refresh();
   string model=Owned+"/"+file;File.Copy(Path.Combine(SourceRoot,file),D(model));made.Add(model);
   Assert.AreEqual(sourceHash,Hash(Path.Combine(SourceRoot,file)),"source FBX hash");
   Assert.AreEqual(sourceHash,Hash(model),"copied FBX hash");
   AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   string modelGuid=AssetDatabase.AssetPathToGUID(model);
   var saved=new Dictionary<char,Material>();var records=new List<R>();
   Shader shader=Shader.Find("Standard");Assert.NotNull(shader);Assert.IsTrue(shader.isSupported);Assert.IsFalse(ShaderUtil.ShaderHasError(shader));
   Assert.IsTrue(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(shader,out string shaderGuid,out long shaderId));
   foreach(char c in faceOrder.Distinct()){
    string p=Owned+"/"+key+"_Preserved_"+c+".mat";Assert.IsFalse(EntryExists(p),"material path occupied: "+p);
    var mat=new Material(shader){name=key+"_Preserved_"+c};AssetDatabase.CreateAsset(mat,p);made.Add(p);saved.Add(c,mat);
   }
   AssetDatabase.SaveAssets();
   foreach(char c in faceOrder.Distinct()){
    Material mat=saved[c];string p=AssetDatabase.GetAssetPath(mat);
    Assert.IsTrue(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mat,out string g,out long id));
    records.Add(new R{export_material_id=Id(c),guid=g,file_id=id.ToString(),asset_sha256=Hash(p),
     shader=new Sh{guid=shaderGuid,file_id=shaderId.ToString()}});
   }
   var task=new T{export_object_id=objectId,model_guid=modelGuid,model_sha256=Hash(model),prefab_path=prefab,
    materials=records.ToArray(),material_slots=faceOrder.Select((c,i)=>new S{slot_index=i.ToString(),export_material_id=Id(c)}).ToArray()};
   if(!exportFolderExisted){Directory.CreateDirectory(D("Assets/VAPBExport"));made.Add("Assets/VAPBExport");}
   var stream=new FileStream(D(Manifest),FileMode.CreateNew,FileAccess.Write);made.Add(Manifest);
   using(stream)using(var writer=new StreamWriter(stream,new UTF8Encoding(false)))
    writer.Write(JsonUtility.ToJson(new M{reference_rebind_tasks=new[]{task}},true));
   AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   var importer=(ModelImporter)AssetImporter.GetAtPath(model);Assert.NotNull(importer);Assert.AreEqual(1f,importer.globalScale,0.00001f);
   importer.materialName=ModelImporterMaterialName.BasedOnMaterialName;importer.SaveAndReimport();
   Type marker=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbExportObjectMarker",false)).First(x=>x!=null);
   FieldInfo markerId=marker.GetField("exportObjectId",BindingFlags.Instance|BindingFlags.Public);Assert.NotNull(markerId);
   var native=ReadModel(model,marker,markerId,objectId);
   Assert.AreEqual(0,importer.GetExternalObjectMap().Count,"unexpected explicit external material remap");
   bool nativeFaces=FaceMap(native.transform,native.mesh,native.identities,native.labels,faceOrder);
  if(key=="ABC"){
   char[] swapped=(char[])native.identities.Clone();char first=swapped[0];swapped[0]=swapped[1];swapped[1]=first;
   bool negativeControl=FaceMap(native.transform,native.mesh,swapped,native.labels,faceOrder);
   TestContext.WriteLine("negative control A/B identity swap detected="+(!negativeControl));
   Assert.IsFalse(negativeControl,"FaceMap must reject a deliberately swapped A/B material identity assignment");
  }
   TestContext.WriteLine(key+" labels="+string.Join(",",native.labels)+" submeshes="+native.mesh.subMeshCount+
    " importer="+importer.materialImportMode+"/"+importer.materialLocation+"/"+importer.materialSearch+
    " scale="+importer.globalScale+" transform="+native.transform.localToWorldMatrix+" localScale="+native.transform.localScale+" position="+native.transform.position+" meshGuidFileId="+native.meshId+" meshHash="+native.meshHash);
  TestContext.WriteLine("Importer useFileScale="+importer.useFileScale+" fileScale="+importer.fileScale+" bakeAxisConversion="+importer.bakeAxisConversion+" useFileUnits="+importer.useFileUnits+" mesh vertices="+string.Join(";",native.mesh.vertices.Select(v=>v.ToString())));
   object read=Fin.GetMethod("ReadTask",BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{Manifest});
   MethodInfo resolver=Fin.GetMethod("ResolveNativeMaterialOrder",BindingFlags.NonPublic|BindingFlags.Static);
   int[] nativeToMaterial=null;Exception guard=null;
   try{nativeToMaterial=(int[])resolver.Invoke(null,new object[]{read,native.labels,native.mesh.subMeshCount});}
   catch(TargetInvocationException e){guard=e.InnerException;}
   TestContext.WriteLine(key+" nativeGuard="+(guard==null?"ACCEPT":guard.Message)+" faceMap="+nativeFaces);
   var protectedPaths=new List<string>{model,model+".meta",Manifest,Manifest+".meta"};
   foreach(char c in faceOrder.Distinct()){string p=AssetDatabase.GetAssetPath(saved[c]);protectedPaths.Add(p);protectedPaths.Add(p+".meta");}
   foreach(string p in protectedPaths)Assert.IsTrue(File.Exists(D(p)),"missing hash input "+p);
   var hashes=protectedPaths.ToDictionary(p=>p,p=>Hash(p),StringComparer.Ordinal);
   string modelMetaBefore=hashes[model+".meta"],modelMetaFirst=null;
   if(guard==null){
    Assert.IsTrue(nativeFaces,key+" native face identity");
    Assert.AreEqual(native.labels.Length,nativeToMaterial.Length);
    char[] declared=faceOrder.Distinct().ToArray();char[] nativeOrder=native.labels.Select(Identity).ToArray();
    Assert.IsTrue(nativeOrder.All(c=>c!='?'),"unknown carrier label");
    for(int i=0;i<nativeOrder.Length;i++)Assert.AreEqual(Array.IndexOf(declared,nativeOrder[i]),nativeToMaterial[i]);
    made.Add(prefab);
    Assert.IsTrue((bool)Fin.GetMethod("Apply").Invoke(null,new object[]{Manifest}),Fin.GetProperty("LastResult").GetValue(null).ToString());
    Assert.AreEqual("COMPLETE",Fin.GetProperty("LastResult").GetValue(null));
    var afterFirst=ReadModel(model,marker,markerId,objectId);
    AssertModelAfterApply(native,afterFirst,faceOrder,"first Apply");
    AssertPrefab(prefab,marker,markerId,objectId,saved,nativeOrder,native.meshHash,native.meshId,faceOrder);
    // The fixture already persisted BasedOnMaterialName before this baseline. Apply reasserts the same setting,
    // so no FBX payload or importer metadata change is expected on first or repeated Apply.
    AssertStable(hashes,null);modelMetaFirst=Hash(model+".meta");LogHashes("after-first",hashes);
    string prefabHash=Hash(prefab),prefabMetaHash=Hash(prefab+".meta"),prefabGuid=AssetDatabase.AssetPathToGUID(prefab);
    Assert.IsTrue((bool)Fin.GetMethod("Apply").Invoke(null,new object[]{Manifest}));
    var afterRepeat=ReadModel(model,marker,markerId,objectId);
    AssertModelAfterApply(native,afterRepeat,faceOrder,"repeat Apply");
    AssertPrefab(prefab,marker,markerId,objectId,saved,nativeOrder,native.meshHash,native.meshId,faceOrder);
    AssertStable(hashes,null);
    Assert.AreEqual(modelMetaFirst,Hash(model+".meta"),"repeat Apply must preserve FBX importer metadata from after first Apply");
    Assert.AreEqual(prefabGuid,AssetDatabase.AssetPathToGUID(prefab));Assert.AreEqual(prefabHash,Hash(prefab));Assert.AreEqual(prefabMetaHash,Hash(prefab+".meta"));
    LogHashes("after-repeat",hashes);
    TestContext.WriteLine("FBX.meta before="+modelMetaBefore+" afterFirst="+modelMetaFirst+" afterRepeat="+Hash(model+".meta")+
     " prefab="+prefabHash+" prefab.meta="+prefabMetaHash+" prefab.guid="+prefabGuid);
   }else{
    Assert.AreEqual("ABA",key,"ABC must pass native mapping");
    Assert.IsTrue(guard.Message.StartsWith("NATIVE_MATERIAL_"),"only ABA native guard refusal is expected");
    LogAssert.Expect(LogType.Error,"VAPB_FINAL_STATE_REJECTED="+guard.Message);
    Assert.IsFalse((bool)Fin.GetMethod("Apply").Invoke(null,new object[]{Manifest}));
    Assert.AreEqual("REJECTED",Fin.GetProperty("LastResult").GetValue(null));
    Assert.IsNull(AssetDatabase.LoadAssetAtPath<GameObject>(prefab));
    var afterReject=ReadModel(model,marker,markerId,objectId);
    Assert.AreEqual(native.meshHash,afterReject.meshHash);CollectionAssert.AreEqual(native.labels,afterReject.labels);
    AssertStable(hashes,null);LogHashes("after-aba-reject",hashes);
    TestContext.WriteLine("ABA rejected Apply FBX.meta beforeApply="+modelMetaBefore+" afterReject="+Hash(model+".meta")+" (all protected files unchanged)");
   }
   Assert.AreEqual(sourceHash,Hash(Path.Combine(SourceRoot,file)),"source FBX changed during Apply");
  }finally{
   var errors=Cleanup(made);
   AssetDatabase.Refresh();
   if(!before.SequenceEqual(Inventory()))errors.Add("pre-existing Assets inventory or hash changed");
   if(errors.Count>0)Assert.Fail("cleanup/non-destructive verification: "+string.Join(" | ",errors));
  }
 }

 static string FixtureHash(string key,string file,string objectId){
  string evidence=Path.Combine(TestRoot,"SourceProject","stage3-fbx-fixture-evidence.json");
  AssertNoReparsePoint(evidence,"fixture evidence file");
  Assert.IsTrue(File.Exists(evidence),"fixture evidence JSON missing");
  var root=JsonUtility.FromJson<FixtureEvidence>(File.ReadAllText(evidence));
  Assert.NotNull(root);Assert.AreEqual("Public synthetic Stage 3 native-FBX material-order fixture preparation",root.purpose);
  Assert.AreEqual("2022.3.22f1",Application.unityVersion);
  var row=FindFixtureCase(root,key);
  Assert.AreEqual(objectId,row.fbx.export_id,"fixture evidence Export ID");
  Assert.AreEqual(file,Path.GetFileName(row.fbx.path),"fixture evidence FBX filename");
  string sourceFbx=Path.GetFullPath(Path.Combine(SourceRoot,file));
  AssertNoReparsePoint(sourceFbx,"source FBX file");
  Assert.IsTrue(string.Equals(sourceFbx,Path.GetFullPath(row.fbx.path),StringComparison.OrdinalIgnoreCase),"fixture evidence FBX path");
  Assert.IsTrue(File.Exists(sourceFbx),"source FBX fixture missing");
  return row.fbx.sha256;
 }
 static FixtureEvidenceCase FindFixtureCase(FixtureEvidence root,string key){
  if(root==null||root.cases==null)throw new InvalidDataException("fixture evidence cases are missing");
  if(root.cases.Any(c=>c==null))throw new InvalidDataException("fixture evidence contains a null case");
  if(root.cases.Any(c=>string.IsNullOrWhiteSpace(c.@case)||c.fbx==null))throw new InvalidDataException("fixture evidence case is malformed");
  if(root.cases.Any(c=>string.IsNullOrWhiteSpace(c.fbx.path)||string.IsNullOrWhiteSpace(c.fbx.export_id)||
   c.fbx.sha256==null||c.fbx.sha256.Length!=64||!c.fbx.sha256.All(Uri.IsHexDigit)))
   throw new InvalidDataException("fixture evidence FBX record is malformed");
  var matches=root.cases.Where(c=>c.@case==key).ToArray();
  if(matches.Length!=1)throw new InvalidDataException("fixture evidence case must be unique: "+key);
  return matches[0];
 }
 [Serializable] sealed class FixtureEvidence{public string purpose;public FixtureEvidenceCase[] cases;}
 [Serializable] sealed class FixtureEvidenceCase{public string @case;public FixtureEvidenceFbx fbx;}
 [Serializable] sealed class FixtureEvidenceFbx{public string path,export_id,sha256;}

 static FixtureEvidenceCase ValidFixtureCase(string key){
  return new FixtureEvidenceCase{@case=key,fbx=new FixtureEvidenceFbx{path="fixture.fbx",export_id="VAPB-OBJ-11111111111111111111111111111111",sha256=new string('a',64)}};
 }
 [Test] public void FixtureEvidenceRejectsNullCaseOrFbx(){
  Assert.Throws<InvalidDataException>(()=>FindFixtureCase(new FixtureEvidence{cases=null},"ABC"));
  Assert.Throws<InvalidDataException>(()=>FindFixtureCase(new FixtureEvidence{cases=new FixtureEvidenceCase[]{null}},"ABC"));
  var row=ValidFixtureCase("ABC");row.fbx=null;
  Assert.Throws<InvalidDataException>(()=>FindFixtureCase(new FixtureEvidence{cases=new[]{row}},"ABC"));
 }
 [Test] public void FixtureEvidenceRejectsMalformedHash(){
  var row=ValidFixtureCase("ABC");row.fbx.sha256="not-a-sha256";
  Assert.Throws<InvalidDataException>(()=>FindFixtureCase(new FixtureEvidence{cases=new[]{row}},"ABC"));
 }
 [Test] public void FixtureEvidenceRejectsDuplicateCase(){
  Assert.Throws<InvalidDataException>(()=>FindFixtureCase(new FixtureEvidence{cases=new[]{ValidFixtureCase("ABC"),ValidFixtureCase("ABC")}},"ABC"));
 }

 sealed class ModelState{public Transform transform;public Mesh mesh;public string[] labels;public char[] identities;public string meshHash,meshId;}
 static ModelState ReadModel(string path,Type marker,FieldInfo markerId,string exportId){
  var root=AssetDatabase.LoadAssetAtPath<GameObject>(path);Assert.NotNull(root);
  var all=root.GetComponentsInChildren(marker,true);Assert.AreEqual(1,all.Length,"authorized marker must be unique");
  Assert.AreEqual(exportId,markerId.GetValue(all[0]));var c=(Component)all[0];
  var renderer=c.GetComponent<MeshRenderer>();var filter=c.GetComponent<MeshFilter>();
  Assert.NotNull(renderer);Assert.NotNull(filter);Assert.NotNull(filter.sharedMesh);
  string[] labels=renderer.sharedMaterials.Select(m=>m==null?"<null>":m.name).ToArray();
  return new ModelState{transform=c.transform,mesh=filter.sharedMesh,labels=labels,identities=labels.Select(Identity).ToArray(),
   meshHash=MeshHash(filter.sharedMesh),meshId=MeshId(filter.sharedMesh)};
 }
 static string MeshId(Mesh m){
  Assert.IsTrue(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(m,out string g,out long id),"mesh must be a persistent FBX subasset");
  return g+":"+id;
 }
 static void AssertModelAfterApply(ModelState initial,ModelState actual,string faceOrder,string phase){
  Assert.AreEqual(initial.meshHash,actual.meshHash,phase+" native mesh content");Assert.AreEqual(initial.meshId,actual.meshId,phase+" native mesh GUID/localFileID");
  CollectionAssert.AreEqual(initial.labels,actual.labels,phase+" native labels");
  Assert.IsTrue(FaceMap(actual.transform,actual.mesh,actual.identities,actual.labels,faceOrder),phase+" native face map");
 }
 static void AssertPrefab(string path,Type marker,FieldInfo markerId,string exportId,
  Dictionary<char,Material> saved,char[] nativeOrder,string modelMeshHash,string modelMeshId,string faceOrder){
  var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);Assert.NotNull(prefab);
  var all=prefab.GetComponentsInChildren(marker,true);Assert.AreEqual(1,all.Length);
  Assert.AreEqual(exportId,markerId.GetValue(all[0]));var c=(Component)all[0];
  var renderer=c.GetComponent<MeshRenderer>();var filter=c.GetComponent<MeshFilter>();
  Assert.NotNull(renderer);Assert.NotNull(filter);Assert.NotNull(filter.sharedMesh);
  Assert.AreEqual(modelMeshHash,MeshHash(filter.sharedMesh),"prefab mesh content");
  Assert.AreEqual(modelMeshId,MeshId(filter.sharedMesh),"prefab mesh GUID/localFileID");
  var slots=renderer.sharedMaterials;Assert.AreEqual(nativeOrder.Length,slots.Length);
  char[] actual=slots.Select(m=>saved.First(kv=>kv.Value==m).Key).ToArray();
  CollectionAssert.AreEqual(nativeOrder,actual,"prefab slot order must follow observed native labels");
  Assert.IsTrue(FaceMap(c.transform,filter.sharedMesh,actual,slots.Select(m=>m.name).ToArray(),faceOrder),"prefab effective face/material map");
 }
 // Unity 2022.3.22f1, for this fixture/import setup, measured FBX vertices and
 // Model transform give (x,y,0)->(-x,0,-y). fileScale=0.01 and root scale=100 cancel.
 static bool FaceMap(Transform tr,Mesh mesh,char[] identityBySlot,string[] labels,string faceOrder){
  if(identityBySlot.Length!=mesh.subMeshCount||labels.Length!=mesh.subMeshCount)return false;
  Vector3[] expected={new Vector3(-1f/3f,0,-1f/3f),new Vector3(-7f/3f,0,-1f/3f),new Vector3(-13f/3f,0,-1f/3f)};
  int[] seen=new int[3];int faceCount=0;bool ok=true;Vector3[] vertices=mesh.vertices;
  for(int s=0;s<mesh.subMeshCount;s++){
   int[] tris=mesh.GetTriangles(s);
   for(int j=0;j+2<tris.Length;j+=3){
    Vector3 center=tr.TransformPoint((vertices[tris[j]]+vertices[tris[j+1]]+vertices[tris[j+2]])/3f);faceCount++;
    int[] nearest=Enumerable.Range(0,3).OrderBy(k=>(center-expected[k]).sqrMagnitude).Take(2).ToArray();
    float d0=Vector3.Distance(center,expected[nearest[0]]),d1=Vector3.Distance(center,expected[nearest[1]]);
    char face=faceOrder[nearest[0]];
    TestContext.WriteLine("sub="+s+" face="+face+" worldCentroid="+center+" material="+labels[s]);
    if(d0>0.0001f||d1-d0<1f||identityBySlot[s]!=face)ok=false;
    seen[nearest[0]]++;
   }
  }
  if(faceCount!=3||seen.Any(n=>n!=1))ok=false;
  TestContext.WriteLine("face counts="+string.Join(",",seen)+" total="+faceCount);
  return ok;
 }
 static string MeshHash(Mesh mesh){
  var b=new StringBuilder().Append(mesh.subMeshCount).Append('|');
  foreach(Vector3 v in mesh.vertices)b.Append(BitConverter.ToString(BitConverter.GetBytes(v.x))).Append(BitConverter.ToString(BitConverter.GetBytes(v.y))).Append(BitConverter.ToString(BitConverter.GetBytes(v.z)));
  for(int s=0;s<mesh.subMeshCount;s++)b.Append('|').Append(string.Join(",",mesh.GetTriangles(s)));
  using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(b.ToString()))).Replace("-","").ToLowerInvariant();
 }
 static void AssertStable(Dictionary<string,string> before,string allowedMeta){
  foreach(var p in before)if(p.Key!=allowedMeta)Assert.AreEqual(p.Value,Hash(p.Key),"protected file changed: "+p.Key);
 }
 static void LogHashes(string label,Dictionary<string,string> paths){
  foreach(string p in paths.Keys)TestContext.WriteLine(label+" "+p+" sha256="+Hash(p));
 }
 static string[] Inventory(){
  string root=D("Assets");
  return Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal)
   .Select(p=>p.Substring(D("Assets").Length+1).Replace('\\','/')+" "+Hash(p)).ToArray();
 }
 static List<string> Cleanup(List<string> made){
  var errors=new List<string>();
  foreach(string p in made.AsEnumerable().Reverse()){
   try{
    bool ownedFolder=p==Owned||p=="Assets/VAPBExport"&&made.Contains(p);
    if(ownedFolder&&Directory.Exists(D(p))&&Directory.GetFileSystemEntries(D(p)).Length!=0){
     errors.Add("refusing to remove nonempty owned folder: "+p);continue;
    }
    bool removed=AssetDatabase.DeleteAsset(p);
    if(!removed){
     string disk=D(p);
     if(ownedFolder&&Directory.Exists(disk))Directory.Delete(disk,false);
     else if(p.StartsWith(Owned+"/",StringComparison.Ordinal)||p==Manifest||p.StartsWith("Assets/VAPBExport/Generated_",StringComparison.Ordinal)){
      if(File.Exists(disk))File.Delete(disk);
      if(File.Exists(disk+".meta"))File.Delete(disk+".meta");
     }
     if(ownedFolder&&File.Exists(disk+".meta"))File.Delete(disk+".meta");
    }
    if(Directory.Exists(D(p))||File.Exists(D(p))||File.Exists(D(p+".meta"))||Directory.Exists(D(p+".meta")))errors.Add("owned path remains: "+p);
   }catch(Exception e){errors.Add(p+": "+e.GetType().Name+" "+e.Message);}
  }
  return errors;
 }
 [TestCase("canonical-string", "\"0\"")]
 [TestCase("raw-numeric", "0")]
 [TestCase("duplicate-raw-key", "\"0\",\"slot_index\":\"1\"")]
 public void CharacterizesRawJsonUtilitySlotIndexAndFinalizerGuard(string label,string rawValue){
  string json="{\"slot_index\":"+rawValue+",\"export_material_id\":\""+Id('A')+"\"}";
  S value;
  try{
   value=JsonUtility.FromJson<S>(json);
   TestContext.WriteLine("raw JsonUtility " + label + " => " +
    (value==null?"<null DTO>":value.slot_index==null?"<null field>":"<"+value.slot_index+">"));
  }catch(Exception e){
   TestContext.WriteLine("raw JsonUtility " + label + " throws " + e.GetType().FullName + ": " + e.Message);
   if(label=="canonical-string")throw;
   return;
  }
  if(label=="canonical-string")Assert.AreEqual("0",value.slot_index);
  string taskJson="{\"kind\":\"BUILD_EXPORTED_STATIC_V2\",\"material_transport_version\":2,"+
   "\"export_object_id\":\"VAPB-OBJ-"+new string('d',32)+"\",\"model_guid\":\""+
   new string('e',32)+"\",\"model_sha256\":\""+new string('f',64)+"\",\"prefab_path\":\"Assets/VAPBExport/Generated_"+
   new string('d',32)+".prefab\",\"materials\":[{\"export_material_id\":\""+Id('A')+
   "\",\"guid\":\""+new string('a',32)+"\",\"file_id\":\"4800000\",\"asset_sha256\":\""+
   new string('b',64)+"\",\"shader\":{\"classification\":\"UNITY_BUILTIN\"},\"textures\":[]}],\"material_slots\":["+json+"]}";
  Type taskType=Fin.GetNestedType("Task",BindingFlags.NonPublic);
  object task;
  try{
   task=JsonUtility.FromJson(taskJson,taskType);
  }catch(Exception e){
   TestContext.WriteLine("raw Finalizer Task JsonUtility " + label + " => NOT_RUN_PARSE_FAILED " + e.GetType().FullName + ": " + e.Message);
   if(label=="canonical-string")throw;
   return;
  }
  Array taskSlots=(Array)taskType.GetField("material_slots",BindingFlags.Public|BindingFlags.Instance).GetValue(task);
  object taskSlot=taskSlots==null||taskSlots.Length==0?null:taskSlots.GetValue(0);
  string taskSlotIndex=taskSlot==null?null:(string)taskSlot.GetType().GetField("slot_index",BindingFlags.Public|BindingFlags.Instance).GetValue(taskSlot);
  TestContext.WriteLine("raw Finalizer Task slot_index " + label + " => " +
   (taskSlotIndex==null?"<null>":"<"+taskSlotIndex+">"));
  if(label=="canonical-string")Assert.AreEqual("0",taskSlotIndex);
  string guard;
  try{
   Fin.GetMethod("ValidateV2Task",BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new[]{task});
   guard="ACCEPT";
  }catch(TargetInvocationException e){
   if(e.InnerException is InvalidOperationException)guard="REJECT "+e.InnerException.Message;
   else guard="THROWS "+(e.InnerException==null?e.GetType().Name:e.InnerException.GetType().FullName+": "+e.InnerException.Message);
  }catch(Exception e){
   guard="THROWS "+e.GetType().FullName+": "+e.Message;
  }
  TestContext.WriteLine("raw finalizer guard " + label + " => " + guard);
  if(label=="canonical-string"){
   Assert.AreEqual("ACCEPT",guard,"canonical raw string must pass Finalizer validation");
  }
 }
}
