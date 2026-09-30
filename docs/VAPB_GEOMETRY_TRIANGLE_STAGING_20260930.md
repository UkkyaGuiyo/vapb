# Production Blender triangle staging — 2026-09-30

Status: production triangle staging verified in the bounded supported export
scope. Starting HEAD: `7b41b30fb45f4a1f6d60bf1e7bc8827a15127d24`.
No overall Geometry/VAPB completion claim.

## Original request / acceptance

Promote the proven D1 behavior into existing supported production exports.
Blender final loop-triangle connectivity is frozen in disposable export copies;
Unity must not choose a different output n-gon diagonal. Do not imitate Unity's
source triangulation, inject Unity geometry, or change the edited scene.
Preserve vertices, UVs, Material face assignments, supported Skin/Shape data,
Armature relations and existing Export ID/Recipe properties. Verify public
controls, fresh Unity, the same four real cases, rollback and persistence.

## Minimal production change

`export/triangle_staging.py` supplies one shared context for triangle Mesh data
on disposable Objects and one isolated-scene wrapper for direct FBX exports.
The frozen topology is copied from actual `Mesh.calc_loop_triangles` vertex and
loop indices. No guessed tessellation algorithm or source identity matching is
introduced. Vertex ordering and coordinates stay fixed; loop UV/corner normals
are copied through the actual triangle-loop map. Material indices and data/OBJECT
slot links, weights, relative Shape deltas/properties, Mesh/Key ID properties and
actual Armature handles are retained. Rig data is cloned in direct scene staging.

Call sites: direct `export_fbx`, static final-state UnityPackage, receipt-based
static/Skin UnityPackage, and FBX/Material-sidecar export with cleanup on/off.
Existing export presets and supported-input checks are retained. The preset
still uses `use_mesh_modifiers=False`; no arbitrary modifier baking, animated
state, absolute Shape animation or constraint-restoration support is claimed.
A direct selected Skin export requires its actual Armature in the selected scope;
missing binding targets fail closed. Outside-scope parents are detached while
keeping world placement; selected parent relations are remapped by handles.

Selection/view-layer overrides explicitly select the staged Objects. Merely
changing the scene/view layer did not direct the FBX operator to the copied Mesh
in the initial control; the regression checks actual output triangles.
Every context restores/removes temporary data on exception as well as success.

A separate source-immutability RED exposed successful final-state export writing
new Object/Material Export IDs back to live data. Those three writeback lines
are removed: existing author-assigned IDs are reused; otherwise labels live only
in the output FBX/Recipe. Fresh export plus reopen checks source fields unchanged
and validates the actual Recipe ID in output FBX. Replay controls explicitly
author fixture IDs before baseline to verify existing-ID reuse. New labels are
not promised stable across separate exports of a scene with no assigned IDs.

## Public RED / production GREEN

Blender **5.2.1**, fresh isolated Unity **2022.3.22f1**.
The historical raw preset remains the D0 negative control. Production D1 is
exported from n-gon Objects without the experiment's manual `explicit_copy`.
Actual FBX PolygonVertexIndex entries are all explicit triangles for D1.

| Control | D0 topology / sampled surface | Production D1 |
|---|---|---|
| Nonplanar n-gons | RED / RED | EXACT / sampled EXACT |
| Planar n-gon | RED / sampled EXACT | EXACT / sampled EXACT |
| Concave | EXACT / sampled EXACT | EXACT / sampled EXACT |
| Triangle-only | EXACT / sampled EXACT | EXACT / sampled EXACT |
| Skin + three Shape frames | EXACT / sampled EXACT | EXACT / sampled EXACT |

All five D1 connectivity, winding, vertex correspondence, raw slot-number
partitions and existing UV-set comparisons are EXACT. Public Skin/Bone-label
bindings are EXACT; three transported Shape frames are EXACT with maximum delta
error **8.17e-8**. Normal rounded-set difference on nonplanar remains recorded.
These ten imports have zero errors/warnings, no invalid CP markers; all output
FBX hashes match their actual fresh Unity observations. Surface uses the unchanged
**3e-5** diagnostic threshold and finite samples, not continuous-surface proof.

## Same bounded real inputs

The same private selection values as the prior experiment were checked exactly:
one earlier EXACT and three earlier topology MISMATCH Skins. Original source
blend hash remains unchanged. Four production D1 cases have connectivity and
sampled base surface **4/4 EXACT**; D0 retains connectivity **1/4** and sampled
surface **3/4**. Baked positions **4/4 EXACT** in both routes. Two measured Shape
cases EXACT, two N/A. Eight imports: zero errors, two unclassified import warnings.
Private identities, assets, snapshots and raw logs stay outside Git.

Two small-weight Skin binding REDs and two genuine normal differences remain.
Rounded UV differences, tangent UNKNOWN, arbitrary deformation UNKNOWN and the
original nonplanar Import-preview surface RED are separate findings. This patch
fixes none of those. The original 14 EXACT / 20 source Geometry MISMATCH verdict
is not overwritten by Blender-authoritative export fidelity.

## Material partitions: numbers are not identity

Three real cases report different numeric Blender slot/Unity submesh partitions,
also present in the previous experimental D1. They are not silently converted to
GREEN. A public first-party three-Material fixture intentionally uses face slots
0,2,1. Exact output revision plus labels assigned to actual temporary Material
handles proves each CP triangle's effective Material association through public
`Renderer.sharedMaterials`, independently of submesh numbering. Original Material
names, appearance, counts and ordering are not correspondence evidence.

The public control retains its numeric slot RED while actual Material-label
partitions are EXACT in D0 and production D1. Wrong-binding and missing-label
negative controls reject. Fresh private label controls prove production D1 effective Material partitions
**4/4 EXACT**, while raw numeric slot partitions remain **1/4 EXACT**. All eight
label-control imports have zero errors and two repeated baseline warnings; the
exact same four selections and source blend hash are checked. Before/after
private memory observations and actual source Material handles also stay unchanged. This proves effective Material
partition correspondence; it does not assert that Unity preserves Blender slot
indices, unused slots or all finalizer/Material semantics.

## Source invariants and regression evidence

- Actual Mesh/Skin/Shape/UV/OBJECT Material synthetic staging control checks
  source Object/data pointers, shared Mesh occurrence, geometry/Shape values,
  selection/active Object, parent/Armature binding, IDs and data-block inventory.
  Success and injected FBX exception leave the source state unchanged.
- Existing final-state/static receipt call sites emit triangles; injected exporter
  failures restore original pointers/selection/inventory. Saved/reopened source
  retains n-gons, Shape deltas and actual Armature relation.
- Existing static, Skin and final-state UnityPackage exports PASS, including
  save/reopen; final-state package additionally exports after a separate reopen.
- Fresh Unity 2022.3.22f1 Finalizer after no-ID source export PASS: one Recipe
  task/export marker, 24 Mesh vertices and UV entries, Material GUID and Texture
  restored, no source Model/Prefab, repeated Apply succeeds. Exit 0; no compiler
  errors/warnings; exact package hash and first-party helper bytes verified.
- Cleanup-enabled and disabled sidecar exports PASS success/failure preservation.
- Hierarchy TR-001..005 and Bone receipt rename/reopen/export regression PASS.
- Repository-parent Python **487 PASS**; compileall PASS. Two bounded read-only
  scope reviews PASS. The subsequent three-line source-ID writeback removal was
  parent-verified with an actual RED/GREEN and replay regression; no third scope
  review was launched, respecting the review limit.
- Deferred Shader, Material naming and phase-2 replay regressions PASS with
  explicit fixture IDs; fresh no-ID source export/reopen is a separate control.
  Earlier Hierarchy 1,274 EXACT / Shape identity 171 EXACT are historical counts,
  not fresh full-private-import results from this patch.

[Public production measurements](../tests/unity_geometry_abcd_probe/production_triangle_measurements.json)
contain synthetic observations and exact output hashes only.

## Exact next action

Investigate the public small-Bone-weight importer RED independently of triangle
staging: prove actual retained influences through public Unity API before any
production workaround or private importer mutation.
