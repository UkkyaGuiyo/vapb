# R2 candidate: transport material identity across native submesh ordering

Status: design candidate only. No product implementation, payload migration, or Unity execution is included.

## Finding

`export/final_state_package.py` stores `material_slots` in Blender source order. `_stage_fbx` copies the object and mesh, but leaves their source material handles and display names in the FBX. `VapbFinalStateFinalizer.ResolveMaterials` reconstructs the source-order array. `Apply` checks the native array length and then assigns that source-order array. Equal counts do not prove that a native submesh still represents the same material identity.

The isolated Blender probe models three face groups with source identities A/B/C and a native importer permutation A/C/B. Native face assignments remain A/B/C before finalization. The current source-order replacement produces A/C/B. This is a synthetic behavior model, not execution of Unity's ModelImporter or Finalizer.

## Proposed transport contract

Introduce an explicit final-state task/transport version, for example `BUILD_EXPORTED_STATIC_V2` with material transport version 2. V2 carries per-export material labels derived from `export_material_id`.

The current `_id` helper validates and reuses an existing custom ID, rejecting duplicate existing IDs in its source collection. If no ID exists, it returns a UUID4 for this export but does not persist it on the source Material. The export-local pointer map means repeated slots referencing the same Blender Material datablock receive the same ID. The current helper does not explicitly collision-check newly generated UUIDs against the complete export set. V2 must validate uniqueness across distinct material records before publishing the package. IDs are package-scoped transport labels, not durable user metadata.

For the disposable FBX only, create one temporary material copy per distinct source Blender Material datablock, set its exact name to its `export_material_id`, and assign it to the copied mesh. Leave source material names/properties untouched. Verify every carrier name is exact before export; fail closed if the name cannot be represented exactly, including auto-suffixing. Remove temporary material, mesh, and object copies in `finally`.

In Unity, configure the generated model's `ModelImporter.materialName` as `BasedOnMaterialName`, reimport synchronously, and require each native `sharedMaterials` element to carry an exact known `export_material_id`. Resolve each label through the existing manifest entry, preserving GUID, local file ID, asset hash, and dependency validation. Build the final renderer array in native order. Repeated Apply must resolve the same mapping from the same package. Do not trim, normalize, or fall back to source indices/display names.

## Slot policy

- Repeated source slots referencing the same Material may repeat the same transport label. Permit this only when the native carrier label multiplicities exactly equal the source slot multiplicities.
- Retain the existing structural equality: native renderer material count must equal source slot count and native mesh submesh count. Reject importer collapse, slot loss, reordering ambiguity, or any count mismatch; do not infer equivalence from a set of labels alone.
- Reject every unused source slot before FBX export by checking polygon `material_index` usage. Return an actionable message to remove the unused slot in Blender and re-export. Never silently omit it.
- Reject conflicting/duplicate ID declarations across distinct material records. Repeated native labels are valid only for repeated source slots with the exact same expected multiplicity. Null, missing, unknown, changed, or auto-suffixed labels fail closed before Prefab creation.

## Compatibility and user data

A V1 task has no material transport labels. Reject it with result code `FINAL_STATE_REEXPORT_REQUIRED` and an explicit message: “This package predates material identity transport. Re-export the final-state package from Blender, then import the new package. Existing assets were not rewritten.” Do not edit or migrate old archives, rename source materials, or automatically rewrite existing Prefabs. If an existing generated Prefab occupies the destination, preserve it and require manual review before retrying.

Keep object-marker uniqueness, model GUID/hash, source Material GUID/local-ID/hash and dependency checks, static Mesh/UV/modifier limits, and triangle staging. This design adds correspondence validation and does not relax mesh, identity, Bone, or Cloth guards.

## Acceptance conditions for a future Unity run

1. A public synthetic package imports with an intentional native submesh/material permutation; every face retains its expected material identity, not merely the expected array length.
2. A second Apply is idempotent and confirms the same native-order mapping.
3. Repeated same-material slots pass only at exact multiplicity. Any unused slot rejects before FBX export with an actionable instruction.
4. Missing, changed, suffixed, unknown, or multiplicity-mismatched labels reject before creating or replacing a Prefab. Existing GUID/local-ID, hash, object-marker, renderer-ambiguity, and dependency controls continue to reject invalid inputs.
5. Source Blender material names/properties, original Unity Material asset bytes, and generated FBX payload bytes are not mutated by finalization. The generated ModelImporter configuration and resulting imported data may change intentionally to use `BasedOnMaterialName`.
6. V1 tasks return the explicit re-export error and leave existing assets untouched.

The Blender roundtrip probe is a bounded control: it checks exact carrier names in Blender 5.2.1 FBX bytes and Blender reimport face assignments. It does not test the product staging cleanup path, Unity label behavior, or Unity Finalizer. The RED probe models the source-order replacement only. Those Unity behaviors remain mandatory integration checks before shipping this design.

Review status: unapproved design candidate; Unity validation has not been performed. No source-preservation or V1-rejection guarantee is implemented by this document.
