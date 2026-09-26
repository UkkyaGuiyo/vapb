using System;
using System.IO;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbRoundtripProbe
{
    private const string Folder = "Assets/VapbRoundtrip";
    private const string Input = Folder + "/Input.fbx";
    private const string Prefab = Folder + "/Avatar.prefab";
    private const string MaterialPath = Folder + "/Original.mat";
    private const string Manifest = "Assets/VAPBExport/manifest.json";
    private const string SessionPhase = "VAPB_ROUNDTRIP_IMPORT_PHASE";
    private const string SessionImportStart = "VAPB_ROUNDTRIP_IMPORT_START";

    static VapbRoundtripProbe()
    {
        AssetDatabase.importPackageCompleted += OnPackageCompleted;
        AssetDatabase.importPackageFailed += OnPackageFailed;
        AssetDatabase.importPackageCancelled += OnPackageCancelled;
        EditorApplication.update += CheckImportTimeout;
        if (SessionState.GetString(SessionPhase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }

    private static void CheckImportTimeout()
    {
        if (SessionState.GetString(SessionPhase, "") != "importing")
            return;
        float started = SessionState.GetFloat(SessionImportStart, 0f);
        if (started > 0f && EditorApplication.timeSinceStartup - started > 180f)
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_TIMEOUT" });
    }

    private static void OnPackageCompleted(string packageName)
    {
        if (SessionState.GetString(SessionPhase, "") != "importing")
            return;
        SessionState.SetString(SessionPhase, "completed");
        EditorApplication.delayCall += ValidateImported;
    }

    private static void OnPackageFailed(string packageName, string error)
    {
        if (SessionState.GetString(SessionPhase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_FAILED" });
    }

    private static void OnPackageCancelled(string packageName)
    {
        if (SessionState.GetString(SessionPhase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_CANCELLED" });
    }

    [Serializable] private sealed class SourceInfo
    {
        public string prefab_guid;
        public string renderer_file_id;
        public string model_guid;
        public string material_guid;
        public string material_file_id;
        public string prefab_source_sha256;
        public string original_vertex_checksum;
        public int original_vertex_count;
        public Vector3 original_bounds_center;
        public Vector3 original_bounds_extents;
    }

    [Serializable] private sealed class OutputManifest
    {
        public OutputTask[] reference_rebind_tasks;
    }

    [Serializable] private sealed class OutputTask
    {
        public string model_guid;
        public string realization_id;
    }

    [Serializable] private sealed class Report
    {
        public bool pass;
        public string phase;
        public string error;
        public bool packageImported;
        public bool firstApply;
        public bool secondApply;
        public bool secondApplyUnchanged;
        public bool editedVertices;
        public bool expectedGeometryScale;
        public Vector3 originalBoundsCenter;
        public Vector3 originalBoundsExtents;
        public Vector3 editedBoundsCenter;
        public Vector3 editedBoundsExtents;
        public int originalVertexCount;
        public int editedVertexCount;
        public bool meshFromEditedModel;
        public bool materialPreserved;
        public bool unrelatedStatePreserved;
        public bool invalidTaskRejected;
        public bool invalidTaskUnchanged;
    }

    public static void Prepare()
    {
        var report = new Report { phase = "prepare", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            AssetDatabase.ImportAsset(Input, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
            Mesh sourceMesh = FindSingleDirectMesh(model);
            if (sourceMesh == null)
                throw new InvalidOperationException("INPUT_MODEL_UNSUPPORTED");

            Shader shader = Shader.Find("Standard");
            if (shader == null)
                throw new InvalidOperationException("STANDARD_SHADER_MISSING");
            Material material = new Material(shader) { name = "VapbOriginal" };
            AssetDatabase.CreateAsset(material, MaterialPath);

            GameObject root = new GameObject("AvatarRoot");
            try
            {
                GameObject rendererNode = new GameObject("EditableRenderer");
                rendererNode.transform.SetParent(root.transform, false);
                rendererNode.transform.localPosition = new Vector3(1.25f, 2.5f, -3.75f);
                rendererNode.AddComponent<MeshFilter>().sharedMesh = sourceMesh;
                rendererNode.AddComponent<MeshRenderer>().sharedMaterials = new[] { material };
                GameObject unrelated = new GameObject("UnrelatedSentinel");
                unrelated.transform.SetParent(root.transform, false);
                unrelated.transform.localPosition = new Vector3(4f, 5f, 6f);
                if (PrefabUtility.SaveAsPrefabAsset(root, Prefab) == null)
                    throw new InvalidOperationException("PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            // Saving Avatar.prefab names the stored asset root Avatar. This is
            // a display-state assertion, never the production identity lookup.
            if (prefab == null || prefab.name != "Avatar")
                throw new InvalidOperationException("SOURCE_ROOT_NAME_UNEXPECTED");
            MeshRenderer renderer = prefab.transform.Find("EditableRenderer").GetComponent<MeshRenderer>();
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string prefabGuid, out long rendererId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId))
                throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
            SourceInfo info = new SourceInfo
            {
                prefab_guid = prefabGuid,
                renderer_file_id = rendererId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                model_guid = AssetDatabase.AssetPathToGUID(Input),
                material_guid = materialGuid,
                material_file_id = materialId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                prefab_source_sha256 = FileHash(AssetFile(Prefab)),
                original_vertex_checksum = VertexChecksum(sourceMesh),
                original_vertex_count = sourceMesh.vertexCount,
                original_bounds_center = sourceMesh.bounds.center,
                original_bounds_extents = sourceMesh.bounds.extents
            };
            if (string.IsNullOrEmpty(info.model_guid))
                throw new InvalidOperationException("MODEL_GUID_UNAVAILABLE");
            File.WriteAllText(ProjectFile("SourceInfo.json"), JsonUtility.ToJson(info, true));
            AssetDatabase.ExportPackage(new[] { Input, Prefab, MaterialPath }, ProjectFile("Source.unitypackage"),
                ExportPackageOptions.IncludeDependencies);
            report.pass = File.Exists(ProjectFile("Source.unitypackage"));
            report.error = report.pass ? "NONE" : "PACKAGE_MISSING";
        }
        catch (Exception e) { report.error = SafeError(e); }
        Finish(report);
    }

    public static void Validate()
    {
        try
        {
            if (!File.Exists(ProjectFile("SourceInfo.json")) || !File.Exists(ProjectFile("Output.unitypackage")))
                throw new FileNotFoundException();
            SessionState.SetString(SessionPhase, "importing");
            SessionState.SetFloat(SessionImportStart, (float)EditorApplication.timeSinceStartup);
            AssetDatabase.ImportPackage(ProjectFile("Output.unitypackage"), false);
        }
        catch (Exception e)
        {
            Finish(new Report { phase = "validate", error = SafeError(e) });
        }
    }

    private static void ValidateImported()
    {
        if (SessionState.GetString(SessionPhase, "") != "completed")
            return;
        SessionState.SetString(SessionPhase, "validating");
        var report = new Report { phase = "validate", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            SourceInfo info = JsonUtility.FromJson<SourceInfo>(File.ReadAllText(ProjectFile("SourceInfo.json")));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            report.packageImported = AssetDatabase.LoadAssetAtPath<TextAsset>(Manifest) != null;
            if (!report.packageImported)
                throw new InvalidOperationException("MANIFEST_NOT_IMPORTED");
            OutputManifest output = JsonUtility.FromJson<OutputManifest>(File.ReadAllText(AssetFile(Manifest)));
            if (output == null || output.reference_rebind_tasks == null || output.reference_rebind_tasks.Length != 1 ||
                string.IsNullOrEmpty(output.reference_rebind_tasks[0].model_guid) ||
                string.IsNullOrEmpty(output.reference_rebind_tasks[0].realization_id))
                throw new InvalidOperationException("OUTPUT_TASK_INVALID");
            report.firstApply = VapbReferenceFinalizer.Apply(Manifest);
            if (!report.firstApply)
                throw new InvalidOperationException("FIRST_APPLY_FAILED");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            Transform node = prefab == null ? null : prefab.transform.Find("EditableRenderer");
            Transform unrelated = prefab == null ? null : prefab.transform.Find("UnrelatedSentinel");
            MeshFilter filter = node == null ? null : node.GetComponent<MeshFilter>();
            MeshRenderer renderer = node == null ? null : node.GetComponent<MeshRenderer>();
            Mesh mesh = filter == null ? null : filter.sharedMesh;
            report.unrelatedStatePreserved = prefab != null && prefab.name == "Avatar" &&
                node != null && node.localPosition == new Vector3(1.25f, 2.5f, -3.75f) &&
                unrelated != null && unrelated.localPosition == new Vector3(4f, 5f, 6f);
            report.editedVertices = mesh != null && VertexChecksum(mesh) != info.original_vertex_checksum;
            report.originalBoundsCenter = info.original_bounds_center;
            report.originalBoundsExtents = info.original_bounds_extents;
            report.originalVertexCount = info.original_vertex_count;
            if (mesh != null)
            {
                report.editedBoundsCenter = mesh.bounds.center;
                report.editedBoundsExtents = mesh.bounds.extents;
                report.editedVertexCount = mesh.vertexCount;
                report.expectedGeometryScale = mesh.vertexCount == info.original_vertex_count &&
                    Near(mesh.bounds.center, info.original_bounds_center * 1.25f) &&
                    Near(mesh.bounds.extents, info.original_bounds_extents * 1.25f);
            }
            report.meshFromEditedModel = mesh != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string meshGuid, out long meshId) &&
                meshGuid == output.reference_rebind_tasks[0].model_guid && meshId != 0;
            Material[] materials = renderer == null ? null : renderer.sharedMaterials;
            report.materialPreserved = materials != null && materials.Length == 1 && materials[0] != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(materials[0], out string materialGuid, out long materialId) &&
                materialGuid == info.material_guid &&
                materialId.ToString(System.Globalization.CultureInfo.InvariantCulture) == info.material_file_id;

            byte[] firstBytes = File.ReadAllBytes(AssetFile(Prefab));
            report.secondApply = VapbReferenceFinalizer.Apply(Manifest);
            report.secondApplyUnchanged = report.secondApply && EqualBytes(firstBytes, File.ReadAllBytes(AssetFile(Prefab)));

            string manifestText = File.ReadAllText(AssetFile(Manifest));
            string negativePath = "Assets/VAPBExport/negative-probe.json";
            string impossibleId = "9223372036854775806";
            if (info.renderer_file_id == impossibleId)
                impossibleId = "9223372036854775805";
            string badText = Regex.Replace(manifestText,
                "\"renderer_file_id\"\\s*:\\s*\"" + Regex.Escape(info.renderer_file_id) + "\"",
                "\"renderer_file_id\":\"" + impossibleId + "\"");
            if (badText == manifestText)
                throw new InvalidOperationException("TARGET_ID_NOT_IN_MANIFEST");
            File.WriteAllText(AssetFile(negativePath), badText);
            AssetDatabase.ImportAsset(negativePath, ImportAssetOptions.ForceUpdate);
            try
            {
                report.invalidTaskRejected = !VapbReferenceFinalizer.Apply(negativePath);
                report.invalidTaskUnchanged = EqualBytes(firstBytes, File.ReadAllBytes(AssetFile(Prefab)));
            }
            finally
            {
                AssetDatabase.DeleteAsset(negativePath);
            }

            report.pass = report.packageImported && report.firstApply && report.secondApply &&
                report.secondApplyUnchanged && report.editedVertices && report.expectedGeometryScale &&
                report.meshFromEditedModel &&
                report.materialPreserved && report.unrelatedStatePreserved &&
                report.invalidTaskRejected && report.invalidTaskUnchanged;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception e) { report.error = SafeError(e); }
        Finish(report);
    }

    private static bool Near(Vector3 a, Vector3 b)
    {
        return Mathf.Abs(a.x - b.x) <= 0.0001f && Mathf.Abs(a.y - b.y) <= 0.0001f &&
            Mathf.Abs(a.z - b.z) <= 0.0001f;
    }

    private static string SafeError(Exception e)
    {
        if (e is InvalidOperationException)
        {
            switch (e.Message)
            {
                case "INPUT_MODEL_UNSUPPORTED":
                case "STANDARD_SHADER_MISSING":
                case "PREFAB_SAVE_FAILED":
                case "ASSET_ID_UNAVAILABLE":
                case "MODEL_GUID_UNAVAILABLE":
                case "MANIFEST_NOT_IMPORTED":
                case "OUTPUT_TASK_INVALID":
                case "FIRST_APPLY_FAILED":
                case "TARGET_ID_NOT_IN_MANIFEST":
                    return e.Message;
            }
        }
        return e.GetType().Name;
    }

    private static Mesh FindSingleDirectMesh(GameObject model)
    {
        if (model == null)
            return null;
        Mesh found = null;
        foreach (MeshRenderer renderer in model.GetComponentsInChildren<MeshRenderer>(true))
        {
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null || found != null)
                return null;
            found = filter.sharedMesh;
        }
        return found;
    }

    private static string VertexChecksum(Mesh mesh)
    {
        using (SHA256 sha = SHA256.Create())
        using (MemoryStream stream = new MemoryStream())
        using (BinaryWriter writer = new BinaryWriter(stream))
        {
            Vector3[] vertices = mesh.vertices;
            writer.Write(vertices.Length);
            foreach (Vector3 v in vertices)
            {
                writer.Write(v.x);
                writer.Write(v.y);
                writer.Write(v.z);
            }
            writer.Flush();
            return Convert.ToBase64String(sha.ComputeHash(stream.ToArray()));
        }
    }

    private static string FileHash(string path)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }

    private static bool EqualBytes(byte[] a, byte[] b)
    {
        if (a.Length != b.Length)
            return false;
        for (int i = 0; i < a.Length; i++)
            if (a[i] != b[i])
                return false;
        return true;
    }

    private static string ProjectFile(string name)
    {
        return Path.Combine(Path.GetDirectoryName(Application.dataPath), name);
    }

    private static string AssetFile(string path)
    {
        return Path.Combine(Application.dataPath, path.Substring("Assets/".Length).Replace('/', Path.DirectorySeparatorChar));
    }

    private static void Finish(Report report)
    {
        SessionState.SetString(SessionPhase, "");
        try { File.WriteAllText(ProjectFile("VapbRoundtripResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_ROUNDTRIP_PASS" : "VAPB_ROUNDTRIP_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
