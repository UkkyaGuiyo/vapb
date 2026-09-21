# Selected-Root Occurrence Provenance Closure

This is a public-safe Stage 0 closure report. It records aggregate results only; it does not contain commercial asset payloads, raw Unity Oracle JSON, GUID/fileID lists, private absolute paths, or screenshots.

## Scope and decision

### OBSERVED FACT

The same-run Unity selected-avatar population contains 26 Renderer occurrences and 41 Material slots. The VAPB Effective graph for that selected-root scope contains 4 Renderer occurrences and 5 non-null slots. The raw FBX graph joins all 26 Unity source Renderer identities exactly. Comparable Material references have 0 valid mismatches.

### STAGE 0 RESULT

**PASS for diagnostic closure; HOLD for semantic freeze and production repair.**

All 26 Unity occurrences are now classified by a scoped source identity and a package-wide reverse lookup. There is no silent omission in the diagnostic result:

| Classification | Count | Meaning |
|---|---:|---|
| EXACT_EFFECTIVE_OCCURRENCE | 4 | Present under the selected Effective root |
| SELECTED_ROOT_REPRESENTATION_GAP | 22 | Absent under the selected root, but present under one or more other package-wide Effective roots |
| PACKAGE_WIDE_EFFECTIVE_ABSENCE | 0 | No selected occurrence is absent from the package-wide candidate set |
| AMBIGUOUS selected-root match | 0 | No selected-root row has multiple candidates under the selected root |

The 22-row classification is an observation about the current VAPB representation. It is not a claim that Unity itself parented those objects under the wrong Prefab.

## Provenance chain classification

Each selected occurrence was checked through these layers:

```text
Unity selected occurrence
  -> source FBX Renderer identity
  -> raw FBX Model/Geometry graph
  -> connected Prefab source observation
  -> selected-root Effective assignment
  -> package-wide Effective reverse lookup
```

### OBSERVED FACT

- Raw FBX join: **26 / 26 exact**.
- Source asset kind for the selected set: **FBX_MODEL**.
- Selected-root Effective assignment: **4 / 26**.
- The remaining **22 / 26** have package-wide Effective candidates under other roots.
- Other-root candidate multiplicity for those 22 rows: **1 row with 1**, **3 rows with 2**, and **18 rows with 3** candidates.
- The package-wide Effective population is 257 Renderer occurrences across 14 roots. It is not the selected-avatar population.
- Name-based resolution was not used in this classification.

### DERIVED

The direct evidence identifies the first missing selected-root stage as the **selected-root Effective assignment / occurrence projection**, not raw FBX reading. The current package-wide graph is able to emit the same source Renderer identities, but attaches the missing rows to other root evaluations.

### UNKNOWN

The existing snapshot does not capture Unity's complete Variant ancestry and does not provide a per-function runtime trace proving whether the underlying cause is:

- incomplete model-child occurrence expansion;
- root/instance attribution loss;
- Variant or inheritance projection loss; or
- another source-to-root mapping defect.

Therefore `SELECTED_ROOT_REPRESENTATION_GAP` is the safe Stage 0 classification. It must not be rewritten as `WRONG_UNITY_PARENT` without additional public Unity observation.

## Current VAPB code-path interpretation

The relevant offline path is:

```text
UnityPackageReader.build_index/extract
  -> parse_prefab
  -> ModelSourceSemanticIndex.from_prefabs
  -> EffectivePrefabResolver.resolve
  -> EffectivePrefab.renderers
```

The current resolver directly materializes renderer documents found in the parsed Prefab and follows explicit nested `m_SourcePrefab` relationships. It also applies serialized material-array modifications. It does not, by itself, expand every Renderer occurrence that Unity exposes after instantiating a connected FBX-backed Prefab. This explains why the current graph can contain a valid subset and can contain the same model-source identities under other package-wide roots, while still not proving the selected instance's full 26-row scope.

This is a code-path diagnosis, not a production change. No production code, schema, or runtime behavior was modified for Stage 0.

## Root attribution and collision findings

### OBSERVED FACT

- The 22 rows are not package-wide absent.
- They are not ambiguous under the selected root.
- The reverse lookup used the composite source asset identity plus source Renderer local identity; fileID alone was not used.
- The 22 rows are all emitted as model-source candidates under other Effective roots.

### DECISION

Classify the current defect as:

`SELECTED_ROOT_REPRESENTATION_GAP` — observed package-wide other-root attribution, with the deeper Unity Variant/parenting cause still unproven.

Do not implement a root reassignment or Variant fix during Stage 0.

## Semantic contract readiness

### DECISION

- Semantic Contract v0 design may proceed because every selected occurrence now has an explicit status and no row is silently discarded.
- Semantic freeze for the full selected avatar must remain **HOLD** until the 22 rows are represented as occurrence-aware selected-root records or explicitly proven to be outside the selected root by a public Unity observation.
- The current graph must not treat the package-wide 257 rows as a substitute for the selected-root 26 rows.
- No exporter implementation or generated identity assumption should be based on the 4-row subset alone.

## Required next experiment

The single most informative next experiment is a **public-API Unity selected-root occurrence export that records, for each of the 26 Renderer occurrences, the selected root's Prefab source object and complete `PrefabUtility` source/instance chain**. This directly distinguishes model-child expansion loss from root/Variant attribution loss without another specialized Oracle and without using object names as identity.

Until that observation exists, the minimum safe implementation target is an occurrence-aware Effective projection keyed by scoped source identity and root context, with `PRESENT`, `REPRESENTATION_GAP`, `AMBIGUOUS`, and `UNRESOLVED` states preserved explicitly.

## Verification and privacy

The private machine-readable matrix is retained outside the repository for local diagnostics. It contains real asset identity and is intentionally not committed. This repository document contains only aggregate counts and sanitized conclusions.

Stage 0 did not commit production code, did not create a ZIP, did not run a Unity mutation, and did not perform any power/session action.
