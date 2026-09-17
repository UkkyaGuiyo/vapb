# Private Corpus Survey v0.1 — public-safe summary

This document contains only anonymized aggregate results. Private package
names, paths, GUIDs, raw Oracle JSON, and extracted payloads are excluded.

## Metadata inventory

- packages: 23
- archive bytes: 2,114,991,089
- prefabs: 145
- FBX assets: 44
- materials: 365
- textures: 647
- packages with PrefabInstance: 19
- packages with direct renderer serialization: 15
- packages with material overrides: 7
- packages with custom shader references: 20
- GUID-evidence package groups: 7
- exact structural clusters: 10
- metadata-only elapsed time: 22.901 seconds

The scanner reads UnityPackage pathname entries and bounded textual metadata.
It does not decode texture or FBX payloads.

## Dominant structural patterns

- PrefabInstance + Model Prefab: 19 packages
- custom shader/material/texture topology: 20 packages
- MonoBehaviour documents: 18 packages
- SkinnedMeshRenderer: 14 packages
- material overrides: 7 packages
- material-provider-shaped packages: 4 packages
- geometry-provider-shaped packages: 3 packages

## Anonymous Oracle E2E coverage

Five representative groups passed public Unity API observation. Their aggregate
results were 22 prefabs, 3,495 object records, and 286/286 resolved property
modification targets. Two additional representative imports produced no Oracle
output within the diagnostic run and remain explicitly unresolved; they are not
treated as semantic failures.

## Fixture gaps

Future neutral fixtures should cover duplicate object names, multi-slot
material overrides, externalObjects remaps, multi-package ambiguity, nested
Prefab/Variant additions/removals, custom shader texture roles, and armature
bone mapping.

No Blender importer behavior was changed by the survey.
