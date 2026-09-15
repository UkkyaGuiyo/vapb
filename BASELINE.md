# Baseline

正式Baseline: 2026-09-15時点の実装・配布ZIP 0.2.0

## Environment

- Target: Blender 5.2.1 LTS only
- Python: 3.13.13
- Add-on version: 0.2.0
- Reference Package: `RepresentativeAvatar-CASE_A.3.1.unitypackage`
- Baseline ZIP: `<LOCAL_PATH>
- Baseline SHA-256: see `experiment_logs/BASELINE_0_2_0_FREEZE_001/REPORT.md` for the final distribution hash.

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

## Known Limitations / Unverified

- Transparent / cutout / blend material visual path is not validated by the reference package.
- File Browser cancel/re-run manual test is not confirmed.
- Arbitrary Prefab manual selection UI is not confirmed.
- Normal UI Undo-key behavior is not confirmed.

## Not Yet Implemented

- Editable texture workflow.
- Multi-package integration validation.
- Bridge UnityPackage export.
- Unity Finalizer.
- Approximate PhysBone preview.
- Full progress-bar UX.

## Baseline Rule

今後の変更はこの基準値との差分を明示し、Blender 5.2.1 LTSで回帰テストする。`experiment_logs/`内の過去記録は歴史的証拠として変更しない。
