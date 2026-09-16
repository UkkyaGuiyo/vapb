# Changelog

## 0.4.0 candidate - 2026-09-16

- Centralized texture role classification for initial build and late binding; unknown properties are preserve-only.
- Reworked sibling discovery around metadata-first manifests, bounded neighbor expansion, visual completeness, and payload-read accounting.
- Added synthetic adjacent-package grouped import coverage for Base Color, Normal, and preserve-only texture roles.
- Added demand-driven selected-Prefab visual closure, missing-dependency foreground flow, exact-GUID manual package/folder validation, and resolution provenance.
- Fixed consumer-binding diagnostics so a provider lookup cannot overwrite `MISSING_CONSUMER`; primary-local visual GUIDs are excluded before sibling resolution.

## 0.4.0 candidate - 2026-09-15

- Top-level UnityPackage imports now automatically perform GUID-based sibling discovery for File > Import and native drag-and-drop; unique complete chains are grouped without a user checkbox.
- Foreground complete discovery now presents Import Together, Import Selected Only, and Cancel; background tests remain deterministic.
- Sibling discovery reuses each package's archive index within one discovery pass, avoiding duplicate root/candidate scans.
- Partial discovery now presents an explicit foreground choice with Primary Only as the safe default; it never auto-groups in background.

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
- Hardened distribution ZIP generation: tracked runtime Python is included by default, development-only trees are excluded explicitly, and extracted ZIP register/unregister is tested in Blender 5.2.1.
- Added Blender 5.2.1 native FileHandler routing for `.unitypackage` drops from the 3D View to the existing import operator.


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
