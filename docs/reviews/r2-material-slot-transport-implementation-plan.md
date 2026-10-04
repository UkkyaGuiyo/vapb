# R2 implementation plan: material identity transport

Status: plan for review. Product implementation has not started. The approved design candidate defines intended behavior; it does not mean any guard or V1 rejection is implemented.

## Scope and invariants

Work only in `feature/r2-material-slot-reorder`. Preserve the two existing local Blender probes unchanged. Do not touch the canonical checkout or private campaign. Do not migrate, rewrite, or auto-repair V1 payloads or existing Prefabs. Keep source identity, model/hash/dependency validation, renderer/object-marker ambiguity rejection, mesh/topology/staging cleanup, Bone, and Cloth guards.

`export_material_id` remains package-scoped: reuse and validate an existing ID; generate missing IDs without persisting them to the Blender source; share the ID for repeated slots referencing the same Material datablock. Check uniqueness across distinct export Material records, including generated values. A repeated native label is valid only with the exact expected slot multiplicity. Require source slot count = native renderer material count = native mesh submesh count. Reject unused source slots before FBX staging.

## Stage 1 — exporter contract RED/GREEN

- **RED:** Add focused tests for repeated source slots sharing an ID, distinct materials having distinct IDs, generated-ID set uniqueness, existing duplicate-ID rejection, and unused-slot rejection before FBX staging.
- **GREEN:** Implement preflight and package-scoped uniqueness checks. Do not write generated IDs or temporary labels onto source materials.
- **Verify:** Snapshot source material names/properties/IDs before success and failure paths; confirm byte/state equivalence afterward. An unused slot returns actionable remove-and-re-export guidance.

## Stage 2 — temporary FBX carriers RED/GREEN

- **RED:** Exercise the actual staging path: exact carrier labels in exported FBX; source scene unchanged; name mismatch/auto-suffix rejected; cleanup after success and induced export failure. Preserve the existing Blender roundtrip probe as a separate bounded control.
- **GREEN:** Copy each distinct source Material once, set the disposable copy's exact name to its export ID, assign only to copied mesh data, validate names, and clean object/mesh/material copies in `finally`.
- **Verify:** Check repeated-slot label multiplicity and exported payload bytes. The existing label roundtrip result alone is not proof that product staging uses or cleans these carriers correctly.

## Stage 3 — V2 payload and Unity label resolution RED/GREEN

- **RED:** Cover explicit V2 serialization and reject missing, null, unknown, renamed, suffixed, duplicate/conflicting declarations, collapsed slots, and wrong label multiplicities. Cover V1 with `FINAL_STATE_REEXPORT_REQUIRED` and actionable re-export instructions.
- **GREEN:** Add the explicit task/transport version. Set generated `ModelImporter.materialName` to `BasedOnMaterialName`, reimport synchronously, resolve exact native labels through existing material records and GUID/local-ID/hash/dependency validation, then build the renderer array in native order. Do not add a fallback to slot order or display names.
- **Verify:** All invalid layouts and V1 requests stop before Prefab create/replace. Existing archive, Material assets, and Prefab remain byte/state unchanged on rejection. Importer `.meta` changes needed for `BasedOnMaterialName` are intentional and should be recorded separately.

## Stage 4 — Apply behavior and guard regression

- **RED:** Demonstrate the existing source-order failure under a known A/B/C to A/C/B native permutation; then show identity-based native-order mapping preserves face-level material identity. Cover first and repeat Apply, repeated labels at exact multiplicity, and mismatches failing before Prefab writes.
- **GREEN:** Apply only the validated mapping. Keep source object marker, model identity/hash, renderer cardinality, static mesh/topology, dependency, staging cleanup, Bone, and Cloth checks intact.
- **Verify:** Existing rejection tests plus focused new tests pass. The two existing local probes remain unmodified and available.

## Stage 5 — Unity integration and release gate

Run a public synthetic package in the supported Unity Editor/importer. Verify native label preservation with `BasedOnMaterialName`, face-level identity on first Apply and repeat Apply, exact repeated-slot multiplicity, unused-slot rejection, malformed-label rejection before Prefab mutation, V1 non-mutation, and the existing identity/topology/Bone/Cloth guards. Confirm source Blender Materials, original Unity Material bytes, FBX package payload, and existing Prefabs are unchanged where specified; separately record intentional generated ModelImporter metadata/imported-data changes.

**Release gate:** Unity integration is mandatory. Blender probes and Python tests cannot establish Unity ModelImporter naming behavior or Finalizer correctness. If Unity cannot run or any integration case fails, stop before release and report the gap; do not claim the implementation is verified or ship it.

## Deferred

No automatic V1 migration, user-data rewriting, source Material renaming, canonical-checkout operation, private-campaign operation, commit, or push is authorized by this plan alone.
