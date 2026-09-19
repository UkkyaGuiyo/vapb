using System;
using System.IO;
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
        private string outputPath = "";
        private string checkpointPath = "";
        private bool running;
        private readonly System.Collections.Generic.HashSet<string> completedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
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
            EditorGUILayout.LabelField("Unity packages (semicolon-separated absolute paths)");
            packagePaths = EditorGUILayout.TextField(packagePaths);
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
            var requested = (packagePaths ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries);
            packagePaths = string.Join(";", Array.FindAll(requested, item => !completedPackages.Contains(item)));
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
            if (File.Exists(outputPath))
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                WriteCheckpoint("COMPLETE", null);
                Repaint();
            }
        }

        private void WriteCheckpoint(string state, string error)
        {
            var checkpoint = new HumanOracleCheckpoint {
                state = state,
                startedAtUtc = DateTime.UtcNow.ToString("O"),
                completedAtUtc = state == "COMPLETE" ? DateTime.UtcNow.ToString("O") : null,
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
            if (previous == null || previous.completedPackages == null) return;
            foreach (var package in previous.completedPackages) completedPackages.Add(package);
        }

        private static void NotifyPackageCompleted(string packageName)
        {
            if (active == null) return;
            active.completedPackages.Add(packageName);
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
