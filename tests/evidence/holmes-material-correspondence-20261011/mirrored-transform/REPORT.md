# HOLMES-20261011-08 — mirrored Transform fidelity

**VERIFIED_IN_SCOPE.** H-A supported in this static negative-ObjectScale case; H-B not observed. A Material, B mirrored world geometry, C world normals, D determinant-aware index parity, E observation-only CullBack render PASS. First failed product stage: none; no product repair.

Instruction source **CHAT_FALLBACK_NOT_SAVED_TO_GITHUB**; no issuing instruction commit. Start branch `feature/holmes-asymmetric-world-fidelity-20261011`, base SHA `c0fee02206782f8786ee02e8d960df3a983b75ac`; prior07 runtime `a5ff57d32303b2489cc4ce9036579e914ca11b42`. Work branch `feature/holmes-mirrored-transform-fidelity-20261011`. Prior07 evidence only read, never rerun. No instruction-branch development.

## Input and frozen authority

Exactly one new Box case. Compared to07, local vertices/polygon order/UV/local face normals/translation/Euler/slots/providers are identical; only ObjectScale.x changes sign. Halfedges `(0.5,1,2.5)`, T `(3,-2,5)`, Blender XYZ Euler degrees `(20,-30,40)`, Scale `(-1.25,0.75,1.5)`. No Skin/ShapeKey/Modifier/hierarchy. No ApplyScale, polygon reversal, normal recalculation or transform baking in Blender. Object/Mesh custom keys remain empty; no old ModelUID/GeometryUID/receipt transfer.

Standard self-authored OrderedSix package input SHA256 `5492475a7231ba21d6f4c20308e2db84865df7e08770aa5c4bd9fd84f7064dcf`; exact four source Material providers retained. Imported Meshes/data were removed only in own working copy. All12 frozen source asset files still match their initial hashes. Historic `coordinate_intervention_20261007/negative_scale_only` is COORDINATE_AND_FACE_IDENTITY_UNPROVEN and contributes no PASS proof.

Actual Blender **5.2.1 LTS**, Unity **2022.3.22f1**. Saved mirror input Blend SHA256 `02f63e4b565d0ecc6f6f879aea75e1a31b5be21dca5ef0e45d11940ad758f117`. Frozen local arrays, corner order, loop UV, local face normals, matrix_world, world vertices/normals, Object determinant and full Material datablock state in `replace.json`; private provider paths omitted publicly. Different-process reopen state identical; export keeps editing geometry/transform/identity keys and Material datablocks unchanged. Package staging uses copied Object/Mesh/Material datablocks.

C remains `(-x,z,-y)`, det(C)=-1, expected translation `(-3,5,2)`. Installed Blender FBX preset/axis_conversion and existing read-only control ground this convention; no08 observation fitting. Object determinant **-1.40625**, det(C*M) **+1.40625**. These differ from native Renderer determinant magnitude because native Mesh file units and Renderer scale are separate.

Oracle SHA256 `cbe13e2671261ff59416d38af39c03423d828676a1278642c30694ed81eb9543` and render-oracle SHA256 `dd08aff37e49625f704833c5c69c5431ea31f9abe9cc769e11d01bbac9dd05c7` frozenUTC `2026-10-11T15:07:04.444962+00:00`, before Unity launch. Launcher checks both hashes. Position envelope128*float32_u*B=6.55089547763e-05, B=8.58638972044; normal envelope256*u*conditionScale=3.0517578125e-05, u=2^-24 and |scale|max/|scale|min=2. Fixed engineering tolerances; no post-observation change.

## A/B/C/D and effective front face

World normals use `normalize(C * inverseTranspose(M) * localNormal)`; negative determinant is not an extra normal negation. `cross(Ma,Mb)=det(M)*inverseTranspose(M)*cross(a,b)` means a mirrored Object can have raw triangle cross opposite its outward normal. Normals, raw index parity and rendered front side are separately assessed.

Native Renderer determinant **-1406250.125**, negative Transform retained. Raw world cross/outward-normal dot range [-0.999999999999999, -0.999999999999978]. This raw sign alone is not a face-flip defect. Determinant-aware parity minimum **0.999999999999978**, threshold0.999999, PASS. Actual render E separately establishes the effective front side.

| Check | Result | Observed bound |
|---|---|---|
| A six-face Material identity | PASS | Each geometric face has exact source package/GUID/signedfileID; array counts alone not used |
| B mirrored world geometry | PASS | Max component error 5.21540641785e-07; each quad has exactly two triangles, exact boundary multiplicities and one cancelling internal diagonal |
| C inverse-transpose normal | PASS | Max component error 1.76770277305e-07 |
| D determinant-aware index parity | PASS | Negative Transform preserved; raw world sign explained, not mistaken for rendered failure |
| E known CullBack render | PASS | Direct3D11, all six outside views visible/all six inside views culled |

Positions/normals were independently recalculated in Python from captured native local arrays and localToWorld. 12 native triangles joined to predeclared world corners; no Material fitting, old IDs, UV fingerprint correspondence or array-count-only verdict. Coverage ignores orientation while D checks actual index order. Missing/duplicate triangles and bad internal diagonals are rejected. All native topology/indices/baseVertex/local vertices/normals/UV/matrix/TRS/determinant/world arrays are in `native.json`.

Four captured-data negatives: one geometric face Material swap fails A (B/C/D PASS); world X/Y swap fails B; normal reversal fails C while A/B/D PASS; one triangle winding reversal fails D while A/B/C PASS. No extra fixtures/native reruns. Full results in `judgment.json`.

## Render evidence and limitations

Original source Materials use a built-in lit shader (serialized shader fileID46). They are not suitable for the lighting-independent binary white/black face oracle. E uses a fresh observation-only clone, the exact untouched Mesh and copied original Transform, and a self-authored unlit Shader with explicit `Cull Back`. Camera size/distance/resolution and thresholds were fixed before consumer. Six face-center outside/inside views use32x32 RenderTexture + Camera.Render/ReadPixels. No GL.invertCulling override. Renderer clone only receives observation Materials; actual prefab Renderer is never assigned by observer. Original Prefab/Materials/Mesh references and bytes checked unchanged afterward. **Product Material rendering NOT_RUN**; E is raster front/back proof for the known observation shader.

| Face | Outside white/1024 | Inside white/1024 |
|---|---|---|
| +X | 1024 | 0 |
| +Y | 1024 | 0 |
| +Z | 1024 | 0 |
| -X | 1024 | 0 |
| -Y | 1024 | 0 |
| -Z | 1024 | 0 |

Exact captured PNGs are in `render/`; hashes/camera poses/backend in `native.json` and `judgment.json`. Real Direct3D11 backend confirmed; -nographics omitted as required by the shared GPU-render lesson.

[Unity axes](https://docs.unity3d.com/2022.3/Documentation/Manual/QuaternionAndEulerRotationsInUnity.html), [front winding](https://docs.unity3d.com/2022.3/Documentation/Manual/AnatomyofaMesh.html), [negative-scale draw winding](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rendering.BatchDrawCommandFlags.FlipWinding.html), [Cull Back](https://docs.unity3d.com/2022.3/Documentation/Manual/SL-Cull.html), [Camera.Render](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Camera.Render.html). The BatchDrawCommand flag documents the principle; this case proves actual MeshRenderer front/back via pixels rather than assuming every renderer uses that API.

## Face Materials and independent world targets

| Face | Material GUID / signedfileID | Expected Unity world center | Expected outward world normal |
|---|---|---|---|
| +X | `afd253dd071f7e5469e24392cdbf181c` / `2100000` | (-2.58536628, 4.6875, 2.34791899) | (0.663413942, -0.50000006, 0.556670368) |
| +Y | `242d369718abeb942873ec054737cf94` / `2100000` | (-2.44873193, 5.22214854, 1.54255766) | (0.735024095, 0.296198189, -0.609923184) |
| +Z | `4d7af3be41387054c9f86b68e180d9e7` / `2100000` | (-2.47471169, 8.05174112, 4.1150527) | (0.140076846, 0.813797712, 0.564014018) |
| -X | `70c1cb3bd3a723141a677eca237e252c` / `2100000` | (-3.41463369, 5.3125, 1.65208101) | (-0.663413942, 0.50000006, -0.556670368) |
| -Y | `242d369718abeb942873ec054737cf94` / `2100000` | (-3.55126804, 4.77785146, 2.45744234) | (-0.735024095, -0.296198189, 0.609923184) |
| -Z | `4d7af3be41387054c9f86b68e180d9e7` / `2100000` | (-3.52528828, 1.94825888, -0.1150527) | (-0.140076846, -0.813797712, -0.564014018) |

All four providers are from the exact input package above; provider asset/meta SHA256 and signed header verification are in `replace.json`. All frozen corner coordinates in `oracle-frozen.json`, actual world coordinates/normals in `native.json`.

| Native asset | GUID | signedfileID |
|---|---|---|
| mesh | `97bcbc6b69a940bc94bfd0f6aeb9ab3c` | `4493585093827132993` |
| renderer | `220f485a723ee564cbd8b5105bbbbec3` | `5233528964529515272` |
| prefab | `220f485a723ee564cbd8b5105bbbbec3` | `7313456084772622100` |
| manifest | `b336eab55f53cbe47e82eece8dbae291` | `4900000` |
| finalizer_script | `e5be0cf984636e0046423986603840e8` | `11500000` |

## Stages, outputs, preservation and next minimum

Blender standard import/preparation/save PASS; normal exit; different-process reopen unchanged PASS; standard VAPB final-state package Export PASS. Fresh owned Unity initially contains only observer plus observation Shader; no VAPB assembly/FBX/Material/Prefab. This output package alone imported; compile errors0, reload complete; explicit packaged Finalizer Apply true/COMPLETE, new Prefab absent beforehand. Repeat Apply keeps prefab bytes/Mesh/Material identities unchanged. No product source edits; same packaged Finalizer SHA as actual source. Export IDs resolved from actual FBX serialized transport labels/properties, recorded with recipe/hash/provider data in `transport.json`/`export.json`. Generated FBX importer meta changes by Finalizer are recorded and distinct from preserved source metas.

| Output | SHA256 |
|---|---|
| package_sha256 | `0f699eb64a3b864cd06ddede7d4e691bd063701d8c675a95ab20b2ccf473edbf` |
| fbx_sha256 | `f8f6ffdb30cac2b30063c63924574fdf32af2665c6660e58ba5c815f65b36a0f` |
| manifest_sha256 | `f44e970ee4ba95b195e6e297a84c1856f20355b2ac00d3378696f04b10b08a57` |

Source SHA256 and exact executed observer/Shader hashes in `pre-consumer-freeze.json`/`run-summary.json`. Both Blender phases execute identical source bytes. All prior evidence, original package/FBX/meta/Prefab/Materials and Scenes preserved; no scene saved. No user private corpus/SDK/purchased assets/secret/raw log publication. Existing lease/mutex/PID/RAM/lock guards reused. No other Editor stop or lock removal.

Blender replace: PID15728, startUTC `2026-10-11T15:05:08.6901965Z`, exitUTC `2026-10-11T15:05:12.2464327Z`, exit0/children absent; actual pre-start freeGiB 5.434910.
Blender export: PID5944, startUTC `2026-10-11T15:05:12.4983309Z`, exitUTC `2026-10-11T15:05:15.7693895Z`, exit0/children absent; actual pre-start freeGiB 5.419277.

Unity PID31132, startUTC `2026-10-11T15:07:24.6399462Z`, exitUTC `2026-10-11T15:07:40.0267115Z`, exit0/children absent/own lock absent, pre-start freeGiB 4.941666. ReturnUTC `2026-10-11T15:09:11.0241270Z`: process census conflict false, Blender absent, pool all FREE, mutex probe available/released, own lock absent, actual freeGiB 5.158859.

Independent review KEEP, one fresh read-only context requested GPT-6.1 SOL/medium; details in REVIEW.md. Publication-only convention JSON trailing newline corrected to exact pre-consumer frozen bytes; staged blob hash verified. No native rerun. Primary actual model/reasoning unavailable. Latest formal remaining93%; no reset/stop threshold reached. Next minimum: normal feature commit/push/exact remote readback. No product fix needed. Parent hierarchies, Skin/animation, other negative-scale combinations, actual product Shader rendering, VRChat and GUI remain outside this one case.

GitHub save state: local evidence only until approved feature commit/push/readback. Runtime evidence commit link will be recorded after verification. No merge/main/dev/Release/force.
