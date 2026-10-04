# R2 Stage 3 topology-boundary RED result

This evidence covers one reviewed synthetic fixture/package case. Three RED invocations in the same disposable Target each reported the same expected rejection; a final invocation's Unity Editor process-handle exit was captured as `0`. Tested repo base: branch `feature/r2-material-slot-reorder`, SHA `c0cc3373a6a681c3ef692990f2fa3d889aae850e`. This is a successful RED rejection check, not a product GREEN or general topology-edit support claim.

## Exact input and package

- Unity Editor: `2022.3.22f1`.
- Synthetic source FBX SHA256: `78f0c552b59ca8ce3ff8e283a0f1f8bbc4add38d8bf6757e2b1fd6fad4dea1af`.
- Output unitypackage SHA256: `157eee6379cc435ad9829db2011c1dabeb6f44259d97c385d6e47e3c2db8da73`.
- Preflight inventory SHA256: `e8dd9cec0cdee54eb777c4e3779f47d8347fd620f3e7fe701cf62852a800255f`.
- Exact package inventory: 12 paths; one `RESTORE_MODEL_SKIN_VARIANT_V1` task.
- Package and inventory pins are specific to this reviewed run, including its generated FBX bytes. Regenerated fixtures require a separately reviewed package and new pins.

## Unity import and compile

- Target import/baseline evidence: `pass=true`, package SHA matches, task kind matches.
- Source mesh: 4 vertices, 2 triangles, 6 indices, 2 bones, 1 material, 0 shapes.
- Final mesh: 6 vertices, 2 triangles, 6 indices, 2 bones, 1 material, 0 shapes.
- The UPM manifest/lock remained unchanged. Unity restored the four already locked packages from the existing cache; the 693-file package-cache inventory hash remained `bab1234131e4e081fe8e62e0c6ae3a65c89ea54a8174a6d31cf0e9c850cac135` before and after. No dependency was added or downloaded.
- A separate post-import Unity Editor compile exited `0` with zero `error CS` diagnostics.

## RED result

- Unity Editor exit code captured from its process handle: `0`.
- Log results: `VAPB_MODEL_SKIN_VARIANT_REJECTED=TOPOLOGY_OR_LAYOUT_CHANGED` and `VAPB_MODEL_SKIN_TOPOLOGY_BOUNDARY_RED_PASS`.
- JSON result: `pass=true`, expected and observed rejection both `TOPOLOGY_OR_LAYOUT_CHANGED`.
- Verified: source/final meshes preserve geometric face and bone-weight correspondence; two UV seam splits are present; rest/bindpose parity holds; Variant is absent.
- Protection assertions: source model, edited model, source Prefab, and manifest are unchanged. Their metadata checks also match the post-import baseline. All eight exact SHA256 values are listed below; `TopologyBoundaryImportEvidence.json` also contains the file hashes it records.

| Protected file | SHA256 after RED |
|---|---|
| `Assets/VapbSkinRoundtrip/Input.fbx` | `78f0c552b59ca8ce3ff8e283a0f1f8bbc4add38d8bf6757e2b1fd6fad4dea1af` |
| `Assets/VapbSkinRoundtrip/Input.fbx.meta` | `b8db1243ab1dc67673d0c4283c066a668725c506c888785888931876ff56390f` |
| `Assets/VAPBExport/EditedSkin_defd390bf9c2aaf30f387716c927c40a.fbx` | `a95d28bdcff674b8fcacd7d8684ba8b78a4eb9b91b6355b576e4992549baf703` |
| `Assets/VAPBExport/EditedSkin_defd390bf9c2aaf30f387716c927c40a.fbx.meta` | `c2baf0c9ec3cf32629f820173a7082df16644df451a9d2c881b940848f62bba0` |
| `Assets/VapbSkinRoundtrip/Avatar.prefab` | `ccb0338b8e67970d23bc5d0949ff0977072d2621031cd0f5d65b5e32ce11d4b2` |
| `Assets/VapbSkinRoundtrip/Avatar.prefab.meta` | `56af97c8212679996b4cb4e3d5af8888eef54686a0f0948fab019e2fdffe3b23` |
| `Assets/VAPBExport/manifest.json` | `f26639122cf44d782821a61a6cf817542c8cc58c5415ac250ec99d0ea2dcc812` |
| `Assets/VAPBExport/manifest.json.meta` | `1bc8591c0e79bd0368408aee4e65ac0e32eb1a0715eb43b516b0310190a27089` |

All eight files match the post-import baseline. Seven also match the original package bytes and metadata. The edited FBX metadata is the one expected difference: the Unity ModelImporter baseline-setting step normalized it before RED; its resulting SHA256 is unchanged by the RED operation.

The probe's static `VapbExportObjectMarker` dependency was resolved from the existing Target-only runtime file `Assets/VAPBFinalState/VapbExportObjectMarker.cs` (SHA256 `01e692ecda93ed309f284c743e32caa6c46f94d6b81c51ca91d5a94495b41eb1`). That file and all of `VAPBFinalState` remained outside the fixture move. This run is not self-contained on a clean Target unless that runtime marker dependency is provided.

After package import, the original fixture folder and Editor folder metadata plus only the current synthetic RED probe `.cs/.meta` were restored; the other product helper sources stayed stashed to avoid duplicate classes. The original eight staged files remain preserved in the disposable run root with matching hashes. Existing FinalState sources were not moved or modified. The broader NUnit/EditMode suite was not run.

Raw Unity logs remain in the local disposable run folder because they include host/license metadata. The two sanitized machine-independent evidence JSON files accompany this summary.
