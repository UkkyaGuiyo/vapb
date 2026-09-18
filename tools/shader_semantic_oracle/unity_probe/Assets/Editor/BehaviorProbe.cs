using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ShaderSemanticOracle
{
    [Serializable] public sealed class PrimitiveObservation
    {
        public string name;
        public string state;
        public string confidence;
        public string provenance;
        public string evidence;
        public float meanRgbDifference;
    }

    [Serializable] public sealed class BehaviorMaterialObservation
    {
        public string assetPath;
        public string shaderName;
        public string shaderGuid;
        public bool shaderSupported;
        public int propertyCount;
        public List<PrimitiveObservation> primitives = new List<PrimitiveObservation>();
    }

    [Serializable] public sealed class BehaviorProbeReport
    {
        public string schemaVersion = "0.1";
        public string accessMethod = "Unity public Material/Shader/Camera/RenderTexture APIs";
        public int renderCount;
        public int candidateMaterialCount;
        public int validShaderMaterialCount;
        public int quarantinedMaterialCount;
        public List<string> quarantineReasons = new List<string>();
        public List<BehaviorMaterialObservation> materials = new List<BehaviorMaterialObservation>();
    }

    public static class BehaviorProbe
    {
        private static bool installed;
        private static string statePath;
        private static string outputPath;
        private static string renderDirectory;

        [UnityEditor.Callbacks.DidReloadScripts]
        private static void OnScriptsReloaded() { Install(); }

        public static void Batch() { Install(); }

        private static void Install()
        {
            if (installed) return;
            if (Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PHASE") != "behavior") return;
            installed = true;
            statePath = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_STATE");
            outputPath = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_RESULT");
            renderDirectory = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_RENDER_DIRECTORY");
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            EditorApplication.update -= Tick;
            var state = JsonUtility.FromJson<DurableProbeState>(File.ReadAllText(statePath));
            if (state.status != "IMPORT_STABLE") { state.status = "FAILED"; state.failureCategory = "ASSET_DISCOVERY_TIMEOUT"; File.WriteAllText(statePath, JsonUtility.ToJson(state, true)); EditorApplication.Exit(0); return; }
            var report = new BehaviorProbeReport();
            var paths = AssetDatabase.FindAssets("t:Material").Select(AssetDatabase.GUIDToAssetPath).Where(p => !p.StartsWith("Assets/Synthetic", StringComparison.OrdinalIgnoreCase)).OrderBy(p => p, StringComparer.Ordinal).Take(16).ToArray();
            report.candidateMaterialCount = paths.Length;
            foreach (var path in paths)
            {
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null) { report.quarantinedMaterialCount++; report.quarantineReasons.Add(path + ":MATERIAL_LOAD_FAILED"); continue; }
                var shader = material.shader;
                if (shader == null || shader.name == "Hidden/InternalErrorShader" || !shader.isSupported)
                {
                    report.quarantinedMaterialCount++;
                    report.quarantineReasons.Add(path + (shader != null && !shader.isSupported ? ":UNSUPPORTED_SHADER" : ":DEPENDENCY_BLOCKED"));
                    continue;
                }
                report.validShaderMaterialCount++;
                ProbeMaterial(material, path, report);
            }
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)));
            File.WriteAllText(Path.GetFullPath(outputPath), JsonUtility.ToJson(report, true));
            state.status = "PROBE_COMPLETE";
            state.events.Add("behavior_probe_complete:" + DateTime.UtcNow.ToString("O"));
            File.WriteAllText(statePath, JsonUtility.ToJson(state, true));
            EditorApplication.Exit(0);
        }

        private static void ProbeMaterial(Material source, string path, BehaviorProbeReport report)
        {
            var shader = source.shader;
            var observation = new BehaviorMaterialObservation { assetPath = path, shaderName = shader == null ? null : shader.name, shaderSupported = shader != null && shader.isSupported, propertyCount = shader == null ? 0 : shader.GetPropertyCount() };
            if (shader == null) { report.materials.Add(observation); return; }
            long fileId;
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(shader, out observation.shaderGuid, out fileId);
            var names = new List<string>();
            for (var i = 0; i < shader.GetPropertyCount(); i++) names.Add(shader.GetPropertyName(i));
            AddPropertyEvidence(observation, "base_texture", names, new[] { "_MainTex", "_BaseMap", "_BaseColor" }, false);
            AddPropertyEvidence(observation, "normal", names, new[] { "_BumpMap", "_NormalMap", "_Normal" }, false);
            AddPropertyEvidence(observation, "emission", names, new[] { "_EmissionMap", "_EmissionColor", "_Emission" }, false);
            AddPropertyEvidence(observation, "alpha", names, new[] { "_Cutoff", "_Alpha", "_AlphaClip" }, false);
            AddPropertyEvidence(observation, "rim_fresnel", names, new[] { "_RimColor", "_RimPower", "_Fresnel" }, false);
            AddPropertyEvidence(observation, "toon_lighting", names, new[] { "_ShadingShift", "_ShadingToony", "_ShadowColor", "_Toon" }, false);
            AddPropertyEvidence(observation, "time_animation", names, new string[0], true);
            AddPropertyEvidence(observation, "billboard", names, new string[0], true);
            AddPropertyEvidence(observation, "vertex_deform", names, new string[0], true);
            var colorName = names.FirstOrDefault(name => name == "_Color" || name == "_BaseColor");
            if (!string.IsNullOrEmpty(colorName))
            {
                var diff = RenderPerturbation(source, colorName, false, path, report, Color.green);
                observation.primitives.Add(new PrimitiveObservation { name = "base_color", state = diff > 0.01f ? "DETECTED" : "INCONCLUSIVE", confidence = "MEDIUM", provenance = "RENDER_OBSERVATION", evidence = "color perturbation; mean RGB difference", meanRgbDifference = diff });
            }
            var textureName = names.FirstOrDefault(name => IsTexture(shader, name));
            if (!string.IsNullOrEmpty(textureName))
            {
                var diff = RenderPerturbation(source, textureName, true, path, report, Color.white);
                observation.primitives.Add(new PrimitiveObservation { name = "base_texture", state = diff > 0.01f ? "DETECTED" : "INCONCLUSIVE", confidence = "MEDIUM", provenance = "RENDER_OBSERVATION", evidence = "synthetic checker substitution; mean RGB difference", meanRgbDifference = diff });
            }
            var viewDiff = RenderViewDifference(source, path, report);
            observation.primitives.Add(new PrimitiveObservation { name = "view_dependent", state = viewDiff > 0.03f ? "INCONCLUSIVE" : "NOT_OBSERVED", confidence = "LOW", provenance = "RENDER_OBSERVATION", evidence = "camera angle perturbation; lighting/geometry confound retained", meanRgbDifference = viewDiff });
            report.materials.Add(observation);
        }

        private static void AddPropertyEvidence(BehaviorMaterialObservation observation, string name, List<string> names, string[] candidates, bool notTested)
        {
            var matched = names.Where(candidate => candidates.Contains(candidate, StringComparer.OrdinalIgnoreCase)).ToArray();
            observation.primitives.Add(new PrimitiveObservation { name = name, state = notTested ? "NOT_TESTED" : (matched.Length > 0 ? "PROBABLE" : "NOT_OBSERVED"), confidence = matched.Length > 0 ? "MEDIUM" : "MEDIUM", provenance = matched.Length > 0 ? "PUBLIC_API" : "PUBLIC_API", evidence = matched.Length > 0 ? "property schema contains: " + string.Join(",", matched) : "no matching property observed" });
        }

        private static bool IsTexture(Shader shader, string name)
        {
            for (var i = 0; i < shader.GetPropertyCount(); i++)
                if (shader.GetPropertyName(i) == name)
                    return shader.GetPropertyType(i).ToString() == "Texture" || shader.GetPropertyType(i).ToString() == "TexEnv";
            return false;
        }

        private static float RenderPerturbation(Material source, string property, bool texture, string path, BehaviorProbeReport report, Color color)
        {
            var clone = new Material(source);
            var baseline = Render(clone, 0f);
            if (texture)
            {
                var map = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                map.SetPixels(new[] { Color.black, Color.white, Color.white, Color.black }); map.Apply(); clone.SetTexture(property, map);
            }
            else if (clone.HasProperty(property)) clone.SetColor(property, color);
            var perturbed = Render(clone, 0f);
            report.renderCount += 2;
            SavePreview(path, "perturb", perturbed);
            UnityEngine.Object.DestroyImmediate(clone);
            return Difference(baseline, perturbed);
        }

        private static float RenderViewDifference(Material source, string path, BehaviorProbeReport report)
        {
            var clone = new Material(source);
            var first = Render(clone, 0f); var second = Render(clone, 30f); report.renderCount += 2; SavePreview(path, "view", second); UnityEngine.Object.DestroyImmediate(clone); return Difference(first, second);
        }

        private static Color32[] Render(Material material, float angle)
        {
            var cameraObject = new GameObject("ShaderBehaviorCamera"); var cube = GameObject.CreatePrimitive(PrimitiveType.Sphere); var lightObject = new GameObject("ShaderBehaviorLight");
            var camera = cameraObject.AddComponent<Camera>(); var light = lightObject.AddComponent<Light>(); cube.GetComponent<Renderer>().sharedMaterial = material;
            camera.transform.position = Quaternion.Euler(0f, angle, 0f) * new Vector3(0f, 0f, -4f); camera.transform.LookAt(cube.transform); light.type = LightType.Directional; light.transform.rotation = Quaternion.Euler(35f, -30f, 0f);
            var target = new RenderTexture(128, 128, 24, RenderTextureFormat.ARGB32); camera.targetTexture = target; camera.Render(); RenderTexture.active = target; var image = new Texture2D(128, 128, TextureFormat.RGBA32, false); image.ReadPixels(new Rect(0, 0, 128, 128), 0, 0); image.Apply(); var pixels = image.GetPixels32(); UnityEngine.Object.DestroyImmediate(image); UnityEngine.Object.DestroyImmediate(target); UnityEngine.Object.DestroyImmediate(cube); UnityEngine.Object.DestroyImmediate(cameraObject); UnityEngine.Object.DestroyImmediate(lightObject); return pixels;
        }

        private static float Difference(Color32[] left, Color32[] right)
        {
            if (left.Length != right.Length) return 1f; double total = 0d; for (var i = 0; i < left.Length; i++) total += Math.Abs(left[i].r - right[i].r) + Math.Abs(left[i].g - right[i].g) + Math.Abs(left[i].b - right[i].b); return (float)(total / (left.Length * 3d * 255d));
        }

        private static void SavePreview(string path, string suffix, Color32[] pixels)
        {
            if (string.IsNullOrEmpty(renderDirectory)) return; Directory.CreateDirectory(renderDirectory); var image = new Texture2D(128, 128, TextureFormat.RGBA32, false); image.SetPixels32(pixels); image.Apply(); var safe = "M-" + Math.Abs(path.GetHashCode()).ToString(); File.WriteAllBytes(Path.Combine(renderDirectory, safe + "-" + suffix + ".png"), image.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(image);
        }
    }
}
