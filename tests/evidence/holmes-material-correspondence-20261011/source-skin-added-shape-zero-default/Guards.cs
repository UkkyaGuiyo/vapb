using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// Focused controls on the actual imported Shape case; clones only, no original edits.
public static class HolmesShapeGuards
{
    [Serializable] class VariantWeightControl {
        public bool expected_reject=true,actual_apply,altered_variant_untouched,baseline_bytes_restored,baseline_meta_restored;
        public float baseline_weight,changed_weight;
        public string[] rejection;
    }
    static string Hash(string path) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","");}
    public static void ObserveVariantWeight(Type finalizer,string manifest,string variant,string work,int index=0)
    {
        byte[] original=File.ReadAllBytes(variant),meta=File.ReadAllBytes(variant+".meta");
        string baseline=Hash(variant),baselineMeta=Hash(variant+".meta");
        var r=new VariantWeightControl();
        try
        {
            var root=PrefabUtility.LoadPrefabContents(variant);
            try {
                var skin=root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                r.baseline_weight=skin.GetBlendShapeWeight(index);
                r.changed_weight=r.baseline_weight==100f?0f:100f;
                skin.SetBlendShapeWeight(index,r.changed_weight);
                PrefabUtility.RecordPrefabInstancePropertyModifications(skin);
                PrefabUtility.SaveAsPrefabAsset(root,variant);
            } finally {PrefabUtility.UnloadPrefabContents(root);}
            string altered=Hash(variant);if(altered==baseline)throw new Exception("VariantWeightControlNotChanged");
            var errors=new List<string>();Application.LogCallback log=(m,s,t)=>{if(t==LogType.Error||t==LogType.Exception)errors.Add(m);};
            Application.logMessageReceived+=log;
            try {r.actual_apply=(bool)finalizer.GetMethod("Apply").Invoke(null,new object[]{manifest});}
            finally {Application.logMessageReceived-=log;}
            r.rejection=errors.ToArray();r.altered_variant_untouched=Hash(variant)==altered;
        }
        finally {
            File.WriteAllBytes(variant,original);File.WriteAllBytes(variant+".meta",meta);
            AssetDatabase.ImportAsset(variant,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);
            r.baseline_bytes_restored=Hash(variant)==baseline;r.baseline_meta_restored=Hash(variant+".meta")==baselineMeta;
            File.WriteAllText(Path.Combine(work,index==0?"variant-weight-control.json":"variant-added-weight-control-"+index+".json"),JsonUtility.ToJson(r,true));
        }
    }
    public static void CheckAddedDefault()
    {
        var args=Environment.GetCommandLineArgs();
        string work=args[Array.IndexOf(args,"-freshWork")+1];
        var manifest=UnityEngine.JsonUtility.FromJson<ControlManifest>(File.ReadAllText("Assets/VAPBExport/manifest.json"));
        var f=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("VapbModelSkinFinalizer")).Single(t=>t!=null);
        ObserveVariantWeight(f,"Assets/VAPBExport/manifest.json",manifest.reference_rebind_tasks.Single().variant_path,work,3);
        EditorApplication.Exit(0);
    }
    [Serializable] class ControlTask { public string variant_path; }
    [Serializable] class ControlManifest { public ControlTask[] reference_rebind_tasks; }
    static object Call(Type type, string method, params object[] args)
    { return type.GetMethod(method, BindingFlags.Static | BindingFlags.NonPublic).Invoke(null, args); }
    public static string[] Run(Type finalizer, GameObject original, GameObject edited)
    {
        var results = new List<string>();
        var clone = UnityEngine.Object.Instantiate(original);
        var mesh = UnityEngine.Object.Instantiate(edited.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single().sharedMesh);
        try
        {
            var target = clone.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var editedRenderer = edited.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var layout = Call(finalizer, "CaptureLayout", target.sharedMesh);
            var identityType = finalizer.GetNestedType("SourceIdentity", BindingFlags.NonPublic);
            var source = Activator.CreateInstance(identityType, true);
            var route = identityType.GetField("sourceModel");
            Func<bool> compatible = () => (bool)Call(finalizer, "HasCompatibleReplacementShapes", layout, mesh, target, editedRenderer, source);
            Action<string, bool> check = (label, expected) => {
                if (compatible() != expected) throw new Exception("ShapeControl:" + label);
                results.Add(label + ":PASS");
            };
            route.SetValue(source, true);
            check("source_model_appended_own_default", true);
            route.SetValue(source, false);
            check("other_routes_still_reject_shape_replacement", false);
            route.SetValue(source, true);
            float originalWeight = target.GetBlendShapeWeight(0);
            target.SetBlendShapeWeight(0, 1f);
            check("nonuniform_source_weight_not_migrated", false);
            target.SetBlendShapeWeight(0, originalWeight);
            for(int i=0;i<target.sharedMesh.blendShapeCount;i++)target.SetBlendShapeWeight(i,originalWeight==100f?0f:100f);
            check("uniform_source_edited_weight_mismatch",false);
            for(int i=0;i<target.sharedMesh.blendShapeCount;i++)target.SetBlendShapeWeight(i,originalWeight);
            var zeros = new Vector3[mesh.vertexCount];
            mesh.AddBlendShapeFrame("unmatched-control", 100, zeros, zeros, zeros);
            check("edited_renderer_shape_count_mismatch_rejected", false);
            UnityEngine.Object.DestroyImmediate(mesh);
            mesh = UnityEngine.Object.Instantiate(edited.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single().sharedMesh);
            mesh.AddBlendShapeFrame(mesh.GetBlendShapeName(mesh.blendShapeCount - 1), 150, zeros, zeros, zeros);
            check("multiframe_channel_rejected", false);
            Action<string, string> rejectScope = (label, expected) => {
                try { Call(finalizer, "ValidateSourceModelReplacementScope", clone, target); }
                catch (TargetInvocationException error) {
                    if (error.InnerException.Message == expected) { results.Add(label + ":PASS"); return; }
                    throw;
                }
                throw new Exception("MissingScopeRejection:" + label);
            };
            var unknown = clone.AddComponent<BoxCollider>();
            rejectScope("unknown_component", "SOURCE_COMPONENT_SCOPE_UNSUPPORTED");
            UnityEngine.Object.DestroyImmediate(unknown);
            var cloth = target.gameObject.AddComponent<Cloth>();
            rejectScope("cloth", "CLOTH_INDEX_STATE_UNSUPPORTED");
            UnityEngine.Object.DestroyImmediate(cloth);
            return results.ToArray();
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(clone);
            UnityEngine.Object.DestroyImmediate(mesh);
        }
    }
}
