using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable]
public sealed class AliasOracleId
{
    public string guid;
    public string fileId;
    public string assetPath;
}

[Serializable]
public sealed class AliasOracleRenderer
{
    public string role;
    public AliasOracleId renderer;
    public AliasOracleId sourceAtContainer;
    public AliasOracleId originalSource;
    public AliasOracleId slotZeroMaterial;
    public List<AliasOracleId> correspondingSourceChain = new List<AliasOracleId>();
}

[Serializable]
public sealed class AliasOracleModification
{
    public string propertyPath;
    public AliasOracleId target;
    public AliasOracleId objectReference;
}

[Serializable]
public sealed class AliasOracleCase
{
    public string caseName;
    public string prefabPath;
    public string prefabType;
    public List<AliasOracleRenderer> renderers = new List<AliasOracleRenderer>();
    public List<AliasOracleModification> materialModifications = new List<AliasOracleModification>();
}

[Serializable]
public sealed class AliasOracleReport
{
    public string unityVersion;
    public AliasOracleId modelR1;
    public AliasOracleId modelR2;
    public AliasOracleId modelR1Owner;
    public AliasOracleId modelR2Owner;
    public AliasOracleId modelR1Transform;
    public AliasOracleId modelR2Transform;
    public AliasOracleId modelR1Mesh;
    public AliasOracleId modelR2Mesh;
    public List<AliasOracleCase> cases = new List<AliasOracleCase>();
}

public static class VapbAliasOracle
{
    const string Root = "Assets/Oracle";
    const string ModelPath = Root + "/Model.fbx";
    const string VariantPath = Root + "/ModelVariant.prefab";
    const string ContainerPath = Root + "/Container.prefab";
    const string DirectPath = Root + "/E0_Direct.prefab";
    const string AliasPath = Root + "/E1_Alias.prefab";
    const string UnrelatedPath = Root + "/E2_Unrelated.prefab";

    static AliasOracleId Id(Object obj)
    {
        if (obj == null) return new AliasOracleId();
        string guid;
        long fileId;
        bool valid = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out guid, out fileId);
        return new AliasOracleId {
            guid = valid ? guid : "",
            fileId = valid ? fileId.ToString(System.Globalization.CultureInfo.InvariantCulture) : "",
            assetPath = AssetDatabase.GetAssetPath(obj)
        };
    }

    static Material Material(string label, Color color)
    {
        string folder = Root + "/Materials";
        if (!AssetDatabase.IsValidFolder(folder)) AssetDatabase.CreateFolder(Root, "Materials");
        string path = folder + "/" + label + ".mat";
        var prior = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (prior != null) return prior;
        var shader = Shader.Find("Standard");
        if (shader == null) throw new Exception("Standard shader unavailable");
        var created = new Material(shader);
        created.color = color;
        AssetDatabase.CreateAsset(created, path);
        return created;
    }

    static MeshRenderer OriginalRenderer(GameObject instance, MeshRenderer original)
    {
        var matches = instance.GetComponentsInChildren<MeshRenderer>(true)
            .Where(renderer => PrefabUtility.GetCorrespondingObjectFromOriginalSource(renderer) == original)
            .ToArray();
        if (matches.Length != 1) throw new Exception("Original Renderer relation is not unique");
        return matches[0];
    }

    static void SetSlot(MeshRenderer renderer, Material material)
    {
        var values = renderer.sharedMaterials;
        if (values.Length == 0) values = new Material[1];
        values[0] = material;
        renderer.sharedMaterials = values;
        PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
    }

    static GameObject Save(GameObject instance, string path)
    {
        var asset = PrefabUtility.SaveAsPrefabAsset(instance, path);
        if (asset == null) throw new Exception("Prefab save failed");
        Object.DestroyImmediate(instance);
        return asset;
    }

    static AliasOracleRenderer Observe(string role, Renderer renderer)
    {
        var row = new AliasOracleRenderer { role = role, renderer = Id(renderer) };
        row.sourceAtContainer = Id(PrefabUtility.GetCorrespondingObjectFromSourceAtPath(renderer, ContainerPath));
        row.originalSource = Id(PrefabUtility.GetCorrespondingObjectFromOriginalSource(renderer));
        var materials = renderer.sharedMaterials;
        row.slotZeroMaterial = materials.Length > 0 ? Id(materials[0]) : new AliasOracleId();
        Object current = renderer;
        var seen = new HashSet<Object>();
        for (int step = 0; step < 8 && current != null && seen.Add(current); ++step) {
            var source = PrefabUtility.GetCorrespondingObjectFromSource(current);
            if (source == null) break;
            row.correspondingSourceChain.Add(Id(source));
            current = source;
        }
        return row;
    }

    static AliasOracleCase ObserveCase(string label, string path, bool hasHolder)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var row = new AliasOracleCase {
            caseName = label, prefabPath = path,
            prefabType = PrefabUtility.GetPrefabAssetType(asset).ToString()
        };
        var loaded = PrefabUtility.LoadPrefabContents(path);
        try {
            if (hasHolder) {
                var holder = loaded.GetComponent<OracleRefHolder>();
                if (holder == null || holder.targetRenderer == null ||
                    holder.otherRenderer == null || holder.siblingRenderer == null)
                    throw new Exception("Container references were not preserved");
                row.renderers.Add(Observe("target_R1", holder.targetRenderer));
                row.renderers.Add(Observe("other_R1", holder.otherRenderer));
                row.renderers.Add(Observe("sibling_R2", holder.siblingRenderer));
            } else {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
                var modelR1 = model.GetComponentsInChildren<MeshRenderer>(true)
                    .Single(renderer => renderer.gameObject.name == "R1");
                row.renderers.Add(Observe("direct_R1", OriginalRenderer(loaded, modelR1)));
            }
            var modifications = PrefabUtility.GetPropertyModifications(loaded);
            if (modifications != null) {
                foreach (var modification in modifications) {
                    if (modification.propertyPath != "m_Materials.Array.data[0]") continue;
                    row.materialModifications.Add(new AliasOracleModification {
                        propertyPath = modification.propertyPath,
                        target = Id(modification.target),
                        objectReference = Id(modification.objectReference)
                    });
                }
            }
        } finally {
            PrefabUtility.UnloadPrefabContents(loaded);
        }
        return row;
    }

    public static void Run()
    {
        try {
            if (Application.unityVersion != "2022.3.22f1")
                throw new Exception("Wrong Unity Editor version");
            EditorSettings.serializationMode = SerializationMode.ForceText;
            AssetDatabase.Refresh();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (model == null) throw new Exception("Synthetic FBX missing");
            var modelR1 = model.GetComponentsInChildren<MeshRenderer>(true)
                .Single(renderer => renderer.gameObject.name == "R1");
            var modelR2 = model.GetComponentsInChildren<MeshRenderer>(true)
                .Single(renderer => renderer.gameObject.name == "R2");
            var baseMaterial = Material("Base", Color.gray);
            var changedMaterial = Material("Changed", Color.red);

            var direct = (GameObject)PrefabUtility.InstantiatePrefab(model);
            SetSlot(OriginalRenderer(direct, modelR1), changedMaterial);
            Save(direct, DirectPath);

            var modelVariant = (GameObject)PrefabUtility.InstantiatePrefab(model);
            SetSlot(OriginalRenderer(modelVariant, modelR1), baseMaterial);
            SetSlot(OriginalRenderer(modelVariant, modelR2), baseMaterial);
            var variantAsset = Save(modelVariant, VariantPath);

            var container = new GameObject("Container");
            var left = (GameObject)PrefabUtility.InstantiatePrefab(variantAsset);
            var right = (GameObject)PrefabUtility.InstantiatePrefab(variantAsset);
            left.name = "Nested_A";
            right.name = "Nested_B";
            left.transform.SetParent(container.transform, false);
            right.transform.SetParent(container.transform, false);
            var holder = container.AddComponent<OracleRefHolder>();
            holder.targetRenderer = OriginalRenderer(left, modelR1);
            holder.otherRenderer = OriginalRenderer(right, modelR1);
            holder.siblingRenderer = OriginalRenderer(left, modelR2);
            var containerAsset = Save(container, ContainerPath);

            var alias = (GameObject)PrefabUtility.InstantiatePrefab(containerAsset);
            SetSlot((MeshRenderer)alias.GetComponent<OracleRefHolder>().targetRenderer, changedMaterial);
            Save(alias, AliasPath);

            var unrelated = (GameObject)PrefabUtility.InstantiatePrefab(containerAsset);
            SetSlot((MeshRenderer)unrelated.GetComponent<OracleRefHolder>().otherRenderer, changedMaterial);
            Save(unrelated, UnrelatedPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            var report = new AliasOracleReport {
                unityVersion = Application.unityVersion, modelR1 = Id(modelR1), modelR2 = Id(modelR2),
                modelR1Owner = Id(modelR1.gameObject), modelR2Owner = Id(modelR2.gameObject),
                modelR1Transform = Id(modelR1.transform), modelR2Transform = Id(modelR2.transform),
                modelR1Mesh = Id(modelR1.GetComponent<MeshFilter>().sharedMesh),
                modelR2Mesh = Id(modelR2.GetComponent<MeshFilter>().sharedMesh)
            };
            report.cases.Add(ObserveCase("E1_E4_E5", AliasPath, true));
            report.cases.Add(ObserveCase("E2", UnrelatedPath, true));
            report.cases.Add(ObserveCase("E0", DirectPath, false));
            var output = Path.Combine(Directory.GetParent(Application.dataPath).FullName,
                                      "AliasOracleReport.json");
            File.WriteAllText(output, JsonUtility.ToJson(report, true));
            Debug.Log("ALIAS_ORACLE_CREATED cases=" + report.cases.Count);
            EditorApplication.Exit(0);
        } catch (Exception error) {
            Debug.LogError("ALIAS_ORACLE_FAILURE " + error.GetType().Name + ": " + error.Message);
            EditorApplication.Exit(1);
        }
    }
}
