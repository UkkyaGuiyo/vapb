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
        public StructuralSummary structuralSummary = new StructuralSummary();
    }

    [Serializable] public sealed class StructuralSummary
    {
        public int objectCount;
        public int transformCount;
        public int animatorCount;
        public int avatarCount;
        public int validAvatarCount;
        public int humanAvatarCount;
        public int skinnedMeshRendererCount;
        public int meshRendererCount;
        public int uniqueMeshCount;
        public int materialSlotCount;
        public int blendShapeCount;
        public int boneReferenceCount;
        public int rootBoneCount;
        public int sourceModelIdentityCount;
        public int originalSourceIdentityCount;
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
        public int blendShapeCount;
        public int boneCount;
        public bool hasRootBone;
        public bool hasAvatar;
        public bool avatarIsHuman;
        public bool avatarIsValid;
        public List<MaterialRecord> materials = new List<MaterialRecord>();
    }

    [Serializable] public sealed class MaterialRecord
    {
        public int slot;
        public string name;
        public string guid;
        public string localFileID;
        public string shaderName;
        public List<TexturePropertyRecord> textureProperties = new List<TexturePropertyRecord>();
    }

    [Serializable] public sealed class TexturePropertyRecord
    {
        public string propertyName;
        public string textureName;
        public string guid;
        public string localFileID;
        public bool resolved;
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
        public string runId = Environment.GetEnvironmentVariable("UNITY_ORACLE_RUN_ID") ?? DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ");
        public string unityVersion = Application.unityVersion;
        public string accessMethod = "unity_2022_3_human_editor";
        public string caseId = "human-run";
        public string checkpoint = "COMPLETE";
        public OracleRun observed;
        public OracleDerived derived = new OracleDerived();
        public List<string> limitations = new List<string>();
        public string observationContext = "UNKNOWN";
        public PackageProvenance packageProvenance = new PackageProvenance();
        public List<CollisionEventRecord> collisionEvents = new List<CollisionEventRecord>();
    }

    [Serializable] public sealed class PackageProvenance
    {
        public string canonicalPath;
        public string packageSha256;
        public int sequenceIndex;
        public int packagesPreviouslyPresent;
        public string baselineId;
        public string baselineHash;
        public bool isolationVerified;
        public string isolationFailureReason;
        public string importStartedAtUtc;
        public string importCompletedAtUtc;
        public string probeStartedAtUtc;
        public string probeCompletedAtUtc;
    }

    [Serializable] public sealed class BaselineManifestHeader
    {
        public string baselineHash;
    }

    [Serializable] public sealed class CollisionEventRecord
    {
        public int packageSequenceIndex;
        public string packagePath;
        public string code;
        public string assetPath;
        public string previousGuid;
        public string currentGuid;
        public string evidence;
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
        private static string pendingObservationContext;
        private static string[] pendingImportedItems = new string[0];
        private static Dictionary<string, string> preImportPathGuids = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        private static List<CollisionEventRecord> pendingCollisionEvents = new List<CollisionEventRecord>();
        private static DateTime pendingImportStartedAtUtc;
        private static DateTime pendingImportCompletedAtUtc;
        private static DateTime pendingProbeStartedAtUtc;
        private static DateTime pendingProbeCompletedAtUtc;
        private static bool pendingPackageCompleted;
        private static bool pendingItemsCompleted;
        private static bool isolatedProbeScheduled;
        public static Action<string> PackageCompletedCallback;
        public static Action<string> PackageFailedCallback;
        public static Action ImportCompletedCallback;
        public static Action ProbeStartedCallback;
        public static Action ProbeCompletedCallback;

        public static void DetachPackageCallbacks()
        {
            AssetDatabase.importPackageCompleted -= OnImportPackageCompleted;
            AssetDatabase.importPackageCancelled -= OnImportPackageCancelled;
            AssetDatabase.importPackageFailed -= OnImportPackageFailed;
            AssetDatabase.onImportPackageItemsCompleted -= OnImportPackageItemsCompleted;
        }

        public static void RetryCurrentPackageImport()
        {
            if (pendingPackageIndex <= 0 || pendingPackageIndex > pendingPackages.Length)
                throw new InvalidOperationException("No current package is available for retry.");
            AssetDatabase.ImportPackage(pendingPackages[pendingPackageIndex - 1], false);
        }

        public static void ContinueAfterPackageFailure()
        {
            if (pendingObservationContext == "ISOLATED_PACKAGE")
                throw new InvalidOperationException("ISOLATION_FAILED: isolated package failure requires disposable project replacement.");
            ImportNextPackageOrProbe();
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
            pendingObservationContext = Environment.GetEnvironmentVariable("UNITY_ORACLE_OBSERVATION_CONTEXT");
            if (string.IsNullOrEmpty(pendingObservationContext)) pendingObservationContext = "UNKNOWN";
            if (pendingPackages.Length == 0)
                throw new InvalidOperationException("At least one package is required for package probing.");
            if (pendingPackages.Length == 1 && pendingObservationContext == "UNKNOWN")
                throw new InvalidOperationException("Package observation requires an explicit observation context.");
            if (pendingPackages.Length > 1 && pendingObservationContext != "MERGED_CORPUS" && pendingObservationContext != "CONTROLLED_COLLISION")
                throw new InvalidOperationException("Multiple-package observation requires explicit MERGED_CORPUS or CONTROLLED_COLLISION context.");
            pendingImportedItems = new string[0];
            pendingCollisionEvents = new List<CollisionEventRecord>();
            pendingImportStartedAtUtc = DateTime.UtcNow;
            pendingImportCompletedAtUtc = default(DateTime);
            pendingProbeStartedAtUtc = default(DateTime);
            pendingProbeCompletedAtUtc = default(DateTime);
            pendingPackageCompleted = false;
            pendingItemsCompleted = false;
            isolatedProbeScheduled = false;
            preImportPathGuids = SnapshotAssetGuids();
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
            AssetDatabase.onImportPackageItemsCompleted += OnImportPackageItemsCompleted;
            ImportNextPackageOrProbe();
        }

        private static void ImportNextPackageOrProbe()
        {
            if (pendingPackageIndex < pendingPackages.Length)
            {
                pendingPackageCompleted = false;
                pendingItemsCompleted = false;
                var package = pendingPackages[pendingPackageIndex++];
                preImportPathGuids = SnapshotAssetGuids();
                pendingImportStartedAtUtc = DateTime.UtcNow;
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
            PackageCompletedCallback?.Invoke(pendingPackages[pendingPackages.Length - 1]);
            AssetDatabase.importPackageCompleted -= OnImportPackageCompleted;
            AssetDatabase.importPackageCancelled -= OnImportPackageCancelled;
            AssetDatabase.importPackageFailed -= OnImportPackageFailed;
            AssetDatabase.onImportPackageItemsCompleted -= OnImportPackageItemsCompleted;
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_NO_EXIT") != "1")
                EditorApplication.Exit(0);
        }

        private static void OnImportPackageCompleted(string packageName)
        {
            pendingPackageCompleted = true;
            pendingImportCompletedAtUtc = DateTime.UtcNow;
            ImportCompletedCallback?.Invoke();
            if (pendingPackages.Length == 1 && pendingObservationContext == "ISOLATED_PACKAGE")
            {
                ScheduleIsolatedProbeIfReady();
                return;
            }
            ScheduleMergedAdvanceIfReady(packageName);
        }

        private static void OnImportPackageItemsCompleted(string[] importedItems)
        {
            pendingImportedItems = importedItems ?? new string[0];
            pendingItemsCompleted = true;
            foreach (var path in pendingImportedItems)
            {
                string previousGuid;
                if (!preImportPathGuids.TryGetValue(path, out previousGuid)) continue;
                var currentGuid = AssetDatabase.AssetPathToGUID(path);
                pendingCollisionEvents.Add(new CollisionEventRecord {
                    packageSequenceIndex = Math.Max(0, pendingPackageIndex - 1),
                    packagePath = pendingPackages != null && pendingPackages.Length > 0 ? pendingPackages[Math.Max(0, pendingPackageIndex - 1)] : null,
                    code = previousGuid == currentGuid ? "PATH_COLLISION" : "GUID_REASSIGNED",
                    assetPath = path,
                    previousGuid = previousGuid,
                    currentGuid = currentGuid,
                    evidence = "public AssetDatabase path/GUID comparison"
                });
            }
            ScheduleIsolatedProbeIfReady();
            ScheduleMergedAdvanceIfReady(null);
        }

        private static void ScheduleMergedAdvanceIfReady(string packageName)
        {
            if (pendingObservationContext == "ISOLATED_PACKAGE" || !pendingPackageCompleted || !pendingItemsCompleted) return;
            if (pendingPackageIndex < pendingPackages.Length)
                PackageCompletedCallback?.Invoke(packageName ?? pendingPackages[pendingPackageIndex - 1]);
            ImportNextPackageOrProbe();
        }

        private static void ScheduleIsolatedProbeIfReady()
        {
            if (!pendingPackageCompleted || pendingImportedItems.Length == 0 || isolatedProbeScheduled) return;
            isolatedProbeScheduled = true;
            EditorApplication.delayCall += ProbeImportedPackageAndFinish;
        }
        private static void OnImportPackageCancelled(string packageName)
        {
            PackageFailedCallback?.Invoke("Unity package import cancelled: " + packageName);
        }

        private static void OnImportPackageFailed(string packageName, string errorMessage)
        {
            PackageFailedCallback?.Invoke("Unity package import failed: " + packageName + " - " + errorMessage);
        }

        private static void ProbeImportedPackageAndFinish()
        {
            isolatedProbeScheduled = false;
            pendingProbeStartedAtUtc = DateTime.UtcNow;
            ProbeStartedCallback?.Invoke();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var filter = pendingPrefabFilter;
            var importedPrefabs = pendingImportedItems
                .Where(path => path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                .Where(path => string.IsNullOrEmpty(filter) || path.IndexOf(filter, StringComparison.OrdinalIgnoreCase) >= 0)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToArray();
            if (importedPrefabs.Length == 0)
                throw new InvalidOperationException("No imported Prefab items were available for isolated package probing.");
            pendingProbeCompletedAtUtc = DateTime.UtcNow;
            WriteProbes(importedPrefabs, pendingOutput);
            ProbeCompletedCallback?.Invoke();
            PackageCompletedCallback?.Invoke(pendingPackages[0]);
            DetachPackageCallbacks();
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_NO_EXIT") != "1")
                EditorApplication.Exit(0);
        }

        private static Dictionary<string, string> SnapshotAssetGuids()
        {
            var snapshot = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var guid in AssetDatabase.FindAssets(""))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (!string.IsNullOrEmpty(path)) snapshot[path] = guid;
            }
            return snapshot;
        }

        private static string PackageSha256(string path)
        {
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return null;
            using (var sha = System.Security.Cryptography.SHA256.Create())
            using (var stream = File.OpenRead(path))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        private static bool VerifyBaselineAttestation(out string failureReason)
        {
            failureReason = null;
            if (Environment.GetEnvironmentVariable("UNITY_ORACLE_ISOLATION_VERIFIED") != "1")
            {
                failureReason = "UNITY_ORACLE_ISOLATION_VERIFIED was not set to 1.";
                return false;
            }
            var manifestPath = Environment.GetEnvironmentVariable("UNITY_ORACLE_BASELINE_MANIFEST");
            var expectedHash = Environment.GetEnvironmentVariable("UNITY_ORACLE_BASELINE_HASH");
            if (string.IsNullOrEmpty(manifestPath) || !File.Exists(manifestPath))
            {
                failureReason = "External baseline manifest is missing.";
                return false;
            }
            if (string.IsNullOrEmpty(expectedHash) || !expectedHash.Equals(expectedHash.ToLowerInvariant(), StringComparison.Ordinal) || expectedHash.Length != 64)
            {
                failureReason = "Baseline hash is not a lowercase SHA-256 value.";
                return false;
            }
            try
            {
                var header = JsonUtility.FromJson<BaselineManifestHeader>(File.ReadAllText(manifestPath));
                if (header == null || !string.Equals(header.baselineHash, expectedHash, StringComparison.Ordinal))
                {
                    failureReason = "External baseline manifest hash does not match UNITY_ORACLE_BASELINE_HASH.";
                    return false;
                }
                return true;
            }
            catch (Exception exception)
            {
                failureReason = "External baseline manifest could not be read: " + exception.Message;
                return false;
            }
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
                envelope.observationContext = pendingObservationContext ?? "UNKNOWN";
                string baselineFailureReason;
                var baselineVerified = VerifyBaselineAttestation(out baselineFailureReason);
                envelope.packageProvenance = new PackageProvenance {
                    canonicalPath = pendingPackages != null && pendingPackages.Length == 1 ? pendingPackages[0] : string.Join(";", pendingPackages ?? new string[0]),
                    packageSha256 = pendingPackages != null && pendingPackages.Length == 1 ? PackageSha256(pendingPackages[0]) : null,
                    sequenceIndex = Math.Max(0, pendingPackageIndex - 1),
                    packagesPreviouslyPresent = pendingObservationContext != "ISOLATED_PACKAGE" ? Math.Max(0, pendingPackageIndex - 1) : 0,
                    baselineId = Environment.GetEnvironmentVariable("UNITY_ORACLE_BASELINE_ID"),
                    baselineHash = Environment.GetEnvironmentVariable("UNITY_ORACLE_BASELINE_HASH"),
                    isolationVerified = baselineVerified,
                    isolationFailureReason = baselineVerified ? Environment.GetEnvironmentVariable("UNITY_ORACLE_ISOLATION_FAILURE_REASON") : baselineFailureReason,
                    importStartedAtUtc = pendingImportStartedAtUtc.ToString("O"),
                    importCompletedAtUtc = (pendingImportCompletedAtUtc == default(DateTime) ? (DateTime?)null : pendingImportCompletedAtUtc)?.ToString("O"),
                    probeStartedAtUtc = (pendingProbeStartedAtUtc == default(DateTime) ? (DateTime?)null : pendingProbeStartedAtUtc)?.ToString("O"),
                    probeCompletedAtUtc = (pendingProbeCompletedAtUtc == default(DateTime) ? (DateTime?)null : pendingProbeCompletedAtUtc)?.ToString("O")
                };
                envelope.collisionEvents = new List<CollisionEventRecord>(pendingCollisionEvents);
                if (envelope.observationContext == "MERGED_CORPUS")
                    envelope.limitations.Add("MERGED_CORPUS: not valid as isolated package evidence.");
                if (envelope.observationContext == "ISOLATED_PACKAGE" && !envelope.packageProvenance.isolationVerified)
                    envelope.limitations.Add("ISOLATION_UNVERIFIED: dedicated fresh-project baseline was not attested.");
                envelope.derived.prefabCount = run.prefabs.Count;
                envelope.derived.objectCount = run.prefabs.Sum(item => item.objects.Count);
                envelope.derived.materialSlotCount = run.prefabs.Sum(item => item.objects.Sum(obj => obj.materials.Count));
                WriteTextAtomically(output, JsonUtility.ToJson(envelope, true));
            }
            else
            {
                WriteTextAtomically(output, JsonUtility.ToJson(run, true));
            }
            Debug.Log("Semantic Oracle wrote " + Path.GetFullPath(output));
        }

        private static void WriteTextAtomically(string output, string content)
        {
            var fullPath = Path.GetFullPath(output);
            if (File.Exists(fullPath)) throw new InvalidOperationException("IMMUTABLE_OUTPUT_ALREADY_EXISTS: " + fullPath);
            var temporary = fullPath + ".tmp";
            try
            {
                File.WriteAllText(temporary, content);
                File.Move(temporary, fullPath);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }

        private static void ProbePrefab(PrefabRecord prefab, string path)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (asset == null) throw new InvalidOperationException("Prefab asset could not be loaded: " + path);
            var scene = EditorSceneManager.NewPreviewScene();
            GameObject root = null;
            try
            {
                root = PrefabUtility.InstantiatePrefab(asset, scene) as GameObject;
                if (root == null) throw new InvalidOperationException("Prefab asset could not be instantiated: " + path);
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
                prefab.structuralSummary = BuildStructuralSummary(prefab);
            }
            finally
            {
                try
                {
                    if (root != null) UnityEngine.Object.DestroyImmediate(root);
                }
                finally
                {
                    if (scene.IsValid()) EditorSceneManager.ClosePreviewScene(scene);
                }
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
            var animator = component as Animator;
            if (animator != null)
            {
                record.hasAvatar = animator.avatar != null;
                record.avatarIsHuman = animator.avatar != null && animator.avatar.isHuman;
                record.avatarIsValid = animator.avatar != null && animator.avatar.isValid;
            }
            var mesh = meshFilter != null ? meshFilter.sharedMesh : (skinned != null ? skinned.sharedMesh : null);
            if (mesh != null) {
                record.meshName = mesh.name;
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out record.meshGuid, out fileId);
                record.meshLocalFileID = fileId.ToString();
                record.blendShapeCount = mesh.blendShapeCount;
            }
            if (skinned != null)
            {
                record.boneCount = skinned.bones == null ? 0 : skinned.bones.Length;
                record.hasRootBone = skinned.rootBone != null;
            }
            if (renderer != null) {
                var materials = renderer.sharedMaterials;
                for (var i = 0; i < materials.Length; i++) {
                    var material = materials[i];
                    var materialRecord = new MaterialRecord { slot = i, name = material == null ? null : material.name };
                if (material != null) {
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out materialRecord.guid, out fileId);
                        materialRecord.localFileID = fileId.ToString();
                        materialRecord.shaderName = material.shader == null ? null : material.shader.name;
                        foreach (var propertyName in material.GetTexturePropertyNames())
                        {
                            var texture = material.GetTexture(propertyName);
                            var property = new TexturePropertyRecord { propertyName = propertyName, resolved = texture != null };
                            if (texture != null)
                            {
                                property.textureName = texture.name;
                                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out property.guid, out fileId);
                                property.localFileID = fileId.ToString();
                            }
                            materialRecord.textureProperties.Add(property);
                        }
                    }
                    record.materials.Add(materialRecord);
                }
            }
            prefab.objects.Add(record);
        }

        private static StructuralSummary BuildStructuralSummary(PrefabRecord prefab)
        {
            var summary = new StructuralSummary { objectCount = prefab.objects.Count };
            var meshes = new HashSet<string>();
            var sources = new HashSet<string>();
            var originalSources = new HashSet<string>();
            foreach (var record in prefab.objects)
            {
                if (record.type == typeof(Transform).FullName) summary.transformCount++;
                if (record.type == typeof(Animator).FullName)
                {
                    summary.animatorCount++;
                    if (record.hasAvatar) summary.avatarCount++;
                    if (record.avatarIsValid) summary.validAvatarCount++;
                    if (record.avatarIsHuman) summary.humanAvatarCount++;
                }
                if (record.type == typeof(SkinnedMeshRenderer).FullName) summary.skinnedMeshRendererCount++;
                if (record.type == typeof(MeshRenderer).FullName) summary.meshRendererCount++;
                if (!string.IsNullOrEmpty(record.meshGuid)) meshes.Add(record.meshGuid + ":" + record.meshLocalFileID);
                if (!string.IsNullOrEmpty(record.sourceGuid)) sources.Add(record.sourceGuid + ":" + record.sourceLocalFileID);
                if (!string.IsNullOrEmpty(record.originalSourceGuid)) originalSources.Add(record.originalSourceGuid + ":" + record.originalSourceLocalFileID);
                summary.materialSlotCount += record.materials.Count;
                summary.blendShapeCount += record.blendShapeCount;
                summary.boneReferenceCount += record.boneCount;
                if (record.hasRootBone) summary.rootBoneCount++;
            }
            summary.uniqueMeshCount = meshes.Count;
            summary.sourceModelIdentityCount = sources.Count;
            summary.originalSourceIdentityCount = originalSources.Count;
            return summary;
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
