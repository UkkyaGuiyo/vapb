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
- WT-02 root authority observed (2026-10-09): one assigned Unity 2022.3.22f1 frame reused prepare_witness / Finalizer.RunWitness on the exact source package FBX. All four raw Model UIDs were witnessed, source bytes/meta restored and root GUID/fileID stable. Actual rootBone is WEIGHT-BONE-1 (raw UID 251529238), not the shared Null Model (51419677); the other Cluster Bone is a sibling, not its descendant. The proposed common-parent-as-root assumption is rejected by this observation. The existing single-root producer rejection remains; consumer sibling ancestry is outside its current source.bonesByUid parent transport. A safe bounded extension must retain the witnessed actual root, explicitly transport/verify the shared parent Transform through existing receipts and preserve strict rest/layout/influence checks, rather than dropping a guard or reparenting the fixture. That extension and the downstream source/edited tiny-weight comparison are not implemented or accepted here. Existing probe observation compiles; Editor exit 0, 2,830 preexisting files/input hashes unchanged, retained probe bytes restored, children/lock absent and pool/mutex released. See transferred-native-root-identity-unity.json; no product Variant was produced.





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


## Shared-parent Skin evidence transport checkpoint (2026-10-09)

Missing information was the official importer's actual Armature Object handle for
the source non-cluster Null Model, and that same parent's receipt on the edited
FBX. The source witness already proved the actual rootBone is cluster Bone UID
251529238; its sibling and it share Null Model UID 51419677. A single Bone root
is not a permanent product requirement.

The chosen minimum is the existing Object receipt family plus one optional
`parent_transform_mapping` row (source Model UID and edited Object realization).
It applies only to the single source-model Skin task. Parent role is separate
from cluster Bone mappings. Adding a new task/schema/runner, treating the Null as
a Bone/rootBone, reparenting siblings, or removing the hierarchy guard globally
were rejected: each loses proven native identity or expands unrelated scope.

Producer captures the Armature returned by the official `build_hierarchy`, checks
source GUID/hash and exact raw shared-parent edges, and rejects tampered receipts,
duplicate realizations and changed Bone parents. Staging carries the parent
Object marker without changing Bone hierarchy. Consumer resolves the original
parent through witnessed UID/fileID, compares exact parent handles and the
parent Transform in the Unity renderer frame, and keeps the actual rootBone,
index layout, Bone order and strict influence comparisons. Original FBX/meta,
original bones/root and separate Variant behavior remain protected.

Observed: 21 focused Python tests PASS; product and adjacent C# tests reference
compile PASS. Normal Blender import/save/reopen/edit 1.25/export passes for the
same 45-control-point/15-face input. Raw edited FBX has one parent marker, both
Bone Models under it, and all 87 positive Cluster associations numerically equal
to the source. Three real Blender negative controls reject parent UID tampering,
duplicated realization and Bone reparenting. Original bytes and edited scene,
Bone rest matrices/parents/deform flags remain unchanged by export.

One independent GPT-6.1 SOL/medium review found a single-root world-parent
compatibility regression. It was fixed and focused tests cover it; no further
actionable finding. Editor/NUnit runtime is NOT_RUN, as Unity is allocated to
another owner. No root substitution or weight epsilon change was introduced.

Next concrete gate: use the exact locally prepared output after the parent
assigns a Unity slot; run the existing ordinary import/Finalizer and adjacent
tests, observe root/parent transport separately from strict influence equality,
and preserve source, project and lease. A SOURCE_MODEL_WEIGHTS_CHANGED refusal
would be a separate source-default/edited-weight boundary, not success or an
authorization to weaken equality. See transferred-parent-transform-export.json.


### Actual shared-parent Unity gate (2026-10-09)

The parent assigned a slot and the exact prepared package was normally imported
in the existing leased Avatar pool project with the existing roundtrip probe.
Apply rejected `EDITED_ROOT_INVALID`: original rootBone remains witnessed source
UID 251529238 (fileID 2606333175405744531), while the edited native importer chose
the sibling UID 763348336. Both imported edited bones share the uniquely marked
parent; both original bones share source parent fileID 7617400270062902505.
This observes parent receipt transport, not complete consumer acceptance: the
actual root equality guard executes before the new parent hierarchy validation.

Native positive-weight counts are source-default 60 and edited 87. The influence
guard was not reached because root validation rejected first. Keep these two
boundaries separate; do not retune either guard or rewrite historical refusal.
No Variant was created, so ancestry/reload/returned geometry 1.25 are NOT_MEASURED.
Source FBX/meta bytes after Apply, all 2,834 pre-existing project files after
restoration and exact package bytes remain unchanged. Editor exited normally
with code 1, owned child tree is empty, project lock is absent; formal pool lease
and shared mutex were released before further record/review work. Compiler
errors zero. No SDK/private logs/project files are published.

One fresh SOL/medium review limited to the new observer found three P2 issues:
Error-versus-Exception reason capture, optional observation obscuring post-Apply
invariance, and legacy fixed-package precedence before explicit selection.
All were corrected locally; product plus observer reference compilation passes.
Corrected observer was not rerun in Editor; the formal actual reason is retained
separately from the unchanged runtime JSON. See
transferred-parent-transform-unity-refusal.json.

Next product seam is the proven difference between original and edited native
rootBone selection, followed separately by the source-default/edited weight
comparison. Current strict root/influence guards remain unchanged; root identity
transport is not complete. No new runner/schema or fabricated Bone was added.


## Source Skin root selection: Cluster connection-order correction

The previous `EDITED_ROOT_INVALID` refusal is causally isolated to the generated
FBX's Cluster-to-Skin OO connection sequence. Source Skin sequence is Bone UID
`763348336`, then `251529238`; Blender's generated sequence was reversed. Existing
exact Bone receipts map both identities; both remain siblings under source Null
UID `51419677`. No parent substitution or Bone reparenting is needed.

Three exact-FBX controls changed only the named row/object sequence (and required
package hashes). Model object order alone and Bone-to-parent connection order alone
both retain the incorrect native root `763348336`. Those approaches were reverted.
Changing only Cluster-to-Skin OO row order produces the original native root
`251529238`. This establishes a bounded causal result for this input; it does not
assert Unity's undocumented root-selection algorithm for all models.

The producer now reads the original selected Skin's ordered cluster membership,
resolves generated clusters by existing exact Bone realization receipts, and
reorders only those existing connection positions in its private staged FBX.
All other FBX values and links are verified against the expected parsed graph
before replacement. Missing/duplicate/unknown identities refuse. The operation
is scoped to the established SourceKind shared-parent route. Finalizer root,
hierarchy, index, matrix and weight guards, Bone parenting, source inputs, and
manifest schema are unchanged.

Fresh normal Blender import/save-reopen/1.25 edit/export succeeds. Source FBX/meta,
Scene, hierarchy/rest/deform and all 87 raw positive associations are preserved;
tampered-parent UID, duplicate realization and reparenting controls reject.
Normal Unity package import and existing Apply now match native root UID
`251529238`, then formally reject `SOURCE_MODEL_WEIGHTS_CHANGED`: original native
60 positive associations versus edited 87. No Variant is produced; Unity shape
multiplier and full Skin roundtrip remain unverified. Zero Material slots make
Material/Texture acceptance inapplicable here. This remains separate from the
ThreeMaterial replacement and override/winding work.

Owned Unity exits normally with code 1 for the refusal; all 2,842 protected files
are unchanged, owned children and project lock are absent, and pool/mutex are
released. Independent GPT-6.1 SOL/medium product review reports no actionable
findings. Focused tests cover receipt-based ordering, original row preservation,
incomplete/duplicate links and wrong semantic roles.

Public safe evidence:
[transferred-cluster-order-root-cause.json](../../../tests/evidence/remapped_model_replacement_export_20261008/transferred-cluster-order-root-cause.json).
The next unresolved product boundary is source-default/edited weight parity
60/87; root-order correction does not authorize relaxing that guard.


## Source-default versus exported weight authority boundary

Fresh observation of the actual normal Blender output identifies all 27 extra
native influences: source Bone UID `763348336`, CP3 through CP29, nine positive
levels from `1e-9` through `0.000999`, three CPs per level. Every one already
exists in the original raw FBX and survives Blender import/edit/export. Native
CPs are joined using the fixture's complete unique UV labels and exact Bone
receipts; array order differs from CP order and is not used as identity.

The original normal Unity import retains 60 positives, while the generated
model's existing exact-revision preservation policy retains all 87. The existing
same-FBX no-policy/policy/repeated-policy causal control reproduces 60/87/87.
The actual package's 87 native associations match the raw CP/Bone set, and all
87 expected bits from the existing bounded M5 model match (zero mismatches).
There are also 21 changed shared values because the original drops the small
influence and retains its remaining Bone at weight one.

The refusal is the Finalizer's `SameSkinInfluences(originalNative, editedNative)`
gate, which compares two different import policies. Product weights are already
authoritative from Blender under the approved specification. Neither removing
this gate alone nor treating a policy-applied original witness as final-state
authority proves the required exported retention and bitwise representation.
Production tasks currently lack authoritative CP correspondence, canonical
exported influences and expected bits; the diagnostic numeric model is not a
production consumer. Independent SOL/medium review confirms this boundary.

Minimum complete repair: carry only the necessary exported Mesh/CP/Bone,
revision/policy and expected-bit data through existing producer/Finalizer paths,
then replace the incorrect weight-authority comparison with exact retention and
bitwise validation. First prove the smallest generic CP mapping; do not require
users to carry fixture UV labels. No new runner/framework, root substitution,
reparenting, tolerance change, tiny-weight deletion or original-data rewrite is
proposed. The earlier no-new-schema scope cannot provide that absent data.

No product change is claimed at this checkpoint. Apply still formally refuses
`SOURCE_MODEL_WEIGHTS_CHANGED`, root UID stays `251529238`, and no Variant exists.
Owned Unity exits normally with code 1; 2,850 protected files are unchanged,
children/lock absent, pool/mutex released. Client validation is NOT_RUN. Further
Unity launches await the newly prioritized shared slot.

[Exact grouped values and scope](../../../tests/evidence/remapped_model_replacement_export_20261008/transferred-weight-authority-boundary.json).

### Exported-weight authority connected — bounded product PASS

The shared-parent SourceKind producer now carries exported canonical CP/Bone
receipts, raw/expected float32 bits and hash-bound noop/stamped validation copies
through the existing task. Internal spare-UV CP labels require no user fixture
labels or Unity preparation. The Finalizer requires this evidence here, checks
the selected raw FBX Mesh/Geometry/Skin/Cluster/Bone graph and arrays directly,
proves canonical CP labels and validates exact native positive retention and
representation in an owned copy under the existing revision-bound policy.
Original/noop/stamped/restored copy snapshots retain Mesh identity, geometry,
bindposes, weights, existing UV and Shape data. Root, hierarchy, rest, layout and
Variant separation guards remain; other SourceKind routes keep existing checks.

Normal import, save/reopen, 1.25 edit and export complete through ordinary Unity
import and ModelSkin Finalizer Apply, including repeat Apply with identical
Variant bytes. All 87 positives match exported expected bits on 45 CP; original
normal native import still reports 60 separately. Root UID remains 251529238.
One-ULP, missing evidence and normalized-equivalent raw factor-two changes
refuse and preserve Variant/manifest. Canonical CP-label mutation and exhausted
decoding budget refuse in focused production-reader calls. Reference compile
and 23 focused Python tests pass. Two independent SOL/medium review passes
produced four findings, all implemented and exercised; no third review was run.

Owned Unity exits with code zero; 2,879 pre-existing protected files are
unchanged, input preserved, owned children/lock absent, pool/mutex released.
This input has no real Material slots or Texture assets; Unity built-in default
Material is preserved. Client validation is NOT_RUN. This is bounded Skin
success, not complete product/Avatar coverage. ThreeMaterial replacement and
old override/winding remain separate. No SDK, purchased asset or private log
is published.

[Public result and precise limits](../../../tests/evidence/remapped_model_replacement_export_20261008/exported-weight-product-roundtrip.json).

### Shared-parent Skin and existing Material/Texture combined — one-case PASS

The next unproved integration edge now has one bounded result. Reusing the
existing first-party Skin and Material/PNG fixtures, one no-Prefab input with
explicit remap completes normal Blender import, save/reopen, 1.25 geometry edit
and export, then ordinary Unity import and existing ModelSkin Finalizer Apply.
All 87 exported influences on 45 CP retain exact expected bits; all 15 native
triangle indices and Material face association match, Material GUID/fileID and
the same PNG GUID/fileID in `_MainTex`/`FutureTexture` are preserved. Original
root, shared-parent hierarchy, bounds, source and separate edited Variant remain
valid. Repeat Apply leaves Variant bytes unchanged. Existing negative controls
also pass; numerical policy and product guards are unchanged.

Initial synthetic construction omitted the Material ObjectType definition from
the zero-Material FBX. Native source used Unity default Material despite explicit
remap, while Blender/export selected the intended one. Additional observation
fields isolated this before changing any assertion. Reusing the working authored
Material definition/count fixed the input; the same strict assertions now pass.
Skin geometry, UV, weights, cluster/bone/rest/hierarchy data remain canonical
exact in the derived input. No product source correction was needed. This is
one corrected combined case, not a new fixture matrix or general importer rule.

Owned Unity exits zero; 2,909 pre-existing files and input package are unchanged,
owned children/lock absent, pool/mutex released. Existing binary inputs/outputs
and private logs remain local. Client validation and whole-product/Avatar
acceptance are NOT_RUN; other historical limitations remain separate.

[Combined public evidence and failure diagnosis](../../../tests/evidence/remapped_model_replacement_export_20261008/combined-skin-material-texture-return.json).

### Semantic Bone Merge equivalent deformation setting — source repair

Following the combined Skin/Material/Texture core proof, the next independent
§11 defect was reproduced in existing Bone Merge: equal Rest/current Pose
allowed a deforming B Bone to map to a non-deforming A Bone. Rest Apply passed,
but equal later 0.5 pose translation lost 0.5 of Mesh movement. Two-line
read-only preflight now rejects unequal equivalent `use_deform`; it does not
change either Bone, transfer weights, reparent the rig or relax existing guards.
Both mismatch directions and both matching controls pass actual Blender
RED/GREEN; the existing full Bone Merge posed/parenting/rollback/Undo suite and
four nearest policy tests pass. README explains the refusal and retry.

[Concrete evidence and scope](../../../TEST_RESULTS.md).
Other campaign and release gates remain pending; no whole-product claim.


## Current installed ZIP checkpoint (2026-10-09)

Product spec section 21 now has a current installable WIP ZIP from code commit `faf451816e2a8fd7a9783fb987e5a0fe38b69486`: `vapb-faf4518.zip`, SHA-256 `2c7fab1fed092329f21dc0570d7fc89fe769078dd50c1a1a358f3e3565960f50`. Existing builder, standard installer, normal Blender route and existing Unity probe were reused; no new product runner/schema was introduced. The installed route and current Bone Merge Deform rejection controls passed. Unity normal import and Apply/repeat passed on the installed output, with unchanged protected files and all owned resources returned. The final Blender observer exited 1 because it expected seven distribution helpers instead of the Skin route's five; an offline exact set/byte check corrected that observation without repeating export. Historical evidence remains intact.

Concrete remaining clauses, rather than a blanket campaign gate:

- Sections 12/21: visible GUI acceptance. One minimal run is ZIP installation into clean Blender settings, author-owned copy import, a small vertex edit, normal export, ordinary Unity import, Japanese Assistant Apply, then selected separate Variant inspection for shape, face materials/Textures and Bone/root. Operator/handler evidence exists; actual visual clicks are NOT_RUN because this environment exposes no desktop interaction tool. No Python console or manual GUID work belongs in this user flow.
- Section 7: serialized Unity/VRC state. This first-party no-Prefab source has no representative AvatarDescriptor, PhysBone, Contact or animation references. Use one existing author-owned representative input and compare its known source/return state and references. Missing evidence here is source-to-return component preservation, not an exhaustive combination campaign. A reproduced product mismatch would justify a minimum implementation fix; the absence of a mismatch in this synthetic Skin case does not prove there is no independent implementation work left.
- Sections 14/15 and core roundtrip priority: rights-qualified real-input verification is not supplied by this first-party fixture. Verify provider terms and use an existing owned copy locally; do not publish assets, SDK or private logs. Existing private evidence remains distinct from this checkpoint.

No whole-product completion or all-Material/Avatar acceptance is asserted. The immediate GUI run and one representative component-state comparison are the next bounded evidence steps; do not expand them into every fixture combination or new verification infrastructure.
