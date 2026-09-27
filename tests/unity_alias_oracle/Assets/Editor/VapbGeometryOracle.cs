// Public Unity API oracle for final MeshRenderer world geometry.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

[Serializable]
public sealed class VapbGeometryResult {
    public string unityVersion;
    public string pairGuid;
    public string meshGuid;
    public string meshFileId;
    public float importerFileScale;
    public float importerGlobalScale;
    public bool importerUseFileScale;
    public bool importerBakeAxisConversion;
    public int vertexCount;
    public int[] triangles;
    public float[] localVertices;
    public float[] aWorldVertices;
    public float[] bWorldVertices;
}

public static class VapbGeometryOracle {
    const string PairPath = "Assets/Oracle/Transform_TwoInstances.prefab";

    static float[] Flatten(Vector3[] values) {
        var result = new float[values.Length * 3];
        for (var i = 0; i < values.Length; i++) {
            result[3 * i] = values[i].x;
            result[3 * i + 1] = values[i].y;
            result[3 * i + 2] = values[i].z;
        }
        return result;
    }

    static float[] World(Renderer renderer, Vector3[] local) {
        var matrix = renderer.localToWorldMatrix;
        return Flatten(local.Select(point => matrix.MultiplyPoint3x4(point)).ToArray());
    }

    public static void Run() {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new InvalidOperationException("Unity version mismatch");
            var output = Environment.GetEnvironmentVariable("VAPB_GEOMETRY_RESULT_OUTPUT");
            if (String.IsNullOrEmpty(output))
                throw new InvalidOperationException("Output required");
            var contents = PrefabUtility.LoadPrefabContents(PairPath);
            if (contents == null) throw new InvalidOperationException("Pair Prefab missing");
            try {
                var renderers = contents.GetComponentsInChildren<MeshRenderer>(true);
                if (renderers.Length != 2) throw new InvalidOperationException("Renderer count mismatch");
                var a = renderers.Single(renderer => renderer.sharedMaterials.Length == 1 &&
                    renderer.sharedMaterials[0] != null);
                var b = renderers.Single(renderer => renderer.sharedMaterials.Length == 1 &&
                    renderer.sharedMaterials[0] == null);
                if (PrefabUtility.GetCorrespondingObjectFromSource(a) !=
                    PrefabUtility.GetCorrespondingObjectFromSource(b))
                    throw new InvalidOperationException("Source Renderer mismatch");
                var aMesh = a.GetComponent<MeshFilter>().sharedMesh;
                var bMesh = b.GetComponent<MeshFilter>().sharedMesh;
                if (aMesh == null || aMesh != bMesh)
                    throw new InvalidOperationException("Shared Mesh mismatch");
                string meshGuid;
                long meshId;
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(aMesh, out meshGuid, out meshId))
                    throw new InvalidOperationException("Mesh identity missing");
                var importer = AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(meshGuid)) as ModelImporter;
                if (importer == null) throw new InvalidOperationException("Model importer missing");
                var local = aMesh.vertices;
                if (local.Length < 4) throw new InvalidOperationException("Insufficient geometry");
                var result = new VapbGeometryResult {
                    unityVersion = Application.unityVersion,
                    pairGuid = AssetDatabase.AssetPathToGUID(PairPath),
                    meshGuid = meshGuid,
                    meshFileId = meshId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    importerFileScale = importer.fileScale,
                    importerGlobalScale = importer.globalScale,
                    importerUseFileScale = importer.useFileScale,
                    importerBakeAxisConversion = importer.bakeAxisConversion,
                    vertexCount = local.Length,
                    triangles = aMesh.triangles,
                    localVertices = Flatten(local),
                    aWorldVertices = World(a, local),
                    bWorldVertices = World(b, local),
                };
                File.WriteAllText(output, JsonUtility.ToJson(result, true));
            } finally { PrefabUtility.UnloadPrefabContents(contents); }
            Debug.Log("VAPB_GEOMETRY_ORACLE_PASS");
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("VAPB_GEOMETRY_ORACLE_FAIL " + error.GetType().Name + " " + error.Message);
            EditorApplication.Exit(1);
        }
    }
}
