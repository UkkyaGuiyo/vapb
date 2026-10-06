# R2 Round-trip Discriminating Verification Plan

> **For agentic workers:** This is a staged verification plan, not a product specification. Use the existing authorization only. Main execution owner: GPT-6 LUNA low; GPT-6.1 SOL medium reviews this plan and new tests read-only. Do not let test fixtures define new product policy.

**Goal:** Identify the earliest failing boundary in the public synthetic `.unitypackage` → Blender → exported `.unitypackage` path without repairing imported state, then use the result to select the next bounded test toward fresh Unity import acceptance.

**Architecture:** Reuse commit-addressed source fixtures and existing Blender operators. Observe package input, immediate Blender state, export, serialized package closure, and persistence as separate gates. Run only the next discriminating stage; stop at its first failure and choose the next experiment from the observed boundary.

**Tech Stack:** Python; Blender 5.2.1 LTS in disposable factory-startup processes; tracked synthetic Unity package fixtures and the production Blender operators. No new dependency. Unity 2022.3.22f1 is deferred while the shared Editor slot is occupied.

**Spec:** [`2026-10-06-vapb-core-roundtrip-and-dependency-closure-design.md`](../specs/2026-10-06-vapb-core-roundtrip-and-dependency-closure-design.md), especially Core Round-trip First and Phase 4 acceptance gates.

## Baseline and evidence limits

- VAPB: `https://github.com/UkkyaGuiyo/vapb`, branch `feature/r2-material-slot-reorder`, inspected HEAD `81262fb8e1ab1bc3f144d6a3f2871816522d97d3`; branch lineage is `004c82bfd8070d98e23f8417ab8e379771a3481d` → CPD test `7057cbd1658375084ba0111a75b3c715e6b394db` → research note `81262fb8e1ab1bc3f144d6a3f2871816522d97d3`.
- `tests/blender_cross_package_dependency_test.py` passed in Blender 5.2.1 at 7057cbd. It establishes bounded synthetic import, exact witnessed Prefab slot binding, and save/reopen observations. The test's texture image GUID is checked before resolver replay; after replay, the texture assertion compares record and node counts only. This does not establish exact texture link survival after replay.
- `tests/blender_final_state_export_test.py` phase `unchanged` assigns or appends the Unity-derived Material after import. Its PASS is not strict no-edit Material preservation evidence.
- `tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage` is the existing first-party public synthetic fixture produced with Unity 2022.3.22f1 public APIs, hash `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`. Its provenance is documented in `tests/unity_model_material_probe/REPRODUCTION.md`. Do not regenerate or modify it for this plan.
- Older Nested Prefab evidence used a different source SHA and is not evidence for the 7057cbd test or the strict export gate.

## Global constraints

- Test only public synthetic, commit-addressed fixtures; no purchased assets, user projects, or secret data.
- Use a run-owned disposable directory and a new output filename. Do not overwrite fixtures, existing user probes, or unexplained output files.
- Run Blender processes serially with factory startup. Do not clear or delete data in a user scene; scenario cleanup is permitted only inside the disposable test process.
- Do not assign, replace, repair, or inject Material slots, texture links, receipts, or IDs in the strict no-edit gate.
- Do not change product source or add dependencies before a failing test demonstrates a product defect and the minimum fix is reviewed.
- Unity acceptance is BLOCKED/NOT RUN while the shared Editor slot is held. Blender, compilation, archive inspection, or callback preparation cannot be reported as Unity round-trip PASS.
- Preserve failure stage, process exit, package/fixture hashes, and per-gate observations separately. Stop on access/licensing failures; do not change permissions or environment security settings.

## Review focus

- Import assigned a different Material, missing slot, or wrong face/slot association: T0 must compare immediate imported state with the fixed source expectation before export.
- Export omitted or changed an asset reference: T0 must verify package GUID/meta/payload identities and Material → Texture closure, not just archive creation.
- Export silently changed the editable Blender scene: T0 records the scene and source archive state before/after export.
- Resolver replay changes a texture assignment while record/node counts stay constant: tighten the CPD repeat assertion before reusing its idempotence result.
- Pending state or ownership changes after process restart/provider arrival: run CPD-006 only as a separate downstream branch, with explicit untouched and user-edited consumer controls.

## Decision sequence

| Gate | Input and single change | Fixed controls and observations | PASS excludes / FAIL points toward | Next branch and stop rule |
|---|---|---|---|---|
| T0-A: strict import | Fresh Blender process imports the exact ThreeSlotSource fixture with the production operator. No post-import slot repair. | Record fixture SHA, one expected native skin/Mesh receipt, current three slot links/material GUID+fileID/package, per-face slot counts, dependency outcomes. Select only the exact receipt-matched Mesh; fail fixture selection if zero or multiple. | PASS excludes an inbound Material-slot failure for this fixture. FAIL before export localizes the first issue to fixture/import/projection/material realization; it says nothing about export. | On first mismatch, stop. Save a bounded report and identify the earliest missing identity edge. Do not repair it and continue to claim no-edit PASS. |
| T0-B: immediate no-edit export | On T0-A PASS, save the imported `.blend`, capture its SHA-256 and a semantic scene snapshot, then export the unchanged imported Mesh with the normal `vapb_unitypackage` production operator to a new output path. | Inventory each file in the source archive store by relative path and SHA-256. After export, require unchanged `.blend` hash, source package hash/archive-store inventory, and semantic scene snapshot (Object/Mesh identity, Material slots, images, and relevant receipts). | PASS excludes an observed source/scene mutation in this operator run. FAIL points to export side effects. | Stop on any mutation or operator failure. |
| T0-C: output closure | Inspect the exact T0-B archive with the production raw package reader plus an independent `tarfile` member checker; use the fixture's raw Unity Prefab YAML as the fixed Material GUID/fileID expectation, not the currently imported Blender values. | Check each required `.mat` GUID/fileID, meta GUID, unchanged payload hash, destination path, manifest `material_mappings` and `material_slots`, and generated FBX. Extract the output FBX and import it using Blender's native FBX importer in a separate disposable process; compare the three material carrier labels to manifest export IDs and face/triangle counts to a baseline imported from the source FBX in another fresh process. The fixture has no Texture assets, so texture closure is N/A here. On a disposable output copy, remove a required Material entry and require the archive checker to fail specifically for the missing expected GUID. | PASS supports only serialized Blender→archive Material/face identity closure for this fixture. FAIL distinguishes missing payload, wrong identity transport, and wrong face/slot association. | Stop at the first failing invariant. If the output FBX/native reader does not expose the transport value, report that observation NOT RUN; do not substitute string occurrence for association. Do not infer Unity behavior from archive inspection. |
| T1: saved-scene replay | Only after T0-A..C pass, compare same in-memory export with export from a second Blender process that opens the saved `.blend`; source archives remain present. | Compare semantic identities, Material/Texture link values, manifest tasks, and package asset closure. Archive byte equality is diagnostic only. | PASS weakens the hypothesis that same-process cache is required. FAIL localizes persistence/source-archive/reopen state, but not which one until compared. | On mismatch, compare persisted receipt/registry and archive path/hash before testing moved/deleted-source portability. |
| T2: CPD-006 pending-provider replay | Candidate only if T0 is green and public cross-package behavior remains a priority. Import geometry without provider; verify a pending exact dependency; save and exit Blender; fresh process reopens, then imports provider from a separate directory and resolves twice. | Keep geometry/provider bytes and IDs fixed; record pending record before/after restart, provider identity, slot link/material, exact statuses after each resolve. Use two exact consumer occurrences: one untouched slot expected to bind, one explicitly user-edited sentinel expected to remain edited. The present `tests/blender_cross_package_dependency_test.py` fixture creates one renderer occurrence, so it cannot be reused unchanged for this two-consumer control; add the second occurrence only if its exact receipt is captured by the same supported route. | PASS supports pending-record persistence plus late provider/ownership behavior for this synthetic pair. FAIL before provider arrival points to persistence/receipt; after arrival points to provider discovery, consumer identity, or ownership. | Do not add ambiguous-provider permutations until this pair has a localized result. If exact two-consumer occurrence receipts cannot be established, split into separate one-consumer persistence and user-edit tests. |
| T3: minimal edit delta | Only after strict no-edit export passes. Move one known vertex by one known small amount; keep hierarchy, UV, face slot, Material, and Texture fixed. | Compare imported and exported evaluated geometry under the documented coordinate conversion; verify non-target package assets and slot identities remain fixed. | PASS supports one narrow edited-geometry transport route. FAIL localizes geometry selection/FBX generation/final-state application candidates. | Stop on unexpected non-target semantic changes. |
| T4: geometry replacement | Only after T3. Remove imported meshes, create/unwrap the planned Cube, and assign Unity-derived Materials as the distinct replacement use case using `vapb_final_state_unitypackage`. | Do not compare source vertex lineage; compare final mesh, UVs, weights if in scope, Material identities and face assignments. | PASS supports this bounded replacement route, not all Avatar components. | If it fails, split “new Mesh” and “source Mesh removed” with one-factor controls. |
| U0/U1: fresh Unity acceptance | Deferred until authorized isolated Unity slot is available. Run T0 output first, then T4 output, in fresh Unity targets. | Bind result to exact output package SHA. Observe actual Unity asset GUID/local IDs, Renderer/Material slots, textures, face/submesh assignments, Finalizer outcome, process exit and post-run Editor inventory independently. | PASS can support only this exact fixture/output/scope. | Until run, status remains Unity acceptance NOT RUN/BLOCKED; no Blender-only result upgrades it. |

## Test-oracle corrections before reusing prior evidence

1. In `tests/blender_cross_package_dependency_test.py::check_scene`, after the two `resolve_scene_dependencies` calls, assert the exact texture record status/target GUID and the actual Image datablock linked to the expected shader node (including Image GUID and source package identity). Preserve the Prefab material exact slot assertion. Record this as a strengthened synthetic idempotence assertion, not a new product defect unless RED reproduces.
2. Keep the CPD assertion fix separate from T0's strict roundtrip test so each has an interpretable result. Do not use node counts or record counts as a substitute for material/image binding identity.
3. T0 should be a separate strict test or explicit mode that shares the source fixture but never runs the slot assignment lines in `tests/unity_model_material_probe/prepare_fixture.py`. Do not silently redefine the existing edited Material probe.
4. T0's face/material oracle must be fixed from input: extract the source Prefab's ordered `m_Materials` GUID/fileID rows with a fixture-bounded parser, and get source face-group counts by directly importing the fixture FBX with Blender's native FBX importer in a separate fresh process. Do not derive expected values from VAPB's current Blender scene or its exporter.
5. T0 uses a skinned source fixture with three Standard Materials and no textures. It is not a static-Cube/final-state export test. T4 uses a separate `vapb_final_state_unitypackage` route. Texture closure is NOT COVERED by T0 and remains a separate later fixture/gate.

## Hypothesis categories and branch rules

- **Input/producer:** if the source package hash or recorded expected asset identity differs, stop and repair fixture provenance before diagnosing VAPB.
- **Inbound identity/binding:** if T0-A differs, follow reference → provider GUID/fileID/package → native consumer receipt → slot/face assignment. Do not start with export or arbitrary duplicate providers.
- **Outbound ownership/closure:** if T0-A passes but T0-C fails, inspect source archive availability, selected asset set, exact provider resolution, staging collisions, emitted GUID/meta, then FBX carrier/face mapping. Change one candidate cause per test.
- **Persistence:** if same-session T0 passes and T1 fails, compare the saved Blender registry/receipts, source archive path and hash, then reopen and provider state. Do not delete/move source archives in the same experiment.
- **Late provider/ownership:** use T2 only after strict path evidence or an independently observed pending record motivates it. Separate untouched binding from user-edit sentinel ownership; do not infer ownership from provider discovery.
- **Unity application:** only evaluate after serialized output closure passes and a fresh Unity run is possible. Separate package import/compiler, identity callback, Finalizer, and resulting native Material/Texture/face assignment.
- **Route boundaries:** `vapb_unitypackage` for the imported skinned source, `vapb_final_state_unitypackage` for a newly created static Cube, and Unity Finalizer/import are separate routes. Do not use evidence from one to claim another.

## Stop conditions

- Stop at the earliest reproducible failing gate; do not run later gates on repaired state and report a no-edit pass.
- After one counterexample distinguishes the competing hypotheses, return to SOL for review before adding variants.
- Stop on uncertain provider/consumer identity, unsafe fixture selection, archive corruption, access denial, or missing evidence rather than guessing.
- All Blender gates green still means **non-Unity roundtrip evidence only; fresh Unity acceptance pending**.
- No assertion of optimality or exhaustive coverage is made. The order is chosen to reuse existing evidence and inspect the closest untested boundary first.

## SOL review corrections

- SOL medium confirmed the strict unchanged T0 is more directly discriminating for the Core Round-trip First gap than CPD-006, which isolates pending-state persistence and late-provider ownership.
- SOL medium confirmed `ThreeSlotSource.unitypackage` is a suitable existing public skinned fixture for the ordinary `vapb_unitypackage`/`RESTORE_DIRECT_SKIN_VARIANT_V1` route, with one critical limit: it has no textures.
- SOL medium required an input-fixed oracle, a concrete native-FBX reimport observation for exported material carrier and face groups, source archive/store inventories for mutation checks, and a separate label for the static Cube final-state route. Where those observations cannot be independently produced, status must be NOT RUN rather than inferred.
