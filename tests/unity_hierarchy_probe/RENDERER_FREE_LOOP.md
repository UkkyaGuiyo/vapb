# Autonomous hierarchy loop — renderer-free nested occurrences

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
