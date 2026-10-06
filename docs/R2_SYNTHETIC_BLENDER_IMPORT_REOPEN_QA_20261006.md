# R2 Synthetic Blender Import and Reopen QA

Date: 2026-10-06

Project: VAPB
Repository: https://github.com/UkkyaGuiyo/vapb
Branch: `feature/r2-material-slot-reorder`
Source snapshot: `9dc810387880194a4ade36516e3125ba1a24162c`
Test: `tests/blender_nested_prefab_realization_test.py` (Git blob `406c344b1a458fd9665951a5cdfacef14d5c536f`)
Blender: `5.2.1 LTS`

## Fixture and byte identity

A disposable synthetic `.unitypackage` was assembled from the exact tracked Git blob bytes of the public `tests/unity_alias_oracle/Assets/Oracle` fixture. It contains 16 payload assets and 16 unique GUIDs; no purchased material, user project, private Avatar asset, or external package was used.

The fixture mapping's FBX SHA-256 (`7123dad66d3a4c0ec138a33363f9e6a315ad76a020a9206b949d2b1db3a9501a`) and Model `.meta` SHA-256 (`f03a7d4f5019fcd723148784aeb466fa923715b6a2c2b9d39d617d1020c39e2b`) match the exact source Git blobs. The mapping was added in `af56ddfddc55a9d28a1e77f7245ecc8da44d2a01`; the tracked Model `.meta` blob is unchanged from `ea0dca4ef883f0e3658e35a50b2be38dd6df17c4` through the tested snapshot.

A Windows checkout converted the `.meta` line endings from LF to CRLF, changing its SHA-256 to `0d83b1703674e59f983d88fda05d066d2fe3ef62ae00df598aa40a50a0d6ae5b`. Two preflight attempts stopped at byte-identity assertions before package import. The fixture and package were then materialized from commit-addressed Git blobs; no expected hash or test assertion was changed.

## Import and persistence result

A fresh background Blender process imported the package through the real UnityPackage operator, reconstructed the synthetic `Null_TwoInstances` Prefab, checked the two renderer occurrences and their material/clear-slot semantics, resolved dependencies, and saved a `.blend` file. The process reported `NESTED_PACKAGE_CREATE_PASS`; the importer reported `local=1`, `cross-package=0`, `unresolved=0`, and `ambiguous=0`. Both occurrences shared the expected Mesh with distinct realization identities. The maximum recorded matrix error was `7.549789682315122e-10`.

A separate Blender process loaded that saved file, checked the scene, called `resolve_scene_dependencies` twice, and checked the scene again. It reported `NESTED_PACKAGE_REOPEN_PASS`. Both successful processes exited with code 0. Blender emitted a nonfatal extension-cache warning; no Blender preferences, dependencies, or security settings were changed.

Unity was not started. This result covers this public synthetic fixture and Blender 5.2.1 only; it is not Avatar, VRChat SDK, general package, or Unity Finalizer verification.

## Sanitized artifact digests

- Synthetic package SHA-256: `f3c43a788cab3feafe091e30a11751acf31502ae41d83d3dea626d433f245ad3`
- Saved `.blend` SHA-256: `a47fb3bb792075095827cad860d6f01a972658bdfd880b82cc77f308b1109eb5`
- Create log SHA-256: `10cc7f8fc94073394261c7fbfe6e79f6fb02b4388657223ea70e6a4af14edb9b`
- Reopen log SHA-256: `1ec337f223c7b67effea1343548db488ce18cd79307254f16c8c9d0bff2703f0`

The run manifest and raw logs are retained in the local disposable evidence directory and are not included in this repository.
