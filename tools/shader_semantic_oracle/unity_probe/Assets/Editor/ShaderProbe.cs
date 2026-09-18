using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ShaderSemanticOracle
{
    [Serializable] public sealed class ShaderPropertyObservation
    {
        public string name;
        public string type;
        public bool materialHasProperty;
        public string textureGuid;
        public string texturePath;
        public string textureScale;
        public string textureOffset;
    }

    [Serializable] public sealed class MaterialObservation
    {
        public string assetPath;
        public string materialGuid;
        public string shaderName;
        public string shaderGuid;
        public bool shaderSupported;
        public int renderQueue;
        public bool enableInstancing;
        public List<string> keywords = new List<string>();
        public List<ShaderPropertyObservation> properties = new List<ShaderPropertyObservation>();
    }

    [Serializable] public sealed class ShaderProbeReport
    {
        public string schemaVersion = "0.1";
        public string unityVersion = Application.unityVersion;
        public string accessMethod = "Unity Editor batchmode + public AssetDatabase/Material/Shader APIs";
        public List<MaterialObservation> materials = new List<MaterialObservation>();
    }

    public static class ShaderProbe
    {
        private static string[] pendingPackages;
        private static int pendingPackageIndex;
        private static string pendingMaterialOutput;

        public static void BatchProbe()
        {
            var output = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_OUTPUT");
            if (string.IsNullOrEmpty(output)) throw new InvalidOperationException("UNITY_SHADER_ORACLE_OUTPUT is required.");
            var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var outputPath = Path.GetFullPath(output);
            if (outputPath.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Shader probe output must be outside the Unity project.");

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var report = new ShaderProbeReport();
            foreach (var path in AssetDatabase.FindAssets("t:Material").Select(AssetDatabase.GUIDToAssetPath).OrderBy(p => p, StringComparer.Ordinal))
            {
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null) continue;
                report.materials.Add(ReadMaterial(path, material));
            }
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
            Debug.Log("Shader Oracle wrote " + outputPath + " materials=" + report.materials.Count);
            EditorApplication.Exit(0);
        }

        public static void BatchRenderProbe()
        {
            var output = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_RENDER_OUTPUT");
            if (string.IsNullOrEmpty(output)) throw new InvalidOperationException("UNITY_SHADER_ORACLE_RENDER_OUTPUT is required.");
            var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var outputPath = Path.GetFullPath(output);
            if (outputPath.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Render probe output must be outside the Unity project.");
            var cameraObject = new GameObject("ShaderOracleCamera");
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var camera = cameraObject.AddComponent<Camera>();
            var lightObject = new GameObject("ShaderOracleLight");
            var light = lightObject.AddComponent<Light>();
            var material = new Material(Shader.Find("Standard")) { color = new Color(0.8f, 0.2f, 0.1f, 1f) };
            cube.GetComponent<Renderer>().sharedMaterial = material;
            camera.transform.position = new Vector3(0f, 0f, -4f);
            camera.transform.LookAt(cube.transform);
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(35f, -30f, 0f);
            var target = new RenderTexture(256, 256, 24, RenderTextureFormat.ARGB32);
            var previous = RenderTexture.active;
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            var image = new Texture2D(256, 256, TextureFormat.RGBA32, false);
            image.ReadPixels(new Rect(0, 0, 256, 256), 0, 0);
            image.Apply();
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllBytes(outputPath, image.EncodeToPNG());
            RenderTexture.active = previous;
            UnityEngine.Object.DestroyImmediate(image);
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(material);
            UnityEngine.Object.DestroyImmediate(cube);
            UnityEngine.Object.DestroyImmediate(cameraObject);
            UnityEngine.Object.DestroyImmediate(lightObject);
            Debug.Log("Shader Oracle rendered " + outputPath);
            EditorApplication.Exit(0);
        }

        public static void BatchImportAndProbeMaterials()
        {
            var packages = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PACKAGES");
            pendingPackages = string.IsNullOrEmpty(packages) ? new string[0] : packages.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries);
            pendingMaterialOutput = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_OUTPUT");
            if (pendingPackages.Length == 0 || string.IsNullOrEmpty(pendingMaterialOutput)) throw new InvalidOperationException("UNITY_SHADER_ORACLE_PACKAGES and UNITY_SHADER_ORACLE_OUTPUT are required.");
            var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (Path.GetFullPath(pendingMaterialOutput).StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Shader probe output must be outside the Unity project.");
            AssetDatabase.importPackageCompleted += OnPackageCompleted;
            AssetDatabase.importPackageCancelled += OnPackageCancelled;
            AssetDatabase.importPackageFailed += OnPackageFailed;
            ImportNextPackage();
        }

        private static void ImportNextPackage()
        {
            if (pendingPackageIndex < pendingPackages.Length)
            {
                AssetDatabase.ImportPackage(pendingPackages[pendingPackageIndex++], false);
                return;
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var report = new ShaderProbeReport();
            foreach (var path in AssetDatabase.FindAssets("t:Material").Select(AssetDatabase.GUIDToAssetPath).OrderBy(p => p, StringComparer.Ordinal))
            {
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material != null) report.materials.Add(ReadMaterial(path, material));
            }
            var outputPath = Path.GetFullPath(pendingMaterialOutput);
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
            AssetDatabase.importPackageCompleted -= OnPackageCompleted;
            AssetDatabase.importPackageCancelled -= OnPackageCancelled;
            AssetDatabase.importPackageFailed -= OnPackageFailed;
            Debug.Log("Shader Oracle imported and wrote " + outputPath + " materials=" + report.materials.Count);
            EditorApplication.Exit(0);
        }

        private static void OnPackageCompleted(string packageName) { ImportNextPackage(); }
        private static void OnPackageCancelled(string packageName) { throw new InvalidOperationException("Shader package import cancelled: " + packageName); }
        private static void OnPackageFailed(string packageName, string errorMessage) { throw new InvalidOperationException("Shader package import failed: " + packageName + " - " + errorMessage); }

        private static MaterialObservation ReadMaterial(string path, Material material)
        {
            var observation = new MaterialObservation { assetPath = path, renderQueue = material.renderQueue, enableInstancing = material.enableInstancing };
            long materialFileId;
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out observation.materialGuid, out materialFileId);
            var shader = material.shader;
            if (shader == null) return observation;
            observation.shaderName = shader.name;
            observation.shaderSupported = shader.isSupported;
            long shaderFileId;
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(shader, out observation.shaderGuid, out shaderFileId);
            observation.keywords.AddRange(material.shaderKeywords ?? new string[0]);
            for (var i = 0; i < shader.GetPropertyCount(); i++)
            {
                var name = shader.GetPropertyName(i);
                var property = new ShaderPropertyObservation { name = name, type = shader.GetPropertyType(i).ToString(), materialHasProperty = material.HasProperty(name) };
                if (property.type == "TexEnv" && property.materialHasProperty)
                {
                    var texture = material.GetTexture(name);
                    if (texture != null)
                    {
                        property.texturePath = AssetDatabase.GetAssetPath(texture);
                        long textureFileId;
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out property.textureGuid, out textureFileId);
                    }
                    property.textureScale = material.GetTextureScale(name).ToString();
                    property.textureOffset = material.GetTextureOffset(name).ToString();
                }
                observation.properties.Add(property);
            }
            return observation;
        }
    }
}
