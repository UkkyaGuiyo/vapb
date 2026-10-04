using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// Public synthetic GREEN regression for whole-final-Mesh assignment. Its
// fixture-specific source/final comparisons validate this exact input only;
// they are not product acceptance predicates. The hash-bound witness may
// temporarily rewrite/reimport source FBX, then must restore bytes and metadata.
public static class VapbModelSkinTopologyBoundaryGreenProbe
{
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string ResultName = "VapbModelSkinTopologyBoundaryReplacementV7Result.json";
    private const string ExpectedKind = "RESTORE_MODEL_SKIN_VARIANT_V1";
    private const string RootMarker = ".vapb-stage3-owned-test-root";
    private const string SourceMarker = ".vapb-stage3-owned-source-project";
    private const string TargetMarker = ".vapb-disposable-unity-test-project";

    [Serializable] private sealed class Manifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string prefab_guid;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string model_guid;
        public string model_sha256;
        public string variant_path;
        public BoneMapping[] bone_mappings;
        public string witness_noop_path;
        public string witness_path;
        public MaterialBinding[] material_bindings;
    }
    [Serializable] private sealed class BoneMapping
    {
        public string edited_bone_realization_id;
        public string source_model_uid;
    }
    [Serializable] private sealed class MaterialBinding
    {
        public string transport_id;
        public string guid;
        public string file_id;
    }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string error;
        public bool finalizer_applied;
        public bool variant_created;
        public bool variant_is_source_prefab_child;
        public bool variant_uses_exact_final_mesh;
        public bool variant_bones_match_exported_uids;
        public bool variant_materials_match_transport;
        public bool variant_renderer_state_preserved;
        public bool variant_structure_preserved;
        public bool repeat_apply_idempotent;
        public bool bounds_tolerance_boundary_verified;
        public string prefab_guid_before;
        public string prefab_guid_after;
        public string task_kind;
        public int source_vertex_count;
        public int final_vertex_count;
        public string final_vertex_attributes;
        public float[] target_local_bounds_min;
        public float[] target_local_bounds_max;
        public float[] final_mesh_bounds_min;
        public float[] final_mesh_bounds_max;
        public float[] final_vertex_min;
        public float[] final_vertex_max;
        public float[] source_mesh_bounds_min;
        public float[] source_mesh_bounds_max;
        public float[] source_renderer_local_bounds_min;
        public float[] source_renderer_local_bounds_max;
        public float[] edited_renderer_local_bounds_min;
        public float[] edited_renderer_local_bounds_max;
        public float[] source_renderer_local_to_world;
        public float[] edited_renderer_local_to_world;
        public float[] target_renderer_local_to_world;
        public float[] target_root_bone_local_to_world;
        public float[] target_renderer_world_bounds_min;
        public float[] target_renderer_world_bounds_max;
        public float[] variant_renderer_world_bounds_min;
        public float[] variant_renderer_world_bounds_max;
        public bool variant_final_skin_bounds_contained;
        public bool variant_baked_skin_bounds_contained;
        public float variant_baked_vs_skin_equation_bounds_delta;
        public float[] variant_final_skin_root_bounds_min;
        public float[] variant_final_skin_root_bounds_max;
        public float[] variant_final_skin_world_bounds_min;
        public float[] variant_final_skin_world_bounds_max;
        public float[] variant_baked_skin_root_bounds_min;
        public float[] variant_baked_skin_root_bounds_max;
        public float[] variant_baked_skin_world_bounds_min;
        public float[] variant_baked_skin_world_bounds_max;
        public float[] source_baked_bounds_min;
        public float[] source_baked_bounds_max;
        public float[] edited_baked_bounds_min;
        public float[] edited_baked_bounds_max;
        public float[] target_baked_bounds_min;
        public float[] target_baked_bounds_max;
        public string baked_bounds_error;
        public int source_triangle_count;
        public int final_triangle_count;
        public int source_index_count;
        public int final_index_count;
        public int source_bone_count;
        public int final_bone_count;
        public bool source_and_final_meshes_have_one_submesh;
        public bool source_and_final_shapes_empty;
        public bool valid_source_and_final_weights;
        public bool source_and_final_geometric_faces_and_bone_weights_match;
        public bool final_uv_seam_proves_two_vertex_splits;
        public bool same_bone_uid_bijection;
        public bool same_root_uid;
        public bool same_parent_uids;
        public bool rest_bindpose_parity;
        public BoneRestRow[] bone_rest_rows;
        public bool source_model_unchanged;
        public bool edited_model_unchanged;
        public bool prefab_unchanged;
        public bool manifest_unchanged;
        public string unknown_index_dependent_components;
    }
    [Serializable] private sealed class BoneRestRow
    {
        public string source_model_uid;
        public int source_slot;
        public int final_slot;
        public string source_parent_uid;
        public string prefab_parent_uid;
        public string final_parent_uid;
        public float source_bindpose_max_error;
        public float final_bindpose_max_error;
        public float final_rest_max_error;
        public float[] expected;
        public float[] source_bindpose;
        public float[] final_bindpose;
        public float[] final_rest;
    }

    public static void Run()
    {
        var report = new Report {
            unknown_index_dependent_components =
                "UNSUPPORTED: this fixture permits only Transform, SkinnedMeshRenderer and VAPB markers"
        };
        string projectRoot = Path.GetFullPath(Path.GetDirectoryName(Application.dataPath));
        string resultFile = Path.Combine(projectRoot, ResultName);
        string guardError = ValidateOwnedProject(projectRoot);
        if (guardError != null)
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_BOUNDARY_GREEN_BLOCKED=" + guardError);
            return;
        }
        if (Occupied(resultFile))
        {
            Debug.LogError("VAPB_MODEL_SKIN_TOPOLOGY_BOUNDARY_GREEN_BLOCKED=RESULT_ALREADY_EXISTS");
            return;
        }

        string observedLog = null;
        int appliedLogCount = 0;
        Application.LogCallback capture = (condition, stackTrace, type) => {
            if (condition.StartsWith("VAPB_MODEL_SKIN_VARIANT_APPLIED=", StringComparison.Ordinal))
                appliedLogCount++;
            if (type == LogType.Error && condition.StartsWith(
                "VAPB_MODEL_SKIN_VARIANT_REJECTED=", StringComparison.Ordinal)) observedLog = condition;
        };
        Application.logMessageReceived += capture;
        try
        {
            string manifestFile = Disk(ManifestPath);
            if (!File.Exists(manifestFile)) throw new InvalidOperationException("MANIFEST_MISSING");
            byte[] manifestBefore = File.ReadAllBytes(manifestFile);
            byte[] manifestMetaBefore = ReadIfPresent(manifestFile + ".meta");
            string manifestText = File.ReadAllText(manifestFile);
            Manifest manifest = JsonUtility.FromJson<Manifest>(manifestText);
            if (manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 1 || manifest.reference_rebind_tasks[0] == null)
                throw new InvalidOperationException("TASK_CARDINALITY_INVALID");
            Task task = manifest.reference_rebind_tasks[0];
            report.task_kind = task.kind;
            if (task.kind != ExpectedKind) throw new InvalidOperationException("NORMAL_KIND_REQUIRED");

            string prefabPath = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            string sourcePath = AssetDatabase.GUIDToAssetPath(task.source_model_guid);
            string editedPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            if (!OwnedAssetPath(prefabPath) || !OwnedAssetPath(sourcePath) || !OwnedAssetPath(editedPath))
                throw new InvalidOperationException("SOURCE_ASSET_PATH_INVALID");
            string prefabFile = Disk(prefabPath), sourceFile = Disk(sourcePath), editedFile = Disk(editedPath);
            if (HasReparseComponent(prefabFile) || HasReparseComponent(sourceFile) ||
                HasReparseComponent(editedFile) || HasReparseComponent(prefabFile + ".meta") ||
                HasReparseComponent(sourceFile + ".meta") || HasReparseComponent(editedFile + ".meta") ||
                HasReparseComponent(Disk(ManifestPath) + ".meta"))
                throw new InvalidOperationException("ASSET_PATH_REPARSE_POINT");
            if (!File.Exists(prefabFile) || !File.Exists(sourceFile) || !File.Exists(editedFile))
                throw new InvalidOperationException("SOURCE_ASSET_MISSING");
            if (Hash(prefabFile) != task.prefab_source_sha256 || Hash(sourceFile) != task.source_model_sha256 ||
                Hash(editedFile) != task.model_sha256)
                throw new InvalidOperationException("SOURCE_HASH_MISMATCH");
            byte[] prefabBefore = File.ReadAllBytes(prefabFile);
            byte[] prefabMetaBefore = ReadIfPresent(prefabFile + ".meta");
            byte[] sourceBefore = File.ReadAllBytes(sourceFile);
            byte[] sourceMetaBefore = ReadIfPresent(sourceFile + ".meta");
            byte[] editedBefore = File.ReadAllBytes(editedFile);
            byte[] editedMetaBefore = ReadIfPresent(editedFile + ".meta");
            if (!OwnedAssetPath(task.witness_noop_path) || !OwnedAssetPath(task.witness_path))
                throw new InvalidOperationException("WITNESS_PATH_INVALID");
            string witnessNoopFile = Disk(task.witness_noop_path);
            string witnessFile = Disk(task.witness_path);
            if (HasReparseComponent(witnessNoopFile) || HasReparseComponent(witnessNoopFile + ".meta") ||
                HasReparseComponent(witnessFile) || HasReparseComponent(witnessFile + ".meta"))
                throw new InvalidOperationException("WITNESS_PATH_REPARSE_POINT");

            if (!OwnedAssetPath(task.variant_path)) throw new InvalidOperationException("VARIANT_PATH_INVALID");
            string variantFile = Disk(task.variant_path);
            if (HasReparseComponent(Path.GetDirectoryName(variantFile)))
                throw new InvalidOperationException("VARIANT_PATH_REPARSE_POINT");
            if (Occupied(variantFile) ||
                AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path) != null)
                throw new InvalidOperationException("VARIANT_ALREADY_EXISTS");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null) throw new InvalidOperationException("PREFAB_MISSING");
            report.prefab_guid_before = AssetDatabase.AssetPathToGUID(prefabPath);
            SkinnedMeshRenderer prefabSkin = SingleSkin(prefab);
            if (prefabSkin == null || prefabSkin.sharedMesh == null || prefabSkin.sharedMesh.blendShapeCount != 0)
                throw new InvalidOperationException("SOURCE_PREFAB_SKIN_SCOPE_INVALID");
            Bounds prefabLocalBounds = prefabSkin.localBounds;
            if (!Finite(prefabLocalBounds.center) || !Finite(prefabLocalBounds.extents) ||
                prefabLocalBounds.extents.x < 0 || prefabLocalBounds.extents.y < 0 || prefabLocalBounds.extents.z < 0)
                throw new InvalidOperationException("SOURCE_LOCAL_BOUNDS_INVALID");
            foreach (Component component in prefab.GetComponentsInChildren<Component>(true))
            {
                if (component == null) throw new InvalidOperationException("MISSING_COMPONENT_UNSUPPORTED");
                if (component is Transform || component is SkinnedMeshRenderer ||
                    component is VapbRealizationMarker || component is VapbExportObjectMarker) continue;
                throw new InvalidOperationException("UNKNOWN_COMPONENT_SCOPE_UNSUPPORTED");
            }

            Dictionary<string, string> localIdToUid;
            if (!ResolveWitnessBoneIds(manifestText, sourceFile, sourceBefore, sourceMetaBefore, out localIdToUid))
                throw new InvalidOperationException("WITNESS_UID_TO_BONE_MAPPING_UNAVAILABLE");
            report.source_model_unchanged = SameBytes(sourceBefore, ReadIfPresent(sourceFile)) &&
                SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta"));
            if (!report.source_model_unchanged) throw new InvalidOperationException("WITNESS_SOURCE_NOT_RESTORED");

            SkinnedMeshRenderer source = SingleSkin(AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath));
            SkinnedMeshRenderer edited = SingleSkin(AssetDatabase.LoadAssetAtPath<GameObject>(editedPath));
            prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (source == null || edited == null || source.sharedMesh == null || edited.sharedMesh == null)
                throw new InvalidOperationException("SKIN_MESH_MISSING");
            if (prefab == null) throw new InvalidOperationException("PREFAB_MISSING_AFTER_WITNESS_REIMPORT");
            prefabSkin = SingleSkin(prefab);
            if (prefabSkin == null || prefabSkin.sharedMesh == null ||
                !SameBounds(prefabSkin.localBounds, prefabLocalBounds))
                throw new InvalidOperationException("PREFAB_SKIN_RELOAD_OR_BOUNDS_CHANGED");
            Mesh sourceMesh = source.sharedMesh, finalMesh = edited.sharedMesh;
            report.source_vertex_count = sourceMesh.vertexCount;
            report.final_vertex_count = finalMesh.vertexCount;
            report.source_mesh_bounds_min = Vector3Values(sourceMesh.bounds.min);
            report.source_mesh_bounds_max = Vector3Values(sourceMesh.bounds.max);
            report.source_renderer_local_bounds_min = Vector3Values(source.localBounds.min);
            report.source_renderer_local_bounds_max = Vector3Values(source.localBounds.max);
            report.edited_renderer_local_bounds_min = Vector3Values(edited.localBounds.min);
            report.edited_renderer_local_bounds_max = Vector3Values(edited.localBounds.max);
            report.source_renderer_local_to_world = MatrixValues(source.transform.localToWorldMatrix);
            report.edited_renderer_local_to_world = MatrixValues(edited.transform.localToWorldMatrix);
            report.target_renderer_local_to_world = MatrixValues(prefabSkin.transform.localToWorldMatrix);
            report.target_root_bone_local_to_world = MatrixValues(prefabSkin.rootBone.localToWorldMatrix);
            report.target_renderer_world_bounds_min = Vector3Values(prefabSkin.bounds.min);
            report.target_renderer_world_bounds_max = Vector3Values(prefabSkin.bounds.max);
            try
            {
                RecordBakedBounds(source, out report.source_baked_bounds_min, out report.source_baked_bounds_max);
                RecordBakedBounds(edited, out report.edited_baked_bounds_min, out report.edited_baked_bounds_max);
                RecordBakedBounds(prefabSkin, out report.target_baked_bounds_min, out report.target_baked_bounds_max);
            }
            catch (Exception bakeError) { report.baked_bounds_error = bakeError.GetType().Name + ":" + bakeError.Message; }
            report.target_local_bounds_min = Vector3Values(prefabSkin.localBounds.min);
            report.target_local_bounds_max = Vector3Values(prefabSkin.localBounds.max);
            report.final_mesh_bounds_min = Vector3Values(finalMesh.bounds.min);
            report.final_mesh_bounds_max = Vector3Values(finalMesh.bounds.max);
            Vector3[] finalVerticesForBounds = finalMesh.vertices;
            if (finalVerticesForBounds.Length != 0)
            {
                Vector3 vertexMin = finalVerticesForBounds[0], vertexMax = finalVerticesForBounds[0];
                foreach (Vector3 vertex in finalVerticesForBounds)
                {
                    vertexMin = Vector3.Min(vertexMin, vertex);
                    vertexMax = Vector3.Max(vertexMax, vertex);
                }
                report.final_vertex_min = Vector3Values(vertexMin);
                report.final_vertex_max = Vector3Values(vertexMax);
            }
            report.final_vertex_attributes = String.Join("|", finalMesh.GetVertexAttributes().Select(a =>
                a.attribute + ":" + a.dimension + ":" + a.format));
            report.source_triangle_count = TriangleCount(sourceMesh);
            report.final_triangle_count = TriangleCount(finalMesh);
            report.source_index_count = IndexCount(sourceMesh);
            report.final_index_count = IndexCount(finalMesh);
            report.source_bone_count = source.bones == null ? 0 : source.bones.Length;
            report.final_bone_count = edited.bones == null ? 0 : edited.bones.Length;
            if (report.source_vertex_count != 4 || report.final_vertex_count != 6 ||
                report.source_triangle_count != 2 || report.final_triangle_count != 2 ||
                report.source_index_count != 6 || report.final_index_count != 6 ||
                report.source_bone_count != 2 || report.final_bone_count != 2)
                throw new InvalidOperationException("FIXTURE_LAYOUT_MISMATCH");
            report.source_and_final_meshes_have_one_submesh =
                sourceMesh.subMeshCount == 1 && finalMesh.subMeshCount == 1 &&
                source.sharedMaterials.Length == 1 && edited.sharedMaterials.Length == 1;
            report.source_and_final_shapes_empty =
                sourceMesh.blendShapeCount == 0 && finalMesh.blendShapeCount == 0;
            report.valid_source_and_final_weights = ValidWeights(sourceMesh, report.source_bone_count) &&
                ValidWeights(finalMesh, report.final_bone_count);
            report.source_and_final_geometric_faces_and_bone_weights_match =
                SameGeometricFacesAndBoneWeights(sourceMesh, source, task, localIdToUid, finalMesh, edited);
            report.final_uv_seam_proves_two_vertex_splits = HasTwoUvSplitPairs(sourceMesh, finalMesh);
            report.rest_bindpose_parity = MeasureRestBindposeParity(sourceMesh, source, prefab,
                task, localIdToUid, finalMesh, edited, report);
            if (!report.source_and_final_meshes_have_one_submesh ||
                !report.source_and_final_shapes_empty || !report.valid_source_and_final_weights ||
                !report.source_and_final_geometric_faces_and_bone_weights_match ||
                !report.final_uv_seam_proves_two_vertex_splits || !report.same_bone_uid_bijection ||
                !report.same_root_uid || !report.same_parent_uids || !report.rest_bindpose_parity)
                throw new InvalidOperationException("FIXTURE_SEMANTIC_PRECONDITION_FAILED");

            report.finalizer_applied = VapbModelSkinFinalizer.Apply(ManifestPath);
            AssetDatabase.ImportAsset(sourcePath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.ImportAsset(editedPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.ImportAsset(prefabPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            source = SingleSkin(AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath));
            edited = SingleSkin(AssetDatabase.LoadAssetAtPath<GameObject>(editedPath));
            prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            prefabSkin = SingleSkin(prefab);
            if (source == null || edited == null || prefabSkin == null || edited.sharedMesh == null)
                throw new InvalidOperationException("ASSET_RELOAD_AFTER_APPLY_FAILED");
            finalMesh = edited.sharedMesh;
            report.variant_created = report.finalizer_applied && Occupied(variantFile);
            GameObject variant = report.finalizer_applied ?
                AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path) : null;
            report.variant_is_source_prefab_child = variant != null &&
                PrefabUtility.GetPrefabAssetType(variant) == PrefabAssetType.Variant &&
                AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(variant)) == prefabPath;
            SkinnedMeshRenderer variantSkin = variant == null ? null : SkinForSource(variant, prefabSkin);
            report.variant_uses_exact_final_mesh = variantSkin != null &&
                SameAssetIdentity(variantSkin.sharedMesh, finalMesh);
            report.variant_bones_match_exported_uids = variantSkin != null &&
                SameVariantBones(variantSkin, edited, task, sourcePath, localIdToUid);
            Material[] expectedMaterials = ResolveExpectedMaterials(task, edited);
            report.variant_materials_match_transport = variantSkin != null && expectedMaterials != null &&
                variantSkin.sharedMaterials.SequenceEqual(expectedMaterials);
            float[] finalRootBoundsMin = null, finalRootBoundsMax = null, finalWorldBoundsMin = null, finalWorldBoundsMax = null;
            bool finalSkinBoundsContained = variantSkin != null && BoundsContainsImportedRestMesh(
                variantSkin, finalMesh, variantSkin.bones, 0.001f, out finalRootBoundsMin, out finalRootBoundsMax,
                out finalWorldBoundsMin, out finalWorldBoundsMax);
            report.variant_final_skin_bounds_contained = finalSkinBoundsContained;
            report.variant_renderer_world_bounds_min = variantSkin == null ? null : Vector3Values(variantSkin.bounds.min);
            report.variant_renderer_world_bounds_max = variantSkin == null ? null : Vector3Values(variantSkin.bounds.max);
            report.variant_final_skin_root_bounds_min = finalRootBoundsMin;
            report.variant_final_skin_root_bounds_max = finalRootBoundsMax;
            report.variant_final_skin_world_bounds_min = finalWorldBoundsMin;
            report.variant_final_skin_world_bounds_max = finalWorldBoundsMax;
            float[] bakedRootMin = null, bakedRootMax = null, bakedWorldMin = null, bakedWorldMax = null;
            report.variant_baked_skin_bounds_contained = variantSkin != null && BakedSkinWithinRootBounds(
                variantSkin, 0.001f, out bakedRootMin, out bakedRootMax, out bakedWorldMin, out bakedWorldMax,
                out report.baked_bounds_error);
            report.variant_baked_skin_root_bounds_min = bakedRootMin;
            report.variant_baked_skin_root_bounds_max = bakedRootMax;
            report.variant_baked_skin_world_bounds_min = bakedWorldMin;
            report.variant_baked_skin_world_bounds_max = bakedWorldMax;
            report.variant_baked_vs_skin_equation_bounds_delta = BoundsPairDelta(
                finalRootBoundsMin, finalRootBoundsMax, bakedRootMin, bakedRootMax);
            report.variant_baked_skin_bounds_contained &= report.variant_baked_vs_skin_equation_bounds_delta <= 0.001f;
            report.variant_renderer_state_preserved = variantSkin != null &&
                variantSkin.enabled == prefabSkin.enabled &&
                variantSkin.shadowCastingMode == prefabSkin.shadowCastingMode &&
                variantSkin.receiveShadows == prefabSkin.receiveShadows &&
                SameBounds(variantSkin.localBounds, prefabLocalBounds) &&
                variantSkin.sharedMesh != null && variantSkin.sharedMesh.blendShapeCount == 0 &&
                finalSkinBoundsContained && report.variant_baked_skin_bounds_contained;
            report.variant_structure_preserved = VariantStructurePreserved(variant, prefab, prefabSkin);
            report.prefab_guid_after = AssetDatabase.AssetPathToGUID(prefabPath);
            report.source_model_unchanged = SameBytes(sourceBefore, ReadIfPresent(sourceFile)) &&
                SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta"));
            report.edited_model_unchanged = SameBytes(editedBefore, ReadIfPresent(editedFile)) &&
                SameBytes(editedMetaBefore, ReadIfPresent(editedFile + ".meta"));
            report.prefab_unchanged = SameBytes(prefabBefore, ReadIfPresent(prefabFile)) &&
                SameBytes(prefabMetaBefore, ReadIfPresent(prefabFile + ".meta"));
            report.manifest_unchanged = SameBytes(manifestBefore, ReadIfPresent(manifestFile)) &&
                SameBytes(manifestMetaBefore, ReadIfPresent(manifestFile + ".meta"));
            bool firstApplyStable = report.finalizer_applied && report.variant_created &&
                report.variant_is_source_prefab_child && report.variant_uses_exact_final_mesh &&
                report.variant_bones_match_exported_uids && report.variant_materials_match_transport &&
                report.variant_renderer_state_preserved && report.variant_structure_preserved &&
                report.prefab_guid_before == report.prefab_guid_after && report.source_model_unchanged &&
                report.edited_model_unchanged && report.prefab_unchanged && report.manifest_unchanged;
            string variantHash = firstApplyStable ? Hash(variantFile) : null;
            string variantMetaHash = firstApplyStable ? Hash(variantFile + ".meta") : null;
            string variantGuid = firstApplyStable ? AssetDatabase.AssetPathToGUID(task.variant_path) : null;
            if (firstApplyStable)
            {
                bool repeated = VapbModelSkinFinalizer.Apply(ManifestPath);
                AssetDatabase.ImportAsset(sourcePath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.ImportAsset(editedPath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.ImportAsset(prefabPath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                AssetDatabase.ImportAsset(task.variant_path,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                GameObject repeatedVariant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
                edited = SingleSkin(AssetDatabase.LoadAssetAtPath<GameObject>(editedPath));
                prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                prefabSkin = SingleSkin(prefab);
                SkinnedMeshRenderer repeatedSkin = repeatedVariant == null || prefabSkin == null ? null :
                    SkinForSource(repeatedVariant, prefabSkin);
                bool repeatAssetState = SameBytes(sourceBefore, ReadIfPresent(sourceFile)) &&
                    SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta")) &&
                    SameBytes(editedBefore, ReadIfPresent(editedFile)) &&
                    SameBytes(editedMetaBefore, ReadIfPresent(editedFile + ".meta")) &&
                    SameBytes(prefabBefore, ReadIfPresent(prefabFile)) &&
                    SameBytes(prefabMetaBefore, ReadIfPresent(prefabFile + ".meta")) &&
                    SameBytes(manifestBefore, ReadIfPresent(manifestFile)) &&
                    SameBytes(manifestMetaBefore, ReadIfPresent(manifestFile + ".meta"));
                report.source_model_unchanged = SameBytes(sourceBefore, ReadIfPresent(sourceFile)) &&
                    SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta"));
                report.edited_model_unchanged = SameBytes(editedBefore, ReadIfPresent(editedFile)) &&
                    SameBytes(editedMetaBefore, ReadIfPresent(editedFile + ".meta"));
                report.prefab_unchanged = SameBytes(prefabBefore, ReadIfPresent(prefabFile)) &&
                    SameBytes(prefabMetaBefore, ReadIfPresent(prefabFile + ".meta"));
                report.manifest_unchanged = SameBytes(manifestBefore, ReadIfPresent(manifestFile)) &&
                    SameBytes(manifestMetaBefore, ReadIfPresent(manifestFile + ".meta"));
                Mesh repeatedFinalMesh = edited == null ? null : edited.sharedMesh;
                Material[] repeatedExpectedMaterials = edited == null ? null : ResolveExpectedMaterials(task, edited);
                report.variant_uses_exact_final_mesh = repeatedSkin != null && repeatedFinalMesh != null &&
                    SameAssetIdentity(repeatedSkin.sharedMesh, repeatedFinalMesh);
                report.variant_bones_match_exported_uids = repeatedSkin != null && edited != null &&
                    SameVariantBones(repeatedSkin, edited, task, sourcePath, localIdToUid);
                report.variant_materials_match_transport = repeatedSkin != null && repeatedExpectedMaterials != null &&
                    repeatedSkin.sharedMaterials.SequenceEqual(repeatedExpectedMaterials);
                float[] repeatedRootBoundsMin = null, repeatedRootBoundsMax = null, repeatedWorldBoundsMin = null, repeatedWorldBoundsMax = null;
                bool repeatedSkinBoundsContained = repeatedSkin != null && repeatedFinalMesh != null &&
                    BoundsContainsImportedRestMesh(repeatedSkin, repeatedFinalMesh, repeatedSkin.bones, 0.001f,
                        out repeatedRootBoundsMin, out repeatedRootBoundsMax, out repeatedWorldBoundsMin, out repeatedWorldBoundsMax);
                report.variant_final_skin_bounds_contained = repeatedSkinBoundsContained;
                report.variant_renderer_world_bounds_min = repeatedSkin == null ? null : Vector3Values(repeatedSkin.bounds.min);
                report.variant_renderer_world_bounds_max = repeatedSkin == null ? null : Vector3Values(repeatedSkin.bounds.max);
                report.variant_final_skin_root_bounds_min = repeatedRootBoundsMin;
                report.variant_final_skin_root_bounds_max = repeatedRootBoundsMax;
                report.variant_final_skin_world_bounds_min = repeatedWorldBoundsMin;
                report.variant_final_skin_world_bounds_max = repeatedWorldBoundsMax;
                float[] repeatedBakedRootMin = null, repeatedBakedRootMax = null;
                float[] repeatedBakedWorldMin = null, repeatedBakedWorldMax = null;
                string repeatedBakeError = null;
                bool repeatedBakeContained = repeatedSkin != null && BakedSkinWithinRootBounds(
                    repeatedSkin, 0.001f, out repeatedBakedRootMin, out repeatedBakedRootMax,
                    out repeatedBakedWorldMin, out repeatedBakedWorldMax, out repeatedBakeError);
                float repeatedBoundsDelta = BoundsPairDelta(repeatedRootBoundsMin, repeatedRootBoundsMax,
                    repeatedBakedRootMin, repeatedBakedRootMax);
                repeatedBakeContained &= repeatedBoundsDelta <= 0.001f;
                report.variant_baked_skin_bounds_contained &= repeatedBakeContained;
                report.variant_baked_vs_skin_equation_bounds_delta = Mathf.Max(
                    report.variant_baked_vs_skin_equation_bounds_delta, repeatedBoundsDelta);
                report.baked_bounds_error = String.IsNullOrEmpty(report.baked_bounds_error)
                    ? repeatedBakeError : report.baked_bounds_error;
                report.variant_renderer_state_preserved = repeatedSkin != null &&
                    repeatedSkin.enabled == prefabSkin.enabled &&
                    repeatedSkin.shadowCastingMode == prefabSkin.shadowCastingMode &&
                    repeatedSkin.receiveShadows == prefabSkin.receiveShadows &&
                    SameBounds(repeatedSkin.localBounds, prefabLocalBounds) && repeatedFinalMesh != null &&
                    repeatedFinalMesh.blendShapeCount == 0 &&
                    repeatedSkinBoundsContained && repeatedBakeContained;
                report.variant_structure_preserved = VariantStructurePreserved(repeatedVariant, prefab, prefabSkin);
                report.prefab_guid_after = AssetDatabase.AssetPathToGUID(prefabPath);
                report.variant_is_source_prefab_child = repeatedVariant != null &&
                    PrefabUtility.GetPrefabAssetType(repeatedVariant) == PrefabAssetType.Variant &&
                    AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(repeatedVariant)) == prefabPath;
                report.repeat_apply_idempotent = repeated && repeatedSkin != null &&
                    repeatedFinalMesh != null && SameAssetIdentity(repeatedSkin.sharedMesh, repeatedFinalMesh) &&
                    report.variant_is_source_prefab_child && report.variant_uses_exact_final_mesh &&
                    report.variant_bones_match_exported_uids && report.variant_materials_match_transport &&
                    report.variant_renderer_state_preserved && report.variant_structure_preserved &&
                    report.prefab_guid_before == report.prefab_guid_after && repeatAssetState &&
                    report.source_model_unchanged && report.edited_model_unchanged &&
                    report.prefab_unchanged && report.manifest_unchanged && Hash(variantFile) == variantHash &&
                    Hash(variantFile + ".meta") == variantMetaHash &&
                    AssetDatabase.AssetPathToGUID(task.variant_path) == variantGuid && appliedLogCount == 2;
            }
            report.bounds_tolerance_boundary_verified = BoundsToleranceBoundaryVerified();
            report.pass = firstApplyStable && report.repeat_apply_idempotent &&
                report.bounds_tolerance_boundary_verified;
            report.error = report.pass ? "NONE" : observedLog == null ? "GREEN_ASSERTION_FAILED" :
                observedLog.Substring("VAPB_MODEL_SKIN_VARIANT_REJECTED=".Length);
        }
        catch (Exception error) { report.pass = false; report.error = error.Message; }
        finally { Application.logMessageReceived -= capture; }
        try
        {
            byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true));
            using (var stream = new FileStream(resultFile, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                stream.Write(bytes, 0, bytes.Length);
        }
        catch { report.pass = false; report.error = "RESULT_WRITE_FAILED_OR_ALREADY_EXISTS"; }
        Debug.Log(report.pass ? "VAPB_MODEL_SKIN_TOPOLOGY_BOUNDARY_GREEN_PASS" :
            "VAPB_MODEL_SKIN_TOPOLOGY_BOUNDARY_GREEN_FAIL=" + report.error);
        EditorApplication.Exit(report.pass ? 0 : 1);
    }

    private static string ValidateOwnedProject(string target)
    {
        string rootValue = Environment.GetEnvironmentVariable("VAPB_STAGE3_TEST_ROOT");
        if (String.IsNullOrWhiteSpace(rootValue)) return "TEST_ROOT_ENV_MISSING";
        string root;
        try { root = Path.GetFullPath(rootValue); }
        catch { return "TEST_ROOT_INVALID"; }
        if (!String.Equals(target, Path.Combine(root, "TargetProject"), StringComparison.OrdinalIgnoreCase))
            return "TARGET_NOT_DIRECT_OWNED_CHILD";
        string source = Path.Combine(root, "SourceProject");
        if (!Directory.Exists(root) || Directory.Exists(Path.Combine(root, ".git")) ||
            File.Exists(Path.Combine(root, ".git"))) return "TEST_ROOT_IS_GIT_CHECKOUT";
        string current = root;
        while (!String.IsNullOrEmpty(current))
        {
            if (File.Exists(Path.Combine(current, ".git")) || Directory.Exists(Path.Combine(current, ".git")))
                return "TEST_ROOT_INSIDE_GIT_CHECKOUT";
            DirectoryInfo info = Directory.GetParent(current);
            current = info == null ? null : info.FullName;
        }
        string rootMarker = Path.Combine(root, RootMarker);
        string sourceMarker = Path.Combine(source, SourceMarker);
        string targetMarker = Path.Combine(target, TargetMarker);
        string manifestAsset = Path.Combine(target, "Assets", "VAPBExport", "manifest.json");
        try
        {
            if (HasReparseComponent(root) || HasReparseComponent(source) || HasReparseComponent(target) ||
                HasReparseComponent(rootMarker) || HasReparseComponent(sourceMarker) ||
                HasReparseComponent(targetMarker) || HasReparseComponent(Path.Combine(target, "Assets")) ||
                HasReparseComponent(manifestAsset) || HasReparseComponent(manifestAsset + ".meta"))
                return "OWNED_PATH_REPARSE_POINT";
        }
        catch { return "OWNED_PATH_CHECK_FAILED"; }
        if (!File.Exists(rootMarker) || !File.Exists(sourceMarker) ||
            !File.Exists(Path.Combine(target, TargetMarker))) return "OWNERSHIP_MARKER_MISSING";
        if (File.ReadAllText(rootMarker).Trim() != "VAPB_STAGE3_OWNED_TEST_ROOT_V1" ||
            File.ReadAllText(sourceMarker).Trim() != "VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1")
            return "OWNERSHIP_MARKER_INVALID";
        if (File.ReadAllText(targetMarker).Trim() != "VAPB_DISPOSABLE_UNITY_TEST_PROJECT_V1")
            return "TARGET_OWNERSHIP_MARKER_INVALID";
        string sourceVersion = Path.Combine(source, "ProjectSettings", "ProjectVersion.txt");
        string targetVersion = Path.Combine(target, "ProjectSettings", "ProjectVersion.txt");
        if (!File.Exists(sourceVersion) || !File.Exists(targetVersion) ||
            File.ReadAllText(sourceVersion).IndexOf("m_EditorVersion: 2022.3.22f1", StringComparison.Ordinal) < 0 ||
            File.ReadAllText(targetVersion).IndexOf("m_EditorVersion: 2022.3.22f1", StringComparison.Ordinal) < 0)
            return "UNITY_VERSION_MISMATCH";
        return null;
    }

    private static bool HasReparseComponent(string path)
    {
        string full = Path.GetFullPath(path);
        string volume = Path.GetPathRoot(full);
        string rest = full.Substring(volume.Length);
        string current = volume;
        foreach (string part in rest.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar))
        {
            if (String.IsNullOrEmpty(part)) continue;
            current = Path.Combine(current, part);
            if ((File.Exists(current) || Directory.Exists(current)) &&
                (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) return true;
        }
        return false;
    }

    private static SkinnedMeshRenderer SingleSkin(GameObject root)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] rows = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        return rows.Length == 1 ? rows[0] : null;
    }
    private static bool OwnedAssetPath(string path)
    {
        if (String.IsNullOrEmpty(path) || !path.StartsWith("Assets/", StringComparison.Ordinal) ||
            path.IndexOf('\\') >= 0 || path.IndexOf(':') >= 0 || Path.IsPathRooted(path)) return false;
        if (path.Split('/').Any(part => part == ".." || part == "." || part.Length == 0)) return false;
        string root = Path.GetFullPath(Application.dataPath) + Path.DirectorySeparatorChar;
        string resolved = Path.GetFullPath(Path.Combine(Application.dataPath, path.Substring(7)
            .Replace('/', Path.DirectorySeparatorChar)));
        return resolved.StartsWith(root, StringComparison.OrdinalIgnoreCase);
    }
    private static bool Occupied(string path)
    {
        return File.Exists(path) || Directory.Exists(path) || File.Exists(path + ".meta") ||
            Directory.Exists(path + ".meta");
    }
    private static bool Finite(Vector3 value)
    {
        return !Single.IsNaN(value.x) && !Single.IsInfinity(value.x) &&
            !Single.IsNaN(value.y) && !Single.IsInfinity(value.y) &&
            !Single.IsNaN(value.z) && !Single.IsInfinity(value.z);
    }
    private static bool SameBounds(Bounds left, Bounds right)
    {
        return left.center.Equals(right.center) && left.extents.Equals(right.extents);
    }
    private static bool SameAssetIdentity(UnityEngine.Object left, UnityEngine.Object right)
    {
        if (left == null || right == null) return false;
        string leftGuid, rightGuid; long leftId, rightId;
        return AssetDatabase.TryGetGUIDAndLocalFileIdentifier(left, out leftGuid, out leftId) &&
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(right, out rightGuid, out rightId) &&
            leftGuid == rightGuid && leftId == rightId;
    }
    private static SkinnedMeshRenderer SkinForSource(GameObject variant, SkinnedMeshRenderer source)
    {
        if (variant == null || source == null) return null;
        SkinnedMeshRenderer found = null;
        foreach (SkinnedMeshRenderer skin in variant.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (PrefabUtility.GetCorrespondingObjectFromSource(skin) != source) continue;
            if (found != null) return null;
            found = skin;
        }
        return found;
    }
    private static bool VariantStructurePreserved(GameObject variant, GameObject prefab,
        SkinnedMeshRenderer prefabSkin)
    {
        if (variant == null || prefab == null || prefabSkin == null ||
            PrefabUtility.GetAddedComponents(variant).Count != 0 ||
            PrefabUtility.GetRemovedComponents(variant).Count != 0 ||
            PrefabUtility.GetAddedGameObjects(variant).Count != 0 ||
            PrefabUtility.GetRemovedGameObjects(variant).Count != 0) return false;
        Transform[] actualTransforms = variant.GetComponentsInChildren<Transform>(true);
        if (actualTransforms.Length != prefab.GetComponentsInChildren<Transform>(true).Length) return false;
        foreach (Transform actual in actualTransforms)
        {
            Transform source = PrefabUtility.GetCorrespondingObjectFromSource(actual) as Transform;
            if (source == null || (actual != variant.transform && actual.name != source.name) ||
                actual.gameObject.activeSelf != source.gameObject.activeSelf ||
                actual.GetSiblingIndex() != source.GetSiblingIndex() || actual.childCount != source.childCount ||
                actual.localPosition != source.localPosition || actual.localRotation != source.localRotation ||
                actual.localScale != source.localScale) return false;
        }
        PropertyModification[] modifications = PrefabUtility.GetPropertyModifications(variant);
        if (modifications == null) return false;
        foreach (PropertyModification modification in modifications)
        {
            if (modification == null || modification.target == null ||
                String.IsNullOrEmpty(modification.propertyPath)) return false;
            bool skinBinding = modification.target == prefabSkin &&
                AllowedSkinOverridePath(modification.propertyPath);
            bool rootDefault = PrefabUtility.IsDefaultOverride(modification) &&
                (modification.target == prefab || modification.target == prefab.transform);
            if (!skinBinding && !rootDefault) return false;
        }
        return true;
    }
    private static bool AllowedSkinOverridePath(string path)
    {
        if (path == "m_Mesh" || path == "m_RootBone") return true;
        return path == "m_Bones.Array.size" || path == "m_Materials.Array.size" ||
            path.StartsWith("m_Bones.Array.data[", StringComparison.Ordinal) ||
            path.StartsWith("m_Materials.Array.data[", StringComparison.Ordinal);
    }
    private static bool SameVariantBones(SkinnedMeshRenderer actual, SkinnedMeshRenderer edited,
        Task task, string sourceModelPath, Dictionary<string, string> localIdToUid)
    {
        if (actual == null || edited == null || actual.bones == null || edited.bones == null ||
            actual.bones.Length != edited.bones.Length || task.bone_mappings == null) return false;
        var receiptToUid = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (BoneMapping mapping in task.bone_mappings)
        {
            if (mapping == null || String.IsNullOrEmpty(mapping.edited_bone_realization_id) ||
                String.IsNullOrEmpty(mapping.source_model_uid) ||
                receiptToUid.ContainsKey(mapping.edited_bone_realization_id)) return false;
            receiptToUid.Add(mapping.edited_bone_realization_id, mapping.source_model_uid);
        }
        string modelGuid = AssetDatabase.AssetPathToGUID(sourceModelPath);
        if (String.IsNullOrEmpty(modelGuid)) return false;
        for (int i = 0; i < actual.bones.Length; i++)
        {
            Transform bone = actual.bones[i];
            VapbRealizationMarker marker = edited.bones[i] == null ? null :
                edited.bones[i].GetComponent<VapbRealizationMarker>();
            string expected;
            if (bone == null || marker == null ||
                !receiptToUid.TryGetValue(marker.boneRealizationId, out expected) ||
                PrefabSourceUid(bone, modelGuid, localIdToUid) != expected) return false;
        }
        Transform actualRoot = actual.rootBone;
        Transform expectedRoot = edited.rootBone;
        VapbRealizationMarker rootMarker = expectedRoot == null ? null :
            expectedRoot.GetComponent<VapbRealizationMarker>();
        string expectedRootUid;
        return actualRoot != null && rootMarker != null &&
            receiptToUid.TryGetValue(rootMarker.boneRealizationId, out expectedRootUid) &&
            PrefabSourceUid(actualRoot, modelGuid, localIdToUid) == expectedRootUid;
    }
    private static Material[] ResolveExpectedMaterials(Task task, SkinnedMeshRenderer edited)
    {
        if (task == null || edited == null || task.material_bindings == null ||
            task.material_bindings.Length != edited.sharedMaterials.Length) return null;
        var byTransportId = new Dictionary<string, Material>(StringComparer.Ordinal);
        foreach (MaterialBinding binding in task.material_bindings)
        {
            if (binding == null || String.IsNullOrEmpty(binding.transport_id) ||
                String.IsNullOrEmpty(binding.guid) || String.IsNullOrEmpty(binding.file_id) ||
                byTransportId.ContainsKey(binding.transport_id)) return null;
            string path = AssetDatabase.GUIDToAssetPath(binding.guid);
            if (String.IsNullOrEmpty(path)) return null;
            Material match = null;
            foreach (Material candidate in AssetDatabase.LoadAllAssetsAtPath(path).OfType<Material>())
            {
                string guid; long localId;
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(candidate, out guid, out localId) ||
                    guid != binding.guid || localId.ToString(CultureInfo.InvariantCulture) != binding.file_id) continue;
                if (match != null) return null;
                match = candidate;
            }
            if (match == null) return null;
            byTransportId.Add(binding.transport_id, match);
        }
        var ordered = new Material[edited.sharedMaterials.Length];
        for (int i = 0; i < ordered.Length; i++)
        {
            Material carrier = edited.sharedMaterials[i];
            Material expected;
            if (carrier == null || !byTransportId.TryGetValue(carrier.name, out expected)) return null;
            ordered[i] = expected;
        }
        return ordered;
    }
    private static bool BoundsContainsImportedRestMesh(SkinnedMeshRenderer target, Mesh mesh, Transform[] bones,
        float tolerance, out float[] rootMinimum, out float[] rootMaximum,
        out float[] worldMinimum, out float[] worldMaximum)
    {
        rootMinimum = rootMaximum = worldMinimum = worldMaximum = null;
        if (target == null || target.rootBone == null || mesh == null || bones == null ||
            bones.Length == 0 || !Finite(target.localBounds.center) || !Finite(target.localBounds.extents) ||
            target.localBounds.extents.x < 0f || target.localBounds.extents.y < 0f || target.localBounds.extents.z < 0f ||
            tolerance < 0f) return false;
        Bounds bounds = target.localBounds;
        Matrix4x4 rootWorldToLocal = target.rootBone.worldToLocalMatrix;
        Matrix4x4 rootLocalToWorld = target.rootBone.localToWorldMatrix;
        if (MatrixDelta(rootWorldToLocal * rootLocalToWorld, Matrix4x4.identity) > 0.001f) return false;
        Matrix4x4[] bindposes = mesh.bindposes;
        if (bindposes == null || bindposes.Length != bones.Length) return false;
        var rootSkinByBone = new Matrix4x4[bones.Length];
        for (int bone = 0; bone < bones.Length; bone++)
        {
            if (bones[bone] == null) return false;
            rootSkinByBone[bone] = rootWorldToLocal * bones[bone].localToWorldMatrix * bindposes[bone];
        }
        for (int matrixIndex = 0; matrixIndex < 16; matrixIndex++)
            if (Single.IsNaN(rootWorldToLocal[matrixIndex]) || Single.IsInfinity(rootWorldToLocal[matrixIndex])) return false;
        Vector3[] vertices = mesh.vertices;
        if (vertices == null || vertices.Length == 0) return false;
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        Vector3 rootLow = Vector3.zero, rootHigh = Vector3.zero, worldLow = Vector3.zero, worldHigh = Vector3.zero;
        try
        {
            if (counts.Length != vertices.Length) return false;
            int weightIndex = 0;
            for (int vertex = 0; vertex < vertices.Length; vertex++)
            {
                int count = counts[vertex];
                if (count <= 0 || weightIndex + count > weights.Length || !Finite(vertices[vertex])) return false;
                Vector3 world = Vector3.zero;
                Vector3 rootLocal = Vector3.zero;
                float totalWeight = 0f;
                for (int influence = 0; influence < count; influence++)
                {
                    BoneWeight1 weight = weights[weightIndex++];
                    if (weight.boneIndex < 0 || weight.boneIndex >= bones.Length || bones[weight.boneIndex] == null ||
                        !Finite(weight.weight) || weight.weight <= 0f) return false;
                    Matrix4x4 bindpose = bindposes[weight.boneIndex];
                    Vector3 bindPoint = bindpose.MultiplyPoint3x4(vertices[vertex]);
                    Vector3 worldPoint = bones[weight.boneIndex].localToWorldMatrix.MultiplyPoint3x4(bindPoint);
                    Vector3 rootInfluence = rootSkinByBone[weight.boneIndex].MultiplyPoint3x4(vertices[vertex]);
                    if (!Finite(bindPoint) || !Finite(worldPoint) || !Finite(rootInfluence)) return false;
                    world += worldPoint * weight.weight;
                    rootLocal += rootInfluence * weight.weight;
                    totalWeight += weight.weight;
                }
                if (!Finite(world) || !Finite(rootLocal) || Mathf.Abs(totalWeight - 1f) > 0.01f) return false;
                if (!Finite(rootLocal) || !WithinBounds(rootLocal, bounds, tolerance)) return false;
                if (vertex == 0) { rootLow = rootHigh = rootLocal; worldLow = worldHigh = world; }
                else { rootLow = Vector3.Min(rootLow, rootLocal); rootHigh = Vector3.Max(rootHigh, rootLocal); worldLow = Vector3.Min(worldLow, world); worldHigh = Vector3.Max(worldHigh, world); }
            }
            if (weightIndex != weights.Length) return false;
            rootMinimum = Vector3Values(rootLow); rootMaximum = Vector3Values(rootHigh);
            worldMinimum = Vector3Values(worldLow); worldMaximum = Vector3Values(worldHigh);
            return true;
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }
    private static bool WithinBounds(Vector3 point, Bounds bounds, float tolerance)
    {
        return point.x >= bounds.min.x - tolerance && point.x <= bounds.max.x + tolerance &&
            point.y >= bounds.min.y - tolerance && point.y <= bounds.max.y + tolerance &&
            point.z >= bounds.min.z - tolerance && point.z <= bounds.max.z + tolerance;
    }
    private static bool BoundsToleranceBoundaryVerified()
    {
        var bounds = new Bounds(Vector3.zero, Vector3.one * 2f);
        return WithinBounds(new Vector3(1f, 0f, 0f), bounds, 0.001f) &&
            WithinBounds(new Vector3(1.0005f, 0f, 0f), bounds, 0.001f) &&
            !WithinBounds(new Vector3(1.0015f, 0f, 0f), bounds, 0.001f);
    }
    private static int TriangleCount(Mesh mesh)
    {
        if (mesh.subMeshCount != 1 || mesh.GetTopology(0) != MeshTopology.Triangles) return -1;
        return (int)(mesh.GetIndexCount(0) / 3);
    }
    private static int IndexCount(Mesh mesh)
    { return mesh.subMeshCount == 1 ? (int)mesh.GetIndexCount(0) : -1; }
    private static bool ValidWeights(Mesh mesh, int boneCount)
    {
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            if (counts.Length != mesh.vertexCount) return false;
            int offset = 0;
            for (int vertex = 0; vertex < counts.Length; vertex++)
            {
                if (counts[vertex] == 0 || offset + counts[vertex] > weights.Length) return false;
                float sum = 0f;
                for (int i = 0; i < counts[vertex]; i++)
                {
                    var weight = weights[offset++];
                    if (weight.boneIndex < 0 || weight.boneIndex >= boneCount ||
                        Single.IsNaN(weight.weight) || Single.IsInfinity(weight.weight) || weight.weight <= 0f)
                        return false;
                    sum += weight.weight;
                }
                if (Math.Abs(sum - 1f) > 0.0001f) return false;
            }
            return offset == weights.Length;
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }
    private static bool SameGeometricFacesAndBoneWeights(Mesh sourceMesh, SkinnedMeshRenderer sourceSkin,
        Task task, Dictionary<string, string> localIdToUid, Mesh finalMesh, SkinnedMeshRenderer finalSkin)
    {
        var sourceIds = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i < sourceSkin.bones.Length; i++)
        {
            string guid; long localId;
            if (sourceSkin.bones[i] == null ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sourceSkin.bones[i], out guid, out localId) ||
                !String.Equals(guid, task.source_model_guid, StringComparison.Ordinal)) return false;
            string uid;
            if (!localIdToUid.TryGetValue(localId.ToString(CultureInfo.InvariantCulture), out uid)) return false;
            sourceIds.Add(i.ToString(CultureInfo.InvariantCulture), uid);
        }
        if (task.bone_mappings == null || task.bone_mappings.Length != finalSkin.bones.Length) return false;
        var receiptToUid = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (BoneMapping mapping in task.bone_mappings)
        {
            if (mapping == null || String.IsNullOrEmpty(mapping.edited_bone_realization_id) ||
                String.IsNullOrEmpty(mapping.source_model_uid) ||
                receiptToUid.ContainsKey(mapping.edited_bone_realization_id)) return false;
            receiptToUid.Add(mapping.edited_bone_realization_id, mapping.source_model_uid);
        }
        var finalIds = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i < finalSkin.bones.Length; i++)
        {
            Transform bone = finalSkin.bones[i];
            VapbRealizationMarker marker = bone == null ? null : bone.GetComponent<VapbRealizationMarker>();
            string uid;
            if (marker == null || !receiptToUid.TryGetValue(marker.boneRealizationId, out uid)) return false;
            finalIds.Add(i.ToString(CultureInfo.InvariantCulture), uid);
        }
        string[] sourceRows, finalRows;
        if (!SemanticWeightRows(sourceMesh, sourceIds, out sourceRows) ||
            !SemanticWeightRows(finalMesh, finalIds, out finalRows)) return false;
        return FaceRows(sourceMesh, sourceRows).SequenceEqual(FaceRows(finalMesh, finalRows));
    }

    private static bool MeasureRestBindposeParity(Mesh sourceMesh, SkinnedMeshRenderer sourceSkin,
        GameObject prefabRoot, Task task, Dictionary<string, string> localIdToUid,
        Mesh finalMesh, SkinnedMeshRenderer finalSkin, Report report)
    {
        report.same_bone_uid_bijection = false;
        report.same_root_uid = false;
        report.same_parent_uids = false;
        report.bone_rest_rows = new BoneRestRow[0];
        if (sourceSkin.bones == null || finalSkin.bones == null || sourceSkin.bones.Length != 2 ||
            finalSkin.bones.Length != 2 || sourceMesh.bindposes.Length != sourceSkin.bones.Length ||
            finalMesh.bindposes.Length != finalSkin.bones.Length || task.bone_mappings == null ||
            task.bone_mappings.Length != finalSkin.bones.Length) return false;
        SkinnedMeshRenderer prefabSkin = SingleSkin(prefabRoot);
        if (prefabSkin == null || prefabSkin.bones == null || prefabSkin.bones.Length != sourceSkin.bones.Length ||
            prefabSkin.rootBone == null || sourceSkin.rootBone == null || finalSkin.rootBone == null) return false;

        var receiptToUid = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (BoneMapping mapping in task.bone_mappings)
        {
            if (mapping == null || String.IsNullOrEmpty(mapping.edited_bone_realization_id) ||
                String.IsNullOrEmpty(mapping.source_model_uid) || receiptToUid.ContainsKey(mapping.edited_bone_realization_id))
                return false;
            receiptToUid.Add(mapping.edited_bone_realization_id, mapping.source_model_uid);
        }
        var sourceSlots = new Dictionary<string, int>(StringComparer.Ordinal);
        var finalSlots = new Dictionary<string, int>(StringComparer.Ordinal);
        var sourceBoneTransforms = new Dictionary<string, Transform>(StringComparer.Ordinal);
        var prefabBones = new Dictionary<string, Transform>(StringComparer.Ordinal);
        for (int i = 0; i < sourceSkin.bones.Length; i++)
        {
            string uid = SourceAssetUid(sourceSkin.bones[i], task.source_model_guid, localIdToUid);
            if (uid == null || sourceSlots.ContainsKey(uid)) return false;
            sourceSlots.Add(uid, i);
            sourceBoneTransforms.Add(uid, sourceSkin.bones[i]);
        }
        foreach (Transform prefabBone in prefabSkin.bones)
        {
            string uid = PrefabSourceUid(prefabBone, task.source_model_guid, localIdToUid);
            if (uid == null || prefabBones.ContainsKey(uid)) return false;
            prefabBones.Add(uid, prefabBone);
        }
        for (int i = 0; i < finalSkin.bones.Length; i++)
        {
            Transform bone = finalSkin.bones[i];
            VapbRealizationMarker marker = bone == null ? null : bone.GetComponent<VapbRealizationMarker>();
            string uid;
            if (marker == null || !receiptToUid.TryGetValue(marker.boneRealizationId, out uid) ||
                finalSlots.ContainsKey(uid)) return false;
            finalSlots.Add(uid, i);
        }
        var sourceUids = new HashSet<string>(sourceSlots.Keys, StringComparer.Ordinal);
        report.same_bone_uid_bijection = sourceSlots.Count == 2 && finalSlots.Count == 2 &&
            prefabBones.Count == 2 && sourceUids.SetEquals(finalSlots.Keys) && sourceUids.SetEquals(prefabBones.Keys);
        if (!report.same_bone_uid_bijection) return false;

        string sourceRootUid = SourceAssetUid(sourceSkin.rootBone, task.source_model_guid, localIdToUid);
        string prefabRootUid = PrefabSourceUid(prefabSkin.rootBone, task.source_model_guid, localIdToUid);
        Transform finalRoot = finalSkin.rootBone;
        VapbRealizationMarker finalRootMarker = finalRoot.GetComponent<VapbRealizationMarker>();
        string finalRootUid = null;
        if (finalRootMarker != null) receiptToUid.TryGetValue(finalRootMarker.boneRealizationId, out finalRootUid);
        report.same_root_uid = sourceRootUid != null && sourceRootUid == prefabRootUid &&
            sourceRootUid == finalRootUid;

        var sourceParentByUid = new Dictionary<string, string>(StringComparer.Ordinal);
        var prefabParentByUid = new Dictionary<string, string>(StringComparer.Ordinal);
        var finalParentByUid = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (KeyValuePair<string, int> row in sourceSlots)
        {
            string uid = row.Key;
            int sourceSlot = row.Value, finalSlot = finalSlots[uid];
            Transform sourceBone = sourceSkin.bones[sourceSlot];
            Transform finalBone = finalSkin.bones[finalSlot];
            Transform prefabBone = prefabBones[uid];
            sourceParentByUid.Add(uid, MappedParentUid(sourceBone.parent, sourceBoneTransforms));
            prefabParentByUid.Add(uid, MappedPrefabParentUid(prefabBone.parent,
                task.source_model_guid, localIdToUid, sourceSlots));
            finalParentByUid.Add(uid, MappedFinalParentUid(finalBone.parent, receiptToUid));

            Matrix4x4 expected = prefabBone.worldToLocalMatrix * prefabSkin.transform.localToWorldMatrix;
            Matrix4x4 sourceBindpose = sourceMesh.bindposes[sourceSlot];
            Matrix4x4 finalBindpose = finalMesh.bindposes[finalSlot];
            Matrix4x4 finalRest = finalBone.worldToLocalMatrix * finalSkin.transform.localToWorldMatrix;
            var rest = new BoneRestRow {
                source_model_uid = uid, source_slot = sourceSlot, final_slot = finalSlot,
                source_parent_uid = sourceParentByUid[uid], prefab_parent_uid = prefabParentByUid[uid],
                final_parent_uid = finalParentByUid[uid], expected = MatrixValues(expected),
                source_bindpose = MatrixValues(sourceBindpose), final_bindpose = MatrixValues(finalBindpose),
                final_rest = MatrixValues(finalRest),
                source_bindpose_max_error = MatrixDelta(sourceBindpose, expected),
                final_bindpose_max_error = MatrixDelta(finalBindpose, expected),
                final_rest_max_error = MatrixDelta(finalRest, expected)
            };
            if (report.bone_rest_rows == null) report.bone_rest_rows = new BoneRestRow[0];
            report.bone_rest_rows = report.bone_rest_rows.Concat(new[] { rest }).ToArray();
        }
        report.same_parent_uids = sourceParentByUid.Count == 2 && prefabParentByUid.Count == 2 &&
            finalParentByUid.Count == 2 && sourceParentByUid.All(row => prefabParentByUid[row.Key] == row.Value &&
                finalParentByUid[row.Key] == row.Value);
        return report.same_bone_uid_bijection && report.same_root_uid && report.same_parent_uids &&
            report.bone_rest_rows.Length == 2 && report.bone_rest_rows.All(row =>
                row.source_bindpose_max_error <= 0.001f && row.final_bindpose_max_error <= 0.001f &&
                row.final_rest_max_error <= 0.001f);
    }

    private static string SourceAssetUid(Transform transform, string modelGuid,
        Dictionary<string, string> localIdToUid)
    {
        string guid; long localId; string uid;
        return transform != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(transform, out guid, out localId) &&
            guid == modelGuid && localIdToUid.TryGetValue(localId.ToString(CultureInfo.InvariantCulture), out uid)
            ? uid : null;
    }
    private static string PrefabSourceUid(Transform transform, string modelGuid,
        Dictionary<string, string> localIdToUid)
    {
        Transform current = transform;
        for (int depth = 0; depth < 16 && current != null; depth++)
        {
            string guid; long localId; string uid;
            if (AssetDatabase.TryGetGUIDAndLocalFileIdentifier(current, out guid, out localId) && guid == modelGuid &&
                localIdToUid.TryGetValue(localId.ToString(CultureInfo.InvariantCulture), out uid)) return uid;
            Transform next = PrefabUtility.GetCorrespondingObjectFromSource(current) as Transform;
            if (next == null || next == current) break;
            current = next;
        }
        return null;
    }
    private static string MappedParentUid(Transform parent, Dictionary<string, Transform> boneTransforms)
    {
        if (parent == null) return "<NO_PARENT>";
        foreach (KeyValuePair<string, Transform> row in boneTransforms)
            if (parent == row.Value) return row.Key;
        return "<NON_SKIN_BONE_PARENT>";
    }
    private static string MappedPrefabParentUid(Transform parent, string modelGuid,
        Dictionary<string, string> localIdToUid, Dictionary<string, int> boneSlots)
    {
        if (parent == null) return "<NO_PARENT>";
        string uid = PrefabSourceUid(parent, modelGuid, localIdToUid);
        return uid != null && boneSlots.ContainsKey(uid) ? uid : "<NON_SKIN_BONE_PARENT>";
    }
    private static string MappedFinalParentUid(Transform parent, Dictionary<string, string> receiptToUid)
    {
        if (parent == null) return "<NO_PARENT>";
        VapbRealizationMarker marker = parent.GetComponent<VapbRealizationMarker>();
        string uid;
        return marker != null && receiptToUid.TryGetValue(marker.boneRealizationId, out uid)
            ? uid : "<NON_SKIN_BONE_PARENT>";
    }
    private static void RecordBakedBounds(SkinnedMeshRenderer renderer, out float[] minimum, out float[] maximum)
    {
        Mesh baked = new Mesh { hideFlags = HideFlags.HideAndDontSave };
        try
        {
            renderer.BakeMesh(baked);
            Vector3[] vertices = baked.vertices;
            if (vertices == null || vertices.Length == 0) throw new InvalidOperationException("BAKED_MESH_EMPTY");
            Vector3 low = vertices[0], high = vertices[0];
            foreach (Vector3 vertex in vertices) { low = Vector3.Min(low, vertex); high = Vector3.Max(high, vertex); }
            minimum = Vector3Values(low); maximum = Vector3Values(high);
        }
        finally { UnityEngine.Object.DestroyImmediate(baked); }
    }
    private static bool BakedSkinWithinRootBounds(SkinnedMeshRenderer renderer, float tolerance,
        out float[] rootMinimum, out float[] rootMaximum, out float[] worldMinimum, out float[] worldMaximum,
        out string error)
    {
        rootMinimum = rootMaximum = worldMinimum = worldMaximum = null;
        error = null;
        if (renderer == null || renderer.rootBone == null || tolerance < 0f) return false;
        Mesh baked = new Mesh { hideFlags = HideFlags.HideAndDontSave };
        try
        {
            // Unity's own skinning path is the independent oracle. BakeMesh(useScale:true) returns
            // the deformed vertices; transform them through the renderer frame, then into rootBone.
            renderer.BakeMesh(baked, true);
            Vector3[] vertices = baked.vertices;
            if (vertices == null || vertices.Length == 0) return false;
            Matrix4x4 rendererLocalToWorld = renderer.transform.localToWorldMatrix;
            Matrix4x4 rootWorldToLocal = renderer.rootBone.worldToLocalMatrix;
            Vector3 rootLow = Vector3.zero, rootHigh = Vector3.zero;
            Vector3 worldLow = Vector3.zero, worldHigh = Vector3.zero;
            for (int i = 0; i < vertices.Length; i++)
            {
                if (!Finite(vertices[i])) return false;
                Vector3 world = rendererLocalToWorld.MultiplyPoint3x4(vertices[i]);
                Vector3 root = rootWorldToLocal.MultiplyPoint3x4(world);
                if (!Finite(world) || !Finite(root)) return false;
                if (i == 0) { rootLow = rootHigh = root; worldLow = worldHigh = world; }
                else
                {
                    rootLow = Vector3.Min(rootLow, root); rootHigh = Vector3.Max(rootHigh, root);
                    worldLow = Vector3.Min(worldLow, world); worldHigh = Vector3.Max(worldHigh, world);
                }
                Bounds bounds = renderer.localBounds;
                if (root.x < bounds.min.x - tolerance || root.x > bounds.max.x + tolerance ||
                    root.y < bounds.min.y - tolerance || root.y > bounds.max.y + tolerance ||
                    root.z < bounds.min.z - tolerance || root.z > bounds.max.z + tolerance) return false;
            }
            rootMinimum = Vector3Values(rootLow); rootMaximum = Vector3Values(rootHigh);
            worldMinimum = Vector3Values(worldLow); worldMaximum = Vector3Values(worldHigh);
            return true;
        }
        catch (Exception bakeError)
        {
            error = bakeError.GetType().Name + ":" + bakeError.Message;
            return false;
        }
        finally { UnityEngine.Object.DestroyImmediate(baked); }
    }
    private static float BoundsPairDelta(float[] leftMin, float[] leftMax, float[] rightMin, float[] rightMax)
    {
        if (leftMin == null || leftMax == null || rightMin == null || rightMax == null ||
            leftMin.Length != 3 || leftMax.Length != 3 || rightMin.Length != 3 || rightMax.Length != 3)
            return Single.PositiveInfinity;
        float maximum = 0f;
        for (int axis = 0; axis < 3; axis++)
        {
            maximum = Mathf.Max(maximum, Mathf.Abs(leftMin[axis] - rightMin[axis]));
            maximum = Mathf.Max(maximum, Mathf.Abs(leftMax[axis] - rightMax[axis]));
        }
        return maximum;
    }
    private static float[] Vector3Values(Vector3 value) { return new[] { value.x, value.y, value.z }; }
    private static float[] MatrixValues(Matrix4x4 matrix)
    {
        var result = new float[16];
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++) result[row * 4 + column] = matrix[row, column];
        return result;
    }
    private static float MatrixDelta(Matrix4x4 left, Matrix4x4 right)
    {
        float max = 0f;
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++)
            {
                float a = left[row, column], b = right[row, column];
                if (Single.IsNaN(a) || Single.IsInfinity(a) || Single.IsNaN(b) || Single.IsInfinity(b))
                    return Single.MaxValue;
                max = Math.Max(max, Math.Abs(a - b));
            }
        return max;
    }

    private static bool ResolveWitnessBoneIds(string manifestText, string sourceFile,
        byte[] sourceBefore, byte[] sourceMetaBefore, out Dictionary<string, string> localIdToUid)
    {
        localIdToUid = new Dictionary<string, string>(StringComparer.Ordinal);
        Type finalizer = typeof(VapbModelSkinFinalizer);
        Type manifestType = finalizer.GetNestedType("Manifest", BindingFlags.NonPublic);
        Type taskType = finalizer.GetNestedType("Task", BindingFlags.NonPublic);
        MethodInfo validate = finalizer.GetMethod("ValidateTask", BindingFlags.NonPublic | BindingFlags.Static);
        MethodInfo prepare = finalizer.GetMethod("PrepareWitness", BindingFlags.NonPublic | BindingFlags.Static);
        if (manifestType == null || taskType == null || validate == null || prepare == null) return false;
        object internalManifest = JsonUtility.FromJson(manifestText, manifestType);
        FieldInfo tasksField = internalManifest == null ? null : internalManifest.GetType().GetField(
            "reference_rebind_tasks", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        Array internalTasks = tasksField == null ? null : tasksField.GetValue(internalManifest) as Array;
        if (internalTasks == null || internalTasks.Length != 1 || internalTasks.GetValue(0) == null ||
            internalTasks.GetValue(0).GetType() != taskType) return false;
        object internalTask = internalTasks.GetValue(0);
        validate.Invoke(null, new[] { internalTask });
        object prepared;
        try { prepared = prepare.Invoke(null, new[] { internalTask }); }
        catch
        {
            if (!SameBytes(sourceBefore, ReadIfPresent(sourceFile)) ||
                !SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta")))
                throw new InvalidOperationException("WITNESS_SOURCE_RESTORE_FAILED");
            return false;
        }
        if (!SameBytes(sourceBefore, ReadIfPresent(sourceFile)) ||
            !SameBytes(sourceMetaBefore, ReadIfPresent(sourceFile + ".meta"))) return false;
        if (prepared == null) return false;
        FieldInfo witnessField = prepared.GetType().GetField("witness", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        object witness = witnessField == null ? null : witnessField.GetValue(prepared);
        FieldInfo transformIdsField = witness == null ? null : witness.GetType().GetField("transformIds",
            BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        var transformIds = transformIdsField == null ? null : transformIdsField.GetValue(witness) as Dictionary<string, long>;
        FieldInfo sourceUidsField = taskType.GetField("source_model_uids",
            BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        string[] sourceUids = sourceUidsField == null ? null : sourceUidsField.GetValue(internalTask) as string[];
        if (transformIds == null || sourceUids == null || transformIds.Count != sourceUids.Length)
            return false;
        foreach (KeyValuePair<string, long> row in transformIds)
            localIdToUid.Add(row.Value.ToString(CultureInfo.InvariantCulture), row.Key);
        return localIdToUid.Count == transformIds.Count;
    }

    private static bool SemanticWeightRows(Mesh mesh, Dictionary<string, string> indexToUid,
        out string[] rows)
    {
        rows = null;
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            if (counts.Length != mesh.vertexCount) return false;
            rows = new string[mesh.vertexCount];
            int offset = 0;
            for (int vertex = 0; vertex < counts.Length; vertex++)
            {
                var byUid = new SortedDictionary<string, float>(StringComparer.Ordinal);
                for (int i = 0; i < counts[vertex]; i++)
                {
                    var influence = weights[offset++];
                    string uid;
                    if (!indexToUid.TryGetValue(influence.boneIndex.ToString(CultureInfo.InvariantCulture), out uid) ||
                        byUid.ContainsKey(uid)) return false;
                    byUid.Add(uid, influence.weight);
                }
                rows[vertex] = String.Join(",", byUid.Select(row => row.Key + "=" + Quantize(row.Value)));
            }
            return offset == weights.Length;
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }

    private static string[] FaceRows(Mesh mesh, string[] weightRows)
    {
        Vector3[] vertices = mesh.vertices;
        int[] indices = mesh.GetTriangles(0);
        if (indices.Length % 3 != 0) return new string[0];
        var faces = new List<string>();
        for (int i = 0; i < indices.Length; i += 3)
        {
            string[] corners = new string[3];
            for (int c = 0; c < 3; c++)
            {
                int index = indices[i + c];
                corners[c] = Quantize(vertices[index].x) + ":" + Quantize(vertices[index].y) + ":" +
                    Quantize(vertices[index].z) + "[" + weightRows[index] + "]";
            }
            Array.Sort(corners, StringComparer.Ordinal);
            faces.Add(String.Join("|", corners));
        }
        faces.Sort(StringComparer.Ordinal);
        return faces.ToArray();
    }

    private static bool HasTwoUvSplitPairs(Mesh sourceMesh, Mesh mesh)
    {
        Vector3[] vertices = mesh.vertices;
        Vector2[] uv = mesh.uv;
        Vector3[] sourceVertices = sourceMesh.vertices;
        Vector2[] sourceUv = sourceMesh.uv;
        if (vertices.Length != 6 || uv.Length != 6 || sourceVertices.Length != 4 || sourceUv.Length != 4)
            return false;
        int[] sourceIndices = sourceMesh.GetTriangles(0);
        int[] finalIndices = mesh.GetTriangles(0);
        if (sourceIndices.Length != 6 || finalIndices.Length != 6) return false;
        var sourceFirst = new HashSet<int>(sourceIndices.Take(3));
        var sourceShared = new HashSet<int>(sourceIndices.Skip(3).Take(3).Where(sourceFirst.Contains));
        if (sourceShared.Count != 2) return false;
        var expectedPairPositions = new HashSet<string>(sourceShared.Select(index => {
            Vector3 v = sourceVertices[index];
            return Quantize(v.x) + ":" + Quantize(v.y) + ":" + Quantize(v.z);
        }), StringComparer.Ordinal);
        var groups = new Dictionary<string, List<int>>(StringComparer.Ordinal);
        for (int i = 0; i < vertices.Length; i++)
        {
            string key = Quantize(vertices[i].x) + ":" + Quantize(vertices[i].y) + ":" + Quantize(vertices[i].z);
            if (!groups.ContainsKey(key)) groups.Add(key, new List<int>());
            groups[key].Add(i);
        }
        List<int>[] pairs = groups.Values.Where(group => group.Count == 2).ToArray();
        if (pairs.Length != 2 || groups.Values.Any(group => group.Count > 2) ||
            !new HashSet<string>(groups.Where(row => row.Value.Count == 2).Select(row => row.Key), StringComparer.Ordinal)
                .SetEquals(expectedPairPositions)) return false;
        var used = new HashSet<int>(finalIndices);
        if (used.Count != mesh.vertexCount) return false;
        int shiftedSharedCorners = 0;
        foreach (List<int> pair in pairs)
        {
            int faceA = Array.IndexOf(finalIndices, pair[0]) / 3;
            int faceB = Array.IndexOf(finalIndices, pair[1]) / 3;
            if (faceA == faceB) return false;
            Vector2 a = uv[pair[0]], b = uv[pair[1]];
            string key = Quantize(vertices[pair[0]].x) + ":" + Quantize(vertices[pair[0]].y) + ":" +
                Quantize(vertices[pair[0]].z);
            int sourceIndex = Array.FindIndex(sourceVertices, v =>
                Quantize(v.x) + ":" + Quantize(v.y) + ":" + Quantize(v.z) == key);
            if (sourceIndex < 0) return false;
            Vector2 baseUv = sourceUv[sourceIndex];
            bool aIsBase = NearUv(a, baseUv), bIsBase = NearUv(b, baseUv);
            bool aIsShifted = NearUv(a, new Vector2(baseUv.x + 0.25f, baseUv.y));
            bool bIsShifted = NearUv(b, new Vector2(baseUv.x + 0.25f, baseUv.y));
            if (!((aIsBase && bIsShifted) || (bIsBase && aIsShifted)))
                return false;
            shiftedSharedCorners++;
        }
        int shiftedFaces = 0;
        for (int face = 0; face < 2; face++)
        {
            int faceShifted = 0;
            for (int corner = 0; corner < 3; corner++)
            {
                int finalIndex = finalIndices[face * 3 + corner];
                Vector3 position = vertices[finalIndex];
                string key = Quantize(position.x) + ":" + Quantize(position.y) + ":" + Quantize(position.z);
                int sourceIndex = Array.FindIndex(sourceVertices, v =>
                    Quantize(v.x) + ":" + Quantize(v.y) + ":" + Quantize(v.z) == key);
                if (sourceIndex < 0) return false;
                Vector2 baseUv = sourceUv[sourceIndex];
                if (NearUv(uv[finalIndex], baseUv)) continue;
                if (!expectedPairPositions.Contains(key) || !NearUv(uv[finalIndex],
                    new Vector2(baseUv.x + 0.25f, baseUv.y))) return false;
                faceShifted++;
            }
            if (faceShifted != 0 && faceShifted != 2) return false;
            if (faceShifted == 2) shiftedFaces++;
        }
        return shiftedSharedCorners == 2 && shiftedFaces == 1;
    }

    private static bool NearUv(Vector2 a, Vector2 b)
    { return Math.Abs(a.x - b.x) <= 0.001f && Math.Abs(a.y - b.y) <= 0.001f; }

    private static string Quantize(float value)
    {
        return Math.Round((double)value * 100000.0, MidpointRounding.AwayFromZero)
            .ToString("0", CultureInfo.InvariantCulture);
    }

    private static byte[] ReadIfPresent(string path)
    { return File.Exists(path) ? File.ReadAllBytes(path) : null; }
    private static bool SameBytes(byte[] a, byte[] b)
    {
        if (a == null || b == null) return a == null && b == null;
        return a.SequenceEqual(b);
    }
    private static string Hash(string path)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static string Disk(string assetPath)
    { return Path.Combine(Application.dataPath, assetPath.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
}
