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
        public string[] requestedPackages;
        public string prefabFilter;
        public string lastFailedPackage;
        public string observationContext;
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
        private bool mergedCorpusMode;
        private readonly System.Collections.Generic.HashSet<string> completedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.List<string> pendingPackages = new System.Collections.Generic.List<string>();
        private int pendingPackageCursor;
        private DateTime lastCheckpointWriteAtUtc;
        private readonly System.Collections.Generic.HashSet<string> failedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.HashSet<string> skippedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private string[] packageList = new string[0];
        private double stallThresholdSeconds = 120d;
        private static HumanOracleRunnerWindow active;
        // Durable checkpoint is the single source of truth for runner state.
        // UI actions below use these properties, never a parallel transient copy.
        private HumanOracleCheckpoint durableState = new HumanOracleCheckpoint {
            state = "IDLE", runState = "IDLE", currentPhase = "IDLE", lastMessage = "Idle"
        };

        private string currentPackage { get { return durableState.currentPackage; } set { durableState.currentPackage = value; } }
        private int currentPackageIndex { get { return durableState.currentPackageIndex; } set { durableState.currentPackageIndex = value; } }
        private string runState { get { return string.IsNullOrEmpty(durableState.runState) ? durableState.state : durableState.runState; } set { durableState.runState = value; } }
        private string currentPhase { get { return durableState.currentPhase ?? "IDLE"; } set { durableState.currentPhase = value; } }
        private int retryCount { get { return durableState.retryCount; } set { durableState.retryCount = value; } }
        private string lastError { get { return durableState.lastError; } set { durableState.lastError = value; } }
        private string lastFailedPackage { get { return durableState.lastFailedPackage; } set { durableState.lastFailedPackage = value; } }
        private string lastStackTracePath { get { return durableState.lastStackTracePath; } set { durableState.lastStackTracePath = value; } }
        private string lastMessage { get { return durableState.lastMessage ?? "Idle"; } set { durableState.lastMessage = value; } }
        private string runId { get { return durableState.runId; } set { durableState.runId = value; } }
        private DateTime runStartedAtUtc { get { return ParseUtc(durableState.runStartedAtUtc); } set { durableState.runStartedAtUtc = FormatUtc(value); } }
        private DateTime packageStartedAtUtc { get { return ParseUtc(durableState.packageStartedAtUtc); } set { durableState.packageStartedAtUtc = FormatUtc(value); } }
        private DateTime? packageCompletedAtUtc { get { return ParseNullableUtc(durableState.packageCompletedAtUtc); } set { durableState.packageCompletedAtUtc = value.HasValue ? FormatUtc(value.Value) : null; } }
        private DateTime lastHeartbeatAtUtc { get { return ParseUtc(durableState.lastHeartbeatAtUtc); } set { durableState.lastHeartbeatAtUtc = FormatUtc(value); } }
        private DateTime lastProgressAtUtc { get { return ParseUtc(durableState.lastProgressAtUtc); } set { durableState.lastProgressAtUtc = FormatUtc(value); } }

        private static string FormatUtc(DateTime value) { return value == default(DateTime) ? null : value.ToString("O"); }
        private static DateTime ParseUtc(string value) { DateTime result; return DateTime.TryParse(value, null, System.Globalization.DateTimeStyles.RoundtripKind, out result) ? result : default(DateTime); }
        private static DateTime? ParseNullableUtc(string value) { var parsed = ParseUtc(value); return parsed == default(DateTime) ? (DateTime?)null : parsed; }

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
            mergedCorpusMode = EditorGUILayout.Toggle("Merged corpus (non-isolated research)", mergedCorpusMode);
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

        private void StartRun(bool resume, bool statePrepared = false)
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
            if (!statePrepared) LoadCompletedPackages();
            if (resume && string.Equals(runState, "ISOLATION_FAILED", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Isolated observation was interrupted by a Unity domain reload; discard the disposable project and start a fresh observation.");
            if (mergedCorpusMode && resume && completedPackages.Count > 0)
                throw new InvalidOperationException("Merged corpus resume is not authoritative; start a fresh merged observation.");
            if (resume && !statePrepared && (string.Equals(runState, "COMPLETE", StringComparison.OrdinalIgnoreCase) || string.Equals(runState, "RUN_COMPLETE", StringComparison.OrdinalIgnoreCase) || string.Equals(durableState.state, "COMPLETE", StringComparison.OrdinalIgnoreCase)))
                throw new InvalidOperationException("This checkpoint is already COMPLETE.");
            if (string.IsNullOrEmpty(runId)) runId = Guid.NewGuid().ToString("N");
            var requested = DiscoverRequestedPackages(resume);
            if (requested.Length > 1 && !mergedCorpusMode)
                throw new InvalidOperationException("Isolated mode accepts exactly one UnityPackage. Enable merged corpus mode only for an explicit collision experiment.");
            pendingPackages.Clear();
            foreach (var package in requested)
            {
                var key = CanonicalPackageKey(package);
                if (!completedPackages.Contains(key) && !failedPackages.Contains(key) && !skippedPackages.Contains(key)) pendingPackages.Add(package);
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
            if (!resume || packageStartedAtUtc == default(DateTime)) packageStartedAtUtc = runStartedAtUtc;
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
            Environment.SetEnvironmentVariable("UNITY_ORACLE_OBSERVATION_CONTEXT", mergedCorpusMode ? "MERGED_CORPUS" : "ISOLATED_PACKAGE");
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
                completedPackages = new System.Collections.Generic.List<string>(completedPackages).ToArray(),
                requestedPackages = packageList,
                prefabFilter = prefabFilter,
                lastFailedPackage = durableState.lastFailedPackage,
                observationContext = mergedCorpusMode ? "MERGED_CORPUS" : "ISOLATED_PACKAGE"
            };
            durableState = checkpoint;
            File.WriteAllText(checkpointPath, JsonUtility.ToJson(checkpoint, true));
        }

        private void LoadCompletedPackages()
        {
            completedPackages.Clear();
            failedPackages.Clear();
            skippedPackages.Clear();
            if (!File.Exists(checkpointPath)) return;
            var previous = JsonUtility.FromJson<HumanOracleCheckpoint>(File.ReadAllText(checkpointPath));
            if (previous == null) return;
            durableState = previous;
            runId = previous.runId;
            runState = string.IsNullOrEmpty(previous.runState) ? previous.state : previous.runState;
            corpusRoot = previous.corpusRoot;
            if (string.IsNullOrEmpty(outputPath)) outputPath = previous.outputPath;
            if (previous.requestedPackages != null && previous.requestedPackages.Length > 0)
                packagePaths = string.Join(";", previous.requestedPackages);
            if (previous.prefabFilter != null) prefabFilter = previous.prefabFilter;
            mergedCorpusMode = string.Equals(previous.observationContext, "MERGED_CORPUS", StringComparison.OrdinalIgnoreCase);
            durableState.lastFailedPackage = previous.lastFailedPackage;
            currentPhase = string.IsNullOrEmpty(previous.currentPhase) ? "WAITING_FOR_IMPORT" : previous.currentPhase;
            currentPackage = previous.currentPackage;
            currentPackageIndex = previous.currentPackageIndex;
            packageList = previous.packageList ?? packageList;
            retryCount = previous.retryCount;
            lastError = previous.lastError;
            lastStackTracePath = previous.lastStackTracePath;
            lastMessage = previous.lastMessage;
            if (string.Equals(previous.observationContext, "ISOLATED_PACKAGE", StringComparison.OrdinalIgnoreCase) &&
                (string.Equals(runState, "RUNNING", StringComparison.OrdinalIgnoreCase) || string.Equals(runState, "WAITING_FOR_UNITY", StringComparison.OrdinalIgnoreCase) || string.Equals(runState, "STALLED", StringComparison.OrdinalIgnoreCase)))
            {
                runState = "ISOLATION_FAILED";
                lastError = "ISOLATION_FAILED: Unity domain reload interrupted isolated package observation; evidence is not authoritative.";
                lastMessage = "Discard the disposable Unity project and start a fresh isolated observation.";
            }
            var reobservationRequired = string.IsNullOrEmpty(previous.observationVersion) && previous.completedPackages != null && previous.completedPackages.Length > 0;
            if (reobservationRequired)
            {
                completedPackages.Clear();
                failedPackages.Clear();
                skippedPackages.Clear();
                runState = "REOBSERVATION_REQUIRED";
                lastMessage = "Observation schema changed; previous package results require re-observation.";
            }
            if (previous.completedPackages == null) return;
            if (!reobservationRequired) foreach (var package in previous.completedPackages) completedPackages.Add(CanonicalPackageKey(package));
            if (!reobservationRequired && previous.failedPackages != null) foreach (var package in previous.failedPackages) failedPackages.Add(CanonicalPackageKey(package));
            if (!reobservationRequired && previous.skippedPackages != null) foreach (var package in previous.skippedPackages) skippedPackages.Add(CanonicalPackageKey(package));
        }

        private string[] DiscoverRequestedPackages(bool resumeFromCheckpoint = false)
        {
            if (resumeFromCheckpoint && packageList != null && packageList.Length > 0)
                return packageList.Select(Path.GetFullPath).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
            var packages = new System.Collections.Generic.List<string>();
            if (!string.IsNullOrWhiteSpace(corpusRoot) && Directory.Exists(corpusRoot))
            {
                packages.AddRange(Directory.GetFiles(corpusRoot, "*", SearchOption.AllDirectories)
                    .Where(path => path.EndsWith(".unitypackage", StringComparison.OrdinalIgnoreCase))
                    .OrderBy(path => CanonicalPackageKey(path), StringComparer.OrdinalIgnoreCase));
            }
            packages.AddRange((packagePaths ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries));
            if (packages.Count == 0 && packageList != null) packages.AddRange(packageList);
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
            if (active.pendingPackageCursor < active.pendingPackages.Count)
                active.completedPackages.Add(CanonicalPackageKey(active.pendingPackages[active.pendingPackageCursor]));
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
            if (!active.mergedCorpusMode)
            {
                active.running = false;
                active.runState = "ISOLATION_FAILED";
                active.currentPhase = "ISOLATION_FAILED";
                active.lastMessage = "Isolated import failed; discard the disposable project before retrying.";
                active.lastProgressAtUtc = DateTime.UtcNow;
                active.WriteCheckpoint("FAILED", error);
                EditorApplication.update -= active.Poll;
                SemanticOracle.DetachPackageCallbacks();
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                return;
            }
            active.lastFailedPackage = active.currentPackage;
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
            if (running || string.IsNullOrEmpty(checkpointPath) || (string.IsNullOrEmpty(currentPackage) && string.IsNullOrEmpty(lastFailedPackage))) return;
            var retryPackage = string.IsNullOrEmpty(lastFailedPackage) ? currentPackage : lastFailedPackage;
            retryCount = 0;
            failedPackages.Remove(CanonicalPackageKey(retryPackage ?? ""));
            durableState.failedPackages = new System.Collections.Generic.List<string>(failedPackages).ToArray();
            durableState.currentPackage = retryPackage;
            durableState.lastFailedPackage = null;
            packageStartedAtUtc = DateTime.UtcNow;
            StartRun(true, true);
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
