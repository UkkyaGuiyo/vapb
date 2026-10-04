# R2 Stage3 Finalizer Post-Patch Unity QA

- Repository: https://github.com/UkkyaGuiyo/vapb
- Branch: `feature/r2-material-slot-reorder`
- Finalizer source under test: `6c433e4106565f982b61c3a9eca6e719f266a956`
- Unity Editor: `2022.3.22f1`
- Fixture: the existing marked disposable Stage3 TargetProject and public synthetic skin-topology fixture. No user Unity Project was copied or changed; no package was added.

## Final-source Apply gate

The final committed Finalizer and updated compatibility test source were synchronized into the disposable TargetProject. The public synthetic probe used a fresh V10 Variant/result path so V7, V8, and V9 outputs were preserved. The manifest was temporarily pointed at that new Variant path and then restored byte-for-byte; original manifest SHA-256: `e5c3dcc9f08a016f34ae8f3e659e73583ec63d860a26e06f26964812c1169642`.

The probe called Finalizer Apply once and repeat Apply once. Unity exited 0 and the probe reported PASS. Both calls logged `VAPB_MODEL_SKIN_VARIANT_APPLIED=1`; repeat Apply was idempotent. The V10 report records Variant creation, expected source-prefab ancestry, exact final mesh, bones/materials/renderer preservation, structural preservation, and the tolerance-boundary assertion as true.

## BakeMesh control semantics

“PASS” means **both** raw booleans `within_target_bounds` and `points_match_equation` are true. It does not mean an expected rejection succeeded. In particular, control 2 is inside the bounds but does not match the skin equation.

| Order | BakeMesh / renderer transform | within_target_bounds | points_match_equation | Max root-local vertex error | Equation-bounds delta |
|---:|---|---:|---:|---:|---:|
| 0 | `useScale=true` / full `localToWorldMatrix` | true | true | `1.863047938144291e-9` | `1.862645149230957e-9` |
| 1 | `useScale=true` / position+rotation only | true | false | `0.01400071196258068` | `0.00989999994635582` |
| 2 | `useScale=false` / full `localToWorldMatrix` | false | false | `1.4000710248947144` | `0.9900000095367432` |
| 3 | `useScale=false` / position+rotation only | true | true | `9.32128041419844e-10` | `9.313225746154785e-10` |

The two measurements are in rootBone-local units. Pointwise match is `maximumRootPointError <= 0.001`; `within_target_bounds` checks the transformed baked points against the renderer's root-local bounds with the same tolerance. On this positive uniform-scale-100 fixture, 0.001 root-local units correspond to about 0.1 world units. The equation-bounds delta is the maximum difference between the baked point-cloud root AABB and the weighted-equation root AABB.

The selected probe path is explicitly fixed to control 0: `useScale=true` followed by the full renderer `localToWorldMatrix`, then the rootBone inverse. The repeat check uses the same fixed path. The four-control rows are diagnostics; the probe does not choose whichever mode passes at runtime. Control 3 also matched the equation, so the observations do not establish a universal rule for the meaning of `useScale`.

The expected points are calculated without using BakeMesh output: for each final-mesh vertex, the probe sums weighted `bone.localToWorld * bindpose * vertex` positions and converts that result to rootBone-local space. The baked point cloud is independently transformed and compared vertex by vertex. This is independent of the baked samples, but it uses the same fixture mesh, weights, bones, and transforms. The product Finalizer itself validates rest-mesh bounds with its weighted bindpose/bone equation; it does not select a BakeMesh mode.

The transform control reported raw `baked_frame_control_valid=true` and scale `100`: positive uniform scale, rotation, positive determinant, and no shear. V8's position/rotation-only explanation for `useScale=true` was an unconfirmed hypothesis and failed this fixture's measurement (max root error 0.014). The four-mode calibration preceded V10 on the same synthetic fixture; V10 rechecked the fixed choice on that fixture, not on an unseen holdout. The result is therefore a limited positive, not general or out-of-sample proof.

## Run identity and inputs

The retained staged V10 probe SHA-256 is `389f013912d6732696f7ea4e3077242484bf44cfd81c1fd804eea48f4767c818`; this was computed from the retained TargetProject probe file after execution because the setup ledger did not capture its pre-run hash. The tracked public probe source SHA-256 is `29534195ea2ee2a7f7434df920172b852e9d2fc7bca03e12fe527b63f77d6974`. The staged copy differs by the result-name change from V9 to V10.

The serialized V10 result SHA-256 is `0c9a6d240c3c0571756d0fb4b0fe04fd5f665d593e5a17782f92fe72e234e4c0`, identical to V9 because the report has no run identifier or probe hash and the serialized values are the same. Do not use that digest alone to identify the V10 run; correlate the V10 result path with the setup record and Unity invocation log.

The read-only evidence collector independently confirmed the Variant parent path `Assets/VapbSkinRoundtrip/Avatar.prefab` and matching GUID; 12 property modifications (mesh/name and root pose defaults); and zero added/removed components or GameObjects. It recorded `variant_created=true` and `anomalous_no_variant=false`; no deliberate no-Variant fault injection was run.

Source FBX SHA-256 `78f0c552b59ca8ce3ff8e283a0f1f8bbc4add38d8bf6757e2b1fd6fad4dea1af`, edited FBX `a95d28bdcff674b8fcacd7d8684ba8b78a4eb9b91b6355b576e4992549baf703`, source prefab `ccb0338b8e67970d23bc5d0949ff0977072d2621031cd0f5d65b5e32ce11d4b2`, and restored original manifest `e5c3dcc9f08a016f34ae8f3e659e73583ec63d860a26e06f26964812c1169642` matched expected hashes. Unity process exit was 0 for the Apply probe and for the separate read-only evidence collector; post-run Target Editor count was 0.

The focused EditMode compatibility suite passed 7/7 with zero C# compile errors after the float-edge patch. It covers exact inclusive tolerance edges on six faces, adjacent outside single-precision values, and existing route/scope controls.

## Planned fault-injection coverage (not run)

The 7 compatibility tests exercise helper/scope/bounds behavior; they do not call public Finalizer Apply. Add two public Apply integration cases in the marked synthetic TargetProject, each with a separate copy of the manifest and a fresh, initially absent Variant path:

1. **Pre-witness rejection:** set `source_model_sha256` in the copied task to a different, syntactically valid 64-hex digest while leaving all asset bytes unchanged. Expect `Apply=false` and `SOURCE_HASH_OR_PATH_MISMATCH` from `PrepareWitness`; assert no applied log, no Variant prefab/meta/GUID, and unchanged source/edited FBX, prefab, canonical manifest, fault-manifest bytes, and their metadata across the call.
2. **Post-witness rejection:** change one non-root `edited_bone_realization_id` in a separate manifest copy to a different unique valid UID. The manifest structure still passes, but edited-marker resolution should reject with `EDITED_BONES_INVALID` after the source witness import/restore. Assert the same no-Variant outcome and byte/hash/GUID invariants, including source FBX/meta restoration and the fault manifest's own bytes/meta.

For both cases, assert the expected rejection log and absence on disk **and** through AssetDatabase. Snapshot existing V7–V10 Variant/result files and GUIDs before and after so the fault cases cannot silently replace prior evidence. These tests cover rejection before Variant save, not rollback after a save has begun. They remain planned, not executed, and do not expand the current limited-positive claim.

Detailed logs, XML, result JSON, and disposable TargetProject outputs remain local; raw logs are not included here. This QA is limited to this synthetic fixture in Unity 2022.3.22f1 and makes no claim for other rigs or negative/nonuniform/sheared transforms.
