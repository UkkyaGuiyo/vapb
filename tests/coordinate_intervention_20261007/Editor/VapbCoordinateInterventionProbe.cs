using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Read-only observation runner for the authored coordinate intervention FBXs.
/// It does not invoke VAPB product import, rebind, or finalizer code.
/// </summary>
[InitializeOnLoad]
public static class VapbCoordinateInterventionProbe
{
#pragma warning disable 0649 // JsonUtility populates these serializable DTO fields from the manifest.
    [Serializable] private sealed class Manifest
    {
        public string schema;
        public string blender_version;
        public FixtureSpec spec;
        public FixtureCase[] cases;
    }
    [Serializable] private sealed class FixtureSpec { public string schema; public Geometry geometry; }
    [Serializable] private sealed class Geometry { public string geometry_id; public string[] materials; public Face[] faces; }
    [Serializable] private sealed class Uv { public float x; public float y; }
    [Serializable] private sealed class Face
    {
        public string face_id;
        public string material;
        public Uv[] uvs;
    }
    [Serializable] private sealed class FixtureCase
    {
        public string id;
        public string factor;
        public string filename;
        public string sha256;
        public string axis_up;
        public string axis_forward;
        public string unit_system;
        public float unit_scale_length;
        public string[] source_material_names;
        public string[] source_material_ids;
        public long[] source_material_fbx_uids;
    }
    [Serializable] private sealed class Result
    {
        public string schema = "vapb-coordinate-intervention-unity-capture-v1";
        public string material_identity_join_method = "fixture-authored-unique-material-name";
        public string status = "UNITY_OBSERVATION_UNPROVEN";
        public string unity_version;
        public string manifest_sha256;
        public string[] errors;
        public CapturedCase[] cases;
    }
    [Serializable] private sealed class CapturedCase
    {
        public string case_id;
        public string factor;
        public string input_sha256;
        public ImporterSettings importer;
        public TransformRow[] hierarchy;
        public RendererRow[] renderers;
        public bool face_membership_matches_source_identity;
        public int unmatched_face_count;
    }
    [Serializable] private sealed class ImporterSettings
    {
        public bool bake_axis_conversion;
        public bool use_file_scale;
        public bool use_file_units;
        public float global_scale;
        public string import_normals;
        public string import_tangents;
        public bool preserve_hierarchy;
        public string mesh_compression;
    }
    [Serializable] private sealed class TransformRow
    {
        public string path;
        public float[] local_matrix;
        public float[] world_matrix;
    }
    [Serializable] private sealed class RendererRow
    {
        public string transform_path;
        public string mesh_guid;
        public string mesh_local_file_id;
        public int vertex_count;
        public Vector3[] vertices_local;
        public Vector3[] normals_local;
        public Vector2[] uv0;
        public MaterialRow[] materials;
        public SubmeshRow[] submeshes;
    }
    [Serializable] private sealed class MaterialRow
    {
        public string name_diagnostic;
        public string imported_asset_path;
        public string fixture_material_id_from_pinned_input_connection;
        public long source_fbx_material_object_uid;
        public string guid;
        public string local_file_id;
    }
    [Serializable] private sealed class SubmeshRow
    {
        public int submesh_index;
        public int triangle_count;
        public int[] indices;
        public FaceRow[] faces;
    }
    [Serializable] private sealed class FaceRow
    {
        public string face_id_by_corner_uv;
        public string source_material_id;
        public string renderer_material_id;
        public Vector2[] corner_uvs;
        public int[] vertex_indices;
    }
#pragma warning restore 0649

    private const string AssetsRoot = "Assets/VapbCoordinateIntervention";
    private static bool started;
    private static int importWaitTicks;

    private sealed class CaptureContext
    {
        public string result_path;
    }

    static VapbCoordinateInterventionProbe()
    {
        if (HasArgument("-vapbCoordinateManifest") && !started)
        {
            started = true;
            EditorApplication.delayCall += Capture;
        }
    }

    private static void Capture()
    {
        var context = new CaptureContext();
        ProbeCaptureExitGuard.Run(
            () => CaptureBody(context),
            exception =>
            {
                var failure = new Result
                {
                    unity_version = Application.unityVersion,
                    errors = new[] { exception.GetType().Name + ":" + exception.Message },
                };
                ProbeCaptureExitGuard.TryRecordFailure(context.result_path,
                    JsonUtility.ToJson(failure, true), WriteNew,
                    writeException => Debug.LogError("VAPB coordinate failure record could not be written: "
                        + writeException));
                Debug.LogException(exception);
            },
            recordException => Debug.LogError("VAPB coordinate failure reporting failed: " + recordException),
            EditorApplication.Exit);
    }

    private static int? CaptureBody(CaptureContext context)
    {
        context.result_path = Argument("-vapbCoordinateResult");
        string resultPath = context.result_path;
        string manifestPath = Argument("-vapbCoordinateManifest");
        string manifestBytes = File.ReadAllText(manifestPath, Encoding.UTF8);
        Manifest manifest = JsonUtility.FromJson<Manifest>(manifestBytes);
        if (manifest == null || manifest.cases == null || manifest.cases.Length != 7 || manifest.spec == null)
            throw new InvalidOperationException("MANIFEST_SHAPE_INVALID");
        if (!AllModelsImported(manifest))
        {
            if (++importWaitTicks <= 120)
            {
                EditorApplication.delayCall += Capture;
                return null;
            }
            throw new InvalidOperationException("MODEL_IMPORTS_NOT_READY_AFTER_120_EDITOR_TICKS");
        }
        if (!string.Equals(Application.unityVersion, "2022.3.22f1", StringComparison.Ordinal))
            throw new InvalidOperationException("UNITY_VERSION_MISMATCH:" + Application.unityVersion);

        var result = new Result
        {
            unity_version = Application.unityVersion,
            manifest_sha256 = Sha256(manifestPath),
            errors = Array.Empty<string>(),
        };
        var captured = new List<CapturedCase>();
        var errors = new List<string>();
        foreach (FixtureCase fixtureCase in manifest.cases)
            captured.Add(CaptureCase(fixtureCase, manifest.spec.geometry, errors));
        if (!SameImporterSettings(captured))
            errors.Add("MODEL_IMPORTER_SETTINGS_DIFFER_BETWEEN_CASES");
        result.cases = captured.ToArray();
        result.errors = errors.ToArray();
        bool allMapped = captured.Count == 7 && captured.All(c => c.face_membership_matches_source_identity
            && c.unmatched_face_count == 0);
        result.status = allMapped && errors.Count == 0
            ? "UNITY_FACE_IDENTITY_CAPTURED"
            : "UNITY_FACE_IDENTITY_UNPROVEN";
        WriteNew(resultPath, JsonUtility.ToJson(result, true));
        return allMapped && errors.Count == 0 ? 0 : 1;
    }

    private static bool AllModelsImported(Manifest manifest)
    {
        foreach (FixtureCase fixtureCase in manifest.cases)
        {
            string path = AssetsRoot + "/" + fixtureCase.filename;
            if (!(AssetImporter.GetAtPath(path) is ModelImporter)) return false;
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (root == null) return false;
            bool hasMeshRenderer = root.GetComponentsInChildren<MeshRenderer>(true)
                .Any(renderer => renderer.GetComponent<MeshFilter>() != null
                                 && renderer.GetComponent<MeshFilter>().sharedMesh != null);
            bool hasSkinRenderer = root.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Any(renderer => renderer.sharedMesh != null);
            if (!hasMeshRenderer && !hasSkinRenderer) return false;
        }
        return true;
    }

    private static bool SameImporterSettings(List<CapturedCase> captured)
    {
        if (captured.Count < 2) return false;
        ImporterSettings baseline = captured[0].importer;
        return captured.Skip(1).All(item =>
            item.importer.bake_axis_conversion == baseline.bake_axis_conversion
            && item.importer.use_file_scale == baseline.use_file_scale
            && item.importer.use_file_units == baseline.use_file_units
            && item.importer.global_scale.Equals(baseline.global_scale)
            && item.importer.import_normals == baseline.import_normals
            && item.importer.import_tangents == baseline.import_tangents
            && item.importer.preserve_hierarchy == baseline.preserve_hierarchy
            && item.importer.mesh_compression == baseline.mesh_compression);
    }

    private static CapturedCase CaptureCase(FixtureCase fixtureCase, Geometry geometry, List<string> errors)
    {
        string assetPath = AssetsRoot + "/" + fixtureCase.filename;
        string diskPath = Path.Combine(Application.dataPath, "VapbCoordinateIntervention", fixtureCase.filename);
        if (!File.Exists(diskPath) || Sha256(diskPath) != fixtureCase.sha256)
            throw new InvalidOperationException("FIXTURE_INPUT_HASH_MISMATCH:" + fixtureCase.id);
        ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
        if (importer == null || model == null)
            throw new InvalidOperationException("MODEL_IMPORT_NOT_READY:" + fixtureCase.id);

        var caseResult = new CapturedCase
        {
            case_id = fixtureCase.id,
            factor = fixtureCase.factor,
            input_sha256 = fixtureCase.sha256,
            face_membership_matches_source_identity = true,
            importer = new ImporterSettings
            {
                bake_axis_conversion = importer.bakeAxisConversion,
                use_file_scale = importer.useFileScale,
                use_file_units = importer.useFileUnits,
                global_scale = importer.globalScale,
                import_normals = importer.importNormals.ToString(),
                import_tangents = importer.importTangents.ToString(),
                preserve_hierarchy = importer.preserveHierarchy,
                mesh_compression = importer.meshCompression.ToString(),
            },
            hierarchy = CaptureHierarchy(model.transform),
        };
        var identityByName = new Dictionary<string, string>(StringComparer.Ordinal);
        if (fixtureCase.source_material_names == null || fixtureCase.source_material_ids == null
            || fixtureCase.source_material_fbx_uids == null
            || fixtureCase.source_material_names.Length != fixtureCase.source_material_ids.Length
            || fixtureCase.source_material_names.Length != fixtureCase.source_material_fbx_uids.Length)
            throw new InvalidOperationException("SOURCE_MATERIAL_IDENTITY_MAP_INVALID:" + fixtureCase.id);
        var sourceFbxUidByName = new Dictionary<string, long>(StringComparer.Ordinal);
        for (int i = 0; i < fixtureCase.source_material_names.Length; i++)
        {
            identityByName.Add(fixtureCase.source_material_names[i], fixtureCase.source_material_ids[i]);
            sourceFbxUidByName.Add(fixtureCase.source_material_names[i], fixtureCase.source_material_fbx_uids[i]);
        }

        var renderers = new List<RendererRow>();
        foreach (MeshRenderer renderer in model.GetComponentsInChildren<MeshRenderer>(true))
        {
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null)
                throw new InvalidOperationException("MESH_FILTER_MISSING:" + fixtureCase.id);
            renderers.Add(CaptureRenderer(renderer, filter.sharedMesh, identityByName, sourceFbxUidByName,
                geometry, caseResult, errors));
        }
        foreach (SkinnedMeshRenderer renderer in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            if (renderer.sharedMesh != null)
                renderers.Add(CaptureRenderer(renderer, renderer.sharedMesh, identityByName, sourceFbxUidByName,
                    geometry, caseResult, errors));
        if (renderers.Count != 1)
            throw new InvalidOperationException("EXPECTED_ONE_RENDERER:" + fixtureCase.id + ":" + renderers.Count);
        caseResult.renderers = renderers.ToArray();
        return caseResult;
    }

    private static RendererRow CaptureRenderer(Renderer renderer, Mesh mesh,
        Dictionary<string, string> identityByName, Dictionary<string, long> sourceFbxUidByName,
        Geometry geometry, CapturedCase owner, List<string> errors)
    {
        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string meshGuid, out long meshLocalId))
            throw new InvalidOperationException("MESH_ASSET_IDENTITY_UNAVAILABLE:" + renderer.name);
        var uvValues = new List<Vector2>();
        mesh.GetUVs(0, uvValues);
        var materialRows = new List<MaterialRow>();
        Material[] sharedMaterials = renderer.sharedMaterials;
        for (int i = 0; i < sharedMaterials.Length; i++)
        {
            Material material = sharedMaterials[i];
            string guid = "", localId = "", logicalId = "";
            long sourceFbxUid = 0;
            if (material != null)
            {
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out guid, out long materialId);
                localId = materialId.ToString(CultureInfo.InvariantCulture);
                identityByName.TryGetValue(material.name, out logicalId);
                sourceFbxUidByName.TryGetValue(material.name, out sourceFbxUid);
            }
            if (string.IsNullOrEmpty(logicalId))
                errors.Add("MATERIAL_CONNECTION_IDENTITY_UNRESOLVED:" + renderer.name + ":slot=" + i);
            materialRows.Add(new MaterialRow
            {
                name_diagnostic = material != null ? material.name : "",
                imported_asset_path = material != null ? AssetDatabase.GetAssetPath(material) : "",
                fixture_material_id_from_pinned_input_connection = logicalId ?? "",
                source_fbx_material_object_uid = sourceFbxUid,
                guid = guid ?? "",
                local_file_id = localId,
            });
        }

        var expectedByUv = new Dictionary<string, Face>(StringComparer.Ordinal);
        foreach (Face face in geometry.faces)
            expectedByUv.Add(UvKey(face.uvs.Select(uv => new Vector2(uv.x, uv.y))), face);
        var submeshes = new List<SubmeshRow>();
        var seenFaceIds = new HashSet<string>(StringComparer.Ordinal);
        int unmatched = 0;
        bool membershipMatches = true;
        for (int submeshIndex = 0; submeshIndex < mesh.subMeshCount; submeshIndex++)
        {
            int[] indices = mesh.GetTriangles(submeshIndex, true);
            var faces = new List<FaceRow>();
            string rendererMaterialId = submeshIndex < materialRows.Count
                ? materialRows[submeshIndex].fixture_material_id_from_pinned_input_connection : "";
            for (int offset = 0; offset + 2 < indices.Length; offset += 3)
            {
                int[] triangleIndices = { indices[offset], indices[offset + 1], indices[offset + 2] };
                if (triangleIndices.Any(index => index < 0 || index >= uvValues.Count))
                    throw new InvalidOperationException("UV_VERTEX_INDEX_INVALID:" + renderer.name);
                Vector2[] cornerUvs = triangleIndices.Select(index => uvValues[index]).ToArray();
                expectedByUv.TryGetValue(UvKey(cornerUvs), out Face sourceFace);
                string sourceMaterialId = sourceFace != null ? sourceFace.material : "";
                string faceId = sourceFace != null ? sourceFace.face_id : "UNMATCHED";
                if (sourceFace == null || !seenFaceIds.Add(faceId)) unmatched++;
                if (sourceFace == null || sourceMaterialId != rendererMaterialId) membershipMatches = false;
                faces.Add(new FaceRow
                {
                    face_id_by_corner_uv = faceId,
                    source_material_id = sourceMaterialId,
                    renderer_material_id = rendererMaterialId,
                    corner_uvs = cornerUvs,
                    vertex_indices = triangleIndices,
                });
            }
            submeshes.Add(new SubmeshRow
            {
                submesh_index = submeshIndex,
                triangle_count = indices.Length / 3,
                indices = indices,
                faces = faces.ToArray(),
            });
        }
        membershipMatches &= seenFaceIds.Count == geometry.faces.Length;
        owner.face_membership_matches_source_identity &= membershipMatches;
        owner.unmatched_face_count += unmatched;

        return new RendererRow
        {
            transform_path = TransformPath(renderer.transform),
            mesh_guid = meshGuid,
            mesh_local_file_id = meshLocalId.ToString(CultureInfo.InvariantCulture),
            vertex_count = mesh.vertexCount,
            vertices_local = mesh.vertices,
            normals_local = mesh.normals,
            uv0 = uvValues.ToArray(),
            materials = materialRows.ToArray(),
            submeshes = submeshes.ToArray(),
        };
    }

    private static TransformRow[] CaptureHierarchy(Transform root)
    {
        var rows = new List<TransformRow>();
        void Visit(Transform current)
        {
            rows.Add(new TransformRow
            {
                path = TransformPath(current),
                local_matrix = Flatten(Matrix4x4.TRS(current.localPosition, current.localRotation, current.localScale)),
                world_matrix = Flatten(current.localToWorldMatrix),
            });
            for (int i = 0; i < current.childCount; i++) Visit(current.GetChild(i));
        }
        Visit(root);
        return rows.ToArray();
    }

    private static float[] Flatten(Matrix4x4 matrix)
    {
        var values = new float[16];
        int offset = 0;
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++) values[offset++] = matrix[row, column];
        return values;
    }

    private static string TransformPath(Transform transform)
    {
        var names = new Stack<string>();
        while (transform != null) { names.Push(transform.name); transform = transform.parent; }
        return string.Join("/", names.ToArray());
    }

    private static string UvKey(IEnumerable<Vector2> values)
    {
        // The per-face U triplet uniquely identifies a triangle even if an importer flips V.
        return string.Join(";", values.Select(v => Mathf.RoundToInt(v.x * 1000f)
            .ToString(CultureInfo.InvariantCulture)).OrderBy(value => value, StringComparer.Ordinal));
    }

    private static string Sha256(string path)
    {
        using (var stream = File.OpenRead(path))
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
    }

    private static void WriteNew(string path, string contents)
    {
        if (string.IsNullOrWhiteSpace(path)) throw new InvalidOperationException("RESULT_PATH_REQUIRED");
        string fullPath = Path.GetFullPath(path);
        Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
        using (var stream = new FileStream(fullPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.Write(contents);
    }

    private static bool HasArgument(string name) => Environment.GetCommandLineArgs().Any(arg => arg == name);
    private static string Argument(string name)
    {
        return ProbeCaptureExitGuard.RequiredArgument(Environment.GetCommandLineArgs(), name);
    }
}
