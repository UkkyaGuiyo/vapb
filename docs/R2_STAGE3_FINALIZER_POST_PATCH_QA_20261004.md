# R2 Stage3 Finalizer Post-Patch Unity QA

- Repository: https://github.com/UkkyaGuiyo/vapb
- Branch: `feature/r2-material-slot-reorder`
- Finalizer source under test: `6c433e4106565f982b61c3a9eca6e719f266a956`
- Unity Editor: `2022.3.22f1`
- Fixture: the existing marked disposable Stage3 TargetProject and its public synthetic skin-topology fixture. No user Unity Project was copied or changed; no package was added.

## Final-source Apply gate

The final committed Finalizer and the updated compatibility test source were hash-synchronized into the disposable TargetProject. The probe ran with a fresh V10 Variant/result path so existing V7, V8, and V9 results were preserved. The manifest was temporarily pointed at that new output path, then restored byte-for-byte; original manifest SHA-256: `e5c3dcc9f08a016f34ae8f3e659e73583ec63d860a26e06f26964812c1169642`.

Unity ran the post-patch V10 probe once. The probe exited 0 and reported PASS:

- First Apply succeeded; repeat Apply was idempotent.
- Variant was created, had the expected source prefab as parent, used the exact final mesh, and preserved the fixture's bones, materials, renderer state, and structure.
- The tolerance boundary assertion passed.
- Independent fixture control reported positive uniform scale 100. Maximum root-local point error was `1.86304794e-9`; bounds delta was `1.86264515e-9`.
- The four BakeMesh conversion controls, in order `true + localToWorld`, `true + position/rotation only`, `false + localToWorld`, `false + position/rotation only`, yielded `PASS / FAIL / FAIL / PASS`. This is specific to this Unity version and synthetic fixture.
- Variant ancestry was independently read back: parent path `Assets/VapbSkinRoundtrip/Avatar.prefab`, matching the source prefab GUID. There were 12 property modifications (mesh/name and root pose defaults), with zero added/removed components or GameObjects. The probe's structure-preservation gate passed.
- No anomalous missing-Variant result occurred: `variant_created=true`, `anomalous_no_variant=false`. A deliberate no-Variant fault injection was not part of this run.
- Source FBX, edited FBX, source prefab, and restored manifest hashes matched the manifest's expected values; the probe also reported all four inputs unchanged.

The V10 result JSON SHA-256 is `0c9a6d240c3c0571756d0fb4b0fe04fd5f665d593e5a17782f92fe72e234e4c0`. The separate read-only evidence JSON SHA-256 is `3a7f5fb08726630307a012944311448b08a68cdc09a040616d17e3bb6423483f`. Unity process exit codes were 0 for the Apply gate and 0 for the evidence collector; a post-run query found no Target Editor process remaining.

## Compatibility suite

After the float-edge patch, the focused EditMode suite reported 7/7 passed and 0 failed, with no C# compiler errors. It covers exact inclusive tolerance edges on all six faces and immediately adjacent outside single-precision values, in addition to the existing route/scope compatibility controls.

## Evidence scope

The detailed Unity logs, XML, result JSON, and disposable TargetProject outputs remain local; raw logs are not included in this note. This QA proves the committed Finalizer on this synthetic fixture in Unity 2022.3.22f1. It does not claim coverage for other rigs, negative/nonuniform/sheared transforms, or a deliberate no-Variant fault case.
