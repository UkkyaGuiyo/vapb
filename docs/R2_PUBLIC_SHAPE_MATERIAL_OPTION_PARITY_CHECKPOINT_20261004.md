# Public Synthetic Skin/Shape Material Option Parity Checkpoint

Date: 2026-10-04
Status: bounded verification checkpoint; not a Stage 3 release gate

Project: VAPB
Repository: `https://github.com/UkkyaGuiyo/vapb`
Branch: `feature/r2-material-slot-reorder`
Tested repository SHA: `064ed9adfac28fba1c7f5155a799eee055c5188c`
Run ID: `shape-material-parity-run-20261004-01`

## Public synthetic fixture

The fixture was authored for this test from a Blender-generated FBX with one source SkinnedMeshRenderer and three asymmetric Shape channels. Unity 2022.3.22f1 created a public `.unitypackage` containing a prefab with two local SkinnedMeshRenderer occurrences sharing one Mesh. The occurrence weight arrays were `[25, 60, 0]` and `[75, 0, 35]`.

- Source FBX SHA-256: `636b43cce69d40e2cf47b0c5d287db39045951e6873d10397619c7bf2ff73ab2`
- Source FBX metadata SHA-256: `5055177f4ec62abb691058ba211f69ef1c7fc89fbc2202d2fb8c6712b3e25cfe`
- Unity package SHA-256: `9020b4f5072bc862169126c72fc35bcd8799879be23c4ad589ffc830e82d68ef`
- Promoted optional v3 witness SHA-256: `60e82d1f45d148d9ac6518d764bdb3ec75c05dd1caab6cf9ea42813e872a1e71`

Three fresh, run-owned Unity projects were used in sequence: creator, bone witness, and Shape controls. Their Editor methods all exited `0` with their expected PASS markers. Each project used Unity `2022.3.22f1`, an empty package dependency manifest, and registered zero UPM packages; no Test Framework, SDK, or other package was added. The creator's `FixtureShapeObservation.json` supplied the independent public-API observation to v3 promotion. A separate Unity package-reimport oracle and the unused hierarchy package observation were omitted. This run does not claim a fresh Unity reimport observation.

## Blender parity result

Blender `5.2.1 LTS` ran the real package import operator once with Materials enabled and once with Materials disabled. Both modes passed checks for the two occurrence weight arrays, witness-mapped Shape channels, Skin pose matrices, evaluated world geometry, and Spine attachment motion against the bone-world delta. The attachment delta used a tolerance of `2e-5 + 1e-6 * matrix_scale`. Each mode was saved and reopened, and its state was compared after reopening. The final Materials ON/OFF comparison passed with exact integer identities and float tolerance `2e-5 + 1e-6 * max(abs(expected), abs(actual))`.

The Blender result report recorded `materials_on_off_parity=true`, `saved_reopen_parity=true`, and both occurrence weight sets. A default temporary-directory attempt failed before package import; the preserved retry used a task-owned temporary directory through process-local `TEMP`/`TMP` and passed. Unity and Blender raw logs, absolute local paths, and the complete run manifest remain outside this repository.

## Remaining material-resolution warning

Materials ON completed the operator and passed the Skin/Shape/pose parity assertions, but its log reported two unresolved dependency records and a scene import warning. Materials OFF reported zero unresolved records. This runner does not assert full Material dependency resolution, so this checkpoint makes no claim that the Materials ON scene outcome was overall `SUCCESS` or that all Materials were restored. Read-only inspection of the saved Blender dependency registry and exact Unity package identified both records. They are two occurrence-scoped `PREFAB_RENDERER_MATERIAL` references at slot 0, each with target GUID `0000000000000000f000000000000000` and file ID `10303`; each belongs to one of the two prefab-local SkinnedMeshRenderer occurrences. The package contains the FBX and prefab, but no Material asset. Both prefab renderer records explicitly point to Unity's built-in default Material identity, which is not a package-local provider. The records therefore describe an intentional fixture reference to an external built-in provider, not a missing Material payload accidentally omitted from this `.unitypackage`. VAPB's registry currently preserves but does not resolve that built-in Material reference, so Materials ON retains an unresolved dependency warning for this fixture. This bounded fixture result is not evidence of a product bug in packaged Material resolution, and it is not proof that built-in Unity Materials are reconstructed. SOL medium read-only review was requested to check this classification. Raw occurrence/realization IDs and paths remain only in the local run evidence.

## Existing Stage 3 project preservation

The pre-existing Stage 3 Source and Target project stable-file inventories were unchanged across this run:

- Source: 46 files; inventory SHA-256 `7921e3b841c160f021be376d9789c2acb0c024d20ce3f30f98e6da551860a553`
- Target: 85 files; inventory SHA-256 `c379c09945df0a94af07b6043ad6d8bd9ad811f0c7ab04e224d5e4fd38f3524d`

Generated Unity caches, logs, and user settings were excluded from these stable-file inventories. No existing Source/Target file was overwritten by the Shape run.

## Separate Finalizer compatibility/bounds verification gate

The latest saved Finalizer compatibility route is in commit `2dafab28190abebb49d5021594969337dd9fa54a` (legacy same-index-layout routing and compatibility coverage). The bounds/frame implementation was checkpointed in `c6cf3fd0442b61ad3b1ba905d4c510e5c2ac2755`; status clarification is in `8078d063b8f416c309cceb18a42f56853eb160fd`. These changes are present in the tested branch history, but this Shape parity run did not execute the Finalizer, `Apply`, native FBX topology, bounds rejection, first/repeat Apply, or the Finalizer NUnit suite. Those Stage 3 Unity checks remain a separate gate and are not upgraded by this result. The existing limited-GREEN design checkpoint continues to mark the route as not Unity-verified.

## Scope

This evidence applies only to the self-authored public synthetic fixture and the Skin/Shape/pose parity assertions above. It is not a general avatar, VRChat, or full Material-restoration roundtrip claim. The optional v3 witness is test evidence and is not a requirement for normal user imports. No purchased material, private corpus, existing user Unity project copy, license change, or credential change was used.
