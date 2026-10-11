using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Reflection;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

// Reuses HOLMES-04 capture; adds first-install lifecycle and repeat/reopen observation.
[InitializeOnLoad] public static class HolmesFreshConsumer
{
    const string Key="HOLMES05_IMPORTED", Started="HOLMES05_STARTED", WorkKey="HOLMES05_WORK";
    const string ManifestPath="Assets/VAPBExport/manifest.json";
    [Serializable] class Ref { public string guid,file_id; }
    [Serializable] class Task { public string kind,prefab_guid,renderer_file_id,model_guid,model_sha256,prefab_source_sha256,realization_id; public Ref[] materials; }
    [Serializable] class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] class Initial {public string[] asset_paths,vapb_named_assemblies;public bool finalizer_available,model_finalizer_available,assistant_available;}
    [Serializable] class Group { public string topology; public int index_count,base_vertex; public int[] indices; }
    [Serializable] class Snapshot {
        public string instruction_id="HOLMES-20261011-05",status="FAIL",error,unity_version,package_sha256,manifest_sha256,policy;
        public string fbx_sha256,fbx_sha256_after,meta_sha256,meta_sha256_after,prefab_sha256_before,prefab_sha256_after;
        public bool import_completed,explicit_apply,apply_returned_true,apply_base_vertex,materials_exact,material_bytes_preserved;
        public Ref mesh,renderer; public Ref[] materials; public Group[] groups; public Vector2[] uv; public Vector3[] vertices;
        public Ref prefab,manifest,finalizer_script;
        public string finalizer_source_sha256,finalizer_assembly;
        public int matching_realization_markers;
        public string phase,prefab_repeat_before,prefab_repeat_after;
        public bool repeat_apply_returned_true,repeat_materials_unchanged,repeat_mesh_unchanged;
    }
    static string Work=>SessionState.GetString(WorkKey,"");
    static string Argument(string name) {var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,name);return i>=0&&i+1<args.Length?args[i+1]:"";}
    static string Phase=>Argument("-freshPhase");
    static Type Finalizer=>AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbReferenceFinalizer",false)).SingleOrDefault(x=>x!=null);
    static void Event(string stage,string detail="") {
        string folder=Argument("-freshWork");if(string.IsNullOrEmpty(folder))return;
        File.AppendAllText(Path.Combine(folder,"events.tsv"),DateTime.UtcNow.ToString("o")+"\t"+stage+"\t"+detail+"\n");
    }
    static string Hash(string path) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static Ref Reference(UnityEngine.Object obj) {
        if(obj==null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj,out string g,out long id))throw new Exception("IdentityUnavailable");
        return new Ref{guid=g,file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture)};
    }
    static HolmesFreshConsumer() {
        EditorApplication.update+=Wait;
        Event("D_observer_initialize","finalizer="+(Finalizer!=null));
        AssemblyReloadEvents.beforeAssemblyReload+=()=>Event("D_before_reload");
        AssemblyReloadEvents.afterAssemblyReload+=()=>{Event("D_after_reload");SessionState.SetBool("HOLMES05_RELOAD_DONE",true);};
        CompilationPipeline.compilationStarted+=context=>Event("C_compile_started");
        CompilationPipeline.assemblyCompilationFinished+=(assembly,messages)=>{
            int errors=messages.Count(x=>x.type==CompilerMessageType.Error);Event("C_assembly_finished",Path.GetFileName(assembly)+";errors="+errors);
            if(errors>0)SessionState.SetBool("HOLMES05_COMPILE_ERRORS",true);
        };
        CompilationPipeline.compilationFinished+=context=>{Event("C_compile_finished");SessionState.SetBool("HOLMES05_COMPILE_DONE",true);};
        AssetDatabase.importPackageCompleted+=name=>{if(SessionState.GetBool(Started,false)){Event("B_import_completed","isCompiling="+EditorApplication.isCompiling);SessionState.SetBool(Key,true);}};
        AssetDatabase.importPackageFailed+=(name,error)=>{if(SessionState.GetBool(Started,false)){Finish(new Snapshot{error="ImportPackageFailed",unity_version=Application.unityVersion});}};
    }
    public static void Run() {
        var args=Environment.GetCommandLineArgs();string work=args[Array.IndexOf(args,"-freshWork")+1];
        if(File.Exists(Path.Combine(work,"native.json")))throw new Exception("ExistingCapture");
        SessionState.SetString(WorkKey,work);SessionState.SetBool(Key,false);SessionState.SetBool(Started,true);
        if(Phase=="reopen"){Event("REOPEN_loaded","finalizer="+(Finalizer!=null));SessionState.SetBool(Key,true);return;}
        var initial=new Initial{asset_paths=AssetDatabase.GetAllAssetPaths().Where(x=>x=="Assets"||x.StartsWith("Assets/",StringComparison.Ordinal)).ToArray(),
            vapb_named_assemblies=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetName().Name).Where(x=>x.IndexOf("Vapb",StringComparison.OrdinalIgnoreCase)>=0).ToArray(),
            finalizer_available=Finalizer!=null,
            model_finalizer_available=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetType("VapbModelSkinFinalizer",false)!=null),
            assistant_available=AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetType("VapbImportAssistant",false)!=null)};
        File.WriteAllText(Path.Combine(work,"initial.json"),JsonUtility.ToJson(initial,true));
        if(initial.finalizer_available||initial.model_finalizer_available||initial.assistant_available||initial.vapb_named_assemblies.Length!=0||initial.asset_paths.Any(p=>p.EndsWith(".fbx")||p.EndsWith(".mat")||p.EndsWith(".prefab")||p.Contains("VAPBExport")))throw new Exception("NotEmptyBeforeImport");
        SessionState.SetBool("HOLMES05_COMPILE_ERRORS",false);SessionState.SetBool("HOLMES05_COMPILE_DONE",false);
        SessionState.SetBool("HOLMES05_RELOAD_DONE",false);
        Event("A_import_start","finalizer=False");AssetDatabase.ImportPackage(Argument("-freshPackage"),false);
    }
    static void Wait() {
        if(!SessionState.GetBool(Started,false)||!SessionState.GetBool(Key,false)||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
        if(SessionState.GetBool("HOLMES05_COMPILE_ERRORS",false)){Finish(new Snapshot{error="CompletedCompileErrors",unity_version=Application.unityVersion});return;}
        if(Phase!="reopen"&&(!SessionState.GetBool("HOLMES05_COMPILE_DONE",false)||!SessionState.GetBool("HOLMES05_RELOAD_DONE",false)))return;
        if(Finalizer==null){Event("E_finalizer_unavailable");Finish(new Snapshot{error="FinalizerUnavailableAfterImport",unity_version=Application.unityVersion});return;}
        Event("E_finalizer_available","assembly="+Finalizer.Assembly.GetName().Name);
        SessionState.SetBool(Started,false);EditorApplication.update-=Wait;
        var r=new Snapshot{unity_version=Application.unityVersion,import_completed=Phase!="reopen",phase=Phase};
        try {
            r.package_sha256=Hash(Argument("-freshPackage"));
            if(r.package_sha256!="0ccf9cd8d4f507a8589c02631d8865ddc456bd8e2627394ae9a8549843118dc9")throw new Exception("PackageRevision");
            r.manifest_sha256=Hash(ManifestPath);
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            if(m.reference_rebind_tasks.Length!=1)throw new Exception("TaskCount");var t=m.reference_rebind_tasks.Single();
            if(t.kind!="REBIND_DIRECT_RENDERER_V1")throw new Exception("TaskKind");
            string model=AssetDatabase.GUIDToAssetPath(t.model_guid),prefab=AssetDatabase.GUIDToAssetPath(t.prefab_guid);
            r.fbx_sha256=Hash(model);r.meta_sha256=Hash(model+".meta");r.prefab_sha256_before=Hash(prefab);
            if(r.fbx_sha256!=t.model_sha256||(Phase!="reopen"&&r.prefab_sha256_before!=t.prefab_source_sha256))throw new Exception("ImportedRevision");
            var materialPaths=t.materials.Select(x=>AssetDatabase.GUIDToAssetPath(x.guid)).ToArray();
            var materialHashes=materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}).ToArray();
            var type=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbReferenceFinalizer",false)).Single(x=>x!=null);
            r.finalizer_assembly=type.Assembly.GetName().Name;
            r.finalizer_source_sha256=Hash("Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs");
            r.finalizer_script=Reference(AssetDatabase.LoadAssetAtPath<MonoScript>("Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs"));
            r.manifest=Reference(AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath));
            r.explicit_apply=true;r.apply_returned_true=(bool)type.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
            if(!r.apply_returned_true)throw new Exception("FinalizerRejected");
            var owner=AssetDatabase.LoadAssetAtPath<GameObject>(prefab);
            r.prefab=Reference(owner);
            var renderer=owner.GetComponentsInChildren<MeshRenderer>(true).Single(x=>Reference(x).file_id==t.renderer_file_id);
            var mesh=renderer.GetComponent<MeshFilter>().sharedMesh;r.mesh=Reference(mesh);r.renderer=Reference(renderer);
            if(r.mesh.guid!=t.model_guid)throw new Exception("MeshIdentity");
            r.materials=renderer.sharedMaterials.Select(Reference).ToArray();
            r.materials_exact=r.materials.Length==t.materials.Length && r.materials.Select((x,i)=>x.guid==t.materials[i].guid&&x.file_id==t.materials[i].file_id).All(x=>x);
            r.material_bytes_preserved=materialHashes.SequenceEqual(materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}));
            r.prefab_repeat_before=Hash(prefab);var repeatedMesh=Reference(mesh);var repeatedMaterials=JsonUtility.ToJson(new Manifest{reference_rebind_tasks=new[]{new Task{materials=r.materials}}});
            r.repeat_apply_returned_true=(bool)type.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
            AssetDatabase.SaveAssets();r.prefab_repeat_after=Hash(prefab);
            var repeatRenderer=AssetDatabase.LoadAssetAtPath<GameObject>(prefab).GetComponentsInChildren<MeshRenderer>(true).Single(x=>Reference(x).file_id==t.renderer_file_id);
            r.repeat_materials_unchanged=repeatedMaterials==JsonUtility.ToJson(new Manifest{reference_rebind_tasks=new[]{new Task{materials=repeatRenderer.sharedMaterials.Select(Reference).ToArray()}}});
            var repeatMesh=Reference(repeatRenderer.GetComponent<MeshFilter>().sharedMesh);r.repeat_mesh_unchanged=repeatMesh.guid==repeatedMesh.guid&&repeatMesh.file_id==repeatedMesh.file_id;
            if(!r.repeat_apply_returned_true||r.prefab_repeat_before!=r.prefab_repeat_after||!r.repeat_materials_unchanged||!r.repeat_mesh_unchanged)throw new Exception("RepeatApplyChangedState");
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
