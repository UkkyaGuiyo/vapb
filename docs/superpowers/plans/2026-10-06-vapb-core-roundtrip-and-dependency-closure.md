# VAPB Core Round-trip and Dependency Closure Implementation Plan

> **For implementation agents:** This document records a proposed work sequence. It does not grant or revoke authorization. Proceed only within user authorization already in force and repository instructions; do not add a fresh per-step approval condition. The intended main implementer is GPT-6 LUNA low; request GPT-6.1 SOL medium for design/code review of new work, not to repeat completed reviews.

**Goal:** Close the public CPD gap by proving Prefab Renderer Material and FBX `externalObjects` late binding through separate exact-identity routes, then progress through VAPB product acceptance gates in their documented dependency order.

**Architecture:** Preserve product boundaries documented in [`2026-10-06-vapb-core-roundtrip-and-dependency-closure-design.md`](../specs/2026-10-06-vapb-core-roundtrip-and-dependency-closure-design.md). First freeze a versioned consumer/source-row/ownership contract. Then repair the Prefab test fixture, evolve the externalObjects parser without dropping raw identity, and implement capture-to-bind through the existing FBX receipt and slot-ownership system. Integrate, review, run focused plus regression evidence, then advance separate product release gates.

**Stack:** Python, Blender 5.2.1 LTS synthetic fixtures; Unity 2022.3.22f1 only where the changed source requires Finalizer verification. Do not add dependencies without explicit authorization. Keep all evidence public-synthetic and path/asset sanitized.

## Work ownership and dependency graph

| Work | Owner | Exclusive files | Depends on | Parallel? |
|---|---|---|---|---|
| Contract freeze | Design owner + SOL medium review | Design doc, schema/status/key proposal | Current user authorization and repository instructions | Serial; blocks coding until contract is frozen |
| Prefab route fixture | LUNA low | `tests/blender_cross_package_dependency_test.py` | Contract; valid MeshFilter serialized reference | Can parallel with parser after contract freeze |
| externalObjects parser | LUNA low | `unity/material_mapping.py`, parser unit-test file(s) | Contract; preserve old callers | Can parallel with Prefab fixture only |
| Receipt capture/resolution | One LUNA low owner | `blender/material_builder.py`, `blender/dependency_resolver.py`, narrowly scoped receipt helper only if required | Parser merged/reviewed and fixture route established | Do not parallel-edit shared capture/resolver files |
| Integration and regression | Integration owner | Test orchestration, checkpoints/evidence docs | Both routes merged | Serial |
| Review | GPT-6.1 SOL medium | Read-only review, findings | Concrete diff and evidence | After each contract/code boundary; no rerun of completed reviews |

## Phase 0 - Re-entry and contract gate

1. **Verify the authorized workspace**
   - From clean `feature/r2-material-slot-reorder`, fetch without force and verify canonical origin `https://github.com/UkkyaGuiyo/vapb`, branch, HEAD, and tracked/untracked state.
   - Read `START_HERE.md`, this plan, design, CPD checkpoint, Stage3 QA, relevant product authority, and Failure Atlas index plus relevant exact-receipt/ownership lessons.
   - Preserve existing user probes and any pre-existing local-only evidence. Never reconcile by deleting or overwriting an unexplained file.
   - If the verified branch or source differs, stop and update the plan/evidence before implementation.
2. **Freeze data and status contracts**
   - Specify exact field names/types for `consumer_receipt_version`, package/FBX identity, Model/Geometry UID, Object/Mesh receipt, realization ID, strict slot index, source row identity/raw+validated target identity, mapping validity/ambiguity, dependency status, and stable key.
   - Decide same-slot Prefab-vs-FBX record precedence/ownership explicitly. No coding split until resolved.
   - Define legacy records as unresolved absent receipt; define duplicate receipt/provider, stale mesh, malformed raw fileID, ambiguous source row, and ownership-changed behavior as fail-closed.
   - Review contract with SOL medium. Record accepted schema and migration behavior in public docs before parallel implementation.

## Phase 1 - Independent route REDs

### 1A. Repair the Prefab Renderer fixture only

- Owner/file: LUNA low; `tests/blender_cross_package_dependency_test.py` only.
- Construct a valid serialized MeshFilter reference and use the existing real projection/witness capture route. Do not use a Prefab wrapper's fileID or display name as native Mesh identity.
- Assert exact `PREFAB_RENDERER_MATERIAL` dependency record, provider identity, consumer receipt, actual Blender material slot assignment, and slot ownership status.
- Keep its RED/GREEN distinct from externalObjects. No product code modifications in this phase.
- Gate: failure before fixture repair demonstrates invalid fixture; after repair the exact route assertions pass. Do not interpret this as proof of FBX external mapping.

### 1B. Preserve externalObjects source rows

- Owner/files: LUNA low; `unity/material_mapping.py` and focused parser unit tests.
- Add a structured row/API while preserving compatibility for existing call sites until they migrate. Carry original raw name/GUID/fileID scalars, canonical validated identity, row identity, duplicate/collision and malformed/null status.
- Test ordinary row, duplicate row/name, duplicate target, malformed/fractional/missing fileID, explicit null, and deterministic row identity. Confirm invalid values cannot become valid through coercion.
- Do not choose provider or scene consumer by material name.
- Gate: parser retains enough information to refuse ambiguous/malformed input; old tests/callers remain green.

## Phase 2 - Exact FBX consumer capture and late binding

- Owner/files: one LUNA low owner for `blender/material_builder.py`, `blender/dependency_resolver.py`, and any strictly necessary receipt helper. Do not divide these shared files among concurrent implementers.
- Capture evidence from the actual imported FBX native Object/Mesh via existing persistent receipt validators: source package, FBX GUID/SHA, Model UID, Geometry UID, Object/Mesh receipt IDs, realization/occurrence, and exact slot. Preserve the external mapping source row and raw target fileID.
- Integrate receipt/source-row identity into the dependency record key. Preserve semantic dependency type so Prefab and FBX routes cannot alias.
- Resolve only a unique exact receipt-matching consumer and exact GUID/fileID provider, then require existing initial/applied slot ownership validation. Never reconstitute initial ownership from current scene state.
- Keep legacy receipt-free records unresolved. Refuse duplicate consumers, duplicate/ambiguous mapping rows, stale or changed mesh receipt, invalid slot, wrong fileID, or ambiguous providers with stable status and no slot mutation.
- Separate provider discovery count from successful binding count in diagnostics.
- Tests: provider absent then added; reverse import order; same-name/wrong-GUID refusal; exact GUID+fileID bind; wrong fileID; duplicate provider; duplicate consumer receipt; repeated source occurrence/shared mesh; malformed/null row; user-edited slot preserved before provider arrival; slot reorder/deletion; provider removal/re-addition; rename; repeat resolve; save/close/reopen.
- Gate: assert exact native mesh slot before and after each operation; exact dependency status and owner; no silent partial binding; scene save/reopen preserves record and slot state.

## Phase 3 - Integrate, review, and regression

1. Integrate Prefab fixture and parser changes, then external capture/resolver changes in dependency order.
2. Run focused parser, receipt, occurrence projection, witness, Prefab, and CPD tests. Then run relevant existing dependency/import outcome, built-in preview, texture role, and Skin/Shape parity suites from `TEST_STRATEGY.md` (CPD-003..013, MPV-001..012, and related MPI/SPD cases as impacted).
3. Run Python compile checks and Blender 5.2.1 synthetic operator tests. Include Blender save/reopen where persistence/ownership is asserted. Record exact command, interpreter/app version, source SHA, fixture/package SHA, process exit, result files, and post-run file/process inventory.
4. Ask SOL medium for one read-only review of the new contract/diff, concentrating on raw-vs-normalized identity, key role separation, legacy behavior, ownership and failure-closed mutation. Fix findings and verify affected tests; do not rerun already-completed review without material new changes.
5. Do not rerun the completed Stage3 Unity suite unless relevant Finalizer/C# source changes. If new Unity work is needed, use only the authorized isolated disposable project, preserve owned markers, add no package, and run Editors serially. Stop on licensing/access failures rather than bypassing them.
6. Update CPD checkpoint and `TEST_RESULTS.md` with bounded evidence and remaining gaps. Keep machine-local raw logs and private assets out of Git.

## Phase 4 - VAPB Core Round-trip First product acceptance gates (separate from CPD completion)

1. **Unchanged E2E:** `.unitypackage` direct Blender import, no edits, VAPB export, fresh Unity import; verify required Material/state reconstruction.
2. **Geometry replacement E2E:** import; delete all imported meshes; create and UV unwrap Cube; assign Unity-derived Blender Materials; export; fresh Unity import; verify intended Material assignments without relying on source Mesh lineage.
3. **Material organization:** satisfy the constrained naming/path policy without changing serialized bytes, `m_Name`, GUID, or `.meta` identity; verify portable collisions and repeated Finalizer/reimport for the supported scope.
4. **Hierarchy Parity:** after material organization and before broad Unity/VRC restoration, automate semantic parent/child, transform chain, renderer owner, armature/bone, occurrence multiplicity, and save/reopen checks. Names/screenshots alone do not pass.
5. **Mandatory campaign scope:** Semantic Cleanup, Weight Transfer, Semantic Bone Merge, practical Japanese UI, and verified distribution all require their own acceptance evidence. No CPD test substitutes for them.
6. **Distribution:** fresh checkout/build; only intended runtime files; no private assets/SDKs/secrets/local paths; selected required assets self-contained and only explicitly declared framework dependencies external; verify final package in fresh Unity import and record immutable source/artifact hashes.
7. Do not introduce integrations or dependencies that are absent from VAPB product authority. Keep third-party framework dependencies explicit and do not bundle private source assets or SDKs.

## Release and merge gates

- All Phase 0-3 acceptance tests pass from a clean checkout at the recorded SHA.
- Both product E2E cases and mandatory campaign requirements are independently green for the claimed release scope.
- Hierarchy Parity is complete before broad Unity/VRC component restoration claims.
- All unresolved/unsupported contexts are visible; no names, candidate counts, discovery-only results, or approximate preview are reported as successful binding/reconstruction.
- Public docs/logs contain no private assets, identifiers, machine paths, raw private logs, or undeclared dependencies.
- New code receives focused SOL review and integration regression evidence. Save evidence in docs with exact commit/branch/hash; follow the user authorization already in force for repository changes.

## Current completion state

At the plan's authoring base `960b8aa011bc533b92d4304ae3c9227bef8e1396`, phases 0-4 are **not executed by this documentation task**. The CPD runner is still documented failing; exact externalObjects runtime binding is not implemented or tested. Stage3 QA is bounded prior evidence and does not cover CPD. No tests, Blender, or Unity are invoked here. This plan does not impose a new approval condition; subsequent work follows existing user authorization and repository instructions.
