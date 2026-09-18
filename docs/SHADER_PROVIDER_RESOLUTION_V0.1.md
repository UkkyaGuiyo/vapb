# Shader Provider Resolution v0.1

This research layer builds a metadata-first provider graph for UnityPackage
materials. It reads `pathname` records and Material YAML Shader GUID references
without extracting commercial payloads or copying shader source into the
repository.

## Classification

- `BUILTIN_SHADER`: the serialized Shader GUID is a known Unity built-in identity.
- `LOCAL_PROVIDER_FOUND`: exactly one provider asset is in the same package.
- `CORPUS_PROVIDER_FOUND`: exactly one provider asset is in another scanned package.
- `SHADER_REFERENCE_AMBIGUOUS`: multiple packages provide the same Shader GUID;
  automatic selection is intentionally refused.
- `EXTERNAL_PROVIDER_MISSING`: no provider asset is present in the scanned corpus.
- `SHADER_REFERENCE_MISSING`: the Material has no usable Shader GUID.

Static provider presence is not a successful Unity validation. A disposable Unity
probe must separately classify each provider as `VALID_SHADER`,
`PROVIDER_PRESENT_COMPILE_FAILED`, or `DEPENDENCY_BLOCKED`. Materials resolving
to `Hidden/InternalErrorShader` are quarantined and are not included in behavior
statistics.

## Boundary

This module is diagnostic infrastructure only. It does not change Blender import
or shader preview behavior. Real assets and raw shader payloads remain private;
public tests use synthetic archives and synthetic GUIDs.
