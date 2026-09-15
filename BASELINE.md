# Baseline

正式Baseline: 2026-09-15時点の実装・配布ZIP 0.3.0

## Environment

- Target: Blender 5.2.1 LTS only
- Python: 3.13.13
- Add-on version: 0.3.0
- Reference Package: `RepresentativeAvatar-CASE_A.3.1.unitypackage`
- Baseline ZIP: see `experiment_logs/BASELINE_0_3_0_FREEZE_001/REPORT.md`
- Baseline SHA-256: see `experiment_logs/BASELINE_0_3_0_FREEZE_001/REPORT.md`

## Reference Scene

- Object: 113
- Mesh: 103
- Armature: 4
- Shape Key: 40
- Material: 112
- Image: 112

## Known Good

- Foreground import returns `FINISHED`.
- Async package preparation and selective sequential extraction.
- Prefab hierarchy reconstruction.
- Post-import modal crash fix.
- Material / Texture identity and Japanese locale Material graph fixes.
- Human Material Preview verification: Face/Skin, Hair, SampleGarment/Clothes, Gloves, accessories; no MAGENTA or white-only rendering reported by the user.
- 147 / 147 Material binding persistence and Japanese save/reopen graph match.
- Serial import and ZIP validation PASS.
- Editable Texture Workflow: external edit, same-file save, reload, and Material Preview update PASS.
- External Editor Launcher: persistent preference, direct launch, safe argument list, and launch-failure handling PASS.
- Real package regression: 113 objects / 103 meshes / 4 armatures / 40 shape keys / 147 material bindings / identity errors 0.

## Known Limitations / Unverified

- Transparent / cutout / blend material visual path is not validated by the reference package.
- File Browser cancel/re-run manual test is not confirmed.
- Arbitrary Prefab manual selection UI is not confirmed.
- Normal UI Undo-key behavior is not confirmed.
- Transparent / cutout / blend material visual path is not validated by the reference package.
- Multi-Package integration is not implemented.
- Bridge UnityPackage export is not complete.
- Unity Finalizer is not implemented.
- MRUS implementation is not implemented; REC-001..010 remain PLANNED / UNVERIFIED.
- Automatic filesystem watcher is not included.
- PhysBone preview is not implemented.

## Not Yet Implemented

- MRUS implementation and REC-001..010.

## Baseline Rule

今後の変更はこの基準値との差分を明示し、Blender 5.2.1 LTSで回帰テストする。`experiment_logs/`内の過去記録は歴史的証拠として変更しない。
