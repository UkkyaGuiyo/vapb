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
        public int skinnedRendererCount;
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
    }

    private sealed class Snapshot
    {
        public readonly Dictionary<long, string> transforms = new Dictionary<long, string>();
        public readonly Dictionary<long, string> meshes = new Dictionary<long, string>();
        public readonly Dictionary<long, string> renderers = new Dictionary<long, string>();
        public readonly HashSet<long> skinBoneIds = new HashSet<long>();
        public string guid;
        public int skinBoneCount;

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
        Snapshot baseline = null;
        try
        {
            if (File.Exists(assetFile) || File.Exists(metaFile))
                throw new InvalidOperationException("MODEL_PATH_OCCUPIED");
            Directory.CreateDirectory(Path.GetDirectoryName(assetFile));
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            original = File.ReadAllBytes(Path.Combine(projectRoot, "Source.fbx"));
            byte[] noop = File.ReadAllBytes(Path.Combine(projectRoot, "Noop.fbx"));
            byte[] witness = File.ReadAllBytes(Path.Combine(projectRoot, "Witness.fbx"));
            if (original.Length == 0 || noop.Length == 0 || witness.Length == 0)
                throw new InvalidOperationException("INPUT_EMPTY");

            File.WriteAllBytes(assetFile, original);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            ModelImporter importer = AssetImporter.GetAtPath(ModelPath) as ModelImporter;
            if (importer == null)
                throw new InvalidOperationException("MODEL_IMPORT_MISSING");
            if (!importer.isReadable)
            {
                importer.isReadable = true;
                importer.SaveAndReimport();
            }
            originalMeta = File.ReadAllBytes(metaFile);
            baseline = Capture();
            report.transformCount = baseline.transforms.Count;
            report.meshCount = baseline.meshes.Count;
            report.skinnedRendererCount = baseline.renderers.Count;
            report.skinBoneCount = baseline.skinBoneCount;
            if (report.transformCount < 3 || report.meshCount == 0 ||
                report.skinnedRendererCount == 0 || report.skinBoneCount < 2)
                throw new InvalidOperationException("FIXTURE_STRUCTURE_INVALID");

            File.WriteAllBytes(assetFile, noop);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            report.noopEquivalent = baseline.SameAs(Capture());
            report.metaStable = EqualBytes(originalMeta, File.ReadAllBytes(metaFile));
            if (!report.noopEquivalent || !report.metaStable)
                throw new InvalidOperationException("NOOP_DRIFT");

            VapbBoneWitnessPostprocessor.CallbackCounts.Clear();
            File.WriteAllBytes(assetFile, witness);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            Snapshot witnessed = Capture();
            report.witnessEquivalent = baseline.SameAs(witnessed);
            report.metaStable &= EqualBytes(originalMeta, File.ReadAllBytes(metaFile));
            InspectMarkers(witnessed, report);
            if (!report.witnessEquivalent || !report.metaStable || !report.callbackExactlyOnce ||
                !report.markerIdentityUnique || !report.allSkinBonesMarked)
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
                    if (originalMeta != null)
                        File.WriteAllBytes(metaFile, originalMeta);
                    AssetDatabase.ImportAsset(ModelPath,
                        ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                    report.restoredEquivalent = baseline != null && baseline.SameAs(Capture());
                    report.metaStable &= originalMeta != null && EqualBytes(originalMeta, File.ReadAllBytes(metaFile));
                }
                catch { report.error = "RESTORE_FAILED"; }
            }
            report.pass = report.error == "NONE" && report.noopEquivalent && report.witnessEquivalent &&
                report.restoredEquivalent && report.metaStable && report.callbackExactlyOnce &&
                report.markerIdentityUnique && report.allSkinBonesMarked;
            if (!report.restoredEquivalent && baseline != null && report.error == "NONE")
                report.error = "RESTORED_STATE_DRIFT";
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
        foreach (SkinnedMeshRenderer renderer in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            long id = LocalId(renderer, result.guid);
            if (result.renderers.ContainsKey(id))
                throw new InvalidOperationException("DUPLICATE_RENDERER_ID");
            result.renderers.Add(id, RendererSignature(renderer, result.guid, result.skinBoneIds));
            result.skinBoneCount += renderer.bones.Length;
        }
        return result;
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
            foreach (Vector3 vertex in mesh.vertices) Write(writer, vertex);
            foreach (Vector3 normal in mesh.normals) Write(writer, normal);
            foreach (int index in mesh.triangles) writer.Write(index);
            foreach (Matrix4x4 bindpose in mesh.bindposes) Write(writer, bindpose);
            foreach (BoneWeight weight in mesh.boneWeights)
            {
                writer.Write(weight.boneIndex0); writer.Write(weight.boneIndex1);
                writer.Write(weight.boneIndex2); writer.Write(weight.boneIndex3);
                writer.Write(weight.weight0); writer.Write(weight.weight1);
                writer.Write(weight.weight2); writer.Write(weight.weight3);
            }
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

    private static string RendererSignature(SkinnedMeshRenderer renderer, string guid, HashSet<long> boneIds)
    {
        return Hash(writer =>
        {
            writer.Write(LocalId(renderer.transform, guid));
            writer.Write(renderer.sharedMesh == null ? 0L : LocalId(renderer.sharedMesh, guid));
            writer.Write(renderer.rootBone == null ? 0L : LocalId(renderer.rootBone, guid));
            Transform[] bones = renderer.bones;
            writer.Write(bones.Length);
            foreach (Transform bone in bones)
            {
                long id = LocalId(bone, guid);
                writer.Write(id);
                boneIds.Add(id);
            }
            writer.Write(renderer.sharedMesh == null ? 0 : renderer.sharedMesh.blendShapeCount);
            if (renderer.sharedMesh != null)
                for (int i = 0; i < renderer.sharedMesh.blendShapeCount; i++)
                    writer.Write(renderer.GetBlendShapeWeight(i));
        });
    }

    private static void InspectMarkers(Snapshot snapshot, Report report)
    {
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        var uids = new HashSet<string>(StringComparer.Ordinal);
        var markedTransformIds = new HashSet<long>();
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
        }
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
        report.allSkinBonesMarked = snapshot.skinBoneIds.Count >= 2 && report.missingSkinBoneMarkerCount == 0;
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
