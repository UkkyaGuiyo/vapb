using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public sealed class VapbBoneWitnessPostprocessor : AssetPostprocessor
{
    internal const string ModelPath = "Assets/VapbBoneWitness/Model.fbx";
    internal static readonly Dictionary<string, int> CallbackCounts = new Dictionary<string, int>(StringComparer.Ordinal);

    private void OnPostprocessGameObjectWithUserProperties(GameObject gameObject, string[] names, object[] values)
    {
        if (assetPath != ModelPath || names == null || values == null || names.Length != values.Length)
            return;
        for (int i = 0; i < names.Length; i++)
        {
            if (names[i] != "_vapb_source_fbx_model_uid")
                continue;
            string uid = values[i] as string;
            if (string.IsNullOrEmpty(uid) || !long.TryParse(uid, NumberStyles.AllowLeadingSign,
                CultureInfo.InvariantCulture, out long parsed) || parsed == 0)
                continue;
            uid = parsed.ToString(CultureInfo.InvariantCulture);
            CallbackCounts[uid] = CallbackCounts.TryGetValue(uid, out int count) ? count + 1 : 1;
            VapbSourceBoneMarker marker = gameObject.GetComponent<VapbSourceBoneMarker>();
            if (marker == null)
                marker = gameObject.AddComponent<VapbSourceBoneMarker>();
            marker.sourceModelUid = uid;
        }
    }
}

public static class VapbBoneWitnessProbe
{
    private const string ModelPath = VapbBoneWitnessPostprocessor.ModelPath;

    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public int transformCount;
        public int meshCount;
        public int rendererCount;
        public int meshRendererCount;
        public int skinnedRendererCount;
        public int markedRendererCount;
        public int skinBoneCount;
        public int witnessMarkerCount;
        public int callbackCount;
        public int duplicateUidCount;
        public int missingSkinBoneMarkerCount;
        public bool noopEquivalent;
        public bool witnessEquivalent;
        public bool restoredEquivalent;
        public bool metaStable;
        public bool callbackExactlyOnce;
        public bool markerIdentityUnique;
        public bool allSkinBonesMarked;
        public bool readabilityChanged;
        public bool sourceMetaRestored;
        public bool sourceRawRestored;
        public bool originalRevisionEquivalent;
        public bool mappingWritten;
    }

    [Serializable] private sealed class RendererMapping
    {
        public string class_id;
        public string renderer_local_id;
        public string mesh_local_id;
    }

    [Serializable] private sealed class ModelMapping
    {
        public string model_uid;
        public string transform_local_id;
        public string game_object_local_id;
        public RendererMapping[] renderers;
    }

    [Serializable] private sealed class Mapping
    {
        public string schema_version = "vapb-source-fbx-model-witness-1";
        public string source_fbx_sha256;
        public string source_meta_sha256;
        public string model_guid;
        public string unity_version;
        public bool importer_readability_changed;
        public ModelMapping[] models;
    }

    private sealed class Snapshot
    {
        public readonly Dictionary<long, string> transforms = new Dictionary<long, string>();
        public readonly Dictionary<long, string> meshes = new Dictionary<long, string>();
        public readonly Dictionary<long, string> renderers = new Dictionary<long, string>();
        public readonly HashSet<long> skinBoneIds = new HashSet<long>();
        public string guid;
        public int skinBoneCount;
        public int meshRendererCount;
        public int skinnedRendererCount;

        public bool SameAs(Snapshot other)
        {
            return other != null && guid == other.guid &&
                Same(transforms, other.transforms) && Same(meshes, other.meshes) &&
                Same(renderers, other.renderers) && skinBoneIds.SetEquals(other.skinBoneIds) &&
                skinBoneCount == other.skinBoneCount;
        }
    }

    private static bool Same(Dictionary<long, string> a, Dictionary<long, string> b)
    {
        if (a.Count != b.Count)
            return false;
        foreach (KeyValuePair<long, string> item in a)
            if (!b.TryGetValue(item.Key, out string value) || value != item.Value)
                return false;
        return true;
    }

    public static void Run()
    {
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        string assetFile = Path.Combine(Application.dataPath, "VapbBoneWitness/Model.fbx");
        string metaFile = assetFile + ".meta";
        byte[] original = null;
        byte[] originalMeta = null;
        byte[] comparisonMeta = null;
        Snapshot baseline = null;
        HashSet<string> originalIdentity = null;
        Mapping mapping = null;
        try
        {
            if (File.Exists(assetFile) || File.Exists(metaFile))
                throw new InvalidOperationException("MODEL_PATH_OCCUPIED");
            Directory.CreateDirectory(Path.GetDirectoryName(assetFile));
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string suppliedMetaPath = Path.Combine(projectRoot, "Source.fbx.meta");
            string mappingPath = Path.Combine(projectRoot, "VapbBoneWitnessMapping.json");
            if (File.Exists(mappingPath))
                throw new InvalidOperationException("MAPPING_PATH_OCCUPIED");
            original = File.ReadAllBytes(Path.Combine(projectRoot, "Source.fbx"));
            byte[] noop = File.ReadAllBytes(Path.Combine(projectRoot, "Noop.fbx"));
            byte[] witness = File.ReadAllBytes(Path.Combine(projectRoot, "Witness.fbx"));
            if (original.Length == 0 || noop.Length == 0 || witness.Length == 0)
                throw new InvalidOperationException("INPUT_EMPTY");

            File.WriteAllBytes(assetFile, original);
            if (File.Exists(suppliedMetaPath))
            {
                originalMeta = File.ReadAllBytes(suppliedMetaPath);
                File.WriteAllBytes(metaFile, originalMeta);
            }
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            if (originalMeta == null) originalMeta = File.ReadAllBytes(metaFile);
            originalIdentity = CaptureSourceIdentity();
            ModelImporter importer = AssetImporter.GetAtPath(ModelPath) as ModelImporter;
            if (importer == null)
                throw new InvalidOperationException("MODEL_IMPORT_MISSING");
            if (!importer.isReadable)
            {
                report.readabilityChanged = true;
                importer.isReadable = true;
                importer.SaveAndReimport();
            }
            comparisonMeta = File.ReadAllBytes(metaFile);
            baseline = Capture();
            report.transformCount = baseline.transforms.Count;
            report.meshCount = baseline.meshes.Count;
            report.rendererCount = baseline.renderers.Count;
            report.meshRendererCount = baseline.meshRendererCount;
            report.skinnedRendererCount = baseline.skinnedRendererCount;
            report.skinBoneCount = baseline.skinBoneCount;
            if (report.transformCount == 0 || report.meshCount == 0 || report.rendererCount == 0)
                throw new InvalidOperationException("FIXTURE_STRUCTURE_INVALID");

            File.WriteAllBytes(assetFile, noop);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            report.noopEquivalent = baseline.SameAs(Capture());
            report.metaStable = EqualBytes(comparisonMeta, File.ReadAllBytes(metaFile));
            if (!report.noopEquivalent || !report.metaStable)
                throw new InvalidOperationException("NOOP_DRIFT");

            VapbBoneWitnessPostprocessor.CallbackCounts.Clear();
            File.WriteAllBytes(assetFile, witness);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            Snapshot witnessed = Capture();
            report.witnessEquivalent = baseline.SameAs(witnessed);
            report.originalRevisionEquivalent = originalIdentity.SetEquals(CaptureSourceIdentity());
            report.metaStable &= EqualBytes(comparisonMeta, File.ReadAllBytes(metaFile));
            mapping = InspectMarkers(witnessed, report, original, originalMeta);
            if (!report.witnessEquivalent || !report.metaStable || !report.callbackExactlyOnce ||
                !report.originalRevisionEquivalent || !report.markerIdentityUnique || !report.allSkinBonesMarked ||
                report.markedRendererCount != report.rendererCount)
                throw new InvalidOperationException("WITNESS_DRIFT_OR_AMBIGUITY");
            report.error = "NONE";
        }
        catch (Exception exception)
        {
            report.error = SafeError(exception);
        }
        finally
        {
            if (original != null)
            {
                try
                {
                    File.WriteAllBytes(assetFile, original);
                    if (comparisonMeta != null)
                        File.WriteAllBytes(metaFile, comparisonMeta);
                    else if (originalMeta != null)
                        File.WriteAllBytes(metaFile, originalMeta);
                    AssetDatabase.ImportAsset(ModelPath,
                        ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                    report.restoredEquivalent = baseline != null && baseline.SameAs(Capture());
                    report.metaStable &= comparisonMeta != null && EqualBytes(comparisonMeta, File.ReadAllBytes(metaFile));
                    if (originalMeta != null && !EqualBytes(originalMeta, File.ReadAllBytes(metaFile)))
                    {
                        File.WriteAllBytes(metaFile, originalMeta);
                        AssetDatabase.ImportAsset(ModelPath,
                            ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                    }
                    report.sourceMetaRestored = originalMeta != null &&
                        EqualBytes(originalMeta, File.ReadAllBytes(metaFile));
                    report.sourceRawRestored = EqualBytes(original, File.ReadAllBytes(assetFile));
                    report.originalRevisionEquivalent &= originalIdentity != null &&
                        originalIdentity.SetEquals(CaptureSourceIdentity());
                }
                catch { report.error = "RESTORE_FAILED"; }
            }
            report.pass = report.error == "NONE" && report.noopEquivalent && report.witnessEquivalent &&
                report.restoredEquivalent && report.metaStable && report.callbackExactlyOnce &&
                report.markerIdentityUnique && report.allSkinBonesMarked && report.sourceMetaRestored &&
                report.sourceRawRestored && report.originalRevisionEquivalent &&
                report.markedRendererCount == report.rendererCount;
            if (!report.restoredEquivalent && baseline != null && report.error == "NONE")
                report.error = "RESTORED_STATE_DRIFT";
            if (report.pass)
            {
                try
                {
                    string output = Path.Combine(Path.GetDirectoryName(Application.dataPath),
                        "VapbBoneWitnessMapping.json");
                    File.WriteAllText(output, JsonUtility.ToJson(mapping, true));
                    report.mappingWritten = true;
                }
                catch { report.pass = false; report.error = "MAPPING_WRITE_FAILED"; }
            }
            try
            {
                File.WriteAllText(Path.Combine(Path.GetDirectoryName(Application.dataPath),
                    "VapbBoneWitnessResult.json"), JsonUtility.ToJson(report, true));
            }
            catch { report.pass = false; report.error = "REPORT_WRITE_FAILED"; }
            Debug.Log(report.pass ? "VAPB_BONE_WITNESS_PASS" : "VAPB_BONE_WITNESS_FAIL");
            EditorApplication.Exit(report.pass ? 0 : 1);
        }
    }

    private static Snapshot Capture()
    {
        var result = new Snapshot { guid = AssetDatabase.AssetPathToGUID(ModelPath) };
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (root == null || string.IsNullOrEmpty(result.guid))
            throw new InvalidOperationException("MODEL_IMPORT_MISSING");
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            long id = LocalId(transform, result.guid);
            if (result.transforms.ContainsKey(id))
                throw new InvalidOperationException("DUPLICATE_TRANSFORM_ID");
            result.transforms.Add(id, TransformSignature(transform, result.guid));
        }
        foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(ModelPath))
        {
            if (!(asset is Mesh mesh))
                continue;
            long id = LocalId(mesh, result.guid);
            if (result.meshes.ContainsKey(id))
                throw new InvalidOperationException("DUPLICATE_MESH_ID");
            result.meshes.Add(id, MeshSignature(mesh));
        }
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            if (!(renderer is SkinnedMeshRenderer) && !(renderer is MeshRenderer))
                throw new InvalidOperationException("RENDERER_UNSUPPORTED");
            long id = LocalId(renderer, result.guid);
            if (result.renderers.ContainsKey(id))
                throw new InvalidOperationException("DUPLICATE_RENDERER_ID");
            result.renderers.Add(id, RendererSignature(renderer, result.guid, result.skinBoneIds));
            if (renderer is SkinnedMeshRenderer skin)
            {
                result.skinnedRendererCount++;
                result.skinBoneCount += skin.bones.Length;
            }
            else result.meshRendererCount++;
        }
        return result;
    }

    private static HashSet<string> CaptureSourceIdentity()
    {
        string guid = AssetDatabase.AssetPathToGUID(ModelPath);
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (root == null || string.IsNullOrEmpty(guid))
            throw new InvalidOperationException("MODEL_IMPORT_MISSING");
        var rows = new HashSet<string>(StringComparer.Ordinal);
        foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
        {
            string row = "T:" + LocalId(transform, guid) + ":" +
                LocalId(transform.gameObject, guid) + ":" +
                (transform.parent == null ? 0L : LocalId(transform.parent, guid));
            if (!rows.Add(row)) throw new InvalidOperationException("SOURCE_IDENTITY_DUPLICATE");
        }
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            string row = "R:" + LocalId(renderer, guid) + ":" +
                LocalId(renderer.gameObject, guid) + ":" +
                LocalId(SharedMesh(renderer), guid) + ":" +
                (renderer is SkinnedMeshRenderer ? 137 : renderer is MeshRenderer ? 23 : 0);
            if (!rows.Add(row)) throw new InvalidOperationException("SOURCE_IDENTITY_DUPLICATE");
        }
        foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(ModelPath))
            if (asset is Mesh mesh && !rows.Add("M:" + LocalId(mesh, guid)))
                throw new InvalidOperationException("SOURCE_IDENTITY_DUPLICATE");
        return rows;
    }

    private static long LocalId(UnityEngine.Object value, string expectedGuid)
    {
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string guid, out long id) ||
            guid != expectedGuid || id == 0)
            throw new InvalidOperationException("OBJECT_ID_UNAVAILABLE");
        return id;
    }

    private static string TransformSignature(Transform transform, string guid)
    {
        return Hash(writer =>
        {
            writer.Write(transform.name);
            writer.Write(transform.parent == null ? 0L : LocalId(transform.parent, guid));
            Write(writer, transform.localPosition);
            Write(writer, transform.localRotation);
            Write(writer, transform.localScale);
            Write(writer, transform.localToWorldMatrix);
        });
    }

    private static string MeshSignature(Mesh mesh)
    {
        return Hash(writer =>
        {
            writer.Write(mesh.vertexCount);
            Write(writer, mesh.bounds.center);
            Write(writer, mesh.bounds.extents);
            writer.Write((int)mesh.indexFormat);
            writer.Write(mesh.subMeshCount);
            for (int submesh = 0; submesh < mesh.subMeshCount; submesh++)
            {
                writer.Write((int)mesh.GetTopology(submesh));
                int[] indices = mesh.GetIndices(submesh);
                writer.Write(indices.Length);
                foreach (int index in indices) writer.Write(index);
            }
            foreach (Vector3 vertex in mesh.vertices) Write(writer, vertex);
            foreach (Vector3 normal in mesh.normals) Write(writer, normal);
            foreach (Vector4 tangent in mesh.tangents) Write(writer, tangent);
            foreach (Color color in mesh.colors) Write(writer, color);
            foreach (Color32 color in mesh.colors32)
            { writer.Write(color.r); writer.Write(color.g); writer.Write(color.b); writer.Write(color.a); }
            for (int channel = 0; channel < 8; channel++)
            {
                var uv = new List<Vector4>();
                mesh.GetUVs(channel, uv);
                writer.Write(uv.Count);
                foreach (Vector4 value in uv) Write(writer, value);
            }
            foreach (Matrix4x4 bindpose in mesh.bindposes) Write(writer, bindpose);
            var boneCounts = mesh.GetBonesPerVertex();
            var boneWeights = mesh.GetAllBoneWeights();
            try
            {
                writer.Write(boneCounts.Length);
                for (int i = 0; i < boneCounts.Length; i++) writer.Write(boneCounts[i]);
                writer.Write(boneWeights.Length);
                for (int i = 0; i < boneWeights.Length; i++)
                { writer.Write(boneWeights[i].boneIndex); writer.Write(boneWeights[i].weight); }
            }
            finally { boneCounts.Dispose(); boneWeights.Dispose(); }
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

    private static string RendererSignature(Renderer renderer, string guid, HashSet<long> boneIds)
    {
        return Hash(writer =>
        {
            writer.Write(renderer is SkinnedMeshRenderer ? 137 : 23);
            writer.Write(LocalId(renderer.transform, guid));
            writer.Write(LocalId(SharedMesh(renderer), guid));
            writer.Write(renderer.enabled);
            writer.Write((int)renderer.shadowCastingMode);
            writer.Write(renderer.receiveShadows);
            Material[] materials = renderer.sharedMaterials;
            writer.Write(materials.Length);
            foreach (Material material in materials)
            {
                if (material == null) { writer.Write(0L); continue; }
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId) ||
                    string.IsNullOrEmpty(materialGuid) || materialId == 0)
                    throw new InvalidOperationException("MATERIAL_ID_UNAVAILABLE");
                writer.Write(materialGuid); writer.Write(materialId);
            }
            if (renderer is SkinnedMeshRenderer skin)
            {
                writer.Write(skin.rootBone == null ? 0L : LocalId(skin.rootBone, guid));
                Transform[] bones = skin.bones;
                writer.Write(bones.Length);
                foreach (Transform bone in bones)
                {
                    long id = LocalId(bone, guid);
                    writer.Write(id);
                    boneIds.Add(id);
                }
                writer.Write(skin.sharedMesh.blendShapeCount);
                for (int i = 0; i < skin.sharedMesh.blendShapeCount; i++)
                    writer.Write(skin.GetBlendShapeWeight(i));
            }
        });
    }

    private static Mesh SharedMesh(Renderer renderer)
    {
        if (renderer is SkinnedMeshRenderer skin && skin.sharedMesh != null) return skin.sharedMesh;
        if (renderer is MeshRenderer direct)
        {
            MeshFilter[] filters = direct.GetComponents<MeshFilter>();
            if (filters.Length == 1 && filters[0].sharedMesh != null) return filters[0].sharedMesh;
        }
        throw new InvalidOperationException("RENDERER_MESH_UNAVAILABLE");
    }

    private static Mapping InspectMarkers(Snapshot snapshot, Report report,
                                          byte[] originalBytes, byte[] originalMeta)
    {
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        var uids = new HashSet<string>(StringComparer.Ordinal);
        var markedTransformIds = new HashSet<long>();
        var markedRendererIds = new HashSet<long>();
        var rows = new List<ModelMapping>();
        foreach (VapbSourceBoneMarker marker in root.GetComponentsInChildren<VapbSourceBoneMarker>(true))
        {
            report.witnessMarkerCount++;
            if (!long.TryParse(marker.sourceModelUid, NumberStyles.AllowLeadingSign,
                CultureInfo.InvariantCulture, out long uid) || uid == 0 ||
                !uids.Add(uid.ToString(CultureInfo.InvariantCulture)))
                report.duplicateUidCount++;
            long id = LocalId(marker.transform, snapshot.guid);
            if (!markedTransformIds.Add(id))
                report.duplicateUidCount++;
            var rendererRows = new List<RendererMapping>();
            var classes = new HashSet<int>();
            foreach (Renderer renderer in marker.GetComponents<Renderer>())
            {
                int classId = renderer is SkinnedMeshRenderer ? 137 :
                              renderer is MeshRenderer ? 23 : 0;
                if (classId == 0 || !classes.Add(classId))
                    throw new InvalidOperationException("RENDERER_MARKER_AMBIGUOUS");
                long rendererId = LocalId(renderer, snapshot.guid);
                if (!snapshot.renderers.ContainsKey(rendererId) || !markedRendererIds.Add(rendererId))
                    throw new InvalidOperationException("RENDERER_MARKER_AMBIGUOUS");
                rendererRows.Add(new RendererMapping
                {
                    class_id = classId.ToString(CultureInfo.InvariantCulture),
                    renderer_local_id = rendererId.ToString(CultureInfo.InvariantCulture),
                    mesh_local_id = LocalId(SharedMesh(renderer), snapshot.guid)
                        .ToString(CultureInfo.InvariantCulture)
                });
            }
            rows.Add(new ModelMapping
            {
                model_uid = marker.sourceModelUid,
                transform_local_id = id.ToString(CultureInfo.InvariantCulture),
                game_object_local_id = LocalId(marker.gameObject, snapshot.guid)
                    .ToString(CultureInfo.InvariantCulture),
                renderers = rendererRows.ToArray()
            });
        }
        report.markedRendererCount = markedRendererIds.Count;
        foreach (long boneId in snapshot.skinBoneIds)
            if (!markedTransformIds.Contains(boneId))
                report.missingSkinBoneMarkerCount++;
        foreach (int count in VapbBoneWitnessPostprocessor.CallbackCounts.Values)
            report.callbackCount += count;
        report.callbackExactlyOnce = report.witnessMarkerCount > 0 &&
            report.callbackCount == report.witnessMarkerCount &&
            VapbBoneWitnessPostprocessor.CallbackCounts.Count == report.witnessMarkerCount;
        foreach (int count in VapbBoneWitnessPostprocessor.CallbackCounts.Values)
            if (count != 1)
                report.callbackExactlyOnce = false;
        report.markerIdentityUnique = report.witnessMarkerCount > 0 && report.duplicateUidCount == 0;
        report.allSkinBonesMarked = report.missingSkinBoneMarkerCount == 0;
        return new Mapping
        {
            source_fbx_sha256 = HashBytes(originalBytes),
            source_meta_sha256 = HashBytes(originalMeta),
            model_guid = snapshot.guid, unity_version = Application.unityVersion,
            importer_readability_changed = report.readabilityChanged,
            models = rows.ToArray()
        };
    }

    private static string HashBytes(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
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
    {
        writer.Write(value.x); writer.Write(value.y); writer.Write(value.z);
    }

    private static void Write(BinaryWriter writer, Vector4 value)
    {
        writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); writer.Write(value.w);
    }

    private static void Write(BinaryWriter writer, Color value)
    {
        writer.Write(value.r); writer.Write(value.g); writer.Write(value.b); writer.Write(value.a);
    }

    private static void Write(BinaryWriter writer, Quaternion value)
    {
        writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); writer.Write(value.w);
    }

    private static void Write(BinaryWriter writer, Matrix4x4 value)
    {
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++)
                writer.Write(value[row, column]);
    }

    private static bool EqualBytes(byte[] a, byte[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    private static string SafeError(Exception exception)
    {
        if (exception is InvalidOperationException)
        {
            switch (exception.Message)
            {
                case "MODEL_PATH_OCCUPIED": case "INPUT_EMPTY": case "FIXTURE_STRUCTURE_INVALID":
                case "MAPPING_PATH_OCCUPIED": case "MATERIAL_ID_UNAVAILABLE":
                case "RENDERER_MESH_UNAVAILABLE": case "RENDERER_MARKER_AMBIGUOUS":
                case "RENDERER_UNSUPPORTED":
                case "NOOP_DRIFT": case "WITNESS_DRIFT_OR_AMBIGUITY":
                case "MODEL_IMPORT_MISSING": case "DUPLICATE_TRANSFORM_ID":
                case "DUPLICATE_MESH_ID": case "DUPLICATE_RENDERER_ID":
                case "OBJECT_ID_UNAVAILABLE":
                    return exception.Message;
            }
        }
        return exception.GetType().Name;
    }
}
