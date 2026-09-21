# VAPB Stage 1A — Synthetic Occurrence Projection Findings

## Scope and safety

This document records a public-safe synthetic isolation run for the selected-root representation gap observed during Stage 0/0.5. It does not contain commercial asset data, real GUIDs/file IDs, raw Unity YAML, or private Oracle output. No production behavior was changed in Stage 1A.

The fixtures use neutral synthetic GUIDs and component IDs. Identity joins are performed with GUID/fileID values only; object names are not used for joins.

## Source of truth

- Current architecture: `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md`
- Stage 0 provenance closure: `docs/CASE_A.md`
- Stage 0.5 source-chain findings: `docs/CASE_A.md`
- Parser: `unity/prefab_parser.py`
- Effective projection: `unity/effective_prefab.py`
- Occurrence model: `unity/provenance_model.py`
- Synthetic tests: `tests/test_stage1a_synthetic_projection.py`

## Question

Which semantic condition causes a source Renderer occurrence to disappear from the selected-root Effective projection?

Stage 0/0.5 established a real selected-root representation gap. Stage 1A does not copy that asset or repeat its private counts. It isolates the semantic mechanisms with a smaller graph.

## Synthetic matrix

| Case | Independent variable | Source Renderer occurrences | Effective occurrences | Observed result |
| --- | --- | ---: | ---: | --- |
| A | Model source has three child Renderers; no Prefab renderer declaration or material override | 3 | 0 | Model index knowledge alone is not expanded into occurrences |
| A-control | Same model source; one, then all three source Renderers receive material overrides | 3 | 1, then 3 | Projection is driven by touched source component identities |
| B | Variant over a serialized base Prefab with three Renderers | 3 | 3 | Variant inheritance itself preserves the three serialized states |
| E | Nested source chain with serialized base and no extra override | 3 | 3 | Basic inherited chain preserves the serialized states |
| B/E identity control | Nested variant override addressed by immediate variant GUID | 3 inherited | 4 | A new state is created when target identity scope differs from inherited state scope |
| F | Same one-renderer override with two different synthetic material GUIDs | 3 | 1 in both runs | In this fixture, changing the tested GUID does not change the count |
| C/D | Same source component reused under two synthetic root/instance contexts | 1 source identity | not representable by `EffectivePrefabResolver` alone | `OccurrenceKey` distinguishes contexts, but resolver has no root-context input |

## Observed facts

### FACT A — model-child expansion is absent at this layer

`ModelSourceSemanticIndex` can contain three distinct model Renderer records, each with an independent Renderer file ID, owner GameObject ID, and mesh identity. Resolving an otherwise empty Prefab produces zero Effective Renderers. A single material override produces one Effective Renderer. Three overrides produce three.

This is a synthetic reproduction of a source-to-occurrence projection gap: the
Prefab explicitly references the model, but the index is only a lookup service,
not an enumerator that projects every model child into a selected Prefab
occurrence.

### FACT B — Variant inheritance is not sufficient by itself to explain the gap

When the source Prefab serializes three Renderer components, a variant with no additional Renderer declarations inherits all three. The same is true through the tested nested chain. Therefore “is a Variant” alone is not a sufficient explanation for a count reduction.

### FACT C — material GUID value is count-neutral, while override presence is not

The presence of a material override exposes the addressed Renderer: zero
overrides produces zero, while one override produces one. In this fixture,
changing between the two tested non-empty synthetic material GUIDs on that same
override leaves the Effective Renderer count unchanged. This is only a
fixture-local control result, not a conclusion about every real material path.

### FACT D — root context is outside the current EffectivePrefab API

`OccurrenceKey` correctly distinguishes the same source component under two different root/instance paths. `EffectivePrefabResolver.resolve()` accepts only `PrefabData`; it has no selected-root context or instance-edge path parameter. The current resolver therefore cannot, by itself, prove that a model source Renderer belongs to one selected root rather than another.

### FACT E — variant identity scope can create an extra state

In the nested synthetic control, inherited states retain the serialized base source GUID. An override addressed using the immediate variant GUID creates a separate state instead of replacing the inherited state. This is an identity scope boundary and is evidence for a variant projection risk, but it is not the same phenomenon as the model-child expansion gap.

## Classification of the independent variables

| Variable | Stage 1A result | Confidence | Meaning |
| --- | --- | --- | --- |
| A. FBX/model child expansion | **REPRODUCED PROJECTION LIMITATION at resolver boundary** | High for this API | Model records are not enumerated into occurrences unless an override exposes each component; real production contribution remains to be attached to the actual projection adapter |
| B. Prefab Variant | **NOT sufficient alone**; identity-scope risk observed | Medium | Serialized source states inherit correctly; variant-target identity can diverge |
| C. Same model reused under multiple roots | **Not representable in resolver alone** | High | Requires occurrence projection context |
| D. Selected root context | **Missing from current resolver contract** | High | Root attribution cannot be proven by `EffectivePrefabResolver` alone |
| E. Nested/inherited source chain | **Basic chain supported; target scope edge remains** | Medium | No-override chain preserves count; variant-target override can add a state |
| F. Material override | **GUID-value change is count-neutral in this fixture** | High for this fixture | The override exposes the addressed occurrence; changing only between the two tested material GUIDs does not change the count |

## Earliest proven boundary

The earliest proven boundary is between the explicit model-source relation and the Prefab occurrence projection. The system knows the three source Renderer records, but it does not create three selected-root occurrences from model children unless the serialized Prefab modifications mention them.

The synthetic evidence does not prove the exact mechanism of the real-asset gap by itself. In particular, the current test harness does not model a full Unity selected-root traversal or Unity ModelImporter generated local-ID graph. The remaining real-world question is how the production package import builds root/instance occurrence context before calling the Effective layer.

## Root cause status

**PARTIAL / MECHANISM NARROWED**

- Proven: model-source lookup is not model-child occurrence expansion.
- Proven for this fixture: changing between the two tested material GUID values
  does not change the count; the existence of an override is a current way the
  resolver learns an occurrence.
- Not proven: whether the real asset gap is caused only by this missing expansion, or by missing selected-root attribution layered on top.
- Observed risk: inherited and immediate variant source identities can be kept in different key scopes, producing an extra state rather than a replacement.

This supports the previous Stage 0.5 classification `VAPB_ROOT_ATTRIBUTION_GAP`
with medium confidence, while identifying a concrete synthetic projection
limitation. It does not yet prove that this limitation alone explains the real
asset gap.

## Semantic Contract v0 decision

**YES — proceed with contract design only.**

The contract should explicitly carry, for every Renderer occurrence:

1. selected root context ID;
2. instance-edge path, including nested and variant edges;
3. source asset kind and source asset GUID;
4. source Renderer file ID;
5. owner GameObject file ID;
6. mesh identity;
7. material override scope;
8. fail-closed ambiguity status.

**Production implementation remains HOLD.** The synthetic run narrows the minimal code path but does not yet justify changing production projection or variant normalization.

## Tests and verification

Passed:

- `python -m unittest tests.test_stage1a_synthetic_projection -v` — 5 tests (run with the repository parent on `PYTHONPATH`)
- `python -m unittest tests.test_prefab_parser tests.test_renderer_provenance_bridge -v` — 21 tests (same environment)
- `python -m compileall -q blender unity operators ui export tests`

The tests are synthetic and public-safe. No Unity GUI, commercial package, raw Oracle JSON, or real asset evidence was used or committed.

## Next action

The single most informative next experiment is a synthetic **occurrence projection adapter test** that supplies one model source graph under two distinct selected-root/instance-edge contexts and asserts that all model child Renderer records are emitted with distinct `OccurrenceKey` values while sharing the same source Renderer identity.

That adapter boundary is the smallest place where A (model-child expansion) and D/C (selected-root attribution and reuse) can be tested together without touching commercial assets or guessing a production fix.

## Production and repository state

- Production behavior changed: **NO**
- Commit/push: **not performed by Stage 1A in this run**
- Existing unrelated dirty worktree changes were preserved
- Private evidence committed: **NO**
