# VAPB Avatar Delivery and Dependency Closure Design

- Status: planning artifact only; product implementation and execution remain paused.
- Project: VAPB
- Repository: https://github.com/UkkyaGuiyo/vapb
- Branch at authoring: `feature/r2-material-slot-reorder`
- Verified base: `cf45a3ec95af853c009fa446eaf76f8c5ea9af3b`
- Work root: `C:\Users\gkgkb\Documents\Codex\2026-10-04\task-3\unitypackage_blender_importer`
- Owner: GPT-6 LUNA low (planning/documentation); read-only design input: GPT-6 Astra medium.

## Decision

Plan the next work as two independent but related goals: (1) repair and correctly test the existing Prefab Material fixture, and (2) implement exact consumer evidence for FBX `externalObjects` late binding. The fixture repair is not product implementation evidence. Keep these routes and their assertions separate.

The product path starts with VHS Avatar deliverability. An unfinished World deliverable is independently gated and must not block Avatar work. This is a supplied priority constraint; VHS and OnlyYou source repositories, versions, and interfaces were not inspected in this VAPB checkout. Do not infer their contracts or add private assets/SDKs to public fixtures.

## Authority and scope

- `.unitypackage` is the ordinary user entry into Blender; Unity project import and manual FBX export are not user prerequisites. Unity is a verification/finalization oracle and finished package import is the return path.
- Blender final geometry, hierarchy, transforms, slots, and face assignments govern exported editable state. Unity semantic state remains separate recipe/evidence. Source geometry lineage is not a general export condition.
- Export identity, source identity, and post-import Unity identity are separate domains. Names, ordering, and candidate counts are diagnostic only.
- The built-in Material preview remains approximate and `PARTIAL`; its recorded 70-test Blender evidence does not establish Unity Material export or general binding.
- The post-patch Stage3 QA records bounded positive Unity 2022.3.22f1 evidence at source `6c433e4…`, including first/repeat Apply, compatibility 7/7, and two rejection tests. Its fixture scope, same-fixture calibration, unsupported transforms/rigs, and lack of post-save rollback coverage remain explicit limits. No Stage3 rerun is planned absent relevant source changes.

## Verified baseline versus open claims

### Verified in tracked source/docs

1. The cross-package runner failure at `ec81dc2c176f2b782eb96562e7476f1719c46023` and `d47091c2680b53ac0cb11041f5ece11cd851aa90` is the same synthetic `Coat.data.materials` failure. The fixture lacks a MeshFilter, and fileID `1001` selects an Empty Prefab wrapper with no mesh data. This establishes only that the observed runner failure was not introduced between those two revisions.
2. `PREFAB_RENDERER_MATERIAL` carries Prefab target identity and consumer GameObject/slot identity; its test must use a valid serialized MeshFilter and the real projection/capture path.
3. `FBX_EXTERNAL_MATERIAL` currently captures external mapping target GUID/source slot/path without an exact imported native Object/Mesh receipt; `target_file_id` is empty in that path. Generic consumer lookup therefore cannot safely identify a native slot.
4. `unity/material_mapping.py` currently reduces external mapping entries to name→GUID; target fileID and duplicate-row ambiguity are not retained. Receipt capture alone cannot close that gap.
5. Existing `blender/fbx_receipt.py` persists and validates FBX GUID/SHA plus Model/Geometry/Object/Mesh receipt identities. `dependency_resolver.py` already has occurrence-aware record identity and slot ownership checks that should be reused.
6. `confirm_renderer_binding` is a provider-present user confirmation flow, not evidence of captured dependency identity or late resolution.

### Not yet verified

- Which FBX mapping forms can be tied unambiguously from source row to imported native slot across Blender versions and fixture types.
- Runtime behavior of exact-receipt `FBX_EXTERNAL_MATERIAL` capture, late bind, save/reopen, or user-edit preservation; implementation/tests do not exist yet.
- VHS/OnlyYou source semantics, staging boundary, current runner issue details, and any versioned integration interface.
- General Avatar/VRC coverage, full product E2E, actual Unity reconstruction for this dependency route, and public distribution readiness.

## Proposed record contract (not implemented)

Freeze this contract before code work or parallel ownership splits.

- Add versioned exact consumer evidence for an FBX external Material dependency. It includes package ID; FBX GUID and SHA; Model UID; Geometry UID; persistent Object and Mesh receipt IDs; native realization/occurrence ID; and strict non-negative slot index.
- Preserve the source mapping row separately: row identity, raw target GUID/fileID scalars, validated canonical identity, and parse validity/ambiguity. Preserve malformed raw values so normalization cannot make invalid references valid.
- Reuse existing initial/applied slot ownership receipts. Current scene state must not be used to manufacture historical ownership for a legacy record.
- Build stable dependency identity from dependency type, package/FBX identity, native realization, slot, source-row identity, and target identity. Do not persist object pointers or use display names as identity.
- Bind only when exactly one imported consumer matches the persistent receipts, the row is valid and unambiguous, target provider GUID/fileID is exact, and existing slot-ownership checks permit mutation. Otherwise leave unresolved/refused without changing the slot.
- Legacy receipt-free records stay unresolved; do not silently migrate by inspecting current scene state. No-slot metadata cannot authorize slot zero.
- Names may interpret a serialized source mapping row only. They cannot select a provider, native object, mesh, or unique child.
- Before implementation, explicitly decide overlap precedence when Prefab and FBX external records refer to the same consumer slot. Keep semantic dependency roles distinct in keys/statuses and prevent double ownership.

## Alternatives considered

- **GUID + slot only:** rejected; identifies the provider but not which native realization owns that slot.
- **Material/object names or unique-child selection:** rejected; ambiguity and rename/repeated occurrence make it unsafe.
- **Reuse Prefab wrapper identity for native FBX mesh:** rejected; wrapper is not the imported mesh consumer.
- **Use `confirm_renderer_binding` as proof:** rejected; it requires the provider already present and does not exercise dependency capture/late resolution.
- **Treat built-in preview as restored Material:** rejected; it is intentionally approximate and import outcome remains `PARTIAL`.

## Product gates

### Avatar priority track

1. Resolve the VAPB public synthetic CPD tests and exact-consumer route.
2. Meet the two core product proof cases: unchanged `.unitypackage`→Blender→export→fresh Unity import reconstruction; and delete imported meshes, make/UV unwrap Cube, assign Unity-derived Blender Materials, export, fresh import, and prove intended Unity Materials attach automatically.
3. Complete human-readable Material export organization before semantic Hierarchy Parity; complete Hierarchy Parity before broad Unity/VRC component restoration.
4. Meet mandatory campaign scope: Cleanup, Weight Transfer, Bone Merge, practical Japanese UI, and verified distribution. These are release gates, not assumptions that this CPD task satisfies them.
5. Ensure output package is self-contained for selected required assets, with only explicitly declared framework dependencies external. Do not bundle or publish private source assets or SDKs.

### World track

World stays a separately scoped future deliverable. It can proceed after Avatar delivery without blocking Avatar acceptance or release. It must not be represented as complete by Avatar evidence.

## Source anchors

- `docs/R2_BUILTIN_MATERIAL_PREVIEW_CHECKPOINT_20261004.md` — current CPD diagnosis, route separation, and bounded preview evidence.
- `docs/R2_STAGE3_FINALIZER_POST_PATCH_QA_20261004.md` — bounded Stage3 Unity QA and limits.
- `unity/material_mapping.py` — externalObjects parser.
- `blender/material_builder.py` — FBX external material capture.
- `blender/dependency_resolver.py` — dependency identity, exact consumer lookup, and slot ownership.
- `blender/fbx_receipt.py` — existing persistent FBX/native receipts.
- `tests/blender_cross_package_dependency_test.py` — failing CPD fixture to repair without weakening assertions.
- `TEST_STRATEGY.md` — CPD-003..013 and MPV regression contracts.
- `PRODUCT_SPEC.md`, `docs/VAPB_CORE_PRODUCT_MODEL_20260928.md` — product authority and mandatory hierarchy/product gates.

## Resume boundary

This document records design, not authorization to implement or execute tests. Product code edits, Blender runs, Unity runs, broader integration, and product release remain paused until a separate explicit execution instruction. When resumed, reverify canonical remote, branch, SHA, and worktree before starting; use the companion implementation plan and do not repeat completed Stage3 QA without relevant source changes.
