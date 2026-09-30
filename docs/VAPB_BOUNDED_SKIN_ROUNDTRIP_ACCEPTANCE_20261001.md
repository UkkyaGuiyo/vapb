# Bounded Skin round-trip acceptance — 2026-10-01

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

**Next exact action:** capture one existing representative real source occurrence
through its supported production Export and fresh Finalizer, retaining the exact
Mesh/Bone/target receipt chain; keep unsupported relations explicit.
