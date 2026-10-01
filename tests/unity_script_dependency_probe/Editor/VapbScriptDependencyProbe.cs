using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Public first-party fixtures only. Reports contain enums, counts and booleans.
public static class VapbScriptDependencyProbe
{
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    [Serializable] private sealed class RequiredBy { public string asset_guid; public string asset_sha256; public string component_file_id; }
    [Serializable] private sealed class Dependency
    {
        public string classification; public string kind; public string reference_id;
        public string guid; public string file_id; public string status; public RequiredBy[] required_by;
    }
    [Serializable] private sealed class InstanceEdge { public string container_guid; }
    [Serializable] private sealed class Task { public string prefab_guid; public string source_model_guid; public string variant_path; public InstanceEdge[] instance_edges; }
    [Serializable] private sealed class Manifest { public Dependency[] external_dependencies; public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Report
    {
        public string result; public string rejection; public int missing_scripts; public int declared_references;
        public bool first_apply; public bool repeated_apply; public bool exact_provider;
        public bool source_unchanged; public bool manifest_unchanged; public bool variant_absent; public bool controls_variant_unchanged;
        public bool variant_unchanged_on_rejection;
        public bool malformed_guid_red; public bool malformed_file_id_red;
        public bool wrong_file_id_red; public bool duplicate_conflict_red;
        public bool stale_required_by_red; public bool unrelated_prefab_red;
    }
    private static string rejection;

    public static void InstallProvider() { InstallPublicProvider("1234567890abcdef1234567890abcdef"); }
    public static void InstallWrongGuidProvider() { InstallPublicProvider("abcdef1234567890abcdef1234567890"); }
    private static void InstallPublicProvider(string guid)
    {
        string folder = Path.Combine(Application.dataPath, "PublicProvider");
        Directory.CreateDirectory(folder);
        string path = Path.Combine(folder, "PublicExternalDependencyMarker.cs");
        File.WriteAllText(path, "// SPDX-License-Identifier: MIT\nusing UnityEngine;\npublic sealed class PublicExternalDependencyMarker : MonoBehaviour { }\n");
        File.WriteAllText(path + ".meta", "fileFormatVersion: 2\nguid: " + guid + "\nMonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n");
        // The next editor launch imports and compiles this separate provider.
        EditorApplication.Exit(0);
    }

    public static void Run()
    {
        var report = new Report { result = "UNEXPECTED_EXCEPTION" };
        try
        {
            string original = File.ReadAllText(Disk(ManifestPath));
            Manifest manifest = JsonUtility.FromJson<Manifest>(original);
            Task task = manifest.reference_rebind_tasks[0];
            string prefab = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            var sourceHashes = new Dictionary<string, string>();
            Capture(sourceHashes, prefab);
            Capture(sourceHashes, AssetDatabase.GUIDToAssetPath(task.source_model_guid));
            if (task.instance_edges != null) foreach (InstanceEdge edge in task.instance_edges)
                Capture(sourceHashes, AssetDatabase.GUIDToAssetPath(edge.container_guid));
            report.declared_references = manifest.external_dependencies == null ? 0 : manifest.external_dependencies.Length;
            report.missing_scripts = Missing(AssetDatabase.LoadAssetAtPath<GameObject>(prefab));
            string variantBefore = File.Exists(Disk(task.variant_path)) ? Hash(File.ReadAllBytes(Disk(task.variant_path))) : "ABSENT";
            report.exact_provider = report.declared_references > 0;
            if (manifest.external_dependencies != null)
                foreach (Dependency dependency in manifest.external_dependencies)
                    report.exact_provider &= Resolves(dependency);
            report.first_apply = Apply();
            report.rejection = rejection;
            report.variant_absent = !File.Exists(Disk(task.variant_path));
            if (!report.first_apply) report.variant_unchanged_on_rejection = variantBefore ==
                (report.variant_absent ? "ABSENT" : Hash(File.ReadAllBytes(Disk(task.variant_path))));
            if (report.first_apply) report.repeated_apply = Apply();
            if (report.exact_provider && report.first_apply && report.declared_references == 1)
            {
                string variantHash = Hash(File.ReadAllBytes(Disk(task.variant_path)));
                Dependency entry = manifest.external_dependencies[0];
                report.malformed_guid_red = Control(original, entry, d => d.guid = "malformed", "EXTERNAL_DEPENDENCY_INVALID");
                report.malformed_file_id_red = Control(original, entry, d => d.file_id = "+11500000", "EXTERNAL_DEPENDENCY_INVALID");
                report.wrong_file_id_red = Control(original, entry, d => {
                    d.file_id = "-11500000"; d.reference_id = ReferenceId(d.guid, d.file_id);
                }, "EXTERNAL_DEPENDENCY_INVALID");
                report.stale_required_by_red = Control(original, entry,
                    d => d.required_by[0].asset_sha256 = new string('0', 64), "EXTERNAL_DEPENDENCY_INVALID");
                report.unrelated_prefab_red = Control(original, entry,
                    d => d.required_by[0].asset_guid = new string('e', 32), "EXTERNAL_DEPENDENCY_INVALID");
                Dependency conflict = Clone(entry);
                conflict.status = "RESOLVED_IN_UNITY";
                Write(WithDependencies(original, new[] { entry, conflict }));
                report.duplicate_conflict_red = !Apply() && rejection == "EXTERNAL_DEPENDENCY_INVALID";
                Write(original);
                report.controls_variant_unchanged = variantHash == Hash(File.ReadAllBytes(Disk(task.variant_path)));
            }
            report.source_unchanged = true;
            foreach (var source in sourceHashes)
                report.source_unchanged &= source.Value == Hash(File.ReadAllBytes(Disk(source.Key)));
            report.manifest_unchanged = original == File.ReadAllText(Disk(ManifestPath));
            report.result = report.first_apply ? "APPLY_PASS" : report.rejection;
        }
        catch { report.result = "PROBE_FAILED"; }
        File.WriteAllText(Path.Combine(Application.dataPath, "../script_dependency_report.json"), JsonUtility.ToJson(report, true));
        EditorApplication.Exit(report.result == "PROBE_FAILED" || report.result == "UNEXPECTED_EXCEPTION" ? 1 : 0);
    }
    private static bool Control(string original, Dependency entry, Action<Dependency> edit, string expected)
    {
        Dependency changed = Clone(entry); edit(changed);
        try { Write(WithDependencies(original, new[] { changed })); return !Apply() && rejection == expected; }
        finally { Write(original); }
    }
    private static Dependency Clone(Dependency entry) { return JsonUtility.FromJson<Dependency>(JsonUtility.ToJson(entry)); }
    private static void Capture(Dictionary<string, string> hashes, string path)
    { if (!String.IsNullOrEmpty(path)) hashes[path] = Hash(File.ReadAllBytes(Disk(path))); }
    private static string WithDependencies(string original, Dependency[] entries)
    {
        Match property = Regex.Match(original, "\"external_dependencies\"\\s*:\\s*\\[");
        if (!property.Success) throw new InvalidOperationException();
        int start = original.IndexOf('[', property.Index), depth = 0, end = start;
        for (; end < original.Length; end++) { if (original[end] == '[') depth++; else if (original[end] == ']' && --depth == 0) break; }
        string replacement = "[";
        for (int i = 0; i < entries.Length; i++) replacement += (i == 0 ? "" : ",") + JsonUtility.ToJson(entries[i]);
        return original.Substring(0, start) + replacement + "]" + original.Substring(end + 1);
    }
    private static void Write(string json) { File.WriteAllText(Disk(ManifestPath), json); AssetDatabase.ImportAsset(ManifestPath, ImportAssetOptions.ForceUpdate); }
    private static bool Apply()
    {
        rejection = ""; Application.logMessageReceived += OnLog;
        try { return VapbModelSkinFinalizer.Apply(ManifestPath); }
        finally { Application.logMessageReceived -= OnLog; }
    }
    private static void OnLog(string message, string stack, LogType type)
    { const string prefix = "VAPB_MODEL_SKIN_VARIANT_REJECTED="; if (message.StartsWith(prefix, StringComparison.Ordinal)) rejection = message.Substring(prefix.Length); }
    private static bool Resolves(Dependency d)
    {
        string path = AssetDatabase.GUIDToAssetPath(d.guid);
        if (String.IsNullOrEmpty(path)) return false;
        foreach (UnityEngine.Object item in AssetDatabase.LoadAllAssetsAtPath(path))
            if (item is MonoScript && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(item, out string guid, out long id) &&
                guid == d.guid && id.ToString(System.Globalization.CultureInfo.InvariantCulture) == d.file_id) return true;
        return false;
    }
    private static int Missing(GameObject prefab)
    { int count = 0; if (prefab == null) return -1; foreach (Transform t in prefab.GetComponentsInChildren<Transform>(true)) count += GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject); return count; }
    private static string ReferenceId(string guid, string id) { return "VAPB-REF-" + Hash(Encoding.UTF8.GetBytes("UNITY_SCRIPT:" + guid + ":" + id)).Substring(0, 32); }
    private static string Hash(byte[] bytes) { using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    private static string Disk(string path) { return Path.Combine(Application.dataPath, path.Substring(7)); }
}
