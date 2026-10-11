# HOLMES-20261011-07 — asymmetric world fidelity

**VERIFIED_IN_SCOPE.** H-A supported in this bounded static box case; H-B not observed. A Material, B world position/coverage, C normal direction and D outward winding all PASS. First failed product stage: none. No product repair.

Instruction source: **CHAT_FALLBACK_NOT_SAVED_TO_GITHUB**; no issuing GitHub commit. Approved base branch `feature/holmes-replacement-multimaterial-20261011`, SHA `7e44c867ad527f6b85dabc17ceb1eacc9bd113e6`. Work branch `feature/holmes-asymmetric-world-fidelity-20261011`; work root is the isolated checkout recorded privately. No OnlyYou placement, old06 rerun, original asset editing, SDK/commercial asset use, main/dev integration or Release.

## Input and frozen oracle

Actual Blender **5.2.1 LTS**, Unity **2022.3.22f1**. Standard OrderedSix import retained four exact Unity Materials from package `sha256:5492475a7231ba21d6f4c20308e2db84865df7e08770aa5c4bd9fd84f7064dcf`. All imported Mesh objects/data were deleted only in the owned working copy. New box halfedges `(0.5,1,2.5)`, translation `(3,-2,5)`, Blender XYZ Euler degrees `(20,-30,40)`, positive scale `(1.25,0.75,1.5)`; no parent/Skin/ShapeKey/Modifier. New Object/Mesh custom keys remain empty; no old ModelUID/GeometryUID/receipt transplant.

Before export, `replace.json` froze local vertex order, six polygons/corner order, face normals, loop UVs, matrix_world, world corners/normals, exact Material providers and datablock state. `export.json` confirms different-process reopen equal state and export preservation of original editing keys, geometry/transform and Material datablocks. Source inspection confirms export stages copied Object/Mesh data and copied transport Materials. Private provider paths are omitted from public snapshots.

World convention fixed before new Unity observation: `C(x,y,z)=(-x,z,-y)`, determinant -1, expected translation `(-3,5,2)`. Installed official Blender `bpy_extras.io_utils.axis_conversion` (defaults Y-forward/Z-up) and FBX preset -Z-forward/Y-up give A `(x,z,-y)`. The X reflection is grounded in the read-only prior06 native Mesh conversion; that control Renderer matrix gives the same composed C. Unity documentation independently establishes the left-handed axes. This is a declared convention inferred jointly from preset/source, official coordinate rules and already-existing06 control; it was never fitted to07 results. Blender-to-Unity Euler equality is not assumed.

[Unity coordinate system](https://docs.unity3d.com/2022.3/Documentation/Manual/QuaternionAndEulerRotationsInUnity.html), [Unity clockwise front faces](https://docs.unity3d.com/2022.3/Documentation/Manual/AnatomyofaMesh.html). Installed official Blender axis conversion was asserted during preparation; relevant Failure Atlas matrix/world and basis/scale lessons were consulted read-only.

Pre-consumer freeze UTC `2026-10-11T14:04:33.972511+00:00`; exact oracle SHA256 `49926016fb5bcf7b43b80793b6737a32a7127d295d757130a24f66cfb2417941` checked by launcher before Unity. Float32 u=2^-24; B=8.58638972044, fixed position envelope128*u*B=6.55089547763e-05; normal envelope256*u*(1.5/0.75)=3.0517578125e-05. This is a bounded engineering tolerance, not a formal bound on every importer operation. Neither was increased after observation.

Normals use `normalize(C * inverseTranspose(Blender matrix3) * localFaceNormal)`. Captured Unity normals use actual Renderer inverse-transpose; Python independently recalculates captured world positions/normals from native local arrays/matrix. Positive nonuniform scale is included.

## Independent results

| Requirement | Result | Evidence |
|---|---|---|
| A face Material | PASS | Exact package provider/GUID/signedfileID on all six geometric faces |
| B world corners | PASS | Max component error 5.21540641785e-07; six quad boundaries each covered by exactly two triangles and one cancelling internal diagonal |
| C world normals | PASS | Max component error 1.49582610076e-07 |
| D front winding | PASS | Minimum normalized outward cross/expected-normal dot 0.999999999999976; threshold0.999999 |

All 12 native triangles were joined to independently frozen world corners; correspondence uses geometry, not Material fitting, old IDs, UV signatures, face ordinals or array counts. Geometric coverage ignores orientation; D separately tests actual winding. C determinant reverses Blender handedness and Unity clockwise-front import reverses triangle indices: native numeric world cross aligns the expected outward normal. Projected sign alone is not a front/back verdict. **Render/culling NOT_RUN**; no camera/image claim.

Captured-data negatives: one geometric quad face Material swap (both triangles) fails A while B/C/D remain PASS; world X/Y swap and translation loss fail B; one triangle winding reversal fails D while A/B/C remain PASS. No new fixture/native reruns for controls. Complete results in `judgment.json`.

## Material and native identities

| Face | Material GUID | signed fileID |
|---|---|---|
| +X | `afd253dd071f7e5469e24392cdbf181c` | `2100000` |
| +Y | `242d369718abeb942873ec054737cf94` | `2100000` |
| +Z | `4d7af3be41387054c9f86b68e180d9e7` | `2100000` |
| -X | `70c1cb3bd3a723141a677eca237e252c` | `2100000` |
| -Y | `242d369718abeb942873ec054737cf94` | `2100000` |
| -Z | `4d7af3be41387054c9f86b68e180d9e7` | `2100000` |

| Native asset | GUID | signed fileID |
|---|---|---|
| mesh | `4da78cf39cdc49ca93ca14a127b43dbe` | `4493585093827132993` |
| renderer | `5c4c8e3596ab7044bbc2703cd8ecffab` | `8509703755612540818` |
| prefab | `5c4c8e3596ab7044bbc2703cd8ecffab` | `8312100919219292552` |
| manifest | `b336eab55f53cbe47e82eece8dbae291` | `4900000` |
| finalizer_script | `e5be0cf984636e0046423986603840e8` | `11500000` |

subMeshCount **4**; native topology/indices/baseVertex/local vertices/normals/UV/localToWorld/world vertices/world normals and slot refs are in `native.json`. Four generated transport Material Export IDs and Object Export ID are resolved from actual FBX serialization in `transport.json`; recipe providers and original asset/meta hashes are in `replace.json`/`export.json`.

## Import lifecycle and outputs

Owned fresh Project initially had only observer/default asset folders and no VAPB assemblies/FBX/Materials/Prefab. Standard package Import completed; compile finished with zero errors, assembly reload completed, packaged Finalizer became available, explicit Apply returned true/COMPLETE. Observer performs no Material assignment. Actual prefab was absent before Apply; repeat Apply preserves prefab bytes, Mesh and Material refs. Original Material asset/meta bytes and generated FBX bytes remain identical. Generated FBX meta changes from explicit Finalizer importer reconfiguration are expected and are reported separately.

| Output | SHA256 |
|---|---|
| package_sha256 | `7c6aff2b7f6fd57749a93b508873d7a37188ba8c8cb5aae938af50c5ed3db277` |
| fbx_sha256 | `a41a24086a8e505c7fa9f19e98b3221a470eab647107f4bf4ccdfec916580232` |
| manifest_sha256 | `7f2b2ead902fc5e84c050da34ee09367ec5a2e83088256864580ae7559456cad` |

Executed Blender phase source hashes are retained: the preparation phase represents Material links as Python tuples, the reopen/export phase as lists, which serialize identically to frozen JSON. Public Python source has LF-only normalization; exact executed bytes remain private. Product working-source SHA256 values and observer SHA256 in `pre-consumer-freeze.json`/`run-summary.json`; packaged Finalizer source SHA matches actual source. Product source unchanged.

## Preservation, resources, review and next step

Blender replace: PID21132, startUTC `2026-10-11T14:02:58.5814454Z`, exitUTC `2026-10-11T14:03:02.1992154Z`, exit0/owned children absent, pre-start freeGiB 5.486916.
Blender export: PID31616, startUTC `2026-10-11T14:03:34.8603333Z`, exitUTC `2026-10-11T14:03:38.2954212Z`, exit0/owned children absent, pre-start freeGiB 5.496178.

Unity PID29960, startUTC `2026-10-11T14:05:01.5778585Z`, exitUTC `2026-10-11T14:05:15.8058741Z`, exit0/owned children absent/lock absent; pre-start freeGiB 5.022083. Return probeUTC `2026-10-11T14:07:07.8210412Z`: census conflict false, Blender absent, all pool slots FREE, mutex available/probe released, own Project lock absent; actual freeGiB 5.269753.

Original input package plus all12 frozen asset files still match their original hashes; prior evidence and product files untouched. Existing guarded launchers reused; no lock removal or stopping other Editors. Formal usage remaining93% at latest read (primary used7%; model-specific bucket unavailable); no reset. Primary actual model/reasoning unavailable; independent review will record its actual requested settings separately.

Independent review: **KEEP**, no blocking/material findings; fresh GPT-6.1 SOL/medium reviewer independently derived XYZ rotation/scale and recomputed A/B/C/D and all negatives. Details in `REVIEW.md`. Next minimum: none required for HOLMES-07; wait for a separately approved next case. Broader user workflow gates remain unchanged. Broader Skin, animation, negative scale, parents, VRChat runtime, rendered culling, GUI and whole-product completion are outside this case.

GitHub runtime evidence saved and verified by exact API readback of all17 files at commit [`a5ff57d32303b2489cc4ce9036579e914ca11b42`](https://github.com/UkkyaGuiyo/vapb/commit/a5ff57d32303b2489cc4ce9036579e914ca11b42), branch `feature/holmes-asymmetric-world-fidelity-20261011`, readbackUTC `2026-10-11T14:15:48.785536+00:00`. This final report records that verified runtime commit; the subsequent report completion commit is reported in the final reply and independently read back. No force/merge/main/dev/Release.
