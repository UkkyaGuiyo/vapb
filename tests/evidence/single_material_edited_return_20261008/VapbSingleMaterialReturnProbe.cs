using System;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

// One existing single-material edited output; existing roundtrip callback pattern.
[InitializeOnLoad]
public static class VapbSingleMaterialReturnProbe
{
    const string Phase = "VAPB_SINGLE_RETURN_PHASE";
    const string Started = "VAPB_SINGLE_RETURN_STARTED";
    const string OutputSha = "0dffe5e25e649abccaf6e28f764c2e618f7cdddf14e7e2456d507c0a2a906f13";
    const string PrefabGuid = "ef933b94f813e324c9cc7268e59ba927";
    const string ModelGuid = "3858744948938584bb2f344670664ead";
    const string MaterialGuid = "1906388f1224e1544a0b8d4044c7deb5";
    const string TextureGuid = "31a60e65d27bc634d951ab7b021a9643";
    const string Manifest = "Assets/VAPBExport/manifest.json";
    static string Root { get { return Directory.GetParent(Application.dataPath).FullName; } }
    [Serializable] sealed class Report
    {
        public string status = "FAIL", error = "", unityVersion, outputSha256;
        public bool finalizerApply, meshFromEditedModel, singleSubmesh, materialIdentity, textureIdentity, shape125;
        public string prefabGuid, meshGuid, meshFileId, materialGuid, materialFileId, textureGuid, textureFileId;
        public int submeshCount, triangleCount, vertexCount;
        public Vector3 meshBoundsSize, prefabSpaceBoundsSize;
    }
    static VapbSingleMaterialReturnProbe()
    {
        AssetDatabase.importPackageCompleted += name => { if (SessionState.GetString(Phase, "") == "importing") SessionState.SetString(Phase, "imported"); };
        AssetDatabase.importPackageFailed += (name, error) => { if (SessionState.GetString(Phase, "") == "importing") Finish(new Report { error = "PACKAGE_IMPORT_FAILED" }); };
        AssetDatabase.importPackageCancelled += name => { if (SessionState.GetString(Phase, "") == "importing") Finish(new Report { error = "PACKAGE_IMPORT_CANCELLED" }); };
        EditorApplication.update += Resume;
    }
    public static void Run()
    {
        try
        {
            if (Application.unityVersion != "2022.3.22f1" || File.Exists(Path.Combine(Root, "UnityReturnResult.json"))) throw new InvalidOperationException("GATE_ENVIRONMENT");
            if (File.Exists(Path.Combine(Root, "Source.unitypackage"))) throw new InvalidOperationException("GATE_SOURCE_SUBSTITUTION");
            if (Hash(Path.Combine(Root, "Output.unitypackage")) != OutputSha) throw new InvalidOperationException("GATE_OUTPUT_HASH");
            SessionState.SetFloat(Started, (float)EditorApplication.timeSinceStartup);
            SessionState.SetString(Phase, "importing");
            AssetDatabase.ImportPackage(Path.Combine(Root, "Output.unitypackage"), false);
        }
        catch (Exception e) { Finish(new Report { error = SafeError(e) }); }
    }
    static void Resume()
    {
        string phase = SessionState.GetString(Phase, "");
        if (phase != "importing" && phase != "imported") return;
        if (EditorApplication.timeSinceStartup - SessionState.GetFloat(Started, 0f) > 180f) { Finish(new Report { error = "IMPORT_TIMEOUT" }); return; }
        if (phase != "imported" || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
        Type finalizer = Type.GetType("VapbReferenceFinalizer, Assembly-CSharp-Editor");
        if (finalizer == null) return; // Imported Editor code must finish compiling.
        SessionState.SetString(Phase, "checking");
        var report = new Report();
        try
        {
            MethodInfo apply = finalizer.GetMethod("Apply", BindingFlags.Public | BindingFlags.Static);
            if (apply == null) throw new InvalidOperationException("GATE_FINALIZER_MISSING");
            report.finalizerApply = (bool)apply.Invoke(null, new object[] { Manifest });
            if (!report.finalizerApply) throw new InvalidOperationException("GATE_FINALIZER_APPLY");
            string prefabPath = AssetDatabase.GUIDToAssetPath(PrefabGuid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            MeshRenderer[] renderers = prefab == null ? new MeshRenderer[0] : prefab.GetComponentsInChildren<MeshRenderer>(true);
            if (renderers.Length != 1) throw new InvalidOperationException("GATE_RENDERER_COUNT");
            MeshRenderer renderer = renderers[0];
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            Mesh mesh = filter == null ? null : filter.sharedMesh;
            if (mesh == null) throw new InvalidOperationException("GATE_MESH_MISSING");
            report.prefabGuid = PrefabGuid;
            report.meshFromEditedModel = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string meshGuid, out long meshId) && meshGuid == ModelGuid && meshId != 0;
            report.meshGuid = meshGuid; report.meshFileId = meshId.ToString();
            report.submeshCount = mesh.subMeshCount; report.vertexCount = mesh.vertexCount;
            report.singleSubmesh = mesh.subMeshCount == 1;
            report.triangleCount = mesh.GetTriangles(0).Length / 3;
            report.meshBoundsSize = mesh.bounds.size;
            Vector3[] vertices = mesh.vertices;
            var bounds = new Bounds(prefab.transform.InverseTransformPoint(renderer.transform.TransformPoint(vertices[0])), Vector3.zero);
            foreach (Vector3 point in vertices) bounds.Encapsulate(prefab.transform.InverseTransformPoint(renderer.transform.TransformPoint(point)));
            report.prefabSpaceBoundsSize = bounds.size;
            report.shape125 = Near(bounds.size, new Vector3(2.5f, 2.5f, 2.5f));
            Material[] materials = renderer.sharedMaterials;
            if (materials.Length != 1 || materials[0] == null) throw new InvalidOperationException("GATE_MATERIAL_COUNT");
            report.materialIdentity = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(materials[0], out string matGuid, out long matId) && matGuid == MaterialGuid && matId == 2100000;
            report.materialGuid = matGuid; report.materialFileId = matId.ToString();
            Texture texture = materials[0].mainTexture;
            if (texture == null) throw new InvalidOperationException("GATE_TEXTURE_MISSING");
            report.textureIdentity = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out string texGuid, out long texId) && texGuid == TextureGuid && texId != 0;
            report.textureGuid = texGuid; report.textureFileId = texId.ToString();
            if (!report.meshFromEditedModel || !report.singleSubmesh || report.triangleCount != 12 || !report.shape125 || !report.materialIdentity || !report.textureIdentity) throw new InvalidOperationException("GATE_ASSERTIONS");
            report.status = "PASS_SINGLE_MATERIAL_EDITED_RETURN";
        }
        catch (Exception e) { report.error = SafeError(e); }
        Finish(report);
    }
    static bool Near(Vector3 a, Vector3 b) { return Mathf.Abs(a.x-b.x) <= 0.0001f && Mathf.Abs(a.y-b.y) <= 0.0001f && Mathf.Abs(a.z-b.z) <= 0.0001f; }
    static string Hash(string path) { using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    static string SafeError(Exception e) { return e is InvalidOperationException && e.Message.StartsWith("GATE_") ? e.Message : e.GetType().Name; }
    static void Finish(Report report)
    {
        SessionState.SetString(Phase, "finished");
        report.unityVersion = Application.unityVersion; report.outputSha256 = OutputSha;
        using (var stream = new StreamWriter(new FileStream(Path.Combine(Root, "UnityReturnResult.json"), FileMode.CreateNew))) stream.Write(JsonUtility.ToJson(report, true));
        Debug.Log("VAPB_SINGLE_MATERIAL_RETURN=" + report.status + ";" + report.error);
        EditorApplication.Exit(report.status == "PASS_SINGLE_MATERIAL_EDITED_RETURN" ? 0 : 1);
    }
}