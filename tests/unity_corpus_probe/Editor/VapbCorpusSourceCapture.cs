// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

// Independent source observation. Identifiers and package paths stay private.
[InitializeOnLoad]
public static class VapbCorpusSourceCapture
{
    private const string Prefix = "VAPB_CORPUS_SOURCE_";
    [Serializable] private sealed class LifecycleRow
    {
        public string event_name;
        public double editor_seconds;
        public double elapsed_seconds;
        public string phase;
        public int package_index;
        public string callback_package_name;
        public string expected_package_name;
        public bool expected_match_known;
        public bool expected_match;
        public bool is_compiling;
        public bool is_updating;
        public bool compilation_error;
        public int compiler_error_count;
    }
    [Serializable] private sealed class Context
    {
        public string[] package_paths;
        public string[] prefab_guids;
        public int timeout_seconds = 300;
        public string capture_mode;
        public string staging_lock_path;
        public string native_import_status;
    }
    [Serializable] private sealed class StagedFile { public string unity_path; public string sha256; }
    [Serializable] private sealed class SourcePackage { public string path; public string sha256; }
    [Serializable] private sealed class StagingLock
    {
        public string schema;
        public string project_path;
        public SourcePackage[] source_packages;
        public StagedFile[] files;
        public string[] prefab_guids;
        public bool exact_asset_meta_bytes;
        public bool source_original_package_sha_preserved;
    }
    [Serializable] private sealed class Identity
    {
        public bool proven;
        public string guid;
        public string local_id;
        public string global_object_id;
    }
    [Serializable] private sealed class RendererRow
    {
        public string root_guid;
        public string type;
        public Identity renderer;
        public Identity owner;
        public Identity mesh;
        public Identity root_bone;
        public Identity[] bones;
        public Identity[] materials;
        public Identity[] source_chain;
        public Identity[] instance_roots;
        public int shape_channels;
        public int vertices;
    }
    [Serializable] private sealed class RootRow
    {
        public string guid;
        public bool loaded;
        public int missing_scripts;
        public RendererRow[] renderers;
    }
    [Serializable] private sealed class Result
    {
        public string schema = "vapb-corpus-source-1";
        public string scope = "INDEPENDENT_SOURCE_OBSERVATION_ONLY";
        public string verdict = "UNPROVEN";
        public string reason = "HARNESS_ERROR";
        public string detail_code = "NOT_RUN";
        public string unity_version;
        public bool source_population_complete;
        public int packages_requested;
        public int packages_imported;
        public int packages_extracted;
        public string capture_mode = "NATIVE_PACKAGE_IMPORT";
        public string native_import_status = "NOT_PASS";
        public bool source_original_package_sha_preserved;
        public int unrelated_package_events;
        public bool lifecycle_write_failed;
        public int roots_requested;
        public int roots_loaded;
        // -1 means unproven rather than an invented zero population.
        public int source_skin_count = -1;
        public int renderer_occurrence_count = -1;
        public int missing_script_count = -1;
        public RootRow[] roots;
    }

    static VapbCorpusSourceCapture()
    {
        AssetDatabase.importPackageCompleted += Completed;
        AssetDatabase.importPackageStarted += Started;
        AssetDatabase.importPackageFailed += Failed;
        AssetDatabase.importPackageCancelled += Cancelled;
        CompilationPipeline.assemblyCompilationFinished += CompilationFinished;
        EditorApplication.update += Update;
        AssemblyReloadEvents.beforeAssemblyReload += BeforeReload;
        Trace("DOMAIN_INITIALIZED");
    }

    public static void Run()
    {
        string result = Argument("--vapb-result");
        SessionState.SetString(Prefix + "result", result);
        try
        {
            string contextPath = Argument("--vapb-context");
            Context context = JsonUtility.FromJson<Context>(File.ReadAllText(contextPath));
            if (context == null || context.package_paths == null || context.package_paths.Length == 0 ||
                context.prefab_guids == null || context.prefab_guids.Length == 0)
                throw new InvalidOperationException("CONTEXT_INCOMPLETE");
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string guid in context.prefab_guids)
            {
                Guid parsed;
                if (guid == null || guid.Length != 32 || !Guid.TryParseExact(guid, "N", out parsed) || !seen.Add(guid))
                    throw new InvalidOperationException("PREFAB_GUID_INVALID_OR_DUPLICATE");
            }
            foreach (string package in context.package_paths)
                if (!Path.IsPathRooted(package) || !File.Exists(package))
                    throw new InvalidOperationException("PACKAGE_MISSING");
            if (!Path.IsPathRooted(result) || File.Exists(result))
                throw new InvalidOperationException("RESULT_PATH_INVALID_OR_EXISTS");
            SessionState.SetString(Prefix + "context", JsonUtility.ToJson(context));
            SessionState.SetInt(Prefix + "index", 0);
            SessionState.SetInt(Prefix + "unrelated_events", 0);
            SessionState.SetBool(Prefix + "compile_error", false);
            SessionState.SetFloat(Prefix + "started", (float)EditorApplication.timeSinceStartup);
            SessionState.SetFloat(Prefix + "heartbeat", (float)EditorApplication.timeSinceStartup);
            SessionState.SetBool(Prefix + "trace_failed", false);
            SessionState.SetBool(Prefix + "source_sha_preserved", false);
            SessionState.SetString(Prefix + "phase", "next");
            Trace("RUN_INITIALIZED");
            if (context.capture_mode == "EXACT_ASSET_EXTRACTION_CAPTURE")
            {
                ValidateStaging(context);
                SessionState.SetFloat(Prefix + "capture_started", (float)EditorApplication.timeSinceStartup);
                SessionState.SetString(Prefix + "phase", "capture");
                Trace("EXACT_ASSET_CAPTURE_READY");
            }
            else if (!String.IsNullOrEmpty(context.capture_mode) && context.capture_mode != "NATIVE_PACKAGE_IMPORT")
                throw new InvalidOperationException("CAPTURE_MODE_INVALID");
        }
        catch (Exception error) { Finish("UNPROVEN", "HARNESS_ERROR", SafeCode(error), null); }
    }

    private static string Argument(string key)
    {
        string[] args = Environment.GetCommandLineArgs();
        for (int i = 0; i + 1 < args.Length; i++) if (args[i] == key) return args[i + 1];
        return "";
    }
    private static Context Current()
    { return JsonUtility.FromJson<Context>(SessionState.GetString(Prefix + "context", "{}")); }
    private static void Completed(string unused)
    {
        Trace("IMPORT_COMPLETED", unused, true, ExpectedPackageEvent(unused));
        if (!ExpectedPackageEvent(unused))
        {
            if (SessionState.GetString(Prefix + "phase", "") == "importing")
                SessionState.SetInt(Prefix + "unrelated_events", SessionState.GetInt(Prefix + "unrelated_events", 0) + 1);
            return;
        }
        SessionState.SetInt(Prefix + "index", SessionState.GetInt(Prefix + "index", 0) + 1);
        SessionState.SetString(Prefix + "phase", "next");
        SessionState.SetInt(Prefix + "idle", 0);
        Trace("PHASE_NEXT");
    }
    private static void Started(string packageName)
    { Trace("IMPORT_STARTED", packageName, true, ExpectedPackageEvent(packageName)); }
    private static void BeforeReload()
    { Trace("DOMAIN_BEFORE_RELOAD"); }
    private static void Failed(string unused, string privateError)
    {
        Trace("IMPORT_FAILED", unused, true, ExpectedPackageEvent(unused));
        if (ExpectedPackageEvent(unused)) Finish("BLOCKED", "ENVIRONMENT_FAILURE", "PACKAGE_IMPORT_FAILED", null);
    }
    private static void Cancelled(string unused)
    {
        Trace("IMPORT_CANCELLED", unused, true, ExpectedPackageEvent(unused));
        if (ExpectedPackageEvent(unused)) Finish("BLOCKED", "ENVIRONMENT_FAILURE", "PACKAGE_IMPORT_CANCELLED", null);
    }
    private static bool ExpectedPackageEvent(string packageName)
    {
        if (SessionState.GetString(Prefix + "phase", "") != "importing") return false;
        Context context = Current();
        int index = SessionState.GetInt(Prefix + "index", 0);
        if (context.package_paths == null || index >= context.package_paths.Length) return false;
        return VapbCorpusPackageCallback.Matches(packageName, context.package_paths[index]);
    }
    private static void CompilationFinished(string unused, CompilerMessage[] messages)
    {
        if (String.IsNullOrEmpty(SessionState.GetString(Prefix + "phase", ""))) return;
        int errors = 0;
        foreach (CompilerMessage message in messages)
            if (message.type == CompilerMessageType.Error)
            { SessionState.SetBool(Prefix + "compile_error", true); errors++; }
        Trace("COMPILATION_FINISHED", compilerErrors: errors);
    }
    private static void Update()
    {
        string phase = SessionState.GetString(Prefix + "phase", "");
        if (String.IsNullOrEmpty(phase) || phase == "done") return;
        if (EditorApplication.timeSinceStartup - SessionState.GetFloat(Prefix + "heartbeat", 0) >= 30)
        {
            SessionState.SetFloat(Prefix + "heartbeat", (float)EditorApplication.timeSinceStartup);
            Trace("UPDATE_HEARTBEAT");
        }
        Context context = Current();
        if (EditorApplication.timeSinceStartup - SessionState.GetFloat(Prefix + "started", 0) >
            Math.Max(30, context.timeout_seconds))
        { Finish("BLOCKED", "TIMEOUT", "SOURCE_CAPTURE_TIMEOUT", null); return; }
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || phase == "importing") return;
        if (SessionState.GetBool(Prefix + "compile_error", false))
        { Finish("BLOCKED", "ENVIRONMENT_FAILURE", "IMPORTED_SCRIPT_COMPILE_ERROR", null); return; }
        if (phase != "next" && phase != "capture") return;
        int idle = SessionState.GetInt(Prefix + "idle", 0) + 1;
        SessionState.SetInt(Prefix + "idle", idle);
        if (idle < 10) return;
        SessionState.SetInt(Prefix + "idle", 0);
        int index = SessionState.GetInt(Prefix + "index", 0);
        try
        {
            if (phase == "capture")
            {
                bool ready = true;
                foreach (string guid in context.prefab_guids)
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    ready &= !String.IsNullOrEmpty(path) && AssetDatabase.LoadAssetAtPath<GameObject>(path) != null;
                }
                if (!ready && EditorApplication.timeSinceStartup - SessionState.GetFloat(Prefix + "capture_started", 0) < 10) return;
                SessionState.SetString(Prefix + "phase", "observing");
                Trace("OBSERVATION_STARTED");
                Observe(context);
                return;
            }
            if (index < context.package_paths.Length)
            {
                SessionState.SetString(Prefix + "phase", "importing");
                Trace("IMPORT_REQUESTED");
                AssetDatabase.ImportPackage(context.package_paths[index], false);
            }
            else
            {
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                SessionState.SetFloat(Prefix + "capture_started", (float)EditorApplication.timeSinceStartup);
                SessionState.SetString(Prefix + "phase", "capture");
                Trace("PHASE_CAPTURE");
            }
        }
        catch (Exception error) { Finish("UNPROVEN", "HARNESS_ERROR", SafeCode(error), null); }
    }
    private static void Observe(Context context)
    {
        if (context.capture_mode == "EXACT_ASSET_EXTRACTION_CAPTURE") ValidateStaging(context);
        var roots = new List<RootRow>();
        var report = new Result { unity_version = Application.unityVersion, source_skin_count = 0,
            renderer_occurrence_count = 0, missing_script_count = 0 };
        foreach (string guid in context.prefab_guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            var row = new RootRow { guid = guid, renderers = new RendererRow[0] };
            roots.Add(row);
            if (String.IsNullOrEmpty(path) || !path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase)) continue;
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (root == null || AssetDatabase.AssetPathToGUID(path) != guid) continue;
            row.loaded = true;
            report.roots_loaded++;
            var renderers = new List<RendererRow>();
            foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
            {
                row.missing_scripts += GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject);
                foreach (Renderer renderer in transform.GetComponents<Renderer>())
                {
                    Mesh mesh = null;
                    var item = new RendererRow { root_guid = guid, renderer = Id(renderer), owner = Id(renderer.gameObject),
                        type = renderer is SkinnedMeshRenderer ? "SKINNED" : renderer is MeshRenderer ? "MESH" : "OTHER",
                        materials = Ids(renderer.sharedMaterials), source_chain = SourceChain(renderer),
                        instance_roots = InstanceRoots(transform), bones = new Identity[0] };
                    var skin = renderer as SkinnedMeshRenderer;
                    if (skin != null)
                    {
                        mesh = skin.sharedMesh;
                        item.bones = Ids(skin.bones);
                        item.root_bone = Id(skin.rootBone);
                        report.source_skin_count++;
                    }
                    else
                    {
                        var filters = renderer.GetComponents<MeshFilter>();
                        if (filters.Length == 1) mesh = filters[0].sharedMesh;
                    }
                    item.mesh = Id(mesh);
                    item.shape_channels = mesh == null ? -1 : mesh.blendShapeCount;
                    item.vertices = mesh == null ? -1 : mesh.vertexCount;
                    renderers.Add(item);
                    report.renderer_occurrence_count++;
                }
            }
            row.renderers = renderers.ToArray();
            report.missing_script_count += row.missing_scripts;
        }
        report.roots = roots.ToArray();
        report.source_population_complete = report.roots_loaded == context.prefab_guids.Length;
        if (!report.source_population_complete)
        {
            report.source_skin_count = -1;
            report.renderer_occurrence_count = -1;
            report.missing_script_count = -1;
        }
        Finish(report.source_population_complete ? "PASS" : "UNPROVEN",
            report.source_population_complete ? "NONE" : "HARNESS_UNSUPPORTED",
            report.source_population_complete ? "SOURCE_OBSERVATION_COMPLETE" : "REQUESTED_PREFAB_NOT_LOADED", report);
    }
    private static Identity Id(UnityEngine.Object value)
    {
        if (value == null) return null;
        string guid; long local;
        bool exact = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out guid, out local);
        var global = GlobalObjectId.GetGlobalObjectIdSlow(value);
        return new Identity { proven = exact && !String.IsNullOrEmpty(guid) && local != 0,
            guid = exact ? guid : "", local_id = exact ? local.ToString(CultureInfo.InvariantCulture) : "",
            global_object_id = global.ToString() };
    }
    private static Identity[] Ids(UnityEngine.Object[] values)
    {
        var result = new Identity[values.Length];
        for (int i = 0; i < values.Length; i++) result[i] = Id(values[i]);
        return result;
    }
    private static Identity[] SourceChain(UnityEngine.Object value)
    {
        var result = new List<Identity>();
        var seen = new HashSet<UnityEngine.Object>();
        while (value != null && seen.Add(value))
        {
            value = PrefabUtility.GetCorrespondingObjectFromSource(value);
            if (value != null) result.Add(Id(value));
        }
        return result.ToArray();
    }
    private static Identity[] InstanceRoots(Transform transform)
    {
        var result = new List<Identity>();
        for (Transform current = transform; current != null; current = current.parent)
            if (PrefabUtility.IsAnyPrefabInstanceRoot(current.gameObject)) result.Add(Id(current.gameObject));
        result.Reverse();
        return result.ToArray();
    }
    private static string SafeCode(Exception error)
    { return error is InvalidOperationException ? error.Message : "SOURCE_CAPTURE_EXCEPTION"; }
    private static string HashFile(string path)
    {
        using (var stream = File.OpenRead(path))
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }
    private static StagingLock ValidateStaging(Context context)
    {
        if (context.native_import_status != "NOT_PASS" || String.IsNullOrEmpty(context.staging_lock_path))
            throw new InvalidOperationException("EXACT_STAGING_LOCK_REQUIRED");
        var stage = JsonUtility.FromJson<StagingLock>(File.ReadAllText(context.staging_lock_path));
        string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        if (stage == null || stage.schema != "vapb-source-asset-staging-1" ||
            !stage.exact_asset_meta_bytes || !stage.source_original_package_sha_preserved ||
            !String.Equals(Path.GetFullPath(stage.project_path), project, StringComparison.OrdinalIgnoreCase) ||
            stage.source_packages == null || stage.files == null || stage.files.Length == 0 ||
            stage.source_packages.Length != context.package_paths.Length || stage.prefab_guids == null ||
            stage.prefab_guids.Length != context.prefab_guids.Length)
            throw new InvalidOperationException("EXACT_STAGING_LOCK_INVALID");
        for (int i = 0; i < stage.source_packages.Length; i++)
            if (!String.Equals(Path.GetFullPath(stage.source_packages[i].path), Path.GetFullPath(context.package_paths[i]), StringComparison.OrdinalIgnoreCase) ||
                HashFile(stage.source_packages[i].path) != stage.source_packages[i].sha256)
                throw new InvalidOperationException("SOURCE_ORIGINAL_SHA_MISMATCH");
        SessionState.SetBool(Prefix + "source_sha_preserved", true);
        var roots = new HashSet<string>(stage.prefab_guids, StringComparer.OrdinalIgnoreCase);
        if (roots.Count != context.prefab_guids.Length) throw new InvalidOperationException("STAGING_ROOT_SET_MISMATCH");
        foreach (string guid in context.prefab_guids)
            if (!roots.Contains(guid)) throw new InvalidOperationException("STAGING_ROOT_SET_MISMATCH");
        string assets = Path.GetFullPath(Application.dataPath) + Path.DirectorySeparatorChar;
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (StagedFile file in stage.files)
        {
            if (file == null || String.IsNullOrEmpty(file.unity_path) || !file.unity_path.StartsWith("Assets/", StringComparison.Ordinal) ||
                file.unity_path.Contains("\\") || Array.Exists(file.unity_path.Split('/'), part => part == "." || part == ".." || part == ""))
                throw new InvalidOperationException("STAGING_PATH_INVALID");
            string destination = Path.GetFullPath(Path.Combine(project, file.unity_path));
            if (!destination.StartsWith(assets, StringComparison.OrdinalIgnoreCase) || !seen.Add(destination) ||
                HashFile(destination) != file.sha256)
                throw new InvalidOperationException("STAGED_ASSET_OR_META_CHANGED");
        }
        return stage;
    }
    private static void Trace(string eventName, string callbackPackage = "", bool matchKnown = false,
                              bool expectedMatch = false, int compilerErrors = 0)
    {
        string output = SessionState.GetString(Prefix + "result", "");
        string phase = SessionState.GetString(Prefix + "phase", "");
        if (String.IsNullOrEmpty(output) || String.IsNullOrEmpty(phase)) return;
        try
        {
            Context context = Current();
            int index = SessionState.GetInt(Prefix + "index", 0);
            string expected = context.package_paths != null && index < context.package_paths.Length
                ? Path.GetFileNameWithoutExtension(context.package_paths[index]) : "";
            var row = new LifecycleRow { event_name = eventName,
                editor_seconds = EditorApplication.timeSinceStartup,
                elapsed_seconds = EditorApplication.timeSinceStartup - SessionState.GetFloat(Prefix + "started", 0),
                phase = phase, package_index = index, callback_package_name = callbackPackage,
                expected_package_name = expected, expected_match_known = matchKnown,
                expected_match = expectedMatch, is_compiling = EditorApplication.isCompiling,
                is_updating = EditorApplication.isUpdating,
                compilation_error = SessionState.GetBool(Prefix + "compile_error", false),
                compiler_error_count = compilerErrors };
            File.AppendAllText(Path.ChangeExtension(output, ".lifecycle.jsonl"), JsonUtility.ToJson(row) + "\n");
        }
        catch { SessionState.SetBool(Prefix + "trace_failed", true); }
    }
    private static void Finish(string verdict, string reason, string detail, Result report)
    {
        Trace("FINISH");
        SessionState.SetString(Prefix + "phase", "done");
        if (report == null) report = new Result();
        Context context = Current();
        report.unity_version = Application.unityVersion;
        report.packages_requested = context.package_paths == null ? 0 : context.package_paths.Length;
        report.packages_imported = SessionState.GetInt(Prefix + "index", 0);
        if (context.capture_mode == "EXACT_ASSET_EXTRACTION_CAPTURE")
        {
            report.capture_mode = context.capture_mode;
            report.native_import_status = context.native_import_status;
            try
            {
                StagingLock stage = ValidateStaging(context);
                report.packages_extracted = stage.source_packages.Length;
                report.source_original_package_sha_preserved = true;
            }
            catch
            {
                report.source_population_complete = false;
                report.source_skin_count = -1;
                report.renderer_occurrence_count = -1;
                report.missing_script_count = -1;
                verdict = "UNPROVEN"; reason = "HARNESS_ERROR";
                if (detail == "SOURCE_OBSERVATION_COMPLETE") detail = "EXACT_STAGING_VALIDATION_FAILED";
            }
            report.source_original_package_sha_preserved = SessionState.GetBool(Prefix + "source_sha_preserved", false);
        }
        else
            report.native_import_status = report.source_population_complete && report.packages_imported == report.packages_requested ? "PASS" : "NOT_PASS";
        report.unrelated_package_events = SessionState.GetInt(Prefix + "unrelated_events", 0);
        report.lifecycle_write_failed = SessionState.GetBool(Prefix + "trace_failed", false);
        report.roots_requested = context.prefab_guids == null ? 0 : context.prefab_guids.Length;
        report.verdict = verdict; report.reason = reason; report.detail_code = detail;
        string output = SessionState.GetString(Prefix + "result", "");
        if (!String.IsNullOrEmpty(output) && !File.Exists(output))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            File.WriteAllText(output, JsonUtility.ToJson(report, true));
        }
        Debug.Log("CORPUS_SOURCE verdict=" + verdict + " reason=" + reason +
                  " roots=" + report.roots_loaded + " skins=" + (report.source_skin_count < 0 ? "UNKNOWN" : report.source_skin_count.ToString()));
        EditorApplication.Exit(verdict == "PASS" ? 0 : 1);
    }
}
