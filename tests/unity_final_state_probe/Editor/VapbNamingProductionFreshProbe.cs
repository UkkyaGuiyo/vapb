// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Only this probe is initially placed in Assets; product helpers arrive in Output.
[InitializeOnLoad]
public static class VapbNamingProductionFreshProbe
{
    const string Phase="VAPB_NAMING_PRODUCTION_PHASE", ManifestPath="Assets/VAPBExport/manifest.json";
    [Serializable] class TextureRef { public string property,guid,file_id; }
    [Serializable] class MaterialRef { public string guid,file_id,path,name,sha256,meta_sha256,shader_guid,shader_id; public TextureRef[] textures; }
    [Serializable] class Expected { public MaterialRef[] materials; public string[] slot_guids,slot_ids; }
    [Serializable] class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] class Task { public string prefab_path,model_guid; }
    static string Project => Directory.GetParent(Application.dataPath).FullName;
    static string Disk(string path) => Path.Combine(Project,path);
    static VapbNamingProductionFreshProbe()
    {
        AssetDatabase.importPackageCompleted += _ => {
            if(SessionState.GetString(Phase,"")=="importing") {
                SessionState.SetString(Phase,"ready"); EditorApplication.delayCall+=Validate;
            }
        };
        AssetDatabase.importPackageFailed += (_,reason) => Fail("IMPORT_FAILED");
        AssetDatabase.importPackageCancelled += _ => Fail("IMPORT_CANCELLED");
        if(SessionState.GetString(Phase,"")=="ready") EditorApplication.delayCall+=Validate;
    }
    public static void Run()
    {
        try {
            Require(Application.unityVersion=="2022.3.22f1","VERSION");
            Require(File.Exists(Disk("Output.unitypackage")),"OUTPUT_MISSING");
            Require(!File.Exists(Disk(ManifestPath)),"NOT_FRESH");
            SessionState.SetString(Phase,"importing"); AssetDatabase.ImportPackage(Disk("Output.unitypackage"),false);
        } catch(Exception e) { Fail(e.Message); }
    }
    public static void DiagnoseModel()
    {
        try {
            var e=JsonUtility.FromJson<Expected>(File.ReadAllText(Disk("Expected.json")));
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(ReadTask().model_guid));
            var renderers=model.GetComponentsInChildren<MeshRenderer>(true);
            Require(renderers.Length==1,"MODEL_RENDERER_COUNT");
            Debug.Log("VAPB_NAMING_MODEL_SLOT_COUNT="+renderers[0].sharedMaterials.Length+" EXPECTED="+e.slot_guids.Length);
            EditorApplication.Exit(0);
        } catch(Exception e) {Fail(e.Message);}
    }
    public static void Recheck()
    {SessionState.SetString(Phase,"ready");Validate();}
    static void Validate()
    {
        if(SessionState.GetString(Phase,"")!="ready") return;
        if(EditorApplication.isCompiling||EditorApplication.isUpdating) {EditorApplication.delayCall+=Validate; return;}
        SessionState.SetString(Phase,"validating");
        try {
            var expected=JsonUtility.FromJson<Expected>(File.ReadAllText(Disk("Expected.json")));
            CheckMaterials(expected);
            Require(Apply(),"FINALIZER"); CheckSlots(expected);
            var task=ReadTask(); string before=Hash(Disk(task.prefab_path));
            Require(Apply(),"SECOND_APPLY"); CheckSlots(expected);
            Require(Hash(Disk(task.prefab_path))==before,"IDEMPOTENCE");
            AssetDatabase.SaveAssets();
            foreach(var r in expected.materials) AssetDatabase.ImportAsset(r.path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.ImportAsset(task.prefab_path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
            CheckMaterials(expected); CheckSlots(expected);
            Require(Apply(),"REIMPORT_FINALIZER"); CheckSlots(expected); CheckMaterials(expected);
            File.WriteAllText(Disk("Observed.json"),JsonUtility.ToJson(expected,true));
            Debug.Log("VAPB_NAMING_PRODUCTION_UNITY_PASS materials="+expected.materials.Length+" apply=3 reimport=1");
            SessionState.SetString(Phase,""); EditorApplication.Exit(0);
        } catch(Exception e) { Fail(e.Message); }
    }
    static void CheckMaterials(Expected e)
    {
        foreach(var r in e.materials) {
            Require(AssetDatabase.GUIDToAssetPath(r.guid)==r.path,"PATH");
            var m=AssetDatabase.LoadAssetAtPath<Material>(r.path); Identity(m,r.guid,r.file_id);
            Require(m.name==r.name,"M_NAME"); Require(Hash(Disk(r.path))==r.sha256,"MATERIAL_BYTES");
            Require(File.ReadAllText(Disk(r.path)+".meta").Contains("guid: "+r.guid),"META_GUID");
            Require(Hash(Disk(r.path)+".meta")==r.meta_sha256,"META_BYTES");
            Identity(m.shader,r.shader_guid,r.shader_id);
            foreach(var t in r.textures) {
                var texture=AssetDatabase.LoadAssetAtPath<Texture>(AssetDatabase.GUIDToAssetPath(t.guid));
                Identity(texture,t.guid,t.file_id);
                // Standard does not declare preserved future texture properties.
                // Their serialized bytes and referenced asset identities are checked.
                if(m.HasProperty(t.property)) Identity(m.GetTexture(t.property),t.guid,t.file_id);
            }
        }
    }
    static Task ReadTask() => JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath))).reference_rebind_tasks.Single();
    static void CheckSlots(Expected e)
    {
        var root=AssetDatabase.LoadAssetAtPath<GameObject>(ReadTask().prefab_path);
        Require(root!=null,"PREFAB"); var renderers=root.GetComponentsInChildren<Renderer>(true);
        Require(renderers.Length==1,"RENDERER_COUNT"); var slots=renderers[0].sharedMaterials;
        Require(slots.Length==e.slot_guids.Length,"SLOT_COUNT");
        for(int i=0;i<slots.Length;i++) Identity(slots[i],e.slot_guids[i],e.slot_ids[i]);
    }
    static bool Apply()
    {
        // Reflection accesses only the first-party public Finalizer entry point.
        Type helper=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbFinalStateFinalizer",false)).Single(t=>t!=null);
        bool ok=(bool)helper.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static).Invoke(null,new object[]{ManifestPath});
        if(ok) Require((string)helper.GetProperty("LastResult",BindingFlags.Public|BindingFlags.Static).GetValue(null)=="COMPLETE","FINALIZER_STATUS");
        return ok;
    }
    static void Identity(UnityEngine.Object obj,string guid,string id)
    {
        Require(obj!=null&&AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj,out string g,out long local)&&g==guid&&local==long.Parse(id),"IDENTITY");
    }
    static string Hash(string path) {using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static void Require(bool ok,string code) {if(!ok)throw new InvalidOperationException(code);}
    static void Fail(string code) {SessionState.SetString(Phase,"");Debug.LogError("VAPB_NAMING_PRODUCTION_UNITY_FAIL="+code);EditorApplication.Exit(1);}
}
