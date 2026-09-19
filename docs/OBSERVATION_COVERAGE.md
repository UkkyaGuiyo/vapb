# Observation Coverage

## Available through the existing public probe

Prefab paths and identity, instantiated hierarchy, components, source/original
source links, renderers, mesh identity, material slots, and public prefab
property modifications are covered by `SemanticOracle.cs`.

The next human-run schema also records compact per-Prefab structural summaries
(Animator/Avatar validity, renderer and mesh counts, material slots,
blendshapes, bones, rootBone presence, and source identity counts) plus public
Material shader and texture-property references. This enables missing-texture
role analysis without treating an auxiliary texture as an optional structural
dependency.

## Planned case families

Model importer, FBX meshes/skinning/bones/blendshapes/humanoid, materials,
shader properties, textures/importer settings, animations/controllers/avatar
masks, constraints, LOD, MonoBehaviour/ScriptableObject/SerializeReference,
missing and unknown references, remaps/externalObjects, reimport stability,
and save/reopen round trips each require an explicit synthetic or human-run
case. A missing case is reported as uncovered, never inferred from a nearby
case.

Current real-corpus harvest state: `FIRST_SMOKE_COMPLETE_NEXT_CORPUS_PENDING`.
Unity 6 state: `UNAVAILABLE_OFFICIAL_MCP`.
