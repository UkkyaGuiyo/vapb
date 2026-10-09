using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbSkinRoundtripProbe
{
    public static Action BoundedCapture;
    private static string Folder => SessionState.GetBool("VAPB_PHYSBONE_CASE", false) ? "Assets/VapbOwnedPhysBonePreservedSlots" : "Assets/VapbSkinRoundtrip";
    private static string Input => Folder + "/Input.fbx";
    private static string Prefab => Folder + "/Avatar.prefab";
    private static string MaterialPath => Folder + "/Original.mat";
    private static string TexturePath => Folder + "/Original.png";
    private const string Manifest = "Assets/VAPBExport/manifest.json";
    private const string Phase = "VAPB_SKIN_ROUNDTRIP_PHASE";
    private const string ImportStart = "VAPB_SKIN_ROUNDTRIP_IMPORT_START";

    [Serializable] private sealed class BoneInfo
    {
        public string name; // Synthetic fixture display aid only; production never joins by name.
        public string target_transform_file_id;
    }
    [Serializable] private sealed class SourceInfo
    {
        public string prefab_guid;
        public string renderer_file_id;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string source_mesh_file_id;
        public string material_guid;
        public string material_file_id;
        public string texture_guid;
        public string texture_sha256;
        public string root_bone_target_transform_file_id;
        public BoneInfo[] bones;
        public string original_vertex_checksum;
        public string original_weight_checksum;
        public int original_vertex_count;
    }
    [Serializable] private sealed class MultiSkinInfo
    {
        public string prefab_guid;
        public string prefab_source_sha256;
        public string source_model_guid;
        public string source_model_sha256;
        public string material_guid;
        public string material_file_id;
        public SourceInfo[] skins;
    }
    [Serializable] private sealed class OutputManifest { public Task[] reference_rebind_tasks; }
    [Serializable] private sealed class Task
    {
        public string kind;
        public string model_guid;
        public string realization_id;
        public string variant_path;
        public BoneTask[] bones;
        public string root_bone_target_transform_file_id;
    }
    [Serializable] private sealed class BoneTask
    {
        public string edited_bone_realization_id;
        public string target_transform_file_id;
    }
    [Serializable] private sealed class Report
    {
        public bool pass;
        public string phase;
        public string error;
        public bool packageImported;
        public bool firstApply;
        public bool editedMesh;
        public bool changedVertices;
        public bool changedWeights;
        public bool boneIdsPreserved;
        public bool materialsPreserved;
        public bool sourceModelUnchanged;
        public bool unrelatedStatePreserved;
        public bool nativePhysBoneAndColliderPreserved;
        public bool sdkScriptsResolved;
        public bool expectedDeformation;
        public float deformationMaxError;
        public float deformationMaxExpected;
        public float deformationMaxObserved;
        public int deformationWeightedVertices;
        public bool secondApply;
        public bool secondApplyUnchanged;
        public bool invalidMappingRejected;
        public bool invalidMappingUnchanged;
        public int boneCount;
        public int vertexCount;
    }

    static VapbSkinRoundtripProbe()
    {
        AssetDatabase.importPackageCompleted += OnImportCompleted;
        AssetDatabase.importPackageFailed += OnImportFailed;
        AssetDatabase.importPackageCancelled += OnImportCancelled;
        EditorApplication.update += CheckTimeout;
        if (SessionState.GetString(Phase, "") == "completed")
            EditorApplication.delayCall += ValidateImported;
    }

    private static void OnImportCompleted(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "completed");
        EditorApplication.delayCall += ValidateImported;
    }
    private static void OnImportFailed(string name, string error)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_FAILED" });
    }
    private static void OnImportCancelled(string name)
    {
        if (SessionState.GetString(Phase, "") == "importing")
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_CANCELLED" });
    }
    private static void CheckTimeout()
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        float started = SessionState.GetFloat(ImportStart, 0f);
        if (started > 0f && EditorApplication.timeSinceStartup - started > 180f)
            Finish(new Report { phase = "validate", error = "PACKAGE_IMPORT_TIMEOUT" });
    }

    public static void Prepare()
    {
        PrepareCore(false, false);
    }

    public static void PrepareSeparateRoot()
    {
        PrepareCore(true, false);
    }

    public static void PrepareTexture()
    {
        PrepareCore(false, true);
    }

    public static void PreparePhysBonePreservedSlots() { PreparePhysBone(); }
    public static void ValidatePhysBonePreservedSlots() { ValidatePhysBone(); }
    public static void PreparePhysBone()
    {
        SessionState.SetBool("VAPB_PHYSBONE_CASE", true);
        PrepareCore(false, false);
    }
    public static void ValidatePhysBone()
    {
        SessionState.SetBool("VAPB_PHYSBONE_CASE", true);
        Validate();
    }
    private static Type SdkComponent(string name)
    {
        var matches = TypeCache.GetTypesDerivedFrom<MonoBehaviour>().Where(t => t.Name == name &&
            t.FullName.StartsWith("VRC.", StringComparison.Ordinal)).ToArray();
        if (matches.Length != 1) throw new InvalidOperationException("SDK_COMPONENT_TYPE_NOT_UNIQUE");
        return matches[0];
    }
    private static SerializedProperty Property(SerializedObject value, string name)
    {
        var prop = value.FindProperty(name);
        if (prop == null) throw new InvalidOperationException("SDK_SERIALIZED_PROPERTY_UNAVAILABLE:" + name);
        return prop;
    }
    private static void AddPhysBone(GameObject root, SkinnedMeshRenderer skin)
    {
        var owner = new GameObject("OwnedPhysBone"); owner.transform.SetParent(skin.bones[0], false);
        var colliderOwner = new GameObject("OwnedCollider"); colliderOwner.transform.SetParent(root.transform, false);
        var collider = (MonoBehaviour)colliderOwner.AddComponent(SdkComponent("VRCPhysBoneCollider"));
        var bone = (MonoBehaviour)owner.AddComponent(SdkComponent("VRCPhysBone"));
        var co = new SerializedObject(collider);
        Property(co, "rootTransform").objectReferenceValue = null;
        Property(co, "radius").floatValue = 0.125f; co.ApplyModifiedPropertiesWithoutUndo();
        var bo = new SerializedObject(bone);
        Property(bo, "rootTransform").objectReferenceValue = null;
        Property(bo, "pull").floatValue = 0.2f; Property(bo, "spring").floatValue = 0.3f;
        Property(bo, "stiffness").floatValue = 0.4f; Property(bo, "gravity").floatValue = 0.5f;
        var refs = Property(bo, "colliders"); refs.arraySize = 1;
        refs.GetArrayElementAtIndex(0).objectReferenceValue = collider; bo.ApplyModifiedPropertiesWithoutUndo();
        ComponentState(root); // Resolve real MonoScript GUID/fileID now, never invent one.
    }
    private static string ComponentState(GameObject root)
    {
        var result = new System.Text.StringBuilder();
        foreach (var typeName in new[] { "VRCPhysBone", "VRCPhysBoneCollider" })
        {
            var components = root.GetComponentsInChildren(SdkComponent(typeName), true);
            if (components.Length != 1) throw new InvalidOperationException("SDK_COMPONENT_COUNT");
            var component = (MonoBehaviour)components[0];
            var script = MonoScript.FromMonoBehaviour(component);
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(script, out string guid, out long id) ||
                string.IsNullOrEmpty(guid) || id == 0 || !AssetDatabase.GetAssetPath(script).StartsWith("Packages/com.vrchat."))
                throw new InvalidOperationException("SDK_SCRIPT_ID_UNRESOLVED");
            result.Append(typeName).Append(':').Append(guid).Append(':').Append(id);
            var so = new SerializedObject(component);
            if (Property(so, "rootTransform").objectReferenceValue != null)
                throw new InvalidOperationException("SDK_NULL_ROOT_CHANGED");
            foreach (var name in typeName == "VRCPhysBone" ? new[] { "pull", "spring", "stiffness", "gravity" } : new[] { "radius" })
                result.Append('|').Append(name).Append('=').Append(Property(so, name).floatValue.ToString("R", CultureInfo.InvariantCulture));
            if (typeName == "VRCPhysBone")
            {
                var refs = Property(so, "colliders");
                var all = root.GetComponentsInChildren(SdkComponent("VRCPhysBoneCollider"), true);
                if (refs.arraySize != 1 || refs.GetArrayElementAtIndex(0).objectReferenceValue != all.Single())
                    throw new InvalidOperationException("SDK_COLLIDER_REFERENCE_CHANGED");
                result.Append("|collider=owned-native-component");
            }
            result.AppendLine();
        }
        return result.ToString();
    }
    private static void ValidatePhysBoneImported()
    {
        var report = new Report { phase = "native_physbone", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            string before = ComponentState(source);
            if (before != File.ReadAllText(ProjectFile("PhysBoneSourceState.txt"))) throw new InvalidOperationException("SOURCE_COMPONENT_CHANGED");
            string sourceHash = FileHash(AssetFile(Prefab));
            var output = JsonUtility.FromJson<OutputManifest>(File.ReadAllText(AssetFile(Manifest)));
            var task = output.reference_rebind_tasks.Single();
            report.packageImported = true;
            var parse = typeof(VapbModelSkinFinalizer).GetMethod("ParseManifestJson", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
            if (parse == null) throw new InvalidOperationException("OPTIONAL_JSON_READER_MISSING");
            foreach (string tail in new[] { "", ",\"weight_transport\":null,\"parent_transform_mapping\":null", ",\"unknown\":{\"weight_transport\":{}},\"label\":\"weight_transport\"" })
            {
                var m = parse.Invoke(null, new object[] { "{\"reference_rebind_tasks\":[{\"kind\":\"RESTORE_DIRECT_SKIN_VARIANT_V1\"" + tail + "}]}" });
                var a = (Array)m.GetType().GetField("reference_rebind_tasks").GetValue(m); var item = a.GetValue(0);
                if (item.GetType().GetField("weight_transport").GetValue(item) != null || item.GetType().GetField("parent_transform_mapping").GetValue(item) != null)
                    throw new InvalidOperationException("ABSENT_OPTIONAL_JSON_CONTROL_FAILED");
            }
            var explicitM = parse.Invoke(null, new object[] { "{\"reference_rebind_tasks\":[{\"kind\":\"RESTORE_DIRECT_SKIN_VARIANT_V1\",\"weight_transport\":{},\"parent_transform_mapping\":{}}]}" });
            var explicitTasks = (Array)explicitM.GetType().GetField("reference_rebind_tasks").GetValue(explicitM); var explicitItem = explicitTasks.GetValue(0);
            if (explicitItem.GetType().GetField("weight_transport").GetValue(explicitItem) == null || explicitItem.GetType().GetField("parent_transform_mapping").GetValue(explicitItem) == null)
                throw new InvalidOperationException("EXPLICIT_OPTIONAL_JSON_CONTROL_FAILED");
            try {
                typeof(VapbModelSkinFinalizer).GetMethod("ValidateTask", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).Invoke(null, new[] { explicitItem });
                throw new InvalidOperationException("EXPLICIT_EMPTY_RECEIPT_ACCEPTED");
            } catch (System.Reflection.TargetInvocationException error) {
                if (error.InnerException.Message != "WEIGHT_TRANSPORT_CONTEXT_UNSUPPORTED") throw;
            }
            Debug.Log("NATIVE_OPTIONAL_JSON_CONTROLS_PASS");
            var read = typeof(VapbModelSkinFinalizer).GetMethod("ReadManifest", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
            var decoded = read.Invoke(null, new object[] { Manifest });
            var tasks = (Array)decoded.GetType().GetField("reference_rebind_tasks").GetValue(decoded);
            var decodedTask = tasks.GetValue(0);
            Debug.Log("NATIVE_OPTIONAL_OBJECT_DIAGNOSIS weight_transport=" + (decodedTask.GetType().GetField("weight_transport").GetValue(decodedTask) != null)
                + " parent_transform_mapping=" + (decodedTask.GetType().GetField("parent_transform_mapping").GetValue(decodedTask) != null));
            report.firstApply = VapbModelSkinFinalizer.Apply(Manifest);
            if (!report.firstApply) throw new InvalidOperationException("FIRST_APPLY_FAILED");
            var variant = AssetDatabase.LoadAssetAtPath<GameObject>(task.variant_path);
            if (variant == null || PrefabUtility.GetCorrespondingObjectFromSource(variant) != source)
                throw new InvalidOperationException("VARIANT_SOURCE_MISMATCH");
            report.nativePhysBoneAndColliderPreserved = ComponentState(variant) == before;
            foreach (var name in new[] { "VRCPhysBone", "VRCPhysBoneCollider" })
                if (PrefabUtility.GetCorrespondingObjectFromSource(variant.GetComponentsInChildren(SdkComponent(name), true).Single()) !=
                    source.GetComponentsInChildren(SdkComponent(name), true).Single()) throw new InvalidOperationException("COMPONENT_SOURCE_MISMATCH");
            report.sdkScriptsResolved = true;
            string first = FileHash(AssetFile(task.variant_path));
            report.secondApply = VapbModelSkinFinalizer.Apply(Manifest);
            report.secondApplyUnchanged = FileHash(AssetFile(task.variant_path)) == first;
            report.sourceModelUnchanged = FileHash(AssetFile(Prefab)) == sourceHash;
            report.pass = report.firstApply && report.nativePhysBoneAndColliderPreserved && report.secondApply && report.secondApplyUnchanged && report.sourceModelUnchanged;
            report.error = report.pass ? "NONE" : "COMPONENT_ASSERTION_FAILED";
        }
        catch (Exception error) { report.error = error.Message; }
        Finish(report);
    }

    public static void PrepareMultiSkin()
    {
        var report = new Report { phase = "prepare_multi", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            AssetDatabase.ImportAsset(Input, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
            SkinnedMeshRenderer[] imported = model == null ? null :
                model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (imported == null || imported.Length != 2 ||
                Array.Exists(imported, skin => skin.sharedMesh == null || skin.rootBone == null || skin.bones.Length < 2))
                throw new InvalidOperationException("INPUT_SKIN_UNSUPPORTED");
            Shader shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidOperationException("STANDARD_SHADER_MISSING");
            Material material = new Material(shader) { name = "SkinOriginal" };
            AssetDatabase.CreateAsset(material, MaterialPath);
            GameObject instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
            if (instance == null) throw new InvalidOperationException("MODEL_INSTANCE_FAILED");
            try
            {
                PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                instance.name = "Avatar";
                SkinnedMeshRenderer[] skins = instance.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                if (skins.Length != 2) throw new InvalidOperationException("UNPACK_SKIN_UNSUPPORTED");
                foreach (SkinnedMeshRenderer skin in skins) skin.sharedMaterials = new[] { material };
                GameObject sentinel = new GameObject("UnrelatedSentinel");
                sentinel.transform.SetParent(instance.transform, false);
                sentinel.transform.localPosition = new Vector3(4f, 5f, 6f);
                if (PrefabUtility.SaveAsPrefabAsset(instance, Prefab) == null)
                    throw new InvalidOperationException("PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer[] renderers = prefab == null ? null :
                prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (renderers == null || renderers.Length != 2)
                throw new InvalidOperationException("PREFAB_SKIN_UNSUPPORTED");
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId))
                throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
            string expectedModelGuid = AssetDatabase.AssetPathToGUID(Input);
            var rows = new SourceInfo[2];
            var meshIds = new HashSet<long>();
            var rendererIds = new HashSet<long>();
            string prefabGuid = null;
            for (int index = 0; index < renderers.Length; index++)
            {
                SkinnedMeshRenderer renderer = renderers[index];
                if (renderer.sharedMesh == null || renderer.rootBone == null || renderer.bones.Length < 2 ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string rowPrefabGuid, out long rendererId) ||
                    !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.sharedMesh, out string modelGuid, out long meshId) ||
                    modelGuid != expectedModelGuid || !meshIds.Add(meshId) || !rendererIds.Add(rendererId) ||
                    (prefabGuid != null && prefabGuid != rowPrefabGuid))
                    throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
                prefabGuid = rowPrefabGuid;
                var bones = new BoneInfo[renderer.bones.Length];
                for (int boneIndex = 0; boneIndex < bones.Length; boneIndex++)
                {
                    Transform bone = renderer.bones[boneIndex];
                    if (bone == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(bone,
                        out string boneGuid, out long boneId) || boneGuid != prefabGuid)
                        throw new InvalidOperationException("BONE_ID_UNAVAILABLE");
                    bones[boneIndex] = new BoneInfo { name = bone.name, target_transform_file_id = Id(boneId) };
                }
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rootBone,
                    out string rootGuid, out long rootId) || rootGuid != prefabGuid)
                    throw new InvalidOperationException("ROOT_ID_UNAVAILABLE");
                rows[index] = new SourceInfo {
                    prefab_guid = prefabGuid, renderer_file_id = Id(rendererId),
                    source_model_guid = modelGuid, source_mesh_file_id = Id(meshId),
                    root_bone_target_transform_file_id = Id(rootId), bones = bones,
                    original_vertex_checksum = VertexChecksum(renderer.sharedMesh),
                    original_weight_checksum = WeightChecksum(renderer.sharedMesh),
                    original_vertex_count = renderer.sharedMesh.vertexCount
                };
            }
            if (rows[0].root_bone_target_transform_file_id != rows[1].root_bone_target_transform_file_id ||
                rows[0].bones.Length != rows[1].bones.Length)
                throw new InvalidOperationException("BONE_ID_UNAVAILABLE");
            for (int i = 0; i < rows[0].bones.Length; i++)
                if (rows[0].bones[i].target_transform_file_id != rows[1].bones[i].target_transform_file_id)
                    throw new InvalidOperationException("BONE_ID_UNAVAILABLE");
            Array.Sort(rows, (left, right) =>
                String.CompareOrdinal(left.renderer_file_id, right.renderer_file_id));
            var info = new MultiSkinInfo {
                prefab_guid = prefabGuid, prefab_source_sha256 = FileHash(AssetFile(Prefab)),
                source_model_guid = expectedModelGuid, source_model_sha256 = FileHash(AssetFile(Input)),
                material_guid = materialGuid, material_file_id = Id(materialId), skins = rows
            };
            File.WriteAllText(ProjectFile("MultiSkinSourceInfo.json"), JsonUtility.ToJson(info, true));
            AssetDatabase.ExportPackage(new[] { Input, Prefab, MaterialPath },
                ProjectFile("Source.unitypackage"), ExportPackageOptions.IncludeDependencies);
            report.pass = File.Exists(ProjectFile("Source.unitypackage"));
            report.error = report.pass ? "NONE" : "PACKAGE_MISSING";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    private static void PrepareCore(bool separateRoot, bool textured)
    {
        var report = new Report { phase = "prepare", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            AssetDatabase.ImportAsset(Input, ImportAssetOptions.ForceUpdate);
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
            SkinnedMeshRenderer imported = SingleSkin(model);
            if (imported == null || imported.sharedMesh == null || imported.bones.Length < 2 ||
                imported.rootBone == null)
                throw new InvalidOperationException("INPUT_SKIN_UNSUPPORTED");
            Shader shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidOperationException("STANDARD_SHADER_MISSING");
            Material material = new Material(shader) { name = "SkinOriginal" };
            if (textured)
            {
                var pixels = new Texture2D(4, 3, TextureFormat.RGBA32, false);
                pixels.SetPixels(new[] {
                    Color.red, Color.green, Color.blue, Color.white,
                    Color.red, Color.green, Color.blue, Color.white,
                    Color.red, Color.green, Color.blue, Color.white });
                pixels.Apply();
                File.WriteAllBytes(AssetFile(TexturePath), pixels.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(pixels);
                AssetDatabase.ImportAsset(TexturePath, ImportAssetOptions.ForceSynchronousImport);
                material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
                if (material.mainTexture == null)
                    throw new InvalidOperationException("TEXTURE_IMPORT_FAILED");
            }
            AssetDatabase.CreateAsset(material, MaterialPath);
            if (SessionState.GetBool("VAPB_PHYSBONE_CASE", false))
            {
                // Reuse the existing three-slot owned fixture without collapsing native submeshes.
                // Explicit importer remaps preserve known face semantics instead of guessing overrides.
                var importer = AssetImporter.GetAtPath(Input) as ModelImporter;
                var modelMaterials = AssetDatabase.LoadAllAssetsAtPath(Input).OfType<Material>().ToArray();
                if (importer == null || modelMaterials.Length != 3) throw new InvalidOperationException("SOURCE_MATERIAL_IDENTIFIERS_UNAVAILABLE");
                for (int slot = 0; slot < modelMaterials.Length; slot++)
                {
                    Material target = material;
                    if (slot > 0 && SessionState.GetBool("VAPB_PHYSBONE_CASE", false))
                    {
                        target = new Material(shader) { name = "OwnedSlot" + slot };
                        AssetDatabase.CreateAsset(target, Folder + "/OwnedSlot" + slot + ".mat");
                    }
                    importer.AddRemap(new AssetImporter.SourceAssetIdentifier(modelMaterials[slot]), target);
                }
                importer.SaveAndReimport();
                model = AssetDatabase.LoadAssetAtPath<GameObject>(Input);
                imported = SingleSkin(model);
            }

            GameObject instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
            if (instance == null) throw new InvalidOperationException("MODEL_INSTANCE_FAILED");
            try
            {
                PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                instance.name = "Avatar";
                SkinnedMeshRenderer skin = SingleSkin(instance);
                if (skin == null || skin.bones.Length != imported.bones.Length)
                    throw new InvalidOperationException("UNPACK_SKIN_UNSUPPORTED");
                skin.sharedMaterials = SessionState.GetBool("VAPB_PHYSBONE_CASE", false) ? imported.sharedMaterials : new[] { material };
                GameObject sentinel = new GameObject("UnrelatedSentinel");
                sentinel.transform.SetParent(instance.transform, false);
                sentinel.transform.localPosition = new Vector3(4f, 5f, 6f);
                if (separateRoot)
                {
                    skin.bones[1].localRotation *= Quaternion.Euler(0f, 0f, 12f);
                    skin.rootBone = sentinel.transform;
                }
                if (SessionState.GetBool("VAPB_PHYSBONE_CASE", false)) AddPhysBone(instance, skin);
                if (PrefabUtility.SaveAsPrefabAsset(instance, Prefab) == null)
                    throw new InvalidOperationException("PREFAB_SAVE_FAILED");
            }
            finally { UnityEngine.Object.DestroyImmediate(instance); }
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer renderer = SingleSkin(prefab);
            if (renderer == null || renderer.sharedMesh == null)
                throw new InvalidOperationException("PREFAB_SKIN_UNSUPPORTED");
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer, out string prefabGuid, out long rendererId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.sharedMesh, out string modelGuid, out long meshId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId) ||
                modelGuid != AssetDatabase.AssetPathToGUID(Input))
                throw new InvalidOperationException("ASSET_ID_UNAVAILABLE");
            var bones = new BoneInfo[renderer.bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                Transform bone = renderer.bones[i];
                if (bone == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(bone, out string guid, out long id) ||
                    guid != prefabGuid)
                    throw new InvalidOperationException("BONE_ID_UNAVAILABLE");
                bones[i] = new BoneInfo { name = bone.name, target_transform_file_id = Id(id) };
            }
            if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.rootBone, out string rootGuid, out long rootId) ||
                rootGuid != prefabGuid)
                throw new InvalidOperationException("ROOT_ID_UNAVAILABLE");
            var info = new SourceInfo
            {
                prefab_guid = prefabGuid,
                renderer_file_id = Id(rendererId),
                prefab_source_sha256 = FileHash(AssetFile(Prefab)),
                source_model_guid = modelGuid,
                source_model_sha256 = FileHash(AssetFile(Input)),
                source_mesh_file_id = Id(meshId),
                material_guid = materialGuid,
                material_file_id = Id(materialId),
                texture_guid = textured ? AssetDatabase.AssetPathToGUID(TexturePath) : null,
                texture_sha256 = textured ? FileHash(AssetFile(TexturePath)) : null,
                root_bone_target_transform_file_id = Id(rootId),
                bones = bones,
                original_vertex_checksum = VertexChecksum(renderer.sharedMesh),
                original_weight_checksum = WeightChecksum(renderer.sharedMesh),
                original_vertex_count = renderer.sharedMesh.vertexCount
            };
            File.WriteAllText(ProjectFile("SourceInfo.json"), JsonUtility.ToJson(info, true));
            if (SessionState.GetBool("VAPB_PHYSBONE_CASE", false)) File.WriteAllText(ProjectFile("PhysBoneSourceState.txt"), ComponentState(prefab));
            AssetDatabase.ExportPackage(SessionState.GetBool("VAPB_PHYSBONE_CASE", false) ? new[] { Input, Prefab, MaterialPath, Folder + "/OwnedSlot1.mat", Folder + "/OwnedSlot2.mat" } : textured ? new[] { Input, Prefab, MaterialPath, TexturePath } :
                new[] { Input, Prefab, MaterialPath }, ProjectFile("Source.unitypackage"),
                SessionState.GetBool("VAPB_PHYSBONE_CASE", false) ? ExportPackageOptions.Default : ExportPackageOptions.IncludeDependencies);
            report.pass = File.Exists(ProjectFile("Source.unitypackage"));
            report.error = report.pass ? "NONE" : "PACKAGE_MISSING";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    public static void Validate()
    {
        try
        {
            if (!File.Exists(ProjectFile("SourceInfo.json")) || !File.Exists(ProjectFile("Output.unitypackage")))
                throw new FileNotFoundException();
            SessionState.SetString(Phase, "importing");
            SessionState.SetFloat(ImportStart, (float)EditorApplication.timeSinceStartup);
            AssetDatabase.ImportPackage(ProjectFile("Output.unitypackage"), false);
        }
        catch (Exception error) { Finish(new Report { phase = "validate", error = SafeError(error) }); }
    }

    private static void ValidateImported()
    {
        if (SessionState.GetString(Phase, "") != "completed") return;
        SessionState.SetString(Phase, "validating");
        if (SessionState.GetBool("VAPB_PHYSBONE_CASE", false)) { ValidatePhysBoneImported(); return; }
        var report = new Report { phase = "validate", error = "UNEXPECTED_EXCEPTION" };
        try
        {
            SourceInfo info = JsonUtility.FromJson<SourceInfo>(File.ReadAllText(ProjectFile("SourceInfo.json")));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            report.packageImported = AssetDatabase.LoadAssetAtPath<TextAsset>(Manifest) != null;
            if (!report.packageImported) throw new InvalidOperationException("MANIFEST_NOT_IMPORTED");
            OutputManifest output = JsonUtility.FromJson<OutputManifest>(File.ReadAllText(AssetFile(Manifest)));
            if (output == null || output.reference_rebind_tasks == null || output.reference_rebind_tasks.Length != 1 ||
                output.reference_rebind_tasks[0].kind != "REBIND_SKINNED_RENDERER_V1" ||
                output.reference_rebind_tasks[0].bones == null ||
                (output.reference_rebind_tasks[0].bones.Length != info.bones.Length &&
                 output.reference_rebind_tasks[0].bones.Length != info.bones.Length + 1))
                throw new InvalidOperationException("OUTPUT_TASK_INVALID");
            Task task = output.reference_rebind_tasks[0];
            report.firstApply = VapbReferenceFinalizer.Apply(Manifest);
            if (!report.firstApply) throw new InvalidOperationException("FIRST_APPLY_FAILED");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            SkinnedMeshRenderer skin = SingleSkin(prefab);
            Mesh mesh = skin == null ? null : skin.sharedMesh;
            report.boneCount = skin == null ? 0 : skin.bones.Length;
            report.vertexCount = mesh == null ? 0 : mesh.vertexCount;
            report.editedMesh = mesh != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string meshGuid, out long meshId) &&
                meshGuid == task.model_guid && meshId != 0;
            report.changedVertices = mesh != null && VertexChecksum(mesh) != info.original_vertex_checksum;
            report.changedWeights = mesh != null && WeightChecksum(mesh) != info.original_weight_checksum;
            report.boneIdsPreserved = skin != null && skin.bones.Length == info.bones.Length &&
                task.root_bone_target_transform_file_id == info.root_bone_target_transform_file_id;
            if (report.boneIdsPreserved)
            {
                var mapping = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (BoneTask row in task.bones)
                    mapping.Add(row.edited_bone_realization_id, row.target_transform_file_id);
                GameObject editedModel = AssetDatabase.LoadAssetAtPath<GameObject>(
                    AssetDatabase.GUIDToAssetPath(task.model_guid));
                SkinnedMeshRenderer editedSkin = SingleSkin(editedModel);
                report.boneIdsPreserved &= editedSkin != null && editedSkin.bones.Length == skin.bones.Length;
                for (int i = 0; i < skin.bones.Length; i++)
                {
                    Transform bone = skin.bones[i];
                    Transform editedBone = editedSkin == null || i >= editedSkin.bones.Length ? null : editedSkin.bones[i];
                    string marker = editedBone == null ? null :
                        editedBone.GetComponent<VapbRealizationMarker>()?.boneRealizationId;
                    report.boneIdsPreserved &= bone != null &&
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(bone, out string guid, out long id) &&
                        guid == info.prefab_guid && marker != null &&
                        mapping.TryGetValue(marker, out string targetId) && Id(id) == targetId;
                }
                report.boneIdsPreserved &= skin.rootBone != null &&
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.rootBone, out string rootGuid, out long rootId) &&
                    rootGuid == info.prefab_guid && Id(rootId) == info.root_bone_target_transform_file_id;
            }
            report.materialsPreserved = skin != null && skin.sharedMaterials.Length == 1 &&
                skin.sharedMaterials[0] != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(skin.sharedMaterials[0], out string matGuid, out long matId) &&
                matGuid == info.material_guid && Id(matId) == info.material_file_id;
            if(File.Exists(ProjectFile("SmallWeights.flag")))
            {
                if(!report.boneIdsPreserved) throw new InvalidOperationException("SMALL_WEIGHT_BONE_ID_UNPROVEN");
                int rootIndex=Array.IndexOf(skin.bones,skin.rootBone);
                var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();int offset=0;
                try {
                    for(int vertex=0;vertex<counts.Length;vertex++) {
                        if(counts[vertex]!=2) throw new InvalidOperationException("SMALL_WEIGHT_LOST");
                        float rootWeight=0;
                        for(int n=0;n<counts[vertex];n++) {var w=weights[offset++];if(w.boneIndex==rootIndex)rootWeight=w.weight;}
                        if(rootWeight!=.0005f) throw new InvalidOperationException("SMALL_WEIGHT_CHANGED");
                    }
                } finally {counts.Dispose();weights.Dispose();}
            }
            report.sourceModelUnchanged = FileHash(AssetFile(Input)) == info.source_model_sha256;
            Transform sentinel = prefab == null ? null : prefab.transform.Find("UnrelatedSentinel");
            report.unrelatedStatePreserved = prefab != null && prefab.name == "Avatar" && sentinel != null &&
                sentinel.localPosition == new Vector3(4f, 5f, 6f);
            report.expectedDeformation = skin != null && DeformsWithWeights(prefab, skin, report);
            byte[] first = File.ReadAllBytes(AssetFile(Prefab));
            report.secondApply = VapbReferenceFinalizer.Apply(Manifest);
            report.secondApplyUnchanged = report.secondApply && Equal(first, File.ReadAllBytes(AssetFile(Prefab)));
            string text = File.ReadAllText(AssetFile(Manifest));
            string impossible = "9223372036854775806";
            if (info.bones[0].target_transform_file_id == impossible) impossible = "9223372036854775805";
            string bad = Regex.Replace(text, "\"target_transform_file_id\"\\s*:\\s*\"" +
                Regex.Escape(task.bones[0].target_transform_file_id) + "\"",
                "\"target_transform_file_id\":\"" + impossible + "\"", RegexOptions.None,
                TimeSpan.FromSeconds(1));
            if (bad == text) throw new InvalidOperationException("BONE_ID_NOT_IN_MANIFEST");
            string negative = "Assets/VAPBExport/negative-skin-probe.json";
            File.WriteAllText(AssetFile(negative), bad);
            AssetDatabase.ImportAsset(negative, ImportAssetOptions.ForceUpdate);
            try
            {
                report.invalidMappingRejected = !VapbReferenceFinalizer.Apply(negative);
                report.invalidMappingUnchanged = Equal(first, File.ReadAllBytes(AssetFile(Prefab)));
            }
            finally { AssetDatabase.DeleteAsset(negative); }
            report.pass = report.packageImported && report.firstApply && report.editedMesh &&
                report.changedVertices && report.changedWeights && report.boneIdsPreserved &&
                report.materialsPreserved && report.sourceModelUnchanged && report.unrelatedStatePreserved &&
                report.expectedDeformation && report.secondApply && report.secondApplyUnchanged &&
                report.invalidMappingRejected && report.invalidMappingUnchanged;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch (Exception error) { report.error = SafeError(error); }
        Finish(report);
    }

    private static bool DeformsWithWeights(GameObject prefab, SkinnedMeshRenderer assetSkin, Report report)
    {
        GameObject instance = UnityEngine.Object.Instantiate(prefab);
        Mesh before = new Mesh();
        Mesh after = new Mesh();
        try
        {
            SkinnedMeshRenderer skin = SingleSkin(instance);
            if (skin == null || skin.bones.Length < 2) return false;
            int leafIndex = skin.bones.Length - 1;
            Transform leaf = skin.bones[leafIndex];
            if (leaf == null) return false;
            skin.BakeMesh(before, true);
            Vector3 original = leaf.localPosition;
            Vector3 oldWorld = leaf.position;
            leaf.localPosition = original + new Vector3(0.2f, 0f, 0f);
            Vector3 localDisplacement = skin.transform.worldToLocalMatrix.MultiplyVector(leaf.position - oldWorld);
            skin.BakeMesh(after, true);
            var counts = assetSkin.sharedMesh.GetBonesPerVertex();
            var weights = assetSkin.sharedMesh.GetAllBoneWeights();
            try
            {
                if (before.vertexCount != after.vertexCount || before.vertexCount != counts.Length) return false;
                int offset = 0;
                bool affected = false;
                Vector3[] a = before.vertices, b = after.vertices;
                for (int vertex = 0; vertex < counts.Length; vertex++)
                {
                    float influence = 0f;
                    for (int i = 0; i < counts[vertex]; i++)
                        if (weights[offset + i].boneIndex == leafIndex)
                            influence += weights[offset + i].weight;
                    offset += counts[vertex];
                    Vector3 expected = localDisplacement * influence;
                    Vector3 observed = b[vertex] - a[vertex];
                    report.deformationMaxError = Mathf.Max(report.deformationMaxError,
                        (observed - expected).magnitude);
                    report.deformationMaxExpected = Mathf.Max(report.deformationMaxExpected, expected.magnitude);
                    report.deformationMaxObserved = Mathf.Max(report.deformationMaxObserved, observed.magnitude);
                    if (influence > 0.01f)
                    {
                        report.deformationWeightedVertices++;
                        affected |= observed.magnitude > 0.001f;
                    }
                }
                return affected && report.deformationMaxError <= 0.005f;
            }
            finally { counts.Dispose(); weights.Dispose(); }
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(before);
            UnityEngine.Object.DestroyImmediate(after);
            UnityEngine.Object.DestroyImmediate(instance);
        }
    }

    private static SkinnedMeshRenderer SingleSkin(GameObject root)
    {
        if (root == null) return null;
        SkinnedMeshRenderer[] values = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        return values.Length == 1 ? values[0] : null;
    }
    private static string VertexChecksum(Mesh mesh)
    {
        using (SHA256 sha = SHA256.Create())
        using (MemoryStream memory = new MemoryStream())
        using (BinaryWriter writer = new BinaryWriter(memory))
        {
            foreach (Vector3 value in mesh.vertices)
            { writer.Write(value.x); writer.Write(value.y); writer.Write(value.z); }
            writer.Flush();
            return Convert.ToBase64String(sha.ComputeHash(memory.ToArray()));
        }
    }
    private static string WeightChecksum(Mesh mesh)
    {
        var counts = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            using (SHA256 sha = SHA256.Create())
            using (MemoryStream memory = new MemoryStream())
            using (BinaryWriter writer = new BinaryWriter(memory))
            {
                for (int i = 0; i < counts.Length; i++) writer.Write(counts[i]);
                for (int i = 0; i < weights.Length; i++)
                { writer.Write(weights[i].boneIndex); writer.Write(weights[i].weight); }
                writer.Flush();
                return Convert.ToBase64String(sha.ComputeHash(memory.ToArray()));
            }
        }
        finally { counts.Dispose(); weights.Dispose(); }
    }
    private static string Id(long value) { return value.ToString(CultureInfo.InvariantCulture); }
    private static string FileHash(string path)
    {
        using (SHA256 sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }
    private static bool Equal(byte[] a, byte[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }
    private static string ProjectFile(string name)
    { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }
    private static string AssetFile(string path)
    { return Path.Combine(Application.dataPath, path.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string SafeError(Exception error)
    {
        if (error is InvalidOperationException)
        {
            switch (error.Message)
            {
                case "INPUT_SKIN_UNSUPPORTED": case "STANDARD_SHADER_MISSING": case "MODEL_INSTANCE_FAILED":
                case "UNPACK_SKIN_UNSUPPORTED": case "PREFAB_SAVE_FAILED": case "PREFAB_SKIN_UNSUPPORTED":
                case "ASSET_ID_UNAVAILABLE": case "BONE_ID_UNAVAILABLE": case "ROOT_ID_UNAVAILABLE":
                case "MANIFEST_NOT_IMPORTED": case "OUTPUT_TASK_INVALID": case "FIRST_APPLY_FAILED":
                case "BONE_ID_NOT_IN_MANIFEST": return error.Message;
            }
        }
        return error.GetType().Name;
    }
    private static void Finish(Report report)
    {
        SessionState.SetString(Phase, "");
        SessionState.SetBool("VAPB_PHYSBONE_CASE", false);
        if (report.pass && File.Exists(ProjectFile("BoundedBlender.json")))
        {
            try { if (BoundedCapture == null) throw new InvalidOperationException(); BoundedCapture(); }
            catch { report.pass = false; report.error = "BOUNDED_CAPTURE_FAILED"; }
        }
        try { File.WriteAllText(ProjectFile("VapbSkinRoundtripResult.json"), JsonUtility.ToJson(report, true)); }
        catch { report.pass = false; }
        Debug.Log(report.pass ? "VAPB_SKIN_ROUNDTRIP_PASS" : "VAPB_SKIN_ROUNDTRIP_FAIL");
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
