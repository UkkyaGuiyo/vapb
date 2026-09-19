using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UnitySemanticOracle
{
    [Serializable] public sealed class OracleRun
    {
        public string schemaVersion = "0.1";
        public string oracleVersion = "0.1-prefabinstance-probe";
        public string unityVersion = Application.unityVersion;
        public string runId = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ");
        public string inputAssetPath;
        public string inputAssetGuid;
        public List<PrefabRecord> prefabs = new List<PrefabRecord>();
    }

    [Serializable] public sealed class PrefabRecord
    {
        public string assetPath;
        public string guid;
        public List<ObjectRecord> objects = new List<ObjectRecord>();
        public List<ModificationRecord> propertyModifications = new List<ModificationRecord>();
    }

    [Serializable] public sealed class ObjectRecord
    {
        public string name;
        public string type;
        public string hierarchyPath;
        public string guid;
        public string localFileID;
        public string globalObjectId;
        public string meshName;
        public string meshGuid;
        public string meshLocalFileID;
        public string sourceAssetPath;
        public string sourceGuid;
        public string sourceLocalFileID;
        public string sourceType;
        public string originalSourceAssetPath;
        public string originalSourceGuid;
        public string originalSourceLocalFileID;
        public string originalSourceType;
        public List<MaterialRecord> materials = new List<MaterialRecord>();
    }

    [Serializable] public sealed class MaterialRecord
    {
        public int slot;
        public string name;
        public string guid;
        public string localFileID;
    }

    [Serializable] public sealed class ModificationRecord
    {
        public TargetRecord target = new TargetRecord();
        public string propertyPath;
        public string value;
        public ObjectReference objectReference;
        public string resolutionStatus;
    }

    [Serializable] public sealed class TargetRecord
    {
        public string guid;
        public string localFileID;
        public string resolvedType;
        public string resolvedName;
        public string owningGameObject;
        public string hierarchyPath;
    }

    [Serializable] public sealed class ObjectReference
    {
        public string guid;
        public string localFileID;
        public string type;
    }

    [Serializable] public sealed class OracleEnvelope
    {
        public string schemaVersion = "0.2";
        public string runId = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ");
        public string unityVersion = Application.unityVersion;
        public string accessMethod = "unity_2022_3_human_editor";
        public string caseId = "human-run";
        public string checkpoint = "COMPLETE";
        public OracleRun observed;
        public OracleDerived derived = new OracleDerived();
        public List<string> limitations = new List<string>();
    }

    [Serializable] public sealed class OracleDerived
    {
        public int prefabCount;
        public int objectCount;
        public int materialSlotCount;
    }

    public static class SemanticOracle
    {
        private static string[] pendingPackages;
        private static int pendingPackageIndex;
        private static string pendingPrefabFilter;
        private static string pendingOutput;
        public static Action<string> PackageCompletedCallback;
        public static Action<string> PackageFailedCallback;

        public static void DetachPackageCallbacks()
        {
            AssetDatabase.importPackageCompleted -= OnImportPackageCompleted;
            AssetDatabase.importPackageCancelled -= OnImportPackageCancelled;
            AssetDatabase.importPackageFailed -= OnImportPackageFailed;
        }

        [MenuItem("Tools/Semantic Oracle/Probe Selected Prefab")]
        public static void ProbeSelectedPrefab()
        {
            var path = Selection.assetGUIDs.Length == 0 ? null : AssetDatabase.GUIDToAssetPath(Selection.assetGUIDs[0]);
            if (string.IsNullOrEmpty(path)) throw new InvalidOperationException("Select a prefab asset first.");
            var output = Environment.GetEnvironmentVariable("UNITY_ORACLE_OUTPUT");
            if (string.IsNullOrEmpty(output)) output = Path.Combine("Library", "semantic-oracle.json");
            WriteProbe(path, output);
        }

        public static void BatchProbe()
        {
            var input = Environment.GetEnvironmentVariable("UNITY_ORACLE_INPUT");
            var output = Environment.GetEnvironmentVariable("UNITY_ORACLE_OUTPUT");
            if (string.IsNullOrEmpty(input)) throw new InvalidOperationException("UNITY_ORACLE_INPUT is required.");
            if (string.IsNullOrEmpty(output)) output = Path.Combine("Library", "semantic-oracle.json");
            WriteProbe(input, output);
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_NO_EXIT") != "1")
                EditorApplication.Exit(0);
        }

        public static void BatchImportAndProbe()
        {
            var packages = Environment.GetEnvironmentVariable("UNITY_ORACLE_PACKAGES");
            pendingPackages = string.IsNullOrEmpty(packages)
                ? new string[0]
                : packages.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries);
            pendingPackageIndex = 0;
            pendingPrefabFilter = Environment.GetEnvironmentVariable("UNITY_ORACLE_PREFAB_FILTER");
            pendingOutput = Environment.GetEnvironmentVariable("UNITY_ORACLE_OUTPUT");
            if (string.IsNullOrEmpty(pendingOutput)) pendingOutput = Path.Combine("Library", "semantic-oracle.json");
            if (pendingPackages.Length > 0)
            {
                if (Environment.GetEnvironmentVariable("UNITY_ORACLE_EXTERNAL_PROJECT") != "1")
                    throw new InvalidOperationException("Package probing requires a disposable external Unity project. Set UNITY_ORACLE_EXTERNAL_PROJECT=1.");
                var projectRoot = Directory.GetParent(Application.dataPath).FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                var outputPath = Path.GetFullPath(pendingOutput);
                if (outputPath.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Package probe output must be outside the Unity project.");
            }
            AssetDatabase.importPackageCompleted += OnImportPackageCompleted;
            AssetDatabase.importPackageCancelled += OnImportPackageCancelled;
            AssetDatabase.importPackageFailed += OnImportPackageFailed;
            ImportNextPackageOrProbe();
        }

        private static void ImportNextPackageOrProbe()
        {
            if (pendingPackageIndex < pendingPackages.Length)
            {
                var package = pendingPackages[pendingPackageIndex++];
                Debug.Log("Semantic Oracle importing package " + package);
                AssetDatabase.ImportPackage(package, false);
                return;
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var filter = pendingPrefabFilter;
            var paths = AssetDatabase.FindAssets("t:Prefab")
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => string.IsNullOrEmpty(filter) || path.IndexOf(filter, StringComparison.OrdinalIgnoreCase) >= 0)
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToArray();
            if (paths.Length == 0) throw new InvalidOperationException("No Prefab assets matched the Oracle filter.");
            var output = Environment.GetEnvironmentVariable("UNITY_ORACLE_OUTPUT");
            if (string.IsNullOrEmpty(output)) output = pendingOutput;
            WriteProbes(paths, output);
            AssetDatabase.importPackageCompleted -= OnImportPackageCompleted;
            AssetDatabase.importPackageCancelled -= OnImportPackageCancelled;
            AssetDatabase.importPackageFailed -= OnImportPackageFailed;
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_NO_EXIT") != "1")
                EditorApplication.Exit(0);
        }

        private static void OnImportPackageCompleted(string packageName)
        {
            PackageCompletedCallback?.Invoke(packageName);
            ImportNextPackageOrProbe();
        }
        private static void OnImportPackageCancelled(string packageName)
        {
            PackageFailedCallback?.Invoke("Unity package import cancelled: " + packageName);
        }

        private static void OnImportPackageFailed(string packageName, string errorMessage)
        {
            PackageFailedCallback?.Invoke("Unity package import failed: " + packageName + " - " + errorMessage);
        }

        private static void WriteProbe(string path, string output)
        {
            WriteProbes(new[] { path }, output);
        }

        private static void WriteProbes(IEnumerable<string> paths, string output)
        {
            var selectedPaths = paths.ToArray();
            var run = new OracleRun {
                inputAssetPath = selectedPaths.Length == 1 ? selectedPaths[0] : string.Join(";", selectedPaths),
                inputAssetGuid = selectedPaths.Length == 1 ? AssetDatabase.AssetPathToGUID(selectedPaths[0]) : null
            };
            foreach (var path in selectedPaths)
            {
                var guid = AssetDatabase.AssetPathToGUID(path);
                var prefab = new PrefabRecord { assetPath = path, guid = guid };
                ProbePrefab(prefab, path);
                run.prefabs.Add(prefab);
            }
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_SCHEMA") == "0.2")
            {
                var envelope = new OracleEnvelope { observed = run };
                envelope.derived.prefabCount = run.prefabs.Count;
                envelope.derived.objectCount = run.prefabs.Sum(item => item.objects.Count);
                envelope.derived.materialSlotCount = run.prefabs.Sum(item => item.objects.Sum(obj => obj.materials.Count));
                File.WriteAllText(output, JsonUtility.ToJson(envelope, true));
            }
            else
            {
                File.WriteAllText(output, JsonUtility.ToJson(run, true));
            }
            Debug.Log("Semantic Oracle wrote " + Path.GetFullPath(output));
        }

        private static void ProbePrefab(PrefabRecord prefab, string path)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (asset == null) throw new InvalidOperationException("Prefab asset could not be loaded: " + path);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = PrefabUtility.InstantiatePrefab(asset) as GameObject;
            if (root == null) throw new InvalidOperationException("Prefab asset could not be instantiated: " + path);
            try
            {
                var seenModifications = new HashSet<string>();
                foreach (var component in root.GetComponentsInChildren<Component>(true))
                {
                    AddObject(prefab, component, root);
                    if (component == null) continue;
                    foreach (var mod in PrefabUtility.GetPropertyModifications(component) ?? new PropertyModification[0])
                    {
                        var targetId = mod.target == null ? "null" : mod.target.GetInstanceID().ToString();
                        var key = targetId + "|" + mod.propertyPath;
                        if (seenModifications.Add(key)) prefab.propertyModifications.Add(ReadModification(mod, root));
                    }
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                EditorSceneManager.CloseScene(scene, true);
            }
        }

        private static void AddObject(PrefabRecord prefab, Component component, GameObject root)
        {
            if (component == null) return;
            string guid; long fileId;
            var hasAssetIdentity = AssetDatabase.TryGetGUIDAndLocalFileIdentifier(component, out guid, out fileId);
            var record = new ObjectRecord {
                name = component.name, type = component.GetType().FullName,
                hierarchyPath = HierarchyPath(component.transform, root.transform),
                guid = hasAssetIdentity ? guid : null,
                localFileID = hasAssetIdentity ? fileId.ToString() : null
            };
            record.globalObjectId = GlobalObjectId.GetGlobalObjectIdSlow(component).ToString();
            AddSourceIdentity(record, PrefabUtility.GetCorrespondingObjectFromSource(component), false);
            AddSourceIdentity(record, PrefabUtility.GetCorrespondingObjectFromOriginalSource(component), true);
            var renderer = component as Renderer;
            var meshFilter = component as MeshFilter;
            var skinned = component as SkinnedMeshRenderer;
            var mesh = meshFilter != null ? meshFilter.sharedMesh : (skinned != null ? skinned.sharedMesh : null);
            if (mesh != null) {
                record.meshName = mesh.name;
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out record.meshGuid, out fileId);
                record.meshLocalFileID = fileId.ToString();
            }
            if (renderer != null) {
                var materials = renderer.sharedMaterials;
                for (var i = 0; i < materials.Length; i++) {
                    var material = materials[i];
                    var materialRecord = new MaterialRecord { slot = i, name = material == null ? null : material.name };
                    if (material != null) {
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out materialRecord.guid, out fileId);
                        materialRecord.localFileID = fileId.ToString();
                    }
                    record.materials.Add(materialRecord);
                }
            }
            prefab.objects.Add(record);
        }

        private static void AddSourceIdentity(ObjectRecord record, UnityEngine.Object source, bool original)
        {
            if (source == null) return;
            string guid; long fileId;
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(source, out guid, out fileId);
            var path = AssetDatabase.GetAssetPath(source);
            if (original)
            {
                record.originalSourceAssetPath = path;
                record.originalSourceGuid = guid;
                record.originalSourceLocalFileID = fileId.ToString();
                record.originalSourceType = source.GetType().FullName;
            }
            else
            {
                record.sourceAssetPath = path;
                record.sourceGuid = guid;
                record.sourceLocalFileID = fileId.ToString();
                record.sourceType = source.GetType().FullName;
            }
        }

        private static ModificationRecord ReadModification(PropertyModification modification, GameObject root)
        {
            var result = new ModificationRecord { propertyPath = modification.propertyPath, value = modification.value };
            long fileId;
            var target = modification.target;
            if (target != null) {
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(target, out result.target.guid, out fileId);
                result.target.localFileID = fileId.ToString();
                result.target.resolvedType = target.GetType().FullName;
                result.target.resolvedName = target.name;
                result.target.owningGameObject = target is Component c ? c.gameObject.name : null;
                result.target.hierarchyPath = target is Component tc ? HierarchyPath(tc.transform, root.transform) : null;
                result.resolutionStatus = "RESOLVED_BY_PREFAB_API";
            } else result.resolutionStatus = "UNRESOLVED_NULL_TARGET";
            var reference = modification.objectReference;
            if (reference != null) {
                result.objectReference = new ObjectReference();
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(reference, out result.objectReference.guid, out fileId);
                result.objectReference.localFileID = fileId.ToString();
                result.objectReference.type = reference.GetType().FullName;
            }
            return result;
        }

        private static string HierarchyPath(Transform transform, Transform root)
        {
            var parts = new List<string>();
            for (var current = transform; current != null && current != root; current = current.parent) parts.Add(current.name);
            if (root != null) parts.Add(root.name);
            parts.Reverse();
            return string.Join("/", parts.ToArray());
        }
    }
}
