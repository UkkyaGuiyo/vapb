using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Reflection;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

// Reuses HOLMES-05 lifecycle capture; observes the standard replacement final-state route.
[InitializeOnLoad] public static class HolmesMirroredConsumer
{
    const string Key="HOLMES08_IMPORTED", Started="HOLMES08_STARTED", WorkKey="HOLMES08_WORK";
    const string ManifestPath="Assets/VAPBExport/manifest.json";
    [Serializable] class Ref { public string guid,file_id; }
    [Serializable] class Task { public string kind,prefab_path,model_guid,model_sha256,export_object_id; public Ref[] materials; }
    [Serializable] class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] class Initial {public string[] asset_paths,vapb_named_assemblies;public bool finalizer_available,model_finalizer_available,assistant_available;}
    [Serializable] class Group { public string topology; public int index_count,base_vertex; public int[] indices; }
    [Serializable] class Snapshot {
        public string instruction_id="HOLMES-20261011-08",status="FAIL",error,unity_version,package_sha256,manifest_sha256,policy;
        public string fbx_sha256,fbx_sha256_after,meta_sha256,meta_sha256_after,prefab_sha256_before,prefab_sha256_after;
        public bool import_completed,explicit_apply,apply_returned_true,apply_base_vertex,materials_exact,material_bytes_preserved;
        public Ref mesh,renderer; public Ref[] materials; public Group[] groups; public Vector2[] uv; public Vector3[] vertices,normals,world_vertices,world_normals; public int subMeshCount; public float renderer_determinant; public Vector3 renderer_position,renderer_scale; public Quaternion renderer_rotation; public string graphics_backend,render_status,render_error,render_shader_sha256; public bool render_observation_clone_only,observation_preserves_assets; public Pixels[] render_pixels; public float[] renderer_matrix; public string finalizer_result;
        public Ref prefab,manifest,finalizer_script;
        public string finalizer_source_sha256,finalizer_assembly;
        public int matching_realization_markers;
        public string phase,prefab_repeat_before,prefab_repeat_after;
        public bool repeat_apply_returned_true,repeat_materials_unchanged,repeat_mesh_unchanged;
    }
    static string Work=>SessionState.GetString(WorkKey,"");
    static string Argument(string name) {var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,name);return i>=0&&i+1<args.Length?args[i+1]:"";}
    static string Phase=>Argument("-freshPhase");
    static Type Finalizer=>AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbFinalStateFinalizer",false)).SingleOrDefault(x=>x!=null);
    static void Event(string stage,string detail="") {
        string folder=Argument("-freshWork");if(string.IsNullOrEmpty(folder))return;
        File.AppendAllText(Path.Combine(folder,"events.tsv"),DateTime.UtcNow.ToString("o")+"\t"+stage+"\t"+detail+"\n");
    }
    static string Hash(string path) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static Ref Reference(UnityEngine.Object obj) {
        if(obj==null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj,out string g,out long id))throw new Exception("IdentityUnavailable");
        return new Ref{guid=g,file_id=id.ToString(System.Globalization.CultureInfo.InvariantCulture)};
    }
    static HolmesMirroredConsumer() {
        EditorApplication.update+=Wait;
        Event("D_observer_initialize","finalizer="+(Finalizer!=null));
        AssemblyReloadEvents.beforeAssemblyReload+=()=>Event("D_before_reload");
        AssemblyReloadEvents.afterAssemblyReload+=()=>{Event("D_after_reload");SessionState.SetBool("HOLMES08_RELOAD_DONE",true);};
        CompilationPipeline.compilationStarted+=context=>Event("C_compile_started");
        CompilationPipeline.assemblyCompilationFinished+=(assembly,messages)=>{
            int errors=messages.Count(x=>x.type==CompilerMessageType.Error);Event("C_assembly_finished",Path.GetFileName(assembly)+";errors="+errors);
            if(errors>0)SessionState.SetBool("HOLMES08_COMPILE_ERRORS",true);
        };
        CompilationPipeline.compilationFinished+=context=>{Event("C_compile_finished");SessionState.SetBool("HOLMES08_COMPILE_DONE",true);};
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
        SessionState.SetBool("HOLMES08_COMPILE_ERRORS",false);SessionState.SetBool("HOLMES08_COMPILE_DONE",false);
        SessionState.SetBool("HOLMES08_RELOAD_DONE",false);
        Event("A_import_start","finalizer=False");AssetDatabase.ImportPackage(Argument("-freshPackage"),false);
    }
    static void Wait() {
        if(!SessionState.GetBool(Started,false)||!SessionState.GetBool(Key,false)||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
        if(SessionState.GetBool("HOLMES08_COMPILE_ERRORS",false)){Finish(new Snapshot{error="CompletedCompileErrors",unity_version=Application.unityVersion});return;}
        if(Phase!="reopen"&&(!SessionState.GetBool("HOLMES08_COMPILE_DONE",false)||!SessionState.GetBool("HOLMES08_RELOAD_DONE",false)))return;
        if(Finalizer==null){Event("E_finalizer_unavailable");Finish(new Snapshot{error="FinalizerUnavailableAfterImport",unity_version=Application.unityVersion});return;}
        Event("E_finalizer_available","assembly="+Finalizer.Assembly.GetName().Name);
        SessionState.SetBool(Started,false);EditorApplication.update-=Wait;
        var r=new Snapshot{unity_version=Application.unityVersion,import_completed=Phase!="reopen",phase=Phase};
        try {
            r.package_sha256=Hash(Argument("-freshPackage"));
            if(r.package_sha256!="0f699eb64a3b864cd06ddede7d4e691bd063701d8c675a95ab20b2ccf473edbf")throw new Exception("PackageRevision");
            r.manifest_sha256=Hash(ManifestPath);
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            if(m.reference_rebind_tasks.Length!=1)throw new Exception("TaskCount");var t=m.reference_rebind_tasks.Single();
            if(t.kind!="BUILD_EXPORTED_STATIC_V2")throw new Exception("TaskKind");
            string model=AssetDatabase.GUIDToAssetPath(t.model_guid),prefab=t.prefab_path;
            r.fbx_sha256=Hash(model);r.meta_sha256=Hash(model+".meta");r.prefab_sha256_before=File.Exists(prefab)?Hash(prefab):"ABSENT";
            if(r.fbx_sha256!=t.model_sha256||r.prefab_sha256_before!="ABSENT")throw new Exception("ImportedRevision");
            var materialPaths=t.materials.Select(x=>AssetDatabase.GUIDToAssetPath(x.guid)).ToArray();
            var materialHashes=materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}).ToArray();
            var type=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbFinalStateFinalizer",false)).Single(x=>x!=null);
            r.finalizer_assembly=type.Assembly.GetName().Name;
            r.finalizer_source_sha256=Hash("Assets/VAPBExport/Editor/VapbFinalStateFinalizer.cs");
            r.finalizer_script=Reference(AssetDatabase.LoadAssetAtPath<MonoScript>("Assets/VAPBExport/Editor/VapbFinalStateFinalizer.cs"));
            r.manifest=Reference(AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath));
            r.explicit_apply=true;r.apply_returned_true=(bool)type.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
            if(!r.apply_returned_true)throw new Exception("FinalizerRejected");
            var owner=AssetDatabase.LoadAssetAtPath<GameObject>(prefab);
            r.prefab=Reference(owner);
            var renderer=owner.GetComponentsInChildren<MeshRenderer>(true).Single();
            var mesh=renderer.GetComponent<MeshFilter>().sharedMesh;r.mesh=Reference(mesh);r.renderer=Reference(renderer);
            if(r.mesh.guid!=t.model_guid)throw new Exception("MeshIdentity");
            r.materials=renderer.sharedMaterials.Select(Reference).ToArray();
            r.materials_exact=r.materials.Length==t.materials.Length && r.materials.All(x=>t.materials.Any(y=>x.guid==y.guid&&x.file_id==y.file_id));
            r.material_bytes_preserved=materialHashes.SequenceEqual(materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")}));
            r.prefab_repeat_before=Hash(prefab);var repeatedMesh=Reference(mesh);var repeatedMaterials=JsonUtility.ToJson(new Manifest{reference_rebind_tasks=new[]{new Task{materials=r.materials}}});
            r.repeat_apply_returned_true=(bool)type.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
            AssetDatabase.SaveAssets();r.prefab_repeat_after=Hash(prefab);
            var repeatRenderer=AssetDatabase.LoadAssetAtPath<GameObject>(prefab).GetComponentsInChildren<MeshRenderer>(true).Single();
            r.repeat_materials_unchanged=repeatedMaterials==JsonUtility.ToJson(new Manifest{reference_rebind_tasks=new[]{new Task{materials=repeatRenderer.sharedMaterials.Select(Reference).ToArray()}}});
            var repeatMesh=Reference(repeatRenderer.GetComponent<MeshFilter>().sharedMesh);r.repeat_mesh_unchanged=repeatMesh.guid==repeatedMesh.guid&&repeatMesh.file_id==repeatedMesh.file_id;
            if(!r.repeat_apply_returned_true||r.prefab_repeat_before!=r.prefab_repeat_after||!r.repeat_materials_unchanged||!r.repeat_mesh_unchanged)throw new Exception("RepeatApplyChangedState");
            var modelRoot=AssetDatabase.LoadAssetAtPath<GameObject>(model);
            r.matching_realization_markers=modelRoot.GetComponentsInChildren<MonoBehaviour>(true).Count(x=>x!=null&&x.GetType().Name=="VapbExportObjectMarker"&&(string)x.GetType().GetField("exportObjectId").GetValue(x)==t.export_object_id);
            mesh=repeatRenderer.GetComponent<MeshFilter>().sharedMesh; r.finalizer_result=(string)type.GetProperty("LastResult").GetValue(null); r.policy=EditorJsonUtility.ToJson(AssetImporter.GetAtPath(model));r.uv=mesh.uv;r.vertices=mesh.vertices;r.normals=mesh.normals;var matrix=repeatRenderer.transform.localToWorldMatrix;r.renderer_matrix=Enumerable.Range(0,16).Select(i=>matrix[i]).ToArray();r.apply_base_vertex=true;r.renderer_determinant=matrix.determinant;r.renderer_position=repeatRenderer.transform.position;r.renderer_scale=repeatRenderer.transform.localScale;r.renderer_rotation=repeatRenderer.transform.rotation;r.subMeshCount=mesh.subMeshCount;r.world_vertices=r.vertices.Select(v=>matrix.MultiplyPoint3x4(v)).ToArray();r.world_normals=r.normals.Select(n=>matrix.inverse.transpose.MultiplyVector(n).normalized).ToArray();
            r.groups=Enumerable.Range(0,mesh.subMeshCount).Select(sub=>{int b=(int)mesh.GetBaseVertex(sub);var indices=mesh.GetIndices(sub,true);
                if(!indices.SequenceEqual(mesh.GetIndices(sub,false).Select(i=>i+b)))throw new Exception("BaseVertexMismatch");
                return new Group{topology=mesh.GetTopology(sub).ToString(),indices=indices,index_count=(int)mesh.GetIndexCount(sub),base_vertex=b};}).ToArray();
            r.fbx_sha256_after=Hash(model);r.meta_sha256_after=Hash(model+".meta");r.prefab_sha256_after=Hash(prefab);
            if(!r.materials_exact||!r.material_bytes_preserved||r.matching_realization_markers!=1||r.fbx_sha256!=r.fbx_sha256_after||Hash(ManifestPath)!=r.manifest_sha256)throw new Exception("ReturnEvidenceMismatch");
            CaptureRender(owner,repeatRenderer,r);
            r.observation_preserves_assets=Hash(prefab)==r.prefab_sha256_after && materialHashes.SequenceEqual(materialPaths.SelectMany(p=>new[]{Hash(p),Hash(p+".meta")})) && JsonUtility.ToJson(new Manifest{reference_rebind_tasks=new[]{new Task{materials=repeatRenderer.sharedMaterials.Select(Reference).ToArray()}}})==repeatedMaterials && Reference(repeatRenderer.GetComponent<MeshFilter>().sharedMesh).guid==r.mesh.guid;
            if(!r.observation_preserves_assets)throw new Exception("RenderObservationModifiedAssets");
            r.status="PASS";
        } catch(Exception error){r.error=error.GetType().Name+": "+error.Message;}
        Finish(r);
    }
    [Serializable] class ProbeFace { public string plane; public Vector3 center,normal; }
    [Serializable] class ProbeOracle { public ProbeFace[] faces; }
    [Serializable] class Pixels { public string plane,side,png_sha256; public int white_pixels,total_pixels; public Vector3 camera_position,camera_forward; }
    static void CaptureRender(GameObject prefab,MeshRenderer original,Snapshot r) {
        r.graphics_backend=SystemInfo.graphicsDeviceType.ToString();r.render_status="NOT_RUN";
        if(SystemInfo.graphicsDeviceType==UnityEngine.Rendering.GraphicsDeviceType.Null){r.render_error="Null graphics device";return;}
        GameObject clone=null,camObject=null;Material material=null;RenderTexture rt=null;Texture2D image=null;
        var previous=RenderTexture.active;
        try {
            if(GL.invertCulling)throw new Exception("Unexpected global invertCulling");
            var oracle=JsonUtility.FromJson<ProbeOracle>(File.ReadAllText(Argument("-freshRenderOracle")));
            if(oracle.faces.Length!=6)throw new Exception("RenderOracleFaceCount");
            var shader=AssetDatabase.LoadAssetAtPath<Shader>("Assets/HolmesMirroredConsumer/ObserveCullBack.shader");
            if(shader==null||!shader.isSupported)throw new Exception("CullBackShaderUnavailable");
            r.render_shader_sha256=Hash("Assets/HolmesMirroredConsumer/ObserveCullBack.shader");
            material=new Material(shader){hideFlags=HideFlags.HideAndDontSave};
            clone=UnityEngine.Object.Instantiate(prefab);clone.hideFlags=HideFlags.HideAndDontSave;
            foreach(var t in clone.GetComponentsInChildren<Transform>(true))t.gameObject.layer=31;
            var renderer=clone.GetComponentsInChildren<MeshRenderer>(true).Single();
            if(renderer.GetComponent<MeshFilter>().sharedMesh!=original.GetComponent<MeshFilter>().sharedMesh)throw new Exception("ObservationMeshChanged");
            var actual=renderer.transform.localToWorldMatrix;var expected=original.transform.localToWorldMatrix;
            if(Enumerable.Range(0,16).Any(i=>actual[i]!=expected[i]))throw new Exception("ObservationTransformChanged");
            // Observation-only copy: never assign Materials on the actual asset Renderer.
            renderer.sharedMaterials=Enumerable.Repeat(material,renderer.sharedMaterials.Length).ToArray();
            camObject=new GameObject("HOLMES08 observation camera"){hideFlags=HideFlags.HideAndDontSave};
            var camera=camObject.AddComponent<Camera>();camera.enabled=false;camera.cullingMask=1<<31;
            camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            camera.orthographic=true;camera.orthographicSize=0.05f;camera.aspect=1;camera.nearClipPlane=0.01f;camera.farClipPlane=20;
            camera.allowHDR=false;camera.allowMSAA=false;camera.useOcclusionCulling=false;
            rt=new RenderTexture(32,32,24,RenderTextureFormat.ARGB32){antiAliasing=1,hideFlags=HideFlags.HideAndDontSave};rt.Create();camera.targetTexture=rt;
            image=new Texture2D(32,32,TextureFormat.RGB24,false){hideFlags=HideFlags.HideAndDontSave};
            var pixels=new System.Collections.Generic.List<Pixels>();
            foreach(var face in oracle.faces)foreach(var side in new[]{"outside","inside"}){
                camera.transform.position=face.center+face.normal.normalized*(side=="outside"?0.25f:-0.25f);
                camera.transform.LookAt(face.center);camera.Render();RenderTexture.active=rt;
                image.ReadPixels(new Rect(0,0,32,32),0,0);image.Apply();var colors=image.GetPixels32();
                string path=Path.Combine(Work,"render-"+face.plane.Replace("+","plus").Replace("-","minus")+"-"+side+".png");File.WriteAllBytes(path,image.EncodeToPNG());
                pixels.Add(new Pixels{plane=face.plane,side=side,white_pixels=colors.Count(c=>c.r>200&&c.g>200&&c.b>200),total_pixels=colors.Length,png_sha256=Hash(path),camera_position=camera.transform.position,camera_forward=camera.transform.forward});
            }
            if(GL.invertCulling)throw new Exception("ObserverChangedGlobalCulling");
            r.render_pixels=pixels.ToArray();r.render_status="CAPTURED";r.render_observation_clone_only=true;
        }catch(Exception e){r.render_status="BLOCKED";r.render_error=e.GetType().Name+":"+e.Message;}
        finally {
            RenderTexture.active=previous;
            if(camObject!=null)UnityEngine.Object.DestroyImmediate(camObject);
            if(clone!=null)UnityEngine.Object.DestroyImmediate(clone);
            if(material!=null)UnityEngine.Object.DestroyImmediate(material);
            if(image!=null)UnityEngine.Object.DestroyImmediate(image);
            if(rt!=null){rt.Release();UnityEngine.Object.DestroyImmediate(rt);}
        }
    }
    static void Finish(Snapshot r) {
        SessionState.SetBool(Started,false);
        using(var s=new FileStream(Path.Combine(Work,"native.json"),FileMode.CreateNew))using(var w=new StreamWriter(s))w.Write(JsonUtility.ToJson(r,true));
        EditorApplication.Exit(r.status=="PASS"?0:1);
    }
}
