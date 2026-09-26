using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Test-only public API check of serialized PrefabInstance edges for model Renderers.
public static class VapbModelOccurrenceProbe
{
    private const string ModelPath = "Assets/VapbModelInstance/Input.fbx";
    private const string BasePath = "Assets/VapbModelInstance/Base.prefab";
    private const string VariantPath = "Assets/VapbModelInstance/Variant.prefab";
    private const string RepeatedFolder = "Assets/VapbModelOccurrence";
    private const string RepeatedPath = RepeatedFolder + "/Repeated.prefab";
    private const string RepeatedVariantPath = RepeatedFolder + "/RepeatedVariant.prefab";

    [Serializable] private sealed class Input { public string[] prefabs; }
    [Serializable] private sealed class Summary
    {
        public bool pass;
        public string error;
        public int prefab_count;
        public int renderer_count;
        public int skinned_renderer_count;
        public int edge_count;
        public int exact_edge_count;
        public int unique_occurrence_count;
        public int unresolved_count;
        public int ambiguous_count;
        public bool missing_edge_rejected;
        public bool wrong_source_rejected;
        public bool repeated_distinct;
    }
    [Serializable] private sealed class Edge
    {
        public string container_guid;
        public string instance_file_id;
        public string source_guid;
    }
    [Serializable] private sealed class Occurrence
    {
        public string root_guid;
        public string root_renderer_file_id;
        public int renderer_class_id;
        public string leaf_guid;
        public string leaf_renderer_file_id;
        public Edge[] edges;
        public string key;
        public string result;
    }
    [Serializable] private sealed class Detail { public Occurrence[] occurrences; }

    private sealed class EdgeDocument
    {
        public long fileId;
        public string sourceGuid;
    }

    public static void Run()
    {
        var summary = new Summary { error = "UNEXPECTED_EXCEPTION" };
        var records = new List<Occurrence>();
        try
        {
            string inputPath = ProjectFile("ModelOccurrenceInput.json");
            if (!File.Exists(inputPath)) throw new InvalidOperationException("INPUT_MISSING");
            Input input = JsonUtility.FromJson<Input>(File.ReadAllText(inputPath));
            Observe(input, summary, records);
        }
        catch (Exception error) { summary.pass = false; summary.error = SafeError(error); }
        Finish(summary, records);
    }

    public static void PrepareSynthetic()
    {
        var summary = new Summary { error = "UNEXPECTED_EXCEPTION" };
        var records = new List<Occurrence>();
        try
        {
            if (AssetDatabase.LoadAssetAtPath<GameObject>(RepeatedPath) != null ||
                AssetDatabase.LoadAssetAtPath<GameObject>(RepeatedVariantPath) != null ||
                File.Exists(AssetFile(RepeatedPath)) || File.Exists(AssetFile(RepeatedVariantPath)) ||
                File.Exists(AssetFile(RepeatedPath) + ".meta") ||
                File.Exists(AssetFile(RepeatedVariantPath) + ".meta") ||
                File.Exists(ProjectFile("ModelOccurrenceInput.json")))
                throw new InvalidOperationException("SYNTHETIC_PATH_OCCUPIED");
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (model == null || AssetDatabase.LoadAssetAtPath<GameObject>(BasePath) == null ||
                AssetDatabase.LoadAssetAtPath<GameObject>(VariantPath) == null)
                throw new InvalidOperationException("SYNTHETIC_SOURCE_MISSING");
            if (!AssetDatabase.IsValidFolder(RepeatedFolder))
                AssetDatabase.CreateFolder("Assets", "VapbModelOccurrence");

            GameObject root = new GameObject("RepeatedSynthetic");
            try
            {
                for (int i = 0; i < 2; i++)
                {
                    GameObject child = PrefabUtility.InstantiatePrefab(model) as GameObject;
                    if (child == null) throw new InvalidOperationException("SYNTHETIC_INSTANCE_FAILED");
                    child.transform.SetParent(root.transform, false);
                    child.transform.localPosition = new Vector3(i * 2.0f, 0, 0);
                }
                if (PrefabUtility.SaveAsPrefabAsset(root, RepeatedPath) == null)
                    throw new InvalidOperationException("SYNTHETIC_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }

            GameObject repeated = AssetDatabase.LoadAssetAtPath<GameObject>(RepeatedPath);
            GameObject instance = PrefabUtility.InstantiatePrefab(repeated) as GameObject;
            if (instance == null) throw new InvalidOperationException("SYNTHETIC_INSTANCE_FAILED");
            try
            {
                if (PrefabUtility.SaveAsPrefabAsset(instance, RepeatedVariantPath) == null)
                    throw new InvalidOperationException("SYNTHETIC_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
            GameObject variant = AssetDatabase.LoadAssetAtPath<GameObject>(RepeatedVariantPath);
            if (variant == null || PrefabUtility.GetPrefabAssetType(variant) != PrefabAssetType.Variant)
                throw new InvalidOperationException("SYNTHETIC_VARIANT_FAILED");

            var input = new Input { prefabs = new[] { BasePath, VariantPath, RepeatedPath, RepeatedVariantPath } };
            File.WriteAllText(ProjectFile("ModelOccurrenceInput.json"), JsonUtility.ToJson(input, true));
            Observe(input, summary, records);
            summary.repeated_distinct = RepeatedDistinct(records, RepeatedPath, RepeatedVariantPath);
            if (!summary.repeated_distinct) { summary.pass = false; summary.error = "REPEATED_NOT_DISTINCT"; }
        }
        catch (Exception error) { summary.pass = false; summary.error = SafeError(error); }
        Finish(summary, records);
    }

    private static void Observe(Input input, Summary summary, List<Occurrence> records)
    {
        if (input == null || input.prefabs == null || input.prefabs.Length == 0)
            throw new InvalidOperationException("INPUT_INVALID");
        var inputPaths = new HashSet<string>(StringComparer.Ordinal);
        var keys = new HashSet<string>(StringComparer.Ordinal);
        var documents = new Dictionary<string, Dictionary<long, EdgeDocument>>(StringComparer.Ordinal);
        Edge firstEdge = null;
        foreach (string path in input.prefabs)
        {
            if (String.IsNullOrEmpty(path) || !path.StartsWith("Assets/", StringComparison.Ordinal) ||
                !path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase) || !inputPaths.Add(path))
                throw new InvalidOperationException("INPUT_INVALID");
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            string rootGuid = AssetDatabase.AssetPathToGUID(path);
            if (root == null || !ValidGuid(rootGuid)) throw new InvalidOperationException("PREFAB_UNAVAILABLE");
            summary.prefab_count++;
            Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) throw new InvalidOperationException("RENDERER_MISSING");
            foreach (Renderer renderer in renderers)
            {
                summary.renderer_count++;
                if (renderer is SkinnedMeshRenderer) summary.skinned_renderer_count++;
                Occurrence occurrence = Resolve(renderer, rootGuid, documents, summary);
                records.Add(occurrence);
                if (occurrence.result != "EXACT") { summary.unresolved_count++; continue; }
                if (!keys.Add(occurrence.key)) { occurrence.result = "AMBIGUOUS"; summary.ambiguous_count++; continue; }
                summary.unique_occurrence_count++;
                if (firstEdge == null && occurrence.edges.Length > 0) firstEdge = occurrence.edges[0];
            }
        }
        if (firstEdge != null)
        {
            Dictionary<long, EdgeDocument> docs = documents[AssetDatabase.GUIDToAssetPath(firstEdge.container_guid)];
            long actual = Int64.Parse(firstEdge.instance_file_id);
            long missing = Int64.MaxValue;
            while (docs.ContainsKey(missing)) missing--;
            summary.missing_edge_rejected = !EdgeMatches(docs, missing, firstEdge.source_guid);
            string wrong = firstEdge.source_guid == new string('0', 32) ? new string('1', 32) : new string('0', 32);
            summary.wrong_source_rejected = !EdgeMatches(docs, actual, wrong);
        }
        summary.pass = summary.prefab_count == input.prefabs.Length && summary.renderer_count > 0 &&
            summary.edge_count > 0 && summary.edge_count == summary.exact_edge_count &&
            summary.renderer_count == summary.unique_occurrence_count && summary.unresolved_count == 0 &&
            summary.ambiguous_count == 0 && summary.missing_edge_rejected && summary.wrong_source_rejected;
        summary.error = summary.pass ? "NONE" : "ASSERTION_FAILED";
    }

    private static Occurrence Resolve(Renderer renderer, string rootGuid,
        Dictionary<string, Dictionary<long, EdgeDocument>> documents, Summary summary)
    {
        var record = new Occurrence { root_guid = rootGuid, result = "UNRESOLVED",
            renderer_class_id = renderer is SkinnedMeshRenderer ? 137 : renderer is MeshRenderer ? 23 : 0 };
        var edges = new List<Edge>();
        record.edges = edges.ToArray();
        if (record.renderer_class_id == 0) return record;
        string rendererGuid;
        long rendererId;
        if (!PersistentId(renderer, out rendererGuid, out rendererId) ||
            !String.Equals(rendererGuid, rootGuid, StringComparison.OrdinalIgnoreCase)) return record;
        record.root_renderer_file_id = rendererId.ToString();
        UnityEngine.Object current = renderer;
        for (int depth = 0; depth < 16; depth++)
        {
            string currentPath = AssetDatabase.GetAssetPath(current);
            string currentGuid = AssetDatabase.AssetPathToGUID(currentPath);
            if (!ValidGuid(currentGuid)) return record;
            UnityEngine.Object source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (currentPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
            {
                if (source != null) return record;
                string leafGuid;
                long leafId;
                if (!PersistentId(current, out leafGuid, out leafId) ||
                    !String.Equals(leafGuid, currentGuid, StringComparison.OrdinalIgnoreCase)) return record;
                record.leaf_guid = leafGuid;
                record.leaf_renderer_file_id = leafId.ToString();
                record.edges = edges.ToArray();
                record.key = Key(record);
                record.result = "EXACT";
                return record;
            }
            if (!currentPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase) ||
                !(source is Renderer) || source.GetType() != current.GetType() || source == current) return record;
            string sourcePath = AssetDatabase.GetAssetPath(source);
            string sourceGuid = AssetDatabase.AssetPathToGUID(sourcePath);
            if (!ValidGuid(sourceGuid)) return record;
            UnityEngine.Object handle = PrefabUtility.GetPrefabInstanceHandle(current);
            string handleGuid;
            long handleId;
            if (handle == null || !PersistentId(handle, out handleGuid, out handleId) ||
                !String.Equals(handleGuid, currentGuid, StringComparison.OrdinalIgnoreCase)) return record;
            Dictionary<long, EdgeDocument> docs;
            if (!documents.TryGetValue(currentPath, out docs))
            {
                docs = ParseEdges(currentPath);
                documents.Add(currentPath, docs);
            }
            summary.edge_count++;
            if (!EdgeMatches(docs, handleId, sourceGuid)) return record;
            summary.exact_edge_count++;
            edges.Add(new Edge { container_guid = currentGuid,
                instance_file_id = handleId.ToString(), source_guid = sourceGuid });
            record.edges = edges.ToArray();
            current = source;
        }
        return record;
    }

    private static Dictionary<long, EdgeDocument> ParseEdges(string assetPath)
    {
        string yaml = File.ReadAllText(AssetFile(assetPath));
        var docs = new Dictionary<long, EdgeDocument>();
        MatchCollection headings = Regex.Matches(yaml, @"(?m)^--- !u!(\d+) &(-?\d+)\s*$");
        for (int i = 0; i < headings.Count; i++)
        {
            if (headings[i].Groups[1].Value != "1001") continue;
            long id;
            if (!Int64.TryParse(headings[i].Groups[2].Value, out id))
                throw new InvalidOperationException("INSTANCE_ID_INVALID");
            int start = headings[i].Index + headings[i].Length;
            int end = i + 1 < headings.Count ? headings[i + 1].Index : yaml.Length;
            Match source = Regex.Match(yaml.Substring(start, end - start),
                @"m_SourcePrefab:\s*\{[^}]*\bguid:\s*([0-9a-fA-F]{32})\b", RegexOptions.Singleline);
            if (!source.Success || docs.ContainsKey(id))
                throw new InvalidOperationException("INSTANCE_DOCUMENT_INVALID");
            docs.Add(id, new EdgeDocument { fileId = id, sourceGuid = source.Groups[1].Value });
        }
        return docs;
    }

    private static bool EdgeMatches(Dictionary<long, EdgeDocument> docs, long id, string sourceGuid)
    {
        EdgeDocument doc;
        return docs.TryGetValue(id, out doc) && doc.fileId == id &&
            String.Equals(doc.sourceGuid, sourceGuid, StringComparison.OrdinalIgnoreCase);
    }

    private static string Key(Occurrence occurrence)
    {
        var key = new StringBuilder(occurrence.root_guid);
        foreach (Edge edge in occurrence.edges)
            key.Append('|').Append(edge.container_guid).Append(':').Append(edge.instance_file_id)
                .Append('>').Append(edge.source_guid);
        return key.Append('|').Append(occurrence.leaf_guid).Append(':')
            .Append(occurrence.leaf_renderer_file_id).Append(':').Append(occurrence.renderer_class_id).ToString();
    }

    private static bool RepeatedDistinct(List<Occurrence> records, string repeated, string variant)
    {
        string repeatedGuid = AssetDatabase.AssetPathToGUID(repeated);
        string variantGuid = AssetDatabase.AssetPathToGUID(variant);
        var a = new HashSet<string>(StringComparer.Ordinal);
        var b = new HashSet<string>(StringComparer.Ordinal);
        foreach (Occurrence record in records)
        {
            if (record.result != "EXACT") continue;
            if (record.root_guid == repeatedGuid) a.Add(record.key);
            if (record.root_guid == variantGuid) b.Add(record.key);
        }
        return a.Count == 2 && b.Count == 2;
    }

    private static bool PersistentId(UnityEngine.Object obj, out string guid, out long id)
    {
        guid = null;
        id = 0;
        return AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out guid, out id) && ValidGuid(guid) && id != 0;
    }

    private static bool ValidGuid(string guid) { return !String.IsNullOrEmpty(guid) && Regex.IsMatch(guid, "^[0-9a-fA-F]{32}$"); }
    private static string AssetFile(string path) { return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string ProjectFile(string name) { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }

    private static string SafeError(Exception error)
    {
        if (error is InvalidOperationException)
        {
            switch (error.Message)
            {
                case "INPUT_MISSING": case "INPUT_INVALID": case "PREFAB_UNAVAILABLE":
                case "RENDERER_MISSING": case "INSTANCE_ID_INVALID": case "INSTANCE_DOCUMENT_INVALID":
                case "SYNTHETIC_PATH_OCCUPIED": case "SYNTHETIC_SOURCE_MISSING":
                case "SYNTHETIC_INSTANCE_FAILED": case "SYNTHETIC_SAVE_FAILED":
                case "SYNTHETIC_VARIANT_FAILED": return error.Message;
            }
        }
        return error.GetType().Name;
    }

    private static void Finish(Summary summary, List<Occurrence> records)
    {
        try
        {
            File.WriteAllText(ProjectFile("VapbModelOccurrenceDetail.json"),
                JsonUtility.ToJson(new Detail { occurrences = records.ToArray() }, true));
            File.WriteAllText(ProjectFile("VapbModelOccurrenceSummary.json"), JsonUtility.ToJson(summary, true));
        }
        catch { summary.pass = false; summary.error = "REPORT_WRITE_FAILED"; }
        Debug.Log(summary.pass ? "VAPB_MODEL_OCCURRENCE_PASS" : "VAPB_MODEL_OCCURRENCE_FAIL");
        EditorApplication.Exit(summary.pass ? 0 : 1);
    }
}
