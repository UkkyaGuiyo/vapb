# VAPB Test Results and Checkpoints

## Latest checkpoint: 2026-10-04 R2 Stage 3

- Public-safe implementation checkpoint: canonical decimal-string material slot indexes with Unity JsonUtility exact invariant comparison; scanner removed.
- Blender 5.2.1 background regressions: 64 passed. C# reference-only compile passed; Unity Editor compile and EditMode tests remain unrun.
- Unity JsonUtility raw-number coercion and duplicate-key behavior remain unverified. Stage 3 is not proven complete or release-ready. See [R2 Stage 3 checkpoint](docs/R2_STAGE3_CHECKPOINT_20261004.md).

## 0.4.0 candidate Centered Import Loading Overlay (2026-09-17)

- Overlay unit coverage: 8 tests PASS for draw-handler registration, 3D View area fallback from non-3D contexts, RNA-area pointer matching, redraw on state updates, dominant Japanese loading copy, FBX blocking warning copy, sink lifecycle, and stale-handler cleanup.
- Blender 5.2.1 foreground synthetic E2E: `PCA_FOREGROUND_AUTOMATIC_OK`; actual draw callback count and timestamp were nonzero, GPU drawing was reached, and the handler was removed after COMPLETE.
- Real local foreground diagnostic: draw callback, valid `VIEW_3D` `WINDOW` region, GPU drawing, and handler removal were observed. The attempted real SAMPLE_AVATAR_B run stopped at an existing unrelated `NO_SUPPORTED_PREFAB` ambiguity after sibling discovery; this is not counted as a successful SAMPLE_AVATAR_B import.

## 0.4.0 candidate Import Progress Monitor (2026-09-17)

- IPM-001..015: PASS. The Blender-independent state model covers IDLE → WORKING → COMPLETE/FAILED, factual current/total, grouped-child ownership, unknown-duration indeterminate state, heartbeat refresh, and pre/post native FBX blocking callbacks.
- Python discovery after the new focused coverage: 143 tests PASS. `python -m compileall -q .`: PASS.
- Foreground synthetic Blender E2E: `PCA_FOREGROUND_AUTOMATIC_OK`; the captured history includes package read, Prefab analysis, related-package resolution, FBX, visuals, hierarchy, resolver, finalization, and COMPLETE. Prefab chooser invocation remained 0 and no active monitor remained.
- Real local foreground verification: `REAL_FOREGROUND_PROGRESS_OK`; the local SAMPLE_AVATAR_B package was supplied only through the runtime argument, producing 15 reconstructed Prefab meshes, 71 node materials, 57 Base Color links, one blocking-FBX interval, elapsed 111.85 seconds, with 400 recorded progress snapshots including timer heartbeats. The resolved related-package action was selected as Import Together by the local harness; proprietary assets remain outside the repository.
- Real local explicit chooser/import control: `REAL_MULTI_PACKAGE_IDENTITY_OK`, 38 object records, one package identity, `PREFAB_1`; no production asset or path was committed.

## 0.4.0 candidate Prefab Candidate Analyzer (2026-09-17)

- `PCA-001..015`: synthetic analyzer tests PASS in Blender 5.2.1. Structural classification, exact visual closure, transitive Material→Texture, cross-package provider, ambiguity refusal, cache reuse, and FBX payload non-read were verified.
- Foreground synthetic Automatic E2E: `PCA_FOREGROUND_AUTOMATIC_OK`. A leading empty candidate did not cause first-entry selection; the only supported visual candidate imported and the Prefab chooser invoke count was 0.
- Existing grouped split-package regression: `GROUP_IMPORT_E2E_OK`; explicit `PREFAB_N` selection remains compatible.
- Real SAMPLE_AVATAR_B metadata-first AUTO probe: 8 Prefabs analyzed; one `AVATAR_LIKE` / `COMPLETE` candidate was selected with `ONLY_COMPLETE_AVATAR_CANDIDATE`. Foreground progress and grouped import are covered above; Material Preview appearance remains a separate human visual check.
- Real SAMPLE_AVATAR_B background import reached `Import complete` with `Sibling discovery: COMPLETE providers=1`; the existing identity probe still has a harness-level package-id assertion failure after grouped child import and is not counted as a full identity PASS.
- Real CaseA control: AUTO correctly stopped with `USER_CHOICE_REQUIRED / NO_UNIQUE_COMPLETE_AVATAR_CANDIDATE` for 15 detected Prefabs; explicit `PREFAB_1` completed (`REAL_MULTI_PACKAGE_IDENTITY_OK`, 38 Objects, one package identity). This confirms no unsafe first-Prefab fallback. Material Preview/normal-map visual confirmation remains human-required.

## 0.4.0 candidate Real Multi-Package Visual E2E (2026-09-15)

- 初回synthetic A→B診断: B Material/Image discovery 1/1、Image node 1、Renderer slot 0、cross-package reuse 0。Texture extraction/loadは成功しており、Prefab GameObject名とFBX import後の`.###`付きObject名の不一致で空placeholderがmapping対象になったことを特定した。
- 修正後: `MPV_SYNTHETIC_OK`、B Renderer slot 1、B Image node 1、cross-package reuse 0。exact nameを優先し、base nameが一意な場合だけ`.###` suffix fallback、曖昧な場合は拒否する。
- `MPV-001..011`: synthetic A→B visual binding、同名Material/Texture isolation、Prefab GUID、externalObjects、ambiguous-safe lookup、save/reopenをPASS。`MPV_REOPEN_DIAGNOSTIC`でB package identityとslot保持を確認する。`MPV-012`は別実行したMPI-017、Blender integration、Python、compileall、real-package regressionの結果を根拠にPASSとする。
- 実Package A+Bの第二Packageは本作業で一意に指定・確認できていないため、`MPV-REAL-001`のForeground Material Preview/二Package目視確認は`HUMAN RETEST REQUIRED`。実Package A単体の既存回帰は下記の通りPASSであり、A+B PASSとは扱わない。
- Exporterとreachability pruningは仕様を追加したのみで、実装・roundtripは未実施（PLANNED / UNVERIFIED）。

## 0.4.0 candidate Multi-Package Identity / Blocker Fix (2026-09-15)

- Python: 59/59 PASS; `compileall`: PASS.
- Blender 5.2.1 LTS synthetic registry and MPI-017 save/reopen test: `MULTI_PACKAGE_IDENTITY_OK`.
- MPI-001..017: PASS through package fingerprint, scoped canonical key, propagation, reverse lookup, duplicate/legacy/ambiguous handling, collision reporting, and JSON persistence.
- Blocker fixes: fileID is never canonical without parent GUID/Asset Path; Prefab `unity_asset_path` comes from the Unity-relative `AssetEntry.unity_path`, not the temporary extraction filesystem path.
- Real Package: `FINISHED`; 113 objects / 103 meshes / 4 armatures / 40 shape keys / 112 materials / 112 images.
- Existing Material/Texture regression: 147 bindings, identity errors 0.
- Package SHA-256 measurement: 385,655,203 bytes, 490.961 ms on the verification machine; `source_package_id=sha256:PRIVATE_ASSET_ID_REMOVED`.
- Real-package identity probe: `REAL_MULTI_PACKAGE_IDENTITY_OK`; 8 Object registry records had `Assets/...` paths, with reconstructed sub-assets retaining fileID scope.
- Automatic collision resolution, multi-package merge, UnityPackage export, and foreground visual Material Preview remain out of scope for this phase.

測定日: 2026-09-15
Version: 0.3.0
対象: Blender 5.2.1 LTS / `private-real-package.unitypackage`

## Automated Verification

- Python tests: 41 PASS
- `compileall`: PASS
- Blender 5.2.1 synthetic integration: PASS
- `register()` / `unregister()`: PASS
- ZIP `testzip`: None

## Reference Package

- Import: `FINISHED`
- Objects / Meshes / Armatures: 113 / 103 / 4
- Shape Keys: 40
- Images: 112
- Material slot bindings: 147 / 147 MATCH
- Material GUID mismatch: 0
- Texture GUID mismatch: 0
- Missing filepath: 0

## BUG-002 / BUG-003

- BUG-002: CLOSED. Identity chain and save/reopen binding persistence are verified.
- BUG-003: CLOSED. 48 / 48 textured materials reach the active Material Output.
- Duplicate Principled BSDF: 0
- Duplicate Material Output: 0
- Japanese UI lookup failure: 0
- Japanese save/reopen: 147 / 147 binding MATCH, node/link graph MATCH

## VIS-010 Human Verification

PASS, user-reported on 2026-09-15 in Blender 5.2.1 Japanese UI Material Preview:

- Face / Skin
- Hair
- SyntheticMaterial / Clothes
- Gloves
- Accessories
- MAGENTA: none
- White-only rendering: resolved

## Current Limitations / Unverified

- Transparent / cutout / blend material visual path is not validated by the reference package.
- File Browser cancel/re-run, arbitrary Prefab manual selection, and normal UI Undo-key behavior are not confirmed.
- Unity shader appearance remains an approximation.
- Multi-package integration and UnityPackage exporter are not complete.

Historical 0.2.0 evidence remains under `experiment_logs/`; those files are not modified by the 0.3.0 freeze.
# 0.3.0 Baseline Verification (2026-09-15)

- Editable Texture ETX-001..009: PASS in Blender 5.2.1 integration test, including same Image datablock, same filepath, material binding, identity, `.blend` reopen, missing-source refusal, dirty refusal, packed conflict, and no copy/backup.
- ETX-010 real-package identity/reload automation: PASS; Face/Hair/SyntheticMaterial representatives present. Material Preview UI visual inspection: UNVERIFIED because Computer Use was unavailable.
- Python: 41/41 PASS. `compileall`: PASS. Synthetic Blender integration: PASS. Real package: 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 bindings / identity errors 0.
- Version metadata is `(0, 3, 0)` and this commit is the formal 0.3.0 baseline.

## External Texture Editor Baseline Verification

- EXT-001: PASS; EXT-002/003: Addon Preferences and executable validation PASS, Browse/restart persistence UI/runtime surface UNVERIFIED; EXT-004: implemented, foreground menu UI UNVERIFIED; EXT-005..009: helper/integration PASS including argument safety, missing-editor, dirty, packed, and identity protection.
- EXT-010: UNVERIFIED for foreground UI/editor pixels because Computer Use was unavailable; direct launch helper is automated PASS.
- Existing ETX-001..009: PASS maintained. Real package regression: 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 bindings / identity errors 0. BUG-002 and BUG-003 remain PASS.

## 0.3.0 Final Hardening (2026-09-15)

- Human follow-up verification in Blender 5.2.1 Japanese UI with Krita: ETX-010 PASS, EXT-003 PASS, EXT-005 PASS, EXT-010 PASS. `SyntheticMaterial_col.png` opened in Krita, saved to the same working file, reloaded from disk, and the Image Editor / Material Preview / 3D avatar reflected the edit; Krita remained selected after restart.
- Launch hardening: `launch_editor()` catches only `OSError` from `Popen()` and returns `EDITOR_LAUNCH_FAILED`; the operator reports it as `ERROR` and returns `CANCELLED`. Argument-list launch with `shell=False` is unchanged.
- EXT-001..010: PASS. EXT-011: PASS (`OSError("launch failed")` is converted to `EDITOR_LAUNCH_FAILED` without leaking to the test process; operator report is `ERROR`).
- Python: 45/45 PASS. `compileall`: PASS. Blender 5.2.1 register/unregister and External Texture Editor integration: PASS. Synthetic import/roundtrip: `BLENDER_INTEGRATION_OK`.
- Real package: `FINISHED`, 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 material bindings / identity errors 0. BUG-002 and BUG-003: PASS.
- Version remains `(0, 3, 0)`. This baseline is tagged `v0.3.0`; no GitHub Release is created in this phase.
## 0.4.0 candidate Cross-Package Dependency Resolution + Sibling Group Import (2026-09-16)

- Synthetic split-package E2E: Geometry Package（FBX + Prefab、Material 0）→ Material Package（FBX 0、Material 1）→ Texture Package（FBX 0、Texture 1）を確認。
- Geometry-first / Provider-firstの両順序で `CROSS_PACKAGE_DEPENDENCY_OK`。Material-only / Texture-only importは`FINISHED`、Material slotとTexture nodeはunique providerへ`RESOLVED_CROSS_PACKAGE`。
- `.blend` save/reopen後もDependency registry、Material binding、Texture bindingを保持。
- `unitypackage_dependency_registry`はUNRESOLVED、RESOLVED_LOCAL、RESOLVED_CROSS_PACKAGE、AMBIGUOUS_PROVIDERを保存する設計。名前だけのcross-package fallbackは行わない。
- CPD-001..006、009、011、013: synthetic PASS。CPD-007/008/010は専用policy fixture PASS。CPD-012はexternalObjectsのGUID解決policyをPASS（実FBXのslot名が不一致の場合はslot推測せず安全に未解決）。
- Sibling Discoveryの同一フォルダ限定、GUID exact match、transitive discovery、duplicate provider ambiguity、SyntheticAvatar-like `Import Together`をBlender 5.2.1でPASS。SyntheticAvatar起点でSyntheticMaterialProviderとTexture providerを検出し、3 Packageをgroup import、Geometry/Material/Texture結合を確認。
- 今回のHuman Retest Targetは実アセットをrepoへ追加せず、上記synthetic SyntheticAvatar-like fixtureで受入経路を確認。実BOOTH分割Packageのforeground確認は`REAL-CPD-001: HUMAN RETEST REQUIRED`。
- UnityPackage ExporterはPHASE Cへ分離し、PRODUCT_SPEC / ARCHITECTURE / TEST_STRATEGYの確定設計のみ。Exporter本体、Unity Finalizer、未知Component resolverは未実装。

## Distribution Pipeline Hardening (2026-09-16)

- 原因: 旧allowlistがroot `preferences.py` / `external_editor.py`をZIPから除外し、Blender enable時に`ModuleNotFoundError`となっていた。
- 修正: tracked `.py`をruntime候補とし、`tests/`、`tools/`、`experiment_logs/`のみを明示除外。future runtime directory fixtureも自動収録判定をPASS。
- Distribution tests: source/ZIP runtime set equality、ZIP CRC、root layout、asset/credential exclusion、revision-derived filenameをPASS。
- Extracted ZIPのみのBlender 5.2.1 register/unregister: `DIST_BENDER_INSTALL_OK`。
- 既存Python 63件にdistribution 2件を加え、65件PASS。CPD/SPD/MPI/MPV/通常integrationのproduction logicは未変更。

## Public Repository Hygiene (2026-09-16)

- Current tracked tree: developer path、real-world fixture identity、obvious credential、proprietary binary assetなし。generic `test_public_repo_hygiene.py` PASS。
- Real-package probe: env/CLI supplied path only。未指定時は`REAL_PACKAGE_TEST_SKIPPED`。
- Reachable history: 過去の実環境検証由来のreal-package identity / local path参照を検出。credential、private key、proprietary binaryは未検出。history rewriteは未実施で、Public化前レビュー対象。

## Native UnityPackage Drag & Drop (2026-09-16)

- Blender 5.2.1公開FileHandler APIをruntime introspectionし、`bl_import_operator`、`.unitypackage` extension、`poll_drop(context)`を確認。
- FileHandlerはVIEW_3Dでのみpollを通し、既存`import_scene.unitypackage`へhandoffするadapterとして実装。独自import pipelineは追加していない。
- Synthetic valid Package handoff、register/unregister cycle、既存CPD/SPD/MPI/MPV/integration regression: PASS。
- `REAL-DND-001: HUMAN RETEST REQUIRED` — Windows Explorerから実際にBlender 3D Viewへdropする目視確認のみ未実施。

## Automatic Sibling Discovery (2026-09-16)

Top-level File > Import and native 3D View drag-and-drop now run same-directory sibling discovery automatically after primary index preparation. The public sibling checkbox was removed. Foreground `COMPLETE` discovery offers Import Together / Import Selected Only / Cancel; background uses deterministic Import Together. Synthetic Geometry → Material → Texture grouped import covers `COMPLETE`, transitive discovery, CPD resolution, and texture graph binding; `NONE`, `PARTIAL`, and `AMBIGUOUS` safety are covered by unit fixtures. Real combined verification remains `REAL-GROUP-001: HUMAN RETEST REQUIRED`.

The discovery implementation caches archive records per package for the duration of one pass, so a root or candidate archive is scanned once before GUID matching and transitive planning. Foreground `PARTIAL` discovery offers the same explicit choice but defaults to Primary Only; background does not auto-group partial results. The cache regression is covered by `test_discovery_reuses_each_archive_scan`.

## 2026-09-16 Visual Discovery Hardening

- Python suite: 93 tests PASS.
- Blender 5.2.1: regression fix, CPD/SPD, adjacent-neighbor E2E, manual provider E2E, MPI, MPV, DND, editable texture workflow, and external editor tests PASS.
- Metadata-first accounting: discovery reports zero texture and FBX payload bytes read; adjacent synthetic grouped import resolves Base Color and Normal while preserving unsupported roles without binding them.
- Distribution install test requires the generated ZIP path and is run after the exact remote revision ZIP is built.

Manual provider synthetic E2E: `MANUAL_PROVIDER_E2E_OK`. A provider outside the bounded automatic neighborhood is validated by exact GUID, imported separately, late-binds the existing unresolved material dependency, and records `USER_SELECTED_PACKAGE` provenance.

Real failed-scene forensic evidence: provider slot binding was masked as `RESOLVED_CROSS_PACKAGE` despite missing consumer binding; the missing visual GUID was a primary-local FBX. Resolver and primary-local subtraction regressions are covered by RF-002/RF-003.

## 2026-09-16 Prefab Selection Handoff

- Python suite: 96 tests PASS.
- Blender 5.2.1 synthetic foreground handoff: `PREFAB_SELECTION_FOREGROUND_E2E_OK`.
- The dialog retains its dynamic Prefab EnumProperty, while the prepared parent stores the selected token in stable string state; AUTO, first, middle, last, invalid fallback, and programmatic explicit selection are covered.

## 2026-09-16 Grouped Import Lifecycle

- Python 3.13.13: 100 tests PASS; compileall PASS.
- Focused foreground synthetic E2E: `GROUP_IMPORT_E2E_OK`; children finish synchronously, preserve primary Meshes, create no async/session workflow or recursive discovery, and precede final primary resolution.
- Wrapped transform/reference and multiple Renderer material-slot fixtures cover selected dependency extraction and visual closure.
- Real local foreground verification: primary Meshes persist after grouped completion; all expected Renderer slots and canonical Base Color/Normal bindings match their exact GUIDs. Commercial assets and diagnostic reports remain outside the repository.

## 2026-09-17 Prepared Handoff / Native Model Hierarchy

- Python 3.13.13: 103 tests PASS; compileall PASS.
- UIH-001..003: ten fresh foreground processes, actual props dialogs and
  native RET input after draw, middle Prefab -> sibling dialog -> import:
  10/10 PASS. One pump, no duplicate dialog, zero stale sessions.
- Controlled baseline rejected invoke stalls; corrected rejected-once recovery
  PASS. Exact original intermittent human failure trigger remains unconfirmed.
- TR-001..005 and necessary attachment bone-parent fixture PASS.
- Existing twelve Blender regression scripts run once, all PASS.
- Real local foreground first-attempt acceptance PASS: 15 Meshes, 18 Objects,
  two Empty objects, native-equivalent upright world matrices and drawn-face
  bounds. Single-package control retains 102 Meshes and identical image maps.
- Staged candidate ZIP extracted register/unregister PASS. Final exact-remote
  ZIP register/unregister is verified again after push.
- Mapped model-instance transform overrides remain unsupported without
  reliable source/default comparison. Private evidence is not committed.

### Bone Merge equivalent Deform preservation (2026-10-09)

At source baseline `266d45412c3cfaedac4e65eb1a3332881a31c5e4`, a public
synthetic equivalent Bone with identical World Rest/current Pose but A
`use_deform=false`, B `use_deform=true` passed preflight and Apply at rest.
Applying the same 0.5 pose translation to A/B then produced 0.5 world Mesh
error versus the retained B control. Current evaluated geometry alone therefore
missed incompatible deformation semantics.

The existing read-only preflight now refuses mismatched equivalent `use_deform`
before any write. `tests/blender_bone_merge_test.py` has focused runtime RED/GREEN:
both mismatch directions refuse without changing Bones, modifier, remap/local
IDs or evaluated geometry; matching true/true and false/false controls retain
future-pose geometry and B. The complete existing Blender 5.2.1 LTS runtime
suite PASS covers posed world geometry, B-only chains, Bone parenting,
collision/ambiguity/shared/animation/constraint/VRC refusals, no automatic
Weight Transfer, target-only group preservation, rollback and Undo. The four
nearest `test_bone_merge` policy tests PASS. Both owned Blender processes exit
zero after GREEN; no Unity run, original packages, private assets or SDK work.
This closes this concrete §11 defect, not broad Bone Merge/VRC or product release.
