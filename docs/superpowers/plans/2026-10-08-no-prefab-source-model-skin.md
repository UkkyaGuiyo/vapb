# No-Prefab source-model Skin return implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Execute inline; one fresh whole-change review at the end.

**Goal:** Export one author-owned no-Prefab Skin edit and restore a separate Variant based on the preserved source FBX Model Prefab.
**Architecture:** One new task kind in the existing manifest. Reuse hash-bound raw graph receipts, Skin staging, witness and Variant verification; old Prefab kinds retain their validation.
**Tech Stack:** Python/Blender 5.2.1, Unity 2022.3.22f1 C# public APIs.
**Spec:** Approved candidate and identity boundaries in tests/evidence/remapped_model_replacement_export_20261008/README.md; human approval relayed 2026-10-08 14:21:47 UTC supersedes its undecided status for this bounded implementation.

## Global constraints
- Original input/FBX/meta/Material assets remain preserved; edited Mesh and Variant are new assets.
- One no-Prefab Skin/source revision; no fabricated context, names-as-identity or guessed bindposes.
- Existing native index layout, Bone order and UID-bound influences must match; reject unsupported change.
- No Unity launch until the parent assigns a slot; WIP is not roundtrip acceptance.

## Review focus
Wrong source revision, absent/duplicate receipts, mixed tasks/Prefab evidence, native topology or weight drift, occupied Variant path.

### Task 1: producer
Modify export/model_skin.py, operators/export_unitypackage.py; extend tests/test_model_skin.py.
- [x] Add source-kind positive and malformed/revision/Prefab/mixed-task tests; observe RED.
- [x] Build hash-validated source-only task and route single unscoped native Skin into existing staging; observe GREEN.

### Task 2: consumer
Modify unity_editor/Editor/VapbModelSkinFinalizer.cs; extend existing ModelSkinRouteCompatibilityTests.cs.
- [x] Add dedicated source-root routing and validation without relaxing old kinds.
- [x] Reuse witnessed source renderer and Variant machinery; enforce layout, Bone order and influence equality.
- [x] Run reference compilation and nearest existing tests. Unity runtime remains pending.

### Task 3: bounded export and save
Reuse existing model-skin Blender check; record exact output/source preservation and scene state.
- [x] Run focused Python and normal Blender export, with failures diagnosed rather than expectations weakened.
- [x] Fresh code review once; save product code/tests/restart evidence on allowed branch and read remote blobs.
- [ ] Parent Unity slot and runtime acceptance pending; no launch while VHS owns it.

Checkpoint: producer/consumer implemented; 24 focused Python tests pass, product C# reference compilation passes, normal Blender native export passes. One fresh SOL/medium review found no critical/important issues; its minor direct-test main-guard placement was fixed. Unity import/NUnit/Variant ancestry/reload/bounds remain NOT_RUN. This is an export-only WIP checkpoint; runtime acceptance requires the parent-assigned Unity slot.

Runtime checkpoint: parent-assigned dedicated Unity project used; final normal-import package, standard Finalizer, fresh Editor restart, important geometry/identity/face/Material/Weight/rest-bounds checks PASS. Product bounds persistence defect fixed and failures retained. NUnit/animation/render/general scopes remain untested. See native-skin-unity-return-pass.json. Owned Editors exited normally; lock gone and allocation released.
