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

The separate Variant inspection exited `1` on the ordered Material GUID/local-ID assertion at slot 0. The manifest binding order is `[eb805efb35118044db5e74adc652673a, 0318f358e4c29034aa90cc8c50b58a93, 64f92a1bd9b35a040bf9e2c6d200b34c]`. Raw Variant YAML overrides slot 0 to `64f92a1bd9b35a040bf9e2c6d200b34c` and slot 2 to `eb805efb35118044db5e74adc652673a`; slot 1 is inherited from the source Prefab as `0318f358e4c29034aa90cc8c50b58a93`. This GUID order differs from the manifest order. The probe left its actual GUID fields empty because it threw before saving the failed slot observation. Face semantics were unresolved at that point.

A diagnostic-only entry was added to capture Variant and source slot identities, material labels from the native carrier using the same generated Mesh GUID/local ID, mesh vertices and submesh triangles, and Material overrides, without changing the acceptance assertion. The attempt-11 failure output remains preserved.

## Correct workflow

The public roundtrip probe calls `VapbModelSkinFinalizer.Apply(ManifestPath)` before loading and inspecting the Variant. The standalone `VapbT0CApplyFinalizerProbe` follows that explicit stage and records the pinned package hash, source FBX/meta hashes before and after Apply, edited FBX/meta hashes, whether the Variant destination was empty, the Apply return value, and Variant creation. It refuses an occupied Variant destination and writes its result with `CreateNew`.

The diagnostic-only entry was run against the existing attempt-11 Variant. Attempt 10 and all prior attempt-11 import/Apply/inspection logs remain unchanged. The trace below locates an earlier ordinal-to-material association boundary; it does not justify changing Unity Finalizer carrier order.

## Diagnostic preparation and resource hold

The diagnostic was extended from source commit `42dfd5abed72a32fdb2df40a8a6ff6128cb3132b` to capture source and Variant mesh vertices, per-submesh triangle indices, and each renderer's mesh-to-Prefab-root matrix. It captures the source Prefab renderer's mesh/material identities and Material property overrides scoped to the corresponding source renderer, with separate identities for the modification target and Material reference. The fixed fixture requires exactly one identifiable source renderer; missing or ambiguous source evidence fails the diagnostic. These are rest mesh observations; they do not prove skin deformation, evaluated pose, or general Avatar fidelity.

GPT-6 LUNA at low reasoning prepared the additions. GPT-6.1 SOL at medium reasoning reviewed the additions and execution plan, then verified the source uniqueness and override-scope corrections. The reviewed and staged diagnostic source SHA-256 is `f93d0e4b3f7b3cc3c07eb22416585918e8924140e04d5325684a0b7ad410b47c`. The existing target probe was preserved separately before staging; its SHA-256 is `7fb47aa508a455e2ce0f853b1fd961e4ca7bc48a86076f5d12da21273e6c2ae2`.

GitHub API readback of commit `415112b828b8519a1230e9956ea82c8a0f3289e2` returned probe SHA-256 `bbe904e9a522984062c63ac632b2207722b17039321eba8060e16f4a0375b785`. The staged file has 326 CR bytes and 24386 bytes total; Git stores the source with LF endings, zero CR bytes and 24060 bytes total. The decoded remote source equals the reviewed source exactly after CRLF-to-LF normalization. Use the staged byte hash for this Target's launcher pin and the remote byte hash for GitHub artifact verification.

No diagnostic Unity process was launched. A fresh resource check at `2026-10-07T12:28:19Z` observed `1455 MB` free RAM and `2336 MB` free virtual memory, with zero Editors on this target. The run-specific gate was `1500 MB` RAM and `2000 MB` virtual memory, based on a `500 MB` process budget plus `1000 MB` RAM reserve. Earlier five-second samples of owned processes had observed up to `419 MB` private memory; this is not a guaranteed peak or a general Unity minimum. The launcher stopped before `Start-Process`; other Editors remained untouched.

The initial prelaunch resource check held the diagnostic at 1455 MB free RAM. After resources recovered, the diagnostic was run once as recorded below. The original acceptance entry point is unchanged and its slot-0 FAIL remains the acceptance result. Its JSON SHA-256 is `6e5643901511d8705653b0f469976d0536bcbb3ba05a42fddf02bbf06f3da9d7`; the successful Apply JSON SHA-256 is `b31e501c78408b36480ef902cc20818aed574f2fc0d47a5860e2a80e44566de7`.

## Attempt 11 material diagnostic result

The reviewed diagnostic ran once in Unity `2022.3.22f1` and exited `0` at `2026-10-07T13:09:08Z`. It recorded `DIAGNOSTIC_ONLY`; this does not change the acceptance result. The log contained zero C# compiler errors. Diagnostic result JSON SHA-256: `af56ccfa654dcf8c09dcd91c5eb62dc58f773682a9dc339a7372056068a690d2`. Unity log SHA-256: `15b141f98d5f914b0a89153559cb4ae5977ad8d385face7a95d02226a093a829`.

The source renderer order is Material2, Material1, Material0, with triangle counts `[6,4,2]`. The Variant Renderer references Material0, Material1, Material2, also with counts `[6,4,2]`. Source and Variant each had 24 vertices and identical mesh-to-Prefab-root matrices. The Variant overrides slot 0 to Material0 and slot 2 to Material2; slot 1 inherits Material1.

An initial comparison grouped Unity source Prefab and Variant triangles by persistent Material GUID. It found Material1 matching (4/4 triangles), Material0 at source 2 versus Variant 6, and Material2 at source 6 versus Variant 2. That comparison was misinterpreted as a Finalizer defect because it did not compare the Blender-visible source assignment that the export route promises to preserve. Corrected trace evidence follows.

The original `Input.fbx` material connections are ordered Material0, Material1, Material2, with polygon groups at FBX material indices 2, 1, 0 having counts `[6,4,2]`. The Unity source Renderer identity order is Material2, Material1, Material0. Existing pre-save confirmation evidence already shows the Blender mesh identity order Material2, Material1, Material0 with counts `[2,4,6]`; the reopened Blender scene retains that same blend hash and assignment. The exported FBX has the same polygon indices/corners and material-connection labels Material2, Material1, Material0 with counts `[2,4,6]`. Unity imports those native carrier labels in order Material0, Material1, Material2 with counts `[6,4,2]`, and the Finalizer resolves each label to the matching persistent Material identity. Thus the generated FBX and finalizer preserve the Blender material face assignment. The observed semantic change occurs before export, when serialized Unity Renderer slot indices are applied by ordinal to Blender material slots whose FBX connection order can differ.

Source review confirms this missing join: the witness bridge writes a serialized Renderer `slot` directly as `consumer_slot_index`; the dependency resolver uses that integer as a Blender material slot; the confirmation operator likewise applies `plan[index]` to Blender slot `index` without correlating the actual face partitions. A regression must compare each source Unity submesh's oriented triangle-corner multiset with Blender's imported FBX groups and attach the exact `(GUID, fileID)` identity by that geometry correspondence. This review traces the likely inbound boundary; run the failing test before changing production code. Equal counts, names, or slot positions alone are not correspondence. Ambiguous duplicate or unused partitions must fail closed unless their entity/face mapping is explicitly supported.

The diagnostic process used PID `9140`, exited normally, observed zero same-Target Editors afterward, and preserved all prior Assets, manifest, Apply output, and acceptance output. The existing Apply remains PASS and the original ordered-slot acceptance remains FAIL. No material was reassigned by the diagnostic. A non-fatal Licensing Client signature-validation warning appeared; Unity connected to its client and the diagnostic completed without changing licensing configuration.

## Resource and process check

Before attempt 10, free memory was about `1950 MB` and free virtual memory about `2818 MB`. Five-second samples observed up to `410 MB` private memory for import and `355 MB` for inspection. These samples are not whole-tree or child-process peak measurements and do not establish a general minimum. The two other Unity Editors and the Unity MCP server were left running; the same-target process check was clear before each serial call.

