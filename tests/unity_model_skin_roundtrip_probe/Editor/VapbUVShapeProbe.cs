using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Public two-triangle fixture only. Its Blender edit splits one UV corner and edits Basis/ShapeA.
public static class VapbUVShapeProbe
{
    [Serializable] private class SourceInfo { public string source_model_guid; }
    [Serializable] private class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private class Task { public string model_guid, variant_path; }
    [Serializable] private class Report
    {
        public bool pass;
        public string error;
        public bool editedMeshBound, splitCorner, baseEdit, uvEdit, selectedShapeEdit;
        public bool otherShapePreserved, otherCornersPreserved;
        public int sourceVertices, editedVertices, indices, shapes;
        public float baseDelta, uvDelta, shapeDelta, otherShapeError;
    }
    private static bool Near(float a, float b, float tolerance = 0.000001f) =>
        Mathf.Abs(a - b) < tolerance;

    private static Vector3[] Shape(Mesh mesh, int shape)
    {
        var vertices = new Vector3[mesh.vertexCount];
        mesh.GetBlendShapeFrameVertices(shape, 0, vertices,
            new Vector3[mesh.vertexCount], new Vector3[mesh.vertexCount]);
        return vertices;
    }

    public static void Run()
    {
        var report = new Report();
        try
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            var info = JsonUtility.FromJson<SourceInfo>(File.ReadAllText(Path.Combine(project, "SourceInfo.json")));
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(Application.dataPath,
                "VAPBExport/manifest.json")));
            Task task = manifest.reference_rebind_tasks.Single();
            Mesh source = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(info.source_model_guid))
                .GetComponentsInChildren<SkinnedMeshRenderer>(true).Single().sharedMesh;
            Mesh edited = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(task.model_guid))
                .GetComponentsInChildren<SkinnedMeshRenderer>(true).Single().sharedMesh;
            Mesh variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path)
                .GetComponentsInChildren<SkinnedMeshRenderer>(true).Single().sharedMesh;
            report.editedMeshBound = variant == edited;
            report.sourceVertices = source.vertexCount;
            report.editedVertices = edited.vertexCount;
            report.indices = edited.GetIndices(0).Length;
            report.shapes = edited.blendShapeCount;
            if (source.vertexCount != 4 || edited.vertexCount != 5 || source.blendShapeCount != 2 ||
                edited.blendShapeCount != 2 || source.GetIndices(0).Length != 6 || report.indices != 6 ||
                source.uv.Length != 4 || edited.uv.Length != 5)
                throw new InvalidOperationException("FIXTURE_LAYOUT_INVALID");
            Vector3[] sourceA = Shape(source, 0), sourceB = Shape(source, 1);
            Vector3[] editedA = Shape(edited, 0), editedB = Shape(edited, 1);
            Vector3[] original = source.vertices, changed = edited.vertices;
            Vector2[] sourceUv = source.uv, editedUv = edited.uv;
            int first = -1, second = -1;
            for (int i = 0; i < changed.Length; i++)
                for (int j = i + 1; j < changed.Length; j++)
                    if ((changed[i] - changed[j]).magnitude < 0.000001f &&
                        Near(Mathf.Abs(editedUv[i].x - editedUv[j].x), 0.25f) &&
                        Near(editedUv[i].y, editedUv[j].y))
                    {
                        if (first >= 0) throw new InvalidOperationException("SPLIT_AMBIGUOUS");
                        first = i; second = j;
                    }
            report.splitCorner = first >= 0;
            if (!report.splitCorner) throw new InvalidOperationException("SPLIT_MISSING");
            int sourceCorner = Enumerable.Range(0, original.Length)
                .OrderBy(i => (original[i] - changed[first]).sqrMagnitude).First();
            report.baseDelta = (original[sourceCorner] - changed[first]).magnitude;
            report.uvDelta = Mathf.Max((editedUv[first] - sourceUv[sourceCorner]).magnitude,
                (editedUv[second] - sourceUv[sourceCorner]).magnitude);
            report.shapeDelta = (editedA[first] - sourceA[sourceCorner]).magnitude;
            report.otherShapeError = Mathf.Max((editedB[first] - sourceB[sourceCorner]).magnitude,
                (editedB[second] - sourceB[sourceCorner]).magnitude);
            // This synthetic FBX imports into Unity at 0.01 model scale.
            report.baseEdit = Near(report.baseDelta, 0.00002f);
            report.uvEdit = Near(report.uvDelta, 0.25f) &&
                Mathf.Min((editedUv[first] - sourceUv[sourceCorner]).magnitude,
                    (editedUv[second] - sourceUv[sourceCorner]).magnitude) < 0.000001f;
            report.selectedShapeEdit = Near(report.shapeDelta, 0.00003f) &&
                Near((editedA[second] - sourceA[sourceCorner]).magnitude, 0.00003f);
            report.otherShapePreserved = report.otherShapeError < 0.000001f;
            report.otherCornersPreserved = true;
            for (int i = 0; i < changed.Length; i++)
            {
                if (i == first || i == second) continue;
                int match = Enumerable.Range(0, original.Length)
                    .OrderBy(j => (original[j] - changed[i]).sqrMagnitude).First();
                report.otherCornersPreserved &= (original[match] - changed[i]).magnitude < 0.000001f &&
                    (sourceUv[match] - editedUv[i]).magnitude < 0.000001f &&
                    (sourceA[match] - editedA[i]).magnitude < 0.000001f &&
                    (sourceB[match] - editedB[i]).magnitude < 0.000001f;
            }
            report.pass = report.editedMeshBound && report.splitCorner && report.baseEdit &&
                report.uvEdit && report.selectedShapeEdit && report.otherShapePreserved &&
                report.otherCornersPreserved;
        }
        catch (Exception error)
        {
            report.pass = false;
            report.error = error is InvalidOperationException &&
                (error.Message == "FIXTURE_LAYOUT_INVALID" || error.Message == "SPLIT_AMBIGUOUS" ||
                 error.Message == "SPLIT_MISSING") ? error.Message : "UNEXPECTED_EXCEPTION";
        }
        try
        {
            File.WriteAllText(Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                "UVShapePositiveResult.json"), JsonUtility.ToJson(report, true));
        }
        catch { EditorApplication.Exit(1); return; }
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
