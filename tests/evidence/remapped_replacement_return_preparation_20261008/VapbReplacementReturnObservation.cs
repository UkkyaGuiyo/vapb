using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// One pinned T4 output; existing package-completion and explicit Apply pattern.
[InitializeOnLoad]
public static class VapbReplacementReturnObservation
{
    const string Phase="VAPB_T4_RETURN_PHASE", Started="VAPB_T4_RETURN_STARTED";
    const string Sha="b77668f09737eb029bd989f44809b44040fcb0d7c1a538a205941be75a81ea16";
    const string ManifestPath="Assets/VAPBExport/manifest.json";
    static string Root { get { return Directory.GetParent(Application.dataPath).FullName; } }
    [Serializable] sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] sealed class Task { public string kind,model_guid,prefab_path; }
    [Serializable] sealed class Faces { public Row[] rows; }
    [Serializable] sealed class Row { public string key; public int count; }
    [Serializable] sealed class Reference { public string guid,file_id; }
    [Serializable] sealed class Result
    {
        public string status="FAIL",error="",unity_version,output_sha256,mesh_guid,mesh_file_id;
        public bool finalizer_apply,mesh_identity,material_identity,face_membership,shape125;
        public int submesh_count,triangle_count;
        public Vector3 source_unity_world_bounds,returned_unity_world_bounds,observed_ratio;
        public Reference[] material_references;
        public Row[] observed_triangles;
    }
    static VapbReplacementReturnObservation()
    {
        AssetDatabase.importPackageCompleted+=name=>{if(SessionState.GetString(Phase,"")=="importing")SessionState.SetString(Phase,"imported");};
        AssetDatabase.importPackageFailed+=(name,error)=>{if(SessionState.GetString(Phase,"")=="importing")Finish(new Result{error="IMPORT_FAILED"});};
        AssetDatabase.importPackageCancelled+=name=>{if(SessionState.GetString(Phase,"")=="importing")Finish(new Result{error="IMPORT_CANCELLED"});};
        EditorApplication.update+=Resume;
    }
    public static void Run()
    {
        try
        {
            if(Application.unityVersion!="2022.3.22f1"||File.Exists(Path.Combine(Root,"ReturnObservation.json")))throw new InvalidOperationException("GATE_ENVIRONMENT");
            if(Hash(Path.Combine(Root,"Output.unitypackage"))!=Sha)throw new InvalidOperationException("GATE_OUTPUT_SHA");
            SessionState.SetFloat(Started,(float)EditorApplication.timeSinceStartup);SessionState.SetString(Phase,"importing");
            AssetDatabase.ImportPackage(Path.Combine(Root,"Output.unitypackage"),false);
        }
        catch(Exception e){Finish(new Result{error=Safe(e)});}
    }
    static void Resume()
    {
        string phase=SessionState.GetString(Phase,"");if(phase!="importing"&&phase!="imported")return;
        if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Started,0)>180){Finish(new Result{error="IMPORT_TIMEOUT"});return;}
        if(phase!="imported"||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
        Type finalizer=Type.GetType("VapbFinalStateFinalizer, Assembly-CSharp-Editor");if(finalizer==null)return;
        SessionState.SetString(Phase,"checking");var report=new Result();
        try
        {
            report.finalizer_apply=(bool)finalizer.GetMethod("Apply",BindingFlags.Static|BindingFlags.Public).Invoke(null,new object[]{ManifestPath});
            if(!report.finalizer_apply)throw new InvalidOperationException("GATE_FINALIZER");
            Task[] tasks=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Root,ManifestPath))).reference_rebind_tasks;
            if(tasks.Length!=1||tasks[0].kind!="BUILD_EXPORTED_STATIC_V2")throw new InvalidOperationException("GATE_TASK");
            GameObject prefab=AssetDatabase.LoadAssetAtPath<GameObject>(tasks[0].prefab_path);
            MeshRenderer[] rs=prefab.GetComponentsInChildren<MeshRenderer>(true);if(rs.Length!=1)throw new InvalidOperationException("GATE_RENDERERS");
            MeshRenderer renderer=rs[0];Mesh mesh=renderer.GetComponent<MeshFilter>().sharedMesh;
            report.mesh_identity=AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh,out string mg,out long mi)&&mg==tasks[0].model_guid&&mi!=0;
            report.mesh_guid=mg;report.mesh_file_id=mi.ToString();report.submesh_count=mesh.subMeshCount;
            string[] allowed={"64f92a1bd9b35a040bf9e2c6d200b34c","0318f358e4c29034aa90cc8c50b58a93","eb805efb35118044db5e74adc652673a"};
            Material[] materials=renderer.sharedMaterials;report.material_identity=materials.Length==3&&mesh.subMeshCount==3;
            report.material_references=new Reference[materials.Length];var seen=new HashSet<string>();
            var actual=new Dictionary<string,int>();Vector3[] vertices=mesh.vertices;
            for(int s=0;s<materials.Length;s++)
            {
                bool identified=AssetDatabase.TryGetGUIDAndLocalFileIdentifier(materials[s],out string guid,out long id);
                report.material_identity&=identified&&Array.IndexOf(allowed,guid)>=0&&id==2100000&&seen.Add(guid);
                report.material_references[s]=new Reference{guid=guid,file_id=id.ToString()};int[] tris=mesh.GetTriangles(s);
                for(int t=0;t<tris.Length;t+=3)
                {
                    var corners=new string[3];for(int c=0;c<3;c++){Vector3 u=renderer.transform.TransformPoint(vertices[tris[t+c]]);corners[c]=Point(new Vector3(-u.x,-u.z,u.y));}
                    Array.Sort(corners,StringComparer.Ordinal);string key=string.Join(";",corners)+"|"+guid+":"+id;
                    actual[key]=actual.ContainsKey(key)?actual[key]+1:1;report.triangle_count++;
                }
            }
            Row[] expected=JsonUtility.FromJson<Faces>(File.ReadAllText(Path.Combine(Root,"ExpectedFaces.json"))).rows;
            report.face_membership=report.triangle_count==12&&actual.Count==expected.Length;
            foreach(Row row in expected)report.face_membership&=actual.TryGetValue(row.key,out int count)&&count==row.count;
            var rows=new List<Row>();foreach(var pair in actual)rows.Add(new Row{key=pair.Key,count=pair.Value});report.observed_triangles=rows.ToArray();
            report.returned_unity_world_bounds=BoundsSize(renderer.transform,vertices);
            GameObject source=GameObject.CreatePrimitive(PrimitiveType.Cube);
            try { source.transform.localScale=Vector3.one*2;report.source_unity_world_bounds=BoundsSize(source.transform,source.GetComponent<MeshFilter>().sharedMesh.vertices); }
            finally { UnityEngine.Object.DestroyImmediate(source); }
            Vector3 a=report.source_unity_world_bounds,b=report.returned_unity_world_bounds;
            report.observed_ratio=new Vector3(b.x/a.x,b.y/a.y,b.z/a.z);
            report.shape125=Near(b,a*1.25f);
            if(!report.mesh_identity||!report.material_identity||!report.face_membership||!report.shape125)throw new InvalidOperationException("GATE_ASSERTIONS");
            report.status="PASS_BOUNDED_T4_REPLACEMENT_RETURN";
        }
        catch(Exception e){report.error=Safe(e);}
        Finish(report);
    }
    static Vector3 BoundsSize(Transform transform,Vector3[] vertices){var b=new Bounds(transform.TransformPoint(vertices[0]),Vector3.zero);foreach(Vector3 p in vertices)b.Encapsulate(transform.TransformPoint(p));return b.size;}
    static bool Near(Vector3 a,Vector3 b){return Mathf.Abs(a.x-b.x)<=0.0001f&&Mathf.Abs(a.y-b.y)<=0.0001f&&Mathf.Abs(a.z-b.z)<=0.0001f;}
    static string Point(Vector3 p){return Math.Round(p.x*1000000d).ToString(CultureInfo.InvariantCulture)+","+Math.Round(p.y*1000000d).ToString(CultureInfo.InvariantCulture)+","+Math.Round(p.z*1000000d).ToString(CultureInfo.InvariantCulture);}
    static string Hash(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static string Safe(Exception e){return e is InvalidOperationException&&e.Message.StartsWith("GATE_")?e.Message:e.GetType().Name;}
    static void Finish(Result report){SessionState.SetString(Phase,"finished");report.unity_version=Application.unityVersion;report.output_sha256=Sha;using(var writer=new StreamWriter(new FileStream(Path.Combine(Root,"ReturnObservation.json"),FileMode.CreateNew)))writer.Write(JsonUtility.ToJson(report,true));Debug.Log("VAPB_T4_RETURN="+report.status+":"+report.error);EditorApplication.Exit(report.status.StartsWith("PASS")?0:1);}
}
