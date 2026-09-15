# Changelog

## 0.4.0 candidate - 2026-09-15

- Added content-addressed `source_package_id` and canonical package-scoped asset identity.
- Propagated package identity to imported Object, Material, and Image datablocks.
- Added Scene package registry, GUID/path reverse lookup, duplicate import status, and cross-package collision reporting.
- Added MPI-001..012 unit/synthetic acceptance coverage while preserving single-package behavior.


## 0.3.0 - 2026-09-15

- Added the manual Editable Texture Workflow for imported Unity Images.
- Added identity/status display and safe same-file Save/Reload actions in the Image Editor sidebar.
- Preserved the 0.2.0 import/material identity chain; missing, dirty, packed, and non-Unity sources are guarded.
- Added persistent External Texture Editor selection, safe manual executable browse, and non-blocking argument-list launch.
- Hardened External Texture Editor launch failure handling: OS `Popen()` failures return `EDITOR_LAUNCH_FAILED` and are reported as an operator error.

## 0.2.0 - 2026-09-15

- Blender 5.2.1 LTS baselineを確定
- UnityPackage selective extraction performanceをBaseline化
- async import lifecycle stabilizationとpost-import native crash fixを反映
- Material GUID / Texture GUID binding fix
- FBX `.meta` externalObjects support
- ambiguous same-name Material rejection
- explicit UV material graph
- locale-independent Node type lookup
- active Material Output selection
- Japanese UI Material Preview graph support
- save/reopen Material binding persistence
- Human Material Preview verification PASSを記録
