using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ShaderSemanticOracle
{
    [Serializable] public sealed class DurableProbeState
    {
        public string package;
        public int packagesExpected;
        public int packagesCompleted;
        public int minimumAssets;
        public string status = "NEW";
        public string classification;
        public string failureCategory;
        public bool callbackReceived;
        public int assetsObserved;
        public int stableFrames;
        public bool compiling;
        public List<string> events = new List<string>();
    }

    [Serializable] public sealed class RealMaterialRecord
    {
        public string assetPath;
        public string shaderName;
        public int propertyCount;
        public bool shaderSupported;
    }

    [Serializable] public sealed class RealProbeResult
    {
        public string schemaVersion = "0.1";
        public string accessMethod = "Unity Editor public AssetDatabase, Material, Shader, Camera and RenderTexture APIs";
        public List<RealMaterialRecord> materials = new List<RealMaterialRecord>();
        public bool gpuRender;
        public bool controlledPerturbation;
    }

    [InitializeOnLoad]
    public static class LifecycleProbe
    {
        private static string phase;
        private static string package;
        private static string[] packages;
        private static string statePath;
        private static string resultPath;
        private static string renderPath;
        private static int stableFrames;
        private static bool installed;
        private static DurableProbeState state;

        static LifecycleProbe()
        {
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PHASE"))) Install();
        }

        public static void Batch()
        {
            Install();
        }

        private static void Install()
        {
            if (installed) return;
            installed = true;
            phase = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PHASE");
            package = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PACKAGE");
            var packageList = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_PACKAGES");
            packages = string.IsNullOrEmpty(packageList) ? new[] { package } : packageList.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries);
            statePath = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_STATE");
            resultPath = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_RESULT");
            renderPath = Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_RENDER_OUTPUT");
            if (string.IsNullOrEmpty(phase) || string.IsNullOrEmpty(statePath)) throw new InvalidOperationException("Lifecycle environment is incomplete.");
            state = LoadState();
            if (state.packagesExpected == 0) state.packagesExpected = packages.Length;
            state.events.Add("process_start:" + DateTime.UtcNow.ToString("O"));
            SaveState();
            AssemblyReloadEvents.beforeAssemblyReload += BeforeReload;
            AssemblyReloadEvents.afterAssemblyReload += AfterReload;
            AssetDatabase.importPackageCompleted += PackageCompleted;
            AssetDatabase.importPackageFailed += PackageFailed;
            AssetDatabase.importPackageCancelled += PackageCancelled;
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            if (phase == "import") TickImport();
            else if (phase == "probe") TickProbe();
        }

        private static void TickImport()
        {
            if (state.status == "NEW")
            {
                state.status = "IMPORT_REQUESTED";
                state.events.Add("import_requested:" + DateTime.UtcNow.ToString("O"));
                SaveState();
                if (packages.Length == 0 || string.IsNullOrEmpty(packages[0])) Fail("IMPORT_PROCESS_TIMEOUT");
                else ImportNextPackage();
                return;
            }
            state.compiling = EditorApplication.isCompiling;
            state.assetsObserved = AssetDatabase.FindAssets("t:Material").Length;
            if (state.compiling || state.packagesCompleted < state.packagesExpected || state.assetsObserved < state.minimumAssets) stableFrames = 0;
            else stableFrames++;
            state.stableFrames = stableFrames;
            if (state.compiling) state.status = "COMPILATION_PENDING";
            else if (state.assetsObserved > 0) state.status = "ASSETS_OBSERVED";
            if (state.packagesCompleted >= state.packagesExpected && state.assetsObserved >= state.minimumAssets && !state.compiling && stableFrames >= 3)
            {
                state.status = "IMPORT_STABLE";
                state.classification = state.callbackReceived ? "CALLBACK_AND_ASSETS_STABLE" : "IMPORT_CALLBACK_MISSING_BUT_ASSETS_PRESENT";
                state.events.Add("import_stable:" + DateTime.UtcNow.ToString("O"));
                SaveState();
                CleanExit();
            }
            else SaveState();
        }

        private static void TickProbe()
        {
            if (state.status != "IMPORT_STABLE") { Fail("ASSET_DISCOVERY_TIMEOUT"); return; }
            if (EditorApplication.isCompiling) { state.compiling = true; state.status = "COMPILATION_PENDING"; SaveState(); return; }
            stableFrames++;
            if (stableFrames < 3) return;
            state.status = "PROBE_STARTED";
            state.events.Add("probe_started:" + DateTime.UtcNow.ToString("O"));
            SaveState();
            RunProbe();
        }

        private static void RunProbe()
        {
            var report = new RealProbeResult();
            foreach (var path in AssetDatabase.FindAssets("t:Material").Select(AssetDatabase.GUIDToAssetPath).OrderBy(p => p, StringComparer.Ordinal))
            {
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null) continue;
                var shader = material.shader;
                report.materials.Add(new RealMaterialRecord { assetPath = path, shaderName = shader == null ? null : shader.name, propertyCount = shader == null ? 0 : shader.GetPropertyCount(), shaderSupported = shader != null && shader.isSupported });
            }
            var source = AssetDatabase.LoadAssetAtPath<Material>(report.materials.Count == 0 ? null : report.materials[0].assetPath);
            if (source == null || source.shader == null) { Fail("PROBE_TIMEOUT"); return; }
            report.gpuRender = RenderMaterial(source, renderPath, out report.controlledPerturbation);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(resultPath)));
            File.WriteAllText(Path.GetFullPath(resultPath), JsonUtility.ToJson(report, true));
            state.status = "PROBE_COMPLETE";
            state.events.Add("probe_complete:" + DateTime.UtcNow.ToString("O"));
            SaveState();
            CleanExit();
        }

        private static bool RenderMaterial(Material source, string output, out bool perturbed)
        {
            perturbed = false;
            var clone = new Material(source);
            var cameraObject = new GameObject("ShaderOracleCamera");
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var lightObject = new GameObject("ShaderOracleLight");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            cube.GetComponent<Renderer>().sharedMaterial = clone;
            camera.transform.position = new Vector3(0f, 0f, -4f);
            camera.transform.LookAt(cube.transform);
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(35f, -30f, 0f);
            var target = new RenderTexture(256, 256, 24, RenderTextureFormat.ARGB32);
            camera.targetTexture = target;
            camera.Render();
            var first = ReadPng(target);
            if (clone.HasProperty("_Color")) { clone.SetColor("_Color", Color.green); perturbed = true; }
            else if (clone.HasProperty("_BaseColor")) { clone.SetColor("_BaseColor", Color.green); perturbed = true; }
            camera.Render();
            var second = ReadPng(target);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            File.WriteAllBytes(Path.GetFullPath(output), first);
            File.WriteAllBytes(Path.GetFullPath(output + ".perturbed.png"), second);
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(clone);
            UnityEngine.Object.DestroyImmediate(cube);
            UnityEngine.Object.DestroyImmediate(cameraObject);
            UnityEngine.Object.DestroyImmediate(lightObject);
            return first.Length > 0 && second.Length > 0;
        }

        private static byte[] ReadPng(RenderTexture target)
        {
            var previous = RenderTexture.active;
            RenderTexture.active = target;
            var image = new Texture2D(256, 256, TextureFormat.RGBA32, false);
            image.ReadPixels(new Rect(0, 0, 256, 256), 0, 0);
            image.Apply();
            var bytes = image.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(image);
            RenderTexture.active = previous;
            return bytes;
        }

        private static DurableProbeState LoadState()
        {
            if (File.Exists(statePath)) return JsonUtility.FromJson<DurableProbeState>(File.ReadAllText(statePath));
            return new DurableProbeState { package = package, packagesExpected = packages.Length, minimumAssets = int.Parse(Environment.GetEnvironmentVariable("UNITY_SHADER_ORACLE_MIN_ASSETS") ?? "1") };
        }

        private static void SaveState()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(statePath)));
            File.WriteAllText(Path.GetFullPath(statePath), JsonUtility.ToJson(state, true));
        }

        private static void ImportNextPackage()
        {
            if (state.packagesCompleted >= packages.Length) return;
            state.events.Add("package_import_requested:" + state.packagesCompleted + ":" + DateTime.UtcNow.ToString("O"));
            SaveState();
            AssetDatabase.ImportPackage(packages[state.packagesCompleted], false);
        }

        private static void PackageCompleted(string packageName)
        {
            state.callbackReceived = true;
            state.packagesCompleted++;
            state.events.Add("callback_received:" + packageName + ":" + DateTime.UtcNow.ToString("O"));
            SaveState();
            if (state.packagesCompleted < packages.Length) ImportNextPackage();
        }
        private static void PackageCancelled(string packageName) { Fail("IMPORT_CALLBACK_TIMEOUT"); }
        private static void PackageFailed(string packageName, string message) { Fail("IMPORT_CALLBACK_TIMEOUT"); }
        private static void BeforeReload() { state.events.Add("assembly_reload_before:" + DateTime.UtcNow.ToString("O")); SaveState(); }
        private static void AfterReload() { state.events.Add("assembly_reload_after:" + DateTime.UtcNow.ToString("O")); SaveState(); }
        private static void Fail(string category) { state.status = "FAILED"; state.failureCategory = category; state.events.Add("failed:" + category); SaveState(); CleanExit(); }
        private static void CleanExit() { EditorApplication.update -= Tick; AssetDatabase.importPackageCompleted -= PackageCompleted; AssetDatabase.importPackageFailed -= PackageFailed; AssetDatabase.importPackageCancelled -= PackageCancelled; EditorApplication.Exit(0); }
    }
}
