// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
// Research only. Copy into separate synthetic source/fresh Unity projects.
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbNamingStudyProbe
{
    static VapbNamingStudyProbe()
    {
        AssetDatabase.importPackageCompleted += name =>
        {
            if (SessionState.GetBool("VAPB_NAMING_IMPORT", false))
                EditorApplication.delayCall += Resume;
        };
        AssetDatabase.importPackageFailed += (name,reason) =>
        { Debug.LogError("VAPB_NAMING_FAIL=IMPORT_FAILED"); EditorApplication.Exit(1); };
        if (SessionState.GetBool("VAPB_NAMING_IMPORT", false))
            EditorApplication.delayCall += Resume;
    }
    public static void Run()
    {
        if (!File.Exists(Path.Combine(Project,"Output.unitypackage")))
        { Debug.LogError("VAPB_NAMING_FAIL=PACKAGE_MISSING"); EditorApplication.Exit(1); return; }
        SessionState.SetBool("VAPB_NAMING_IMPORT", true);
        AssetDatabase.ImportPackage(Path.Combine(Project,"Output.unitypackage"), false);
    }
    private static void Resume()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        { EditorApplication.delayCall += Resume; return; }
        if (!SessionState.GetBool("VAPB_NAMING_IMPORT", false)) return;
        SessionState.SetBool("VAPB_NAMING_IMPORT", false);
        Validate();
    }
    [Serializable] public sealed class Record
    {
        public string guid, file_id, original_path, original_name, output_path, output_name;
        public string sha256, mode, material_name, object_field_label;
        public string[] owners;
        public string[] candidate_labels;
    }
    [Serializable] public sealed class OwnerBinding
    {
        public string path, guid;
        public string[] material_guids, material_ids;
    }
    [Serializable] public sealed class Evidence
    {
        public Record[] materials;
        public string[] prefabs;
        public OwnerBinding[] owner_bindings;
        public string shader_guid, shader_id, texture_guid, texture_id;
        public string finalizer_material_guid, finalizer_material_id;
    }
    private static string Project => Directory.GetParent(Application.dataPath).FullName;
    private static string Disk(string path) => Path.Combine(Project, path);
    private static string Hash(string path)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static void Require(bool condition, string code)
    { if (!condition) throw new InvalidOperationException(code); }
    private static void Id(UnityEngine.Object value, out string guid, out string id)
    {
        Require(value != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string g, out long f), "IDENTITY");
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out guid, out long fileId);
        id = fileId.ToString(System.Globalization.CultureInfo.InvariantCulture);
    }
    private static void Check(UnityEngine.Object value, string guid, string id)
    { Id(value, out string actual, out string local); Require(actual == guid && local == id, "IDENTITY_CHANGED"); }
    public static void Prepare()
    {
        try
        {
            Require(Application.unityVersion == "2022.3.22f1", "VERSION");
            var source = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(new string('1',32)));
            Require(source != null, "SOURCE_MATERIAL");
            source.name = "Body"; EditorUtility.SetDirty(source); AssetDatabase.SaveAssets();
            var materials = new Material[6]; materials[0] = source;
            var paths = new[] { AssetDatabase.GetAssetPath(source), "Assets/NamingSource/Other/Body.mat",
                "Assets/NamingSource/MaterialOnly/Body.mat", "Assets/NamingSource/Shared/SharedSkin.mat",
                "Assets/NamingSource/Majun/Alternate/Body.mat", "Assets/NamingSource/Majun/Unknown/Body.mat" };
            for (int i=1;i<6;i++)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Disk(paths[i]))); AssetDatabase.Refresh();
                materials[i] = new Material(source) { name = i == 3 ? "SharedSkin" : "Body" };
                AssetDatabase.CreateAsset(materials[i], paths[i]);
            }
            Directory.CreateDirectory(Disk("Assets/NamingSource/Prefabs")); AssetDatabase.Refresh();
            var prefabs = new[] {"Assets/NamingSource/Prefabs/Majun.prefab", "Assets/NamingSource/Prefabs/SyntheticOther.prefab"};
            for (int i=0;i<2;i++)
            {
                var root = new GameObject(i == 0 ? "Majun" : "SyntheticOther");
                try
                {
                    root.AddComponent<MeshRenderer>().sharedMaterials = i == 0
                        ? new[] {materials[0],materials[2],materials[3],materials[4]}
                        : new[] {materials[1],materials[3]};
                    Require(PrefabUtility.SaveAsPrefabAsset(root,prefabs[i]) != null, "PREFAB_SAVE");
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            var records = new Record[6];
            for (int i=0;i<6;i++)
            {
                Id(materials[i],out string guid,out string fileId);
                var owners = prefabs.Where(p => AssetDatabase.LoadAssetAtPath<GameObject>(p)
                    .GetComponentsInChildren<Renderer>(true).Any(r => r.sharedMaterials.Contains(materials[i])))
                    .Select(AssetDatabase.AssetPathToGUID).OrderBy(g => g).ToArray();
                records[i] = new Record {guid=guid,file_id=fileId,original_path=paths[i],
                    original_name=materials[i].name,sha256=Hash(Disk(paths[i])),owners=owners};
            }
            Require(records[0].owners.Length == 1 && records[1].owners.Length == 1 &&
                records[2].owners.Length == 1 && records[3].owners.Length == 2 &&
                records[4].owners.Length == 1 && records[5].owners.Length == 0, "OWNER_CASES");
            Id(source.shader,out string shaderGuid,out string shaderId);
            Id(source.GetTexture("_MainTex"),out string textureGuid,out string textureId);
            var evidence = new Evidence {materials=records,prefabs=prefabs,shader_guid=shaderGuid,
                shader_id=shaderId,texture_guid=textureGuid,texture_id=textureId};
            File.WriteAllText(Path.Combine(Project,"SourceEvidence.json"),JsonUtility.ToJson(evidence,true));
            AssetDatabase.ExportPackage(new[] {"Assets/VAPBExport","Assets/VAPBPhase2","Assets/NamingSource"},
                Path.Combine(Project,"Source.unitypackage"),ExportPackageOptions.Recurse);
            SaveSplitInputs(evidence);
            Debug.Log("VAPB_NAMING_SOURCE_PASS cases=5"); EditorApplication.Exit(0);
        }
        catch(Exception e) { Debug.LogError("VAPB_NAMING_FAIL="+e.Message); EditorApplication.Exit(1); }
    }
    public static void ExportSplitInputs()
    {
        try
        {
            var evidence=JsonUtility.FromJson<Evidence>(File.ReadAllText(Path.Combine(Project,"SourceEvidence.json")));
            SaveSplitInputs(evidence);
            Debug.Log("VAPB_NAMING_SPLIT_SOURCE_PASS"); EditorApplication.Exit(0);
        }
        catch(Exception e) { Debug.LogError("VAPB_NAMING_FAIL="+e.Message); EditorApplication.Exit(1); }
    }
    private static void SaveSplitInputs(Evidence evidence)
    {
        evidence.materials[5].candidate_labels=new[]{"Majun","SyntheticOther"};
        evidence.owner_bindings=evidence.prefabs.Select(path =>
        {
            var slots=AssetDatabase.LoadAssetAtPath<GameObject>(path).GetComponent<MeshRenderer>().sharedMaterials;
            return new OwnerBinding {path=path,guid=AssetDatabase.AssetPathToGUID(path),
                material_guids=slots.Select(m=>{ Id(m,out string guid,out string id); return guid; }).ToArray(),
                material_ids=slots.Select(m=>{ Id(m,out string guid,out string id); return id; }).ToArray()};
        }).ToArray();
        File.WriteAllText(Path.Combine(Project,"SourceEvidence.json"),JsonUtility.ToJson(evidence,true));
        string[] p=evidence.materials.Select(r=>r.original_path).ToArray();
        AssetDatabase.ExportPackage(new[]{evidence.prefabs[0],p[0],p[4]},Path.Combine(Project,"Majun.unitypackage"));
        AssetDatabase.ExportPackage(new[]{evidence.prefabs[1],p[1]},Path.Combine(Project,"SyntheticOther.unitypackage"));
        AssetDatabase.ExportPackage(p[2],Path.Combine(Project,"Materials.unitypackage"));
        AssetDatabase.ExportPackage(p[3],Path.Combine(Project,"Shared.unitypackage"));
    }
    public static void Validate()
    {
        try
        {
            Require(Application.unityVersion == "2022.3.22f1", "VERSION");
            var expected=JsonUtility.FromJson<Evidence>(File.ReadAllText(Path.Combine(Project,"Expected.json")));
            foreach(var record in expected.materials)
            {
                string path=AssetDatabase.GUIDToAssetPath(record.guid); Require(path==record.output_path,"OUTPUT_PATH");
                var material=AssetDatabase.LoadAssetAtPath<Material>(path); Check(material,record.guid,record.file_id);
                Require(Hash(Disk(path))==record.sha256,"SERIALIZED_BYTES_CHANGED");
                Check(material.shader,expected.shader_guid,expected.shader_id);
                foreach(string property in new[]{"_MainTex","_FutureTexture"})
                    Check(material.GetTexture(property),expected.texture_guid,expected.texture_id);
                record.material_name=material.name;
                record.object_field_label=EditorGUIUtility.ObjectContent(material,typeof(Material)).text;
            }
            foreach(var binding in expected.owner_bindings)
            {
                string path=AssetDatabase.GUIDToAssetPath(binding.guid);Require(path==binding.path,"PREFAB_GUID");
                var root=AssetDatabase.LoadAssetAtPath<GameObject>(path); Require(root!=null,"PREFAB_MISSING");
                var slots=root.GetComponent<MeshRenderer>().sharedMaterials;
                Require(slots.Length==binding.material_guids.Length,"SLOT_COUNT");
                for(int i=0;i<slots.Length;i++)Check(slots[i],binding.material_guids[i],binding.material_ids[i]);
            }
            Type helper=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbFinalStateFinalizer",false)).First(t=>t!=null);
            MethodInfo apply=helper.GetMethod("Apply",BindingFlags.Public|BindingFlags.Static);
            Require((bool)apply.Invoke(null,new object[]{"Assets/VAPBExport/manifest.json"}),"FINALIZER");
            Require((bool)apply.Invoke(null,new object[]{"Assets/VAPBExport/manifest.json"}),"IDEMPOTENCE");
            string[] generated=AssetDatabase.FindAssets("t:Prefab",new[]{"Assets/VAPBExport"});
            Require(generated.Length==1,"FINALIZER_PREFAB_COUNT");
            var attached=AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(generated[0]))
                .GetComponentInChildren<MeshRenderer>().sharedMaterial;
            Check(attached,expected.finalizer_material_guid,expected.finalizer_material_id);
            File.WriteAllText(Path.Combine(Project,"Observed.json"),JsonUtility.ToJson(expected,true));
            Debug.Log("VAPB_NAMING_FRESH_PASS materials=6 cases=5"); EditorApplication.Exit(0);
        }
        catch(Exception e) { Debug.LogError("VAPB_NAMING_FAIL="+e.Message); EditorApplication.Exit(1); }
    }
}
