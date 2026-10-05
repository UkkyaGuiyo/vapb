# R2 Built-in Material Preview Checkpoint

Date: 2026-10-04  
Project: VAPB  
Repository: `https://github.com/UkkyaGuiyo/vapb`  
Branch: `feature/r2-material-slot-reorder`  
Base source SHA: `dedc9021bf310c6786364ce88a5a1a867509bafa`

## Scope

This bounded change handles only `PREFAB_RENDERER_MATERIAL` records whose exact serialized identity is the Unity built-in default Material GUID `0000000000000000f000000000000000` with integer file ID `10303`. The raw fileID scalar is preserved through projection and witness dependency capture; a normalized integer by itself does not qualify. Wrong fileID, wrong GUID, another dependency type, a fractional raw fileID, an ordinary absent provider, and explicit null stay outside this route.

The resolver creates one neutral gray Blender Material tagged as `UNITY_DEFAULT_MATERIAL` approximate preview. It carries dedicated preview metadata and no package ID, package Material GUID identity, or `.mat` path. Each exact dependency record retains its original GUID/fileID and occurrence identity; binding still uses the existing slot ownership receipt and object-level assignment. Re-resolution reuses the one preview Material and preserves changed user slots.

The import outcome is explicitly `PARTIAL` with `BUILTIN_PREVIEW_APPROXIMATE`. The preview is a display/editing aid, not evidence that Unity's original Material or shader appearance was reconstructed. This does not define how a built-in reference should be exported back to Unity.

The resolver is part of the ordinary `.unitypackage` import dependency stage. The two-occurrence public fixture uses the optional model identity witness to establish exact Renderer-to-native occurrence joins for the test; that witness remains test evidence, not a user prerequisite. This change does not guess a mesh or Renderer by name. A separate no-witness miniature package without an exact source mesh/Renderer association produced no Material dependency record, so it could not exercise this provider branch; no claim about arbitrary no-witness occurrence mapping is made.

## RED and GREEN evidence

The RED used the existing public synthetic Shape/Skin package, with Materials ON through the real Blender import operator. Before the code change, both slot-0 records retained the reserved GUID/fileID pair, remained `UNRESOLVED`, and had no preview assigned. Materials OFF captured no renderer Material dependency.

Final GREEN used Blender `5.2.1 LTS`, the same package (`SHA-256 9020b4f5072bc862169126c72fc35bcd8799879be23c4ad589ffc830e82d68ef`) and optional v3 witness (`SHA-256 60e82d1f45d148d9ac6518d764bdb3ec75c05dd1caab6cf9ea42813e872a1e71`). It passed:

- real import operator with Materials ON and OFF; both preserved the existing two occurrence Skin/Shape/pose checks and saved/reopened parity;
- Materials ON bound the two exact occurrences to one reusable preview datablock, reported no unresolved package dependency, preserved one user-edited slot through repeated resolve and save/reopen, and kept overall outcome `PARTIAL`;
- Materials OFF created no preview Material;
- negative controls for wrong fileID/GUID/type, fractional raw fileID, ordinary missing provider, and explicit null remained unresolved and unbound;
- focused Python suite: 70 tests passed, including import outcome, Prefab parsing, occurrence projection, and witness bridge;
- `compileall` over Blender, Unity, operator, and test Python modules passed; `git diff --check` passed.

The generated `SkinShapeMaterialOptionResult.json` reports the fixture/package/witness SHA, Materials ON/OFF parity, save/reopen parity, preview provenance, negative controls, and `PARTIAL` outcome. It is local run evidence, not committed as a machine-specific log. Unity was not launched for this checkpoint. The focused late material slot Blender regression passed.

## Final SOL review and follow-up

GPT-6.1 SOL medium read-only final review found a remaining variant-path issue: `PrefabData.modifications()` extracted the integer prefix of a fractional `objectReference.fileID` before occurrence projection. The parser now preserves the raw scalar, accepting it as raw `int` only when the entire scalar is integer syntax; `10303.9` stays a string through variant projection and witness dependency capture and therefore fails the preview allowlist. The compatibility override capture also carries the raw field. Parser and variant projection regressions cover this route. The internal effective-prefab comparison view intentionally omits the auxiliary raw field.

The same review found that duplicate existing preview candidates were refused but mislabeled as missing consumer, and a lone candidate without the approximate marker could be reused on the compatibility route. Duplicate candidates now report `AMBIGUOUS_PROVIDER`; an incomplete sole candidate reports `UNSUPPORTED` and remains unbound. Persistent Blender integration assertions cover both cases. SOL reviewed the corrected final diff and reported no remaining blocking findings.

After those changes, the focused Python suite passed 70 tests. Blender `5.2.1 LTS` reran the public synthetic import with Materials ON/OFF, occurrence-level slot edit preservation, save/reopen, fractional-ID negative control, duplicate/incomplete preview candidate checks, and Skin/Shape parity; `BUILTIN_PREVIEW_CANDIDATE_SAFETY_PASS`, `BUILTIN_PREVIEW_BOUNDARY_PASS`, both mode PASS markers, and overall parity PASS were observed. Unity and actual Material export were not run.

The separate cross-package synthetic Blender runner first hit `WinError 5` at its default AppData source-storage path under ordinary sandbox execution. The same runner was then submitted via the formal approved execution path, without redirecting that path; it got past access and failed at its own grouped-fixture assertion (`AttributeError: 'NoneType' object has no attribute 'materials'`, `tests/blender_cross_package_dependency_test.py:169`) because its synthetic `Coat` object had no mesh data. This is a runner/fixture failure, not evidence of a Unity license or runtime problem, and does not establish an importer product defect. The runner remains non-passing and requires separate fixture diagnosis.

### Cross-package runner diagnosis (2026-10-05)

Current public source was `d47091c2680b53ac0cb11041f5ece11cd851aa90`; a correctly isolated comparison at `ec81dc2c176f2b782eb96562e7476f1719c46023` fails at the same grouped assertion. This supports the narrow conclusion that the failure was not introduced by changes between those two revisions; it does not establish when it first appeared or make a broader claim about product behavior.

The fixture's `prefab(fbx_guid, material_guid)` does not use `fbx_guid`. Its synthetic GameObject has a Transform and MeshRenderer but no MeshFilter. Renderer occurrence projection therefore has no exact mesh reference (`INVALID_MESH_FILTER`). The Blender object selected by `unity_prefab_file_id == "1001"` is an Empty Prefab wrapper; its `.data` is `None`. The native FBX mesh is a distinct Mesh object and is not identified merely by sharing a display name.

The importer has two distinct Material dependency routes:

- `PREFAB_RENDERER_MATERIAL` records carry the Prefab renderer's target GUID/fileID and consumer GameObject/slot identity. `apply_prefab_materials` captures this route only when its exact `object_map[game_object_id]` entry is a material-bearing object; the resolver then uses that serialized identity and slot ownership receipt for late resolution. The witness restoration route can carry a stronger native FBX receipt. The current fixture has no MeshFilter, so it cannot establish the required renderer-to-mesh relationship; its wrapper lookup is not proof that the actual native Mesh was bound.
- `FBX_EXTERNAL_MATERIAL` records come from the FBX `.meta` `externalObjects` mapping. `apply_materials_by_name` records the target GUID and source slot/path, but omits a consumer GameObject ID or FBX object/mesh receipt. Generic `_find_consumer` requires an exact object consumer and returns no match without it. Therefore, finding a later provider by GUID does not identify a safe native slot to mutate. The CPD runner counts these records but does not assert that they bind.

SOL medium confirmed the second route is a product gap in the current source. A focused fixture should keep these routes separate: for Prefab materials, serialize a valid MeshFilter reference and route import through the existing projection/witness capture, then assert a real `PREFAB_RENDERER_MATERIAL` record resolves after provider import; for FBX `externalObjects`, make the Prefab material reference null so it cannot satisfy the same assertion. The latter fixture should map a source FBX material slot through `.meta` to a target material GUID/fileID, then use the actual import operator to capture an exact FBX receipt (source package, FBX GUID/SHA, geometry/object/mesh receipt IDs, slot). Test no-provider, same-name/wrong-GUID provider refusal, correct late provider binding, and a user edit made before provider arrival remaining `USER_EDIT_PRESERVED`. Save/reopen and repeated resolve must retain the exact slot state. A new resolver branch should require a unique receipt-matching object and existing slot ownership checks; material names may identify the source serialized mapping row only and must never select a provider or substitute for the receipt.

The existing `confirm_renderer_binding` operator is a separate explicit path: it needs the provider already present and assigns object-level slots, but does not capture or resolve dependency records. It cannot be used as evidence for late resolution. No test expectation was weakened and no child Mesh was selected by name or uniqueness alone. No product code or test was changed, and Unity was not used. The runner's original failure is shared by `ec81` and `d470`; the evidence only shows it was not introduced between those revisions.

## Boundaries

This checkpoint establishes a usable, approximate Blender preview for one exact built-in Material reference in the tested public synthetic occurrence route. It does not establish every built-in Material, exact Unity shader appearance, arbitrary Renderer mapping without identity evidence, export restoration, fresh Unity package reimport, either product E2E gate, or Unity runtime behavior.
