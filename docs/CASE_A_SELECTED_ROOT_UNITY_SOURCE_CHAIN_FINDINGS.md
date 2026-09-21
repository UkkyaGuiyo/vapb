# Selected-Root Unity Source Chain Findings

This is a public-safe Stage 0.5 report. It contains aggregate results only. Private JSONL, real asset GUID/local-file-ID tables, commercial asset payloads, and screenshots are not included.

## Status

**Stage 0.5 observation: COMPLETE.**

The Unity human gate was completed with the selected completed avatar root preserved. The observation used Unity 2022.3 documented public Editor APIs and performed read-only enumeration.

## Unity selected-root source-chain counts

| Observation | Count |
|---|---:|
| Selected-root Renderer occurrences | 26 |
| Material slots | 41 |
| Immediate Prefab source resolved | 26 / 26 |
| Original source resolved | 26 / 26 |
| FBX model asset resolved | 26 / 26 |
| Connected Prefab instance | 26 / 26 |
| Prefab asset type reported as Variant | 26 / 26 |
| Renderer source-chain depth | 3 for 26 / 26 |
| Unity Console errors during capture | 0 |

The three observed source-chain levels are:

```text
Scene Renderer occurrence
  -> selected Prefab source Renderer
  -> original FBX Model Renderer
```

This is a source/instance identity chain. It does not use object names or hierarchy paths as an identity key.

## Chain classification

| Classification | Count | Interpretation |
|---|---:|---|
| UNITY_CHAIN_CONFIRMS_VARIANT_CHAIN | 26 | All rows are connected instances whose source is a Variant Prefab and whose original source is an FBX Renderer |
| UNITY_CHAIN_CONFIRMS_SELECTED_ROOT | 0 | No row lacked the Variant/model evidence needed for the stronger classification |
| UNITY_CHAIN_INDICATES_DIFFERENT_ROOT_CONTEXT | 0 | The selected root context is the same for all 26 rows |
| UNITY_CHAIN_AMBIGUOUS | 0 | No source-chain row had competing public-API chains |
| UNITY_CHAIN_UNAVAILABLE | 0 | No required chain step was unavailable |

The exact Unity Variant ancestry depth beyond the observed selected Prefab source and original FBX source was **not captured**. `Variant` here is the public `PrefabAssetType` observation, not a claim that every historical inheritance edge was enumerated.

## Identity join with Stage 0

The Stage 0 private matrix was joined using the original source asset identity plus original source Renderer local identity and selected-root context. Names and display paths were not used for the join.

| Stage 0 result | Count |
|---|---:|
| EXACT_EFFECTIVE_OCCURRENCE under selected root | 4 |
| SELECTED_ROOT_REPRESENTATION_GAP | 22 |
| Package-wide Effective absence | 0 |
| Selected-root ambiguity | 0 |

The 22 gap rows all have the same Unity source-chain pattern as the 4 exact rows. They are present as package-wide Effective candidates under other roots, but not under the selected-root Effective assignment.

## 26 -> 4 causal boundary

The count transition is:

```text
Unity selected-root Renderer population       26
  -> immediate Prefab source                   26
  -> original FBX source                       26
  -> FBX model asset                            26
  -> VAPB selected-root Effective occurrence     4
  -> representation gap                        22
```

### PROVEN

The loss boundary is after the Unity source/original/model chain and at the VAPB selected-root Effective occurrence projection. This is not a raw FBX source-read failure, not a missing Unity source chain, and not a valid Material-value mismatch.

The current VAPB Effective rows for this scope are model-source records with incomplete model-child provenance (`UNKNOWN_MODEL_SOURCE` evidence and no complete owner/mesh occurrence identity). The package-wide replay can emit the same source identities under other root evaluations.

## Classification of the 22 gaps

### Final classification after Sol review

All 22 are classified as:

`VAPB_ROOT_ATTRIBUTION_GAP`

Confidence: **MEDIUM**. This is the strongest evidence-backed classification, not a claim that Unity parented the objects incorrectly.

### Mechanism assessment

`SELECTED_ROOT_ATTRIBUTION_MISMATCH_MODEL_CHILD_AND_VARIANT_MECHANISM_UNRESOLVED`

This means:

- **Model-child expansion gap: possible, not isolated.** Unity proves that all 26 selected occurrences are FBX-backed child Renderer occurrences, while VAPB emits only 4 under the selected Effective root. This establishes the symptom but not the implementation-level mechanism.
- **Variant projection gap: possible, not isolated.** All 26 Unity rows are Variant-backed, but the 4 exact rows have the same chain as the 22 gaps. The chain alone cannot prove that Variant handling is the differentiator.
- **Root attribution gap: strongest supported classification.** The 22 rows are not absent package-wide; they are emitted under other package-wide root evaluations. The strongest interpretation is that VAPB has a selected-root attribution mismatch. This does not prove incorrect Unity parenting.
- **Occurrence projection gap: symptom boundary.** The selected Unity occurrence set is not projected one-for-one into the selected-root Effective set.

The evidence does not justify implementing a Variant-only fix, model-child-only fix, or automatic root reassignment fix. The safe next step is to contractually preserve root attribution and keep the mechanism unresolved.

## Semantic Contract v0 decision

**YES for contract design; NO for full semantic freeze.**

The contract may now define explicit occurrence states, because all 26 rows have a public-API source chain and the 22 non-matches are no longer silent omissions. The full selected-root freeze must remain on hold until the 22 rows are represented under the correct occurrence context or explicitly proven outside that context.

Required state vocabulary includes at least:

- `EXACT_EFFECTIVE_OCCURRENCE`
- `SELECTED_ROOT_REPRESENTATION_GAP`
- `AMBIGUOUS`
- `UNRESOLVED`
- `UNSUPPORTED`

## Accepted and rejected hypotheses

### Accepted / supported

- The VAPB loss is downstream of Unity source-chain resolution.
- The current Effective graph is not occurrence-complete for the selected root.
- The strongest current classification is a VAPB selected-root attribution mismatch.

### Rejected by this evidence

- Raw FBX source graph corruption as the explanation for the 22 rows.
- Selected-root Unity parenting error.
- Name-based identity collision as the explanation.
- Material value mismatch as the explanation.

### Still unknown

- Whether the production correction needs complete FBX model-child enumeration, a Variant-aware occurrence projection layer, or both.
- The complete Unity Variant inheritance edge set beyond the observed source chain.
- Whether each of the 22 rows has a distinct Unity PrefabInstance modification path that must be preserved.

## Production and privacy status

- Production VAPB behavior changed: **NO**.
- Unity mutation, asset mutation, reimport, save, Apply/Revert: **NO**.
- Private evidence committed: **NO**.
- ZIP generation: **NOT REQUIRED**.
- Power action: **NONE**.

## Next action

Implement no fix yet. The next single action is to add a synthetic occurrence-aware fixture that reproduces a Variant-backed FBX model with repeated child Renderer occurrences, then make the Effective projection preserve the selected-root context and explicit gap states before touching real-asset behavior.
