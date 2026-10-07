# Confirmed renderer-binding route: winding check

## Scope and result

This public synthetic-fixture evidence covers only the user-confirmed renderer-binding route after save and fresh-process reopen. It does not establish strict no-edit binding: **T0-A remains FAIL**. The downstream roundtrip gate **T0-B remains BLOCKED**.

The winding check compares material-grouped, world-space triangulated mesh coordinates with cyclic rotations treated as equivalent and reversed orientation distinguished. The recorded result is for a Windows-path-redacted copy of the generated FBX, not the original exporter bytes. The copy changed only four length-prefixed binary FBX string payloads, retained file and payload lengths, and imported in Blender 5.2.1.

Recorded comparison: Material GUID groups contain 2, 4, and 6 triangles respectively; oriented multiset differences are zero and reverse-only matches are zero. The checker also validates source package identity, scene SHA, raw Prefab material references (GUID/fileID/order), `OBJECT` links, and occurrence package provenance.

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
