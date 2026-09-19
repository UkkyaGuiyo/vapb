using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace UnitySemanticOracle
{
    [Serializable]
    public sealed class HumanOracleCheckpoint
    {
        public string state;
        public string startedAtUtc;
        public string completedAtUtc;
        public string runStartedAtUtc;
        public string packageStartedAtUtc;
        public string packageCompletedAtUtc;
        public string runCompletedAtUtc;
        public long durationMs;
        public string runId;
        public string schemaVersion;
        public string outputPath;
        public string error;
        public string[] completedPackages;
    }

    // This is intentionally human-started. Codex must not launch/control the
    // 2022.3 Editor; the human selects paths and presses Run in this window.
    public sealed class HumanOracleRunnerWindow : EditorWindow
    {
        private string packagePaths = "";
        private string prefabFilter = "";
        private string corpusRoot = "";
        private string packagePreview = "No packages selected.";
        private string outputPath = "";
        private string checkpointPath = "";
        private bool running;
        private readonly System.Collections.Generic.HashSet<string> completedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.List<string> pendingPackages = new System.Collections.Generic.List<string>();
        private int currentPackageIndex;
        private DateTime runStartedAtUtc;
        private DateTime packageStartedAtUtc;
        private DateTime? packageCompletedAtUtc;
        private string runId;
        private static HumanOracleRunnerWindow active;

        [MenuItem("Tools/VAPB/Unity Semantic Oracle (Human Runner)")]
        public static void Open()
        {
            GetWindow<HumanOracleRunnerWindow>("VAPB Oracle");
        }

        private void OnGUI()
        {
            EditorGUILayout.HelpBox(
                "Human-started Unity 2022.3 observation only. Uses public AssetDatabase/PrefabUtility APIs. " +
                "Keep output outside this Unity project and never commit commercial payloads.",
                MessageType.Info);
            EditorGUILayout.LabelField("Corpus folder (recursive .unitypackage discovery)");
            corpusRoot = EditorGUILayout.TextField(corpusRoot);
            if (GUILayout.Button("Select corpus folder"))
            {
                var folder = EditorUtility.OpenFolderPanel("UnityPackage corpus folder", "", "");
                if (!string.IsNullOrEmpty(folder))
                {
                    corpusRoot = folder;
                    RefreshPackagePreview();
                }
            }
            EditorGUILayout.LabelField("Individual packages (semicolon-separated absolute paths)");
            packagePaths = EditorGUILayout.TextField(packagePaths);
            if (GUILayout.Button("Refresh package preview")) RefreshPackagePreview();
            EditorGUILayout.HelpBox(packagePreview, MessageType.None);
            prefabFilter = EditorGUILayout.TextField("Prefab filter (optional)", prefabFilter);
            outputPath = EditorGUILayout.TextField("External JSON output", outputPath);
            checkpointPath = EditorGUILayout.TextField("External checkpoint", checkpointPath);
            using (new EditorGUI.DisabledScope(running))
            {
                if (GUILayout.Button("Select output folder"))
                {
                    var folder = EditorUtility.OpenFolderPanel("Oracle output folder", "", "");
                    if (!string.IsNullOrEmpty(folder))
                    {
                        outputPath = Path.Combine(folder, "unity-semantic-oracle.json");
                        checkpointPath = Path.Combine(folder, "checkpoint.json");
                    }
                }
                if (GUILayout.Button("Run observation")) StartRun();
            }
            if (running) EditorGUILayout.HelpBox("RUNNING — leave this Editor open until checkpoint is COMPLETE or FAILED.", MessageType.Warning);
        }

        private void StartRun()
        {
            if (string.IsNullOrWhiteSpace(outputPath) || string.IsNullOrWhiteSpace(checkpointPath))
                throw new InvalidOperationException("Select an external output folder first.");
            if (File.Exists(checkpointPath) && File.Exists(outputPath))
            {
                var previous = JsonUtility.FromJson<HumanOracleCheckpoint>(File.ReadAllText(checkpointPath));
                if (previous != null && previous.state == "COMPLETE")
                {
                    Debug.Log("VAPB Oracle checkpoint already COMPLETE; no work resumed.");
                    return;
                }
            }
            LoadCompletedPackages();
            if (string.IsNullOrEmpty(runId)) runId = Guid.NewGuid().ToString("N");
            var requested = DiscoverRequestedPackages();
            pendingPackages.Clear();
            foreach (var package in requested)
            {
                var key = CanonicalPackageKey(package);
                if (!completedPackages.Contains(key)) pendingPackages.Add(package);
            }
            if (pendingPackages.Count == 0)
            {
                if (File.Exists(outputPath))
                    throw new InvalidOperationException("Checkpoint has no pending packages but output is missing or stale.");
                throw new InvalidOperationException("No pending UnityPackages were selected.");
            }
            packagePaths = string.Join(";", pendingPackages.ToArray());
            currentPackageIndex = 0;
            runStartedAtUtc = DateTime.UtcNow;
            packageStartedAtUtc = runStartedAtUtc;
            packageCompletedAtUtc = null;
            var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var fullOutput = Path.GetFullPath(outputPath);
            if (fullOutput.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Output must be outside the Unity project.");
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(checkpointPath)));
            if (File.Exists(outputPath)) File.Delete(outputPath);
            WriteCheckpoint("RUNNING", null);
            Environment.SetEnvironmentVariable("UNITY_ORACLE_PACKAGES", packagePaths ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_PREFAB_FILTER", prefabFilter ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_OUTPUT", outputPath);
            Environment.SetEnvironmentVariable("UNITY_ORACLE_EXTERNAL_PROJECT", "1");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_NO_EXIT", "1");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_SCHEMA", "0.2");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_RUN_ID", runId);
            running = true;
            active = this;
            SemanticOracle.PackageCompletedCallback = NotifyPackageCompleted;
            SemanticOracle.PackageFailedCallback = NotifyPackageFailed;
            EditorApplication.update += Poll;
            try
            {
                SemanticOracle.BatchImportAndProbe();
            }
            catch (Exception exception)
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                WriteCheckpoint("FAILED", exception.Message);
                throw;
            }
        }

        private void Poll()
        {
            if (!running) return;
            if (File.Exists(outputPath) && File.GetLastWriteTimeUtc(outputPath) >= runStartedAtUtc)
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                var finished = DateTime.UtcNow;
                packageCompletedAtUtc = packageCompletedAtUtc ?? finished;
                WriteCheckpoint("COMPLETE", null, finished);
                Repaint();
            }
        }

        private void WriteCheckpoint(string state, string error, DateTime? completedAt = null)
        {
            var now = completedAt ?? DateTime.UtcNow;
            var runStart = runStartedAtUtc == default(DateTime) ? now : runStartedAtUtc;
            var checkpoint = new HumanOracleCheckpoint {
                state = state,
                startedAtUtc = runStart.ToString("O"),
                completedAtUtc = state == "COMPLETE" ? now.ToString("O") : null,
                runStartedAtUtc = runStart.ToString("O"),
                packageStartedAtUtc = packageStartedAtUtc == default(DateTime) ? null : packageStartedAtUtc.ToString("O"),
                packageCompletedAtUtc = packageCompletedAtUtc.HasValue ? packageCompletedAtUtc.Value.ToString("O") : null,
                runCompletedAtUtc = state == "COMPLETE" ? now.ToString("O") : null,
                durationMs = state == "COMPLETE" ? Math.Max(0L, (long)(now - runStart).TotalMilliseconds) : 0L,
                runId = runId,
                schemaVersion = "0.2",
                outputPath = Path.GetFullPath(outputPath),
                error = error,
                completedPackages = new System.Collections.Generic.List<string>(completedPackages).ToArray()
            };
            File.WriteAllText(checkpointPath, JsonUtility.ToJson(checkpoint, true));
        }

        private void LoadCompletedPackages()
        {
            completedPackages.Clear();
            if (!File.Exists(checkpointPath)) return;
            var previous = JsonUtility.FromJson<HumanOracleCheckpoint>(File.ReadAllText(checkpointPath));
            if (previous == null) return;
            runId = previous.runId;
            if (previous.completedPackages == null) return;
            foreach (var package in previous.completedPackages) completedPackages.Add(CanonicalPackageKey(package));
        }

        private string[] DiscoverRequestedPackages()
        {
            var packages = new System.Collections.Generic.List<string>();
            if (!string.IsNullOrWhiteSpace(corpusRoot) && Directory.Exists(corpusRoot))
            {
                packages.AddRange(Directory.GetFiles(corpusRoot, "*", SearchOption.AllDirectories)
                    .Where(path => path.EndsWith(".unitypackage", StringComparison.OrdinalIgnoreCase))
                    .OrderBy(path => CanonicalPackageKey(path), StringComparer.OrdinalIgnoreCase));
            }
            packages.AddRange((packagePaths ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries));
            return packages.Select(Path.GetFullPath).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        }

        private static string CanonicalPackageKey(string path)
        {
            return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar).ToLowerInvariant();
        }

        private void RefreshPackagePreview()
        {
            LoadCompletedPackages();
            var packages = DiscoverRequestedPackages();
            var resumed = packages.Count(package => completedPackages.Contains(CanonicalPackageKey(package)));
            packagePreview = packages.Length == 0
                ? "No .unitypackage files found."
                : packages.Length + " package(s) discovered; " + resumed + " will resume from the existing checkpoint by canonical full path.";
            Repaint();
        }

        private static void NotifyPackageCompleted(string packageName)
        {
            if (active == null) return;
            if (active.currentPackageIndex < active.pendingPackages.Count)
                active.completedPackages.Add(CanonicalPackageKey(active.pendingPackages[active.currentPackageIndex]));
            active.currentPackageIndex++;
            active.packageCompletedAtUtc = DateTime.UtcNow;
            active.packageStartedAtUtc = DateTime.UtcNow;
            active.WriteCheckpoint("RUNNING", null);
        }

        private static void NotifyPackageFailed(string error)
        {
            if (active == null) return;
            active.running = false;
            EditorApplication.update -= active.Poll;
            SemanticOracle.DetachPackageCallbacks();
            SemanticOracle.PackageCompletedCallback = null;
            SemanticOracle.PackageFailedCallback = null;
            active.WriteCheckpoint("FAILED", error);
            active.Repaint();
        }

        private void OnDisable()
        {
            EditorApplication.update -= Poll;
            if (active == this) active = null;
            SemanticOracle.PackageCompletedCallback = null;
            SemanticOracle.PackageFailedCallback = null;
        }
    }
}
