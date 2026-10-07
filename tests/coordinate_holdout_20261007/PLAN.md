# Independent coordinate holdout preparation

This is a bounded synthetic experiment, based on source commit `1a750b8148dba605947a9baa52cf8d4a743fd7ee`. The candidate below was inferred from all seven previous observations. Those observations are training evidence, never holdouts or expectations for these new inputs. The original 126-error UNPROVEN comparison remains unchanged.

## Preregistered hypotheses

Use column vectors with row-major matrix serialization. Freeze `C(x,y,z)=(-x,z,-y)` and `D=diag(-s,s,s,1)`, where `s` is the authored scene unit ratio relative to H0, never fitted from capture residuals or substituted from raw FBX metadata.

For each U-tagged corner, test:

```text
rV = V_Unity - D V_Blender
rW = W_Unity D - C W_Blender
rP = W_Unity V_Unity - C W_Blender V_Blender
```

All components must be finite, with absolute maximum at most `1e-4`. No fitting, basis search, sign search, per-case rebase, tolerance increase, aggregate averaging, or slot swap is permitted after observations. A failed residual rejects this candidate for that case; malformed or incomplete capture invalidates the evidence. The original comparator is not rewritten.

Independently compute `M=T Rz Ry Rx S` and authored world corners `Q=s M V_authored` by scalar arithmetic from the new constants. Predeclare the separate hypotheses `P_Blender=Q` and `P_Unity=C Q`, with the same component tolerance. These equations are predictions, not facts about importer behavior. Each receives its own verdict; cross-tool candidate agreement cannot hide an authored-world failure. H1 must additionally match H0 world points within each tool; H2 must match `0.1 H0`. These comparisons use new H0 only, not any old capture.

## Four unseen inputs

All inputs share six newly authored asymmetric triangles, eighteen unique vertices/corner U tags, and equal two-face logical material partitions. Exact geometry, export/import controls and versions are frozen in `contract.json` before export. U tags are exactly representable integers `100+8f+k`. All eighteen tags must occur exactly once; V remains diagnostic because importers may flip it.

| Case | Export up/forward | Unit ratio | Location | XYZ rotation degrees | Scale |
|---|---|---:|---|---|---|
| H0 fresh geometry | Y / -Z | 1 | 0,0,0 | 0,0,0 | 1,1,1 |
| H1 unused axis | X / -Y | 1 | 0,0,0 | 0,0,0 | 1,1,1 |
| H2 unused unit | Y / -Z | 0.1 | 0,0,0 | 0,0,0 | 1,1,1 |
| H3 compound reflected TRS | X / -Y | 0.1 | 1.375,-2.125,0.625 | 31,-19,47 | -1.25,0.6,1.8 |

Pin Blender 5.2.1 and Unity 2022.3.22f1, one mesh and one root. Require complete case sets, exact same-run FBX and manifest hashes, finite matrices/points, expected face/tag identities, and recorded effective importer settings. Raw FBX axis and unit metadata must match the declared inputs with a separately frozen metadata tolerance; no observed metadata changes the candidate unit ratio. Export timestamps may change FBX bytes across runs, so future consumers must use this run's actual hashes.

## Execution boundary

First create contract/oracle files and an exclusive-create preregistration receipt with UTC and hashes of the contract, authored oracle and executable sources. Then export into a new directory, record per-file hashes, capture Blender in a separate process, and run pure validation. Preserve every failed attempt under its original filename; use another filename or directory for retries. Never delete or overwrite an existing result. Non-Unity preparation passing is not runtime holdout validation.

No Unity process or Project is created in this preparation. The existing Unity probe hardcodes seven cases; a narrowly scoped four-case runtime adapter remains deferred. After VHS/FA/Two scheduling and resource alignment, review that adapter, pin its bytes, use the frozen fixtures/settings, capture all four cases once in an owned disposable Project, and apply the frozen gates. Additional captures, repairs, or candidate revisions require a new documented contract; never relabel a revised candidate's previously seen cases as independent holdouts.

Parent-child importer behavior, winding and normal transport remain unproven. Parent-child algebra tests do not replace actual hierarchy import evidence. A parent fixture would require changes beyond this minimal single-root preparation and is deferred.

## Separate material identity gate

Coordinate agreement establishes point-frame correspondence for these inputs. It cannot establish which external package Material GUID/fileID owns a native submesh or its faces: multiple material permutations preserve every coordinate and even equal per-slot face counts. Current fixture names/logical IDs/raw FBX Material UIDs are synthetic experiment keys, not a general package binding rule.

The separate gate needs exact package/source FBX revision hashes, raw serialized Prefab renderer occurrence and ordered external Material GUID/fileID references, actual imported renderer/mesh GUID/local IDs, each native submesh's triangle indices and vertices, and an independently justified bridge to tagged source/native face partitions. Verify per-GUID oriented triangle/corner partitions, including equal-count disjoint controls and ambiguity rejection. Empty `externalObjects` and the current witness without submesh geometry do not supply that bridge. No name/count/index fallback, fixed 0/2 swap, mandatory user Unity Project, or new product witness infrastructure is introduced here. Evidence collection through a test oracle does not change the direct `.unitypackage` product entry.

## Retained provenance limitation

The previous offline analysis's provisional report was deleted before its bytes/hash were retained. That original is missing and is not reconstructed or concealed. Its corrected report remains labeled exploratory, and all prior evidence is preserved. This preparation records new outputs and failures without overwriting them.

Design: GPT-6 Astra medium; design/code review: GPT-6.1 SOL medium; implementation: GPT-6 LUNA low. Failure Atlas's existing relevant lessons were consulted read-only; prior instructions keep Atlas updates/writes and new infrastructure stopped.
