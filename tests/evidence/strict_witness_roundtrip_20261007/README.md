# Strict witnessed import, archive closure, and saved-scene reopen

This report covers one first-party synthetic three-slot Unity package. It records T0-A through T1, including a fresh native FBX import and a fresh-process saved-scene reopen/export. Unity target import remains a separate pending gate. It does not establish rendering/GPU behavior, skin deformation fidelity in Unity, or VRChat acceptance.

## Fixed source identity

- Unity package SHA-256: `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`.
- Source FBX: GUID `abcdefabcdefabcdefabcdefabcdefab`, SHA-256 `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5`.
- Source FBX meta SHA-256: `ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d`.
- Unity version: `2022.3.22f1`.

## Unity source witness

The dedicated source project ran `VapbBoneWitnessProbe.Run` once under the approved logged-in execution session. Unity exited 0 and logged `VAPB_BONE_WITNESS_PASS`. The report had `pass=true`, `error=NONE`, and successful original/no-op/marker/restored equivalence and source/meta restoration flags. The mapping linked FBX Model UID `208084244` to Renderer class 137, signed local ID `-61738223220265358`, and Mesh local ID `3538053534738119282`. Its V2 witness records the two ordered Skin bone Model UIDs `144385489`, `517309283`, with root UID `144385489`.

Mapping SHA-256: `9990d46882dd40132f5e59a5ce412c37560caa84bcabb24b577d7e1a0c48113b`; result SHA-256: `c9b2afbc21b95c0e14f24307883f2b7bc1395ab061850cf537db30c9cbe1eae9`; promoted V2 witness SHA-256: `029c56e945b513b27dc72ddf3c636b2a882995ce576e4d0db51cf13fa38a048f`.

The restricted default execution route first failed to connect to the Unity LicensingClient and exited 199 before the probe ran. A retry from the explicitly approved logged-in user session connected and completed the probe. No license settings, security settings, or credentials changed. The successful log also contains a nonfatal validation warning; this result asserts only the observed probe outcome.

## T0-A strict untouched import

Blender 5.2.1 imported the fixed package through the production UnityPackage operator with the exact V2 witness. The test did not assign or repair Material slots. The receipt-matched native Skin Mesh had the three raw Prefab GUID/fileID pairs in order, all linked as `OBJECT` and all carrying the package SHA provenance. An independent native FBX import, performed without loading the VAPB add-on, produced face-slot triangle counts `[2, 4, 6]`; the VAPB import matched those counts and found exactly one valid native Skin receipt.

T0-A result SHA-256: `c362d2f4abb2725e2dff26a5e696cfd7785e89b590eafdaf54225e93dd2d8ced`. Native FBX baseline result SHA-256: `cd052d39ef3081d2d8ef914943a0021f970a40ae57a086d43b7efd61cca11e55`.

## T0-B immediate unchanged export

The imported scene was saved before export. The existing `vapb_unitypackage` Skin/Model route exported the unchanged active Skin Mesh. The semantic snapshot compared object/data identity, transforms, mesh datablock properties, vertex/edge/polygon data and material indices, UVs, modifier targets, material references/links/properties, texture-node and image identities, and image datablocks. It matched before and after export. The saved `.blend` SHA-256 remained `1e4f75e36ff5d0ed76523fdd54eaf936a8275426e3186082eca9e2421de6aa05`; the source archive inventory and original Unity package SHA also remained unchanged.

The emitted Unity package SHA-256 is `b8f3901ef5dd386ecf1a51d266ff3f6b866c6ae7c3409f66e87be335f292c16d`. T0-B result SHA-256: `daf168a1878662478ce6e05fd32db4deb6fa37bd39b40f50dab21f0481e5591d`.

## Source checkout isolation

The T0-C and T1 runners now fail closed if `unitypackage_blender_importer` or any child module is already present in the embedded interpreter's `sys.modules`. On a clean namespace, the selected checkout is loaded and every module origin is checked to remain under that checkout. Focused tests cover a cached child from another checkout, a cached child from the selected checkout, a cached root, and a clean load.

## T0-C output closure

The exact T0-B package was read with the production `RawAssetRepository` and independently with a strict `tarfile` member pass. Both inventories agreed. Duplicate GUID/kind members, case-variant GUID directories, non-regular members, unsafe paths, and NFC/casefold destination collisions are rejected. The source Prefab's raw ordered Material references were `eb805efb35118044db5e74adc652673a:2100000`, `0318f358e4c29034aa90cc8c50b58a93:2100000`, and `64f92a1bd9b35a040bf9e2c6d200b34c:2100000`.

All three source `.mat` payloads, `.meta` bytes/GUIDs, fileIDs, and destination paths matched byte-for-byte. The export manifest has an empty `material_mappings` array for this unchanged route; its `RESTORE_DIRECT_SKIN_VARIANT_V1.material_bindings` records the same ordered GUID/fileID references and transport IDs. Its model GUID/SHA matched the generated FBX asset GUID and payload SHA. The generated FBX was `de246c64f2740ebfb1a93dbad053e07b`, SHA-256 `492344707d583fec2b43b5aa4cda27c47f0466dd8ad497c366292082e3403942`.

A disposable package copy with Material GUID `eb805efb35118044db5e74adc652673a` removed failed specifically with “missing expected Material GUID”; the original package remained unchanged. A separate fresh Blender 5.2.1 process imported the generated FBX without the VAPB add-on. The one armature-backed three-slot Mesh carried the manifest transport IDs as its ordered Material-name labels and had triangle counts `[2, 4, 6]`, matching the independent source FBX oracle. T0-C result SHA-256: `0e058d3449624fec123aefd8828e46de244f9f1a3defc124c46ac38d54786f5d`.

## T1 saved-scene reopen

A fresh Blender process opened the exact saved `.blend` from T0-B. Its complete Mesh-candidate set matched the T0-A recorded semantic fields (receipt identities/validity, slot GUID/fileID, vertex counts, and armature presence), including a second duplicate-like Mesh candidate that was already present in T0-A. The export target was selected by the exact source/root receipt. For that selected target Mesh, the reopened ordered Material references, `OBJECT` links, package provenance, and `[2, 4, 6]` face counts matched; its observed fields remained unchanged across export. Link/provenance claims apply only to this selected receipt-matched Mesh, not every candidate. The source package and saved `.blend` hashes also remained unchanged. This comparison does not include vertex coordinates, UVs, image/node state, or the full source archive store.

The fresh-process export SHA-256 is `20b4b3551b245d9709dac842ba854abfbe7acdb202504f334c7fc5e70e3f89cd`. Its T0-C closure, required-Material negative control, and native FBX carrier/face-count import all passed. The generated FBX SHA-256 was `a27cc6100cd2cbce5f0e9b3a4b24867e042e861ac33ff233a4f37276de491c1e`. T1 result SHA-256: `7efbd0e6bf9427ac9b36e65bdee0948b08a78e3a0f54f2daa0954ba979eef061`; closure result SHA-256: `b314d5a00b834b1634f33edd1537a782624639efdabb1229f8f225c5af603a3c`; native import result SHA-256: `e365f6e7190230b5880fcd8aecc78457fe0511539560d0b9bca37386994d8400`.

## Limits and next gate

These results apply to the pinned synthetic package and exact Unity witness. They do not prove Unity can import the output. A fresh Unity 2022.3.22f1 target is prepared separately with an empty package dependency manifest and a read-only Editor probe; the Editor has not been launched yet. No package download, test-framework install, platform build, rendering/GPU check, or final VRChat validation is claimed. Keep overall roundtrip acceptance pending until the fixed T1 output completes a real CLI Unity package import and its post-import GUID/local-ID, Renderer slot, Mesh, and submesh checks pass.

Raw logs, local project paths, process manifests, Blender scene files, and package artifacts remain in the local task evidence directory and are not included in the repository.
