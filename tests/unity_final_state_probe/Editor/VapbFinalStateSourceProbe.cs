using System;
using System.IO;
using UnityEditor;
using UnityEngine;

// Public synthetic source for the final-state export contract.
public static class VapbFinalStateSourceProbe
{
    private const string Folder = "Assets/VapbFinalState";
    private const string ModelPath = Folder + "/Input.fbx";
    private const string TexturePath = Folder + "/Pattern.png";
    private const string MaterialPath = Folder + "/Pattern.mat";
    private const string PrefabPath = Folder + "/Source.prefab";

    [Serializable]
    private sealed class SourceInfo
    {
        public string unityVersion;
        public string materialGuid;
        public string textureGuid;
        public string modelGuid;
    }

    public static void Prepare()
    {
        try
        {
            if (Application.unityVersion != "2022.3.22f1" ||
                !File.Exists(Path.Combine(Application.dataPath, "VapbFinalState/Input.fbx")))
                throw new InvalidOperationException("SOURCE_ENVIRONMENT_UNAVAILABLE");
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            MeshFilter sourceFilter = model == null ? null : model.GetComponentInChildren<MeshFilter>(true);
            if (sourceFilter == null || sourceFilter.sharedMesh == null)
                throw new InvalidOperationException("SOURCE_MESH_UNAVAILABLE");

            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            texture.SetPixels(new[] { Color.red, Color.green, Color.blue, Color.white });
            texture.Apply();
            File.WriteAllBytes(Path.Combine(Application.dataPath, "VapbFinalState/Pattern.png"), texture.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(texture);
            AssetDatabase.ImportAsset(TexturePath, ImportAssetOptions.ForceUpdate);
            Texture2D importedTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
            Shader shader = Shader.Find("Standard");
            if (importedTexture == null || shader == null)
                throw new InvalidOperationException("MATERIAL_DEPENDENCY_UNAVAILABLE");
            var material = new Material(shader) { name = "SyntheticPattern", mainTexture = importedTexture };
            AssetDatabase.CreateAsset(material, MaterialPath);

            var root = new GameObject("SyntheticRoot");
            try
            {
                var body = new GameObject("SyntheticBody");
                body.transform.SetParent(root.transform, false);
                body.AddComponent<MeshFilter>().sharedMesh = sourceFilter.sharedMesh;
                body.AddComponent<MeshRenderer>().sharedMaterial = material;
                if (PrefabUtility.SaveAsPrefabAsset(root, PrefabPath) == null)
                    throw new InvalidOperationException("SOURCE_PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }

            var info = new SourceInfo {
                unityVersion = Application.unityVersion,
                materialGuid = AssetDatabase.AssetPathToGUID(MaterialPath),
                textureGuid = AssetDatabase.AssetPathToGUID(TexturePath),
                modelGuid = AssetDatabase.AssetPathToGUID(ModelPath)
            };
            if (string.IsNullOrEmpty(info.materialGuid) || string.IsNullOrEmpty(info.textureGuid))
                throw new InvalidOperationException("SOURCE_GUID_UNAVAILABLE");
            File.WriteAllText(Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                "VapbFinalStateSourceInfo.json"), JsonUtility.ToJson(info, true));
            AssetDatabase.ExportPackage(new[] { ModelPath, TexturePath, MaterialPath, PrefabPath },
                Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Source.unitypackage"),
                ExportPackageOptions.IncludeDependencies);
            Debug.Log("VAPB_FINAL_STATE_SOURCE_PASS");
            EditorApplication.Exit(0);
        }
        catch (Exception exception)
        {
            Debug.LogError("VAPB_FINAL_STATE_SOURCE_FAIL=" + exception.Message);
            EditorApplication.Exit(1);
        }
    }
}
