# Confirmed renderer-binding route: winding check

## Scope and result

This public synthetic-fixture evidence covers only the user-confirmed renderer-binding route after save and fresh-process reopen. It does not establish strict no-edit binding: **T0-A remains FAIL**. The downstream roundtrip gate **T0-B remains BLOCKED**.

The winding check compares material-grouped, world-space triangulated mesh coordinates with cyclic rotations treated as equivalent and reversed orientation distinguished. The recorded result is for a Windows-path-redacted copy of the generated FBX, not the original exporter bytes. The copy changed only four length-prefixed binary FBX string payloads, retained file and payload lengths, and imported in Blender 5.2.1.

Recorded comparison: Material GUID groups contain 2, 4, and 6 triangles respectively; oriented multiset differences are zero and reverse-only matches are zero. The checker also validates source package identity, scene SHA, raw Prefab material references (GUID/fileID/order), `OBJECT` links, and occurrence package provenance.

## Raw Prefab versus fresh-process saved-scene check

This additional check reopened the exact previously saved, explicitly user-confirmed scene in a fresh Blender process. It is a fixed-evidence reproduction, not a general scene inspector: the script asserts the source `.unitypackage` SHA-256 and saved `.blend` SHA-256, independently reads raw Prefab YAML, and compares Renderer/Mesh/Material references against the stored projection and reopened Blender slots.

- Blender 5.2.1; process exit 0; result `PASS`.
- The three raw Prefab GUID/fileID pairs matched the projection and reopened slots in order. All three slots were `OBJECT` linked and package-scoped; the existing user-confirmed binding and persistent Mesh receipt revalidated; triangle counts remained `[2, 4, 6]`.
- Saved scene SHA-256: `58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c`. Source package SHA-256: `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`; source FBX SHA-256: `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5`; source FBX meta SHA-256: `ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d`.
- The probe did not save the scene or modify a Unity Project. It checks persistence after explicit confirmation only; strict T0-A remains **FAIL**, T0-B remains **BLOCKED**, and no Unity-observed identity witness was produced.

To rerun, provide the exact saved scene and fixture package; the checker takes `--package`, `--output`, and `--repo-root` after `--`. `--repo-root` may be a normal VAPB clone root or an add-on source directory named `unitypackage_blender_importer`.

```powershell
$blender = '<Blender 5.2.1 executable>'
$repo = '<VAPB repository root>'
$scene = '<authorized-local-confirmed-scene.blend>'
$package = Join-Path $repo 'tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage'
$result = '<new-output-result.json>'
& $blender --background $scene --python-exit-code 1 --python tests/evidence/confirmed_route_winding_20261007/confirm-raw-prefab-reopen.py -- --package $package --output $result --repo-root $repo
```

The checker rejects outputs resolving to the package or currently opened `.blend`; it creates output files exclusively and refuses to replace an existing file. Use a new output filename for each run.

Included: `confirm-raw-prefab-reopen.py`, its standalone `confirmed_route_output_safety.py` path/write guard, sanitized `confirm-raw-prefab-reopen-evidence.json`, and `tests/test_confirmed_route_output_safety.py` for alias refusal, no-overwrite, and repository-root resolution. Raw logs and the `.blend` remain local.

## Exact Unity identity witness: prepared, Editor run pending

The manual confirmation route preserves slot identities after save/reopen, but it does not supply the missing automatic identity bridge. A separate isolated Unity source project was prepared from the same exact public package/FBX/meta revision using the existing `tests/unity_hierarchy_probe/prepare_exact_witness.py` workflow. Blender 5.2.1 generated semantic no-op and test-marker FBX copies (`models=4`, `original_unchanged=1`, exit 0). The Unity project targets 2022.3.22f1 and its manifest has no dependencies. See `unity-source-witness-preparation.json`.

Unity Editor has **not** been launched for this project; compile, mapping capture and witness promotion remain pending. The minimum needed observation is the existing `VapbBoneWitnessProbe.Run` output on this exact revision: Unity must associate the marked source-FBX Model UID to the generated GameObject, Renderer and Mesh and report its GUID/signed local ID; the probe must pass original/no-op/marked/restored equivalence and exact source/meta restoration. `promote_exact_witness.py` then validates the mapping against the source FBX Model/Geometry graph and package/FBX/meta SHA before it can produce a trusted witness. No name or single-candidate fallback is used.

When an isolated Editor slot is available, run in the prepared source project:

```powershell
$unity = '<Unity 2022.3.22f1 executable>'
$sourceProject = '<prepared external source project>'
& $unity -batchmode -nographics -projectPath $sourceProject -executeMethod VapbBoneWitnessProbe.Run -logFile (Join-Path $sourceProject 'unity.log')
```

Require process exit 0, `VAPB_BONE_WITNESS_PASS`, and the restoration/revision flags in `VapbBoneWitnessResult.json`; then run `tests/unity_hierarchy_probe/promote_exact_witness.py` against that project and verify the generated witness package, FBX and meta SHA values before retrying strict untouched import. The new source project and raw process logs remain local; the summary JSON is sanitized.

## Reproduction command

The private scene, source package, generated FBX, and raw logs are not included. Supply authorized local inputs: repository root, confirmed scene, path-redacted generated FBX, export result JSON, closure result JSON, original source package, and output JSON path. The standalone checker accepts seven arguments after `--`:

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$repo = (Get-Location).Path
$scene = '<authorized-local-confirmed-scene.blend>'
$fbx = '<authorized-local-path-redacted-generated.fbx>'
$export = '<authorized-local-export-result.json>'
$closure = '<authorized-local-closure-result.json>'
$package = '<authorized-local-source.unitypackage>'
$result = '<new-output-result.json>'
& $blender --background --factory-startup --python-exit-code 1 --python tests/evidence/confirmed_route_winding_20261007/winding_probe.py -- $repo $scene $fbx $export $closure $package $result
```

The result JSON is written only if every assertion passes. To create a same-length path-redacted FBX copy, run `redact_fbx_paths.py` with source FBX, a new output FBX, and a new report JSON as its three arguments after `--`. The redactor recognizes Windows drive-letter paths in the expected FBX string-property format and fails closed when validation does not match.

## Source identity

- Repository: `https://github.com/UkkyaGuiyo/vapb`
- Branch: `feature/r2-material-slot-reorder`
- Tested repository commit: `16014374757b22e909711055cbdfe6cd19f73970`
- Checker SHA-256: `fcb2f84104017ed72844fc288d52b61d8fb83d29a64bdd80c95b630fecebd628`
- Redactor SHA-256: `41a3033513d59a6ddd2e6ab09d6ab78ec3ddb49c3b21d86e45022685eeb65ab9`
- Winding-result JSON SHA-256: `9c279d6e307ac26c800dfe2b62be9329ee6f2d112180ce7708c984d29ebd681e`
- Product source blob IDs: `operators/export_unitypackage.py` `a0798e33bb94fb038de7bb4f64f8b570ac5316c1`; `export/model_skin.py` `677b29e20712e4f091d1d2b28d191747193167be`; `blender/renderer_binding.py` `d67399bae9182242ce0a8c79aa1b9e3fbbfed1af`; `blender/fbx_receipt.py` `0043352621dd0ad1fd674669ebbbc51958e39f1d`; `tests/blender_three_slot_fixture_oracle.py` `afc285c40f8fbf676c0261a90c3795a1e9131bec`.

## Included summaries

- `confirm-prepare-evidence.json` and `confirm-reopen-evidence.json`: explicit-confirmation route and fresh-process persistence evidence.
- `export-evidence.json` and `closure-evidence.json`: sanitized export and package/FBX closure summaries.
- `fbx-redaction-evidence.json`: redaction counts, byte-length preservation, and artifact hashes.
- `winding-result.json`: per-material oriented comparison and bounded status.

No `.blend`, Unity package, raw FBX, or raw process log is included.
