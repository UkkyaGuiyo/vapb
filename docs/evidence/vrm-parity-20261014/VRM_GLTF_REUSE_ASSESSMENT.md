# VRM / glTF reuse assessment — preliminary, 2026-10-14

Authority: owner's 12:29 clarification, alongside [ABC report](ABC_COMPARISON_REPORT.md). Format adoption and retaining a custom FBX implementation are neither product goals. Do not delete FBX or migrate product code before comparison acceptance. Desired entry remains UnityPackage directly into Blender; unedited Unity data is preserved separately, with intended edits only restored.

## Official specification versus observations

[glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) defines indexed mesh primitives, per-primitive materials, position/normal/tangent/UV attributes, joint weights and inverse binds, morph targets, node transforms and animation. These are format representation capabilities, not measured roundtrip guarantees. [VRM1 humanoid specification](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md) adds humanoid roles; generic props/non-Humanoid rigs require separate glTF evaluation rather than forcing VRM eligibility. Neither specification establishes original Unity AssetDatabase identity or preserved Unity shader/component assets. An existing Manifest/Recipe composite can compensate only if its preservation and reconnection are independently demonstrated.

## Candidate reuse map

| Existing concern | Candidate | Measured status / decision condition |
| --- | --- | --- |
| Geometry/topology/UV/normals/tangents | Bundled Blender glTF IO + UniGLTF return | One Blender-only generic-rig GLB export/import captured; Unity return NOT_MEASURED; generated/recomputed channels separate |
| Material-face/primitive association | glTF primitives plus original Unity Material recipe | GLB reports 3 primitives; native corner/face data captured for independent judgment; original Unity identity NOT_AUTHORED in this preliminary case |
| Bone/Weight/Shape | glTF skin/morph plus optional VRM human mapping | Native arrays captured; full source/return binding proof and expected weight representation remain required |
| Transform/units/rest | glTF node/bind data; pinned consumer APIs | Compare declared frames and native consumer matrices, not bone names or vertex counts |
| Non-Humanoid props | glTF rather than mandatory VRM | Current generic rig has no VRM humanoid extension; source Humanoid validity still NOT_MEASURED |
| Import/export implementation | Existing Blender IO / UniVRM / VRM Add-on | Versions/licenses pinned only where actually verified; preserve VAPB's normal package entry and safe refusal boundaries |
| Unity-specific state | Existing Manifest/Recipe/source assets | SOURCE_PRESERVED, IDENTITY_RESOLVED, UNITY_RESTORED must be separate; no native Blender emulation requirement |

## Actual preliminary execution

Blender 5.2.1 LTS build `9e2066aef7ef`. Bundled `io_scene_gltf2` header declares Apache-2.0; no implementation algorithm was read. Export/import operator properties were observed through public RNA metadata. A separate owned process loaded the same self-authored Blend, captured native arrays, exported GLB without compression or animation, reset only its own in-memory state, imported with vertex merging disabled, then captured again. Exit 0; elapsed **5.4161095 seconds**, operator **AI_CLI**. This includes startup and both conversions; log-reported individual converter times are distinct. Source Blend bytes remained unchanged. This is **not V0/R0**, not UnityPackage entry, and not a Unity restoration result.

`capture()` recomputes Blender tangents. Those observations cannot prove retained imported tangents. RGBA is a diagnostic color tag, not original Unity Material identity or complete shader semantics. Shape defaults and modifier/skin-owner binding are not captured by this preliminary observer. The public-safe native arrays and raw GLB JSON header are saved under `tests/evidence/vrm-parity-20261014/observations`; no whole-route PASS.

Independent saved-array review and a separate root recheck establish the following bounded observations. These are G1 generic glTF findings, not V/R results or format-wide guarantees.

| Feature | G1 observed result | Limit |
| --- | --- | --- |
| Primary mesh | 8 to 36 vertices; all 12 unique oriented UV faces / 36 corners matched; world position maximum component error 0 | UV-seam expansion observed, whole-scene completeness not established |
| Corner UV/normal | UV correspondence unique; 0 changed normal vectors in recorded equal object frames | No Unity consumer observation |
| Tangents | Recomputed values and signs unchanged at matched corners | Imported tangent retention NOT_MEASURED |
| Shapes | Two distinct full world-delta patterns matched; 0 changed matched corner deltas | Native returned defaults not captured |
| Weights | 72 positive corner influences matched with unchanged raw values, including tiny influences | Modifier / armature ownership not captured, semantic skin PASS unavailable |
| Bones | 18 unique correspondences from three exact head anchors and distinct child topology; parent edges agree | 15/18 heads changed, maximum component 3.0547380447387695e-7 m; 18/18 rest matrices changed, maximum component 4.172325134277344e-7. No tolerance or owner acceptance inferred |
| Material face groups | All 2/4/6 memberships preserved in the primary mesh | Original Unity Material identity NOT_AUTHORED |
| Diagnostic RGBA | All three distinct source colors became identical gray [0.800000011920929, 0.800000011920929, 0.800000011920929, 1] | Raw GLB already has these gray factors: divergence at/before export for this material representation/options. FAIL for diagnostic color retention only, not full Unity material/shader or universal glTF loss |
| Additional mesh | Return capture includes a second mesh, diagnostic name Icosphere, 42 vertices / 80 faces; no source UV-face correspondence | Raw GLB contains one mesh; visibility, custom-shape ownership and helper/render role NOT_CAPTURED. UNRESOLVED, not dismissed by name |

GLB SHA256 `3ba1d9e507ba31cf2be79e2d602d9a5f09d4700b4d5653d1c32e1690d41202b3`; generator `Khronos glTF Blender I/O v5.2.40`. No compression, no animation; all influences/morphs requested and vertex merging disabled. A primary-mesh match is not whole-scene parity. Narrow saved-array mutation checks accepted face reordering/cyclic corners, rejected missing/duplicate UV-face correspondence, and detected equal-count material swaps and extra position/shape changes. They do not qualify unimplemented Unity/skin/UV-edit judges. See the independent review for exact scope.

## Recommendation gate

After V0/R0 and matched edits, compare fidelity, original identity, face assignments, shader-state omissions, bone/skin/shape/rest, non-Humanoid scope, actual user actions/time, existing reuse and maintenance/dependency cost. Choose the smallest demonstrated improvement; changing formats is not sufficient. Libraries can reduce handwritten format handling but add version/importer-policy maintenance. Cost is NOT_MEASURED, not assumed lower. SoulFlame detailed algorithms remain gated on saved actual ABC results. No product integration or external package installation occurred.
