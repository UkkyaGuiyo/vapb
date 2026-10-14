# VRM data loss matrix — r2, NOT MEASURED

Base and preservation contract: [comparison report](ABC_COMPARISON_REPORT.md). All following V/R feature outcomes are **NOT_MEASURED**; execution is currently **BLOCKED**. The evidence column defines required observation, not a result.

| Domain | Feature | Required independent evidence |
| --- | --- | --- |
| A | Mesh | Bijective source/output vertex or seam-equivalence relation, oriented face multiplicity, positions in declared frames; duplicates/missing/ambiguous matches refuse judgment |
| A | UV | Per-face per-corner UV and seam membership; split/weld explained, not hidden by vertex count |
| A | Normals / Tangent | Corner normals, tangent xyz and handedness in declared transform; record recomputation vs retained values and importer policy |
| A | Bone hierarchy | Source-bone to output-bone correspondence, edges and extra bones; names/counts alone insufficient |
| A | RestPose | Local/world rest matrices, bind matrices, scale/axis convention and actual mesh/bone relation; current pose separate |
| A | SkinWeight | Matched vertex/seam class + matched bone + every positive influence; raw value changes and expected Unity representation independently recorded |
| A | ShapeKey | Matched channel plus matched vertex delta, channel existence/default value, affected face/corner topology; name alone insufficient |
| B | Multiple materials | Oriented face→slot→Material semantic mapping and multiplicity; material names or slot count insufficient |
| B | lilToon | Required: native shader/serialized properties, texture refs/settings, actual original Unity Material GUID/signed fileID and face/edited-slot association; appearance reference-only; baking/MToon conversion separate |
| B | Poiyomi | Same observation, exact shader variant/version and locks; basic fallback separate |
| B | Transparency | Required original cutout/blend/zwrite/cull/order state; composited sample reference-only |
| B | NormalMap | Required texture identity/content/settings, strength/UV/property refs; tangent frame under A; shading reference-only |
| B | MatCap | Required original texture/ref/intensity/mask/blend property state; view dependence reference-only |
| B | Reflection | Required original reflection settings/refs; controlled view/light observation reference-only |
| C | PhysBone / Collider | Component script identity, source owner/root, referenced transforms/colliders, serialized fields; SpringBone regeneration is separate |
| C | ContactSender / Receiver | Script identity, owner/ref, collision tags/parameter/shape/fields; SDK Editor serialization only, no client behavior claim |
| C | FXController | Original asset reference, layers/states/transitions/clips/parameters and object bindings; selected appearance isn't retained controller |
| C | ExpressionMenu | Original asset and submenu/parameter references; VRM expression channels aren't the same menu |
| C | AvatarDescriptor | Serialized fields, playable layers, expressions/view/lip/eye refs; newly built descriptor isn't retained original |
| C | PrefabVariant | Native prefab ancestry, overrides and resolved references; ordinary imported Prefab isn't original Variant lineage |
| C | GUID / fileID | Scope-qualified original asset/object IDs, native post-import IDs and actual resolved refs; preserved annotations aren't native identity continuity |
| C | Animation / Playable Layer | Original Clip/Controller states/transitions/parameters/layers/bindings and Descriptor playable references; unchanged preservation vs explicitly edited animation separated |
| C | Expression Parameters | Original asset/ref, value/type/default and menu/FX connections, independent of generated VRM expressions |
| C | Constraint / MA / NDMF | Original supported serialized state/owners/targets/script refs and resolved pinned dependencies; editor build output separate |
| C | Nested Prefab | Original ancestry, nested instance/override correspondence and native resolved target refs |

For B all native preservation fields apply to Poiyomi as well. MToon conversion is not mandatory if original Unity Material is accurately restored. Approximate Blender preview is acceptable as preview; it never supplies original Shader properties. For C use C1 original, C2 VRM regeneration, C3 edited mesh plus original settings restore, with original reuse / serialized-only / regenerated / absent / UNRESOLVED columns. PhysBone parameters, bone/collider correspondence and actual behavior get independent verdicts; no required SpringBone-to-PhysBone approximation. Bone/weight editing can alter motion despite unchanged parameters. No VRChat-runtime verdict is permitted.

## Verdict rules

- `PASS`: observed required semantics at all stated boundaries, save/reopen and Unity readback; unexplained or ambiguous correspondence prohibits PASS. Geometry may be regenerated, but identity continuity and semantic parity must be judged independently. Skin transport obeys the existing PRODUCT_SPEC exact expected-representation/positive-influence contract; no new epsilon overrides it.
- `LOSSY_ACCEPTABLE`: measured loss, its amount/affected scope, and an explicit owner-approved acceptance condition. Owner preference has not been supplied; do not assign it now.
- `FAIL`: execution succeeded enough to observe a violation of the stated feature contract; record first divergent stage and expected/actual.
- `UNSUPPORTED`: pinned tool/runtime explicitly refuses or does not offer the operation; cite actual refusal or exact documented support boundary. Non-Humanoid input does not establish VRM failure on valid Humanoid avatars.
- `NOT_MEASURED`: no required observation. `BLOCKED`: named missing prerequisite stops execution; never a data-loss verdict.

`UNRESOLVED` is a correspondence/reference-resolution observation alongside the allowed verdict vocabulary, not a seventh invented success verdict. Refuse unsupported/incompatible Apply with a reason; if a dependency or matching proof is missing, classify execution BLOCKED and the unresolved feature NOT_MEASURED. Do not copy a preserved component blindly: verify bone survival, Transform/Renderer/Material/Animation/Variant references, scoped IDs, dependencies and original asset protection. A confirmed loss in R alone does not imply an unimplemented composite VRM+recipe route cannot compensate.

## Independent judge and negative controls

Reuse the independent face/corner method from `tests/evidence/holmes-material-correspondence-20261011/judge_faces.py` where applicable, without importing generator expected-output mapping. Fix a separate source snapshot and source vertex/face/bone identities before either converter. Unique UV/corner signatures are observations, not guaranteed universal identifiers. The intentional UV edit invalidates that signature locally: use an unchanged independent position/topology anchor or another declared diagnostic channel for that run. If unique correspondence cannot be established, report NOT_MEASURED for parity instead of fitting a mapping. Coordinate transforms must be predeclared and stage measurements must report max errors/changed sets independently; floating-point PASS expectations need a pinned representation rule before execution.

Existing `judge_faces.py` contains fixed geometry/model/material IDs, 12-face assumptions and VAPB parser dependencies. Reuse its correspondence approach only; it is not an unchanged cross-route judge. Native Blender/Unity arrays must establish semantics independently from VAPB manifests.

Predeclare immutable UV corner signatures for the vertex-displacement run. For the UV-only run, use independently unique positions plus oriented topology/corner incidence; verify uniqueness before editing. Every seam-class member must retain its own corner attributes, weights and shape deltas, never averaged representatives. Bone joins use human roles and independently captured hierarchy/rest relationships; extra-bone relationship must be unique. Shape joins use source distinct delta patterns plus stable unaffected anchors, and edited-channel identity remains ambiguous unless independent correspondence survives. Capture all influences using full native weight APIs, not four-weight summaries. The exact expected Unity representation must be established independently for each route/importer scope; an unproven expectation remains NOT_MEASURED. Raw numeric change and deformation stay separate.

Judge existing captured arrays independently; do not require a new framework. Before live use, minimal mutations of saved first-party snapshots should reject a missing/duplicated face, an equal-count swap of two faces between materials, lost small positive influence, wrong bone edge and modified shape delta. Reordered vertex/face arrays must retain successful correspondence. UV fallback must accept precisely the declared corner edit and detect an additional undeclared edit. These are a planned judge qualification, **not performed tests**. Source/output count equality is never sufficient. Inspect native Unity snapshots independently from export manifests. Record restored original ref, serialized snapshot only, regenerated analogous object, and absent state in distinct columns. Keep appearance evidence separate from reference evidence. Lost geometry fileID continuity alone does not fail geometry parity; report its native identity column independently.

Post-allocation r3: parent allocated runtime/project use, but selected environment lacks verified host RAM/full-process access and supported native UI tooling; see report. No loss-matrix cell changed to measured. This is an execution-access blocker, not evidence of VRM/VAPB data loss.
