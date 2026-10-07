# T0-C fresh import Finalizer boundary

## Scope

This note records a fixed synthetic `T0-C` package check in Unity `2022.3.22f1`. The package SHA-256 was `20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd`; the generated FBX SHA-256 was `a27cc6100cd2cbce5f0e9b3a4b24867e042e861ac33ff233a4f37276de491c1e`.

## Attempt 10 result

The package import process exited `0`. A later inspection process exited `1` because `Assets/VAPBExport/manifest.json` named a Variant path that did not exist in the AssetDatabase. The probe had not called `VapbModelSkinFinalizer.Apply` before looking for that Variant. The manifest also contained `NEW_PREFAB_VARIANT` and `UNITY_MODEL_IDENTITY_CHECK_REQUIRED` warnings.

This is a failed end-to-end probe sequence, but it does not show a Finalizer defect: the intended Finalizer stage was omitted. The import stage did prove the pinned package and generated FBX hashes and compile reached the inspection method. It did not produce Renderer, Mesh, Material, or submesh observations.

Sanitized process evidence:

- import: PID `19024`, exit `0`; log SHA-256 `332bdf9fe48c4071d2c94decf203be0d1919e4c1e8df7e44270af5a86aad257`
- inspection: PID `44636`, exit `1`; log SHA-256 `45c9af3f28127607645d7cb4c234ea787e88a1663fba4f2a872caacdb07e3f5`
- result JSON SHA-256 `4ebfaa8751be0037d3be7844b27b290ceeb1c2f4aea1306cd00bf324d3f666b`
- both owned processes exited; no Editor remained on the disposable target

## Attempt 11 bootstrap failure

The first import call for the corrected workflow exited `1` during C# compilation. The apply probe directly referenced `VapbModelSkinFinalizer`, but that type is supplied by the package being imported and was unavailable in the initial compile. Unity did not import the package manifest or its assets in this attempt. The probe now resolves the exact public static `Apply(string)` method by reflection after import; the same owned Target will be retried with distinct logs, preserving this failure record.

The failed import log SHA-256 was `13196ba2c36f3ba08c6fcb4a2f9a67df481a32ff9492f0dca53573e378c022fc`. The C# diagnostic was `CS0103` for the unavailable `VapbModelSkinFinalizer` symbol.

The probe was changed to resolve the exact public static `Apply(string)` method after import through reflection, rejecting duplicate same-named types and an unexpected return type. The import retry exited `0`, recorded zero C# compile errors, and imported the pinned manifest and finalizer.

## Attempt 11 Finalizer and inspection

The explicit Apply process exited `0` and returned `PASS`. The Variant destination was vacant before Apply and the Variant was created. Source FBX bytes stayed at SHA-256 `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5`; its `.meta` stayed at `ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d`. Edited FBX bytes stayed unchanged. Its importer `.meta` changed during finalization and is recorded in the run evidence.

The separate Variant inspection exited `1` on the ordered Material GUID/local-ID assertion at slot 0. The manifest binding order is `[eb805efb35118044db5e74adc652673a, 0318f358e4c29034aa90cc8c50b58a93, 64f92a1bd9b35a040bf9e2c6d200b34c]`. Raw Variant YAML overrides slot 0 to `64f92a1bd9b35a040bf9e2c6d200b34c` and slot 2 to `eb805efb35118044db5e74adc652673a`; slot 1 is inherited from the source Prefab as `0318f358e4c29034aa90cc8c50b58a93`. This is a GUID permutation relative to manifest array order. The probe left its actual GUID fields empty because it threw before saving the failed slot observation. Submesh triangle counts and face-to-Material semantics were not captured, so this mismatch remains unresolved and is not a product PASS or a confirmed product defect.

A diagnostic-only entry was added to capture all Variant slot identities, expected manifest bindings, Material identities from the native carrier renderer that uses the same generated Mesh GUID/local ID, and submesh triangle counts without changing the ordered acceptance assertion. Static review found and fixed a missing project-path helper before running it. Its Unity execution is pending; the attempt-11 failure output remains preserved.

## Correct workflow

The public roundtrip probe calls `VapbModelSkinFinalizer.Apply(ManifestPath)` before loading and inspecting the Variant. The standalone `VapbT0CApplyFinalizerProbe` follows that explicit stage and records the pinned package hash, source FBX/meta hashes before and after Apply, edited FBX/meta hashes, whether the Variant destination was empty, the Apply return value, and Variant creation. It refuses an occupied Variant destination and writes its result with `CreateNew`.

The next validation runs the diagnostic-only entry against the existing attempt-11 Variant, then uses the captured native carrier order and triangle counts to decide whether a distinct semantic oracle is justified. Attempt 10 and all attempt-11 import/Apply/inspection logs remain unchanged. Do not change Material ordering until face/submesh semantics are observed.

## Resource and process check

Before attempt 10, free memory was about `1950 MB` and free virtual memory about `2818 MB`. Five-second samples observed up to `410 MB` private memory for import and `355 MB` for inspection. These samples are not whole-tree or child-process peak measurements and do not establish a general minimum. The two other Unity Editors and the Unity MCP server were left running; the same-target process check was clear before each serial call.
