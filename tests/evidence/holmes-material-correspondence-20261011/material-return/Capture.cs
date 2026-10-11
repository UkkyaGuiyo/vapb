using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Bounded OrderedSix return capture. Existing package Finalizer only; no Scene edits.
[InitializeOnLoad] public static class HolmesMaterialReturn
{
    const string Key="HOLMES04_IMPORTED", Started="HOLMES04_STARTED", WorkKey="HOLMES04_WORK";
    const string ManifestPath="Assets/VAPBExport/manifest.json";
    [Serializable] class Ref { public string guid,file_id; }
    [Serializable] class Task { public string kind,prefab_guid,renderer_file_id,model_guid,model_sha256,prefab_source_sha256,realization_id; public Ref[] materials; }
    [Serializable] class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] class Group { public string topology; public int index_count,base_vertex; public int[] indices; }
    [Serializable] class Snapshot {
        public string instruction_id="HOLMES-20261011-04",status="FAIL",error,unity_version,package_sha256,manifest_sha256,policy;
        public string fbx_sha256,fbx_sha256_after,meta_sha256,meta_sha256_after,prefab_sha256_before,prefab_sha256_after;
        public bool import_completed,explicit_apply,apply_returned_true,apply_base_vertex,materials_exact,material_bytes_preserved;
        public Ref mesh,renderer; public Ref[] materials; public Group[] groups; public Vector2[] uv; public Vector3[] vertices;
        public int matching_realization_markers;
    }
    static string Work=>SessionState.GetString(WorkKey,"");
    static string Hash(string path) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static Ref Reference(UnityEngine.Object obj) {
        if(obj==null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj,out string g,out long id))throw new Exception("IdentityUnavailable");
        return new Ref{guid=g,file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture)};
    }
    static HolmesMaterialReturn() {
        EditorApplication.update+=Wait;
        AssetDatabase.importPackageCompleted+=name=>{if(SessionState.GetBool(Started,false))SessionState.SetBool(Key,true);};
        AssetDatabase.importPackageFailed+=(name,error)=>{if(SessionState.GetBool(Started,false)){Finish(new Snapshot{error="ImportPackageFailed",unity_version=Application.unityVersion});}};
    }
    public static void Run() {
        var args=Environment.GetCommandLineArgs();string work=args[Array.IndexOf(args,"-orderedWork")+1];
        if(File.Exists(Path.Combine(work,"native.json")))throw new Exception("ExistingCapture");
        SessionState.SetString(WorkKey,work);SessionState.SetBool(Key,false);SessionState.SetBool(Started,true);
        AssetDatabase.ImportPackage(Path.Combine(Directory.GetParent(work).FullName,"EditedMaterialOutput.unitypackage"),false);
    }
    static void Wait() {
        if(!SessionState.GetBool(Started,false)||!SessionState.GetBool(Key,false)||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
        SessionState.SetBool(Started,false);EditorApplication.update-=Wait;
        var r=new Snapshot{unity_version=Application.unityVersion,import_completed=true};
        try {
            r.package_sha256=Hash(Path.Combine(Directory.GetParent(Work).FullName,"EditedMaterialOutput.unitypackage"));
            if(r.package_sha256!="0ccf9cd8d4f507a8589c02631d8865ddc456bd8e2627394ae9a8549843118dc9")throw new Exception("PackageRevision");
            r.manifest_sha256=Hash(ManifestPath);
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            if(m.reference_rebind_tasks.Length!=1)throw new Exception("TaskCount");var t=m.reference_rebind_tasks.Single();
            if(t.kind!="REBIND_DIRECT_RENDERER_V1")throw new Exception("TaskKind");
            string model=AssetDatabase.GUIDToAssetPath(t.model_guid),prefab=AssetDatabase.GUIDToAssetPath(t.prefab_guid);
            r.fbx_sha256=Hash(model);r.meta_sha256=Hash(model+".meta");r.prefab_sha256_before=Hash(prefab);
            if(r.fbx_sha256!=t.model_sha256||r.prefab_sha256_before!=t.prefab_source_sha256)throw new Exception("ImportedRevision");
            var materialPaths=t.materials.Select(x=>AssetDatabase.GUIDToAssetPath(x.guid)).ToArray();
            var materialHashes=materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}).ToArray();
            var type=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbReferenceFinalizer",false)).Single(x=>x!=null);
            r.explicit_apply=true;r.apply_returned_true=(bool)type.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
            if(!r.apply_returned_true)throw new Exception("FinalizerRejected");
            var owner=AssetDatabase.LoadAssetAtPath<GameObject>(prefab);
            var renderer=owner.GetComponentsInChildren<MeshRenderer>(true).Single(x=>Reference(x).file_id==t.renderer_file_id);
            var mesh=renderer.GetComponent<MeshFilter>().sharedMesh;r.mesh=Reference(mesh);r.renderer=Reference(renderer);
            if(r.mesh.guid!=t.model_guid)throw new Exception("MeshIdentity");
            r.materials=renderer.sharedMaterials.Select(Reference).ToArray();
            r.materials_exact=r.materials.Length==t.materials.Length && r.materials.Select((x,i)=>x.guid==t.materials[i].guid&&x.file_id==t.materials[i].file_id).All(x=>x);
            r.material_bytes_preserved=materialHashes.SequenceEqual(materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}));
            var modelRoot=AssetDatabase.LoadAssetAtPath<GameObject>(model);
            r.matching_realization_markers=modelRoot.GetComponentsInChildren<MonoBehaviour>(true).Count(x=>x!=null&&x.GetType().Name=="VapbRealizationMarker"&&(string)x.GetType().GetField("realizationId").GetValue(x)==t.realization_id);
            r.policy=EditorJsonUtility.ToJson(AssetImporter.GetAtPath(model));r.uv=mesh.uv;r.vertices=mesh.vertices;r.apply_base_vertex=true;
            r.groups=Enumerable.Range(0,mesh.subMeshCount).Select(sub=>{int b=(int)mesh.GetBaseVertex(sub);var indices=mesh.GetIndices(sub,true);
                if(!indices.SequenceEqual(mesh.GetIndices(sub,false).Select(i=>i+b)))throw new Exception("BaseVertexMismatch");
                return new Group{topology=mesh.GetTopology(sub).ToString(),indices=indices,index_count=(int)mesh.GetIndexCount(sub),base_vertex=b};}).ToArray();
            r.fbx_sha256_after=Hash(model);r.meta_sha256_after=Hash(model+".meta");r.prefab_sha256_after=Hash(prefab);
            if(!r.materials_exact||!r.material_bytes_preserved||r.matching_realization_markers!=1||r.fbx_sha256!=r.fbx_sha256_after||r.meta_sha256!=r.meta_sha256_after||Hash(ManifestPath)!=r.manifest_sha256)throw new Exception("ReturnEvidenceMismatch");
            r.status="PASS";
        } catch(Exception error){r.error=error.GetType().Name+": "+error.Message;}
        Finish(r);
    }
    static void Finish(Snapshot r) {
        SessionState.SetBool(Started,false);
        using(var s=new FileStream(Path.Combine(Work,"native.json"),FileMode.CreateNew))using(var w=new StreamWriter(s))w.Write(JsonUtility.ToJson(r,true));
        EditorApplication.Exit(r.status=="PASS"?0:1);
    }
}
