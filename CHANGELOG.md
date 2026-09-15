# Changelog

## 0.4.0 candidate - 2026-09-15

- Added content-addressed `source_package_id` and canonical package-scoped asset identity.
- Propagated package identity to imported Object, Material, and Image datablocks.
- Added Scene package registry, GUID/path reverse lookup, duplicate import status, and cross-package collision reporting.
- Added MPI-001..012 unit/synthetic acceptance coverage while preserving single-package behavior.
- Fixed canonical sub-asset identity so fileID is scoped by parent GUID or Asset Path; fileID-only records are explicit `AMBIGUOUS_IDENTITY`.
- Fixed Prefab `unity_asset_path` propagation to use the Unity-relative AssetDatabase path rather than the temporary extracted filesystem path.
- Added MPI-013..017 including same-fileID prefab separation and `.blend` save/reopen persistence.
- Fixed Prefab material binding when sequential FBX imports add Blender `.###` duplicate suffixes; ambiguous base-name fallback remains unresolved instead of guessing.
- Added MPV-001..012 synthetic Real Multi-Package Visual E2E diagnostics and save/reopen coverage; real two-package foreground retest remains human-required.
- Added UnityPackage Exporter and reachability-pruning specification only; exporter implementation is not included.


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
- Added package-scoped Cross-Package Dependency Resolver for Renderer Material, FBX externalObjects Material, and Material Texture references.
- Added Material-only and Texture-only package import with persistent unresolved records and late binding in either import order.
- Added synthetic CPD split-package and save/reopen coverage; real BOOTH split-package validation remains human-required.
