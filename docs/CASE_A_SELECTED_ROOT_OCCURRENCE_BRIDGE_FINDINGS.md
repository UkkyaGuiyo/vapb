# CASE_A selected-root occurrence bridge findings

This is a public-safe, aggregate summary of a private Unity diagnostic run. No commercial asset payload, raw Unity Oracle output, GUID/fileID inventory, package, FBX, texture, or material file is included.

## Scope and result

The run observed exactly one connected Variant Prefab Instance root through Unity 2022.3 public Editor APIs. The selected root contained:

- 26 `SkinnedMeshRenderer` occurrences
- 41 ordered material slots
- 26 FBX-backed mesh references
- no nested Prefab chain observed in this run

The package-wide Effective replay contained 257 Renderer occurrences and 394 non-null material slots across multiple Prefab roots. Filtering by the selected root identity produced 4 Effective Renderers and 5 Effective slots.

This establishes two separate facts:

1. Package-wide versus selected-root scope explains most of the 257-versus-26 difference.
2. The remaining 26-versus-4 difference is a real unresolved Effective-side inheritance/expansion or root-representation gap. It must not be hidden by forcing the counts to match.

## Identity rules

The diagnostic model stores source identity and occurrence identity separately. A source Renderer identity identifies the source definition; a selected-root occurrence identity additionally includes the selected root and instance context. A raw FBX Model UID alone is not a valid occurrence identity because one source definition can be reused by multiple instances.

## Bridge results

- Selected-root Renderer joins: 4 exact, 0 ambiguous, 22 missing from the selected-root Effective set.
- Raw FBX graph joins: 26 exact.
- Frozen historical Edge A reattachments: 26 exact for the selected root; the remaining historical rows are outside this selected-root scope.
- Material comparisons are performed only after an exact Renderer join: 5 exact, 0 valid material mismatches, 2 slot-count mismatches.
- Material slots belonging to missing Renderer occurrences remain not comparable.

## Decision

The full occurrence bridge is `PARTIAL`, not proven. The next diagnostic action is one offline provenance matrix for the 22 missing source Renderer identities. For each, trace all package-wide Effective candidates and record root identity, source kind, occurrence path, Prefab chain, and omission reason. This distinguishes inherited model expansion omission from wrong-root representation without changing production behavior or requiring another Unity run.

No production importer behavior was changed by this investigation.
