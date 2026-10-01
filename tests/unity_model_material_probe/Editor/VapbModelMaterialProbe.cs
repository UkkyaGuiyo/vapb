using System;
using System.IO;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbModelMaterialProbe
{
    private const string Phase = "VAPB_PUBLIC_MATERIAL_IMPORT";
    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task { public string model_guid; public string prefab_guid; public string variant_path; public Binding[] material_bindings; }
    [Serializable] private sealed class Binding { public string transport_id, guid, file_id; }
    [Serializable] private sealed class MaterialReference { public string guid; public string file_id; }
    [Serializable] private sealed class BlenderReport { public MaterialReference[] current_material_refs; public int[] blender_triangle_slot_counts; }
    [Serializable] private sealed class Report
    {
        public string result; public int[] imported_triangle_slot_counts; public int imported_model_material_slots;
        public int original_material_slots; public int variant_material_slots;
        public bool material_array_preserved; public bool first_apply; public bool repeated_apply;
        public bool material_array_matches_blender; public bool native_material_association_correct;
        public bool wrong_label_refused, wrong_guid_refused, wrong_local_id_refused, controls_no_variant, source_assets_unchanged, native_transport_labels_exact;
        public string[] native_transport_labels; public MaterialReference[] actual_material_refs;
    }
    static VapbModelMaterialProbe()
    {
        AssetDatabase.importPackageCompleted += Complete;
        if (SessionState.GetString(Phase, "") == "complete") EditorApplication.delayCall += Capture;
    }
    public static void Import()
    { SessionState.SetString(Phase, "importing"); AssetDatabase.ImportPackage(Argument("-vapbPublicPackage"), false); }
    private static void Complete(string name)
    { if (SessionState.GetString(Phase, "") == "importing") { SessionState.SetString(Phase, "complete"); EditorApplication.delayCall += Capture; } }
    private static void Capture()
    {
        SessionState.SetString(Phase, "done");
        var report = new Report { result = "PROBE_FAILED" };
        try
        {
            const string path = "Assets/VAPBExport/manifest.json";
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Application.dataPath, "VAPBExport/manifest.json")));
            Task task = manifest.reference_rebind_tasks[0];
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
            SkinnedMeshRenderer[] skins = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (skins.Length != 1) throw new InvalidOperationException();
            Mesh mesh = skins[0].sharedMesh;
            report.imported_triangle_slot_counts = new int[mesh.subMeshCount];
            for (int i = 0; i < mesh.subMeshCount; i++) report.imported_triangle_slot_counts[i] = (int)mesh.GetIndexCount(i) / 3;
            report.imported_model_material_slots = skins[0].sharedMaterials.Length;
            string disk = Path.Combine(Application.dataPath, "VAPBExport/manifest.json");
            string raw = File.ReadAllText(disk);
            var sourceHashes = SnapshotSource();
            report.controls_no_variant = !File.Exists(Disk(task.variant_path));
            report.wrong_label_refused = Negative(raw, disk, path, task.variant_path, "transport_id", "VAPB-MAT-00000000000000000000000000000000", null);
            report.controls_no_variant &= !File.Exists(Disk(task.variant_path));
            string wrongGuid = "ffffffffffffffffffffffffffffffff";
            report.wrong_guid_refused = Negative(raw, disk, path, task.variant_path, "guid", wrongGuid, Label(wrongGuid, task.material_bindings[0].file_id));
            report.controls_no_variant &= !File.Exists(Disk(task.variant_path));
            report.wrong_local_id_refused = Negative(raw, disk, path, task.variant_path, "file_id", "-2100000", Label(task.material_bindings[0].guid, "-2100000"));
            report.controls_no_variant &= !File.Exists(Disk(task.variant_path));
            report.native_transport_labels = Array.ConvertAll(skins[0].sharedMaterials, m => m.name);
            report.native_transport_labels_exact = true;
            foreach (string label in report.native_transport_labels) report.native_transport_labels_exact &= Array.Exists(task.material_bindings, b => b.transport_id == label);
            report.first_apply = Apply(path);
            if (report.first_apply)
            {
                report.repeated_apply = Apply(path);
                GameObject variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
                SkinnedMeshRenderer selected = null;
                foreach (SkinnedMeshRenderer skin in variant.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (skin.sharedMesh != null && AssetDatabase.GetAssetPath(skin.sharedMesh) == AssetDatabase.GUIDToAssetPath(task.model_guid)) selected = skin;
                SkinnedMeshRenderer original = PrefabUtility.GetCorrespondingObjectFromSource(selected);
                Material[] before = original.sharedMaterials, after = selected.sharedMaterials;
                report.original_material_slots = before.Length; report.variant_material_slots = after.Length;
                report.material_array_preserved = before.Length == after.Length;
                for (int i = 0; i < before.Length && report.material_array_preserved; i++) report.material_array_preserved &= before[i] == after[i];
                string expectation = Argument("-vapbPublicExpectation");
                if (File.Exists(expectation))
                {
                    BlenderReport blender = JsonUtility.FromJson<BlenderReport>(File.ReadAllText(expectation));
                    report.actual_material_refs = new MaterialReference[after.Length];
                    report.material_array_matches_blender = after.Length == blender.current_material_refs.Length;
                    report.native_material_association_correct = after.Length == 3;
                    for (int i = 0; i < after.Length; i++)
                    {
                        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(after[i], out string guid, out long id)) throw new InvalidOperationException();
                        report.actual_material_refs[i] = new MaterialReference { guid = guid, file_id = id.ToString(System.Globalization.CultureInfo.InvariantCulture) };
                        report.material_array_matches_blender &= guid == blender.current_material_refs[i].guid && id.ToString() == blender.current_material_refs[i].file_id;
                        int count = report.imported_triangle_slot_counts[i];
                        int slot = Array.IndexOf(blender.blender_triangle_slot_counts, count);
                        report.native_material_association_correct &= slot >= 0 && guid == blender.current_material_refs[slot].guid && id.ToString() == blender.current_material_refs[slot].file_id;
                    }
                }
            }
            report.source_assets_unchanged = SameSource(sourceHashes);
            report.result = report.first_apply && report.repeated_apply && report.native_material_association_correct && report.native_transport_labels_exact && report.wrong_label_refused && report.wrong_guid_refused && report.wrong_local_id_refused && report.controls_no_variant && report.source_assets_unchanged ? "MATERIAL_ASSOCIATION_PASS" : "PROBE_FAILED";
        }
        catch { }
        File.WriteAllText(Argument("-vapbPublicReport"), JsonUtility.ToJson(report, true));
        EditorApplication.Exit(report.result == "PROBE_FAILED" ? 1 : 0);
    }
    private static string Disk(string path) { return Path.GetFullPath(Path.Combine(Application.dataPath, "../" + path)); }
    private static string Argument(string name)
    {
        string[] args = Environment.GetCommandLineArgs();
        int index = Array.IndexOf(args, name);
        if (index < 0 || index + 1 >= args.Length) throw new ArgumentException(name);
        return Path.GetFullPath(args[index + 1]);
    }
    private static string Label(string guid, string id)
    { using (var sha = System.Security.Cryptography.SHA256.Create()) return "VAPB-MAT-" + BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.ASCII.GetBytes("MODEL_SKIN_MATERIAL_V1:" + guid + ":" + id))).Replace("-", "").ToLowerInvariant().Substring(0,32); }
    private static bool Negative(string raw, string disk, string path, string variant, string field, string value, string label)
    {
        var pattern = new System.Text.RegularExpressions.Regex(@"""material_bindings""\s*:\s*\[(.*?)\]", System.Text.RegularExpressions.RegexOptions.Singleline);
        var match = pattern.Match(raw);
        if (!match.Success) throw new InvalidOperationException();
        string block = match.Value;
        var fieldPattern = new System.Text.RegularExpressions.Regex("\"" + field + "\"\\s*:\\s*\"[^\"]*\"");
        block = fieldPattern.Replace(block, "\"" + field + "\":\"" + value + "\"", 1);
        if (label != null) block = new System.Text.RegularExpressions.Regex(@"""transport_id""\s*:\s*""[^""]*""").Replace(block, "\"transport_id\":\"" + label + "\"", 1);
        try { File.WriteAllText(disk, raw.Substring(0,match.Index) + block + raw.Substring(match.Index+match.Length)); return !Apply(path) && !File.Exists(Disk(variant)); }
        finally { File.WriteAllText(disk, raw); }
    }
    private static System.Collections.Generic.Dictionary<string,string> SnapshotSource()
    {
        var values = new System.Collections.Generic.Dictionary<string,string>();
        foreach (string file in Directory.GetFiles(Application.dataPath, "*.mat", SearchOption.AllDirectories))
            using (var sha = System.Security.Cryptography.SHA256.Create()) { values[file] = Convert.ToBase64String(sha.ComputeHash(File.ReadAllBytes(file))); values[file + ".meta"] = Convert.ToBase64String(sha.ComputeHash(File.ReadAllBytes(file + ".meta"))); }
        return values;
    }
    private static bool SameSource(System.Collections.Generic.Dictionary<string,string> values)
    { foreach(var pair in SnapshotSource()) if (!values.ContainsKey(pair.Key) || values[pair.Key] != pair.Value) return false; return values.Count == SnapshotSource().Count; }
    private static bool Apply(string path)
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type type = assembly.GetType("VapbModelSkinFinalizer");
            if (type != null) return (bool)type.GetMethod("Apply").Invoke(null, new object[] { path });
        }
        return false;
    }
}
