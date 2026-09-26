using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEditor;
using UnityEngine;

// Read-only observation of imported Prefab and Model structures through public Unity APIs.
// Detailed identifiers stay in the temporary Oracle project, outside the VAPB repository.
[InitializeOnLoad]
public static class VapbPrivateStructureProbe
{
    private const string Phase = "VAPB_PRIVATE_STRUCTURE_PHASE";
    private const string Started = "VAPB_PRIVATE_STRUCTURE_STARTED";

    [Serializable] private sealed class Identity
    {
        public string asset_path;
        public string guid;
        public string local_id;
        public bool persistent_id;
    }

    [Serializable] private sealed class RendererRecord
    {
        public string owner_ordinal_path;
        public string renderer_type;
        public Identity renderer;
        public Identity owner;
        public Identity mesh;
        public Identity[] materials;
        public Identity[] bones;
        public Identity root_bone;
        public Identity[] source_chain;
        public bool prefab_instance_component;
    }

    [Serializable] private sealed class AssetRecord
    {
        public string asset_path;
        public string asset_guid;
        public string asset_type;
        public bool loaded;
        public int game_objects;
        public int instance_roots;
        public int missing_components;
        public int renderer_count;
        public int skin_count;
        public int bone_reference_count;
        public RendererRecord[] renderers;
    }

    [Serializable] private sealed class Detail
    {
        public string observation_schema = "vapb-private-structure-observation-1";
        public AssetRecord[] assets;
    }

    [Serializable] private sealed class Summary
    {
        public bool pass;
        public string phase;
        public string error;
        public bool package_imported;
        public int asset_count;
        public int prefab_count;
        public int model_count;
        public int loaded_prefabs;
        public int loaded_models;
        public int game_object_count;
        public int prefab_instance_root_count;
        public int renderer_occurrence_count;
        public int skinned_renderer_occurrence_count;
        public int direct_renderer_occurrence_count;
        public int inherited_renderer_occurrence_count;
        public int renderer_with_persistent_id_count;
        public int renderer_with_source_chain_count;
        public int renderer_without_identity_count;
        public int bone_reference_count;
        public int unresolved_bone_reference_count;
        public int missing_component_count;
    }

    static VapbPrivateStructureProbe()
    {
        AssetDatabase.importPackageCompleted += OnCompleted;
        AssetDatabase.importPackageFailed += OnFailed;
        AssetDatabase.importPackageCancelled += OnCancelled;
        EditorApplication.update += CheckTimeout;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += Observe;
    }

    public static void Run()
    {
        try
        {
            string path = ProjectFile("Input.unitypackage");
            if (!File.Exists(path)) throw new InvalidOperationException("PACKAGE_MISSING");
            SessionState.SetString(Phase, "importing");
            SessionState.SetFloat(Started, (float)EditorApplication.timeSinceStartup);
            AssetDatabase.ImportPackage(path, false);
        }
        catch (Exception error)
        {
            Finish(new Summary { phase = "import", error = SafeError(error) });
        }
    }

    private static void OnCompleted(string packageName)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "completed");
        EditorApplication.delayCall += Observe;
    }

    private static void OnFailed(string packageName, string error)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Summary { phase = "import", error = "PACKAGE_IMPORT_FAILED" });
    }

    private static void OnCancelled(string packageName)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Summary { phase = "import", error = "PACKAGE_IMPORT_CANCELLED" });
    }

    private static void CheckTimeout()
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        float start = SessionState.GetFloat(Started, 0f);
        if (start > 0f && EditorApplication.timeSinceStartup - start > 180f)
            Finish(new Summary { phase = "import", error = "PACKAGE_IMPORT_TIMEOUT" });
    }

    private static void Observe()
    {
        if (SessionState.GetString(Phase, "") != "completed") return;
        SessionState.SetString(Phase, "observing");
        var summary = new Summary { phase = "observe", error = "UNEXPECTED_EXCEPTION", package_imported = true };
        try
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var records = new List<AssetRecord>();
            recordsForContents.Clear();
            foreach (string path in AssetDatabase.GetAllAssetPaths())
            {
                if (!path.StartsWith("Assets/", StringComparison.Ordinal) ||
                    (!path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase) &&
                     !path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase)))
                    continue;
                bool prefab = path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase);
                if (prefab) summary.prefab_count++; else summary.model_count++;
                AssetRecord record = Inspect(path, prefab, summary);
                records.Add(record);
            }
            summary.asset_count = records.Count;
            if (summary.asset_count == 0) throw new InvalidOperationException("NO_MODEL_OR_PREFAB");
            records.AddRange(recordsForContents);
            File.WriteAllText(ProjectFile("VapbPrivateStructureDetail.json"),
                JsonUtility.ToJson(new Detail { assets = records.ToArray() }, true));
            summary.pass = true;
            summary.error = "NONE";
        }
        catch (Exception error) { summary.error = SafeError(error); }
        Finish(summary);
    }

    private static AssetRecord Inspect(string path, bool prefab, Summary summary)
    {
        var record = new AssetRecord
        {
            asset_path = path, asset_guid = AssetDatabase.AssetPathToGUID(path),
            asset_type = prefab ? "PREFAB" : "MODEL"
        };
        GameObject persistent = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (persistent == null) return record;
        record.loaded = true;
        if (prefab) summary.loaded_prefabs++; else summary.loaded_models++;
        // Persistent asset objects expose stable GUID/local IDs. LoadPrefabContents
        // below supplies an independent expanded hierarchy for nested instances.
        var renderers = new List<RendererRecord>();
        InspectHierarchy(persistent, record, summary, renderers);
        if (prefab)
        {
            GameObject contents = PrefabUtility.LoadPrefabContents(path);
            try
            {
                var contentsRecord = new AssetRecord
                {
                    asset_path = path, asset_guid = record.asset_guid,
                    asset_type = "PREFAB_CONTENTS", loaded = true
                };
                var contentsRenderers = new List<RendererRecord>();
                InspectHierarchy(contents, contentsRecord, null, contentsRenderers);
                // Keep both independent public-API observations in the private detail.
                recordsForContents.Add(contentsRecord);
                contentsRecord.renderers = contentsRenderers.ToArray();
            }
            finally { PrefabUtility.UnloadPrefabContents(contents); }
        }
        record.renderers = renderers.ToArray();
        return record;
    }

    private static readonly List<AssetRecord> recordsForContents = new List<AssetRecord>();

    private static void InspectHierarchy(GameObject root, AssetRecord record, Summary summary,
                                         List<RendererRecord> renderers)
    {
        var instanceRoots = new HashSet<GameObject>();
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            record.game_objects++;
            if (summary != null) summary.game_object_count++;
            GameObject instanceRoot = PrefabUtility.GetNearestPrefabInstanceRoot(transform.gameObject);
            if (instanceRoot != null) instanceRoots.Add(instanceRoot);
            foreach (Component component in transform.GetComponents<Component>())
                if (component == null)
                {
                    record.missing_components++;
                    if (summary != null) summary.missing_component_count++;
                }
            foreach (Renderer renderer in transform.GetComponents<Renderer>())
            {
                var item = new RendererRecord
                {
                    owner_ordinal_path = OrdinalPath(transform, root.transform),
                    renderer_type = renderer is SkinnedMeshRenderer ? "SKINNED" :
                                    renderer is MeshRenderer ? "DIRECT" : "OTHER",
                    renderer = GetIdentity(renderer), owner = GetIdentity(transform.gameObject),
                    prefab_instance_component = PrefabUtility.IsPartOfPrefabInstance(renderer),
                    source_chain = SourceChain(renderer),
                    materials = Materials(renderer.sharedMaterials)
                };
                if (renderer is SkinnedMeshRenderer skin)
                {
                    item.mesh = GetIdentity(skin.sharedMesh);
                    item.bones = Identities(skin.bones);
                    item.root_bone = GetIdentity(skin.rootBone);
                    record.skin_count++;
                    record.bone_reference_count += skin.bones.Length;
                    if (summary != null)
                    {
                        summary.skinned_renderer_occurrence_count++;
                        summary.bone_reference_count += skin.bones.Length;
                        foreach (Identity bone in item.bones)
                            if (bone == null || !bone.persistent_id)
                                summary.unresolved_bone_reference_count++;
                    }
                }
                else if (renderer is MeshRenderer direct)
                {
                    MeshFilter[] filters = direct.GetComponents<MeshFilter>();
                    item.mesh = filters.Length == 1 ? GetIdentity(filters[0].sharedMesh) : null;
                    if (summary != null) summary.direct_renderer_occurrence_count++;
                }
                record.renderer_count++;
                renderers.Add(item);
                if (summary != null)
                {
                    summary.renderer_occurrence_count++;
                    if (item.prefab_instance_component) summary.inherited_renderer_occurrence_count++;
                    if (item.renderer.persistent_id) summary.renderer_with_persistent_id_count++;
                    if (item.source_chain.Length > 0) summary.renderer_with_source_chain_count++;
                    if (!item.renderer.persistent_id && item.source_chain.Length == 0)
                        summary.renderer_without_identity_count++;
                }
            }
        }
        record.instance_roots = instanceRoots.Count;
        if (summary != null) summary.prefab_instance_root_count += instanceRoots.Count;
    }

    private static string OrdinalPath(Transform transform, Transform root)
    {
        var parts = new List<string>();
        for (Transform current = transform; current != null && current != root; current = current.parent)
            parts.Add(current.GetSiblingIndex().ToString(CultureInfo.InvariantCulture));
        parts.Reverse();
        return string.Join("/", parts);
    }

    private static Identity[] SourceChain(UnityEngine.Object asset)
    {
        var result = new List<Identity>();
        var seen = new HashSet<UnityEngine.Object>();
        UnityEngine.Object current = asset;
        for (int depth = 0; current != null && depth < 32; depth++)
        {
            if (!seen.Add(current)) break;
            UnityEngine.Object source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (source == null || source == current) break;
            result.Add(GetIdentity(source));
            current = source;
        }
        return result.ToArray();
    }

    private static Identity GetIdentity(UnityEngine.Object asset)
    {
        if (asset == null) return null;
        bool success = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id);
        return new Identity
        {
            asset_path = AssetDatabase.GetAssetPath(asset),
            guid = success ? guid : "",
            local_id = success ? id.ToString(CultureInfo.InvariantCulture) : "",
            persistent_id = success && !string.IsNullOrEmpty(guid) && id != 0
        };
    }

    private static Identity[] Identities(Transform[] assets)
    {
        var result = new Identity[assets.Length];
        for (int i = 0; i < assets.Length; i++) result[i] = GetIdentity(assets[i]);
        return result;
    }

    private static Identity[] Materials(Material[] assets)
    {
        var result = new Identity[assets.Length];
        for (int i = 0; i < assets.Length; i++) result[i] = GetIdentity(assets[i]);
        return result;
    }

    private static string ProjectFile(string name)
    {
        return Path.Combine(Path.GetDirectoryName(Application.dataPath), name);
    }

    private static string SafeError(Exception error)
    {
        if (error is InvalidOperationException)
        {
            if (error.Message == "PACKAGE_MISSING" || error.Message == "NO_MODEL_OR_PREFAB")
                return error.Message;
        }
        return error.GetType().Name;
    }

    private static void Finish(Summary summary)
    {
        SessionState.SetString(Phase, "");
        try { File.WriteAllText(ProjectFile("VapbPrivateStructureSummary.json"), JsonUtility.ToJson(summary, true)); }
        catch { summary.pass = false; }
        Debug.Log(summary.pass ? "VAPB_PRIVATE_STRUCTURE_PASS" : "VAPB_PRIVATE_STRUCTURE_FAIL");
        EditorApplication.Exit(summary.pass ? 0 : 1);
    }
}
