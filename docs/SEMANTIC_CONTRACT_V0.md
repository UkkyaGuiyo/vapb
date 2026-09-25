# VAPB Semantic Contract v0

## Purpose

Semantic Contract v0 separates a reusable Unity source Renderer identity from a
selected-root / instance-specific Renderer occurrence identity.

This is a contract and synthetic reference adapter only. It is not a production
import fix and is not wired into `EffectivePrefabResolver`, package import,
Blender realization, or export.

## Identity layers

### Source component identity

`SourceComponentKey` identifies the reusable serialized source component:

- `source_kind`
- `source_asset_guid`
- `renderer_file_id`

This key may be shared by multiple instantiated occurrences.

### Occurrence identity

`OccurrenceKey` identifies one use of the source component:

- `root_context_id`
- ordered `instance_edge_path`
- source `SourceComponentKey`

Two occurrences may share the same source key while remaining distinct because
their root context or instance-edge path differs.

Object names and display paths are not identity fields.

### Expected semantic relations

Each `RendererOccurrenceContract` carries:

- occurrence key;
- expected owner GameObject identity;
- expected mesh identity;
- material overrides scoped to slots;
- contract version `v0`.

Material override changes are values attached to an existing occurrence. They do
not mutate the occurrence key.

## Adapter contract

The Stage 1B synthetic adapter accepts:

1. explicit source Renderer relations;
2. one or more occurrence projection contexts.

For every non-ambiguous source relation and context, it emits one occurrence
contract. It must:

- preserve the source key;
- include the complete root context;
- preserve ordered nested/variant instance edges;
- emit distinct occurrence keys for distinct contexts;
- fail closed when one source key has conflicting owner/mesh relations;
- never use names or first-match selection.

The adapter is intentionally a small contract oracle. Production integration
requires a separately reviewed projection boundary.

## Invariants

1. Same source key does not imply same occurrence.
2. Different root context or instance-edge path implies different occurrence.
3. Material slot changes preserve occurrence identity.
4. Conflicting source relations are ambiguous, never automatically selected.
5. Owner and mesh identities remain explicit and independent.
6. Serialization contains identity data only and does not depend on object names.
7. Contract version is explicit and currently `v0`.

## Synthetic contract evidence

`tests/test_semantic_contract_v0.py` proves:

- one source Renderer projected into two root contexts yields two occurrences;
- nested instance-edge paths remain part of identity;
- material overrides do not mutate occurrence identity;
- conflicting source relations fail closed;
- serialized contract data contains identity fields and no name-based join.

The Stage 1A tests remain the evidence for the upstream limitation:
model-source lookup alone does not enumerate all model-child occurrences.

## Deliberately unresolved

Stage 1B does not decide:

- whether production correction belongs inside `EffectivePrefabResolver`;
- whether a separate occurrence projection layer is required;
- where model-child expansion and selected-root context are integrated;
- how Unity-generated ModelImporter local IDs are obtained in production;
- how the contract is persisted through Blender realization and Unity rebind.

Those are implementation decisions for a later stage after the contract boundary
is reviewed.

## Verification

- Stage 1B contract tests: 5 PASS
- Stage 1A synthetic tests: 5 PASS
- Production behavior changed: NO
- Commercial/private evidence included: NO

