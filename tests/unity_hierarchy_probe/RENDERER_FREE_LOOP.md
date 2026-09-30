# Autonomous hierarchy loop — renderer-free nested occurrences

## Hierarchy Parity acceptance closure — 2026-09-30

**HIERARCHY_PARITY: GOAL_VERIFIED for the measured supported scope.**
**GEOMETRY: RED; aggregate comparator remains RED on the real input.**
This closure follows PRODUCT_SPEC.md, Mandatory Hierarchy Parity Milestone:
semantic parents/Transforms, Renderer ownership, Skin/Bone relationships,
occurrence multiplicity and save/reopen. Identical Unity triangulation was an
extra acceptance condition introduced during debugging; it is now reported as
separate geometry corroboration, without deleting or passing its failures.
The five required native relationship dimensions have zero unsupported or
unexplained mismatches in the measured public and real compositions.

- Original Majun: hierarchy **53 EXACT / GREEN**, geometry **1 EXACT / GREEN**.
- Deferred-component/outside-weighted-root and authored Bone-pose followups:
  fresh Import and all-Object/all-Bone rename/save/reopen each hierarchy
  **53 EXACT / GREEN**, geometry **1 EXACT / GREEN**.
- First-party nonplanar n-gon fixture: hierarchy **53 EXACT / GREEN**,
  geometry **1 GEOMETRY_MISMATCH / RED**, overall **RED**.
- Representative private exact-byte Unity/normal Blender differential:
  **276 semantic nodes / 275 edges / 34 Skins / 5,440 ordered Bone bindings**.
  Fresh Import and all-Object/all-Bone rename/save/reopen both hierarchy
  **1,274 EXACT / GREEN**: 1,104 node/parent/local/world checks and 170 native
  Renderer-owner/Mesh-receipt/Bone-order/rootBone/representation checks.
  **160** distinct native Bone motion controls corroborate carrier/attachment
  relations. Geometry separately retains **14 EXACT / 20 GEOMETRY_MISMATCH**;
  overall comparator/CLI remains **RED / exit 1**. No surface equivalence claim.
- Exact-revision witness uses Unity public API and original/no-op/stamped/restored
  controls, restored source/meta bytes and native UID receipts. Unity remains
  optional. Names, enumeration order and candidate counts are not identity.
- Six actual Blender corruptions (owner, receipt, Armature target, Bone parent,
  rootBone, attachment) fail hierarchy acceptance: **PASS / process exit 0**.
  Wrong proof-file arguments in two verification attempts were rejected with
  exit 1; corrected immutable evidence paths produced the six-control PASS.
- Python repository-parent full discovery: **458 PASS**, zero failures/errors.
  compileall PASS; final read-only scope review PASS. Previous production
  integration/register/Bone-receipt/Transform checks remain valid; this closure
  changes only comparator tests and documentation, not production behavior.

**UNKNOWN / retained findings:** three private Renderer serialized states contain
seven nonzero blend-shape weights; native Key values retain source-cache state.
Authoritative Unity blend-shape channel to native KeyBlock correspondence is not
proven. This observation does not attribute any of the 20 geometry mismatches.
No private identity, path, source, snapshot or raw log is tracked.

Prior pushed checkpoints: `1e653538eb758215146477b96526265b99438a3f`
(production realization fixes) and `7f09c976f40c7c2515ea676c051bf8a5c533e6df`
(triangle-connectivity negative control and public nonplanar RED).
Old `18.2968` is not a resource percentage; latest measured balance was **80%
remaining**, with no resource-floor blocker. Stop reason is the requested
Hierarchy Parity goal, not synthetic GREEN, a checkpoint or a budget estimate.
No broad Unity/VRC component restoration, main merge, ZIP or Release in this loop.

**Exact next action:** create a public synthetic RED for revision-bound Unity
blend-shape channel to native KeyBlock identity before applying serialized
Prefab weights; keep geometry RED until independently proven or fixed.

Older sections below are historical checkpoints, not the current next action.

## Geometry proof checkpoint — 2026-09-30

**STATUS: hierarchy/native identity proven; nonplanar tessellation remains RED.**
Previous verified implementation checkpoint: `1e653538eb758215146477b96526265b99438a3f`
(feature branch pushed, remote equal, clean at that checkpoint).

- Original Majun and authored Bone-pose synthetic: **53 EXACT / GREEN**.
- New wholly first-party nonplanar polygon fixture: **52 EXACT / 1 native
  representation mismatch**. Exact package SHA-256:
  `fc6bfa0f29b6dba637780320438d6f7b6da7e566966620550bfe8da567f88595`.
  Unity original/no-op/stamped/restored controls, exact package observation,
  witness promotion and normal Blender Import all exit 0. Comparator exits 1.
- Private fresh Import and all-Object/all-Bone rename/save/reopen both:
  **1,254 EXACT / 20 native representation mismatches**. Identity, parent,
  Transform, ordered Bones, rootBone, native frames and motion remain proven.
- Six standard triangulation controls and common fans/ear rules did not
  eliminate differences. FIXED residuals uniquely attribute to 92 nonplanar
  n-gons: 70 convex, 22 concave. Ninety have complete triangle attribution;
  two remain UNKNOWN. Exact raw FBX polygon loops match native loops.
  Active source ShapeKeys explain raw-to-evaluated displacement; evaluated
  referenced points agree with Unity. This does not prove surface equality.
- Public comparator RED showed that equal corner incidence could hide changed
  triangle connectivity. Minimal proof-side fix compares triangle multisets,
  preserving multiplicity and allowing triangle/vertex reorder. Public GREEN
  controls remain GREEN; genuine geometry RED remains RED. No production
  triangulation or witness geometry-copy behavior was introduced.
- Python **456 PASS**, compileall PASS, bounded scope review PASS. Raw private
  evidence remains outside Git. Last authoritative usage: **80% remaining**;
  no resource-floor blocker. This checkpoint is not a stop condition.

**Exact next automatic action:** test documented constrained triangulation on
raw Geometry-local polygons in the small public fixture; only a uniform proven
candidate proceeds to real recheck. If it fails, reassess geometry proof/fix
options against existing product authority rather than fitting private data.

## Hierarchy Parity — exact native Skin bridge checkpoint — 2026-09-30

**CURRENT STATUS: public supported synthetic GREEN; real geometry RED.**
Resume HEAD `db5a1c62abc0f845f7d71078fb64280156e51404`.
Old `18.2968` was a credit balance, not remaining token percentage. Latest official
usage observed **83% remaining**. There is no resource-floor blocker, and this
checkpoint is not a stop condition. Continue the autonomous loop.

Original Majun and deferred-component/outside-weighted-root followup: **53 EXACT /
GREEN**. Authored per-Bone pose followup: public RED before fix, then normal Import
GREEN 53, all-Object/all-Bone rename/save/reopen GREEN 53, six corruption controls
PASS. Unity exact-source original/no-op/stamped/restored controls and FBX/meta
restoration hashes PASS. Source cache Bone state and evaluated Mesh geometry are
unchanged; member rest head/tail/matrix/parent match source exactly. Native
connected children with authored translation require a member-only disconnect;
independent Armature deform data also needs independent Mesh data to prevent
source-cache Bone renames changing member weight channels.

Private identical-byte Unity/Blender differential: **276 nodes / 275 edges / 34
Skins / 5,440 ordered Bone references / 160 distinct native motion controls**.
Comparator: **1,254 EXACT, 20 NATIVE_REPRESENTATION_MISMATCH**. All node, parent,
local/world, owner, Mesh bridge, ordered Bones, rootBone, full native Bone frame
and motion/attachment checks pass. The remaining failures are Geometry evidence.
Independent source-cache versus exact Unity FBX-default observation already has
20 triangle-corner discrepancies before Prefab pose: 14 exact, 14 same-count
multiplicity differences, six count differences. Vertex coverage passes 32 of 34.
Prefab point coverage passes 30 of 34; morph/weight effects are not yet attributed.
These are RED observations, not proof of Geometry corruption or equivalence.
Source surface diagnostics: all referenced corner pointsets match within 1.01e-5;
19 native loose vertices account for the two all-vertex coverage discrepancies.
316 native zero-area triangles have no Unity counterparts. Bidirectional finite
samples nevertheless find 1,495 distances above 3e-5 across 14 Meshes (maximum
0.001919), so corner counts alone cannot establish surface equivalence. Six standard
Blender triangulation controls exited 0 with temporary modifiers restored.
No global mode eliminated differences: FIXED gave 17/34 corner matches but
residual sampled differences on 10 Meshes. No production triangulation change
or false GREEN is claimed.

Python **454 PASS**, compileall and existing Blender integration/Bone receipt/
hierarchy transform regressions PASS. Mandatory scope review PASS. Only generic
code and aggregate findings are tracked; raw private assets, IDs, paths, logs,
.blend and snapshots remain outside Git. Unity remains optional; witness frames
bridge source importer/native rest axes, while Prefab semantics remain serialized
package authority. No broad Unity/VRC component restoration or ZIP/Release.

**Exact next automatic action:** measure source geometry surface differences
independently of triangle-corner multiplicity, isolate actual deformations from
triangulation/degenerate faces, reduce real findings to public RED, then minimal
fix / GREEN / full comparator / real recheck. Do not stop at this checkpoint.

Earlier sections below are historical checkpoints, not current stop authority.


**STATUS: PARTIAL.** Starting HEAD `ba42f957747f0b9d531dd8691e64b2bdf5c09f32`.
Exact phase 1 package revision retained:
`358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098`.

## Completed causal loops

1. **Production RED → fix → GREEN.** Normal Import focused probe observed
   zero renderer-free nested semantic Objects and exited 1. Hierarchy construction
   only iterated direct prefab GO entries; existing model realization did not
   cover transform-only source prefabs. The builder now receives the existing
   source loader/root context/issue list and expands a directly nested,
   transform-only source tree per exact instance edge. It retains source GUID,
   signed GO/Transform IDs, root context and ordered instance edge. No source
   identity is replaced with a guessed Unity-generated occurrence fileID.
   Existing instance TRS resolution is reused; display-name overrides only
   affect labels. The first implementation rejected Unity's diagnostic Euler
   hints; allowing those hints while retaining quaternion authority completed
   the same causal fix. Focused probe now observes two distinct occurrences,
   one source GO identity, one context and their correct semantic parent; exit 0.
2. **Comparator source/occurrence bridge.** Unity's selected-prefab GO IDs are
   not necessarily serialized in the source. Its public source GO identity plus
   ordered prefab-instance handles now bridge the two new Blender occurrences
   to the independent Oracle. Ambiguous bridges reject comparison. Result:
   **12 nodes, 11 edges, 48 EXACT checks** (12 each: nodes, parents, local and
   world matrices), zero MISSING/EXTRA/WRONG_PARENT/multiplicity/transform issues.
3. **Persistence and falsification.** Twelve semantic IDs and the complete
   comparison checks survive actual Object rename, save and reopen. Four
   production builder controls reject ambiguous provider, extra component,
   incomplete TRS and removed GO without creating nested Objects. Eleven
   comparator tests pass, including wrong occurrence edge and duplicate claims.
4. **Next native-Skin boundary investigated.** Two source/native-member Mesh
   Objects and two Armature Objects remain unproven in semantic realization.
   Normal Import was explicitly package-only: no witness supplied and no
   authoritative renderer binding injected. Existing `plan_witness_realizations`
   rejects absent witnesses as WITNESS_MISSING; the integration regression
   explicitly requires user confirmation for its independent synthetic Skin.
   Source projection describes intended Skin state, not actual native ownership.
   No name/order/candidate-count pairing or production Skin patch was introduced.

## Current supported scope and current RED

The new route is bounded to directly nested, transform-only prefab source trees.
Renderer/model sources keep their existing route. Ambiguous provider, incomplete
parent/source TRS, descendant overrides, extra components, structural changes,
cycles or deeper nesting do not acquire invented support. Supported subtree
realization validates parent and source references before creating Objects;
unsupported resolved trees add an issue to the existing occurrence projection.
No parallel identity registry was added. Source/default/native transform
conversion outside this route is unchanged.

Public Unity nodes: **12**. Blender semantic nodes: **12**; semantic edges **11**;
technical wrapper **1**; unmapped native realizations **4**. Two accessory
occurrences remain distinct. Semantic Hips/Spine/attachment Object edges pass;
native Bone correspondence is not inferred from that result.

`renderer_free_comparison.json` records **48 EXACT** and **5
UNSUPPORTED_REPRESENTATION** checks. Those five native Renderer/Mesh/Bone-order/
rootBone/equivalent-representation dimensions are still unimplemented and
unproven; full comparator remains **RED**, not synthetic GOAL_VERIFIED.
Native Renderer/Bone negative controls and full Skin persistence remain pending.

## Executed verification

- Focused Blender 5.2.1 normal Import: RED exit 1 before fix → GREEN exit 0.
- Actual rename/save/reopen: twelve semantic IDs and comparison checks unchanged.
- Four fail-closed production controls: PASS.
- Comparator: eleven tests PASS; native checks retain RED.
- Full Python repository-parent discovery: **449 PASS**, zero failures/errors.
  This includes occurrence projection and prefab instance transform tests.
- `blender_hierarchy_transform_test.py`: PASS, TR_001_005_OK.
- `blender_bone_receipt_test.py`: PASS, two native UID receipts across rename/reload.
- `blender_integration_test.py`: PASS, BLENDER_INTEGRATION_OK.
- Existing nested Prefab transform realization create and separate-process
  reopen: PASS, including two native occurrences sharing Mesh data with distinct
  realization IDs. Its public package was built with existing StagingTree /
  UnityPackageWriter. An initial reopen invocation omitted loading the `.blend`,
  producing zero roots; supplying the `.blend` on Blender's command line passed.
  No production change was made for that invocation error.
- compileall: PASS. Mandatory scope review: PASS; one existing reviewer reused.

Focused reproduction uses `tests/blender_renderer_free_hierarchy_test.py` with
the same four arguments as `tests/blender_hierarchy_snapshot.py` in BASELINE.md.
It keeps raw snapshots, `.blend` files and logs outside Git. All checked-in
identities/results here are public synthetic; no private asset was used.

## Hard-stop convergence

Opening API balance: **18.2968137500**, hard floor **15**. The small 3.2968
margin and unreliable within-turn debit make a new Unity witness generation /
native Skin implementation loop unsafe to budget after this production fix,
independent comparator extension and verification. Stop is resource-floor risk,
not completion of a phase, discovery of RED or creation of a checkpoint.
Actual effective final balance is unconfirmed; unchanged API balance is not
zero-spend evidence. No Astra, ZIP/Release or broad component restoration.

Real UnityPackage differential has **NOT RUN**: prerequisite public supported
Skin comparator/GREEN remains incomplete. No real-input path question is needed.

**Exact next automatic action:** generate and verify an optional Unity public-API
witness for this exact FBX/package/meta revision using the existing witness
probe's no-op/stamped/restored identity controls, then exercise the existing
native realization bridge and compare actual Renderer/Skin/Bone receipt state.
Do not regenerate the input package or pair by names. If the existing witness
schema lacks required ordered bone/rootBone evidence, add the minimum public
regression/schema evidence before claiming equivalence.
