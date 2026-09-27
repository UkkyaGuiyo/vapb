# Case B residual Material override: causal audit (2026-09-27)

Scope: one remaining `UNRESOLVED_OVERRIDE` (U) after the witness-assisted
Case B Import. This document contains only aggregate observations and synthetic
identities. Commercial assets, raw Unity output, GUIDs, local IDs, and machine
paths remain outside the repository.

## Result and authority boundary

**Classification D — `INERT_ONLY_KNOWN_VIA_UNITY`**, for the exact tested
revision and the expanded Renderer/Material state enumerated below. Keep U as
`UNRESOLVED_OVERRIDE` in production. Do not infer a safe target or delete the
serialized modification. This is a causal Unity Oracle result, not a new
package-only rule. No production or user-facing behavior changed.

| Phase | Disposable Unity 2022.3.22f1 input | Expanded result |
| --- | --- | --- |
| O | Original copied Prefab | 8 Prefabs, 107 Renderer occurrences |
| R | Remove only U; reimport | Same 107 Renderer rows and fields as O |
| I | Restore original Prefab bytes; reimport | Same 107 Renderer rows and fields as O and R; original Prefab revision restored |
| S | Set only U's object reference to a distinct synthetic Material; reimport | Same 107 Renderer rows and fields as O |
| P | Set one independently identified **active** direct override to that synthetic Material; reimport | Exactly one Renderer row changed, in `sharedMaterials` only |

All five batch runs completed successfully, with no C# compile errors. The
snapshot compared every enumerated Renderer occurrence's class, owner,
hierarchy/instance path, source and corresponding-source chains, all
`sharedMaterials` slots and Material identities, enabled/active state, and Mesh
identity. O–R, R–I, O–I, and O–S each had zero added, removed, or changed rows.
The positive control P demonstrates that this reimport and comparison detect
an active Material override. The disposable Prefab was restored to its original
bytes after the controls. The private original was not modified.

**Unity knows:** U does not alter any of those observed final fields for these
8 imported Prefabs at this revision. Its target appears in none of the 107
expanded Renderer source chains. S rules out the simple equal-final-Material
masking explanation. This does not assert noninterference with every Unity
property or every future revision.

**Package knows:** U is a serialized slot-0 Material modification under
Instance A, referencing the same model source asset as proven R1/R2. Its
Material provider exists. U's target is absent from the current projection and
from the accepted witness's Renderer rows. No serialized stripped-Renderer
alias from U to R1/R2 was found in the inspected Prefab chain. The witness is
scoped to its accepted model/Geometry mappings; it does **not** certify that
every possible Renderer identity has been enumerated. An unmatched target can
be active through a stripped alias in a different public synthetic case.
Consequently, these package facts do not prove that U is orphaned. The
package-only Import must keep the unresolved issue and avoid a guessed binding.

Anonymous chain inspected: containing Prefab → Instance A → model source → U
target. No stripped document or `m_CorrespondingSourceObject` edge completed a
chain from U to an active Renderer in the inspected serialized assets. Unity's
expanded source chains independently contained R1/R2 but not U. The absence of
an edge in the currently inspected package is evidence of uncertainty, not a
general proof that such an edge cannot exist.

## Hypothesis ledger

Each verdict concerns the exact tested revision and observed fields. “Rejected
in scope” does not mean universally impossible.

| Hypothesis | Necessary condition / falsifier | Smallest experiment and observation | Verdict and scope |
| --- | --- | --- | --- |
| H1 stale/deleted Renderer override | U must have targeted a former Renderer; historical identity would establish deletion | Inspect current source/alias chain; U target absent from final Renderer chains, but no deletion history was established | Plausible, **not proven** as historical cause |
| H2 Unity-ignored orphan | Removing or changing U leaves final state unchanged; a material difference falsifies it | O=R=I=S across 107 Renderer rows; P detects an active override | **Supported** for observed Renderer/Material state; package-only orphan proof absent |
| H3 stripped Renderer alias | A stripped component and corresponding-source chain must reach an active Renderer | Inspect serialized chain and all expanded Renderer source chains; no U chain found; O=R=I=S | **Rejected in scope** for this revision, not for other nested Prefabs |
| H4 Variant inheritance target | Inherited active Renderer must trace to U or change when U changes | Compare all 8 imported Prefabs and source chains across O/R/I/S; no U target or delta | **Rejected in scope** for enumerated Prefabs |
| H5 VAPB omitted an active Renderer | Unity enumeration must expose an active target absent from projection | Public API enumerated 107 Renderers; no U target in their chains and no causal delta | **Rejected in scope** for these imported Prefabs; witness completeness remains unproven |
| H6 equal-value override | A distinct U value must reveal a hidden active binding | S uses a distinct synthetic Material; O=S; positive control P changes one slot | **Rejected in scope** for observed slots |
| H7 indirect non-Renderer effect | Another final property must change when U changes | Full Renderer/owner/source/mesh/material snapshot is equal; unrelated Unity state was not exhaustively snapshotted | **Inconclusive** outside observed Renderer/Material scope |
| H8 malformed/unsupported serialization | Unity cannot consume the Prefab, or the target cannot be interpreted within supported evidence | Unity loads/reimports all five phases; provider and serialized modification exist, but package identity remains incomplete | Broken-file explanation **rejected in scope**; unsupported package-only identity remains possible |

The root cause of the **residual VAPB issue** is proven only to this extent:
current package/witness evidence does not identify U's active Renderer target or
prove its absence. The historical reason this serialized U exists is unknown.

## Public synthetic boundary

`tests/test_unrelated_model_override.py` models an unmatched target U beside
proven direct R1/R2 references. Remove/reinsert/order and a distinct synthetic
Material on U leave R1/R2 identity-bound dependencies unchanged while retaining
the unresolved issue; changing a proven direct target changes its dependency.
These are VAPB package-projection controls, **not** an independent Unity liveness
claim for the private U. `tests/unity_alias_oracle/` supplies the opposite
public Unity control: a stripped alias can make an unmatched target active.

Coverage relative to the requested synthetic matrix: S1 direct and S2 active
stripped alias have Unity and projection evidence in the existing alias Oracle;
S3 unmatched target and S4 separate instance have projection controls; S6
broken chain has a projection negative control only. A Unity-authored S3/S4/S5
matrix, including equal-base/override S5, has **not** been completed. No private
identifier was used to construct the synthetic tests.

The previously saved installed-ZIP Case B Import had 114/114 proven Object-slot
identity matches after save/reopen and re-resolution at the same production
HEAD; no fresh Import was required for this docs/test-only audit. The existing
Import result UI must continue to explain U as unresolved package identity;
it must not claim that every user's unmatched override is inert.
