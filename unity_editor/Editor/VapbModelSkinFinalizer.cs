// SPDX-License-Identifier: MIT
/*
MIT License

Copyright (c) 2026 UkkyaGuiyo and VAPB contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Only the manifest-authorized edited model and the synchronous source witness may create markers.
public sealed class VapbModelSkinPostprocessor : AssetPostprocessor
{
    private void OnPostprocessGameObjectWithUserProperties(GameObject node, string[] names, object[] values)
    {
        if (names == null || values == null || names.Length != values.Length) return;
        bool witness = VapbModelSkinFinalizer.IsWitnessImport(assetPath);
        bool edited = !witness && VapbModelSkinFinalizer.IsAuthorizedEditedModel(assetPath);
        if (!witness && !edited) return;
        for (int i = 0; i < names.Length; i++)
        {
            if (witness && names[i] == "_vapb_source_fbx_model_uid" &&
                !(values[i] is string supplied && VapbModelSkinFinalizer.IsExpectedWitnessUid(supplied)))
                VapbModelSkinFinalizer.MarkUnexpectedWitnessUid();
            string value = values[i] as string;
            if (String.IsNullOrEmpty(value)) continue;
            bool sourceUid = witness && names[i] == "_vapb_source_fbx_model_uid" &&
                VapbModelSkinFinalizer.IsExpectedWitnessUid(value);
            bool realization = edited && names[i] == "_vapb_fbx_realization_id" &&
                VapbModelSkinFinalizer.IsAuthorizedRealization(assetPath, value);
            bool bone = edited && names[i] == "_vapb_fbx_bone_realization_id" &&
                VapbModelSkinFinalizer.IsAuthorizedBone(assetPath, value);
            if (!sourceUid && !realization && !bone) continue;
            VapbRealizationMarker marker = node.GetComponent<VapbRealizationMarker>();
            if (marker == null) marker = node.AddComponent<VapbRealizationMarker>();
            if (sourceUid) marker.sourceModelUid = value;
            if (realization) marker.realizationId = value;
            if (bone) marker.boneRealizationId = value;
            if (sourceUid) VapbModelSkinFinalizer.CountWitnessCallback(value);
        }
    }
}

public static class VapbModelSkinFinalizer
{
    private const string Kind = "RESTORE_MODEL_SKIN_VARIANT_V1";
    private const string DirectKind = "RESTORE_DIRECT_SKIN_VARIANT_V1";
    private const string Schema = "vapb-export-manifest-1";
    private static string witnessPath;
    private static HashSet<string> witnessUids;
    private static bool unexpectedWitnessUid;
    private static readonly Dictionary<string, int> callbackCounts = new Dictionary<string, int>(StringComparer.Ordinal);

    [Serializable] private sealed class Manifest { public string schema_version; public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string prefab_guid;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string source_model_uid;
        public InstanceEdge[] instance_edges;
        public RendererCandidate[] renderer_candidates;
        public string model_guid;
        public string model_sha256;
        public string realization_id;
        public BoneMapping[] bone_mappings;
        public string variant_path;
        public string witness_noop_path;
        public string witness_noop_sha256;
        public string witness_path;
        public string witness_sha256;
        public string[] source_model_uids;
    }
    [Serializable] private sealed class InstanceEdge
    {
        public string container_guid;
        public string container_sha256;
        public string instance_file_id;
        public string source_guid;
    }
    [Serializable] private sealed class BoneMapping
    {
        public string edited_bone_realization_id;
        public string source_model_uid;
    }
    [Serializable] private sealed class RendererCandidate
    {
        public string renderer_file_id;
        public string source_mesh_file_id;
        public string[] bone_transform_file_ids;
        public string root_bone_transform_file_id;
    }
    private sealed class SourceIdentity
    {
        public SkinnedMeshRenderer renderer;
        public readonly Dictionary<string, Transform> bonesByUid = new Dictionary<string, Transform>(StringComparer.Ordinal);
        public string[] sourceBoneUids;
        public string rootUid;
    }
    private sealed class EditedIdentity
    {
        public SkinnedMeshRenderer renderer;
        public Mesh mesh;
        public string[] editedBoneUids;
        public string rootUid;
    }
    private sealed class Snapshot
    {
        public string guid;
        public readonly Dictionary<long, string> transforms = new Dictionary<long, string>();
        public readonly Dictionary<long, string> meshes = new Dictionary<long, string>();
        public readonly Dictionary<long, string> renderers = new Dictionary<long, string>();
        public bool Same(Snapshot other)
        {
            return other != null && guid == other.guid && SameMap(transforms, other.transforms) &&
                SameMap(meshes, other.meshes) && SameMap(renderers, other.renderers);
        }
    }
    private sealed class WitnessResult
    {
        public readonly Dictionary<string, long> transformIds = new Dictionary<string, long>(StringComparer.Ordinal);
        public long rendererId;
        public long meshId;
        public MeshLayout sourceLayout;
        public Matrix4x4[] sourceBindposes;
    }
    private sealed class MeshLayout
    {
        public int vertexCount;
        public MeshTopology[] topologies;
        public int[][] indices;
        public string[] shapeNames;
        public float[][] frameWeights;
    }
    private sealed class PreparedTask
    {
        public Task task;
        public WitnessResult witness;
        public SkinnedMeshRenderer target;
        public SourceIdentity source;
        public EditedIdentity edited;
        public string sourceMetaHash;
    }

    public static bool Handles(string manifestAssetPath)
    {
        try
        {
            Manifest manifest = ReadManifest(manifestAssetPath);
            return manifest != null && manifest.schema_version == Schema &&
                manifest.reference_rebind_tasks != null &&
                Array.Exists(manifest.reference_rebind_tasks, task =>
                    task != null && (task.kind == Kind || task.kind == DirectKind));
        }
        catch { return false; }
    }

    public static bool Apply(string manifestAssetPath)
    {
        try
        {
            Manifest manifest = ReadManifest(manifestAssetPath);
            if (manifest == null || manifest.schema_version != Schema || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length == 0)
                Reject("MANIFEST_UNSUPPORTED");
            ValidateBatch(manifest.reference_rebind_tasks);
            var plans = new List<PreparedTask>();
            foreach (Task task in manifest.reference_rebind_tasks)
                plans.Add(PrepareWitness(task));
            var imported = new HashSet<string>(StringComparer.Ordinal);
            foreach (PreparedTask plan in plans)
            {
                string path = AssetDatabase.GUIDToAssetPath(plan.task.model_guid);
                if (imported.Add(path)) RefreshEditedModel(path);
            }
            string prefabPath = AssetDatabase.GUIDToAssetPath(plans[0].task.prefab_guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null || HasMissingScripts(prefab)) Reject("PREFAB_UNAVAILABLE_OR_MISSING_SCRIPT");
            var targets = new HashSet<SkinnedMeshRenderer>();
            foreach (PreparedTask plan in plans)
            {
                ResolvePrepared(plan, prefab);
                if (!targets.Add(plan.target)) Reject("TARGET_DUPLICATE");
            }
            foreach (PreparedTask plan in plans)
            {
                CheckSourceHashes(plan.task);
                string sourcePath = AssetDatabase.GUIDToAssetPath(plan.task.source_model_guid);
                if (!FileHash(Disk(sourcePath) + ".meta").Equals(plan.sourceMetaHash,
                    StringComparison.OrdinalIgnoreCase)) Reject("SOURCE_RESTORE_FAILED");
            }
            SaveVariant(plans, prefab);
            Debug.Log("VAPB_MODEL_SKIN_VARIANT_APPLIED=" + plans.Count);
            return true;
        }
        catch (Exception error)
        {
            Debug.LogError("VAPB_MODEL_SKIN_VARIANT_REJECTED=" + SafeError(error));
            return false;
        }
    }

    internal static bool IsWitnessImport(string path) { return !String.IsNullOrEmpty(witnessPath) && path == witnessPath; }
    internal static bool IsExpectedWitnessUid(string uid) { return witnessUids != null && witnessUids.Contains(uid); }
    internal static void MarkUnexpectedWitnessUid() { unexpectedWitnessUid = true; }
    internal static void CountWitnessCallback(string uid)
    {
        callbackCounts[uid] = callbackCounts.TryGetValue(uid, out int count) ? count + 1 : 1;
    }
    internal static bool IsAuthorizedEditedModel(string path)
    {
        string guid = AssetDatabase.AssetPathToGUID(path);
        if (!ValidGuid(guid) || !path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase)) return false;
        foreach (Task task in AuthorizedTasks()) if (task.model_guid == guid) return true;
        return false;
    }
    internal static bool IsAuthorizedRealization(string path, string id)
    {
        string guid = AssetDatabase.AssetPathToGUID(path);
        foreach (Task task in AuthorizedTasks())
            if (task.model_guid == guid && task.realization_id == id) return true;
        return false;
    }
    internal static bool IsAuthorizedBone(string path, string id)
    {
        string guid = AssetDatabase.AssetPathToGUID(path);
        foreach (Task task in AuthorizedTasks())
            if (task.model_guid == guid)
                foreach (BoneMapping bone in task.bone_mappings)
                    if (bone.edited_bone_realization_id == id) return true;
        return false;
    }
    private static List<Task> AuthorizedTasks()
    {
        const string folder = "Assets/VAPBExport";
        var authorized = new List<Task>();
        if (!AssetDatabase.IsValidFolder(folder)) return authorized;
        foreach (string guid in AssetDatabase.FindAssets("t:TextAsset", new[] { folder }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            try
            {
                Manifest manifest = ReadManifest(path);
                if (manifest == null || manifest.schema_version != Schema ||
                    manifest.reference_rebind_tasks == null || manifest.reference_rebind_tasks.Length == 0)
                    continue;
                ValidateBatch(manifest.reference_rebind_tasks);
                foreach (Task task in manifest.reference_rebind_tasks)
                {
                    string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
                    if (!FbxPath(modelPath) || !FileHash(Disk(modelPath)).Equals(task.model_sha256,
                        StringComparison.OrdinalIgnoreCase)) Reject("SOURCE_HASH_OR_PATH_MISMATCH");
                }
                authorized.AddRange(manifest.reference_rebind_tasks);
            }
            catch { /* Unreadable manifest does not authorize an import. */ }
        }
        return authorized;
    }

    private static void ValidateBatch(Task[] tasks)
    {
        if (tasks == null || tasks.Length == 0) Reject("MANIFEST_UNSUPPORTED");
        var realizations = new HashSet<string>(StringComparer.Ordinal);
        var sourceGuids = new HashSet<string>(StringComparer.Ordinal);
        var editedGuids = new HashSet<string>(StringComparer.Ordinal);
        foreach (Task task in tasks)
        {
            if (task == null) Reject("MANIFEST_UNSUPPORTED");
            ValidateTask(task);
            if (task.prefab_guid != tasks[0].prefab_guid ||
                task.prefab_source_sha256 != tasks[0].prefab_source_sha256 ||
                task.variant_path != tasks[0].variant_path ||
                !realizations.Add(task.realization_id) ||
                !editedGuids.Add(task.model_guid)) Reject("TASK_BATCH_INVALID");
            sourceGuids.Add(task.source_model_guid);
        }
        foreach (string guid in editedGuids)
            if (sourceGuids.Contains(guid)) Reject("TASK_BATCH_INVALID");
    }

    private static void CheckSourceHashes(Task task)
    {
        string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
        string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
        string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
        if (!PrefabPath(prefabPath) || !FbxPath(sourcePath) || !FbxPath(editedPath) ||
            sourcePath == editedPath || !FileHash(Disk(sourcePath)).Equals(task.source_model_sha256,
                StringComparison.OrdinalIgnoreCase) || !FileHash(Disk(editedPath)).Equals(task.model_sha256,
                StringComparison.OrdinalIgnoreCase)) Reject("SOURCE_HASH_OR_PATH_MISMATCH");
        if (!FileHash(Disk(prefabPath)).Equals(task.prefab_source_sha256, StringComparison.OrdinalIgnoreCase))
            Reject("STALE_PREFAB_SOURCE");
        if (task.kind == DirectKind) return;
        foreach (InstanceEdge edge in task.instance_edges)
        {
            string path = AssetDatabase.GUIDToAssetPath(edge.container_guid);
            if (!PrefabPath(path) || !FileHash(Disk(path)).Equals(edge.container_sha256,
                StringComparison.OrdinalIgnoreCase)) Reject("STALE_INSTANCE_EDGE");
        }
    }

    private static PreparedTask PrepareWitness(Task task)
    {
        CheckSourceHashes(task);
        string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
        string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
        byte[] sourceBytes = File.ReadAllBytes(Disk(sourcePath));
        byte[] sourceMeta = File.ReadAllBytes(Disk(sourcePath) + ".meta");
        bool direct = task.kind == DirectKind;
        if (!direct)
        {
            if (task.instance_edges[0].container_guid != task.prefab_guid ||
                task.instance_edges[task.instance_edges.Length - 1].source_guid != task.source_model_guid)
                Reject("EDGE_CHAIN_INVALID");
            for (int i = 1; i < task.instance_edges.Length; i++)
                if (task.instance_edges[i - 1].source_guid != task.instance_edges[i].container_guid)
                    Reject("EDGE_CHAIN_INVALID");
        }

        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (prefab == null || HasMissingScripts(prefab)) Reject("PREFAB_UNAVAILABLE_OR_MISSING_SCRIPT");
        byte[] noop = Payload(task.witness_noop_path, task.witness_noop_sha256);
        byte[] witness = Payload(task.witness_path, task.witness_sha256);
        WitnessResult mapping = RunWitness(sourcePath, task, sourceBytes, sourceMeta, noop, witness);
        return new PreparedTask { task = task, witness = mapping,
            sourceMetaHash = HashBytes(sourceMeta) };
    }

    private static void ResolvePrepared(PreparedTask plan, GameObject prefab)
    {
        Task task = plan.task;
        WitnessResult mapping = plan.witness;
        string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
        string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
        string sourceGuid = task.source_model_guid;
        bool direct = task.kind == DirectKind;
        SkinnedMeshRenderer target = direct ? ResolveDirectOccurrence(prefab, task, mapping.meshId) :
            ResolveOccurrence(prefab, task, mapping.rendererId);
        if (target.sharedMesh == null || target.bones == null || target.bones.Length == 0 ||
            target.rootBone == null) Reject("SOURCE_SKIN_UNSUPPORTED");
        string[] targetBoneIds = null;
        SkinnedMeshRenderer sourceRenderer = direct ?
            SourceRendererById(sourcePath, sourceGuid, mapping.rendererId) :
            SourceLeaf(target, task, out targetBoneIds);
        if (sourceRenderer == null || sourceRenderer.sharedMesh == null) Reject("SOURCE_SKIN_UNSUPPORTED");
        if (LocalId(sourceRenderer, sourceGuid) != mapping.rendererId ||
            LocalId(sourceRenderer.sharedMesh, sourceGuid) != mapping.meshId)
            Reject("SOURCE_ID_DRIFT");
        SourceIdentity source = direct ?
            ResolveDirectSourceIdentity(target, sourceRenderer, task, mapping) :
            ResolveSourceIdentity(target, sourceRenderer, sourceGuid, targetBoneIds);
        if (!mapping.transformIds.TryGetValue(task.source_model_uid, out long mappedRendererTransform) ||
            mappedRendererTransform != LocalId(sourceRenderer.transform, sourceGuid))
            Reject("WITNESS_RENDERER_MISMATCH");
        var uidByTransform = new Dictionary<long, string>();
        foreach (KeyValuePair<string, long> row in mapping.transformIds)
        {
            if (uidByTransform.ContainsKey(row.Value)) Reject("WITNESS_UID_AMBIGUOUS");
            uidByTransform.Add(row.Value, row.Key);
        }
        for (int i = 0; i < source.sourceBoneUids.Length; i++)
        {
            long id = ParseId(source.sourceBoneUids[i]);
            if (!uidByTransform.TryGetValue(id, out string uid)) Reject("WITNESS_BONE_MISSING");
            source.sourceBoneUids[i] = uid;
        }
        if (!uidByTransform.TryGetValue(ParseId(source.rootUid), out string rootUid))
            Reject("WITNESS_BONE_MISSING");
        source.rootUid = rootUid;
        source.bonesByUid.Clear();
        for (int i = 0; i < source.sourceBoneUids.Length; i++)
            source.bonesByUid.Add(source.sourceBoneUids[i], target.bones[i]);
        if (!source.bonesByUid.ContainsKey(source.rootUid))
            source.bonesByUid.Add(source.rootUid, target.rootBone);
        EditedIdentity edited = ResolveEdited(task, editedPath, mapping, source);
        CheckSkinCompatibility(mapping, target, edited, source, direct);
        plan.target = target;
        plan.source = source;
        plan.edited = edited;
    }

    private static void ValidateTask(Task task)
    {
        bool direct = task.kind == DirectKind;
        if ((task.kind != Kind && !direct) || !ValidGuid(task.prefab_guid) || !ValidGuid(task.source_model_guid) ||
            !ValidGuid(task.model_guid) || !ValidSha(task.prefab_source_sha256) ||
            !ValidSha(task.source_model_sha256) || !ValidSha(task.model_sha256) ||
            !ValidSha(task.witness_noop_sha256) || !ValidSha(task.witness_sha256) ||
            !ValidUid(task.source_model_uid) || String.IsNullOrEmpty(task.realization_id) ||
            task.instance_edges == null || (direct ? task.instance_edges.Length != 0 : task.instance_edges.Length == 0) ||
            task.bone_mappings == null || task.bone_mappings.Length == 0 ||
            task.source_model_uids == null || task.source_model_uids.Length == 0 ||
            !PayloadPath(task.witness_noop_path) || !PayloadPath(task.witness_path) ||
            !VariantPath(task.variant_path)) Reject("TASK_INVALID");
        var allUids = new HashSet<string>(StringComparer.Ordinal);
        foreach (string uid in task.source_model_uids)
            if (!ValidUid(uid) || !allUids.Add(uid)) Reject("SOURCE_UID_SET_INVALID");
        if (!allUids.Contains(task.source_model_uid)) Reject("SOURCE_UID_SET_INVALID");
        var receipts = new HashSet<string>(StringComparer.Ordinal);
        var boneUids = new HashSet<string>(StringComparer.Ordinal);
        foreach (BoneMapping bone in task.bone_mappings)
            if (bone == null || String.IsNullOrEmpty(bone.edited_bone_realization_id) ||
                !ValidUid(bone.source_model_uid) || !allUids.Contains(bone.source_model_uid) ||
                !receipts.Add(bone.edited_bone_realization_id) || !boneUids.Add(bone.source_model_uid))
                Reject("BONE_MAPPING_INVALID");
        for (int i = 0; i < task.instance_edges.Length; i++)
        {
            InstanceEdge edge = task.instance_edges[i];
            if (edge == null || !ValidGuid(edge.container_guid) || !ValidGuid(edge.source_guid) ||
                !ValidSha(edge.container_sha256)) Reject("EDGE_INVALID");
            ParseId(edge.instance_file_id);
        }
        if (direct)
        {
            if (task.renderer_candidates == null || task.renderer_candidates.Length == 0)
                Reject("DIRECT_CANDIDATES_INVALID");
            var rendererIds = new HashSet<long>();
            foreach (RendererCandidate candidate in task.renderer_candidates)
            {
                if (candidate == null || candidate.bone_transform_file_ids == null ||
                    candidate.bone_transform_file_ids.Length == 0 ||
                    !rendererIds.Add(ParseId(candidate.renderer_file_id)))
                    Reject("DIRECT_CANDIDATES_INVALID");
                ParseId(candidate.source_mesh_file_id);
                ParseId(candidate.root_bone_transform_file_id);
                var bones = new HashSet<long>();
                foreach (string value in candidate.bone_transform_file_ids)
                    if (!bones.Add(ParseId(value))) Reject("DIRECT_CANDIDATES_INVALID");
            }
        }
        else if (task.renderer_candidates != null && task.renderer_candidates.Length != 0)
            Reject("TASK_INVALID");
    }

    private static Manifest ReadManifest(string path)
    {
        if (String.IsNullOrEmpty(path) || !path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal) ||
            !path.EndsWith(".json", StringComparison.OrdinalIgnoreCase) || path.Contains("..") ||
            AssetDatabase.LoadAssetAtPath<TextAsset>(path) == null) Reject("MANIFEST_UNAVAILABLE");
        return JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(path)));
    }

    private static bool PrefabPath(string path) { return !String.IsNullOrEmpty(path) && path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase); }
    private static bool FbxPath(string path) { return !String.IsNullOrEmpty(path) && path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase); }
    private static bool PayloadPath(string path) { return !String.IsNullOrEmpty(path) && path.StartsWith("Assets/VAPBExport/", StringComparison.Ordinal) && path.EndsWith(".bytes", StringComparison.OrdinalIgnoreCase) && !path.Contains(".."); }
    private static bool VariantPath(string path) { return !String.IsNullOrEmpty(path) && path.StartsWith("Assets/VAPBExport/EditedVariant_", StringComparison.Ordinal) && path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase) && !path.Contains(".."); }
    private static bool ValidGuid(string value) { return value != null && Regex.IsMatch(value, "^[0-9a-fA-F]{32}$"); }
    private static bool ValidSha(string value) { return value != null && Regex.IsMatch(value, "^[0-9a-fA-F]{64}$"); }
    private static bool ValidUid(string value) { return value != null && Int64.TryParse(value, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out long id) && id != 0 && id.ToString(CultureInfo.InvariantCulture) == value; }
    private static long ParseId(string value) { if (!ValidUid(value)) Reject("LOCAL_ID_INVALID"); return Int64.Parse(value, CultureInfo.InvariantCulture); }
    private static string Disk(string path) { if (String.IsNullOrEmpty(path) || !path.StartsWith("Assets/", StringComparison.Ordinal) || path.Contains("..")) Reject("PATH_INVALID"); return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static byte[] Payload(string path, string hash) { byte[] bytes = File.ReadAllBytes(Disk(path)); if (bytes.Length == 0 || !HashBytes(bytes).Equals(hash, StringComparison.OrdinalIgnoreCase)) Reject("PAYLOAD_HASH_MISMATCH"); return bytes; }
    private static string FileHash(string path) { return HashBytes(File.ReadAllBytes(path)); }
    private static string HashBytes(byte[] bytes) { using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    private static void Reject(string code) { throw new InvalidOperationException(code); }
    private static string SafeError(Exception error) { return error is InvalidOperationException && Regex.IsMatch(error.Message, "^[A-Z_]+$") ? error.Message : "UNEXPECTED_EXCEPTION"; }

    private static SkinnedMeshRenderer ResolveOccurrence(GameObject prefab, Task task, long leafRendererId)
    {
        SkinnedMeshRenderer found = null;
        foreach (SkinnedMeshRenderer skin in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (MatchesOccurrence(skin, task, leafRendererId))
            {
                if (found != null) Reject("OCCURRENCE_AMBIGUOUS");
                found = skin;
            }
        }
        if (found == null) Reject("OCCURRENCE_NOT_FOUND");
        return found;
    }

    private static SkinnedMeshRenderer ResolveDirectOccurrence(GameObject prefab, Task task, long meshId)
    {
        RendererCandidate selected = null;
        foreach (RendererCandidate candidate in task.renderer_candidates)
            if (ParseId(candidate.source_mesh_file_id) == meshId)
            {
                if (selected != null) Reject("DIRECT_OCCURRENCE_AMBIGUOUS");
                selected = candidate;
            }
        if (selected == null) Reject("DIRECT_OCCURRENCE_NOT_FOUND");
        SkinnedMeshRenderer found = null;
        foreach (SkinnedMeshRenderer skin in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (PrefabUtility.IsPartOfPrefabInstance(skin) ||
                PrefabUtility.GetCorrespondingObjectFromSource(skin) != null ||
                skin.sharedMesh == null ||
                AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(skin.sharedMesh)) !=
                    task.source_model_guid) continue;
            if (LocalId(skin.sharedMesh, task.source_model_guid) != meshId) continue;
            if (found != null) Reject("DIRECT_OCCURRENCE_AMBIGUOUS");
            found = skin;
        }
        if (found == null || LocalId(found, task.prefab_guid) != ParseId(selected.renderer_file_id))
            Reject("DIRECT_OCCURRENCE_NOT_FOUND");
        if (found.bones == null || found.bones.Length != selected.bone_transform_file_ids.Length ||
            found.rootBone == null) Reject("DIRECT_BONES_MISMATCH");
        for (int i = 0; i < found.bones.Length; i++)
            if (LocalId(found.bones[i], task.prefab_guid) != ParseId(selected.bone_transform_file_ids[i]))
                Reject("DIRECT_BONES_MISMATCH");
        if (LocalId(found.rootBone, task.prefab_guid) != ParseId(selected.root_bone_transform_file_id))
            Reject("DIRECT_ROOT_MISMATCH");
        return found;
    }

    private static SkinnedMeshRenderer SourceRendererById(string path, string guid, long rendererId)
    {
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (root == null) Reject("SOURCE_MODEL_UNAVAILABLE");
        SkinnedMeshRenderer found = null;
        foreach (SkinnedMeshRenderer skin in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            if (LocalId(skin, guid) == rendererId)
            {
                if (found != null) Reject("SOURCE_RENDERER_AMBIGUOUS");
                found = skin;
            }
        if (found == null) Reject("SOURCE_RENDERER_MISSING");
        return found;
    }

    private static bool MatchesOccurrence(SkinnedMeshRenderer renderer, Task task, long leafRendererId)
    {
        UnityEngine.Object current = renderer;
        for (int i = 0; i < task.instance_edges.Length; i++)
        {
            InstanceEdge edge = task.instance_edges[i];
            string path = AssetDatabase.GetAssetPath(current);
            if (AssetDatabase.AssetPathToGUID(path) != edge.container_guid) return false;
            UnityEngine.Object source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (!(source is SkinnedMeshRenderer) || source == current ||
                AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(source)) != edge.source_guid)
                return false;
            UnityEngine.Object handle = PrefabUtility.GetPrefabInstanceHandle(current);
            if (handle == null || LocalId(handle, edge.container_guid) != ParseId(edge.instance_file_id) ||
                !SerializedEdgeMatches(path, ParseId(edge.instance_file_id), edge.source_guid)) return false;
            current = source;
        }
        return AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(current)) == task.source_model_guid &&
            PrefabUtility.GetCorrespondingObjectFromSource(current) == null &&
            current is SkinnedMeshRenderer && LocalId(current, task.source_model_guid) == leafRendererId;
    }

    private static SkinnedMeshRenderer SourceLeaf(SkinnedMeshRenderer renderer, Task task, out string[] targetBoneIds)
    {
        var chain = new List<SkinnedMeshRenderer>();
        UnityEngine.Object current = renderer;
        chain.Add(renderer);
        for (int i = 0; i < task.instance_edges.Length; i++)
        {
            current = PrefabUtility.GetCorrespondingObjectFromSource(current);
            SkinnedMeshRenderer skin = current as SkinnedMeshRenderer;
            if (skin == null) Reject("SOURCE_CHAIN_INVALID");
            chain.Add(skin);
        }
        var leaf = (SkinnedMeshRenderer)current;
        if (leaf.bones.Length != renderer.bones.Length || leaf.rootBone == null) Reject("SOURCE_BONES_MISMATCH");
        targetBoneIds = new string[renderer.bones.Length];
        for (int i = 0; i < renderer.bones.Length; i++)
        {
            Transform source = FollowSource(renderer.bones[i], task.instance_edges.Length);
            if (source == null || source != leaf.bones[i]) Reject("SOURCE_BONES_MISMATCH");
            targetBoneIds[i] = LocalId(source, task.source_model_guid).ToString(CultureInfo.InvariantCulture);
        }
        if (FollowSource(renderer.rootBone, task.instance_edges.Length) != leaf.rootBone)
            Reject("SOURCE_ROOT_MISMATCH");
        return leaf;
    }

    private static Transform FollowSource(Transform target, int hops)
    {
        UnityEngine.Object current = target;
        for (int i = 0; i < hops; i++)
        {
            if (current == null) return null;
            current = PrefabUtility.GetCorrespondingObjectFromSource(current);
        }
        return current as Transform;
    }

    private static bool SerializedEdgeMatches(string path, long id, string sourceGuid)
    {
        string yaml = File.ReadAllText(Disk(path));
        MatchCollection headings = Regex.Matches(yaml, @"(?m)^--- !u!(\d+) &(-?\d+)\s*$");
        int matches = 0;
        for (int i = 0; i < headings.Count; i++)
        {
            if (headings[i].Groups[1].Value != "1001" || headings[i].Groups[2].Value !=
                id.ToString(CultureInfo.InvariantCulture)) continue;
            int start = headings[i].Index + headings[i].Length;
            int end = i + 1 < headings.Count ? headings[i + 1].Index : yaml.Length;
            Match source = Regex.Match(yaml.Substring(start, end - start),
                @"m_SourcePrefab:\s*\{[^}]*\bguid:\s*([0-9a-fA-F]{32})\b", RegexOptions.Singleline);
            if (source.Success && source.Groups[1].Value.Equals(sourceGuid, StringComparison.OrdinalIgnoreCase))
                matches++;
        }
        return matches == 1;
    }

    private static SourceIdentity ResolveSourceIdentity(SkinnedMeshRenderer target,
        SkinnedMeshRenderer sourceRenderer, string guid, string[] sourceBoneIds)
    {
        var result = new SourceIdentity { renderer = sourceRenderer, sourceBoneUids = sourceBoneIds };
        if (target.bones.Length != sourceRenderer.bones.Length || target.rootBone == null)
            Reject("SOURCE_SKIN_UNSUPPORTED");
        if (sourceRenderer.sharedMesh.bindposes.Length != target.bones.Length ||
            target.sharedMesh != sourceRenderer.sharedMesh) Reject("SOURCE_MESH_MISMATCH");
        for (int i = 0; i < target.bones.Length; i++)
            if (target.bones[i] == null || sourceRenderer.bones[i] == null ||
                !SameMatrix(sourceRenderer.sharedMesh.bindposes[i],
                    target.bones[i].worldToLocalMatrix * target.transform.localToWorldMatrix, 0.001f))
                Reject("SOURCE_REST_MISMATCH");
        result.rootUid = LocalId(sourceRenderer.rootBone, guid).ToString(CultureInfo.InvariantCulture);
        return result;
    }

    private static SourceIdentity ResolveDirectSourceIdentity(SkinnedMeshRenderer target,
        SkinnedMeshRenderer sourceRenderer, Task task, WitnessResult witness)
    {
        string sourceGuid = task.source_model_guid;
        if (target.sharedMesh != sourceRenderer.sharedMesh ||
            LocalId(target.sharedMesh, sourceGuid) != witness.meshId ||
            sourceRenderer.bones == null || target.bones == null ||
            sourceRenderer.bones.Length != target.bones.Length ||
            sourceRenderer.bones.Length == 0 || sourceRenderer.rootBone == null ||
            target.rootBone == null || witness.sourceBindposes == null ||
            witness.sourceBindposes.Length != target.bones.Length)
            Reject("DIRECT_SOURCE_MESH_OR_BONES_MISMATCH");
        var result = new SourceIdentity { renderer = sourceRenderer,
            sourceBoneUids = new string[target.bones.Length] };
        var sourceIds = new HashSet<long>();
        var targetIds = new HashSet<long>();
        int sourceRoot = -1;
        for (int i = 0; i < target.bones.Length; i++)
        {
            Transform sourceBone = sourceRenderer.bones[i], targetBone = target.bones[i];
            if (sourceBone == null || targetBone == null ||
                !sourceIds.Add(LocalId(sourceBone, sourceGuid)) ||
                !targetIds.Add(LocalId(targetBone, task.prefab_guid)) ||
                !FiniteMatrix(sourceBone.worldToLocalMatrix * sourceRenderer.transform.localToWorldMatrix) ||
                !FiniteMatrix(targetBone.worldToLocalMatrix * target.transform.localToWorldMatrix))
                Reject("DIRECT_SOURCE_REST_MISMATCH");
            result.sourceBoneUids[i] = LocalId(sourceBone, sourceGuid).ToString(CultureInfo.InvariantCulture);
            if (sourceBone == sourceRenderer.rootBone) sourceRoot = i;
        }
        if (sourceRoot < 0) Reject("DIRECT_ROOT_MISMATCH");
        // Shared Mesh bindposes and m_Bones use the same slot indices; current target pose may differ.
        for (int i = 0; i < target.bones.Length; i++)
        {
            int sourceParent = Array.IndexOf(sourceRenderer.bones, sourceRenderer.bones[i].parent);
            int targetParent = Array.IndexOf(target.bones, target.bones[i].parent);
            if (sourceParent != targetParent || (i != sourceRoot && sourceParent < 0) ||
                (i == sourceRoot && sourceParent >= 0)) Reject("DIRECT_HIERARCHY_MISMATCH");
        }
        result.rootUid = LocalId(sourceRenderer.rootBone, sourceGuid).ToString(CultureInfo.InvariantCulture);
        return result;
    }

    private static WitnessResult RunWitness(string sourcePath, Task task, byte[] original,
        byte[] originalMeta, byte[] noop, byte[] witness)
    {
        byte[] comparisonMeta = null;
        Snapshot baseline = null;
        WitnessResult result = null;
        bool equivalentAfterRestore = false;
        bool metaStable = false;
        bool restored = false;
        try
        {
            ModelImporter importer = AssetImporter.GetAtPath(sourcePath) as ModelImporter;
            if (importer == null) Reject("SOURCE_IMPORTER_MISSING");
            if (!importer.isReadable)
            {
                importer.isReadable = true;
                importer.SaveAndReimport();
            }
            comparisonMeta = File.ReadAllBytes(Disk(sourcePath) + ".meta");
            baseline = Capture(sourcePath, task.source_model_guid);
            File.WriteAllBytes(Disk(sourcePath), noop);
            AssetDatabase.ImportAsset(sourcePath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            if (!baseline.Same(Capture(sourcePath, task.source_model_guid)) ||
                !EqualBytes(comparisonMeta, File.ReadAllBytes(Disk(sourcePath) + ".meta")))
                Reject("NOOP_SEMANTIC_DRIFT");
            callbackCounts.Clear();
            unexpectedWitnessUid = false;
            witnessPath = sourcePath;
            witnessUids = new HashSet<string>(task.source_model_uids, StringComparer.Ordinal);
            File.WriteAllBytes(Disk(sourcePath), witness);
            AssetDatabase.ImportAsset(sourcePath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            if (!baseline.Same(Capture(sourcePath, task.source_model_guid)) ||
                !EqualBytes(comparisonMeta, File.ReadAllBytes(Disk(sourcePath) + ".meta")))
                Reject("WITNESS_SEMANTIC_DRIFT");
            result = InspectWitness(sourcePath, task);
            if (!baseline.renderers.ContainsKey(result.rendererId) ||
                !baseline.meshes.ContainsKey(result.meshId)) Reject("WITNESS_SOURCE_ID_MISSING");
            Mesh witnessedMesh = SourceMeshById(sourcePath, task.source_model_guid, result.meshId);
            result.sourceLayout = CaptureLayout(witnessedMesh);
            result.sourceBindposes = witnessedMesh.bindposes;
        }
        finally
        {
            witnessPath = null;
            witnessUids = null;
            unexpectedWitnessUid = false;
            callbackCounts.Clear();
            try
            {
                File.WriteAllBytes(Disk(sourcePath), original);
                File.WriteAllBytes(Disk(sourcePath) + ".meta", comparisonMeta ?? originalMeta);
                AssetDatabase.ImportAsset(sourcePath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                equivalentAfterRestore = baseline != null && baseline.Same(Capture(sourcePath, task.source_model_guid));
                metaStable = comparisonMeta != null &&
                    EqualBytes(comparisonMeta, File.ReadAllBytes(Disk(sourcePath) + ".meta"));
                File.WriteAllBytes(Disk(sourcePath) + ".meta", originalMeta);
                AssetDatabase.ImportAsset(sourcePath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                restored = EqualBytes(original, File.ReadAllBytes(Disk(sourcePath))) &&
                    EqualBytes(originalMeta, File.ReadAllBytes(Disk(sourcePath) + ".meta"));
            }
            catch { Reject("SOURCE_RESTORE_FAILED"); }
            if (!equivalentAfterRestore || !metaStable || !restored) Reject("SOURCE_RESTORE_FAILED");
        }
        return result;
    }

    private static WitnessResult InspectWitness(string sourcePath, Task task)
    {
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath);
        var result = new WitnessResult();
        var expected = new HashSet<string>(task.source_model_uids, StringComparer.Ordinal);
        foreach (VapbRealizationMarker marker in model.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            string uid = marker.sourceModelUid;
            if (!expected.Remove(uid) || !callbackCounts.TryGetValue(uid, out int count) || count != 1 ||
                result.transformIds.ContainsKey(uid))
                Reject("WITNESS_UID_AMBIGUOUS");
            result.transformIds.Add(uid, LocalId(marker.transform, task.source_model_guid));
            if (uid != task.source_model_uid) continue;
            SkinnedMeshRenderer[] skins = marker.GetComponents<SkinnedMeshRenderer>();
            if (skins.Length != 1 || marker.GetComponents<Renderer>().Length != 1)
                Reject("WITNESS_RENDERER_AMBIGUOUS");
            result.rendererId = LocalId(skins[0], task.source_model_guid);
            result.meshId = LocalId(skins[0].sharedMesh, task.source_model_guid);
        }
        if (unexpectedWitnessUid || expected.Count != 0 || callbackCounts.Count != task.source_model_uids.Length ||
            result.rendererId == 0 || result.meshId == 0)
            Reject("WITNESS_UID_SET_MISMATCH");
        return result;
    }

    private static void RefreshEditedModel(string editedPath)
    {
        ModelImporter importer = AssetImporter.GetAtPath(editedPath) as ModelImporter;
        if (importer == null) Reject("EDITED_IMPORTER_MISSING");
        if (!importer.isReadable)
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
        }
        else AssetDatabase.ImportAsset(editedPath,
            ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
    }

    private static EditedIdentity ResolveEdited(Task task, string editedPath, WitnessResult witness,
        SourceIdentity source)
    {
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(editedPath);
        if (root == null) Reject("EDITED_MODEL_UNAVAILABLE");
        SkinnedMeshRenderer found = null;
        var markerCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (VapbRealizationMarker marker in root.GetComponentsInChildren<VapbRealizationMarker>(true))
        {
            if (!String.IsNullOrEmpty(marker.boneRealizationId))
                markerCounts[marker.boneRealizationId] = markerCounts.TryGetValue(marker.boneRealizationId,
                    out int count) ? count + 1 : 1;
            if (marker.realizationId != task.realization_id) continue;
            if (found != null || marker.GetComponents<Renderer>().Length != 1)
                Reject("EDITED_RENDERER_AMBIGUOUS");
            found = marker.GetComponent<SkinnedMeshRenderer>();
            if (found == null || found.sharedMesh == null) Reject("EDITED_RENDERER_AMBIGUOUS");
        }
        if (found == null || found.bones == null || found.bones.Length != source.sourceBoneUids.Length ||
            found.rootBone == null) Reject("EDITED_BONES_INVALID");
        var receiptToUid = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (BoneMapping bone in task.bone_mappings)
            receiptToUid.Add(bone.edited_bone_realization_id, bone.source_model_uid);
        var edited = new EditedIdentity { renderer = found, mesh = found.sharedMesh,
            editedBoneUids = new string[found.bones.Length] };
        var seen = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < found.bones.Length; i++)
        {
            string receipt = found.bones[i] == null ? null :
                found.bones[i].GetComponent<VapbRealizationMarker>()?.boneRealizationId;
            string uid = null;
            if (receipt == null || !receiptToUid.TryGetValue(receipt, out uid) ||
                !markerCounts.TryGetValue(receipt, out int count) || count != 1 ||
                !source.bonesByUid.ContainsKey(uid) || !seen.Add(uid)) Reject("EDITED_BONES_INVALID");
            edited.editedBoneUids[i] = uid;
        }
        string rootReceipt = found.rootBone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
        string rootUid = null;
        if (rootReceipt == null || !receiptToUid.TryGetValue(rootReceipt, out rootUid) ||
            rootUid != source.rootUid || !markerCounts.TryGetValue(rootReceipt, out int rootCount) ||
            rootCount != 1) Reject("EDITED_ROOT_INVALID");
        edited.rootUid = rootUid;
        seen.Add(rootUid);
        if (seen.Count != receiptToUid.Count) Reject("BONE_MAPPING_INVALID");
        for (int i = 0; i < found.bones.Length; i++)
        {
            Transform sourceBone = source.bonesByUid[edited.editedBoneUids[i]];
            string sourceParentUid = null;
            foreach (KeyValuePair<string, Transform> row in source.bonesByUid)
                if (row.Value == sourceBone.parent) sourceParentUid = row.Key;
            string editedParentReceipt = found.bones[i].parent == null ? null :
                found.bones[i].parent.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
            string editedParentUid = editedParentReceipt != null &&
                receiptToUid.TryGetValue(editedParentReceipt, out string parentUid) ? parentUid : null;
            if (sourceParentUid != editedParentUid) Reject("BONE_HIERARCHY_CHANGED");
            if (sourceParentUid == null &&
                (edited.editedBoneUids[i] != source.rootUid || found.bones[i] != found.rootBone))
                Reject("BONE_HIERARCHY_UNSUPPORTED");
        }
        return edited;
    }

    private static void CheckSkinCompatibility(WitnessResult witness,
        SkinnedMeshRenderer target, EditedIdentity edited, SourceIdentity source, bool direct)
    {
        MeshLayout old = witness.sourceLayout;
        Mesh mesh = edited.mesh;
        if (old == null || (!direct && old.vertexCount != mesh.vertexCount) ||
            old.topologies.Length != mesh.subMeshCount || mesh.bindposes.Length != edited.editedBoneUids.Length ||
            !SameBlendShapes(old, mesh)) Reject("TOPOLOGY_OR_LAYOUT_CHANGED");
        bool layoutChanged = old.vertexCount != mesh.vertexCount;
        for (int i = 0; i < old.topologies.Length; i++)
        {
            if (old.topologies[i] != mesh.GetTopology(i)) Reject("TOPOLOGY_OR_LAYOUT_CHANGED");
            int[] a = old.indices[i];
            int[] b = mesh.GetIndices(i);
            if (a.Length != b.Length) Reject("TOPOLOGY_OR_LAYOUT_CHANGED");
            for (int j = 0; j < a.Length; j++)
                if (a[j] != b[j])
                {
                    if (!direct) Reject("TOPOLOGY_OR_LAYOUT_CHANGED");
                    layoutChanged = true;
                }
        }
        if (direct)
        {
            if (layoutChanged && target.GetComponent<Cloth>() != null)
                Reject("CLOTH_INDEX_STATE_UNSUPPORTED");
            ValidateMeshStreams(mesh);
        }
        var sourceSlots = new Dictionary<string, int>(StringComparer.Ordinal);
        if (direct)
            for (int i = 0; i < source.sourceBoneUids.Length; i++)
                if (sourceSlots.ContainsKey(source.sourceBoneUids[i])) Reject("SOURCE_BONE_AMBIGUOUS");
                else sourceSlots.Add(source.sourceBoneUids[i], i);
        for (int i = 0; i < edited.editedBoneUids.Length; i++)
        {
            Matrix4x4 expected;
            if (direct)
            {
                int slot = -1;
                if (witness.sourceBindposes == null ||
                    !sourceSlots.TryGetValue(edited.editedBoneUids[i], out slot) ||
                    slot >= witness.sourceBindposes.Length) Reject("SOURCE_BINDPOSE_MISSING");
                expected = witness.sourceBindposes[slot];
            }
            else
            {
                Transform bone = source.bonesByUid[edited.editedBoneUids[i]];
                expected = bone.worldToLocalMatrix * target.transform.localToWorldMatrix;
            }
            if (!FiniteMatrix(mesh.bindposes[i]) || !FiniteMatrix(expected) ||
                !SameMatrix(mesh.bindposes[i], expected, 0.001f)) Reject("EDITED_REST_MISMATCH");
        }
        ValidateWeights(mesh, edited.editedBoneUids.Length);
    }

    private static void SaveVariant(List<PreparedTask> plans, GameObject original)
    {
        string path = plans[0].task.variant_path;
        string disk = Disk(path);
        if (File.Exists(disk) || File.Exists(disk + ".meta") || AssetDatabase.LoadAssetAtPath<GameObject>(path) != null)
        {
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing == null || PrefabUtility.GetPrefabAssetType(existing) != PrefabAssetType.Variant ||
                AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(existing)) !=
                    AssetDatabase.GetAssetPath(original)) Reject("VARIANT_PATH_OCCUPIED");
            VerifyVariant(existing, original, plans);
            return;
        }
        GameObject instance = PrefabUtility.InstantiatePrefab(original) as GameObject;
        if (instance == null) Reject("VARIANT_INSTANCE_FAILED");
        bool saved = false;
        try
        {
            if (HasMissingScripts(instance)) Reject("VARIANT_TARGET_MISSING");
            foreach (PreparedTask plan in plans)
            {
                SkinnedMeshRenderer target = null;
                foreach (SkinnedMeshRenderer skin in instance.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (PrefabUtility.GetCorrespondingObjectFromSource(skin) == plan.target)
                    {
                        if (target != null) Reject("VARIANT_AMBIGUOUS");
                        target = skin;
                    }
                if (target == null || target.rootBone == null) Reject("VARIANT_TARGET_MISSING");
                var bones = new Transform[plan.edited.editedBoneUids.Length];
                for (int i = 0; i < bones.Length; i++)
                {
                    Transform sourceBone = plan.source.bonesByUid[plan.edited.editedBoneUids[i]];
                    foreach (Transform transform in instance.GetComponentsInChildren<Transform>(true))
                        if (PrefabUtility.GetCorrespondingObjectFromSource(transform) == sourceBone)
                        {
                            if (bones[i] != null) Reject("VARIANT_BONE_AMBIGUOUS");
                            bones[i] = transform;
                        }
                    if (bones[i] == null) Reject("VARIANT_BONE_MISSING");
                }
                target.sharedMesh = plan.edited.mesh;
                target.bones = bones;
                PrefabUtility.RecordPrefabInstancePropertyModifications(target);
            }
            GameObject variant = PrefabUtility.SaveAsPrefabAsset(instance, path);
            if (variant == null) Reject("VARIANT_SAVE_FAILED");
            GameObject reloaded = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (reloaded == null || PrefabUtility.GetPrefabAssetType(reloaded) != PrefabAssetType.Variant)
                Reject("VARIANT_RELOAD_FAILED");
            VerifyVariant(reloaded, original, plans);
            saved = true;
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(instance);
            if (!saved && (File.Exists(disk) || File.Exists(disk + ".meta")))
            {
                AssetDatabase.DeleteAsset(path);
                if (File.Exists(disk) || File.Exists(disk + ".meta")) Reject("VARIANT_ROLLBACK_FAILED");
            }
        }
    }

    private static void VerifyVariant(GameObject variant, GameObject original,
        List<PreparedTask> plans)
    {
        var expected = new Dictionary<SkinnedMeshRenderer, PreparedTask>();
        foreach (PreparedTask plan in plans) expected.Add(plan.target, plan);
        if (HasMissingScripts(variant)) Reject("VARIANT_MISSING_SCRIPT");
        if (PrefabUtility.GetAddedComponents(variant).Count != 0 ||
            PrefabUtility.GetRemovedComponents(variant).Count != 0 ||
            PrefabUtility.GetAddedGameObjects(variant).Count != 0 ||
            PrefabUtility.GetRemovedGameObjects(variant).Count != 0)
            Reject("VARIANT_STRUCTURE_CHANGED");
        PropertyModification[] modifications = PrefabUtility.GetPropertyModifications(variant);
        if (modifications == null) Reject("VARIANT_MODIFICATIONS_UNAVAILABLE");
        foreach (PropertyModification mod in modifications)
        {
            if (mod == null || mod.target == null || String.IsNullOrEmpty(mod.propertyPath))
                Reject("VARIANT_MODIFICATION_UNKNOWN");
            bool skinBinding = mod.target is SkinnedMeshRenderer skinTarget &&
                expected.ContainsKey(skinTarget) &&
                (mod.propertyPath == "m_Mesh" || mod.propertyPath == "m_Bones.Array.size" ||
                 mod.propertyPath.StartsWith("m_Bones.Array.data[", StringComparison.Ordinal));
            bool rootDefault = PrefabUtility.IsDefaultOverride(mod) &&
                (mod.target == original || mod.target == original.transform);
            if (!skinBinding && !rootDefault) Reject("VARIANT_MODIFICATION_UNKNOWN");
        }
        Transform[] sourceTransforms = original.GetComponentsInChildren<Transform>(true);
        Transform[] variantTransforms = variant.GetComponentsInChildren<Transform>(true);
        if (sourceTransforms.Length != variantTransforms.Length) Reject("VARIANT_STRUCTURE_CHANGED");
        foreach (Transform transform in variantTransforms)
        {
            Transform corresponding = PrefabUtility.GetCorrespondingObjectFromSource(transform) as Transform;
            if (corresponding == null || transform.localPosition != corresponding.localPosition ||
                transform.localRotation != corresponding.localRotation ||
                transform.localScale != corresponding.localScale ||
                (transform != variant.transform && transform.name != corresponding.name))
                Reject("VARIANT_TRANSFORM_CHANGED");
        }
        Renderer[] sourceRenderers = original.GetComponentsInChildren<Renderer>(true);
        Renderer[] variantRenderers = variant.GetComponentsInChildren<Renderer>(true);
        if (sourceRenderers.Length != variantRenderers.Length) Reject("VARIANT_STRUCTURE_CHANGED");
        var matched = new HashSet<SkinnedMeshRenderer>();
        foreach (Renderer renderer in variantRenderers)
        {
            Renderer corresponding = PrefabUtility.GetCorrespondingObjectFromSource(renderer) as Renderer;
            if (corresponding == null || renderer.GetType() != corresponding.GetType() ||
                !SameMaterials(renderer.sharedMaterials, corresponding.sharedMaterials) ||
                renderer.enabled != corresponding.enabled) Reject("VARIANT_RENDERER_CHANGED");
            if (corresponding is SkinnedMeshRenderer originalSkin &&
                expected.TryGetValue(originalSkin, out PreparedTask plan))
            {
                SkinnedMeshRenderer skin = renderer as SkinnedMeshRenderer;
                if (skin == null || !matched.Add(originalSkin))
                    Reject("VARIANT_AMBIGUOUS");
                if (skin.sharedMesh != plan.edited.mesh || skin.rootBone == null ||
                    FollowSource(skin.rootBone, 1) != plan.target.rootBone ||
                    skin.bones.Length != plan.edited.editedBoneUids.Length) Reject("VARIANT_MISMATCH");
                for (int i = 0; i < skin.bones.Length; i++)
                    if (FollowSource(skin.bones[i], 1) !=
                        plan.source.bonesByUid[plan.edited.editedBoneUids[i]])
                        Reject("VARIANT_MISMATCH");
            }
            else if (renderer is SkinnedMeshRenderer otherSkin)
            {
                SkinnedMeshRenderer otherSource = (SkinnedMeshRenderer)corresponding;
                if (otherSkin.sharedMesh != otherSource.sharedMesh ||
                    FollowSource(otherSkin.rootBone, 1) != otherSource.rootBone ||
                    otherSkin.bones.Length != otherSource.bones.Length)
                    Reject("VARIANT_SIBLING_CHANGED");
                for (int i = 0; i < otherSkin.bones.Length; i++)
                    if (FollowSource(otherSkin.bones[i], 1) != otherSource.bones[i])
                        Reject("VARIANT_SIBLING_CHANGED");
            }
            else if (renderer is MeshRenderer direct)
            {
                MeshFilter filter = direct.GetComponent<MeshFilter>();
                MeshFilter originalFilter = corresponding.GetComponent<MeshFilter>();
                if (filter == null || originalFilter == null || filter.sharedMesh != originalFilter.sharedMesh)
                    Reject("VARIANT_SIBLING_CHANGED");
            }
        }
        if (matched.Count != plans.Count) Reject("VARIANT_MISMATCH");
    }

    private static bool HasMissingScripts(GameObject root)
    {
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
            if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject) != 0)
                return true;
        return false;
    }

    private static long LocalId(UnityEngine.Object value, string guid)
    {
        long id = 0;
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value,
                out string actual, out id) || actual != guid || id == 0) Reject("PUBLIC_ID_UNAVAILABLE");
        return id;
    }

    private static Mesh SourceMeshById(string path, string guid, long id)
    {
        Mesh found = null;
        foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
            if (asset is Mesh mesh && LocalId(mesh, guid) == id)
            {
                if (found != null) Reject("SOURCE_MESH_AMBIGUOUS");
                found = mesh;
            }
        if (found == null) Reject("SOURCE_MESH_MISSING");
        return found;
    }

    private static MeshLayout CaptureLayout(Mesh mesh)
    {
        var layout = new MeshLayout { vertexCount = mesh.vertexCount,
            topologies = new MeshTopology[mesh.subMeshCount], indices = new int[mesh.subMeshCount][],
            shapeNames = new string[mesh.blendShapeCount], frameWeights = new float[mesh.blendShapeCount][] };
        for (int i = 0; i < mesh.subMeshCount; i++)
        {
            layout.topologies[i] = mesh.GetTopology(i);
            layout.indices[i] = mesh.GetIndices(i);
        }
        for (int i = 0; i < mesh.blendShapeCount; i++)
        {
            layout.shapeNames[i] = mesh.GetBlendShapeName(i);
            layout.frameWeights[i] = new float[mesh.GetBlendShapeFrameCount(i)];
            for (int j = 0; j < layout.frameWeights[i].Length; j++)
                layout.frameWeights[i][j] = mesh.GetBlendShapeFrameWeight(i, j);
        }
        return layout;
    }

    private static bool SameBlendShapes(MeshLayout a, Mesh b)
    {
        if (a.shapeNames.Length != b.blendShapeCount) return false;
        for (int i = 0; i < a.shapeNames.Length; i++)
        {
            if (a.shapeNames[i] != b.GetBlendShapeName(i) ||
                a.frameWeights[i].Length != b.GetBlendShapeFrameCount(i)) return false;
            for (int j = 0; j < a.frameWeights[i].Length; j++)
                if (!Finite(a.frameWeights[i][j]) || !Finite(b.GetBlendShapeFrameWeight(i, j)) ||
                    Mathf.Abs(a.frameWeights[i][j] - b.GetBlendShapeFrameWeight(i, j)) > 0.0001f)
                    return false;
        }
        return true;
    }

    private static bool SameMaterials(Material[] a, Material[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    private static bool SameMatrix(Matrix4x4 a, Matrix4x4 b, float tolerance)
    {
        for (int i = 0; i < 16; i++)
            if (float.IsNaN(a[i]) || float.IsInfinity(a[i]) || float.IsNaN(b[i]) ||
                float.IsInfinity(b[i]) || Mathf.Abs(a[i] - b[i]) > tolerance) return false;
        return true;
    }

    private static bool FiniteMatrix(Matrix4x4 value)
    {
        for (int i = 0; i < 16; i++)
            if (float.IsNaN(value[i]) || float.IsInfinity(value[i])) return false;
        return true;
    }

    private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    private static bool Finite(Vector3 value) => Finite(value.x) && Finite(value.y) && Finite(value.z);
    private static bool Finite(Vector4 value) => Finite(value.x) && Finite(value.y) &&
        Finite(value.z) && Finite(value.w);

    private static void ValidateMeshStreams(Mesh mesh)
    {
        int count = mesh.vertexCount;
        if (count == 0) Reject("EDITED_STREAM_INVALID");
        Vector3[] vertices = mesh.vertices, normals = mesh.normals;
        Vector4[] tangents = mesh.tangents;
        Color[] colors = mesh.colors;
        if (vertices.Length != count || (normals.Length != 0 && normals.Length != count) ||
            (tangents.Length != 0 && tangents.Length != count) ||
            (colors.Length != 0 && colors.Length != count)) Reject("EDITED_STREAM_INVALID");
        foreach (Vector3 value in vertices) if (!Finite(value)) Reject("EDITED_STREAM_INVALID");
        foreach (Vector3 value in normals) if (!Finite(value)) Reject("EDITED_STREAM_INVALID");
        foreach (Vector4 value in tangents) if (!Finite(value)) Reject("EDITED_STREAM_INVALID");
        foreach (Color value in colors)
            if (!Finite(value.r) || !Finite(value.g) || !Finite(value.b) || !Finite(value.a))
                Reject("EDITED_STREAM_INVALID");
        var uvs = new List<Vector4>();
        for (int channel = 0; channel < 8; channel++)
        {
            uvs.Clear();
            mesh.GetUVs(channel, uvs);
            if (uvs.Count != 0 && uvs.Count != count) Reject("EDITED_STREAM_INVALID");
            foreach (Vector4 value in uvs) if (!Finite(value)) Reject("EDITED_STREAM_INVALID");
        }
        if (!Finite(mesh.bounds.center) || !Finite(mesh.bounds.extents))
            Reject("EDITED_STREAM_INVALID");
        for (int submesh = 0; submesh < mesh.subMeshCount; submesh++)
        {
            int[] indices = mesh.GetIndices(submesh);
            if (mesh.GetTopology(submesh) == MeshTopology.Triangles && indices.Length % 3 != 0)
                Reject("EDITED_STREAM_INVALID");
            foreach (int index in indices)
                if (index < 0 || index >= count) Reject("EDITED_STREAM_INVALID");
        }
        var deltaVertices = new Vector3[count];
        var deltaNormals = new Vector3[count];
        var deltaTangents = new Vector3[count];
        for (int shape = 0; shape < mesh.blendShapeCount; shape++)
            for (int frame = 0; frame < mesh.GetBlendShapeFrameCount(shape); frame++)
            {
                mesh.GetBlendShapeFrameVertices(shape, frame, deltaVertices, deltaNormals, deltaTangents);
                for (int vertex = 0; vertex < count; vertex++)
                    if (!Finite(deltaVertices[vertex]) || !Finite(deltaNormals[vertex]) ||
                        !Finite(deltaTangents[vertex])) Reject("EDITED_STREAM_INVALID");
            }
    }

    private static void ValidateWeights(Mesh mesh, int boneCount)
    {
        try
        {
            var counts = mesh.GetBonesPerVertex();
            var weights = mesh.GetAllBoneWeights();
            try
            {
                if (counts.Length != mesh.vertexCount) Reject("WEIGHTS_INVALID");
                int offset = 0;
                for (int vertex = 0; vertex < counts.Length; vertex++)
                {
                    int count = counts[vertex];
                    if (count == 0 || offset + count > weights.Length) Reject("WEIGHTS_INVALID");
                    float sum = 0;
                    for (int i = 0; i < count; i++)
                    {
                        var weight = weights[offset + i];
                        if (weight.boneIndex < 0 || weight.boneIndex >= boneCount ||
                            float.IsNaN(weight.weight) || float.IsInfinity(weight.weight) || weight.weight <= 0)
                            Reject("WEIGHTS_INVALID");
                        sum += weight.weight;
                    }
                    if (Mathf.Abs(sum - 1f) > 0.01f) Reject("WEIGHTS_INVALID");
                    offset += count;
                }
                if (offset != weights.Length) Reject("WEIGHTS_INVALID");
            }
            finally { counts.Dispose(); weights.Dispose(); }
        }
        catch (InvalidOperationException) { throw; }
        catch { Reject("WEIGHTS_INVALID"); }
    }

    private static Snapshot Capture(string path, string guid)
    {
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (root == null) Reject("SOURCE_IMPORT_FAILED");
        var snapshot = new Snapshot { guid = guid };
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            long id = LocalId(transform, guid);
            if (snapshot.transforms.ContainsKey(id)) Reject("DUPLICATE_SOURCE_ID");
            snapshot.transforms.Add(id, Hash(writer =>
            {
                writer.Write(transform.name);
                writer.Write(transform.parent == null ? 0L : LocalId(transform.parent, guid));
                Write(writer, transform.localPosition);
                Write(writer, transform.localRotation);
                Write(writer, transform.localScale);
                Write(writer, transform.localToWorldMatrix);
            }));
        }
        foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(path))
        {
            if (!(asset is Mesh mesh)) continue;
            long id = LocalId(mesh, guid);
            if (snapshot.meshes.ContainsKey(id)) Reject("DUPLICATE_SOURCE_ID");
            snapshot.meshes.Add(id, MeshSignature(mesh));
        }
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            if (!(renderer is SkinnedMeshRenderer) && !(renderer is MeshRenderer))
                Reject("SOURCE_RENDERER_UNSUPPORTED");
            long id = LocalId(renderer, guid);
            if (snapshot.renderers.ContainsKey(id)) Reject("DUPLICATE_SOURCE_ID");
            snapshot.renderers.Add(id, RendererSignature(renderer, guid));
        }
        if (snapshot.transforms.Count == 0 || snapshot.meshes.Count == 0 || snapshot.renderers.Count == 0)
            Reject("SOURCE_STRUCTURE_INVALID");
        return snapshot;
    }

    private static string MeshSignature(Mesh mesh)
    {
        return Hash(writer =>
        {
            writer.Write(mesh.vertexCount);
            Write(writer, mesh.bounds.center); Write(writer, mesh.bounds.extents);
            writer.Write((int)mesh.indexFormat);
            writer.Write(mesh.subMeshCount);
            for (int sub = 0; sub < mesh.subMeshCount; sub++)
            {
                writer.Write((int)mesh.GetTopology(sub));
                int[] indices = mesh.GetIndices(sub);
                writer.Write(indices.Length);
                foreach (int index in indices) writer.Write(index);
            }
            foreach (Vector3 value in mesh.vertices) Write(writer, value);
            foreach (Vector3 value in mesh.normals) Write(writer, value);
            foreach (Vector4 value in mesh.tangents) Write(writer, value);
            foreach (Color value in mesh.colors) Write(writer, value);
            foreach (Color32 value in mesh.colors32)
            { writer.Write(value.r); writer.Write(value.g); writer.Write(value.b); writer.Write(value.a); }
            for (int channel = 0; channel < 8; channel++)
            {
                var uv = new List<Vector4>();
                mesh.GetUVs(channel, uv);
                writer.Write(uv.Count);
                foreach (Vector4 value in uv) Write(writer, value);
            }
            foreach (Matrix4x4 value in mesh.bindposes) Write(writer, value);
            var counts = mesh.GetBonesPerVertex();
            var weights = mesh.GetAllBoneWeights();
            try
            {
                writer.Write(counts.Length);
                for (int i = 0; i < counts.Length; i++) writer.Write(counts[i]);
                writer.Write(weights.Length);
                for (int i = 0; i < weights.Length; i++)
                { writer.Write(weights[i].boneIndex); writer.Write(weights[i].weight); }
            }
            finally { counts.Dispose(); weights.Dispose(); }
            writer.Write(mesh.blendShapeCount);
            for (int i = 0; i < mesh.blendShapeCount; i++)
            {
                writer.Write(mesh.GetBlendShapeName(i));
                int frames = mesh.GetBlendShapeFrameCount(i);
                writer.Write(frames);
                for (int j = 0; j < frames; j++)
                {
                    writer.Write(mesh.GetBlendShapeFrameWeight(i, j));
                    var positions = new Vector3[mesh.vertexCount];
                    var normals = new Vector3[mesh.vertexCount];
                    var tangents = new Vector3[mesh.vertexCount];
                    mesh.GetBlendShapeFrameVertices(i, j, positions, normals, tangents);
                    foreach (Vector3 value in positions) Write(writer, value);
                    foreach (Vector3 value in normals) Write(writer, value);
                    foreach (Vector3 value in tangents) Write(writer, value);
                }
            }
        });
    }

    private static string RendererSignature(Renderer renderer, string guid)
    {
        return Hash(writer =>
        {
            writer.Write(renderer is SkinnedMeshRenderer ? 137 : 23);
            writer.Write(LocalId(renderer.transform, guid));
            Mesh mesh = renderer is SkinnedMeshRenderer skin ? skin.sharedMesh :
                renderer.GetComponent<MeshFilter>()?.sharedMesh;
            writer.Write(LocalId(mesh, guid));
            writer.Write(renderer.enabled);
            writer.Write((int)renderer.shadowCastingMode);
            writer.Write(renderer.receiveShadows);
            Material[] materials = renderer.sharedMaterials;
            writer.Write(materials.Length);
            foreach (Material material in materials)
            {
                if (material == null) { writer.Write(0L); continue; }
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid,
                    out long materialId) || !ValidGuid(materialGuid) || materialId == 0)
                    Reject("MATERIAL_ID_UNAVAILABLE");
                writer.Write(materialGuid); writer.Write(materialId);
            }
            if (renderer is SkinnedMeshRenderer skinned)
            {
                writer.Write(skinned.rootBone == null ? 0L : LocalId(skinned.rootBone, guid));
                Transform[] bones = skinned.bones;
                writer.Write(bones.Length);
                foreach (Transform bone in bones) writer.Write(LocalId(bone, guid));
                writer.Write(skinned.sharedMesh.blendShapeCount);
                for (int i = 0; i < skinned.sharedMesh.blendShapeCount; i++)
                    writer.Write(skinned.GetBlendShapeWeight(i));
            }
        });
    }

    private static bool SameMap(Dictionary<long, string> a, Dictionary<long, string> b)
    {
        if (a.Count != b.Count) return false;
        foreach (KeyValuePair<long, string> row in a)
            if (!b.TryGetValue(row.Key, out string value) || value != row.Value) return false;
        return true;
    }
    private static string Hash(Action<BinaryWriter> write)
    {
        using (var stream = new MemoryStream())
        using (var writer = new BinaryWriter(stream))
        using (SHA256 sha = SHA256.Create())
        {
            write(writer);
            writer.Flush();
            return Convert.ToBase64String(sha.ComputeHash(stream.ToArray()));
        }
    }
    private static void Write(BinaryWriter writer, Vector3 value)
    { writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); }
    private static void Write(BinaryWriter writer, Vector4 value)
    { writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); writer.Write(value.w); }
    private static void Write(BinaryWriter writer, Color value)
    { writer.Write(value.r); writer.Write(value.g); writer.Write(value.b); writer.Write(value.a); }
    private static void Write(BinaryWriter writer, Quaternion value)
    { writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); writer.Write(value.w); }
    private static void Write(BinaryWriter writer, Matrix4x4 value)
    { for (int i = 0; i < 16; i++) writer.Write(value[i]); }
    private static bool EqualBytes(byte[] a, byte[] b)
    {
        if (a == null || b == null || a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }
}
