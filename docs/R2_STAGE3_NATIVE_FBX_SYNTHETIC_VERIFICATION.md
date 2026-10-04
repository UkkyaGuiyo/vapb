# Stage 3 Synthetic Native-FBX Verification

This procedure uses authored synthetic geometry and the repository's public FBX exporter. It does not use purchased material assets, user project copies, private campaign data, or external project dependencies.

## Disposable test root

Create a new directory outside the repository, with separate empty Unity 2022.3.22f1 SourceProject and TargetProject directories. The runner accepts that root through VAPB_STAGE3_TEST_ROOT and refuses to proceed unless the root is explicitly marked:

- Root marker file: .vapb-stage3-owned-test-root with exact value VAPB_STAGE3_OWNED_TEST_ROOT_V1.
- Source marker file: SourceProject/.vapb-stage3-owned-source-project with exact value VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1.
- Target marker file: TargetProject/.vapb-disposable-unity-test-project.
- SourceProject and TargetProject must be direct children of the marked root. The root cannot be inside a Git checkout. Existing symlink/junction/reparse-point components on owned paths are rejected, including fixture and TargetProject Assets paths.

Set VAPB_STAGE3_TEST_ROOT to the canonical path of this root in the Blender and Unity processes. Do not point it at a repository, existing user project, or an unmarked folder. The root resolver has Python unit tests for missing/wrong markers, a Git checkout, missing child markers, and symlink escape (the symlink case skips when Windows does not grant symlink privileges).

## Generate and run

1. Use an installed Blender 5.2.1 executable; no dependency install is needed. In PowerShell:

   ~~~powershell
   $repo = (git rev-parse --show-toplevel)
   $env:VAPB_STAGE3_TEST_ROOT = (Resolve-Path $stage3Root).Path
   & $blender --background --python "$repo/tests/unity_final_state_v2/build_stage3_fbx_fixtures.py" -- --test-root $env:VAPB_STAGE3_TEST_ROOT
   ~~~

   The builder validates the marked root and refuses to overwrite any existing fixture input, output directory, evidence file, or build log. It writes only under SourceProject and the owned run root. The Unity test reads each expected FBX SHA-256 from that same run's evidence JSON and checks its case, Export ID, filename, and path; FBX bytes are not compared to hashes from a previous run because the exporter serializes creation time and source path. If output already exists, keep it and continue testing, or select a new explicitly disposable root when a full rebuild is required.

2. Prepare TargetProject with the Finalizer and export marker from unity_editor, the existing V2 Editor tests and asmdef, and Stage3NativeFbxApplyReviewTests.cs plus its checked-in .meta. Test Framework 1.1.33 and its NUnit assembly must already be available from the existing package cache. Do not download/install dependencies for this verification; if Test Framework is unavailable, stop at compilation and report that blocker.

3. With no other Unity Editor using the project, run Unity 2022.3.22f1 serially:

   ~~~powershell
   $env:VAPB_STAGE3_TEST_ROOT = (Resolve-Path $stage3Root).Path
   & $unityEditor -batchmode -nographics -projectPath "$env:VAPB_STAGE3_TEST_ROOT/TargetProject" -runTests -testPlatform EditMode -testFilter Stage3NativeFbxApplyReviewTests -testResults "$env:VAPB_STAGE3_TEST_ROOT/TargetProject/Logs/Stage3NativeFbx.xml" -logFile "$env:VAPB_STAGE3_TEST_ROOT/TargetProject/Logs/Stage3NativeFbx.log"
   ~~~

   Allow Test Runner to exit normally; omit -quit so the results XML is written. Use the same TargetProject for reruns. The test verifies its resolved Application.dataPath is exactly the marked TargetProject. It snapshots Assets and protected files, creates test-owned content only under its fixed owned paths, restores/cleans those paths, and fails if pre-existing Assets content changes.

## What the tests check

- ABC: native submesh material labels and world-space face centroids independently map all three triangles to A/B/C. A deliberate A/B identity swap is a negative control and must fail FaceMap. Apply must succeed twice, preserving FBX data/importer metadata and all protected file hashes; the generated prefab must retain the native mesh identity and correct material assignment.
- ABA: Unity collapses the source A/B/A slots to two native submeshes. The Finalizer must reject with NATIVE_MATERIAL_CARDINALITY_MISMATCH before rewriting protected files.
- JSON characterization: canonical string slot indices, a raw numeric token, and duplicate raw slot_index keys are logged separately. These are Unity JsonUtility observations; passing characterization tests do not establish that raw numbers or duplicate keys are rejected.

For this exact synthetic fixture in Unity 2022.3.22f1, the measured importer settings were globalScale 1, useFileScale true, fileScale 0.01, useFileUnits true, and root scale 100. Imported local mesh vertices plus the root transform yielded (x,y,0) -> (-x,0,-y); source and world centroids are derived independently of material labels. Do not generalize this basis to other Unity versions or importer settings.

## Recorded result

A baseline run of the native-FBX candidate before root parameterization reported 5/5 passed, 0 failed, 0 skipped. It verified the FaceMap and Apply assertions before the three evidence-validation tests were added. Its JSON characterization observed raw numeric 0 and the duplicate-key case deserialize as "0" and pass the current guard. Those observations are not rejection guarantees or implementation changes.

The parameterized candidate was run serially in the existing disposable TargetProject with Unity 2022.3.22f1. `R2Stage3NativeFbxFinal_20261004_06.xml` reports Passed, 8 total, 8 passed, 0 failed, 0 skipped (2026-10-04 08:56:37-08:56:40 UTC); the launcher captured Unity Editor process exit code 0. The suite includes the three fixture-evidence rejection cases (duplicate case, malformed hash, and null case/FBX). ABC first and repeat Apply passed with protected-file hashes unchanged and the deliberate A/B swap detected; ABA was rejected with `NATIVE_MATERIAL_CARDINALITY_MISMATCH`. Raw numeric and duplicate-key JSON tokens deserialize as "0" and pass the current guard in this Unity version, so those passing characterization cases are observations, not rejection guarantees. Test-owned output and export manifest were absent after the run; the pre-existing FBX fixtures were not regenerated. A prior 5/5 baseline predates path parameterization and these added tests.
