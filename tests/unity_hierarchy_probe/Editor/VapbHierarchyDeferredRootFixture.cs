// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class VapbHierarchyDeferredRootFixture
{
    private const string Phase = "VAPB_DEFERRED_ROOT_FIXTURE_PHASE";
    [Serializable] private sealed class Report
    {
        public string status, package_sha256, source_fbx_sha256, source_meta_sha256, selected_prefab_path;
        public string root_representation;
        public int authored_root_bone_slot, no_op_marker_state, accessory_audio_source_count; public bool authored_bone_pose_override;
    }
    static VapbHierarchyDeferredRootFixture()
    {
        AssetDatabase.importPackageCompleted += Imported;
        if (SessionState.GetString(Phase, "") == "ready") EditorApplication.delayCall += Build;
    }
    private static string Project { get { return Path.GetDirectoryName(Application.dataPath); } }
    public static void Run()
    {
        SessionState.SetString(Phase, "importing");
        AssetDatabase.ImportPackage(Path.Combine(Project, "ExactPackage.unitypackage"), false);
    }
    private static void Imported(string name)
    {
        if (SessionState.GetString(Phase, "") != "importing") return;
        SessionState.SetString(Phase, "ready"); EditorApplication.delayCall += Build;
    }
    public static void Build()
    {
        if (SessionState.GetString(Phase, "") != "ready") return;
        if (EditorApplication.isCompiling || EditorApplication.isUpdating) { EditorApplication.delayCall += Build; return; }
        SessionState.SetString(Phase, "building");
        try
        {
            const string accessoryPath = "Assets/VapbHierarchy/Accessory.prefab";
            const string selectedPath = "Assets/VapbHierarchy/Majun.prefab";
            const string modelPath = "Assets/VapbHierarchy/Model.fbx";
            byte[] originalModel = File.ReadAllBytes(Path.Combine(Project, modelPath));
            byte[] originalMeta = File.ReadAllBytes(Path.Combine(Project, modelPath + ".meta"));
            if (Hash(originalModel) != Hash(File.ReadAllBytes(Path.Combine(Project, "Source.fbx")))
                || Hash(originalMeta) != Hash(File.ReadAllBytes(Path.Combine(Project, "Source.fbx.meta"))))
                throw new InvalidOperationException("EXACT_SOURCE_REVISION_MISMATCH");
            GameObject accessory = PrefabUtility.LoadPrefabContents(accessoryPath);
            try
            {
                if (accessory.GetComponent<VapbHierarchyDeferredFixtureMarker>() != null || accessory.GetComponent<AudioSource>() != null)
                    throw new InvalidOperationException("FIXTURE_ALREADY_CHANGED");
                accessory.AddComponent<VapbHierarchyDeferredFixtureMarker>().fixture_state = 17;
                accessory.AddComponent<AudioSource>().playOnAwake = false;
                PrefabUtility.SaveAsPrefabAsset(accessory, accessoryPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(accessory); }
            GameObject selected = PrefabUtility.LoadPrefabContents(selectedPath);
            try
            {
                SkinnedMeshRenderer skin = selected.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                if (skin.bones.Length != 2 || skin.rootBone != skin.bones[0]) throw new InvalidOperationException("SOURCE_SKIN_FIXTURE_MISMATCH");
                // Legal Unity bounds/root frame outside the weighted Bone array.
                skin.rootBone = selected.transform;
                if (Environment.GetEnvironmentVariable("VAPB_HIERARCHY_FIXTURE_POSE_OVERRIDE") == "1")
                {
                    // Exact authored Skin slot; no cross-runtime matching by labels.
                    skin.bones[1].localPosition += new Vector3(0.025f, 0.03f, -0.015f);
                    skin.bones[1].localRotation *= Quaternion.Euler(8f, -6f, 11f);
                }
                Transform[] instances = selected.GetComponentsInChildren<Transform>(true)
                    .Where(t => PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject)).ToArray();
                if (instances.Length != 2) throw new InvalidOperationException("NESTED_FIXTURE_MISMATCH");
                instances[0].SetSiblingIndex(0); instances[1].SetSiblingIndex(1);
                PrefabUtility.SaveAsPrefabAsset(selected, selectedPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(selected); }
            AssetDatabase.SaveAssets();
            if (Hash(originalModel) != Hash(File.ReadAllBytes(Path.Combine(Project, modelPath)))
                || Hash(originalMeta) != Hash(File.ReadAllBytes(Path.Combine(Project, modelPath + ".meta"))))
                throw new InvalidOperationException("SOURCE_MODEL_CHANGED");
            string output = Path.Combine(Project, "PublicDeferredComponentsRootOverride.unitypackage");
            if (File.Exists(output)) throw new InvalidOperationException("OUTPUT_OCCUPIED");
            AssetDatabase.ExportPackage("Assets/VapbHierarchy", output, ExportPackageOptions.Recurse | ExportPackageOptions.IncludeDependencies);
            File.WriteAllText(Path.Combine(Project, "FixtureResult.json"), JsonUtility.ToJson(new Report {
                status = "CREATED_PUBLIC_API", package_sha256 = Hash(File.ReadAllBytes(output)),
                source_fbx_sha256 = Hash(originalModel), source_meta_sha256 = Hash(originalMeta), selected_prefab_path = selectedPath,
                root_representation = "ROOT_FRAME_OBJECT", authored_root_bone_slot = -1, no_op_marker_state = 17, accessory_audio_source_count = 1,
                authored_bone_pose_override = Environment.GetEnvironmentVariable("VAPB_HIERARCHY_FIXTURE_POSE_OVERRIDE") == "1" }, true));
            SessionState.SetString(Phase, ""); Debug.Log("VAPB_DEFERRED_ROOT_FIXTURE_PASS"); EditorApplication.Exit(0);
        }
        catch { SessionState.SetString(Phase, ""); Debug.LogError("VAPB_DEFERRED_ROOT_FIXTURE_FAIL"); EditorApplication.Exit(1); }
    }
    private static string Hash(byte[] bytes)
    { using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
}
