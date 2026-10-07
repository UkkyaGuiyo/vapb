# Strict witnessed import and immediate export

This report covers one first-party synthetic three-slot Unity package. It records T0-A and T0-B only. It does not establish output-package closure, saved-scene reopen behavior, a Unity target import, rendering/GPU behavior, or VRChat acceptance.

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

## Limits and next gate

This pass applies to the pinned synthetic package and its exact Unity witness. It does not show that the emitted package contains all expected assets or that a fresh Unity project imports it correctly. T0-C must independently inspect the output package's Material GUID/fileID/meta/payload closure, manifest mappings, generated FBX material carriers, and face-group association. Only after that should a fresh Unity target import be considered.

Raw logs, local project paths, process manifests, Blender scene files, and package artifacts remain in the local task evidence directory and are not included in the repository.
