using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>Fixture-bounded Unity 2022.3 fresh-project import oracle for T0-C.</summary>
public static class VapbT0CFreshImportProbe
{
    private const string ExpectedPackageSha256 = "20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd";
    private const string ExpectedModelGuid = "de246c64f2740ebfb1a93dbad053e07b";
    private const string ExpectedModelSha256 = "a27cc6100cd2cbce5f0e9b3a4b24867e042e861ac33ff233a4f37276de491c1e";
    private const string ManifestPath = "Assets/VAPBExport/manifest.json";
    private const string ResultFileName = "VAPB_T0C_UnityImport_Result.json";
    private const string DiagnosticResultFileName = "VAPB_T0C_MaterialDiagnostic_Result.json";

    [Serializable]
    private sealed class Manifest
    {
        public RebindTask[] reference_rebind_tasks;
    }

    [Serializable]
    private sealed class RebindTask
    {
        public string kind;
        public string variant_path;
        public string model_guid;
        public string model_sha256;
        public string prefab_guid;
        public MaterialBinding[] material_bindings;
    }

    [Serializable]
    private sealed class MaterialBinding
    {
        public string guid;
        public string file_id;
        public string transport_id;
    }

    [Serializable]
    private sealed class MaterialResult
    {
        public bool is_null;
        public bool guid_lookup_succeeded;
        public string guid;
        public long local_file_id;
        public string path;
        public string name;
    }

    [Serializable]
    private sealed class SubmeshResult
    {
        public int triangle_count;
        public int[] indices;
    }

    [Serializable]
    private sealed class OverrideResult
    {
        public string property_path;
        public string target_renderer_guid;
        public long target_renderer_local_id;
        public string object_reference_guid;
        public long object_reference_local_id;
        public string value;
    }

    [Serializable]
    private sealed class ProbeResult
    {
        public string status;
        public string error;
        public string editor_version;
        public string package_sha256;
        public string generated_model_guid;
        public string generated_model_sha256;
        public string generated_model_mesh_guid;
        public long generated_model_mesh_local_file_id;
        public string variant_path;
        public string variant_asset_guid;
        public int renderer_count;
        public MaterialResult[] materials;
        public MaterialBinding[] expected_material_bindings;
        public MaterialResult[] native_carrier_materials;
        public int native_carrier_renderer_count;
        public int native_carrier_matching_mesh_renderer_count;
        public int[] triangles_by_submesh;
        public SubmeshResult[] submeshes;
        public Vector3[] mesh_vertices;
        public string source_prefab_path;
        public string source_renderer_mesh_guid;
        public long source_renderer_mesh_local_file_id;
        public MaterialResult[] source_renderer_materials;
        public SubmeshResult[] source_submeshes;
        public Vector3[] source_mesh_vertices;
        public Matrix4x4 mesh_to_prefab_root;
        public Matrix4x4 source_mesh_to_prefab_root;
        public int source_renderer_count;
        public OverrideResult[] variant_material_overrides;
        public int asset_database_path_count;
    }

    public static void InspectFreshPackageImport()
    {
        var result = new ProbeResult { status = "FAIL", editor_version = Application.unityVersion };
        var resultPath = Path.Combine(Directory.GetParent(Application.dataPath).FullName, ResultFileName);
        try
        {
            var packagePath = Environment.GetEnvironmentVariable("VAPB_T0C_PACKAGE");
            if (String.IsNullOrWhiteSpace(packagePath) || !File.Exists(packagePath))
                throw new InvalidOperationException("VAPB_T0C_PACKAGE is missing or not a file");
            result.package_sha256 = Sha256(File.ReadAllBytes(packagePath));
            if (result.package_sha256 != ExpectedPackageSha256)
                throw new InvalidOperationException("package SHA differs from the pinned T1 export");

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var manifestAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath);
            if (manifestAsset == null)
                throw new InvalidOperationException("export manifest was not imported");
            var manifest = JsonUtility.FromJson<Manifest>(manifestAsset.text);
            var tasks = manifest == null || manifest.reference_rebind_tasks == null
                ? new RebindTask[0]
                : Array.FindAll(manifest.reference_rebind_tasks, row => row != null && row.kind == "RESTORE_DIRECT_SKIN_VARIANT_V1");
            if (tasks.Length != 1)
                throw new InvalidOperationException("expected one direct-skin rebind task");
            var task = tasks[0];
            result.generated_model_guid = task.model_guid;
            result.generated_model_sha256 = task.model_sha256;
            result.variant_path = task.variant_path;
            if (!String.Equals(task.model_guid, ExpectedModelGuid, StringComparison.OrdinalIgnoreCase)
                || !String.Equals(task.model_sha256, ExpectedModelSha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("manifest generated Model GUID/SHA differs from pinned T1 export");
            if (task.material_bindings == null || task.material_bindings.Length != 3)
                throw new InvalidOperationException("manifest must contain three ordered material bindings");

            var modelPath = AssetDatabase.GUIDToAssetPath(ExpectedModelGuid);
            if (String.IsNullOrEmpty(modelPath) || !modelPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("generated Model GUID did not resolve to an imported FBX");
            var modelPayloadPath = Path.Combine(Directory.GetParent(Application.dataPath).FullName, modelPath);
            var modelPayloadSha = Sha256(File.ReadAllBytes(modelPayloadPath));
            if (modelPayloadSha != ExpectedModelSha256)
                throw new InvalidOperationException("imported generated FBX payload bytes changed");

            var variantGuid = AssetDatabase.AssetPathToGUID(task.variant_path);
            if (String.IsNullOrEmpty(variantGuid))
                throw new InvalidOperationException("manifest Variant path did not resolve in AssetDatabase");
            result.variant_asset_guid = variantGuid;
            var contents = PrefabUtility.LoadPrefabContents(task.variant_path);
            try
            {
                var renderers = contents.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                result.renderer_count = renderers.Length;
                if (renderers.Length != 1)
                    throw new InvalidOperationException("expected exactly one SkinnedMeshRenderer in the imported Variant");
                var renderer = renderers[0];
                var mesh = renderer.sharedMesh;
                if (mesh == null)
                    throw new InvalidOperationException("imported SkinnedMeshRenderer has no Mesh");
                string meshGuid;
                long meshLocalId;
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out meshGuid, out meshLocalId))
                    throw new InvalidOperationException("Unity could not identify the imported Mesh subasset");
                result.generated_model_mesh_guid = meshGuid;
                result.generated_model_mesh_local_file_id = meshLocalId;
                if (!String.Equals(meshGuid, ExpectedModelGuid, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Variant Mesh does not resolve to the generated Model GUID");

                var slots = renderer.sharedMaterials;
                if (slots == null || slots.Length != task.material_bindings.Length)
                    throw new InvalidOperationException("Unity Renderer material slot count differs from manifest bindings");
                result.materials = new MaterialResult[slots.Length];
                for (var index = 0; index < slots.Length; index++)
                {
                    var expected = task.material_bindings[index];
                    var material = slots[index];
                    if (material == null)
                        throw new InvalidOperationException("Unity Renderer contains a null Material at slot " + index);
                    string materialGuid;
                    long localId;
                    if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out materialGuid, out localId))
                        throw new InvalidOperationException("Unity could not identify Material subasset at slot " + index);
                    var path = AssetDatabase.GetAssetPath(material);
                    if (!String.Equals(materialGuid, expected.guid, StringComparison.OrdinalIgnoreCase)
                        || localId.ToString() != expected.file_id)
                        throw new InvalidOperationException("Unity Material GUID/local ID differs from ordered manifest binding at slot " + index);
                    result.materials[index] = new MaterialResult {
                        guid = materialGuid, local_file_id = localId, path = path
                    };
                }

                if (mesh.subMeshCount != 3)
                    throw new InvalidOperationException("Unity generated Mesh does not contain exactly three submeshes");
                result.triangles_by_submesh = new int[mesh.subMeshCount];
                for (var index = 0; index < mesh.subMeshCount; index++)
                {
                    result.triangles_by_submesh[index] = (int)mesh.GetIndexCount(index) / 3;
                    if (result.triangles_by_submesh[index] != new[] { 2, 4, 6 }[index])
                        throw new InvalidOperationException("Unity submesh triangle count differs from [2,4,6] at slot " + index);
                }
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(contents);
            }

            var paths = AssetDatabase.GetAllAssetPaths();
            result.asset_database_path_count = paths.Length;
            result.status = "PASS";
        }
        catch (Exception exception)
        {
            result.error = exception.GetType().Name + ": " + exception.Message;
            result.status = "FAIL";
        }

        var json = JsonUtility.ToJson(result, true);
        using (var stream = new FileStream(resultPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
            writer.Write(json);
        Debug.Log("VAPB_T0C_UNITY_IMPORT_" + result.status + " " + json);
        if (result.status != "PASS")
            throw new InvalidOperationException(result.error ?? "Unity fresh import probe failed");
    }

    /// <summary>Diagnostic only: capture material slot identities and submesh sizes without acceptance assertions.</summary>
    public static void DiagnoseMaterialSlots()
    {
        var result = new ProbeResult { status = "DIAGNOSTIC_ONLY", editor_version = Application.unityVersion };
        var resultPath = Path.Combine(Directory.GetParent(Application.dataPath).FullName,
            DiagnosticResultFileName);
        GameObject contents = null;
        try
        {
            var packagePath = Environment.GetEnvironmentVariable("VAPB_T0C_PACKAGE");
            if (String.IsNullOrWhiteSpace(packagePath) || !File.Exists(packagePath))
                throw new InvalidOperationException("VAPB_T0C_PACKAGE is missing or not a file");
            result.package_sha256 = Sha256(File.ReadAllBytes(packagePath));
            if (result.package_sha256 != ExpectedPackageSha256)
                throw new InvalidOperationException("package SHA differs from the pinned T1 export");

            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Disk(ManifestPath)));
            if (manifest == null || manifest.reference_rebind_tasks == null ||
                manifest.reference_rebind_tasks.Length != 1)
                throw new InvalidOperationException("Expected exactly one manifest rebind task");
            var task = manifest.reference_rebind_tasks[0];
            result.variant_path = task.variant_path;
            result.expected_material_bindings = task.material_bindings;
            result.source_prefab_path = AssetDatabase.GUIDToAssetPath(task.prefab_guid);
            string variantGuid = AssetDatabase.AssetPathToGUID(task.variant_path);
            if (String.IsNullOrEmpty(variantGuid))
                throw new InvalidOperationException("Variant path is not present in the AssetDatabase");
            result.variant_asset_guid = variantGuid;

            contents = PrefabUtility.LoadPrefabContents(task.variant_path);
            if (contents == null) throw new InvalidOperationException("Unity could not load Variant contents");
            var renderers = contents.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            result.renderer_count = renderers.Length;
            if (renderers.Length != 1)
                throw new InvalidOperationException("Expected exactly one SkinnedMeshRenderer in the imported Variant");
            var renderer = renderers[0];
            var sourceRendererObject = PrefabUtility.GetCorrespondingObjectFromSource(renderer);
            if (sourceRendererObject == null) throw new InvalidOperationException("Variant renderer has no corresponding source renderer");
            var mods = PrefabUtility.GetPropertyModifications(contents);
            var overrides = new List<OverrideResult>();
            if (mods != null) foreach (var mod in mods)
            {
                if (mod == null || mod.target != sourceRendererObject || mod.propertyPath == null || !mod.propertyPath.StartsWith("m_Materials.Array.data[", StringComparison.Ordinal)) continue;
                var entry = new OverrideResult { property_path = mod.propertyPath, value = mod.value ?? "" };
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mod.target, out entry.target_renderer_guid, out entry.target_renderer_local_id);
                if (mod.objectReference != null)
                {
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mod.objectReference, out entry.object_reference_guid, out entry.object_reference_local_id);
                }
                overrides.Add(entry);
            }
            result.variant_material_overrides = overrides.ToArray();
            result.mesh_to_prefab_root = contents.transform.worldToLocalMatrix * renderer.transform.localToWorldMatrix;
            var mesh = renderer.sharedMesh;
            if (mesh == null) throw new InvalidOperationException("Variant renderer has no Mesh");
            string meshGuid;
            long meshLocalId;
            result.generated_model_mesh_guid = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                mesh, out meshGuid, out meshLocalId) ? meshGuid : "";
            result.generated_model_mesh_local_file_id = meshLocalId;

            var slots = renderer.sharedMaterials;
            result.materials = new MaterialResult[slots == null ? 0 : slots.Length];
            for (var index = 0; index < result.materials.Length; index++)
            {
                var material = slots[index];
                var item = new MaterialResult { is_null = material == null };
                if (material != null)
                {
                    item.name = material.name;
                    item.path = AssetDatabase.GetAssetPath(material);
                    item.guid_lookup_succeeded = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                        material, out string guid, out long localId);
                    item.guid = item.guid_lookup_succeeded ? guid : "";
                    item.local_file_id = item.guid_lookup_succeeded ? localId : 0;
                }
                result.materials[index] = item;
            }
            string modelPath = AssetDatabase.GUIDToAssetPath(task.model_guid);
            var importedModel = String.IsNullOrEmpty(modelPath)
                ? null : AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (importedModel != null)
            {
                var nativeRenderers = importedModel.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                result.native_carrier_renderer_count = nativeRenderers.Length;
                SkinnedMeshRenderer matchingNativeRenderer = null;
                foreach (var nativeRenderer in nativeRenderers)
                {
                    if (nativeRenderer.sharedMesh == null ||
                        !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(nativeRenderer.sharedMesh,
                            out string nativeMeshGuid, out long nativeMeshLocalId)) continue;
                    if (nativeMeshGuid != result.generated_model_mesh_guid ||
                        nativeMeshLocalId != result.generated_model_mesh_local_file_id) continue;
                    result.native_carrier_matching_mesh_renderer_count++;
                    matchingNativeRenderer = nativeRenderer;
                }
                if (result.native_carrier_matching_mesh_renderer_count == 1)
                {
                    var nativeSlots = matchingNativeRenderer.sharedMaterials;
                    result.native_carrier_materials = new MaterialResult[nativeSlots == null ? 0 : nativeSlots.Length];
                    for (var index = 0; index < result.native_carrier_materials.Length; index++)
                    {
                        var material = nativeSlots[index];
                        var item = new MaterialResult { is_null = material == null };
                        if (material != null)
                        {
                            item.name = material.name;
                            item.path = AssetDatabase.GetAssetPath(material);
                            item.guid_lookup_succeeded = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                                material, out string guid, out long localId);
                            item.guid = item.guid_lookup_succeeded ? guid : "";
                            item.local_file_id = item.guid_lookup_succeeded ? localId : 0;
                        }
                        result.native_carrier_materials[index] = item;
                    }
                }
            }
            if (mesh.subMeshCount > 0)
            {
                result.mesh_vertices = mesh.vertices;
                result.triangles_by_submesh = new int[mesh.subMeshCount];
                result.submeshes = new SubmeshResult[mesh.subMeshCount];
                for (var index = 0; index < mesh.subMeshCount; index++)
                {
                    var indices = mesh.GetTriangles(index);
                    result.triangles_by_submesh[index] = indices.Length / 3;
                    result.submeshes[index] = new SubmeshResult { triangle_count = indices.Length / 3, indices = indices };
                }
            }
            var sourcePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(result.source_prefab_path);
            if (sourcePrefab == null) throw new InvalidOperationException("Source Prefab could not be loaded");
            {
                var sourceRenderers = sourcePrefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                result.source_renderer_count = sourceRenderers.Length;
                if (sourceRenderers.Length != 1) throw new InvalidOperationException("Expected exactly one source SkinnedMeshRenderer");
                foreach (var sourceRenderer in sourceRenderers)
                {
                    if (sourceRenderer.sharedMesh == null) throw new InvalidOperationException("Source renderer has no Mesh");
                    if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sourceRenderer.sharedMesh, out string sourceMeshGuid, out long sourceMeshLocalId)) throw new InvalidOperationException("Could not identify source Mesh");
                    result.source_renderer_mesh_guid = sourceMeshGuid;
                    result.source_renderer_mesh_local_file_id = sourceMeshLocalId;
                    result.source_mesh_to_prefab_root = sourcePrefab.transform.worldToLocalMatrix * sourceRenderer.transform.localToWorldMatrix;
                    var sourceSlots = sourceRenderer.sharedMaterials;
                    result.source_renderer_materials = new MaterialResult[sourceSlots == null ? 0 : sourceSlots.Length];
                    for (var i = 0; i < result.source_renderer_materials.Length; i++)
                    {
                        var material = sourceSlots[i];
                        var item = new MaterialResult { is_null = material == null };
                        if (material != null)
                        {
                            item.name = material.name; item.path = AssetDatabase.GetAssetPath(material);
                            item.guid_lookup_succeeded = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string guid, out long id);
                            item.guid = item.guid_lookup_succeeded ? guid : ""; item.local_file_id = item.guid_lookup_succeeded ? id : 0;
                        }
                        result.source_renderer_materials[i] = item;
                    }
                    var sourceMesh = sourceRenderer.sharedMesh;
                    result.source_mesh_vertices = sourceMesh.vertices;
                    result.source_submeshes = new SubmeshResult[sourceMesh.subMeshCount];
                    for (var i = 0; i < sourceMesh.subMeshCount; i++)
                    {
                        var indices = sourceMesh.GetTriangles(i);
                        result.source_submeshes[i] = new SubmeshResult { triangle_count = indices.Length / 3, indices = indices };
                    }
                    break;
                }
            }
            result.asset_database_path_count = AssetDatabase.GetAllAssetPaths().Length;
            result.error = "DIAGNOSTIC_CAPTURED_NO_ACCEPTANCE_ASSERTIONS";
        }
        catch (Exception exception)
        {
            result.status = "DIAGNOSTIC_FAILED";
            result.error = exception.GetType().Name + ": " + exception.Message;
        }
        finally
        {
            if (contents != null) PrefabUtility.UnloadPrefabContents(contents);
        }

        using (var stream = new FileStream(resultPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
            writer.Write(JsonUtility.ToJson(result, true));
        Debug.Log("VAPB_T0C_MATERIAL_DIAGNOSTIC_" + result.status + " " + JsonUtility.ToJson(result));
        if (result.status != "DIAGNOSTIC_ONLY")
            throw new InvalidOperationException(result.error ?? "T0-C material diagnostic failed");
    }

    private static string Disk(string assetPath)
    {
        if (String.IsNullOrEmpty(assetPath) || !assetPath.StartsWith("Assets/", StringComparison.Ordinal))
            throw new InvalidOperationException("Expected an Assets path");
        return Path.Combine(Directory.GetParent(Application.dataPath).FullName,
            assetPath.Replace('/', Path.DirectorySeparatorChar));
    }

    private static string Sha256(byte[] bytes)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }
}
