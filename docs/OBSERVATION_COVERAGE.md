# Observation Coverage

## Available through the existing public probe

Prefab paths and identity, instantiated hierarchy, components, source/original
source links, renderers, mesh identity, material slots, and public prefab
property modifications are covered by `SemanticOracle.cs`.

## Planned case families

Model importer, FBX meshes/skinning/bones/blendshapes/humanoid, materials,
shader properties, textures/importer settings, animations/controllers/avatar
masks, constraints, LOD, MonoBehaviour/ScriptableObject/SerializeReference,
missing and unknown references, remaps/externalObjects, reimport stability,
and save/reopen round trips each require an explicit synthetic or human-run
case. A missing case is reported as uncovered, never inferred from a nearby
case.

Current real-corpus harvest state: `WAITING_FOR_HUMAN_2022_3_RUN`.
Unity 6 state: `UNAVAILABLE_OFFICIAL_MCP`.
