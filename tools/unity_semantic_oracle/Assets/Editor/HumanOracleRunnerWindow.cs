using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnitySemanticOracle
{
    [Serializable]
    public sealed class HumanOracleCheckpoint
    {
        public string state;
        public string runState;
        public string runnerVersion = "0.3";
        public string observationVersion = "0.3";
        public string corpusRoot;
        public string[] packageList;
        public string[] failedPackages;
        public string[] skippedPackages;
        public string currentPackage;
        public int currentPackageIndex;
        public int totalPackages;
        public string currentPhase;
        public string lastHeartbeatAtUtc;
        public string lastProgressAtUtc;
        public string lastMessage;
        public int retryCount;
        public string lastError;
        public string lastStackTracePath;
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
        private int pendingPackageCursor;
        private DateTime runStartedAtUtc;
        private DateTime packageStartedAtUtc;
        private DateTime? packageCompletedAtUtc;
        private string runId;
        private string runState = "IDLE";
        private string currentPhase = "IDLE";
        private string lastMessage = "Idle";
        private DateTime lastHeartbeatAtUtc;
        private DateTime lastProgressAtUtc;
        private DateTime lastCheckpointWriteAtUtc;
        private int retryCount;
        private string lastError;
        private string lastStackTracePath;
        private readonly System.Collections.Generic.HashSet<string> failedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.HashSet<string> skippedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private string[] packageList = new string[0];
        private double stallThresholdSeconds = 120d;
        private static HumanOracleRunnerWindow active;

        private void OnEnable()
        {
            if (string.IsNullOrEmpty(checkpointPath))
                checkpointPath = SessionState.GetString("VAPB_ORACLE_CHECKPOINT_PATH", "");
            if (!string.IsNullOrEmpty(checkpointPath) && File.Exists(checkpointPath))
                LoadCompletedPackages();
        }

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
                if (GUILayout.Button("Run observation")) StartRun(false);
                if (GUILayout.Button("Resume run")) StartRun(true);
            if (GUILayout.Button("Retry current package")) RetryCurrentPackage();
            if (GUILayout.Button("Skip current package")) SkipCurrentPackage();
            if (GUILayout.Button("Abort safely")) AbortSafely();
            if (GUILayout.Button("Open checkpoint")) RevealPath(checkpointPath);
            if (GUILayout.Button("Open output folder")) RevealPath(Path.GetDirectoryName(outputPath));
            if (GUILayout.Button("Open error log folder")) RevealPath(Path.Combine(Path.GetDirectoryName(checkpointPath) ?? "", "errors"));
            }
            DrawStatus();
        }

        private void DrawStatus()
        {
            var completed = completedPackages.Count;
            var failed = failedPackages.Count;
            var skipped = skippedPackages.Count;
            var remaining = Math.Max(0, packageList.Length - completed - failed - skipped);
            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Overall state", runState);
            EditorGUILayout.LabelField("Progress", completed + " / " + packageList.Length + " complete; " + remaining + " remaining");
            EditorGUILayout.LabelField("Current package", string.IsNullOrEmpty(currentPackage) ? "-" : Path.GetFileName(currentPackage));
            EditorGUILayout.LabelField("Current phase", currentPhase);
            EditorGUILayout.LabelField("Completed / Failed / Skipped", completed + " / " + failed + " / " + skipped);
            EditorGUILayout.LabelField("Retry count", retryCount.ToString());
            EditorGUILayout.LabelField("Run elapsed", FormatElapsed(runStartedAtUtc));
            EditorGUILayout.LabelField("Current package elapsed", FormatElapsed(packageStartedAtUtc));
            EditorGUILayout.LabelField("Last heartbeat", AgeText(lastHeartbeatAtUtc));
            EditorGUILayout.LabelField("Last progress", AgeText(lastProgressAtUtc));
            EditorGUILayout.LabelField("Last message", lastMessage);
            if (!string.IsNullOrEmpty(lastError)) EditorGUILayout.HelpBox(lastError, MessageType.Error);
            if (!string.IsNullOrEmpty(lastStackTracePath)) EditorGUILayout.LabelField("Error log", lastStackTracePath);
        }

        private static string FormatElapsed(DateTime started)
        {
            if (started == default(DateTime)) return "-";
            var elapsed = DateTime.UtcNow - started;
            return Math.Max(0, (int)elapsed.TotalHours).ToString("00") + ":" + elapsed.Minutes.ToString("00") + ":" + elapsed.Seconds.ToString("00");
        }

        private static string AgeText(DateTime timestamp)
        {
            if (timestamp == default(DateTime)) return "-";
            return timestamp.ToString("O") + " (" + Math.Max(0, (int)(DateTime.UtcNow - timestamp).TotalSeconds) + " sec ago)";
        }

        private void StartRun(bool resume)
        {
            if (string.IsNullOrWhiteSpace(outputPath) || string.IsNullOrWhiteSpace(checkpointPath))
                throw new InvalidOperationException("Select an external output folder first.");
            if (File.Exists(checkpointPath) && File.Exists(outputPath) && !resume)
            {
                var previous = JsonUtility.FromJson<HumanOracleCheckpoint>(File.ReadAllText(checkpointPath));
                if (previous != null && previous.state == "COMPLETE")
                {
                    Debug.Log("VAPB Oracle checkpoint already COMPLETE; no work resumed.");
                    return;
                }
            }
            LoadCompletedPackages();
            if (resume && string.Equals(runState, "COMPLETE", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("This checkpoint is already COMPLETE.");
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
            packageList = requested;
            currentPackageIndex = completedPackages.Count + failedPackages.Count + skippedPackages.Count;
            pendingPackageCursor = 0;
            if (!resume || runStartedAtUtc == default(DateTime)) runStartedAtUtc = DateTime.UtcNow;
            packageStartedAtUtc = runStartedAtUtc;
            packageCompletedAtUtc = null;
            lastHeartbeatAtUtc = DateTime.UtcNow;
            lastProgressAtUtc = DateTime.UtcNow;
            runState = "RUNNING";
            currentPhase = "IMPORT_REQUESTED";
            lastMessage = resume ? "Resuming from durable checkpoint." : "Run started.";
            var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var fullOutput = Path.GetFullPath(outputPath);
            if (fullOutput.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Output must be outside the Unity project.");
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(checkpointPath)));
            SessionState.SetString("VAPB_ORACLE_CHECKPOINT_PATH", checkpointPath);
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
                currentPhase = "WAITING_FOR_IMPORT";
                currentPackage = pendingPackages.Count == 0 ? null : pendingPackages[0];
                WriteCheckpoint("RUNNING", null);
                SemanticOracle.BatchImportAndProbe();
            }
            catch (Exception exception)
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                runState = "RUN_FATAL";
                currentPhase = "RUN_FATAL";
                lastError = exception.Message;
                WriteCheckpoint("FAILED", exception.Message);
                throw;
            }
        }

        private void Poll()
        {
            if (!running) return;
            Heartbeat();
            if (File.Exists(outputPath) && File.GetLastWriteTimeUtc(outputPath) >= runStartedAtUtc)
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                var finished = DateTime.UtcNow;
                packageCompletedAtUtc = packageCompletedAtUtc ?? finished;
                runState = "RUN_COMPLETE";
                currentPhase = "RUN_COMPLETE";
                lastMessage = "Corpus observation complete.";
                WriteCheckpoint("COMPLETE", null, finished);
                Repaint();
            }
        }

        private void Heartbeat()
        {
            var now = DateTime.UtcNow;
            lastHeartbeatAtUtc = now;
            var waitingForUnity = EditorApplication.isCompiling || EditorApplication.isUpdating;
            var noProgress = lastProgressAtUtc != default(DateTime) && (now - lastProgressAtUtc).TotalSeconds >= stallThresholdSeconds;
            runState = waitingForUnity ? "WAITING_FOR_UNITY" : (noProgress ? "STALLED" : "RUNNING");
            if (waitingForUnity) lastMessage = "Unity is compiling or updating the AssetDatabase.";
            else if (noProgress) lastMessage = "No semantic progress observed; inspect or resume explicitly.";
            if ((now - lastCheckpointWriteAtUtc).TotalSeconds >= 5d || noProgress)
            {
                lastCheckpointWriteAtUtc = now;
                WriteCheckpoint("RUNNING", lastError);
            }
            Repaint();
        }

        private void WriteCheckpoint(string state, string error, DateTime? completedAt = null)
        {
            var now = completedAt ?? DateTime.UtcNow;
            var runStart = runStartedAtUtc == default(DateTime) ? now : runStartedAtUtc;
            var checkpoint = new HumanOracleCheckpoint {
                state = state,
                runState = runState,
                corpusRoot = corpusRoot,
                packageList = packageList,
                failedPackages = new System.Collections.Generic.List<string>(failedPackages).ToArray(),
                skippedPackages = new System.Collections.Generic.List<string>(skippedPackages).ToArray(),
                currentPackage = currentPackage,
                currentPackageIndex = currentPackageIndex,
                totalPackages = packageList.Length,
                currentPhase = currentPhase,
                lastHeartbeatAtUtc = lastHeartbeatAtUtc == default(DateTime) ? null : lastHeartbeatAtUtc.ToString("O"),
                lastProgressAtUtc = lastProgressAtUtc == default(DateTime) ? null : lastProgressAtUtc.ToString("O"),
                lastMessage = lastMessage,
                retryCount = retryCount,
                lastError = lastError,
                lastStackTracePath = lastStackTracePath,
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
            runState = string.IsNullOrEmpty(previous.runState) ? previous.state : previous.runState;
            corpusRoot = previous.corpusRoot;
            if (string.IsNullOrEmpty(outputPath)) outputPath = previous.outputPath;
            currentPhase = string.IsNullOrEmpty(previous.currentPhase) ? "WAITING_FOR_IMPORT" : previous.currentPhase;
            currentPackage = previous.currentPackage;
            currentPackageIndex = previous.currentPackageIndex;
            packageList = previous.packageList ?? packageList;
            retryCount = previous.retryCount;
            lastError = previous.lastError;
            lastStackTracePath = previous.lastStackTracePath;
            lastMessage = previous.lastMessage;
            if (string.IsNullOrEmpty(previous.observationVersion) && previous.completedPackages != null && previous.completedPackages.Length > 0)
            {
                completedPackages.Clear();
                runState = "REOBSERVATION_REQUIRED";
                lastMessage = "Observation schema changed; previous package results require re-observation.";
            }
            if (!string.IsNullOrEmpty(previous.runStartedAtUtc)) DateTime.TryParse(previous.runStartedAtUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out runStartedAtUtc);
            if (!string.IsNullOrEmpty(previous.packageStartedAtUtc)) DateTime.TryParse(previous.packageStartedAtUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out packageStartedAtUtc);
            if (!string.IsNullOrEmpty(previous.lastHeartbeatAtUtc)) DateTime.TryParse(previous.lastHeartbeatAtUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out lastHeartbeatAtUtc);
            if (!string.IsNullOrEmpty(previous.lastProgressAtUtc)) DateTime.TryParse(previous.lastProgressAtUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out lastProgressAtUtc);
            if (previous.completedPackages == null) return;
            foreach (var package in previous.completedPackages) completedPackages.Add(CanonicalPackageKey(package));
            if (previous.failedPackages != null) foreach (var package in previous.failedPackages) failedPackages.Add(CanonicalPackageKey(package));
            if (previous.skippedPackages != null) foreach (var package in previous.skippedPackages) skippedPackages.Add(CanonicalPackageKey(package));
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
            active.pendingPackageCursor++;
            active.currentPackageIndex++;
            active.packageCompletedAtUtc = DateTime.UtcNow;
            active.lastProgressAtUtc = active.packageCompletedAtUtc.Value;
            active.retryCount = 0;
            active.currentPhase = "PACKAGE_COMPLETE";
            active.lastMessage = "Package completed; continuing to the next package.";
            active.currentPackage = active.pendingPackageCursor < active.pendingPackages.Count
                ? active.pendingPackages[active.pendingPackageCursor]
                : null;
            active.packageStartedAtUtc = DateTime.UtcNow;
            active.currentPhase = active.currentPackage == null ? "WRITING_OUTPUT" : "IMPORT_REQUESTED";
            active.WriteCheckpoint("RUNNING", null);
        }

        private static void NotifyPackageFailed(string error)
        {
            if (active == null) return;
            active.lastError = error;
            active.WriteFailureLog(error);
            if (active.retryCount < 1)
            {
                active.retryCount++;
                active.currentPhase = "IMPORT_REQUESTED";
                active.lastMessage = "Package failed; retrying once.";
                active.packageStartedAtUtc = DateTime.UtcNow;
                active.WriteCheckpoint("RUNNING", error);
                SemanticOracle.RetryCurrentPackageImport();
                return;
            }
            active.failedPackages.Add(active.currentPackage == null ? "unknown" : CanonicalPackageKey(active.currentPackage));
            active.pendingPackageCursor++;
            active.currentPackageIndex++;
            active.currentPackage = active.pendingPackageCursor < active.pendingPackages.Count
                ? active.pendingPackages[active.pendingPackageCursor]
                : null;
            active.packageStartedAtUtc = DateTime.UtcNow;
            active.runState = "PACKAGE_FAILED";
            active.currentPhase = "PACKAGE_FAILED";
            active.lastMessage = "Package failed after bounded retry; continuing.";
            active.lastProgressAtUtc = DateTime.UtcNow;
            active.WriteCheckpoint("RUNNING", error);
            SemanticOracle.ContinueAfterPackageFailure();
        }

        private void RetryCurrentPackage()
        {
            if (running || string.IsNullOrEmpty(checkpointPath)) return;
            retryCount = 0;
            failedPackages.Remove(CanonicalPackageKey(currentPackage ?? ""));
            StartRun(true);
        }

        private void SkipCurrentPackage()
        {
            if (running || string.IsNullOrEmpty(currentPackage)) return;
            skippedPackages.Add(CanonicalPackageKey(currentPackage));
            pendingPackageCursor++;
            currentPackageIndex++;
            currentPackage = pendingPackageCursor < pendingPackages.Count ? pendingPackages[pendingPackageCursor] : null;
            packageStartedAtUtc = DateTime.UtcNow;
            currentPhase = "PACKAGE_FAILED";
            lastMessage = "Current package skipped by human.";
            WriteCheckpoint("RUNNING", "Skipped by human.");
            SemanticOracle.ContinueAfterPackageFailure();
        }

        private void AbortSafely()
        {
            if (!running) return;
            running = false;
            runState = "ABORTED";
            currentPhase = "ABORTED";
            lastMessage = "Abort requested; checkpoint written.";
            EditorApplication.update -= Poll;
            SemanticOracle.DetachPackageCallbacks();
            SemanticOracle.PackageCompletedCallback = null;
            SemanticOracle.PackageFailedCallback = null;
            WriteCheckpoint("ABORTED", "Aborted by human.");
            Repaint();
        }

        private static void RevealPath(string path)
        {
            if (!string.IsNullOrEmpty(path) && (File.Exists(path) || Directory.Exists(path)))
                EditorUtility.RevealInFinder(path);
        }

        private void WriteFailureLog(string error)
        {
            try
            {
                var root = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(checkpointPath)), "errors");
                using (var sha = SHA256.Create())
                {
                    var key = currentPackage ?? "unknown";
                    var hash = BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(key))).Replace("-", "").ToLowerInvariant();
                    var directory = Path.Combine(root, hash);
                    Directory.CreateDirectory(directory);
                    lastStackTracePath = Path.Combine(directory, "stacktrace.txt");
                    File.WriteAllText(lastStackTracePath, error ?? "unknown error");
                    File.WriteAllText(Path.Combine(directory, "error.json"), "{\n  \"phase\": \"" + currentPhase + "\",\n  \"retryCount\": " + retryCount + "\n}");
                }
            }
            catch (Exception exception)
            {
                lastError = "RUN_FATAL: cannot write error log: " + exception.Message;
                runState = "RUN_FATAL";
            }
        }

        private void OnDisable()
        {
            EditorApplication.update -= Poll;
            if (active == this) active = null;
            SemanticOracle.PackageCompletedCallback = null;
            SemanticOracle.PackageFailedCallback = null;
        }
    }

    [InitializeOnLoad]
    internal static class HumanOracleDomainReloadRecovery
    {
        static HumanOracleDomainReloadRecovery()
        {
            EditorApplication.delayCall += InspectDurableState;
        }

        private static void InspectDurableState()
        {
            var checkpoint = SessionState.GetString("VAPB_ORACLE_CHECKPOINT_PATH", "");
            if (string.IsNullOrEmpty(checkpoint) || !File.Exists(checkpoint)) return;
            var text = File.ReadAllText(checkpoint);
            if (text.IndexOf("\"state\": \"RUNNING\"", StringComparison.OrdinalIgnoreCase) >= 0)
                Debug.Log("VAPB Oracle durable RUNNING checkpoint detected after domain reload. Human Resume is required.");
        }
    }
}
