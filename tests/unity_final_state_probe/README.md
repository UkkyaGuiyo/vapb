# Public synthetic final-state roundtrip

Requires Blender 5.2.1 and Unity 2022.3.22f1. All inputs here are synthetic.
Use separate throwaway Unity projects outside the repository, with a normal
Unity 2022.3.22f1 `ProjectSettings/ProjectVersion.txt` and `Packages/manifest.json`.

1. In a new **source** project, copy `Assets/VapbFinalState/Input.fbx` and its
   `.meta` from this directory, and copy `Editor/VapbFinalStateSourceProbe.cs`
   into `Assets/Editor`. Run Unity batch method
   `VapbFinalStateSourceProbe.Prepare`. It writes `Source.unitypackage` to the
   project root and prints `VAPB_FINAL_STATE_SOURCE_PASS` before exit 0.
2. For Case A, run Blender with `--background --factory-startup --disable-autoexec
   --python-exit-code 1 --python tests/blender_final_state_export_test.py --
   unchanged <Source.unitypackage> <Unchanged.blend> <Output.unitypackage>`.
   This keeps the selected imported Mesh geometry unchanged. Use a separate
   fresh Unity project and step 3 to validate its return package.
3. For Case B, run Blender with `--background --factory-startup --disable-autoexec
   --python-exit-code 1 --python tests/blender_final_state_export_test.py --
   create <Source.unitypackage> <Replacement.blend> <Output.unitypackage>`.
   The script performs normal Import, deletes the source Mesh, creates a UV
   Cube, assigns its imported Material, exports and saves. A second Blender
   invocation can open `<Replacement.blend>` and run phase `reopen` with a
   distinct output path; it checks unchanged source data and valid output-only Export IDs. Existing
   author-assigned IDs are reused; new labels are stored in the FBX/Recipe without
   writing into the editing scene.
4. In a new **fresh** Unity project, copy `Editor/VapbFinalStateFreshProbe.cs`
   to `Assets/Editor` and the two first-party `unity_editor` support sources
   into the same `Assets/VAPBExport/...` paths used by the output package.
   Put `Output.unitypackage` in the project root. Run Unity batch method
   `VapbFinalStateFreshProbe.Run`. It imports the package, applies the Recipe,
   checks actual Mesh, UV, Material GUID, Texture and missing source Model,
   then prints `VAPB_FINAL_STATE_FRESH_PASS` before exit 0.
5. For fail-closed controls, open `<Replacement.blend>` and run
   `tests/blender_final_state_mutation_test.py` with `-- <missing|duplicate|renamed>
   <Output.unitypackage> <Mutant_mode.fbx>`. Place the three generated FBX
   variants beside the fresh Unity project's `Output.unitypackage`. Run batch
   method `VapbFinalStateFreshProbe.RunMutations`. It restores all mutated
   project files and prints `VAPB_FINAL_STATE_MUTATIONS_PASS` before exit 0.

Use `-logFile` outside the repository for Unity runs. Keep generated packages,
Unity projects, `.blend` files and logs outside the public repository.

## Deferred Shader / self-contained output

Run `tests/blender_deferred_shader_test.py` in Blender with `--python-exit-code 1`
and `-- <unused-external-scratch>`. It creates Material/Texture input Packages,
normal-imports them, exports a new Cube, tests save/reopen, and makes only the
generated source inputs/archive unavailable. `--addon-zip <exact-built-zip>`
uses Blender's standard install/enable/disable operations in isolated settings.

Copy only `Editor/VapbDeferredShaderProbe.cs` into a new Unity project's
`Assets/Editor`. Put generated `Output.unitypackage`, `Expected.json` and
`ExternalShader.unitypackage` at its root. Run batch executeMethod
`VapbDeferredShaderProbe.Run`. Product helpers arrive through Output only.
Expect `VAPB_DEFERRED_PARTIAL_PASS` then `VAPB_DEFERRED_COMPLETE_PASS`, exit 0.
This checks missing provider, same-name wrong GUID, later exact provider,
Mesh/UV and Material/Texture identities, unchanged original bytes and Prefab,
and repeat finalization. No input Package A/B is imported into Unity.
