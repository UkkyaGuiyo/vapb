# Coordinate and material partition intervention

Project: `vapb`
Branch/base: `feature/r2-material-slot-reorder` / `18dc330739d770c47a96f4bc0a1c0c930a08574e` (local parent, still unpushed)
Purpose: isolate importer response to authored axis, unit, transform, and reflection changes without changing VAPB product behavior.

## Fixed contract

The fixture has six asymmetric, non-coplanar triangles and three intended material identities, with two triangles per identity. Each of the eighteen triangle corners receives a distinct UV0 U tag. A face is identified by its three U tags; the complete UV coordinates and face winding remain captured for later comparison. Equal face counts prevent count matching from identifying material membership.

The fixed world-point comparison is:

```text
P_blender(case, cornerTag) = W_blender(case, mesh) * V_blender(case, cornerTag)
P_unity(case, cornerTag)   = W_unity(case, renderer) * V_unity(case, cornerTag)
delta(case, cornerTag)      = P_unity - P_blender
```

The comparator reports the largest absolute component of `delta` against a fixed `1e-4` tolerance. It does not fit a transform or select a basis from the output. The same UV corner tags also identify face material membership. Expected membership comes from the pinned input geometry. Unity records imported Material GUID/local file ID and imported asset path. In this self-authored fixture only, the imported Material is joined to its raw FBX Material object UID through a unique fixture-authored material name; this is an experiment key, not independent evidence of how a general FBX/Unity pipeline maps materials.

Unity and Blender receive the same FBX with axis import controls fixed to `axis_up=Y`, `axis_forward=-Z`, and global import scale `1`. The generator changes only the named source factor between each fixture and baseline. It records raw FBX GlobalSettings and Model TRS, verifies the real axis and UnitScaleFactor changes, and preserves material object UIDs across every file.

## Seven conditions

| Case | Single source intervention |
|---|---|
| `baseline` | Baseline: axes `Y/-Z`, units `NONE`, identity Model TRS |
| `axis_only` | FBX export axes `up=Z`, `forward=Y` |
| `unit_only` | Scene units `METRIC`, length scale `0.01`; raw FBX UnitScaleFactor changes from `100` to approximately `1` |
| `translation_only` | Model translation `(2.25, -0.75, 1.125)` |
| `rotation_only` | Model Euler XYZ `(23, -37, 61)` degrees |
| `positive_nonuniform_scale_only` | Model scale `(2, 0.5, 1.5)` |
| `negative_scale_only` | Model scale `(-1, 1, 1)` |

`bakeAxisConversion` is held constant as an importer setting. The input directory contains only self-authored FBXs. No SDK, external package, or VAPB import/finalizer action is required.

## Observations

Capture both sides separately. Blender records imported mesh vertices/normals, polygon material index, UV corners, material UID joined by the unique fixture material name, and full object local/world matrices. The Unity Editor runner records Unity version, effective ModelImporter settings, hierarchy local/world matrices, mesh GUID/file ID, vertices/normals/UV0, submesh triangles, renderer Material GUID/file ID/path, and the fixture-name-joined raw FBX Material UID.

The comparator keys corners by authored U tags and compares world positions; it checks each face material identity, not aggregate slot counts. It requires exact case and manifest receipts, successful Unity capture status, zero Unity errors and unmatched faces, all eighteen expected corner tags, three corners per face, embedded material asset identities, and complete non-null importer settings that remain constant across all seven cases. It parses Unity Vector2/Vector3 JSON objects and Blender numeric arrays. No missing observation is converted into a pass.

This measures only the selected Blender/Unity versions and these seven synthetic inputs. It does not prove a universal Unity import rule or choose a VAPB product mapping, fixed slot swap, or fallback policy. Any failed case is the stopping boundary; adding another intervention requires a separate review.

## Current preparation evidence

- Spec and comparator tests: 13/13 pass using Blender 5.2.1 bundled Python with bytecode writes disabled, including missing-vector, non-finite transform, duplicate case, missing-corner, failed-capture, bad receipt, and missing importer-setting rejection cases.
- Final generator rerun: 7 FBXs generated. The raw FBX metadata validator confirmed distinct axis and unit values and identical material UIDs. Final fixture and output hashes are in `../evidence/coordinate_intervention_20261007/final/execution.json`.
- Blender 5.2.1 import capture: 7/7 cases have unique corner UV identities and the expected per-face material partition.
- Unity 2022.3.22f1 Editor runner: compiled offline with the installed Unity Roslyn compiler and Unity managed reference assemblies, zero C# errors. This is a standalone compile check, not an Editor project compile or runtime capture.
- Unity runtime capture and cross-tool coordinate comparison: not run. The new Editor remains on hold for the VHS/Prop run slot.

The runner's terminal path is covered separately without starting Unity: missing `-vapbCoordinateResult`, failure-record serialization error, failure-record write denial plus throwing error reporters, a pre-existing output file, and a deferred import retry. The latter remains byte-for-byte unchanged because both failure recording and normal output use `FileMode.CreateNew`. The exit guard keeps the delayed import retry open when it returns no exit code and invokes exit code 1 on failure paths. Five pure C# guard scenarios pass; these are not a Unity Editor runtime test.

The comparator requires exact case and manifest receipts, successful Unity capture status, zero Unity errors/unmatched faces, all eighteen expected corner tags, three corners per triangle, material asset identities, and complete non-null importer settings that remain constant across all seven cases. It parses Unity `Vector2`/`Vector3` JSON objects and Blender numeric arrays. Importer settings are checked for completeness and consistency, not prescribed to a product-wide policy. Raw Model TRS is recorded for diagnosis but is not independently validated as a complete matrix decomposition. The unique fixture-name material join is limited to these authored names and does not establish a reusable material-identity fallback.

Development failures retained in the task run records: the first Blender capture left orphan material datablocks, so subsequent imported material names acquired `.001` suffixes and identity resolution returned unproven. Clearing the run-owned orphan meshes/materials fixed that harness issue. The first raw manifest attempt also failed JSON serialization on byte-valued FBX properties; strict UTF-8 decoding fixed it. An earlier unit intervention did not change raw `UnitScaleFactor`; generator validation caught it before accepting the fixture. The accepted generator uses common `FBX_SCALE_UNITS` and `apply_unit_scale=true` settings, which produce baseline `100` and the unit intervention approximately `1`.
