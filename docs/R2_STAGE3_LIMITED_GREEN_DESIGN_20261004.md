# R2 Stage 3 limited ModelSkin GREEN design

Status: design checkpoint only. No product code is changed by this document.

Repository: `https://github.com/UkkyaGuiyo/vapb`

Branch: `feature/r2-material-slot-reorder`

Design base: `55afc9ed054af6e1d784d5ba931791fdd044715a`

RED evidence: [`tests/evidence/model_skin_topology_boundary_20261004`](../tests/evidence/model_skin_topology_boundary_20261004/README.md)

## Observed behavior and decision

`VapbModelSkinFinalizer.Apply` validates the task batch, prepares the source witness, refreshes edited models, resolves the source occurrence and edited model, calls `CheckSkinCompatibility`, then creates a Variant through `SaveVariant`. In `CheckSkinCompatibility`, the non-Direct ModelSkin route rejects vertex-count changes, changed submesh topology, and any raw index change as `TOPOLOGY_OR_LAYOUT_CHANGED`. `DirectKind` has a separate allowance for changed count/indices and validates streams; its behavior is out of scope and must remain unchanged.

The committed RED run proves one synthetic case: 4 source vertices become 6 final vertices to split two UV seams; both meshes have 2 triangles, 6 indices, one submesh/material and 2 bones. Its result records geometric-face/bone-weight correspondence, UV seam presence and rest/bindpose parity, followed by the expected rejection. It does not record explicit face sequence/winding or per-corner material/weight assertions, and it does not serialize a per-final-vertex source lineage map. Those are GREEN assertions to add, not claims established by the existing RED. Position-only matching is not sufficient proof: coincident, overlapping or degenerate corners can make correspondence ambiguous. Therefore `Kind` must continue rejecting changed topology/index layout until the package carries a validated correspondence. Do not simply delete the normal-Kind guard.

## Proposed limited allow contract

The first GREEN is restricted to the pinned, synthetic seam-split fixture and a corner-preserving vertex duplication/remap. It is not general topology editing support.

- `RESTORE_MODEL_SKIN_VARIANT_V1` only. Require the existing manifest, witness, GUID/hash, occurrence, bone UID and material-transport checks to pass.
- Blender's exported final mesh is authoritative. The Variant's target `SkinnedMeshRenderer.sharedMesh` must reference that exact imported mesh. Never rewrite the source FBX, source Prefab, source mesh, or regenerate final geometry in Unity.
- Require an explicit transport lineage from each final vertex/corner to its source vertex/corner, emitted by the Blender export package. Validate schema/version, complete coverage, integer ranges, uniqueness/duplication rules, triangle-corner coverage and submesh association. Reject absent, duplicate, contradictory or ambiguous lineage. Do not infer correspondence from positions alone.
- For this first fixture, permit only corner-preserving seam duplication: source 4 vertices to final 6, same 2 oriented triangle faces and one triangle submesh, same face/material assignment, exactly two duplicated seam vertices. No face add/remove/reorder, winding change, topology-class change, material partition change, bone hierarchy change or arbitrary vertex remap.
- Compare source/final per-corner positions within a documented tolerance, UV seam values and other supported vertex streams, and normalized skin weights after mapping bone slots by transported source UID. Require finite, correctly sized streams and all indices in range. Require the same unique source bone UID set, root and hierarchy/rest relationship; every final bindpose must match its mapped source bone rest matrix within the existing tolerance. Existing weight checks still require nonempty valid influences and normalized sums.
- First GREEN fixture requires zero blend shapes on both source and final meshes. Any shape/frame addition or difference rejects; remapping shape deltas is out of scope.
- First GREEN fixture requires exactly one triangle submesh and one uniquely resolved material transport binding with unchanged face assignment. Missing/extra/ambiguous material labels, unused declarations, submesh/material cardinality mismatch or changed face-to-material association reject.
- For changed index layout, reject Cloth and any non-whitelisted or unknown component in the entire source Prefab hierarchy that may store vertex/index references. The initial synthetic allowlist is limited to `Transform`, the single target `SkinnedMeshRenderer`, its required bone Transform hierarchy and the explicitly identified VAPB marker/receipt component if present. No additional Renderer, MeshCollider, arbitrary MonoBehaviour, unknown component or missing script anywhere in the Prefab. Expand this allowlist only with a separately specified remap contract and tests.
- Preserve the original source Prefab as the Variant parent. The saved Variant may contain only the target renderer's mesh/bone/material reference overrides (plus Unity root default overrides already tolerated by `VerifyVariant`). No added/removed objects or components, transform changes, sibling renderer changes, or unrelated property modifications.
- Validate every task and all safety conditions before saving any Variant. Rejection must leave source model, source Prefab, manifest and their `.meta`/GUID identities unchanged and leave the Variant absent. A repeated successful Apply must be idempotent and point to the same final mesh.

## Intended code surface (not changed in this checkpoint)

1. Keep `Apply`'s prepare/resolve-all-before-save transaction order; insert the new checks before `SaveVariant`.
2. Split `CheckSkinCompatibility`: retain existing behavior for `DirectKind`; route only normal `Kind` through a new limited topology/correspondence validator. Do not share DirectKind's changed-index exception as the Kind policy.
3. Extend the Blender packager and task/transport validation path with an explicit, versioned lineage contract. Current `Task` hashes cover model, prefab/container and witness/no-op files; they do not generically bind a new manifest field. Either add a separately path+SHA-bound lineage payload with strict root-contained path, uniqueness and authorized-file checks, or embed lineage in an existing SHA-bound witness payload with an explicit schema. Do not treat a new manifest field as authenticated by current hashes.
4. Extend `MeshLayout`/`CaptureLayout` only as required for source corner and face data; add helpers for lineage validation, per-corner semantic comparison and changed-layout component allowlisting.
5. Reuse `ValidateMeshStreams`, `ValidateWeights`, bone UID/rest checks, material-ID resolution and `VerifyVariant` where their existing semantics are sufficient. Add tests if an existing check does not prove a required invariant.
6. Keep `DirectKind` task serialization, compatibility behavior and tests byte-for-byte/behaviorally unchanged.

## Test-first plan

1. **Legacy no-lineage negative:** run the exact package/fixture from the committed evidence and assert it rejects before and after the change. Pin its existing hashes; it must never produce a Variant without lineage.
2. **Limited GREEN assertion:** build a second, lineage-bearing package from the same synthetic 4→6 seam-split fixture and independently pin its package/inventory hashes. Assert same two oriented faces and order, per-corner UV/position/material identity, per-corner bone-weight equivalence, bone UID/root/rest/bindpose parity, and exact authoritative imported final mesh reference. These explicit corner/order/material assertions extend what the current RED evidence records.
3. **Source-layout preservation regression:** hash source FBX + `.meta`, source Prefab + `.meta`, manifest + `.meta`; capture Prefab GUID/local IDs, hierarchy/transforms/components and sibling renderers; after Apply and reload require all source hashes/identities unchanged, source layout untouched, Variant parent is the original Prefab, no added/removed objects/components and only the target skin binding overrides.
4. **Idempotency:** second Apply preserves Variant bytes/GUID and source hashes without creating another asset or changing overrides.
5. **Lineage negatives:** absent/old lineage schema, out-of-range source or final corner, incomplete coverage, duplicate/conflicting mapping, ambiguous geometric match and degenerate triangle all reject before Variant creation.
6. **Geometry/index negatives:** added/removed/reordered face, winding change, changed face/material assignment, non-triangle topology, bad submesh/material count, negative/out-of-range/malformed index, nonfinite position/normal/tangent/color/UV/bounds reject.
7. **Skin negatives:** missing/zero/invalid influence, invalid bone index, nonfinite/unnormalized weight, missing/duplicate/unknown bone UID, changed root/hierarchy/rest matrix or bindpose reject.
8. **Unsupported data negatives:** any nonzero/new/changed blend shape, Cloth, extra renderer/MeshCollider, unknown or missing-script component on affected subtree, and missing/ambiguous material transport identity reject before Variant creation.
9. **DirectKind compatibility control:** run existing DirectKind positive and negative cases unchanged; add a focused unchanged-behavior assertion if no current test covers changed vertex/index layout. No DirectKind expectation is relaxed by the limited Kind GREEN.

## SOL review and open gate

SOL reviewed `VapbModelSkinFinalizer.cs`, the committed RED evidence and this draft. Review agreed with keeping DirectKind separate, validating before save, preserving the source Prefab and using a narrow component allowlist. Review corrected three scope points incorporated above: current task hashes do not bind a new manifest field; RED does not assert face order/winding or per-corner material/weight equivalence; and the current pinned no-lineage package must remain a negative control while a second, lineage-bearing package is the future GREEN input. SOL identified the decisive blocker: the RED evidence has no serialized vertex lineage. Until lineage is present and GREEN/negative controls pass in Unity, implementation must retain rejection for changed Kind indices. This checkpoint records a design proposal; it does not claim implementation or GREEN.
