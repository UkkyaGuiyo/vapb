# Bounded Skin round-trip acceptance — 2026-10-01

## External Unity Script closure and real retry — 2026-10-01

**Dependency closure proven; full representative bounded report remains RED.**

The existing `external_dependencies` array now carries exact Unity Script
references. Each record has `classification=UNRESOLVED_BUT_PRESERVED`,
`kind=UNITY_SCRIPT`, `status=EXTERNAL_DEPENDENCY_REQUIRED`, canonical lowercase
GUID, nonzero signed Int64 decimal-string `file_id`, and
`reference_id=VAPB-REF-<first32hex of SHA256(UNITY_SCRIPT:guid:file_id)>`.
`required_by` carries declaring asset GUID, exact SHA256 and signed component
localID. Collection follows selected Skin tasks and serialized class1001 source
Prefab chains, excludes unrelated Prefabs and contained providers, and deduplicates
and sorts exact pairs/contexts. No additional registry or SDK hardcoding.

Before witness/import or Variant mutation, Finalizer validates source/context
revisions and class114 serialized references, then resolves exact MonoScript
GUID/localID through public APIs. Absent/wrong providers explicitly refuse;
invalid/conflicting/stale/unrelated declarations refuse without mutation.
Additional undeclared missing scripts keep the generic missing-script failure.
No-declaration manifests retain their existing behavior.

Unchanged old Output bytes, with exact locally proven SDK3.10.5 providers,
resolve missing55→0 and actual Apply/repeated Apply succeed. Earlier three-provider
counts meant distinct provider GUIDs; the regenerated manifest correctly records
six distinct GUID/signed-localID pairs. Provider binaries remain outside both
output and repository. Public production collector/writer output declares one
reference, is byte-deterministic and preserves source bytes. Actual Unity import
proves no-provider refusal/no mutation/no Variant, then exact provider later
resolves the same Package/manifest and initial/repeated Apply succeed. Ten public
controls cover identity/revision/declaration failures and undeclared missing scripts.

Real normal ACTIVE export declares six pairs. Fresh no-SDK Unity measures
missing55/resolved0 and explicit refusal/no mutation/no Variant. Exact provider
resolves6/6/missing0; actual Finalizer/repeat and source/sibling/count preservation
PASS. Exact public-API source GUID/GO/Transform/PrefabInstance relations bridge
five nested renderer-free nodes: all276 semantic nodes/parents, selected owner,
Mesh,160 ordered Bones and root representation are EXACT. Explicit triangles,
CP bridge, topology and sampled surface are EXACT. Skin6010/6010 bitwise
influences PASS;948 raw differences and deformation UNMEASURED remain. Shape N/A.

The remaining mandatory real RED is Material face association: imported native
submesh partitions exchange slot0/2 while Finalizer retains the source Material
array. Public three-slot FBX→Unity permutation is reproduced; an exact transport
binding is required. UV float32 CP sets differ322/2360 and remain a separate
diagnostic boundary, without epsilon/comparator relaxation. Normals differences,
Tangents UNKNOWN and unsupported contexts remain separate.

Five real subject-corruption controls reject; they do not imply a positive full
acceptance result. Python524 PASS; compileall and actual Blender triangle/
Skin/Shape/UV/Material/IDs regression PASS. Real injected rollback, Object rename/
save/reopen and immutable original blend/Package PASS. Private assets, identities,
provider paths and raw evidence remain outside the repository. Continue from
public Material RED to minimal fix and same representative real recheck.

## Result and scope

**PARTIAL overall. Public bounded round-trip PASS. Real full round-trip UNSUPPORTED.**
Starting remote: `f9ad8a078133a2bffdc739a4e1189fb5d6d3ad20`.
No production behavior, importer policy, weight model or epsilon changes.
No main merge, release, tag or ZIP in this mission.

This is the existing **direct, explicitly confirmed Skin Renderer/Bone** route.
The initial fixture makes explicit user choices, then preserves authoritative
native receipts across rename. It does not claim automatic source/native matching.
Native Mesh remains under its native rig. Renderer-owner EXACT means the source
serialized GameObject, observed semantic carrier and confirmed occurrence receipt
agree; it does not claim automatic native reparenting/attachment restoration.

The numeric Skin report still says source Renderer owner **UNMEASURED**. The joined
report obtains owner EXACT from the independent source/hierarchy evidence. Nothing
rewrites the numeric report to pretend it observed ownership.

## Minimal evidence join and identity domains

No registry, new runtime service or name-based matching was added.

| Domain | Existing authority consumed |
| --- | --- |
| Source | Exact Package SHA, Prefab bytes SHA, Prefab GUID, signed Renderer/owner fileIDs, serialized Mesh reference and source FBX hash |
| Occurrence | Selected root context ID and occurrence ID from persistent projection/confirmed binding; direct root, no nested instance edge |
| Native | Mesh realization ID, hash-bound Mesh receipt on Object/data, Armature Object ID, Bone realization receipts and parent relations |
| Export | Recipe task realization ID, generated model GUID, actual generated FBX SHA, exported Bone markers |
| Unity post-import | Public API Mesh GUID/signed localID, target Renderer/owner IDs, ordered Bone target IDs, rootBone ID, marker-to-task correspondence |

The exact Blender capture SHA is also retained by Unity's capture, so a changed
capture cannot be silently joined to old Unity evidence. Source Package bytes are
hashed on both sides. Source serialized Mesh reference and FBX bytes are checked
against the recipe and native receipt. Semantic parent maps are independently
compared with package YAML, Blender actual parent handles and Unity public API.

Source, occurrence, export and post-import identities remain separate. This
preserved-source fixture is a bounded proof; it does not impose source Mesh lineage
on normal Blender-final-state exports or geometry replacement workflows.

## Public actual path

The wholly first-party `blender_skin_package_test.py` fixture was reused. It imports
through normal VAPB, confirms Renderer/Bone choices, edits geometry and weights,
authors a diagnostic CP UV on its final editing state, renames Objects/Bones,
saves/reopens, and calls production UnityPackage export. The diagnostic channel
is fixture data, not a new production setting.

- Source semantic parent/owner, native Mesh receipt, Armature relation, ordered
  Bones and rootBone: EXACT in this direct confirmed route.
- Raw generated FBX polygons: all explicit triangles. Existing CP comparator:
  topology, sampled surface, CP correspondence and effective Material partitions
  EXACT. Existing finite-sample/tolerance geometry rules remain unchanged.
- Skin: 52 positive CP/Bone influences retained, missing0, representation52/52
  BITWISE_EXACT, unexplained0, max expected/actual ULP0. Small positive weights
  retained. In this combined control raw changed0; prior raw-difference controls
  remain independently tested and are not relabeled.
- Disposable staged numeric rows: **UNMEASURED**; no invented B1 evidence.
- Shape: **NOT_APPLICABLE** (no Shape Keys in this combined fixture). Wrong-Mesh
  Shape subject is rejected even for N/A. Existing native Shape staging regression
  ran separately and PASS is not promoted to combined Shape proof.
- Fresh Unity2022.3.22f1 imported Output Package alone; Finalizer first/repeated
  Apply, exact target/mesh resolution, preserved Bone/Material/state, invalid
  mapping rejection and idempotence PASS.
- Same editing Mesh/rig: source success immutability and real injected staged-skin
  FBX failure rollback PASS. Full semantic graph and source geometry/weights remain
  unchanged. A second all-Object/all-Bone rename, save/reopen and Unity capture
  rerun keeps the exact entity key and PASS unchanged. No Unity identity renamed.
- Deformation metric here is CPU expected vs Unity BakeMesh in the existing
  Finalizer pose control: measured error0. It is not Blender/Unity arbitrary-pose
  equality and does not erase the earlier measured nonzero differences.

## Fail-closed composition

`tests/bounded_skin_roundtrip.py` requires subject equality per dimension before
consuming that dimension's checks. Independent PASS reports without subjects are
CROSS_EVIDENCE_IDENTITY_UNPROVEN / UNSUPPORTED. Conflicting subjects are RED.
Missing mandatory checks or unsupported Skin context cannot PASS. Lower-level
Skin acceptance is recomputed using the existing approved reducer.

Ten controls on the actual joined capture all reject: wrong package revision,
occurrence, export Mesh, stale FBX, owner, rootBone, Geometry export revision,
Material Renderer, Shape Mesh and repeated-instance occurrence collapse. Ordered
Bone corruption and mandatory Finalizer failure also reject in focused tests.
No display-name, list-order, candidate-count or aggregate-count acceptance exists.

## Bounded real intersection

Two previous numeric cases retain 6636/6636 BITWISE_EXACT, missing0, raw changed1002
and independently measured nonzero deformation. Their existing source baseline
was identified by exact .blend SHA and Package SHA; immutable selection links
both source occurrences to their diagnostic D1 FBX revisions (**2 partial joins**).
No private identifier/path/raw row is published.

However these D1 experiments exported standalone diagnostic FBX, with no matching
production Finalizer task/target/Apply capture. Original source Bone slots cannot
be equated with exported native Bone indices by order. The complete ordered-Bone
bridge and Unity target relation remain unproven. Thus **full joins0/2, full
round-trip UNSUPPORTED**. A source/export subset is not full round-trip PASS.

This is an evidence coverage gap, not proof of a production regression. Neither
an unrelated Hierarchy PASS nor numeric PASS can fill the missing relation.
Recapturing a complete real production Export/Finalizer path is still required;
this mission did not broaden into private Avatar/component restoration.

## Retained boundaries

- Prior raw Skin difference and nonzero deformation remain visible; the public
  numeric183 and real6636 controls retain their original separate metrics/poses.
- Normals: earlier known differences remain; not measured by this joined capture.
- Tangents: UNKNOWN. Import-preview nonplanar discrepancy remains separate.
- Unsupported version/numeric contexts, including subnormals, cannot PASS.
- No whole-Avatar, all-VRC-components, arbitrary-pose, all-Unity-version or general
  visual-harmlessness claim. Surface samples are not a continuous surface proof.

## Reproduction and engineering evidence

Use the repository parent as Python working directory, or explicit parent
PYTHONPATH. Blender CLI uses factory startup and `--python-exit-code 1`.

1. Generate synthetic source FBX with existing Skin fixture `--prepare-fbx`, then
   Unity `VapbSkinRoundtripProbe.Prepare` to generate Source Package/SourceInfo.
2. Run `tests/blender_skin_package_test.py -- <fixture-folder> --small-weights
   --bounded-capture` through Blender5.2.1. Output includes exact captures/recipe.
3. Prepare a fresh Unity2022.3.22f1 project with the existing production helpers,
   both `unity_skin_roundtrip_probe/Editor` capture scripts, Output Package,
   Source Package/SourceInfo and BoundedBlender capture. CPChannel.txt contains
   the explicitly authored capture marker_channel; SmallWeights.flag enables
   the existing tiny-weight control. Run `VapbSkinRoundtripProbe.Validate`.
4. Blender executes `tests/blender_bounded_skin_compare.py -- <fixture-folder>
   <fresh-unity-project> <external-report.json>`. Non-PASS exits nonzero.
5. Repeat actual rename/reopen observation, use `VapbBoundedSkinCapture.Run`, then
   rerun comparator. This Run is read-only except the existing idempotent Apply
   on the synthetic project and external capture file.
6. Pure module `tests.bounded_skin_roundtrip` sanitizes full report + bounded real
   intersection + existing numeric aggregates + negative-control result into
   the committed measurements JSON. No private subjects are copied.

Public join RED before implementation, then GREEN; cross-evidence controls10/10
reject. Focused report/Skin/Hierarchy39 PASS. Full Python517 PASS, compileall PASS.
Actual Blender Skin export, triangle/Skin/Shape/UV/Material/IDs, injected rollback
and reopen PASS. Fresh Unity application and repeated capture PASS.

The first isolated full-suite attempt had one existing SHA-bound synthetic .meta
fixture changed to CRLF by checkout. Restoring only its exact committed LF bytes
made the full suite PASS; no tracked fixture change or test weakening.

Independent scope review: one Important aggregate mismatch (staging falsely
EXACT) was fixed by regenerating actual evidence; a regression observed RED first,
then GREEN with staging UNMEASURED. A final follow-up review returned
PASS — no unnecessary implementation found. No excess production changes identified.

[Actual sanitized report](../tests/bounded_skin_roundtrip_measurements.json).

**Next exact action:** resolve the undeclared external SDK prerequisite before retrying this exact output through the existing Finalizer.


## Representative real production closure attempt — 2026-10-01

**PARTIAL; one real production export/import captured, complete joins 0/1.**
Starting source commit `9bd2a26418b5bcf63d1968869cef4513c2d0214e`.

The two existing numerically measured occurrences were checked against the
current model-derived Skin route. Both prepared; the occurrence with no Shape
Keys was selected to avoid an additional unsupported Shape comparison. Selection
used the existing exact occurrence, source Mesh reference and native receipts,
not displayed names or Object order. Private identity and all capture scripts,
Package bytes, raw reports and Unity logs remain outside Git.

The ordinary `export_scene.vapb_unitypackage` ACTIVE route produced a Package
with one `RESTORE_DIRECT_SKIN_VARIANT_V1` task and 160 Bone mappings. Its output
contained 257 assets, including the four generated first-party support scripts.
The source scene hierarchy snapshot and original Package bytes were unchanged;
the immutable source blend was never saved. No diagnostic marker was added to
the editing source. No old diagnostic D1 FBX was used as the acceptance artifact.

An isolated Unity2022.3.22f1 project imported only this actual output Package.
The Finalizer compiled with zero C# errors and was actually invoked. It returned
false with `PREFAB_UNAVAILABLE_OR_MISSING_SCRIPT`. Public Unity API counted 55
missing MonoBehaviours in the loaded source hierarchy. The directly serialized
Prefab had 51 script components referencing three distinct script asset GUIDs;
none had providers in the output. The manifest's `external_dependencies` was
empty. A bounded read-only check of all relevant `.meta` files in the known
primary VRC Oracle found three exact GUID-matching DLL providers, belonging to
`com.vrchat.base` and `com.vrchat.avatars`, version3.10.5. Searching only C# script
meta files initially missed the DLL providers; the complete meta check corrected
that finding. Attribution comes from GUID matches and provider package manifests,
not from avatar appearance. The output still does not declare this prerequisite.

This is a supported-scope/dependency blocker, not proof of a Mesh/Bone numerical
regression. No scripts were removed, no source Prefab was rewritten and no
undeclared framework or original source Package was preloaded to force a PASS.
Broad component restoration and shader work remain outside this mission.

Consequently target resolution, ordered target Bones/rootBone, effective
Material association, CP/topology/surface comparison, Skin numeric acceptance,
first/repeated Apply and the combined real report are **UNPROVEN**. No real
positive capture exists, so the five real evidence-corruption controls were not
run. Shape is N/A for the selected occurrence. The second case was not exported:
the required first complete PASS gate was not reached. Historical numeric
6636 PASS and public combined PASS remain separate prior evidence.

Current verification: Python517 PASS using repository-parent context and
`unittest discover -s unitypackage_blender_importer/tests -t . -p "test_*.py"`;
compileall PASS. Actual Blender5.2.1 triangle staging regression PASS, including
Skin, Shape, UV, Materials, Export IDs, shared datablock preservation, success
immutability, injected rollback and save/reopen. Previous same-source-commit
public Skin package/Finalizer/repeated Apply captures were reused rather than
claimed as a new real result. Production/code changes NONE.

The initial test invocations exposed two harness errors: discovery without
`-t .` lost relative imports; Unity `-quit` exited before asynchronous Package
import completed. Corrected discovery passed all 517 tests. A further disposable
Oracle reload lost its import callback; after import completion and an idle
batch restart, the final dedicated Apply invocation compiled and emitted the
explicit rejection above. These harness errors are not production regressions.
