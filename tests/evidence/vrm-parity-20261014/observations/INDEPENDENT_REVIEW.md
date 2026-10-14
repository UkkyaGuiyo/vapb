# Independent G1 saved-array review

2026-10-14. Read-only data judgment by the separately configured GPT-6.1 SOL / medium reviewer, followed by this authorized review-file write. Scope: the first-party generic-rig Blender/glTF preliminary observation, not UnityPackage V0, SoulFlame R0, Humanoid eligibility or Unity restoration. No overall PASS. No runtime applications, hardware queries, exporter algorithms or generator/driver imports were used for this judgment.

Evidence: `gltf-observation.json`, `gltf-header.json`, `authoring.json`, `reopened.json` and `root-primary-geometry-check.json` in this directory; original GLB and snapshots under repository-relative `runtime/gltf-001` and `runtime/fixture-001`. The public observation equals the original runtime observation. Independently computed source Blend and GLB hashes match the observation: source Blend SHA256 `45b4bed62faac7b914615cff6f10e91d38339262b04c433c5222b8b4be22b912`; GLB SHA256 `3ba1d9e507ba31cf2be79e2d602d9a5f09d4700b4d5653d1c32e1690d41202b3`.

## Corrected whole-scene boundary

The initial analysis selected `after.meshes[0]` without checking the complete inventory. That selection was too narrow and did not establish whole-scene parity. The corrected selection scans every returned mesh and requires its entire unique UV-face multiset to equal the source multiset. Exactly one returned mesh satisfies this criterion. Its diagnostic name and ordinal do not participate in selection.

| Returned entity | Vertices | Faces | Source UV-face matches | Observation |
| --- | --- | --- | --- | --- |
| Uniquely UV-corresponded mesh | 36 | 12 | 12 | Complete source face/corner correspondence |
| Additional mesh, diagnostic name `Icosphere` | 42 | 80 | 0 | Extra captured mesh; unclassified |

The raw GLB has one mesh with three primitives containing 2/4/6 triangles. The second captured mesh is therefore consistent with an importer-generated additional entity, but its actual provenance, ownership, visibility, custom-shape reference and rendered/helper role were not captured. Its name cannot establish those properties. No whole-scene mesh/hierarchy PASS follows, and it must not be discarded silently.

## Quantitative observations on the uniquely corresponded mesh

| Channel | Observed result | Limit |
| --- | --- | --- |
| UV faces/corners | 12 unique exact face signatures, 36 matched corners; all 12 face orientations agree | Explicitly excludes the additional mesh |
| Positions | Zero changed world-position corners; maximum component difference 0 | 8 source vertices become 36 return vertices; counts alone are not loss |
| Normals | Zero changed corner normals | Recorded source/return object matrices are both identity, so the captured frames agree |
| Tangents | Zero changed corner tangent vectors or handedness signs | The observer recalculates tangents; imported tangent retention remains NOT_MEASURED |
| Shapes | Two unique complete world-delta patterns match exactly; zero changed matched corner deltas | Matched by patterns, not cross-format names; returned shape defaults were not captured |
| Face partitions | The same UV faces remain in the three 2/4/6 partition groups | Diagnostic partition correspondence, not original Unity Material identity |
| Diagnostic colors | Three distinct source material RGBA values become identical gray `[0.800000011920929, 0.800000011920929, 0.800000011920929, 1]` | The GLB already has those gray base-color factors, locating this observed diagnostic difference at/before export; no universal glTF or Unity shader-loss claim |
| Bones | Three exact unique joint-head anchors plus uniquely distinguishing child topology map all 18 captured bones; all parent edges agree | Names resolve links within each snapshot only; they are not cross-format identities |
| Bone head numerics | 15/18 joint heads differ; maximum component difference `3.0547380447387695e-7` metres | No tolerance, harmlessness or owner acceptance inferred |
| Bone frame numerics | 18/18 rest matrices differ; maximum component difference `4.172325134277344e-7` | Raw frame difference is distinct from semantic deformation loss |
| Weights | Structurally bone-mapped raw weights agree at all 36 matched corners, totaling 72 positive corner influences, including tiny values | Modifier/armature ownership and actual skin binding were not captured; semantic skin PASS is unavailable |

The common captured authoring/reopened fields are equal: vertices, faces, UVs, face materials, weights, bone rest data, shape arrays and Blender version. This is bounded source save/reopen evidence, not a Unity restoration result.

## Mutation qualification

Pure standard-library analysis used copied in-memory snapshots only. No files were mutated.

| Mutation/control | Result |
| --- | --- |
| Reverse face-array order and cyclically reorder each face's corners | All 12 joins remain valid and preserve orientation |
| Remove one face | Reject `FACE_MULTISET_MISMATCH` |
| Duplicate one UV face | Reject duplicate signature |
| Swap two faces between material groups while keeping group counts unchanged | Correspondence survives; exactly two changed face memberships are exposed |
| Add an extra position change of 0.03125 to one copied corner component | Correspondence survives; exactly one changed corner is exposed |
| Add an extra shape-delta change of 0.03125 to one copied corner component | Correspondence survives; exactly one changed corner is exposed |

These qualify this narrow UV correspondence and changed-array observation, not the unimplemented full ABC, edited-UV, skin-binding or Unity restoration judges. A detected slot change is a diagnostic observation, not proof of original Unity Material identity.

## Reproduction recipe

Use Python's standard-library `json`, `collections`, `struct` and `hashlib`; do not import the fixture generator, observer driver or product modules.

1. Load `gltf-observation.json`. For each triangle, form a face key from the sorted three exact UV pairs. Reject repeated face keys and repeated UV corners. Scan all returned meshes and select only a unique complete source face-key multiset match; separately report every unmatched entity.
2. Join each source face to its returned face by that key. Join corners by their exact UV pair. Compute the corner permutation: `[0,1,2]`, `[1,2,0]` and `[2,0,1]` preserve orientation; the other permutations reverse it. Compare all joined world positions and other captured arrays without a tolerance. Compare partition membership as sets of immutable face keys, independently of slot labels.
3. For each shape channel, flatten its ordered world-delta vectors across the joined source corners. Match complete unique patterns across snapshots. Require a unique match; labels alone cannot resolve a channel.
4. Resolve each captured bone's parent link within its own snapshot, where diagnostic names are unique. Anchor the three unique exactly equal world heads. Recursively form each node's unordered child-subtree signature. Under already matched parents, match only uniquely distinguishing unmatched child signatures. This fixture's extra child makes the arm branches distinguishable. Verify the resulting mapping is bijective and every mapped parent edge agrees. Compare mapped head and rest-matrix values exactly. Use that structural map to relabel weight-group observations; leave missing actual modifier/skin ownership unresolved.
5. Repeat the tabled mutations on deep copies. A cyclic corner rotation is the positive reorder control. For the equal-count material control, exchange membership of one face from each of two groups. Measure the changed set separately from correspondence validity.
6. Read the GLB's 12-byte header, then its JSON chunk using `struct` and `json`; confirm its declared length/version and inspect material factors, primitive index counts and skin joint counts. This inspects first-party serialized output, not exporter implementation. Independently hash the original GLB and source Blend where available.

## Public safety and remaining scope

Reviewed all five public JSON files listed above, the newly authored source files in the fixture directory, and the new external-shader, Unity-preservation and format-assessment documents. Recursive JSON string inspection and text checks found no private absolute paths, credentials, personal host identifiers or raw runtime logs in this packet. Diagnostic first-party entity names, array data, public upstream URLs, artifact hashes and explicit unresolved scopes are suitable for public evidence. No private runtime logs or host resource inventories are included in this review.

Unresolved: the extra mesh's role/ownership/visibility; actual skin modifier and armature binding; returned shape defaults; retained imported tangents; expected representation and acceptance of changed bone frames; complete material semantics; Humanoid eligibility; Unity source/restore state; V0/R0 and owner UX. No full-route PASS, LOSSY_ACCEPTABLE, product migration or algorithm-analysis gate is established by this preliminary observation.
