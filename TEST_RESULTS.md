# Current 0.3.0 Baseline Test Results

## 0.4.0 candidate Multi-Package Identity (2026-09-15)

- Python: 54/54 PASS; `compileall`: PASS.
- Blender 5.2.1 LTS synthetic registry test: `MULTI_PACKAGE_IDENTITY_OK`.
- MPI-001..012: PASS through package fingerprint, canonical key, propagation, reverse lookup, duplicate/legacy handling, collision reporting, and JSON persistence.
- Real Package: `FINISHED`; 113 objects / 103 meshes / 4 armatures / 40 shape keys / 112 materials / 112 images.
- Existing Material/Texture regression: 147 bindings, identity errors 0.
- Package SHA-256 measurement: 385,655,203 bytes, 490.961 ms on the verification machine; `source_package_id=sha256:PRIVATE_ASSET_ID_REMOVED`.
- Automatic collision resolution, multi-package merge, UnityPackage export, and foreground visual Material Preview remain out of scope for this phase.

測定日: 2026-09-15  
Version: 0.3.0
対象: Blender 5.2.1 LTS / `RepresentativeAvatar-CaseA-Ver1.3.1.unitypackage`

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
- SampleGarment / Clothes
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
- ETX-010 real-package identity/reload automation: PASS; Face/Hair/SampleGarment representatives present. Material Preview UI visual inspection: UNVERIFIED because Computer Use was unavailable.
- Python: 41/41 PASS. `compileall`: PASS. Synthetic Blender integration: PASS. Real package: 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 bindings / identity errors 0.
- Version metadata is `(0, 3, 0)` and this commit is the formal 0.3.0 baseline.

## External Texture Editor Baseline Verification

- EXT-001: PASS; EXT-002/003: Addon Preferences and executable validation PASS, Browse/restart persistence UI/runtime surface UNVERIFIED; EXT-004: implemented, foreground menu UI UNVERIFIED; EXT-005..009: helper/integration PASS including argument safety, missing-editor, dirty, packed, and identity protection.
- EXT-010: UNVERIFIED for foreground UI/editor pixels because Computer Use was unavailable; direct launch helper is automated PASS.
- Existing ETX-001..009: PASS maintained. Real package regression: 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 bindings / identity errors 0. BUG-002 and BUG-003 remain PASS.

## 0.3.0 Final Hardening (2026-09-15)

- Human follow-up verification in Blender 5.2.1 Japanese UI with Krita: ETX-010 PASS, EXT-003 PASS, EXT-005 PASS, EXT-010 PASS. `SampleGarment_col.png` opened in Krita, saved to the same working file, reloaded from disk, and the Image Editor / Material Preview / 3D avatar reflected the edit; Krita remained selected after restart.
- Launch hardening: `launch_editor()` catches only `OSError` from `Popen()` and returns `EDITOR_LAUNCH_FAILED`; the operator reports it as `ERROR` and returns `CANCELLED`. Argument-list launch with `shell=False` is unchanged.
- EXT-001..010: PASS. EXT-011: PASS (`OSError("launch failed")` is converted to `EDITOR_LAUNCH_FAILED` without leaking to the test process; operator report is `ERROR`).
- Python: 45/45 PASS. `compileall`: PASS. Blender 5.2.1 register/unregister and External Texture Editor integration: PASS. Synthetic import/roundtrip: `BLENDER_INTEGRATION_OK`.
- Real package: `FINISHED`, 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 material bindings / identity errors 0. BUG-002 and BUG-003: PASS.
- Version remains `(0, 3, 0)`. This baseline is tagged `v0.3.0`; no GitHub Release is created in this phase.
