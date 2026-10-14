# Unity source preservation — three independent judgments

Authority: owner 12:29 clarification. [ABC](ABC_COMPARISON_REPORT.md), [external shader matrix](EXTERNAL_SHADER_DEPENDENCY_MATRIX.md) and [format assessment](VRM_GLTF_REUSE_ASSESSMENT.md) share this contract. Preserving serialized data alone never establishes native restoration.

| Judgment | Required proof |
| --- | --- |
| SOURCE_PRESERVED | Original available asset/meta bytes or declared serialized fields and references captured unchanged; identify absent content honestly |
| IDENTITY_RESOLVED | Actual edited entity/source ownership, scoped GUID/signed fileID, dependencies and binding correspondence independently proved; ambiguity UNRESOLVED |
| UNITY_RESTORED | Native Unity assets/components/refs after import/Apply/reopen reflect intended edits and preserved unedited state; no snapshot-only PASS |

## Current matrix

| Source state | SOURCE_PRESERVED | IDENTITY_RESOLVED | UNITY_RESTORED | Current evidence |
| --- | --- | --- | --- | --- |
| Original Unity Material/meta/Shader properties/texture settings | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | Source Unity helper not run; Blender RGBA isn't Unity source state |
| PhysBone/Collider/Contact/Descriptor | NOT_AUTHORED | NOT_MEASURED | NOT_MEASURED | No SDK components yet; no client/upload |
| Clip/Controller/state/transition/parameter/layer/Playable Layer | NOT_AUTHORED | NOT_MEASURED | NOT_MEASURED | Frozen no-animation authoring input; edited animation separately scoped |
| Menu/Expression Parameters/Constraint/MA/NDMF | NOT_AUTHORED | NOT_MEASURED | NOT_MEASURED | Providers and source structures absent, no assumptions |
| Prefab/Variant/Nested and native GUID/fileID/owners/targets | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | Owned helper will create/assert Source prefab+Variant and capture native refs; Nested not authored |
| Self-authored Blender source files | MEASURED_UNCHANGED_BYTES | NOT_A_UNITY_IDENTITY_TEST | NOT_MEASURED | Source Blend hash stable through save/reopen and GLB observation; FBX copy hash matched |

NOT_AUTHORED describes source presence, not an additional PASS/FAIL verdict. Geometry authority remains Blender final state; original Mesh native fileID continuity is separately observable, not a universal prerequisite for correct regenerated geometry. Source Material/Texture identity and unedited Unity state must still be resolved and verified.

For each V/R boundary and C1 original/C2 regenerated/C3 edited mesh+original restoration, record these columns independently. Original reuse, serialized-only retention, regenerated analogue, absent and unresolved are separate observations. Verify bone survival/frames, renderer/material refs, animation bindings after renamed bones/shapes, variant ancestry, dependencies and original asset preservation. No name-similarity repair, unconditional component copy or approximation-derived Shader/PhysBone state. Setting retention and actual behavior are distinct: bone/weight edits may change motion. VRChat behavior stays NOT_MEASURED.

An independently reviewed source-creation helper uses an exact owned root/marker, rejects occupied or partial outputs, asserts required human mappings/Variant relation, and captures full hierarchy, skin-bone order/bindposes, native full influences with float bits and zero-default single-frame shapes. Static compilation succeeds; this is preparation, not a source-native or restoration success. Existing source/evidence and FBX remain intact; no new restore mechanism or product migration was implemented.
