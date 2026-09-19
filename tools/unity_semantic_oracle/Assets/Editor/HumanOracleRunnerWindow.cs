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
        public string runnerVersion = "0.4";
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
        public string checkpointPath;
        public string outputDirectory;
        public string runTimestamp;
        public string error;
        public string[] completedPackages;
        public string[] requestedPackages;
        public string prefabFilter;
        public string lastFailedPackage;
        public string observationContext;
        public string baselineManifestPath;
        public string baselineStatus;
        public int unexpectedAssetCount;
        public string cleanupStartedAtUtc;
        public string cleanupCompletedAtUtc;
        public string stabilityReachedAtUtc;
        public string baselineVerifiedAtUtc;
        public string packageFinalizedAtUtc;
        public int baselineStableTicks;
        public string importStartedAtUtc;
        public string importCompletedAtUtc;
        public string probeStartedAtUtc;
        public string probeCompletedAtUtc;
        public long runDurationMs;
        public long packageDurationMs;
        public long importDurationMs;
        public long probeDurationMs;
        public PackageTimingRecord[] packageTimings;
    }

    [Serializable]
    public sealed class ActiveRunPointer
    {
        public string schemaVersion = "1";
        public string state;
        public string runId;
        public string runTimestamp;
        public string checkpointPath;
        public string observationPath;
        public string updatedAtUtc;
    }

    [Serializable]
    public sealed class PackageTimingRecord
    {
        public string packagePath;
        public string packageStartedAtUtc;
        public string importStartedAtUtc;
        public string importCompletedAtUtc;
        public string probeStartedAtUtc;
        public string probeCompletedAtUtc;
        public string packageCompletedAtUtc;
    }

    [Serializable] public sealed class BaselineManifestFile
    {
        public string path;
        public string sha256;
    }

    [Serializable] public sealed class BaselineManifestData
    {
        public string manifestVersion;
        public string baselineId;
        public string baselineHash;
        public string projectRootIdentity;
        public string unityTargetVersion;
        public BaselineManifestFile[] files;
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
        private string outputDirectory = "";
        private string runTimestamp = "";
        private string activeRunState = "NONE";
        private string activeRunId = "";
        private Vector2 scrollPosition;
        private bool running;
        private bool mergedCorpusMode;
        private string baselineManifestPath = "";
        private string baselineStatus = "UNKNOWN";
        private string baselineId = "";
        private string baselineHash = "";
        private int unexpectedAssetCount;
        private readonly System.Collections.Generic.HashSet<string> completedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.List<string> pendingPackages = new System.Collections.Generic.List<string>();
        private int pendingPackageCursor;
        private DateTime lastCheckpointWriteAtUtc;
        private readonly System.Collections.Generic.HashSet<string> failedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private readonly System.Collections.Generic.HashSet<string> skippedPackages = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private string[] packageList = new string[0];
        private double stallThresholdSeconds = 120d;
        private static HumanOracleRunnerWindow active;
        private const string OutputDirectoryPref = "VAPB_ORACLE_OUTPUT_DIRECTORY";
        private const string BaselineManifestPref = "VAPB_ORACLE_BASELINE_MANIFEST";
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
        private DateTime cleanupStartedAtUtc { get { return ParseUtc(durableState.cleanupStartedAtUtc); } set { durableState.cleanupStartedAtUtc = FormatUtc(value); } }
        private DateTime cleanupCompletedAtUtc { get { return ParseUtc(durableState.cleanupCompletedAtUtc); } set { durableState.cleanupCompletedAtUtc = FormatUtc(value); } }
        private DateTime stabilityReachedAtUtc { get { return ParseUtc(durableState.stabilityReachedAtUtc); } set { durableState.stabilityReachedAtUtc = FormatUtc(value); } }
        private DateTime baselineVerifiedAtUtc { get { return ParseUtc(durableState.baselineVerifiedAtUtc); } set { durableState.baselineVerifiedAtUtc = FormatUtc(value); } }
        private DateTime packageFinalizedAtUtc { get { return ParseUtc(durableState.packageFinalizedAtUtc); } set { durableState.packageFinalizedAtUtc = FormatUtc(value); } }
        private DateTime importStartedAtUtc { get { return ParseUtc(durableState.importStartedAtUtc); } set { durableState.importStartedAtUtc = FormatUtc(value); } }
        private DateTime importCompletedAtUtc { get { return ParseUtc(durableState.importCompletedAtUtc); } set { durableState.importCompletedAtUtc = FormatUtc(value); } }
        private DateTime probeStartedAtUtc { get { return ParseUtc(durableState.probeStartedAtUtc); } set { durableState.probeStartedAtUtc = FormatUtc(value); } }
        private DateTime probeCompletedAtUtc { get { return ParseUtc(durableState.probeCompletedAtUtc); } set { durableState.probeCompletedAtUtc = FormatUtc(value); } }
        private int baselineStableTicks { get { return durableState.baselineStableTicks; } set { durableState.baselineStableTicks = value; } }
        private bool finalizationPending;
        private readonly System.Collections.Generic.List<PackageTimingRecord> packageTimings = new System.Collections.Generic.List<PackageTimingRecord>();

        private static string FormatUtc(DateTime value) { return value == default(DateTime) ? null : value.ToString("O"); }
        private static DateTime ParseUtc(string value) { DateTime result; return DateTime.TryParse(value, null, System.Globalization.DateTimeStyles.RoundtripKind, out result) ? result : default(DateTime); }
        private static DateTime? ParseNullableUtc(string value) { var parsed = ParseUtc(value); return parsed == default(DateTime) ? (DateTime?)null : parsed; }

        private PackageTimingRecord TimingFor(string package)
        {
            var key = CanonicalPackageKey(package ?? "");
            var record = packageTimings.FirstOrDefault(item => CanonicalPackageKey(item.packagePath ?? "") == key);
            if (record == null)
            {
                record = new PackageTimingRecord { packagePath = package };
                packageTimings.Add(record);
            }
            return record;
        }

        private static string KeepTimestamp(string existing, DateTime value)
        {
            return string.IsNullOrEmpty(existing) ? value.ToString("O") : existing;
        }

        private void OnEnable()
        {
            outputDirectory = EditorPrefs.GetString(OutputDirectoryPref, "");
            baselineManifestPath = EditorPrefs.GetString(BaselineManifestPref, "");
            if (string.IsNullOrEmpty(checkpointPath))
                checkpointPath = SessionState.GetString("VAPB_ORACLE_CHECKPOINT_PATH", "");
            if (!string.IsNullOrEmpty(outputDirectory)) LoadActiveRunPointer(false);
            if (!string.Equals(activeRunState, "COMPLETE", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrEmpty(checkpointPath) && File.Exists(checkpointPath))
            {
                LoadCompletedPackages();
                EditorApplication.delayCall += ReconcileTerminalState;
            }
        }

        private string ActiveRunPointerPath
        {
            get { return string.IsNullOrEmpty(outputDirectory) ? "" : Path.Combine(outputDirectory, "active-run.json"); }
        }

        [MenuItem("Tools/VAPB/Unity Semantic Oracle (Human Runner)")]
        public static void Open()
        {
            GetWindow<HumanOracleRunnerWindow>("VAPB Oracle");
        }

        private void OnGUI()
        {
            scrollPosition = EditorGUILayout.BeginScrollView(scrollPosition);
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
            baselineManifestPath = EditorGUILayout.TextField("Baseline manifest (external)", baselineManifestPath);
            if (GUI.changed) EditorPrefs.SetString(BaselineManifestPref, baselineManifestPath ?? "");
            if (GUILayout.Button("Verify baseline")) VerifyBaselineStatus();
            EditorGUILayout.LabelField("Baseline", baselineStatus);
            EditorGUILayout.LabelField("Baseline ID", string.IsNullOrEmpty(baselineId) ? "-" : baselineId);
            EditorGUILayout.LabelField("Unexpected Assets", unexpectedAssetCount.ToString());
            EditorGUILayout.LabelField("Isolation ready", (!mergedCorpusMode && baselineStatus == "CLEAN") || mergedCorpusMode ? "YES" : "NO");
            EditorGUILayout.LabelField("Output directory", string.IsNullOrEmpty(outputDirectory) ? "-" : outputDirectory);
            EditorGUILayout.LabelField("Current run", string.IsNullOrEmpty(runTimestamp) ? "-" : runTimestamp);
            EditorGUILayout.LabelField("Observation", string.IsNullOrEmpty(outputPath) ? "-" : Path.GetFileName(outputPath));
            EditorGUILayout.LabelField("Checkpoint", string.IsNullOrEmpty(checkpointPath) ? "-" : Path.GetFileName(checkpointPath));
            EditorGUILayout.LabelField("Active run", string.IsNullOrEmpty(activeRunId) ? activeRunState : activeRunState + " / " + activeRunId);
            using (new EditorGUI.DisabledScope(running))
            {
                if (GUILayout.Button("Select output folder"))
                {
                    var folder = EditorUtility.OpenFolderPanel("Oracle output folder", "", "");
                    if (!string.IsNullOrEmpty(folder))
                    {
                        outputDirectory = folder;
                        EditorPrefs.SetString(OutputDirectoryPref, outputDirectory);
                        outputPath = "";
                        checkpointPath = "";
                        runTimestamp = "";
                        activeRunId = "";
                        activeRunState = "NONE";
                        LoadActiveRunPointer(false);
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
            EditorGUILayout.EndScrollView();
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

        private static string RelativeProjectPath(string root, string path)
        {
            var normalizedRoot = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!path.StartsWith(normalizedRoot, StringComparison.OrdinalIgnoreCase)) return null;
            return path.Substring(normalizedRoot.Length).Replace('\\', '/');
        }

        private static bool IsBaselineExcluded(string relative)
        {
            var parts = relative.Split('/');
            return parts.Any(part => part == "Library" || part == "Temp" || part == "Obj" || part == "Logs" || part == "UserSettings");
        }

        private static string Sha256File(string path)
        {
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(path))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        private void VerifyBaselineStatus()
        {
            baselineStatus = "VERIFYING";
            baselineId = "";
            baselineHash = "";
            unexpectedAssetCount = 0;
            try
            {
                if (string.IsNullOrEmpty(baselineManifestPath) || !File.Exists(baselineManifestPath)) throw new InvalidOperationException("Baseline manifest is missing.");
                var data = JsonUtility.FromJson<BaselineManifestData>(File.ReadAllText(baselineManifestPath));
                if (data == null || data.manifestVersion != "2" || data.unityTargetVersion != "2022.3.62f3" || string.IsNullOrEmpty(data.baselineId) || string.IsNullOrEmpty(data.baselineHash) || data.baselineHash.Length != 64 || data.files == null)
                    throw new InvalidOperationException("Baseline manifest schema or target version is invalid.");
                var expected = data.files.ToDictionary(item => item.path, item => item.sha256, StringComparer.OrdinalIgnoreCase);
                var root = Directory.GetParent(Application.dataPath).FullName;
                using (var rootSha = SHA256.Create())
                {
                    var rootIdentity = BitConverter.ToString(rootSha.ComputeHash(Encoding.UTF8.GetBytes(root.ToLowerInvariant()))).Replace("-", "").ToLowerInvariant();
                    if (!string.Equals(data.projectRootIdentity, rootIdentity, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Baseline project root identity differs.");
                }
                var actual = new System.Collections.Generic.Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                foreach (var file in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
                {
                    var relative = RelativeProjectPath(root, file);
                    if (string.IsNullOrEmpty(relative) || IsBaselineExcluded(relative)) continue;
                    actual[relative] = Sha256File(file);
                }
                var errors = expected.Keys.Except(actual.Keys, StringComparer.OrdinalIgnoreCase).ToList();
                errors.AddRange(actual.Keys.Except(expected.Keys, StringComparer.OrdinalIgnoreCase));
                errors.AddRange(expected.Keys.Where(path => actual.ContainsKey(path) && !string.Equals(expected[path], actual[path], StringComparison.OrdinalIgnoreCase)));
                unexpectedAssetCount = actual.Keys.Count(path => path.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase) && !expected.ContainsKey(path));
                if (unexpectedAssetCount > 0) throw new InvalidOperationException("Unexpected non-Oracle Assets detected.");
                if (errors.Count > 0) throw new InvalidOperationException("Baseline file drift detected.");
                baselineId = data.baselineId;
                baselineHash = data.baselineHash.ToLowerInvariant();
                baselineStatus = "CLEAN";
            }
            catch (Exception exception)
            {
                baselineStatus = "DIRTY";
                lastError = "BASELINE_DIRTY: " + exception.Message;
            }
            Repaint();
        }

        private static string NewRunTimestamp(DateTime startedAtUtc)
        {
            return startedAtUtc.ToUniversalTime().ToString("yyyyMMdd_HHmmss");
        }

        private static bool IsUnderDirectory(string path, string directory)
        {
            if (string.IsNullOrEmpty(path) || string.IsNullOrEmpty(directory)) return false;
            var root = Path.GetFullPath(directory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            return Path.GetFullPath(path).StartsWith(root, StringComparison.OrdinalIgnoreCase);
        }

        private void LoadActiveRunPointer(bool requireResumable)
        {
            activeRunState = "NONE";
            activeRunId = "";
            if (string.IsNullOrEmpty(ActiveRunPointerPath) || !File.Exists(ActiveRunPointerPath)) return;
            try
            {
                var pointer = JsonUtility.FromJson<ActiveRunPointer>(File.ReadAllText(ActiveRunPointerPath));
                if (pointer == null || pointer.schemaVersion != "1" || string.IsNullOrEmpty(pointer.runId) ||
                    string.IsNullOrEmpty(pointer.checkpointPath) || string.IsNullOrEmpty(pointer.observationPath) ||
                    !IsUnderDirectory(pointer.checkpointPath, outputDirectory) || !IsUnderDirectory(pointer.observationPath, outputDirectory))
                    throw new InvalidOperationException("Active run pointer is invalid or escapes the output directory.");
                activeRunState = string.IsNullOrEmpty(pointer.state) ? "UNKNOWN" : pointer.state;
                activeRunId = pointer.runId;
                checkpointPath = Path.GetFullPath(pointer.checkpointPath);
                outputPath = Path.GetFullPath(pointer.observationPath);
                runTimestamp = pointer.runTimestamp ?? "";
                if (string.Equals(activeRunState, "COMPLETE", StringComparison.OrdinalIgnoreCase))
                {
                    if (requireResumable) throw new InvalidOperationException("Active run is already COMPLETE. Use Run observation to create a new run.");
                    return;
                }
                if (requireResumable && File.Exists(checkpointPath))
                {
                    var checkpoint = JsonUtility.FromJson<HumanOracleCheckpoint>(File.ReadAllText(checkpointPath));
                    if (checkpoint == null || !string.Equals(checkpoint.runId, pointer.runId, StringComparison.OrdinalIgnoreCase) ||
                        !string.Equals(checkpoint.runTimestamp, pointer.runTimestamp, StringComparison.OrdinalIgnoreCase) ||
                        !string.Equals(Path.GetFullPath(checkpoint.outputPath), outputPath, StringComparison.OrdinalIgnoreCase) ||
                        !string.Equals(Path.GetFullPath(checkpoint.checkpointPath), checkpointPath, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidOperationException("ACTIVE_RUN_MISMATCH: pointer and checkpoint identity differ.");
                }
                if (!requireResumable) return;
            }
            catch (Exception exception)
            {
                activeRunState = "INVALID";
                activeRunId = "";
                if (requireResumable) throw new InvalidOperationException("ACTIVE_RUN_INVALID: " + exception.Message);
            }
        }

        private void CreateNewRunFiles(DateTime startedAtUtc)
        {
            if (string.IsNullOrWhiteSpace(outputDirectory))
                throw new InvalidOperationException("Select an output directory first.");
            outputDirectory = Path.GetFullPath(outputDirectory);
            Directory.CreateDirectory(outputDirectory);
            runTimestamp = NewRunTimestamp(startedAtUtc);
            var stem = runTimestamp;
            var candidateCheckpoint = Path.Combine(outputDirectory, "checkpoint_" + stem + ".json");
            var candidateOutput = Path.Combine(outputDirectory, "unity-semantic-oracle_" + stem + ".json");
            if (File.Exists(candidateCheckpoint) || File.Exists(candidateOutput))
            {
                stem += "_" + runId.Substring(0, Math.Min(8, runId.Length));
                candidateCheckpoint = Path.Combine(outputDirectory, "checkpoint_" + stem + ".json");
                candidateOutput = Path.Combine(outputDirectory, "unity-semantic-oracle_" + stem + ".json");
            }
            if (File.Exists(candidateCheckpoint) || File.Exists(candidateOutput))
                throw new InvalidOperationException("RUN_FILE_COLLISION: timestamped run files already exist.");
            checkpointPath = candidateCheckpoint;
            outputPath = candidateOutput;
            activeRunState = "RUNNING";
            activeRunId = runId;
            EditorPrefs.SetString(OutputDirectoryPref, outputDirectory);
        }

        private void WriteActiveRunPointer(string state)
        {
            if (string.IsNullOrEmpty(ActiveRunPointerPath)) return;
            var pointer = new ActiveRunPointer {
                state = state,
                runId = runId,
                runTimestamp = runTimestamp,
                checkpointPath = Path.GetFullPath(checkpointPath),
                observationPath = Path.GetFullPath(outputPath),
                updatedAtUtc = DateTime.UtcNow.ToString("O")
            };
            WriteTextAtomically(ActiveRunPointerPath, JsonUtility.ToJson(pointer, true));
            activeRunState = state;
            activeRunId = runId;
        }

        private static void WriteTextAtomically(string path, string content)
        {
            var fullPath = Path.GetFullPath(path);
            var temporary = fullPath + ".tmp";
            try
            {
                File.WriteAllText(temporary, content);
                if (File.Exists(fullPath)) File.Replace(temporary, fullPath, null);
                else File.Move(temporary, fullPath);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }

        private void StartRun(bool resume, bool statePrepared = false)
        {
            if (string.IsNullOrWhiteSpace(outputDirectory))
                throw new InvalidOperationException("Select an output directory first.");
            if (resume)
            {
                LoadActiveRunPointer(true);
                if (!File.Exists(checkpointPath)) throw new InvalidOperationException("ACTIVE_RUN_INVALID: checkpoint is missing.");
                LoadCompletedPackages();
            }
            else
            {
                runId = Guid.NewGuid().ToString("N");
                completedPackages.Clear();
                failedPackages.Clear();
                skippedPackages.Clear();
                packageTimings.Clear();
                packageList = new string[0];
                durableState = new HumanOracleCheckpoint { state = "IDLE", runState = "IDLE", currentPhase = "IDLE", lastMessage = "Idle", runId = runId };
                CreateNewRunFiles(DateTime.UtcNow);
            }
            if (!mergedCorpusMode)
            {
                VerifyBaselineStatus();
                if (baselineStatus != "CLEAN")
                    throw new InvalidOperationException("BASELINE_DIRTY: Unexpected non-Oracle assets detected. Isolated observation is blocked.");
            }
            if (resume && string.Equals(runState, "ISOLATION_FAILED", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Isolated observation was interrupted by a Unity domain reload; discard the disposable project and start a fresh observation.");
            if (mergedCorpusMode && resume && completedPackages.Count > 0)
                throw new InvalidOperationException("Merged corpus resume is not authoritative; start a fresh merged observation.");
            if (resume && !statePrepared && (string.Equals(runState, "COMPLETE", StringComparison.OrdinalIgnoreCase) || string.Equals(runState, "RUN_COMPLETE", StringComparison.OrdinalIgnoreCase) || string.Equals(durableState.state, "COMPLETE", StringComparison.OrdinalIgnoreCase)))
                throw new InvalidOperationException("This checkpoint is already COMPLETE.");
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
            cleanupStartedAtUtc = default(DateTime);
            cleanupCompletedAtUtc = default(DateTime);
            stabilityReachedAtUtc = default(DateTime);
            baselineVerifiedAtUtc = default(DateTime);
            packageFinalizedAtUtc = default(DateTime);
            baselineStableTicks = 0;
            finalizationPending = false;
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
            WriteCheckpoint("RUNNING", null);
            WriteActiveRunPointer("RUNNING");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_PACKAGES", packagePaths ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_PREFAB_FILTER", prefabFilter ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_OBSERVATION_CONTEXT", mergedCorpusMode ? "MERGED_CORPUS" : "ISOLATED_PACKAGE");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_OUTPUT", outputPath);
            Environment.SetEnvironmentVariable("UNITY_ORACLE_EXTERNAL_PROJECT", "1");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_NO_EXIT", "1");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_SCHEMA", "0.2");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_RUN_ID", runId);
            Environment.SetEnvironmentVariable("UNITY_ORACLE_BASELINE_MANIFEST", baselineManifestPath ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_BASELINE_ID", baselineId ?? "");
            Environment.SetEnvironmentVariable("UNITY_ORACLE_BASELINE_HASH", baselineHash ?? "");
            // A pre-run clean baseline proves only that the disposable project was
            // ready. The package import itself makes the project dirty. Isolation
            // is therefore attested only after external cleanup and finalization.
            Environment.SetEnvironmentVariable("UNITY_ORACLE_ISOLATION_VERIFIED", "0");
            running = true;
            active = this;
            SemanticOracle.PackageCompletedCallback = NotifyPackageCompleted;
            SemanticOracle.PackageFailedCallback = NotifyPackageFailed;
            SemanticOracle.ImportCompletedCallback = NotifyImportCompleted;
            SemanticOracle.ProbeStartedCallback = NotifyProbeStarted;
            SemanticOracle.ProbeCompletedCallback = NotifyProbeCompleted;
            EditorApplication.update += Poll;
            try
            {
                currentPhase = "WAITING_FOR_IMPORT";
                currentPackage = pendingPackages.Count == 0 ? null : pendingPackages[0];
                importStartedAtUtc = DateTime.UtcNow;
                if (currentPackage != null)
                {
                    var timing = TimingFor(currentPackage);
                    timing.packageStartedAtUtc = KeepTimestamp(timing.packageStartedAtUtc, packageStartedAtUtc);
                    timing.importStartedAtUtc = KeepTimestamp(timing.importStartedAtUtc, importStartedAtUtc);
                }
                WriteCheckpoint("RUNNING", null);
                SemanticOracle.BatchImportAndProbe();
            }
            catch (Exception exception)
            {
                running = false;
                EditorApplication.update -= Poll;
                SemanticOracle.PackageCompletedCallback = null;
                SemanticOracle.PackageFailedCallback = null;
                SemanticOracle.ImportCompletedCallback = null;
                SemanticOracle.ProbeStartedCallback = null;
                SemanticOracle.ProbeCompletedCallback = null;
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
                SemanticOracle.ImportCompletedCallback = null;
                SemanticOracle.ProbeStartedCallback = null;
                SemanticOracle.ProbeCompletedCallback = null;
                var finished = DateTime.UtcNow;
                packageCompletedAtUtc = packageCompletedAtUtc ?? finished;
                cleanupStartedAtUtc = finished;
                baselineStableTicks = 0;
                finalizationPending = true;
                runState = "WAITING_FOR_CLEANUP";
                currentPhase = "CLEANUP_REQUIRED";
                lastMessage = "Import evidence is ready. Close Unity, run external cleanup, reopen Unity, then verify the clean baseline.";
                WriteCheckpoint("PENDING_CLEANUP", null);
                Repaint();
            }
        }

        private void ReconcileTerminalState()
        {
            if (mergedCorpusMode || string.IsNullOrEmpty(outputPath) || !File.Exists(outputPath)) return;
            if (!string.Equals(runState, "COMPLETE", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(runState, "RUN_COMPLETE", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(runState, "WAITING_FOR_CLEANUP", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(runState, "PENDING_CLEANUP", StringComparison.OrdinalIgnoreCase)) return;
            finalizationPending = true;
            runState = "WAITING_FOR_CLEANUP";
            currentPhase = "CLEANUP_REQUIRED";
            lastMessage = "Waiting for external cleanup and a stable clean baseline.";
            baselineStableTicks = 0;
            EditorApplication.update -= FinalizeAfterCleanup;
            EditorApplication.update += FinalizeAfterCleanup;
            WriteCheckpoint("PENDING_CLEANUP", lastError);
        }

        private void FinalizeAfterCleanup()
        {
            if (!finalizationPending || mergedCorpusMode) return;
            if (EditorApplication.isCompiling || EditorApplication.isUpdating)
            {
                baselineStableTicks = 0;
                return;
            }
            VerifyBaselineStatus();
            if (baselineStatus != "CLEAN")
            {
                baselineStableTicks = 0;
                return;
            }
            cleanupCompletedAtUtc = cleanupCompletedAtUtc == default(DateTime) ? DateTime.UtcNow : cleanupCompletedAtUtc;
            baselineStableTicks++;
            if (baselineStableTicks < 3) return;
            VerifyBaselineStatus();
            if (baselineStatus != "CLEAN") { baselineStableTicks = 0; return; }
            var now = DateTime.UtcNow;
            stabilityReachedAtUtc = now;
            baselineVerifiedAtUtc = now;
            packageFinalizedAtUtc = now;
            finalizationPending = false;
            runState = "RUN_COMPLETE";
            currentPhase = "RUN_COMPLETE";
            lastMessage = "Corpus observation complete; cleanup and stable baseline verification passed.";
            EditorApplication.update -= FinalizeAfterCleanup;
            WriteFinalizationMarker(now);
            WriteCheckpoint("COMPLETE", null, now);
            Repaint();
        }

        private void WriteFinalizationMarker(DateTime finalizedAtUtc)
        {
            var marker = Path.GetFullPath(outputPath) + ".finalization.json";
            var text = "{\n" +
                "  \"runId\": \"" + (runId ?? "") + "\",\n" +
                "  \"isolationVerified\": true,\n" +
                "  \"baselineId\": \"" + (baselineId ?? "") + "\",\n" +
                "  \"baselineHash\": \"" + (baselineHash ?? "") + "\",\n" +
                "  \"finalizedAtUtc\": \"" + finalizedAtUtc.ToString("O") + "\"\n" +
                "}\n";
            File.WriteAllText(marker, text);
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
                runTimestamp = runTimestamp,
                schemaVersion = "0.3",
                outputPath = Path.GetFullPath(outputPath),
                checkpointPath = Path.GetFullPath(checkpointPath),
                outputDirectory = outputDirectory,
                error = error,
                completedPackages = new System.Collections.Generic.List<string>(completedPackages).ToArray(),
                requestedPackages = packageList,
                prefabFilter = prefabFilter,
                lastFailedPackage = durableState.lastFailedPackage,
                observationContext = mergedCorpusMode ? "MERGED_CORPUS" : "ISOLATED_PACKAGE",
                baselineManifestPath = baselineManifestPath,
                baselineStatus = baselineStatus,
                unexpectedAssetCount = unexpectedAssetCount,
                cleanupStartedAtUtc = cleanupStartedAtUtc == default(DateTime) ? null : cleanupStartedAtUtc.ToString("O"),
                cleanupCompletedAtUtc = cleanupCompletedAtUtc == default(DateTime) ? null : cleanupCompletedAtUtc.ToString("O"),
                stabilityReachedAtUtc = stabilityReachedAtUtc == default(DateTime) ? null : stabilityReachedAtUtc.ToString("O"),
                baselineVerifiedAtUtc = baselineVerifiedAtUtc == default(DateTime) ? null : baselineVerifiedAtUtc.ToString("O"),
                packageFinalizedAtUtc = packageFinalizedAtUtc == default(DateTime) ? null : packageFinalizedAtUtc.ToString("O"),
                baselineStableTicks = baselineStableTicks,
                importStartedAtUtc = importStartedAtUtc == default(DateTime) ? null : importStartedAtUtc.ToString("O"),
                importCompletedAtUtc = importCompletedAtUtc == default(DateTime) ? null : importCompletedAtUtc.ToString("O"),
                probeStartedAtUtc = probeStartedAtUtc == default(DateTime) ? null : probeStartedAtUtc.ToString("O"),
                probeCompletedAtUtc = probeCompletedAtUtc == default(DateTime) ? null : probeCompletedAtUtc.ToString("O"),
                runDurationMs = state == "COMPLETE" ? Math.Max(0L, (long)(now - runStart).TotalMilliseconds) : 0L,
                packageDurationMs = packageCompletedAtUtc.HasValue && packageStartedAtUtc != default(DateTime) ? Math.Max(0L, (long)(packageCompletedAtUtc.Value - packageStartedAtUtc).TotalMilliseconds) : 0L,
                importDurationMs = importCompletedAtUtc != default(DateTime) && importStartedAtUtc != default(DateTime) ? Math.Max(0L, (long)(importCompletedAtUtc - importStartedAtUtc).TotalMilliseconds) : 0L,
                probeDurationMs = probeCompletedAtUtc != default(DateTime) && probeStartedAtUtc != default(DateTime) ? Math.Max(0L, (long)(probeCompletedAtUtc - probeStartedAtUtc).TotalMilliseconds) : 0L,
                packageTimings = packageTimings.ToArray()
            };
            durableState = checkpoint;
            WriteTextAtomically(checkpointPath, JsonUtility.ToJson(checkpoint, true));
            WriteActiveRunPointer(state);
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
            packageTimings.Clear();
            if (previous.packageTimings != null) packageTimings.AddRange(previous.packageTimings);
            runId = previous.runId;
            runTimestamp = previous.runTimestamp;
            if (!string.IsNullOrEmpty(previous.outputDirectory)) outputDirectory = previous.outputDirectory;
            if (!string.IsNullOrEmpty(previous.checkpointPath)) checkpointPath = previous.checkpointPath;
            if (!string.IsNullOrEmpty(previous.outputPath)) outputPath = previous.outputPath;
            runState = string.IsNullOrEmpty(previous.runState) ? previous.state : previous.runState;
            corpusRoot = previous.corpusRoot;
            if (string.IsNullOrEmpty(outputPath)) outputPath = previous.outputPath;
            if (previous.requestedPackages != null && previous.requestedPackages.Length > 0)
                packagePaths = string.Join(";", previous.requestedPackages);
            if (previous.prefabFilter != null) prefabFilter = previous.prefabFilter;
            mergedCorpusMode = string.Equals(previous.observationContext, "MERGED_CORPUS", StringComparison.OrdinalIgnoreCase);
            baselineManifestPath = previous.baselineManifestPath;
            baselineStatus = string.IsNullOrEmpty(previous.baselineStatus) ? "UNKNOWN" : previous.baselineStatus;
            unexpectedAssetCount = previous.unexpectedAssetCount;
            finalizationPending = string.Equals(previous.runState, "WAITING_FOR_CLEANUP", StringComparison.OrdinalIgnoreCase) || string.Equals(previous.runState, "PENDING_CLEANUP", StringComparison.OrdinalIgnoreCase);
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
            packagePreview = packages.Length == 0
                ? "No .unitypackage files found."
                : packages.Length + " package(s) discovered. New Run creates a fresh timestamped run; explicit Resume uses only the active run pointer.";
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
            var completedTiming = active.TimingFor(active.pendingPackageCursor > 0 && active.pendingPackageCursor - 1 < active.pendingPackages.Count ? active.pendingPackages[active.pendingPackageCursor - 1] : active.currentPackage);
            completedTiming.packageCompletedAtUtc = KeepTimestamp(completedTiming.packageCompletedAtUtc, active.packageCompletedAtUtc.Value);
            active.currentPackage = active.pendingPackageCursor < active.pendingPackages.Count
                ? active.pendingPackages[active.pendingPackageCursor]
                : null;
            if (active.currentPackage != null)
            {
                active.packageStartedAtUtc = DateTime.UtcNow;
                active.importStartedAtUtc = active.packageStartedAtUtc;
                var nextTiming = active.TimingFor(active.currentPackage);
                nextTiming.packageStartedAtUtc = KeepTimestamp(nextTiming.packageStartedAtUtc, active.packageStartedAtUtc);
                nextTiming.importStartedAtUtc = KeepTimestamp(nextTiming.importStartedAtUtc, active.importStartedAtUtc);
            }
            active.currentPhase = active.currentPackage == null ? "WRITING_OUTPUT" : "IMPORT_REQUESTED";
            active.WriteCheckpoint("RUNNING", null);
        }

        private static void NotifyImportCompleted()
        {
            if (active == null) return;
            active.importCompletedAtUtc = DateTime.UtcNow;
            active.TimingFor(active.currentPackage).importCompletedAtUtc = KeepTimestamp(active.TimingFor(active.currentPackage).importCompletedAtUtc, active.importCompletedAtUtc);
            active.currentPhase = "IMPORT_COMPLETE";
            active.lastProgressAtUtc = active.importCompletedAtUtc;
            active.WriteCheckpoint("RUNNING", null);
        }

        private static void NotifyProbeStarted()
        {
            if (active == null) return;
            active.probeStartedAtUtc = DateTime.UtcNow;
            active.TimingFor(active.currentPackage).probeStartedAtUtc = KeepTimestamp(active.TimingFor(active.currentPackage).probeStartedAtUtc, active.probeStartedAtUtc);
            active.currentPhase = "PROBE_STARTED";
            active.lastProgressAtUtc = active.probeStartedAtUtc;
            active.WriteCheckpoint("RUNNING", null);
        }

        private static void NotifyProbeCompleted()
        {
            if (active == null) return;
            active.probeCompletedAtUtc = DateTime.UtcNow;
            active.TimingFor(active.currentPackage).probeCompletedAtUtc = KeepTimestamp(active.TimingFor(active.currentPackage).probeCompletedAtUtc, active.probeCompletedAtUtc);
            active.lastProgressAtUtc = active.probeCompletedAtUtc;
            active.currentPhase = "PROBE_COMPLETE";
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
            SemanticOracle.ImportCompletedCallback = null;
            SemanticOracle.ProbeStartedCallback = null;
            SemanticOracle.ProbeCompletedCallback = null;
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
