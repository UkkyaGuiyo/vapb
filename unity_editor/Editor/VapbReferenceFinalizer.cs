using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public sealed class VapbRealizationPostprocessor : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject gameObject, string[] names, object[] values)
    {
        if (names == null || values == null || names.Length != values.Length ||
            !VapbReferenceFinalizer.IsAuthorizedModel(assetPath))
            return;
        for (int i = 0; i < names.Length; i++)
        {
            if (names[i] != "_vapb_fbx_realization_id" || !(values[i] is string id) ||
                !VapbReferenceFinalizer.IsAuthorizedRealization(assetPath, id))
                continue;
            VapbRealizationMarker marker = gameObject.GetComponent<VapbRealizationMarker>();
            if (marker == null)
                marker = gameObject.AddComponent<VapbRealizationMarker>();
            marker.realizationId = id;
        }
    }
}

public static class VapbReferenceFinalizer
{
    private static readonly HashSet<string> KnownErrors = new HashSet<string>(StringComparer.Ordinal)
    {
        "MODEL_UNAVAILABLE", "DUPLICATE_TARGET", "PREFAB_UNAVAILABLE", "TARGET_STRUCTURE_UNSUPPORTED",
        "PREFAB_SAVE_FAILED", "MANIFEST_UNAVAILABLE", "MANIFEST_UNSUPPORTED", "TASK_UNSUPPORTED",
        "MATERIAL_ID_INVALID", "NESTED_OR_AMBIGUOUS_TARGET", "TARGET_NOT_FOUND",
        "MODEL_STRUCTURE_UNSUPPORTED", "MODEL_MESH_MISSING", "REALIZATION_NOT_FOUND",
        "MATERIAL_NOT_FOUND", "MATERIAL_AMBIGUOUS", "LOCAL_ID_INVALID",
        "MODEL_HASH_MISMATCH", "STALE_PREFAB_SOURCE", "INCONSISTENT_PREFAB_SOURCE", "UNSAVED_PREFAB_CHANGES"
    };
    [Serializable] private sealed class Manifest
    {
        public string schema_version;
        public Task[] reference_rebind_tasks;
    }

    [Serializable] private sealed class Task
    {
        public string kind;
        public string prefab_guid;
        public string renderer_file_id;
        public string model_guid;
        public string model_sha256;
        public string prefab_source_sha256;
        public string realization_id;
        public int renderer_class_id;
        public MaterialId[] materials;
    }

    [Serializable] private sealed class MaterialId
    {
        public string guid;
        public string file_id;
    }

    private sealed class Binding
    {
        public MeshFilter filter;
        public MeshRenderer renderer;
        public Mesh mesh;
        public Material[] materials;
    }

    private sealed class PrefabPlan
    {
        public string path;
        public GameObject contents;
        public readonly List<Binding> bindings = new List<Binding>();
        public byte[] originalBytes;
        public string sourceHash;
    }

    [MenuItem("Tools/VAPB/Apply Selected Export Manifest")]
    private static void ApplySelected()
    {
        string path = AssetDatabase.GetAssetPath(Selection.activeObject);
        if (!Apply(path))
            Debug.LogError("VAPB_FINALIZER_FAILED");
    }

    [MenuItem("Tools/VAPB/Apply Selected Export Manifest", true)]
    private static bool CanApplySelected()
    {
        return Selection.activeObject is TextAsset &&
            IsManifestPath(AssetDatabase.GetAssetPath(Selection.activeObject));
    }

    public static bool Apply(string manifestAssetPath)
    {
        var plans = new Dictionary<string, PrefabPlan>(StringComparer.Ordinal);
        try
        {
            Manifest manifest = ReadManifest(manifestAssetPath);
            ValidateTaskSyntax(manifest);
            // Import may have seen the model before the manifest. Reimport now that
            // authorization is available so its persistent marker is materialized.
            var modelGuids = new HashSet<string>(StringComparer.Ordinal);
            foreach (Task task in manifest.reference_rebind_tasks)
                modelGuids.Add(task.model_guid);
            foreach (string guid in modelGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path) || !path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) ||
                    !IsAuthorizedModel(path))
                    throw new InvalidOperationException("MODEL_UNAVAILABLE");
                string actualHash = FileHash(ToDiskPath(path));
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task.model_guid == guid && !actualHash.Equals(task.model_sha256, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidOperationException("MODEL_HASH_MISMATCH");
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }

            var identities = new HashSet<string>(StringComparer.Ordinal);
            foreach (Task task in manifest.reference_rebind_tasks)
            {
                long rendererId = ParseLocalId(task.renderer_file_id);
                string key = task.prefab_guid + ":" + rendererId.ToString(CultureInfo.InvariantCulture);
                if (!identities.Add(key))
                    throw new InvalidOperationException("DUPLICATE_TARGET");
                string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
                if (string.IsNullOrEmpty(prefabPath) || !prefabPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("PREFAB_UNAVAILABLE");
                if (!plans.TryGetValue(prefabPath, out PrefabPlan plan))
                {
                    plan = new PrefabPlan { path = prefabPath };
                    plan.contents = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                    if (plan.contents == null)
                        throw new InvalidOperationException("PREFAB_UNAVAILABLE");
                    plan.sourceHash = task.prefab_source_sha256;
                    foreach (Transform transform in plan.contents.GetComponentsInChildren<Transform>(true))
                    {
                        if (EditorUtility.IsDirty(transform.gameObject))
                            throw new InvalidOperationException("UNSAVED_PREFAB_CHANGES");
                        foreach (Component component in transform.GetComponents<Component>())
                            if (component != null && EditorUtility.IsDirty(component))
                                throw new InvalidOperationException("UNSAVED_PREFAB_CHANGES");
                    }
                    plans.Add(prefabPath, plan);
                }
                else if (!plan.sourceHash.Equals(task.prefab_source_sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("INCONSISTENT_PREFAB_SOURCE");
                MeshRenderer target = ResolveTarget(plan.contents, task.prefab_guid, rendererId);
                MeshFilter filter = target.GetComponent<MeshFilter>();
                if (filter == null || target.GetComponents<Renderer>().Length != 1)
                    throw new InvalidOperationException("TARGET_STRUCTURE_UNSUPPORTED");
                Mesh mesh = ResolveModelMesh(task);
                Material[] materials = ResolveMaterials(task.materials);
                plan.bindings.Add(new Binding { filter = filter, renderer = target, mesh = mesh, materials = materials });
            }

            // All targets and references are resolved before any prefab is changed.
            foreach (PrefabPlan plan in plans.Values)
            {
                plan.originalBytes = File.ReadAllBytes(ToDiskPath(plan.path));
                bool needsChange = false;
                foreach (Binding binding in plan.bindings)
                    if (binding.filter.sharedMesh != binding.mesh ||
                        !SameMaterials(binding.renderer.sharedMaterials, binding.materials))
                        needsChange = true;
                if (needsChange && !HashBytes(plan.originalBytes).Equals(plan.sourceHash, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("STALE_PREFAB_SOURCE");
            }
            var saved = new List<PrefabPlan>();
            try
            {
                foreach (PrefabPlan plan in plans.Values)
                {
                    // Cover exceptions during property mutation as well as save.
                    saved.Add(plan);
                    bool changed = false;
                    foreach (Binding binding in plan.bindings)
                    {
                        if (binding.filter.sharedMesh != binding.mesh)
                        {
                            binding.filter.sharedMesh = binding.mesh;
                            EditorUtility.SetDirty(binding.filter);
                            changed = true;
                        }
                        if (!SameMaterials(binding.renderer.sharedMaterials, binding.materials))
                        {
                            binding.renderer.sharedMaterials = binding.materials;
                            EditorUtility.SetDirty(binding.renderer);
                            changed = true;
                        }
                    }
                    if (!changed)
                        continue;
                    GameObject result = PrefabUtility.SavePrefabAsset(plan.contents);
                    if (result == null)
                        throw new InvalidOperationException("PREFAB_SAVE_FAILED");
                }
            }
            catch
            {
                foreach (PrefabPlan plan in saved)
                {
                    File.WriteAllBytes(ToDiskPath(plan.path), plan.originalBytes);
                    AssetDatabase.ImportAsset(plan.path, ImportAssetOptions.ForceUpdate);
                }
                throw;
            }
            Debug.Log("VAPB_FINALIZER_APPLIED=" + manifest.reference_rebind_tasks.Length);
            return true;
        }
        catch (Exception exception)
        {
            string code = exception is InvalidOperationException && KnownErrors.Contains(exception.Message)
                ? exception.Message : "UNEXPECTED_EXCEPTION";
            Debug.LogError("VAPB_FINALIZER_REJECTED=" + code);
            return false;
        }
    }

    private static Manifest ReadManifest(string path)
    {
        if (!IsManifestPath(path) || AssetDatabase.LoadAssetAtPath<TextAsset>(path) == null)
            throw new InvalidOperationException("MANIFEST_UNAVAILABLE");
        return JsonUtility.FromJson<Manifest>(File.ReadAllText(ToDiskPath(path)));
    }

    private static void ValidateTaskSyntax(Manifest manifest)
    {
        if (manifest == null || manifest.schema_version != "vapb-export-manifest-1" ||
            manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length == 0)
            throw new InvalidOperationException("MANIFEST_UNSUPPORTED");
        foreach (Task task in manifest.reference_rebind_tasks)
        {
            if (task == null || task.kind != "REBIND_DIRECT_RENDERER_V1" || task.renderer_class_id != 23 ||
                !ValidGuid(task.prefab_guid) || !ValidGuid(task.model_guid) ||
                !ValidSha256(task.model_sha256) || !ValidSha256(task.prefab_source_sha256) ||
                string.IsNullOrEmpty(task.realization_id) || task.materials == null)
                throw new InvalidOperationException("TASK_UNSUPPORTED");
            ParseLocalId(task.renderer_file_id);
            foreach (MaterialId material in task.materials)
                if (material != null && (!ValidGuid(material.guid) || ParseLocalId(material.file_id) == 0))
                    throw new InvalidOperationException("MATERIAL_ID_INVALID");
        }
    }

    private static MeshRenderer ResolveTarget(GameObject contents, string guid, long localId)
    {
        MeshRenderer result = null;
        foreach (MeshRenderer renderer in contents.GetComponentsInChildren<MeshRenderer>(true))
        {
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string sourceGuid, out long sourceId) ||
                sourceGuid != guid || sourceId != localId)
                continue;
            if (PrefabUtility.IsPartOfPrefabInstance(renderer) || result != null)
                throw new InvalidOperationException("NESTED_OR_AMBIGUOUS_TARGET");
            result = renderer;
        }
        if (result == null)
            throw new InvalidOperationException("TARGET_NOT_FOUND");
        return result;
    }

    private static Mesh ResolveModelMesh(Task task)
    {
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid));
        if (model == null)
            throw new InvalidOperationException("MODEL_UNAVAILABLE");
        Mesh found = null;
        foreach (VapbRealizationMarker marker in model.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if (marker.realizationId != task.realization_id)
                continue;
            if (found != null || marker.GetComponents<Renderer>().Length != 1 ||
                marker.GetComponent<MeshRenderer>() == null || marker.GetComponents<MeshFilter>().Length != 1)
                throw new InvalidOperationException("MODEL_STRUCTURE_UNSUPPORTED");
            found = marker.GetComponent<MeshFilter>().sharedMesh;
            if (found == null)
                throw new InvalidOperationException("MODEL_MESH_MISSING");
        }
        if (found == null)
            throw new InvalidOperationException("REALIZATION_NOT_FOUND");
        return found;
    }

    private static Material[] ResolveMaterials(MaterialId[] ids)
    {
        var result = new Material[ids.Length];
        for (int i = 0; i < ids.Length; i++)
        {
            if (ids[i] == null)
                continue;
            long localId = ParseLocalId(ids[i].file_id);
            string path = AssetDatabase.GUIDToAssetPath(ids[i].guid);
            if (string.IsNullOrEmpty(path))
                throw new InvalidOperationException("MATERIAL_NOT_FOUND");
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
            {
                if (!(asset is Material material) ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(asset, out string guid, out long id) ||
                    guid != ids[i].guid || id != localId)
                    continue;
                if (result[i] != null)
                    throw new InvalidOperationException("MATERIAL_AMBIGUOUS");
                result[i] = material;
            }
            if (result[i] == null)
                throw new InvalidOperationException("MATERIAL_NOT_FOUND");
        }
        return result;
    }

    private static bool SameMaterials(Material[] a, Material[] b)
    {
        if (a.Length != b.Length)
            return false;
        for (int i = 0; i < a.Length; i++)
            if (a[i] != b[i])
                return false;
        return true;
    }

    internal static bool IsAuthorizedModel(string modelPath)
    {
        if (string.IsNullOrEmpty(modelPath) || !modelPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
            return false;
        string guid = AssetDatabase.AssetPathToGUID(modelPath);
        if (!ValidGuid(guid))
            return false;
        foreach (string path in ManifestPaths())
        {
            try
            {
                Manifest manifest = ReadManifest(path);
                ValidateTaskSyntax(manifest);
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task != null && task.kind == "REBIND_DIRECT_RENDERER_V1" && task.model_guid == guid)
                        return true;
            }
            catch { /* Invalid manifest does not authorize imports. */ }
        }
        return false;
    }

    internal static bool IsAuthorizedRealization(string modelPath, string id)
    {
        if (string.IsNullOrEmpty(id))
            return false;
        string guid = AssetDatabase.AssetPathToGUID(modelPath);
        foreach (string path in ManifestPaths())
        {
            try
            {
                Manifest manifest = ReadManifest(path);
                ValidateTaskSyntax(manifest);
                foreach (Task task in manifest.reference_rebind_tasks)
                    if (task != null && task.kind == "REBIND_DIRECT_RENDERER_V1" && task.model_guid == guid &&
                        task.realization_id == id)
                        return true;
            }
            catch { /* Invalid manifest does not authorize imports. */ }
        }
        return false;
    }

    private static IEnumerable<string> ManifestPaths()
    {
        const string folder = "Assets/VAPBExport";
        if (!AssetDatabase.IsValidFolder(folder))
            yield break;
        foreach (string guid in AssetDatabase.FindAssets("t:TextAsset", new[] { folder }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (IsManifestPath(path))
                yield return path;
        }
    }

    private static bool IsManifestPath(string path)
    {
        return !string.IsNullOrEmpty(path) && path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal) &&
            path.EndsWith(".json", StringComparison.OrdinalIgnoreCase) && path.IndexOf("..", StringComparison.Ordinal) < 0;
    }

    private static bool ValidGuid(string value)
    {
        if (value == null || value.Length != 32)
            return false;
        foreach (char c in value)
            if (!Uri.IsHexDigit(c))
                return false;
        return true;
    }

    private static bool ValidSha256(string value)
    {
        if (value == null || value.Length != 64)
            return false;
        foreach (char c in value)
            if (!Uri.IsHexDigit(c))
                return false;
        return true;
    }

    private static string FileHash(string path)
    {
        return HashBytes(File.ReadAllBytes(path));
    }

    private static string HashBytes(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }

    private static long ParseLocalId(string value)
    {
        if (string.IsNullOrEmpty(value) || !long.TryParse(value, NumberStyles.AllowLeadingSign,
            CultureInfo.InvariantCulture, out long id) || id == 0)
            throw new InvalidOperationException("LOCAL_ID_INVALID");
        return id;
    }

    private static string ToDiskPath(string assetPath)
    {
        return Path.Combine(Application.dataPath, assetPath.Substring("Assets/".Length).Replace('/', Path.DirectorySeparatorChar));
    }
}
