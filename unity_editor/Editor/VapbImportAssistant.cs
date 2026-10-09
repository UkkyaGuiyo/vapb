// SPDX-License-Identifier: MIT
// Copyright (c) 2026 UkkyaGuiyo and VAPB contributors
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

// Detection and presentation only. Providers retain their own strict validators
// and restoration code; this class never imports, repairs, or saves an Asset.
public sealed class VapbImportAssistant : EditorWindow
{
    public sealed class Inspection
    {
        public string target, output, changes, warning;
        public int count;
        public bool partial;
    }
    private sealed class Provider
    {
        public Func<string, Inspection> inspect;
        public Func<string, bool> apply;
        public Func<bool> partialResult;
    }
    [Serializable] private sealed class Manifest { public string schema_version; public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task { public string kind; }
    private sealed class Entry
    {
        public string path, identity, error;
        public Inspection inspection;
        public Provider provider;
        public bool details, recognized;
    }
    private static readonly Dictionary<string, Provider> providers = new Dictionary<string, Provider>();
    private readonly List<Entry> entries = new List<Entry>();
    private static bool pending;
    private static double stableSince;
    private Vector2 scroll;
    private static string StatePath { get { return Path.Combine(Directory.GetParent(Application.dataPath).FullName,
        "Library", "VapbApplyAssistant.state"); } }

    public static void Register(string kind, Func<string, Inspection> inspect, Func<string, bool> apply, Func<bool> partialResult = null)
    {
        providers[kind] = new Provider { inspect = inspect, apply = apply, partialResult = partialResult };
        Schedule();
    }
    [InitializeOnLoadMethod]
    private static void Initialize()
    {
        if (Application.isBatchMode || AssetDatabase.IsAssetImportWorkerProcess()) return;
        EditorApplication.projectChanged -= Schedule;
        EditorApplication.projectChanged += Schedule;
        Schedule();
    }
    private static void Schedule()
    {
        if (Application.isBatchMode || AssetDatabase.IsAssetImportWorkerProcess()) return;
        stableSince = EditorApplication.timeSinceStartup;
        if (pending) return;
        pending = true;
        EditorApplication.update += WaitForStableEditor;
    }
    private static void WaitForStableEditor()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode)
        { stableSince = EditorApplication.timeSinceStartup; return; }
        if (EditorApplication.timeSinceStartup - stableSince < 1) return;
        pending = false;
        EditorApplication.update -= WaitForStableEditor;
        Open(false, null);
    }
    [MenuItem("Tools/VAPB/編集内容を確認")]
    private static void OpenManually() { Open(true, null); }
    public static void Show(string path) { Open(true, path); }

    private static Entry Inspect(string path)
    {
        var entry = new Entry { path = path };
        try
        {
            TextAsset asset = AssetDatabase.LoadAssetAtPath<TextAsset>(path);
            if (asset == null) throw new InvalidOperationException("MANIFEST_UNAVAILABLE");
            using (var sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(path + "\n" + asset.text));
                entry.identity = BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
            Manifest manifest = JsonUtility.FromJson<Manifest>(asset.text);
            if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
                manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length == 0)
                throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
            entry.recognized = true;
            foreach (Task task in manifest.reference_rebind_tasks)
            {
                if (task == null || task.kind == null || !providers.TryGetValue(task.kind, out Provider provider) ||
                    (entry.provider != null && entry.provider.inspect != provider.inspect))
                    throw new InvalidOperationException("TASK_UNSUPPORTED");
                entry.provider = provider;
            }
            entry.inspection = entry.provider.inspect(path);
        }
        catch (Exception error) { entry.error = error.Message; }
        return entry;
    }
    private static void Remember(Entry entry, string state)
    {
        if (entry.identity == null) return;
        // Library is project-local and not an Asset. Asset bytes stay unchanged on cancel.
        var lines = File.Exists(StatePath) ? new List<string>(File.ReadAllLines(StatePath)) : new List<string>();
        lines.RemoveAll(line => line.StartsWith(entry.identity + " ", StringComparison.Ordinal));
        lines.Add(entry.identity + " " + state);
        Directory.CreateDirectory(Path.GetDirectoryName(StatePath));
        File.WriteAllLines(StatePath, lines.ToArray());
    }
    private static void Open(bool manual, string selected)
    {
        if (Application.isBatchMode || AssetDatabase.IsAssetImportWorkerProcess() ||
            EditorApplication.isCompiling || EditorApplication.isUpdating) return;
        var found = new List<Entry>();
        var remembered = new HashSet<string>();
        try
        {
            if (File.Exists(StatePath)) foreach (string line in File.ReadAllLines(StatePath))
                remembered.Add(line.Split(' ')[0]);
            var paths = new List<string>();
            if (selected != null) paths.Add(selected);
            else if (AssetDatabase.IsValidFolder("Assets/VAPBExport"))
                foreach (string guid in AssetDatabase.FindAssets("t:TextAsset", new[] { "Assets/VAPBExport" }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    if (path.EndsWith(".json", StringComparison.OrdinalIgnoreCase)) paths.Add(path);
                }
            paths.Sort(StringComparer.Ordinal);
            foreach (string path in paths)
            {
                Entry entry = Inspect(path);
                // Other JSON files aren't VAPB export manifests.
                if (selected == null && !entry.recognized) continue;
                if (!manual && remembered.Contains(entry.identity ?? "")) continue;
                Remember(entry, "prompted");
                found.Add(entry);
            }
        }
        catch (Exception error)
        { Debug.LogWarning("VAPB_ASSISTANT_STATE_UNAVAILABLE=" + error.GetType().Name); return; }
        if (found.Count == 0)
        {
            if (manual) EditorUtility.DisplayDialog("VAPB", "確認する編集データがありません。Unity用PackageをImportしてください。", "閉じる");
            return;
        }
        var window = GetWindow<VapbImportAssistant>(true, "VAPB：編集内容を確認", true);
        window.entries.Clear(); window.entries.AddRange(found);
        window.minSize = new Vector2(520, 400);
        window.Show();
    }
    private static string Reason(string error)
    {
        if (error == null) return "";
        if (error.Contains("HASH") || error.Contains("STALE") || error.Contains("REVISION"))
            return "原本または編集データの版が一致しません。対象のPackageを確認してください。";
        if (error.Contains("OCCUPIED") || error.Contains("ALREADY")) return "保存先が別の内容で使用されています。上書きは行いません。";
        if (error.Contains("DEPENDENCY") || error.Contains("MISSING_SCRIPT")) return "必要な外部依存またはScriptが不足しています。指定された依存を導入後、再確認してください。";
        if (error.Contains("MATERIAL") || error.Contains("TEXTURE")) return "素材の対応を確認できません。名前から推測して割り当てません。";
        if (error.Contains("UNAVAILABLE") || error.Contains("NOT_FOUND")) return "必要な対象Assetが見つかりません。PackageのImport結果を確認してください。";
        return "この編集データの構造または参照は確認できませんでした。詳細を確認し、対応する経路で書き出してください。";
    }
    private void OnGUI()
    {
        EditorGUILayout.HelpBox("原本を保持し、確認した編集内容だけを適用します。適用時にも既存Finalizerが出所・参照を再検証します。", MessageType.Info);
        scroll = EditorGUILayout.BeginScrollView(scroll);
        foreach (Entry entry in entries)
        {
            EditorGUILayout.BeginVertical("box");
            Inspection view = entry.inspection;
            EditorGUILayout.LabelField(entry.error != null ? "適用不可" : view.partial ? "部分対応" : "適用可能（事前確認済み）", EditorStyles.boldLabel);
            if (entry.error != null) EditorGUILayout.HelpBox(Reason(entry.error), MessageType.Error);
            else
            {
                EditorGUILayout.LabelField("対象", view.target, EditorStyles.wordWrappedLabel);
                EditorGUILayout.LabelField("更新予定", view.count + " Mesh/Skin", EditorStyles.wordWrappedLabel);
                EditorGUILayout.LabelField("保存先", view.output, EditorStyles.wordWrappedLabel);
                EditorGUILayout.HelpBox(view.changes, MessageType.Info);
                if (!String.IsNullOrEmpty(view.warning)) EditorGUILayout.HelpBox(view.warning, MessageType.Warning);
            }
            entry.details = EditorGUILayout.Foldout(entry.details, "詳細");
            if (entry.details)
            {
                EditorGUILayout.SelectableLabel(entry.path, GUILayout.Height(35));
                if (entry.error != null) EditorGUILayout.SelectableLabel(entry.error, GUILayout.Height(35));
            }
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("再確認"))
            {
                Entry refreshed = Inspect(entry.path);
                entry.identity = refreshed.identity; entry.provider = refreshed.provider;
                entry.inspection = refreshed.inspection; entry.error = refreshed.error;
            }
            using (new EditorGUI.DisabledScope(entry.error != null || view == null || EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode))
                if (GUILayout.Button("適用")) ApplyEntry(entry);
            if (GUILayout.Button("キャンセル"))
            {
                try { Remember(entry, "cancelled"); } catch (Exception error) { Debug.LogWarning(error.GetType().Name); }
                Close(); GUIUtility.ExitGUI();
            }
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.EndVertical();
        }
        EditorGUILayout.EndScrollView();
    }
    private void ApplyEntry(Entry entry)
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode) return;
        Entry fresh = Inspect(entry.path);
        if (fresh.error != null || fresh.identity != entry.identity)
        {
            entry.error = fresh.error ?? "MANIFEST_CHANGED";
            EditorUtility.DisplayDialog("VAPB：再確認が必要です", Reason(entry.error), "閉じる"); return;
        }
        bool complete = fresh.provider.apply(fresh.path);
        bool partial = !complete && fresh.provider.partialResult != null && fresh.provider.partialResult();
        if (complete || partial)
        {
            GameObject output = AssetDatabase.LoadAssetAtPath<GameObject>(fresh.inspection.output);
            if (output != null) { Selection.activeObject = output; EditorGUIUtility.PingObject(output); }
            try { Remember(fresh, "applied"); } catch (Exception error) { Debug.LogWarning(error.GetType().Name); }
        }
        EditorUtility.DisplayDialog("VAPB：適用結果", complete ? "適用が完了しました。出力Prefabを開いて確認してください。" :
            partial ? "部分対応：Prefabを生成しました。外部依存の解決が必要です。" :
            "適用できませんでした。Consoleの理由を確認してください。", "閉じる");
    }
}
