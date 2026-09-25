# Export Identity Model

Status: design contract. Names are diagnostic labels only; they are never identity keys.

## Identity layers

| Layer | Stable key | Purpose |
|---|---|---|
| Source package | `source_package_id = sha256:<package-bytes>` | Separates packages even when filenames collide. |
| Source asset | `(source_package_id, unity_guid)`; path is a locator | Identifies a Unity asset entry. A path-only entry is explicitly weaker and must be scoped to the package. |
| Serialized object | `(source_package_id, source_asset_guid, signed_local_file_id)` | Identifies a serialized object or subasset in an asset. FileID alone is ambiguous. |
| Model subasset | `(source_package_id, model_asset_guid, signed_local_file_id, declared_type)` | Separates generated mesh/material/animation subassets from the FBX asset container. |
| Prefab source component | `(source_package_id, declaring_asset_guid, component_local_file_id, component_type)` | Identifies the renderer or component declaration in the source prefab/asset. |
| Prefab occurrence | `(containing_prefab_occurrence_id, source_component_identity, occurrence_path_token)` | Distinguishes repeated instances of one declaration. Occurrence path tokens are identity-bearing serialized relations, not display names. |
| Mesh resource | `model_subasset_identity` or source mesh identity | Keeps a shared mesh resource separate from each renderer occurrence that consumes it. |
| Blender realization | `(source_package_id, occurrence_id, realization_ordinal)` | Identifies the actual Blender object or material slot created for an occurrence. Blender names are only UI labels. |
| Export asset | `(export_namespace_id, export_guid)`; path is a locator | Identifies a staged output asset and its operation (`PRESERVE`, `MODIFY`, `CREATE`, etc.). |
| Unity post-import object | `(destination_namespace_id, import_observation_id, export_guid, observed_postimport_local_file_id, observed_type)` | Records what a specific Unity import observation created. It must not be assumed equal to source identity. |

## Required separation

The manifest must carry source, realization, and post-import identities simultaneously. A source Prefab renderer can therefore map to one or many prefab occurrences, each occurrence can map to one Blender object realization, and the exported asset can receive a new GUID/fileID while retaining a rebind task back to the source semantic identity.

## Synthetic example

Assume package `sha256:pkg-a` contains asset GUID `guid-model` at `Assets/Avatar/Body.fbx`. Unity observes mesh subasset fileID `-100` and material subasset fileID `-200`. A Prefab at `Assets/Avatar/Avatar.prefab` declares renderer component fileID `300` using mesh `-100`.

The same Prefab occurrence is instantiated twice. The declarations are the same, but the occurrence identities differ:

```text
source asset       = (pkg-a, guid-avatar-prefab)
renderer declaration = (pkg-a, guid-avatar-prefab, 300, SkinnedMeshRenderer)
occurrence 1       = (prefab-instance-1, declaration-300, relation-token-1)
occurrence 2       = (prefab-instance-2, declaration-300, relation-token-2)
mesh resource      = (pkg-a, guid-model, -100, Mesh)
realization 1      = (pkg-a, occurrence-1, ordinal-0)
realization 2      = (pkg-a, occurrence-2, ordinal-0)
```

If the export creates a new FBX, its Unity post-import mesh fileID is unknown until Unity observes it. The manifest must retain both the source mesh identity and the post-import mapping task, including destination namespace and observation ID; it must not match by object name.

## Manifest identity fields

Every exported semantic record should be able to reference:

- `source_package_id`, `source_asset_guid`, `source_asset_path`, `source_file_id`, and `source_component_type`;
- `occurrence_id` and `realization_id` where the record is occurrence-specific;
- `export_namespace_id`, `export_asset_guid`, `export_asset_path`, and `operation` for output;
- `destination_namespace_id`, `import_observation_id`, `unity_postimport_guid`, `unity_postimport_file_id`, and `postimport_status` only after observation;
- `ambiguity`, `unsupported_preserved_state`, and `rebind_tasks` when exact mapping is not proven.

## Fail-closed rules

1. A name match never resolves an identity.
2. FileID without its declaring asset is ambiguous.
3. Multiple providers or multiple post-import candidates remain unresolved.
4. A changed source asset cannot retain `PRESERVE` semantics.
5. Missing generated model identity becomes a recorded gate, not a guessed mapping.
