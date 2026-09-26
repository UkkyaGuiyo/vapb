using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public sealed class VapbMarkerPostprocessor : AssetPostprocessor
{
    internal const string AssetPath = "Assets/VapbProbe/Synthetic.fbx";
    internal const string PropertyName = "_vapb_fbx_realization_id";
    internal const string ExpectedValue = "synthetic-realization-001";
    internal static int ExpectedPropertyCallbacks;

    private void OnPostprocessGameObjectWithUserProperties(
        GameObject gameObject, string[] propertyNames, object[] values)
    {
        if (assetPath != AssetPath || propertyNames == null || values == null)
            return;

        int count = Math.Min(propertyNames.Length, values.Length);
        for (int i = 0; i < count; i++)
        {
            if (propertyNames[i] != PropertyName)
                continue;

            ExpectedPropertyCallbacks++;
            string value = values[i] as string;
            if (value != ExpectedValue)
                continue;

            VapbSyntheticMarker marker = gameObject.GetComponent<VapbSyntheticMarker>();
            if (marker == null)
                marker = gameObject.AddComponent<VapbSyntheticMarker>();
            marker.realizationId = value;
        }
    }
}

public static class VapbMarkerProbe
{
    [Serializable]
    private sealed class Report
    {
        public bool pass;
        public string unityVersion;
        public string error;
        public int firstMarkerCount;
        public int secondMarkerCount;
        public bool firstCallbackObserved;
        public bool secondCallbackObserved;
        public bool rendererFound;
        public bool meshFound;
        public bool positiveVertexCount;
        public bool markerGameObjectIdAvailable;
        public bool rendererIdAvailable;
        public bool meshIdAvailable;
        public bool markerGameObjectIdStable;
        public bool rendererIdStable;
        public bool meshIdStable;
        public int warningCount;
        public int errorLogCount;
    }

    private struct AssetIdentity
    {
        public string guid;
        public long localId;
        public bool available;

        public bool SameAs(AssetIdentity other)
        {
            return available && other.available && guid == other.guid && localId == other.localId;
        }
    }

    private sealed class Snapshot
    {
        public int markerCount;
        public bool markerValueCorrect;
        public bool rendererFound;
        public bool meshFound;
        public bool positiveVertexCount;
        public AssetIdentity markerGameObjectId;
        public AssetIdentity rendererId;
        public AssetIdentity meshId;
    }

    private static int warningCount;
    private static int errorLogCount;

    public static void Run()
    {
        Report report = new Report { unityVersion = Application.unityVersion, error = "UNEXPECTED_EXCEPTION" };
        warningCount = 0;
        errorLogCount = 0;
        Application.logMessageReceived += CountLog;
        try
        {
            VapbMarkerPostprocessor.ExpectedPropertyCallbacks = 0;
            AssetDatabase.ImportAsset(VapbMarkerPostprocessor.AssetPath, ImportAssetOptions.ForceUpdate);
            report.firstCallbackObserved = VapbMarkerPostprocessor.ExpectedPropertyCallbacks > 0;
            Snapshot first = ReadSnapshot();
            CopyObserved(first, report, true);

            VapbMarkerPostprocessor.ExpectedPropertyCallbacks = 0;
            AssetDatabase.ImportAsset(VapbMarkerPostprocessor.AssetPath, ImportAssetOptions.ForceUpdate);
            report.secondCallbackObserved = VapbMarkerPostprocessor.ExpectedPropertyCallbacks > 0;
            Snapshot second = ReadSnapshot();
            CopyObserved(second, report, false);

            report.markerGameObjectIdStable = first.markerGameObjectId.SameAs(second.markerGameObjectId);
            report.rendererIdStable = first.rendererId.SameAs(second.rendererId);
            report.meshIdStable = first.meshId.SameAs(second.meshId);

            report.error = Failure(first, second, report);
            report.pass = report.error == "NONE";
        }
        catch
        {
            // Exception text and stack traces can contain project paths or imported data.
            report.error = "UNEXPECTED_EXCEPTION";
        }
        finally
        {
            Application.logMessageReceived -= CountLog;
            report.warningCount = warningCount;
            report.errorLogCount = errorLogCount;
            try
            {
                string projectRoot = Path.GetDirectoryName(Application.dataPath);
                File.WriteAllText(Path.Combine(projectRoot, "VapbMarkerProbeResult.json"),
                    JsonUtility.ToJson(report, true));
            }
            catch
            {
                report.pass = false;
                report.error = "REPORT_WRITE_FAILED";
            }

            Debug.Log(report.pass ? "VAPB_MARKER_PROBE_PASS" : "VAPB_MARKER_PROBE_FAIL");
            EditorApplication.Exit(report.pass ? 0 : 1);
        }
    }

    private static void CountLog(string condition, string stackTrace, LogType type)
    {
        if (type == LogType.Warning)
            warningCount++;
        else if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert)
            errorLogCount++;
    }

    private static Snapshot ReadSnapshot()
    {
        Snapshot result = new Snapshot();
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(VapbMarkerPostprocessor.AssetPath);
        if (model == null)
            return result;

        VapbSyntheticMarker[] markers = model.GetComponentsInChildren<VapbSyntheticMarker>(true);
        result.markerCount = markers.Length;
        if (markers.Length != 1)
            return result;

        VapbSyntheticMarker marker = markers[0];
        result.markerValueCorrect = marker.realizationId == VapbMarkerPostprocessor.ExpectedValue;
        result.markerGameObjectId = GetIdentity(marker.gameObject);

        Renderer[] renderers = marker.GetComponents<Renderer>();
        if (renderers.Length != 1)
            return result;

        Renderer renderer = renderers[0];
        result.rendererFound = true;
        result.rendererId = GetIdentity(renderer);
        Mesh mesh = null;
        SkinnedMeshRenderer skinned = renderer as SkinnedMeshRenderer;
        if (skinned != null)
            mesh = skinned.sharedMesh;
        else if (renderer is MeshRenderer)
        {
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            if (filter != null)
                mesh = filter.sharedMesh;
        }

        if (mesh != null)
        {
            result.meshFound = true;
            result.positiveVertexCount = mesh.vertexCount > 0;
            result.meshId = GetIdentity(mesh);
        }
        return result;
    }

    private static AssetIdentity GetIdentity(UnityEngine.Object value)
    {
        AssetIdentity result = new AssetIdentity();
        if (value != null &&
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out result.guid, out result.localId))
            result.available = !string.IsNullOrEmpty(result.guid) && result.localId != 0;
        return result;
    }

    private static void CopyObserved(Snapshot snapshot, Report report, bool first)
    {
        if (first)
            report.firstMarkerCount = snapshot.markerCount;
        else
            report.secondMarkerCount = snapshot.markerCount;

        report.rendererFound = snapshot.rendererFound;
        report.meshFound = snapshot.meshFound;
        report.positiveVertexCount = snapshot.positiveVertexCount;
        report.markerGameObjectIdAvailable = snapshot.markerGameObjectId.available;
        report.rendererIdAvailable = snapshot.rendererId.available;
        report.meshIdAvailable = snapshot.meshId.available;
    }

    private static string Failure(Snapshot first, Snapshot second, Report report)
    {
        if (!report.firstCallbackObserved || !report.secondCallbackObserved)
            return "CALLBACK_MISSING";
        if (first.markerCount != 1 || second.markerCount != 1 ||
            !first.markerValueCorrect || !second.markerValueCorrect)
            return "MARKER_MISSING_OR_INVALID";
        if (!first.rendererFound || !second.rendererFound ||
            !first.meshFound || !second.meshFound ||
            !first.positiveVertexCount || !second.positiveVertexCount)
            return "MESH_STRUCTURE_INVALID";
        if (!first.markerGameObjectId.available || !second.markerGameObjectId.available ||
            !first.rendererId.available || !second.rendererId.available ||
            !first.meshId.available || !second.meshId.available)
            return "ASSET_ID_UNAVAILABLE";
        if (!report.markerGameObjectIdStable || !report.rendererIdStable || !report.meshIdStable)
            return "ASSET_ID_CHANGED";
        if (errorLogCount != 0 || warningCount != 0)
            return "UNITY_LOG_WARNING_OR_ERROR";
        return "NONE";
    }
}
