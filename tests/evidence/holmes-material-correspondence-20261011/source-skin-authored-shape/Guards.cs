using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;

// Focused controls on the actual imported Shape case; clones only, no original edits.
public static class HolmesShapeGuards
{
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
            check("source_model_matching_existing_uniform_weight", true);
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
            check("unmatched_channel_rejected", false);
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
