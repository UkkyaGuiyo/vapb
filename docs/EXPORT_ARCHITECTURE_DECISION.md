# Export Architecture Decision

Status: `EXPORT_ARCHITECTURE = READY` after SOL architecture review.

## 2026-09-28 product-model update

The current product authority is [VAPB Core Product Model — 2026-09-28](VAPB_CORE_PRODUCT_MODEL_20260928.md). The HYBRID architecture remains useful, but **source geometry identity continuity is no longer a normal export requirement**. Source identities remain import provenance and restoration evidence. Regenerated Blender-authored geometry may receive new export/post-import identities; the Finalizer uses VAPB Export IDs and the recipe to attach preserved Unity semantics to the current output structure. Raw-preserve remains preferred for unchanged reusable Unity assets such as Materials/Textures where appropriate, not as a requirement to preserve source Mesh lineage.

## Decision context

The importer already stores package-scoped and source-scoped identity metadata, but it does not yet provide a deterministic UnityPackage repacker. The canonical Unity snapshot closes the source-side renderer/material records for the captured CASE_A dataset (311 renderer occurrences and 490 ordered slots); it is not a general proof for arbitrary packages. The Blender audit proves that generated Unity model localIDs are not all retained by Blender. Export must therefore distinguish source preservation from regenerated output.

## Options

| Option | Fidelity | Identity safety | Unity/VRC compatibility | Observability/recovery | Complexity | Decision |
|---|---|---|---|---|---|---|
| PURE OFFLINE | Good only for unchanged/source-backed assets | Weak for generated model subassets | Cannot prove importer/SDK rebinding | Strong deterministic logs, poor post-import truth | Lower initially, high risk later | Reject as sole architecture |
| RAW PRESERVE + PATCH | Strong for unchanged assets and typed patches | Strong when GUID/path/bytes are preserved; fail closed on unsupported edits | Good for preserved source state, bounded for patches | High; every operation can be recorded | Moderate | Required offline foundation |
| UNITY FINALIZER | Highest post-import observability | Can observe generated identities through public APIs | Unity import/reference integrity plus available public SDK validation; not a general VRC guarantee | Strong validation, requires Unity environment | Higher operational cost | Explicit optional boundary |
| HYBRID | Preserves source fidelity and handles generated gaps explicitly | Strong with sidecar/rebind tasks and fail-closed ambiguity | Best practical balance | Strong offline manifest plus Unity validation | Moderate/high but bounded | Recommended |

## Recommended architecture: HYBRID

1. **Offline semantic planner:** consume the imported scene and source identity registry; compute typed reachability from selected export roots; preserve all meaningful dependencies and record unsupported state.
2. **Identity-aware manifest:** emit source identities, occurrence-aware renderer/material/texture mappings, export operations, collision results, and post-import rebind tasks.
3. **Raw-preserve/patch staging:** copy unchanged source-backed assets exactly; apply only typed, validated modifications; reject collisions and ambiguous references.
4. **Deterministic package writer:** later write a reproducible gzip tar UnityPackage with required `asset`, `asset.meta`, and `pathname` members; a preview is optional. Ordering, metadata, and hashes must be deterministic; no silent overwrite.
5. **Explicit Finalizer:** later provide `Tools > VAPB > Finalize Export` as an idempotent Unity public-API action for generated model identity observation, rebind, and validation of Unity import/reference integrity plus available public SDK validation. No network, credentials, shell, reflection, or private API.

## Manifest boundary

The future manifest must include at least:

`schema_version`, `source_packages`, `source_assets`, `export_assets`, `export_namespace_id`, `mesh_mappings`, `renderer_occurrences`, `material_mappings`, `texture_mappings`, `bone_identity_map`, `shape_key_map`, `prefab_source_chains`, `component_provenance`, `reference_rebind_tasks`, `unity_postimport_identity_map`, `destination_namespace_id`, `import_observation_id`, `external_dependencies`, `unsupported_preserved_state`, `warnings`, and `errors`.

Each export asset records one operation: `PRESERVE`, `MODIFY`, `CREATE`, `DELETE`, `DUPLICATE`, `SPLIT`, or `MERGE`, plus the expected Unity importer type. `DELETE` is a manifest/Finalizer operation; omission from a UnityPackage does not itself delete an existing project asset. Reachability is typed and occurrence-aware; unused Blender datablocks are not destructively pruned merely because they are outside one export set.

## Blender export boundary

FBX export is allowed only through Blender 5.x public capabilities with a named, version-tested preset. The preset must be recorded in the manifest and must not imply Unity identity survival. Embedded textures, modifier application, animation baking, leaf bones, path mode, and selection scope are explicit policy fields, not hidden defaults.

The later UnityPackage writer contract requires `asset`, `asset.meta`, and `pathname` members for each staged asset; a preview is optional. If safe metadata cannot be written, staging must fail or use an explicitly approved preserve path rather than silently emitting an incomplete entry.

## Security and recovery

- Reject absolute paths, traversal, NULs, duplicate output identities, and archive collisions.
- Do not execute source package content or arbitrary component code.
- Preserve unknown serialized state when possible; otherwise record it in `unsupported_preserved_state` and stop before claiming exact export.
- Make every staging run isolated and reproducible; never mutate the source package.

## Implementation gate

No production exporter writer, UnityPackage release artifact, commit, push, or ZIP is authorized by this document. Source-side semantic capture and post-import identity observation are separate artifacts. Generated model export additionally requires a post-import sidecar produced after Unity imports the exact staged output; it must bind output asset hash, importer settings, Unity version, and observation ID. A source-side sidecar alone is insufficient. Production implementation begins only after SOL changes the status to `EXPORT_ARCHITECTURE = READY` and the unknown matrix has an explicit treatment for generated model identity.
