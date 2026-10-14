// SPDX-License-Identifier: GPL-3.0-or-later
// First-party fixture setup only. No exporter internals or automatic roundtrip repair.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class VrmParityCreateSource
{
    const string Folder = "Assets/Fixture";
    const string Model = Folder + "/Source.fbx";
    static readonly string[] Roles = { "Hips", "Spine", "Chest", "Neck", "Head",
        "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
        "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot" };
    [Serializable] public class Ref { public string guid; public long fileId; }
    [Serializable] public class Influence { public int vertex, bone, bits; public float weight; }
    [Serializable] public class FaceSet { public int slot; public int[] indices; }
    [Serializable] public class Shape { public string diagnosticName; public float[] deltas; public int frameCount; public float frameWeight, defaultValue; }
    [Serializable] public class Bone { public string diagnosticName, path, parentPath; public float[] localToWorld, localMatrix; public Ref nativeRef, parentRef; }
    [Serializable] public class Snapshot
    {
        public string unityVersion, phase, materialState, cState, prefabType, colorSpace;
        public bool avatarValid, avatarHuman;
        public string[] requiredRoles, mappedRoles;
        public float[] vertices, uv, normals, tangents, worldVertices, bindposes;
        public Influence[] influences; public FaceSet[] submeshes; public Shape[] shapes; public Bone[] hierarchy;
        public Ref modelRef, meshRef, prefabRef, variantRef, avatarRef; public Ref[] materialRefs, textureRefs;
        public Ref rootBoneRef, variantSourceRef, rendererRef, rendererTransformRef;
        public Ref[] skinBoneRefs; public float[] rendererWorldMatrix;
    }
    static Ref Reference(UnityEngine.Object value)
    {
        if (value == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string guid, out long id))
            throw new InvalidOperationException("NATIVE_ASSET_REFERENCE_UNRESOLVED");
        return new Ref { guid = guid, fileId = id };
    }
    static float[] Flat(IEnumerable<Vector3> values) => values.SelectMany(v => new[] { v.x, v.y, v.z }).ToArray();
    static float[] Matrix(Matrix4x4 m) => Enumerable.Range(0, 16).Select(i => m[i / 4, i % 4]).ToArray();
    static string PathOf(Transform t, Transform root) => t == root ? "" : AnimationUtility.CalculateTransformPath(t, root);
    static string Disk(string relative) => System.IO.Path.GetFullPath(System.IO.Path.Combine(Application.dataPath, "..", relative));

    public static void Run()
    {
        // Reject before entering any write/exit failure path. Caller supplies the exact
        // parent-allocated root, and the marker exists only in the newly owned project.
        var expected = Environment.GetEnvironmentVariable("VAPB_PARITY_OWNED_PROJECT");
        if (string.IsNullOrEmpty(expected) || !string.Equals(Disk("."), System.IO.Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase)
            || new DirectoryInfo(Disk(".")).Name != "unity-parity"
            || !File.Exists(Disk(".vrm-parity-owner")) || File.ReadAllText(Disk(".vrm-parity-owner")).Trim() != "VAPB-VRM-Parity")
            throw new InvalidOperationException("EXACT_OWNED_COMPARISON_PROJECT_REQUIRED");
        GameObject instance = null;
        try
        {
            var assets = new[] { "SourceAvatar.prefab", "SourceAvatar.asset", "SourceVariant.prefab", "Diagnostic.png",
                "OriginalMaterial0.mat", "OriginalMaterial1.mat", "OriginalMaterial2.mat" };
            if (assets.Any(name => File.Exists(Disk(Folder + "/" + name)) || File.Exists(Disk(Folder + "/" + name + ".meta")))
                || new[] { "source-native.json", "source.unitypackage", "source-failure.txt" }.Any(name => File.Exists(Disk(name))))
                throw new InvalidOperationException("SOURCE_OUTPUT_OR_PARTIAL_RUN_ALREADY_EXISTS");
            if (!File.Exists(Disk(Model))) throw new InvalidOperationException("FIRST_PARTY_FBX_MISSING");
            PlayerSettings.colorSpace = ColorSpace.Linear;
            var importer = AssetImporter.GetAtPath(Model) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("MODEL_IMPORTER_MISSING");
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.importAnimation = false; importer.importBlendShapes = true;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.Import;
            importer.weldVertices = false; importer.meshCompression = ModelImporterMeshCompression.Off;
            importer.globalScale = 1; importer.useFileScale = true;
            importer.SaveAndReimport();
            instance = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Model));
            PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            instance.name = "ParitySource";
            var transforms = instance.GetComponentsInChildren<Transform>(true);
            if (transforms.GroupBy(t => t.name).Any(g => g.Count() != 1))
                throw new InvalidOperationException("AUTHORING_ROLE_NAME_NOT_UNIQUE");
            var human = Roles.Select(role => {
                var native = transforms.SingleOrDefault(t => t.name == role);
                if (native == null) throw new InvalidOperationException("DECLARED_ROLE_MISSING:" + role);
                var humanIndex = (int)(HumanBodyBones)Enum.Parse(typeof(HumanBodyBones), role);
                return new HumanBone { boneName = native.name, humanName = HumanTrait.BoneName[humanIndex],
                    limit = new HumanLimit { useDefaultValues = true } };
            }).ToArray();
            var required = Enumerable.Range(0, HumanTrait.BoneCount).Where(HumanTrait.RequiredBone)
                .Select(i => HumanTrait.BoneName[i]).ToArray();
            if (required.Except(human.Select(h => h.humanName)).Any())
                throw new InvalidOperationException("REQUIRED_HUMAN_MAPPING_MISSING");
            var description = new HumanDescription { human = human,
                skeleton = transforms.Select(t => new SkeletonBone { name = t.name, position = t.localPosition,
                    rotation = t.localRotation, scale = t.localScale }).ToArray(),
                upperArmTwist = .5f, lowerArmTwist = .5f, upperLegTwist = .5f, lowerLegTwist = .5f,
                armStretch = .05f, legStretch = .05f, feetSpacing = 0, hasTranslationDoF = false };
            var avatar = AvatarBuilder.BuildHumanAvatar(instance, description);
            var eligible = avatar != null && avatar.isValid && avatar.isHuman;
            if (!eligible) throw new InvalidOperationException("UNITY_HUMANOID_NOT_ELIGIBLE");
            avatar.name = "ParitySourceAvatar"; AssetDatabase.CreateAsset(avatar, Folder + "/SourceAvatar.asset");
            var animator = instance.GetComponent<Animator>() ?? instance.AddComponent<Animator>();
            animator.avatar = avatar; animator.applyRootMotion = false;
            var skin = instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var mesh = skin.sharedMesh;
            if (mesh.subMeshCount != 3) throw new InvalidOperationException("THREE_SOURCE_PARTITIONS_REQUIRED");
            var shader = Shader.Find("Standard"); if (shader == null) throw new InvalidOperationException("BUILTIN_SHADER_MISSING");
            var texture = new Texture2D(2, 2); texture.SetPixels(new[] { Color.red, Color.green, Color.blue, Color.white }); texture.Apply();
            File.WriteAllBytes(Disk(Folder + "/Diagnostic.png"), texture.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(texture);
            AssetDatabase.ImportAsset(Folder + "/Diagnostic.png", ImportAssetOptions.ForceSynchronousImport);
            var nativeTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Diagnostic.png");
            var colors = new[] { new Color(.8f, .12f, .08f, 1), new Color(.1f, .7f, .2f, 1), new Color(.08f, .2f, .85f, 1) };
            var materials = colors.Select((color, index) => {
                var material = new Material(shader) { name = "OriginalMaterial" + index, color = color, mainTexture = nativeTexture };
                AssetDatabase.CreateAsset(material, Folder + "/OriginalMaterial" + index + ".mat"); return material;
            }).ToArray();
            skin.sharedMaterials = materials;
            var prefab = PrefabUtility.SaveAsPrefabAsset(instance, Folder + "/SourceAvatar.prefab");
            UnityEngine.Object.DestroyImmediate(instance); instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            var variant = PrefabUtility.SaveAsPrefabAsset(instance, Folder + "/SourceVariant.prefab");
            UnityEngine.Object.DestroyImmediate(instance); instance = null; AssetDatabase.SaveAssets();
            if (PrefabUtility.GetPrefabAssetType(variant) != PrefabAssetType.Variant)
                throw new InvalidOperationException("VARIANT_NOT_CREATED");
            var variantSource = PrefabUtility.GetCorrespondingObjectFromSource(variant);
            if (variantSource != prefab) throw new InvalidOperationException("VARIANT_SOURCE_RELATION_UNRESOLVED");
            var originalSkin = variant.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
            var beforeMeshRef = Reference(mesh); var afterMeshRef = Reference(originalSkin.sharedMesh);
            if (beforeMeshRef.guid != afterMeshRef.guid || beforeMeshRef.fileId != afterMeshRef.fileId)
                throw new InvalidOperationException("SOURCE_MESH_REFERENCE_CHANGED");
            mesh = originalSkin.sharedMesh;
            var all = mesh.GetAllBoneWeights(); var counts = mesh.GetBonesPerVertex(); var influences = new List<Influence>();
            try { int offset = 0; for (int vertex = 0; vertex < mesh.vertexCount; vertex++)
                for (int n = 0; n < counts[vertex]; n++) { var w = all[offset++];
                    influences.Add(new Influence { vertex = vertex, bone = w.boneIndex, weight = w.weight,
                        bits = BitConverter.ToInt32(BitConverter.GetBytes(w.weight), 0) }); } }
            finally { all.Dispose(); counts.Dispose(); }
            var snapshot = new Snapshot { unityVersion = Application.unityVersion, phase = "C1_SOURCE_CREATED_NOT_ROUNDTRIP",
                avatarValid = avatar.isValid, avatarHuman = avatar.isHuman, requiredRoles = required,
                mappedRoles = human.Select(h => h.humanName).ToArray(), vertices = Flat(mesh.vertices),
                worldVertices = Flat(mesh.vertices.Select(originalSkin.transform.TransformPoint)),
                bindposes = mesh.bindposes.SelectMany(Matrix).ToArray(),
                uv = mesh.uv.SelectMany(v => new[] { v.x, v.y }).ToArray(), normals = Flat(mesh.normals),
                tangents = mesh.tangents.SelectMany(t => new[] { t.x, t.y, t.z, t.w }).ToArray(), influences = influences.ToArray(),
                submeshes = Enumerable.Range(0, mesh.subMeshCount).Select(i => new FaceSet { slot = i, indices = mesh.GetIndices(i) }).ToArray(),
                shapes = Enumerable.Range(0, mesh.blendShapeCount).Select(i => { var delta = new Vector3[mesh.vertexCount];
                    if (mesh.GetBlendShapeFrameCount(i) != 1 || originalSkin.GetBlendShapeWeight(i) != 0)
                        throw new InvalidOperationException("SINGLE_FRAME_ZERO_DEFAULT_CONTROL_REQUIRED");
                    mesh.GetBlendShapeFrameVertices(i, 0, delta, null, null);
                    return new Shape { diagnosticName = mesh.GetBlendShapeName(i), deltas = Flat(delta), frameCount = 1,
                        frameWeight = mesh.GetBlendShapeFrameWeight(i, 0), defaultValue = originalSkin.GetBlendShapeWeight(i) }; }).ToArray(),
                hierarchy = variant.GetComponentsInChildren<Transform>(true).Select(t => new Bone {
                    diagnosticName = t.name, path = PathOf(t, variant.transform),
                    parentPath = t.parent == null ? null : PathOf(t.parent, variant.transform),
                    localToWorld = Matrix(t.localToWorldMatrix), localMatrix = Matrix(Matrix4x4.TRS(t.localPosition, t.localRotation, t.localScale)),
                    nativeRef = Reference(t), parentRef = t.parent == null ? null : Reference(t.parent) }).ToArray(),
                modelRef = Reference(AssetDatabase.LoadAssetAtPath<GameObject>(Model)), meshRef = Reference(mesh),
                prefabRef = Reference(prefab), variantRef = Reference(variant), avatarRef = Reference(avatar),
                materialRefs = materials.Select(Reference).ToArray(), textureRefs = new[] { Reference(nativeTexture) },
                rootBoneRef = Reference(originalSkin.rootBone), colorSpace = PlayerSettings.colorSpace.ToString(),
                variantSourceRef = Reference(variantSource), rendererRef = Reference(originalSkin),
                rendererTransformRef = Reference(originalSkin.transform), rendererWorldMatrix = Matrix(originalSkin.transform.localToWorldMatrix),
                skinBoneRefs = originalSkin.bones.Select(Reference).ToArray(),
                materialState = "ORIGINAL_UNITY_STANDARD_MATERIALS_AND_TEXTURE_CREATED",
                cState = "SDK_COMPONENTS_AND_FX_MENU_CONSTRAINTS_NOT_AUTHORED",
                prefabType = PrefabUtility.GetPrefabAssetType(variant).ToString() };
            File.WriteAllText(Disk("source-native.json"), JsonUtility.ToJson(snapshot, true));
            AssetDatabase.ExportPackage(Folder, Disk("source.unitypackage"), ExportPackageOptions.Recurse | ExportPackageOptions.IncludeDependencies);
            EditorApplication.Exit(0);
        }
        catch (Exception e) { if (!File.Exists(Disk("source-failure.txt"))) File.WriteAllText(Disk("source-failure.txt"), e.ToString());
            Debug.LogException(e); EditorApplication.Exit(1); }
        finally { if (instance != null) UnityEngine.Object.DestroyImmediate(instance); }
    }
}
