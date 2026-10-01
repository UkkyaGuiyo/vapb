# Public model Material regression

This fixture and probe use first-party geometry, three Standard Materials and public Unity Editor APIs. No SDK or third-party scripts are needed. The fixture contains a direct prefab with one skin and three distinct triangle groups. It exercises `RESTORE_DIRECT_SKIN_VARIANT_V1` through the normal VAPB import/export operators.

## Requirements

- Blender 5.2.1 with this repository importable as `unitypackage_blender_importer`.
- Unity 2022.3.22f1 and a fresh project with the normal built-in modules (including animation).
- Paths below are placeholders: set them to absolute local paths. Use a new work directory and new output file. Preserve the `Sources` directory beside the generated `.blend`.

```powershell
$repo = '<addon repository directory>'
$addonParent = Split-Path $repo
$probe = Join-Path $repo 'tests/unity_model_material_probe'
$work = '<empty external work directory>'
$blender = '<Blender executable>'
$unity = '<Unity 2022.3.22f1 executable>'
$project = '<fresh Unity project directory>'

& $blender --background --python "$probe/prepare_fixture.py" -- `
  --addon-parent $addonParent --source-package "$probe/fixtures/ThreeSlotSource.unitypackage" --work-dir $work
& $blender --background --python "$probe/export_fixture.py" -- `
  --addon-parent $addonParent --edited-blend "$work/Edited.blend" --output "$work/Output.unitypackage"

New-Item -ItemType Directory -Force "$project/Assets/PublicProbe/Editor" | Out-Null
Copy-Item "$probe/Editor/VapbModelMaterialProbe.cs" "$project/Assets/PublicProbe/Editor/"
& $unity -batchmode -nographics -projectPath $project `
  -executeMethod VapbModelMaterialProbe.Import `
  -vapbPublicPackage "$work/Output.unitypackage" `
  -vapbPublicExpectation "$work/Output.expectation.json" `
  -vapbPublicReport "$work/Report.json" -logFile "$work/Unity.log"
```

The first script imports the supplied source package, assigns canonical Materials using exact serialized GUID/fileID/package identities, changes one vertex and saves the edited fixture. This explicit fixture setup supplies the intended current Blender slots. The second script uses the ordinary production export operator and writes the expected Material identities and triangle counts.

## Acceptance

`Report.json` must have `result: MATERIAL_ASSOCIATION_PASS`; Unity exits 0. Inspect `Unity.log` separately for compiler errors. The probe checks:

- Initial and repeated Apply succeed.
- Each distinct triangle group maps to its expected Material GUID and signed local file ID. `actual_material_refs` records the exact resulting IDs.
- Native imported Material names carry exact declared `VAPB-MAT` transport labels.
- Wrong transport label, nonexistent GUID and wrong signed local ID are refused before a Variant exists. The exact manifest is restored after each control.
- All source `.mat` and `.mat.meta` bytes remain unchanged across controls and both Apply calls.

`material_array_preserved` and `material_array_matches_blender` are diagnostic fields; the correct native submesh permutation can make both false. The acceptance condition is the triangle-group association, not the unchanged slot array. This three-group fixture identifies face groups by distinct triangle counts; it does not assert a general geometry comparator.

## Fixture provenance

`fixtures/ThreeSlotSource.unitypackage` is a 9,812-byte first-party synthetic package: only `Assets/PublicMaterialSource`, `Input.fbx`, `Direct.prefab`, and three Standard `.mat` assets with their metas. It contains no Editor scripts, SDK files or third-party source. One FBX source-file metadata string was replaced with a relative first-party label of the same length; geometry and serialized asset identities were preserved.

Fixture SHA256: `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`.

The exact published fixture and scripts were run with Blender 5.2.1 and Unity 2022.3.22f1. Runtime results are reported by the probe rather than stored as a reusable PASS claim. Use a fresh project for every run because the negative controls require no pre-existing Variant.
