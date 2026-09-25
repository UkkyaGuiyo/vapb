# Export Research Corrections

Status: pre-production research. `EXPORT_ARCHITECTURE = READY` after SOL architecture review.

This document corrects the confidence level of export assumptions. It is a design boundary, not an implementation claim.

## Evidence classes

| Class | Meaning in this project |
|---|---|
| OFFICIAL/PUBLIC | Behavior exposed by documented Unity or Blender public APIs, or a format contract that is directly documented by the owner. |
| EMPIRICAL | Observed in the current local Unity 2022.3 Oracle or Blender 5.2.1 runs. It is evidence, not a universal guarantee. |
| STRONGLY SUPPORTED | Follows from multiple empirical observations and source code, but still needs a compatibility gate before being treated as a product guarantee. |
| HEURISTIC | A useful fallback or approximation that must never silently replace an exact identity. |
| UNKNOWN | Not established by the available public observation or offline source data. |

## Corrected claims

### UnityPackage container layout

The current importer and local packages empirically use a gzip-compressed tar layout with GUID directories containing `asset`, `asset.meta` where present, and `pathname`. This is **EMPIRICAL**, not a claim that every UnityPackage producer emits exactly the same optional members. An exporter must write deterministic members, reject path traversal, and fail on collisions rather than silently overwrite.

### GUID, path, and local file identifiers

Unity GUID/path lookup and public APIs such as `AssetDatabase` and `TryGetGUIDAndLocalFileIdentifier` are **OFFICIAL/PUBLIC** interfaces when used inside a supported Unity Editor version. The current Oracle also **EMPIRICALLY** captured asset GUIDs, paths, serialized object references, and renderer declarations. A GUID is the primary asset identity within a package namespace; a path is a diagnostic locator and is not a substitute for a GUID.

A local fileID is an identity component for a serialized object, but the exporter must not claim that a fileID generated after reimport will remain equal to the source fileID. Generated model subassets are specifically **UNKNOWN** offline and must be represented by an explicit source-to-post-import map or a finalizer observation.

### FBX subassets

An FBX byte stream and Blender's imported object names do not, by themselves, prove Unity's generated model subasset localFileIDs. The current Unity snapshot demonstrates that model assets expose generated subassets; the current Blender audit demonstrates that the imported scene does not retain every authoritative Unity renderer/owner localFileID. Therefore “export FBX and reuse the old model fileIDs” is an unsupported assumption and is corrected to **UNKNOWN / EXPORT V1 BLOCKER for exact model-backed roundtrip** unless a semantic sidecar or Unity finalizer supplies the map.

### Blender FBX settings

The current FBX operator options are an implementation preset chosen for the importer’s current needs. They are not proof of Unity identity preservation, VRC compatibility, or visual equivalence. Export settings must be explicit, version-tested, and recorded in the manifest; arbitrary settings and undocumented defaults are not acceptable.

### Raw preservation and patching

Preserving an unchanged source asset is stronger than regenerating it, but “same GUID” alone does not prove that changed bytes are safe to substitute. `PRESERVE` requires source bytes and metadata to remain unchanged. `MODIFY` requires a typed patch record and validation of references; unsupported serialized state must be preserved or reported, never silently dropped.

### Unity Finalizer

An explicit Unity Finalizer is an architecture option for public-API observation and rebinding. It is not proven necessary for every export, and it must not be used to hide an incomplete offline manifest. It is required only where offline data cannot establish generated post-import identity or public compatibility.

### Unity/VRC compatibility

Unity Editor public APIs can observe imported assets and public component state. They do not make arbitrary third-party serialized components safe to synthesize offline. VRC/SDK compatibility is therefore a per-component contract with `UNSUPPORTED` and `PRESERVE` paths, not a promise that a generic YAML writer can reproduce all behavior.

## Consequence

The first implementation milestone is a typed manifest/reachability planner and deterministic staging design. A release-quality package writer and automatic finalizer remain gated until SOL accepts the identity and unknown matrix.
