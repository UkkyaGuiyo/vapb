# VAPB Core Round-trip and Dependency Closure Implementation Plan

## Planning revision — 2026-10-08

User-approved overengineering correction. The current priority is the earliest failed boundary of the required end-to-end workflow, not completion of all late-provider and recovery permutations before testing the core. This revises scheduling and work size only: product requirements, strict semantic contracts, established data formats and original evidence are unchanged.

**Goal:** Prove direct `.unitypackage` input into Blender and Unity return in both required cases: unchanged input, and Blender-authored replacement geometry receiving the intended Unity Material/state automatically. Then close the remaining required dependency/campaign/release gates.

**Architecture:** Reuse existing import/export operators, identity/receipt mechanisms, Finalizer and discriminating tests. Keep source identity, Blender final-state Export IDs and Unity post-import identity distinct. Fix one demonstrated broken semantic edge at a time; do not create another witness, parser, receipt or orchestration system simply to continue a historical checklist.

**Stack:** Existing Python, Blender 5.2.1 LTS and approved Unity 2022.3.22f1 verification environment. No additional dependency, SDK update, runtime launch or permission change is authorized by this planning revision.

**Authority:** [PRODUCT_SPEC](../../../PRODUCT_SPEC.md), [Core Product Model](../../VAPB_CORE_PRODUCT_MODEL_20260928.md), [approved design](../specs/2026-10-06-vapb-core-roundtrip-and-dependency-closure-design.md), [R2 discriminating plan](2026-10-06-r2-roundtrip-discriminating-verification.md), current `START_HERE.md`, `TEST_STRATEGY.md` and latest relevant evidence. The old contents of this file remain in Git at `f9327ba62e901dff9383f5b123ff5252f37c5f3f`.

Existing Phase 0–3 contract/parser/binding checkpoints are historical completed or partial work, not instructions to recreate them. Current user/AGENTS routing governs the primary engineer and review; this revision supersedes fixed LUNA staffing and automatic per-stage review in the linked older plans without removing required safety/semantic review.

## Current dependency sequence — 2026-10-09

- The installed-distribution representative native Skin/nonnull Texture return is complete; reuse its bounded result, not whole-product acceptance.
- Source implementation and nearest checks now pass for human-readable Material paths on the single no-Prefab source-model Skin route only. In `operators/export_unitypackage.py`, reuse `proven_owners`, the existing raw Material reader and `allocate_material_paths`; absent proof remains Unassigned. Pass the resulting path map into `export/model_package.py` and represent it with existing MOVE/Material plan fields. Do not change Material bytes, m_Name, GUID or meta, or other export routes.
- Extend `tests/test_model_package.py` only for path-only identity/byte preservation, allocator collisions/repeat/package readback and rejection of non-Material/unknown destinations. Reuse the existing native Blender edit/save-reopen/export observation with one owned input. Run nearest naming/model tests, then inspect the diff and normally save source plus safe status.
- The named output now passes bounded Unity placement/reference/geometry acceptance in an existing isolated Project with output GUIDs and destinations absent. Three organized Materials and ten source Asset/meta files match their original bytes; all preexisting Project files remain unchanged and the pool was normally released. Preserve the earlier occupied-path observation and its occupants; do not infer general collision handling or whole-product acceptance. The existing 2026-09-30 Hierarchy Parity and direct Shape-channel/occurrence-weight closures already verify their measured supported scopes and must not be reimplemented. Production D1 disposable Blender triangle staging subsequently verifies bounded export topology/surface; do not repeat the earlier triangulation or small-weight repair. Source import-preview nonplanar surface differences, genuine normal differences and raw Skin numeric parity remain separate open boundaries. Existing failed tessellation candidates are not a justified implementation; strict Skin policy may not be relaxed from representation diagnostics. Require a concrete public defect and an authority-compatible remedy before another production patch, without a broad fixture matrix.
- Real downloaded packages stay local and are not an implementation prerequisite. Before one real representative return, inspect its bundled terms, exact selected Skin and dependencies; defer only that material-use gate if conditions remain unknown. Do not publish commercial assets, extracted/edited derivatives, identities, private paths or detailed contents.

- Source-only WT-02 correction (2026-10-09): FILL_MISSING now preserves every positive existing weight as the Japanese zero-only UI promises. Existing transfer planning and application no longer suppress/remove positive values with a fixed 1e-8 cutoff. Pure and actual Blender RED/GREEN cover tiny fill/add/replace and explicit zero removal; existing mode/scope/lock/source preservation/rollback/Undo/deformation checks pass. No automatic transfer, normalization policy, Bone mapping, Unity/VRC restoration or product-wide acceptance was added.
- WT-02 export continuation (2026-10-09): actual explicit transfer of the existing first-party ladder, including 1e-9, preserves all 45 control-point weights exactly through normal FBX export and existing optional Bone Cleanup staging. Both actual FBX Cluster graph comparisons pass; source weights/data/scene and disposable-object counts remain unchanged. No further export product defect was found. The existing fixture now covers 1e-9 and resolves vertex-group assignments through Bone names, because transfer can change local group creation order. Its regular Blender run passes. The existing Unity probe reads the already-recorded source cp_count instead of hard-coding the historical 42; that observer change is prepared but has not been compiled/run in Unity.
- Current-code ZIP continuation: distribution revision 2e17d867b787ec8fd79e344e2ccc85f53b5f9bf9, SHA256 c42f40935e76404d9b8e4cf36e49f5b4c478979fe06048c0a7f902369527655b. Existing build validation checks 115 runtime members; isolated Blender 5.2.1 LTS addon install/enable/disable and the existing full Weight Transfer runtime case pass from the installed ZIP. Modified source modules match archive bytes and all seven Unity helpers are present. Relevant Japanese RNA labels pass; interactive GUI, current tiny-weight Unity restoration and overall release remain unverified. The shared Unity resource is not used for these checks.
- WT-02 Unity continuation (2026-10-09): the assigned shared frame ran the transferred 45-CP first-party native FBX through only existing SmallWeightProbe.ProductionControl (without policy / existing production policy / repeated import). The cp_count observer compiles in Unity 2022.3.22f1. Default import drops 27 positive influences; policy and repeat preserve 45/45 CP weights bitwise, including the three 1e-9 influences, with zero missing positive influences and stable mesh GUID/fileID and Bone labels. BakeMesh(true) + TransformPoint versus the raw CPU skin equation has measured maximum Unity-world error 1.9157121992097135e-6 for policy/repeat; this is not an exact-deformation claim. All 2,823 preexisting Assets/Packages/ProjectSettings files and local input files retain their hashes. Owned Editor normal exit 0, children/project lock absent, pool and shared mutex released. Public first-party measurements are in tests/unity_small_weight_probe/transferred_tiny_weight_measurements.json. This bounded native-FBX policy control does not add unitypackage/Finalizer, Texture, commercial input or product-wide acceptance.
- WT-02 product-path continuation: the exact transferred FBX (4d16ca1b16521f2cafbddb5eba94c732e33aa4c1c937c4a83f582a11829fee23) was wrapped unchanged by the existing package writer and normally imported by the product. It retains 45 CP / 15 triangles and the three positive 1e-9 values. Normal source-model Skin export formally rejects the two independent Bone roots before producing any output. Raw FBX confirms both Cluster Bones share a noncluster Null Model parent; this is not an observed Unity rootBone UID. The existing producer requires one selected Bone root and consumer requires the actual source root UID in explicit Bone receipts. No guard was removed, input reparented, receipt fabricated or synthetic native result upgraded to product acceptance. Next obtain the exact Unity rootBone/parent identity through existing witnessed source machinery before implementing any bounded common-parent support; a potential default-source versus preserved-edited influence comparison remains untested downstream. See transferred-native-package-root-boundary.json. The original owned input and prior product checkpoints remain intact; no Unity was launched in this continuation.




## 1. Product constraints retained

- Normal input is UnityPackage(s) directly into Blender. A Unity input project or manual FBX export is not a user prerequisite. Development-only Unity observations/witnesses may diagnose a seam but cannot become a mandatory product workflow.
- Blender final geometry/topology, UV, bones/weights/Shape Keys, editable hierarchy/Transform, Material slots and face assignment are authoritative at export. The user may delete all imported Meshes and create a replacement. Source geometry lineage is required only for a specific source-index-dependent preservation claim, not all successful export.
- Unity serialized Material/Texture/component state remains independently preserved recipe data. Material preview is approximate; matching names/counts/screenshots are not identity or face-assignment proof.
- Source GUID/fileID/package/occurrence evidence remains essential for import, dependency recovery, Prefab/Variant and reusable asset identity. Exact provider/consumer and owned-slot rules are not weakened.
- Required selected Material/Texture/Prefab assets must be self-contained in output. Only explicit approved framework dependencies remain external. Do not require reimporting original asset packages to make ordinary output work.
- Preserve the existing strict Skin transport acceptance contract. Do not replace exact required identity/representation checks with epsilon/ULP tolerance or infer visual/deformation equivalence. Unsupported context remains unsupported.
- Material human-readable path organization must preserve serialized bytes, `m_Name`, GUID and `.meta`. Preserve the specified ordering of this milestone before mandatory Hierarchy Parity, and Hierarchy Parity before broad Unity/VRC component restoration.
- Semantic Cleanup, Weight Transfer, Semantic Bone Merge, practical Japanese UI and verified distribution remain mandatory campaign requirements, not removed because the first core milestone is smaller.
- Use owned synthetic fixtures and authorized isolated processes. Preserve user scenes/probes, original archives, failed output and unrelated dirty/untracked files. No silent fixture repair, deletion, retuning, security bypass or automatic SDK install. Public records exclude private assets, secrets, identifiers and raw private logs.

## 2. Active sequence: closest failed boundary first

### R0 — Choose the exact next discriminating question

- [ ] Read the latest relevant evidence and identify the first unproved or contradicted edge: input provenance, import identity/face assignment, export closure, persistence, coordinate transport or fresh Unity application. Do not infer its current result from old summary counts.
- [ ] Keep fixture/source/expected semantics fixed for that question. Reuse accepted parser/receipt/CPD components; read completed work instead of rerunning all Phase 0 tasks.
- [ ] Prefer the next existing discriminating test. New helper/schema/holdout machinery needs a concrete missing capability and smaller-alternative comparison.

### R1 — Strict unchanged core route

Use the linked R2 plan's T0-A/T0-B/T0-C/T1 and U0 contracts, not a parallel new verification framework.

- [ ] T0-A: fresh production import; compare immediate Material GUID/fileID/package and face association against independent input expectations before any repair. No assignment/injected receipt can be smuggled into a no-edit claim. If the present probe requires a development witness, label that condition and keep direct-input product acceptance open.
- [ ] On T0-A failure, stop downstream success claims and trace the missing reference/provider/consumer/face edge. Do not repair the scene and continue as unchanged PASS.
- [ ] T0-B/C: unchanged export, scene/source preservation and output closure. Inspect actual Material/meta/Texture where present, manifest and generated FBX associations. Use independent input expectations, not the current possibly-wrong Blender state as its own oracle.
- [ ] T1: verify save/reopen of the same route where persistence is claimed. Do not simultaneously move/delete source archives or introduce absent providers; those are separate hypotheses.
- [ ] U0: once the existing source/output prerequisites hold and the isolated Unity slot is authorized, inspect the exact output in fresh Unity with explicit Finalizer/build steps where required. Record GUID/local IDs, Material/face/submesh association, hierarchy/Transform and relevant state. Do not wait for unrelated provider permutations before this essential return proof.

**Exit:** bounded unchanged E2E evidence or one localized failure. Archive creation, Blender-only success, scalar fits and a working witness fixture alone do not establish the product workflow.

### R2 — Resolve coordinate/face hypotheses without fitting the test

Use existing coordinate intervention/holdout work only where it answers the current boundary. Keep preregistered inputs, expected conversion and tolerances fixed. A candidate inferred from observed cases requires unseen controls before a broader claim. Shape correspondence, winding/normal transport and Material-to-face identity are independent claims.

Stop after a decisive counterexample; preserve it and revise the hypothesis explicitly. Do not keep adding cases that measure the same settled question, tune thresholds after seeing failure, or use source/display order as the fix. A correction to product source needs a minimal regression for the reproduced error and relevant existing regression checks.

### R3 — Edited and replacement geometry

- [ ] Reuse T3's minimal edit control if needed to isolate transport from replacement. It is a diagnostic, not a new product restriction.
- [ ] T4: remove imported Meshes, create/unwrap the specified Cube, assign Unity-derived Materials and export through the existing final-state route. Use current final geometry/UV/Material-face data, not source vertex lineage, as the expectation.
- [ ] U1: import that exact output into fresh Unity and verify intended Material/state reattachment. Keep unchanged and replacement routes/results distinct.

**Exit:** both required core proof cases, with limitations stated. This milestone is not the complete product campaign.

## 3. Conditional dependency closure work — former Phases 0–3

Run this before a core gate only if that gate demonstrably depends on it. Otherwise keep it downstream of the basic E2E proof. Deferral is sequencing, not deletion of required supported behavior from release.

| Existing responsibility | Preserve / perform only as needed |
|---|---|
| Phase 0 contract | Reuse the accepted consumer/source-row/slot ownership contract and precedence. Do not refreeze unchanged schemas or add a new ID family. |
| Phase 1A Prefab route | Reuse the correct MeshFilter/reference fixture and exact Prefab Renderer Material consumer evidence. Its result does not prove the FBX externalObjects route. |
| Phase 1B externalObjects parser | Preserve raw and validated name/GUID/fileID, row identity, explicit null, malformed and ambiguous statuses and current caller compatibility. Do not coerce invalid IDs or select by Material name. |
| Phase 2 consumer binding | Reuse actual native Object/Mesh receipts, package/FBX/Model/Geometry identity and the exact slot. Require unique exact provider and retained ownership; no ownership reconstructed from current edited state. Provider discovery is not successful binding. |
| Phase 3 regression | Run tests affected by the actual contract/source change, including persistence if claimed. Existing relevant full dependency/import/Skin/Shape regression follows before release, not as an unchanged per-investigation ritual. |

CPD-006 and duplicate-provider/consumer, provider removal/re-addition, user-edited slot, reorder/deletion, rename and import-order permutations remain important for the scope they protect. Choose the smallest pending-provider/untouched-versus-user-edited control when that behavior is in scope; do not execute the whole permutation matrix while strict import/face mapping already fails. No release claim may omit a required supported dependency case merely because it was deferred during diagnosis.

Keep exact Texture Image datablock/node identity checks where textures exist; node/record counts alone are insufficient. The existing no-Texture strict fixture cannot claim texture closure. A changed assertion is a test correction unless it actually reproduces a product defect.

## 4. Remaining product campaign and final acceptance

- [ ] Complete unchanged and replacement E2E through normal user input without mandatory pre-import Unity preparation.
- [ ] Complete constrained Material organization and its collision/repeat/save/reimport coverage for claimed routes without modifying Material bytes or `m_Name`.
- [ ] Complete mandatory semantic Hierarchy Parity: parent/child, Transform chains, renderer owner, armature/bones and occurrence multiplicity; persistence where promised. Do this before broad Unity/VRC restoration as product authority requires.
- [ ] Complete Semantic Cleanup, Weight Transfer, Semantic Bone Merge and practical Japanese UI against their existing approved requirements and tests. Preserve strict Skin/state boundaries; do not infer these from Material tests.
- [ ] Close required CPD/regression/unsupported-reporting gaps for the claimed release. Relevant Finalizer/C# changes require corresponding Unity evidence; unchanged unrelated Unity suites need not be rerun during every Python diagnostic.
- [ ] Validate a fresh build/package and clean Unity import with correct self-contained selected assets and explicit framework dependencies. Inspect actual distributed content, licenses, setup instructions and exclusion of private/SDK/test payloads. Release/merge/publication follow current explicit authorization, not this file alone.

## 5. Ownership, evidence and stop rules

One primary engineer owns the current failing seam. Split work only across genuinely independent files; shared material_builder/dependency_resolver/receipt contracts have one writer. Independent scope/design/code review is proportional to new risk; do not respawn agents to repeat an accepted review.

Keep original T0/T1/T2/T3/T4/U0/U1 IDs and historical results. This revision reorders optional work, never rewrites old failures or claims a new experiment occurred. Source/final-state/Unity identity domains, fixture revisions, process exit and actual semantic observations remain traceable using existing records.

If tooling work keeps expanding without a new semantic observation, compare standard APIs, current probes and the smallest bounded control before more infrastructure. A missing permission/resource is a blocker, not a product defect or permission to bypass a guard. Do not automatically resume an explicitly stopped project or knowledge collection.

Planning completion means these instructions are saved and readable. No code, fixture, oracle, threshold, dependency, runtime result or product acceptance was changed by this revision.
