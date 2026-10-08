using System;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// One observation in the original SourceProject; no import, export or repair.
public static class VapbSourceBoundsMeasurement
{
    [Serializable] sealed class Observation
    {
        public string unityVersion, sourcePackageSha256, prefabGuid, meshGuid, meshFileId;
        public int vertexCount, submeshCount;
        public Vector3 meshBoundsSize, prefabSpaceBoundsSize;
    }
    public static void Measure()
    {
        try
        {
            string root = Directory.GetParent(Application.dataPath).FullName;
            if (Application.unityVersion != "2022.3.22f1") throw new InvalidOperationException("VERSION");
            string packageSha;
            using (var hash = SHA256.Create()) packageSha = BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(Path.Combine(root, "Source.unitypackage")))).Replace("-", "").ToLowerInvariant();
            if (packageSha != "c784c3f27d654fa8808daa77b152d2dd175f31c2f2549931df6394075bedcb4e") throw new InvalidOperationException("SOURCE_HASH");
            const string prefabGuid = "ef933b94f813e324c9cc7268e59ba927";
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(prefabGuid));
            MeshRenderer[] renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            if (renderers.Length != 1) throw new InvalidOperationException("RENDERER_COUNT");
            MeshRenderer renderer = renderers[0];
            Mesh mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long id) || guid != "3858744948938584bb2f344670664ead" || id != -1944139265773155678L) throw new InvalidOperationException("SOURCE_MESH");
            Vector3[] vertices = mesh.vertices;
            var bounds = new Bounds(prefab.transform.InverseTransformPoint(renderer.transform.TransformPoint(vertices[0])), Vector3.zero);
            foreach (Vector3 point in vertices) bounds.Encapsulate(prefab.transform.InverseTransformPoint(renderer.transform.TransformPoint(point)));
            var observation = new Observation { unityVersion = Application.unityVersion, sourcePackageSha256 = packageSha, prefabGuid = prefabGuid, meshGuid = guid, meshFileId = id.ToString(), vertexCount = mesh.vertexCount, submeshCount = mesh.subMeshCount, meshBoundsSize = mesh.bounds.size, prefabSpaceBoundsSize = bounds.size };
            using (var writer = new StreamWriter(new FileStream(Path.Combine(root, "SourceBoundsObservation.json"), FileMode.CreateNew))) writer.Write(JsonUtility.ToJson(observation, true));
            Debug.Log("VAPB_SOURCE_BOUNDS_OBSERVED");
            EditorApplication.Exit(0);
        }
        catch (Exception e) { Debug.LogError("VAPB_SOURCE_BOUNDS_FAILED=" + e.GetType().Name); EditorApplication.Exit(1); }
    }
}
