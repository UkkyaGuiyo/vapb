using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// One author-owned normal input; declared source material identifiers, no Prefab.
public static class VapbRemappedModelInput
{
    const string ModelPath = "Assets/PublicMaterialSource/Input.fbx";
    [Serializable] public sealed class Row { public string sourceIdentifier, materialGuid, materialFileId; public int triangleCount; }
    [Serializable] public sealed class Report { public string status = "FAIL", unityVersion, error; public Row[] declaredRemaps, observedRendererMaterials; public bool noPrefab, originalMetaRestored; }
    public static void Prepare()
    {
        string project = Directory.GetParent(Application.dataPath).FullName;
        string metaPath = Path.Combine(project, ModelPath + ".meta");
        byte[] originalMeta = File.ReadAllBytes(metaPath);
        var report = new Report { unityVersion = Application.unityVersion };
        ModelImporter importer = null;
        try
        {
            if (Application.unityVersion != "2022.3.22f1") throw new InvalidOperationException("VERSION");
            importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            if (importer.GetExternalObjectMap().Count != 0) throw new InvalidOperationException("INITIAL_REMAP_NOT_EMPTY");
            string[] guids = { "64f92a1bd9b35a040bf9e2c6d200b34c", "0318f358e4c29034aa90cc8c50b58a93", "eb805efb35118044db5e74adc652673a" };
            var embedded = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Material>().ToArray();
            report.declaredRemaps = new Row[3];
            for (int i = 0; i < 3; i++)
            {
                string key = "Public fixture material " + i;
                if (embedded.Count(m => m.name == key) != 1) throw new InvalidOperationException("SOURCE_IDENTIFIER_NOT_UNIQUE");
                Material target = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guids[i]));
                if (target == null || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(target, out string guid, out long id) || guid != guids[i] || id != 2100000) throw new InvalidOperationException("TARGET_IDENTITY");
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), key), target);
                report.declaredRemaps[i] = new Row { sourceIdentifier = key, materialGuid = guid, materialFileId = id.ToString() };
            }
            importer.SaveAndReimport();
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            Renderer[] renderers = model.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length != 1) throw new InvalidOperationException("RENDERER_COUNT");
            Renderer renderer = renderers[0];
            Mesh mesh = renderer is SkinnedMeshRenderer skin ? skin.sharedMesh : renderer.GetComponent<MeshFilter>().sharedMesh;
            if (mesh.subMeshCount != 3 || renderer.sharedMaterials.Length != 3) throw new InvalidOperationException("SUBMESH_COUNT");
            report.observedRendererMaterials = new Row[3];
            for (int i = 0; i < 3; i++)
            {
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(renderer.sharedMaterials[i], out string guid, out long id) || !guids.Contains(guid) || id != 2100000) throw new InvalidOperationException("APPLIED_REMAP_IDENTITY");
                report.observedRendererMaterials[i] = new Row { materialGuid = guid, materialFileId = id.ToString(), triangleCount = mesh.GetTriangles(i).Length / 3 };
            }
            report.noPrefab = AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/PublicMaterialSource" }).All(g => AssetDatabase.GUIDToAssetPath(g).EndsWith(".fbx"));
            if (!report.noPrefab) throw new InvalidOperationException("PREFAB_PRESENT");
            AssetDatabase.ExportPackage(new[] { ModelPath, "Assets/PublicMaterialSource/Material0.mat", "Assets/PublicMaterialSource/Material1.mat", "Assets/PublicMaterialSource/Material2.mat" }, Path.Combine(project, "RemappedInput.unitypackage"), ExportPackageOptions.IncludeDependencies);
            report.status = "PASS_NORMAL_REMAPPED_MODEL_INPUT_PREPARED";
        }
        catch (Exception e) { report.error = e.GetType().Name + ":" + e.Message; }
        finally
        {
            if (importer != null)
            {
                foreach (var key in importer.GetExternalObjectMap().Keys.ToArray()) importer.RemoveRemap(key);
                importer.SaveAndReimport();
            }
            File.WriteAllBytes(metaPath, originalMeta);
            report.originalMetaRestored = File.ReadAllBytes(metaPath).SequenceEqual(originalMeta);
            using (var writer = new StreamWriter(new FileStream(Path.Combine(project, "RemappedInputObservation.json"), FileMode.CreateNew))) writer.Write(JsonUtility.ToJson(report, true));
            Debug.Log("VAPB_REMAPPED_MODEL_INPUT=" + report.status);
            EditorApplication.Exit(report.status.StartsWith("PASS") && report.originalMetaRestored ? 0 : 1);
        }
    }
}
