# Export Unknown Matrix

Status: pre-production gate. This matrix is based on current source review and the canonical Unity Full Semantic Snapshot; it does not claim more than that evidence proves.

| Question | KNOWN | UNKNOWN | DERIVABLE_OFFLINE | REQUIRES_UNITY_OBSERVATION | BLOCKS_EXPORT_V1 | CAN_DEFER | Export V1 impact |
|---|---|---|---|---|---|---|---|
| 1. FBX subasset identity | Unity public observation can report generated subassets for a specific import. | Generated IDs cannot be proven from Blender FBX bytes/object names. | Source-side mesh/material references and rebind tasks. | Yes, for generated output identity. | Yes, exact generic model-backed V1. | Yes, with preserved source or a sidecar. | Requires sidecar or Finalizer before exact claims. |
| 2. Prefab reference survival | Source references can be recorded. | Import survival is not guaranteed by offline text alone. | Preservation candidate with original bytes, meta, and GUIDs. | Yes, to validate actual import resolution. | Yes for unverified regenerated model references; no for planning. | Yes for preserve-only milestone. | STRONGLY_SUPPORTED only under complete preservation conditions, never proven before Unity validation. |
| 3. Material patch safety | Typed source references are observable. | Arbitrary shader/property compatibility and third-party serialized behavior. | Only after typed patch grammar, supported property set, and reference checks. | Yes, for final compatibility. | Yes for unrestricted `MODIFY`. | Unsupported patches can defer or remain preserved. | `MODIFY` blocked until grammar and validation exist. |
| 4. Unity/VRC rebinding | Source identity and public source references. | Generated IDs and broad SDK compatibility. | Source rebind tasks and semantic maps. | Yes, for post-import identity and available public SDK validation. | Yes for automatic exact final validation of generated assets. | Yes for offline planning. | Finalizer covers Unity import/reference integrity plus available public SDK validation only. |
| 5. Offline Prefab generation | No verified offline Prefab-generation contract is established. | Full importer, generated-model, and third-party/VRC behavior. | Text-generation prototype/design capability only; not semantic compatibility. | Yes, for actual import validation. | Yes for release-quality generic V1. | Yes by deferring broad generation. | Do not claim generic compatibility from YAML alone. |

## Gate interpretation

The matrix does not justify another Unity run merely because the implementation is uncertain. The current canonical snapshot is sufficient for source-side planning for this captured dataset only; it is not proof that arbitrary future packages expose the same fields. A human Unity gate is required only if a later implementation reaches a fact that is both required for correctness and impossible to derive from the snapshot or public offline data.

## Minimum acceptable evidence for generated model export

One of the following must be present before claiming exact model-backed roundtrip:

1. a Unity-generated semantic sidecar that maps source occurrence identities to export asset/path/fileID identities; or
2. an explicit Unity Finalizer that imports the staged package, observes public identities, applies deterministic rebind tasks, and emits a validation report.

Until then, the exporter may plan, preserve unchanged source assets, emit unsupported-preserved-state warnings, and fail closed on unresolved references, but it must not silently synthesize a “correct” mapping.
