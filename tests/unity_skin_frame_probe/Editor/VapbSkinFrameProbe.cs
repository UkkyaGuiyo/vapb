using System;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Synthetic-only probe for FBX unit representation across Blender and Unity.
public static class VapbSkinFrameProbe
{
    private const string Source = "Assets/VapbSkinRoundtrip/Input.fbx";
    private const string Folder = "Assets/VapbFrameTest";

    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool localFrameChanged;
        public bool uniformPositiveFrame;
        public bool noEditNormalized;
        public bool editAndNoEditMatricesEqual;
        public bool editAndNoEditBindposesEqual;
        public bool editedVertexSmallNonzero;
        public int vertexCount;
        public int boneCount;
        public int triangleIndexCount;
        public int changedVertexCount;
        public float scaleFactor;
        public float maxLocalVertexDelta;
        public float maxNoEditNormalizedError;
        public float maxEditedNormalizedDelta;
        public float maxRendererMatrixDelta;
        public float maxBindposeMatrixDelta;
    }

    public static void Run()
    {
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        try
        {
            string sourceDisk = Disk(Source);
            if (!File.Exists(sourceDisk) || !File.Exists(sourceDisk + ".meta") ||
                !File.Exists(ProjectFile("NoEdit.fbx")) || !File.Exists(ProjectFile("Edited.fbx")))
                throw new InvalidOperationException("INPUT_MISSING");
            Directory.CreateDirectory(Disk(Folder));
            string noEditPath = CopyControl("NoEdit.fbx", sourceDisk + ".meta");
            string editedPath = CopyControl("Edited.fbx", sourceDisk + ".meta");
            SkinnedMeshRenderer source = LoadSkin(Source);
            SkinnedMeshRenderer noEdit = LoadSkin(noEditPath);
            SkinnedMeshRenderer edited = LoadSkin(editedPath);
            Mesh a = source.sharedMesh, b = noEdit.sharedMesh, c = edited.sharedMesh;
            if (a == null || b == null || c == null || source.bones == null ||
                noEdit.bones == null || edited.bones == null || source.bones.Length < 2 ||
                source.bones.Length != noEdit.bones.Length || source.bones.Length != edited.bones.Length ||
                a.vertexCount != b.vertexCount || a.vertexCount != c.vertexCount ||
                a.bindposes.Length != b.bindposes.Length || b.bindposes.Length != c.bindposes.Length ||
                a.bindposes.Length != source.bones.Length || a.blendShapeCount != b.blendShapeCount ||
                b.blendShapeCount != c.blendShapeCount || a.subMeshCount != b.subMeshCount ||
                b.subMeshCount != c.subMeshCount)
                throw new InvalidOperationException("LAYOUT_MISMATCH");
            for (int sub = 0; sub < a.subMeshCount; sub++)
            {
                if (a.GetTopology(sub) != b.GetTopology(sub) || b.GetTopology(sub) != c.GetTopology(sub))
                    throw new InvalidOperationException("TOPOLOGY_MISMATCH");
                int[] ai = a.GetIndices(sub), bi = b.GetIndices(sub), ci = c.GetIndices(sub);
                if (ai.Length != bi.Length || bi.Length != ci.Length)
                    throw new InvalidOperationException("INDEX_MISMATCH");
                report.triangleIndexCount += ai.Length;
                for (int i = 0; i < ai.Length; i++)
                    if (ai[i] != bi[i] || bi[i] != ci[i])
                        throw new InvalidOperationException("INDEX_MISMATCH");
            }
            report.vertexCount = a.vertexCount;
            report.boneCount = source.bones.Length;
            Matrix4x4 frame = source.transform.worldToLocalMatrix * noEdit.transform.localToWorldMatrix;
            Vector3 col0 = frame.GetColumn(0), col1 = frame.GetColumn(1), col2 = frame.GetColumn(2);
            float s0 = col0.magnitude, s1 = col1.magnitude, s2 = col2.magnitude;
            report.scaleFactor = (s0 + s1 + s2) / 3f;
            report.uniformPositiveFrame = Finite(report.scaleFactor) && report.scaleFactor > 0f &&
                Finite(frame.determinant) && frame.determinant > 0f &&
                Mathf.Abs(s0 - report.scaleFactor) < 0.0001f * report.scaleFactor &&
                Mathf.Abs(s1 - report.scaleFactor) < 0.0001f * report.scaleFactor &&
                Mathf.Abs(s2 - report.scaleFactor) < 0.0001f * report.scaleFactor &&
                Mathf.Abs(Vector3.Dot(col0, col1)) < 0.0001f * s0 * s1 &&
                Mathf.Abs(Vector3.Dot(col0, col2)) < 0.0001f * s0 * s2 &&
                Mathf.Abs(Vector3.Dot(col1, col2)) < 0.0001f * s1 * s2;
            if (!report.uniformPositiveFrame) throw new InvalidOperationException("FRAME_UNSUPPORTED");
            report.maxRendererMatrixDelta = MatrixDelta(noEdit.transform.localToWorldMatrix,
                edited.transform.localToWorldMatrix);
            report.editAndNoEditMatricesEqual = report.maxRendererMatrixDelta <= 1e-6f;
            Matrix4x4[] bb = b.bindposes, cb = c.bindposes;
            for (int i = 0; i < bb.Length; i++)
                report.maxBindposeMatrixDelta = Mathf.Max(report.maxBindposeMatrixDelta,
                    MatrixDelta(bb[i], cb[i]));
            report.editAndNoEditBindposesEqual = report.maxBindposeMatrixDelta <= 1e-6f;
            Vector3[] av = a.vertices, bv = b.vertices, cv = c.vertices;
            for (int i = 0; i < av.Length; i++)
            {
                report.maxLocalVertexDelta = Mathf.Max(report.maxLocalVertexDelta,
                    Vector3.Distance(av[i], bv[i]));
                report.maxNoEditNormalizedError = Mathf.Max(report.maxNoEditNormalizedError,
                    Vector3.Distance(av[i], frame.MultiplyPoint3x4(bv[i])));
                float delta = Vector3.Distance(frame.MultiplyPoint3x4(bv[i]),
                    frame.MultiplyPoint3x4(cv[i]));
                report.maxEditedNormalizedDelta = Mathf.Max(report.maxEditedNormalizedDelta, delta);
                if (delta > 1e-6f) report.changedVertexCount++;
            }
            report.localFrameChanged = Mathf.Abs(report.scaleFactor - 1f) > 0.01f ||
                report.maxLocalVertexDelta > 1e-4f;
            report.noEditNormalized = report.maxNoEditNormalizedError <= 1e-5f;
            float extent = a.bounds.size.magnitude;
            report.editedVertexSmallNonzero = report.changedVertexCount > 0 &&
                report.maxEditedNormalizedDelta > 1e-6f &&
                report.maxEditedNormalizedDelta < 0.05f * extent;
            report.pass = report.localFrameChanged && Mathf.Abs(report.scaleFactor - 100f) < 0.01f &&
                report.noEditNormalized && report.editAndNoEditMatricesEqual &&
                report.editAndNoEditBindposesEqual && report.editedVertexSmallNonzero;
            report.error = report.pass ? "NONE" : "FRAME_PARITY_FAILED";
        }
        catch (Exception error)
        {
            report.pass = false;
            report.error = error is InvalidOperationException ? error.Message : error.GetType().Name;
        }
        try { File.WriteAllText(ProjectFile("FrameProbeResult.json"), JsonUtility.ToJson(report, true)); }
        catch
        {
            Debug.LogError("FRAME_REPORT_WRITE_FAILED");
            EditorApplication.Exit(1);
            return;
        }
        Debug.Log("VAPB_SKIN_FRAME_PASS=" + report.pass + " ERROR=" + report.error);
        EditorApplication.Exit(report.pass ? 0 : 1);
    }

    private static string CopyControl(string filename, string sourceMetaPath)
    {
        string path = Folder + "/" + filename;
        string disk = Disk(path);
        string meta = File.ReadAllText(sourceMetaPath);
        Match sourceGuid = Regex.Match(meta, @"(?m)^guid: ([0-9a-fA-F]{32})\s*$");
        if (!sourceGuid.Success) throw new InvalidOperationException("SOURCE_META_GUID_MISSING");
        string newGuid = File.Exists(disk + ".meta") ?
            Regex.Match(File.ReadAllText(disk + ".meta"), @"(?m)^guid: ([0-9a-fA-F]{32})\s*$").Groups[1].Value :
            Guid.NewGuid().ToString("N");
        if (newGuid.Length != 32 || newGuid == sourceGuid.Groups[1].Value)
            throw new InvalidOperationException("CONTROL_META_GUID_INVALID");
        File.Copy(ProjectFile(filename), disk, true);
        File.WriteAllText(disk + ".meta", meta.Substring(0, sourceGuid.Groups[1].Index) +
            newGuid + meta.Substring(sourceGuid.Groups[1].Index + sourceGuid.Groups[1].Length));
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate |
            ImportAssetOptions.ForceSynchronousImport);
        return path;
    }

    private static SkinnedMeshRenderer LoadSkin(string path)
    {
        ModelImporter importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (importer == null) throw new InvalidOperationException("MODEL_IMPORTER_MISSING");
        if (!importer.isReadable)
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
        }
        else AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate |
            ImportAssetOptions.ForceSynchronousImport);
        GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (root == null) throw new InvalidOperationException("MODEL_MISSING");
        SkinnedMeshRenderer[] skins = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        if (skins.Length != 1) throw new InvalidOperationException("SKIN_NOT_UNIQUE");
        return skins[0];
    }

    private static float MatrixDelta(Matrix4x4 a, Matrix4x4 b)
    {
        float result = 0f;
        for (int i = 0; i < 16; i++)
        {
            if (!Finite(a[i]) || !Finite(b[i])) return float.PositiveInfinity;
            result = Mathf.Max(result, Mathf.Abs(a[i] - b[i]));
        }
        return result;
    }

    private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    private static string ProjectFile(string name) => Path.Combine(Directory.GetParent(Application.dataPath).FullName, name);
    private static string Disk(string path) => Path.Combine(Directory.GetParent(Application.dataPath).FullName,
        path.Replace('/', Path.DirectorySeparatorChar));
}
