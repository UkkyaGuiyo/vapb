# Public Unity A/C/D geometry observer

Diagnostic tooling only. Create a new external project using `prepare_project.py
CONTROL PROJECT`. CONTROL is an existing proven `unity_geometry_probe` output;
the source hashes and diagnostic UV marker hashes are checked before A/C capture.
Use Unity **2022.3.22f1** with `-batchmode -nographics -projectPath PROJECT
-executeMethod VapbGeometryAbcd.RunAC -logFile PROJECT/UnityAC.log`.

`A_unmarked.json` observes the original source asset. `A_stamped.json` observes
the same imported asset with the diagnostic CP index UV channel. `C_unmarked.fbx`
and `C_stamped.fbx` use Unity's official `ModelExporter.ExportObject` public API
with `ExportModelOptions.ExportFormat = ExportFormat.Binary`; all other official
options retain defaults. BlendShape renderer weights are fixed to zero for C.
`UnityACStatus.json` records editor/exporter versions, result, output hashes, and
warning/error counts during the executed method. Inspect the safe aggregate of
the complete Editor log separately for compilation/startup warnings/errors.

Put Blender outputs `D0.fbx` and `D1.fbx` in the external project root, then run
`VapbGeometryAbcd.RunD` with a separate log file. It captures `D0.json` and
`D1.json`; `UnityDStatus.json` records the executed method result.

`VapbGeometryAbcd.RunCReimport` checks raw C file hashes against the export
status and captures `C_Unity_unmarked.json` and `C_Unity_stamped.json`, with
`UnityCReimportStatus.json`. This measures the official export/reimport boundary
independently of Blender import. Do not infer a scale correction from exporter
constants: actual FBX GlobalSettings and imported object transforms are authority.
`RunACCapturesOnly` checks Source/stamped input hashes and resnapshots A without
writing C exports; this keeps previously captured official C FBX hashes unchanged.

`RunWeightControl` is a bounded diagnostic on the isolated D1 importer. It records
actual public API defaults, an attempted zero threshold in Standard mode, then
Custom mode with zero, and only when that fails to remain zero after import, a
positive threshold of `1e-8`. Each capture records actual imported influences;
the `D1_no_trim` filename describes the requested control, not a success claim.
Assigned and post-import settings are recorded separately, and original importer
metadata bytes/settings and the input FBX hash must be restored. Public 2022.3
API source accepts thresholds in 0..1 and warns that Standard ignores the value:
https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/2022.3/Modules/AssetPipelineEditor/Public/ModelImporting/ModelImporter.bindings.cs
The small-weight public fixture must demonstrate actual retention before any
corresponding private diagnostic is run.

Schema `vapb-geometry-abcd-public-api-1` captures each Renderer/sharedMesh
occurrence using actual public API object references and asset GUID/local ID.
Hierarchy paths are diagnostic sibling-index paths, never source matching keys.
Mesh local/world positions, normals, tangents, per-channel UV values, submesh
indices/topology, bounds, all BlendShape frames/deltas, renderer shape weights,
variable bone influences, bindposes, bone transforms, and renderer matrices are
included. All observed Shape renderer weights are fixed zero. Public `BakeMesh`
captures both scale modes in world space. `baked_true_world_positions` uses the
existing repository observer contract `BakeMesh(true)` then `TransformPoint`.
`cpu_weighted_world_positions` independently sums public bone world matrices
times bindpose times source vertex, weighted by each variable bone influence.
The earlier `baked_world_positions` remains the false-scale diagnostic only;
it is not sufficient by itself to conclude that a skin is broken.
Arrays indexed by triangle vertex indices provide per-corner evidence.
Matrices use Unity's column-major single-index convention. CP values decode only
the proven diagnostic marker; invalid or absent values remain `-1` with a count.
Bone names/indices/paths and Shape names/indices are diagnostic observations,
and do not prove source semantic identity. Mesh vertex counts do not establish
correspondence. Shape and skin identity require their own authoritative bridge.

Official package: `com.unity.formats.fbx` **5.1.1**, Unity Companion License;
its package manifest requires Unity 2020.3+. Official docs:
https://docs.unity3d.com/Packages/com.unity.formats.fbx@5.1/api/UnityEditor.Formats.Fbx.Exporter.ExportModelOptions.html
https://docs.unity3d.com/Packages/com.unity.formats.fbx@5.1/api/UnityEditor.Formats.Fbx.Exporter.ModelExporter.html

The initial 4.2.1 public API trial emitted ASCII FBX. Its format settings are
internal; the 5.1 public options API was selected to emit Blender-readable binary
FBX without private APIs or post-export geometry conversion. The initial trial
is retained externally in `nonplanar_unity/ascii_4_2_1/`.
