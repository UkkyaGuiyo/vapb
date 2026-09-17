using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UnitySemanticOracle
{
    public static class SyntheticFixture
    {
        public static void Build()
        {
            const string modelPath = "Assets/SyntheticModel.fbx";
            const string materialPath = "Assets/SyntheticSurfaceB.mat";
            const string prefabPath = "Assets/SyntheticVariant.prefab";
            AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null) throw new InvalidOperationException("Synthetic FBX model was not imported.");
            var shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidOperationException("Standard shader unavailable.");
            var replacement = new Material(shader) { name = "SyntheticSurfaceB" };
            AssetDatabase.DeleteAsset(materialPath);
            AssetDatabase.CreateAsset(replacement, materialPath);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("SyntheticVariant");
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(model);
            instance.name = model.name;
            instance.transform.SetParent(root.transform, false);
            var renderer = instance.GetComponentInChildren<Renderer>(true);
            if (renderer == null || renderer.sharedMaterials.Length == 0)
                throw new InvalidOperationException("Synthetic model has no Renderer material slot.");
            var materials = renderer.sharedMaterials;
            materials[0] = replacement;
            renderer.sharedMaterials = materials;
            PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            EditorSceneManager.CloseScene(scene, true);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log("Synthetic Semantic Oracle fixture built: " + prefabPath);
            EditorApplication.Exit(0);
        }
    }
}
