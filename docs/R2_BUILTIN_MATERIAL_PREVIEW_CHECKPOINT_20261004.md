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
- focused Python suite: 68 tests passed, including import outcome, Prefab parsing, occurrence projection, and witness bridge;
- `compileall` over Blender, Unity, operator, and test Python modules passed; `git diff --check` passed.

The generated `SkinShapeMaterialOptionResult.json` reports the fixture/package/witness SHA, Materials ON/OFF parity, save/reopen parity, preview provenance, negative controls, and `PARTIAL` outcome. It is local run evidence, not committed as a machine-specific log. Unity was not launched for this checkpoint. A separate cross-package Blender runner was attempted but stopped on Windows access denied at Blender's default AppData source-storage path; that path was not redirected or bypassed. The focused late material slot Blender regression passed.

GPT-6.1 SOL medium read-only review found that integer normalization could admit a fractional raw fileID and that the witness route needed raw-value transport. The raw identity is now carried to dependency resolution; the fractional case is covered through parser normalization and the resolver's fail-closed negative control. The updated code was not submitted for a second SOL review.

## Boundaries

This checkpoint establishes a usable, approximate Blender preview for one exact built-in Material reference in the tested public synthetic occurrence route. It does not establish every built-in Material, exact Unity shader appearance, arbitrary Renderer mapping without identity evidence, export restoration, fresh Unity package reimport, either product E2E gate, or Unity runtime behavior.
