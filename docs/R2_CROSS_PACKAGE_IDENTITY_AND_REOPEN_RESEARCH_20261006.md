# R2 Cross-Package Identity and Reopen Research Note

Date: 2026-10-06

Project: VAPB
Repository: https://github.com/UkkyaGuiyo/vapb
Branch: `feature/r2-material-slot-reorder`
Inspected source: `7057cbd1658375084ba0111a75b3c715e6b394db`
Scope: public synthetic Blender package imports and read-only source inspection

This is an engineering research note, not a product contract or a claim of general Avatar compatibility. It separates what the inspected code appears to do from what the synthetic runs demonstrate.

## Evidence sources

1. `tests/blender_cross_package_dependency_test.py`, tested at the source content committed as `7057cbd`. Blender 5.2.1 completed the script with `CROSS_PACKAGE_DEPENDENCY_OK` (exit 0). Local run log SHA-256: `17fbdfc8f60ccaaab88d785d2a0247efbaa7d61c40042b9e1bef704dc76136f3`.
2. [`R2_SYNTHETIC_BLENDER_IMPORT_REOPEN_QA_20261006.md`](R2_SYNTHETIC_BLENDER_IMPORT_REOPEN_QA_20261006.md), a separate two-process Nested Prefab create/reopen run on source snapshot `9dc810387880194a4ade36516e3125ba1a24162c`.
3. Read-only inspection of identity, dependency, receipt, and binding paths at `7057cbd`. Code inspection is a hypothesis source; it is not runtime proof for cases omitted by the fixtures.

The CPD log and disposable `.blend` outputs remain local and are not published. No Unity Editor, VRChat SDK, purchased asset, or user project was involved.

## Working identity model inferred from the code

The current implementation suggests three checks that should remain distinct:

1. **Reference validity:** retain the raw package reference and classify it as valid, explicit null, malformed, or ambiguous. Do not convert malformed or ambiguous explicit references into a name lookup.
2. **Provider identity:** identify the candidate asset with its package, GUID, optional fileID, and provider type. Prefer a unique local provider; otherwise use a unique cross-package provider. Refuse multiple candidates instead of choosing by enumeration order.
3. **Consumer binding:** identify the exact consumer occurrence and target (for example, Prefab occurrence plus renderer slot) and validate a receipt before mutating it. Provider discovery by itself is not proof that a particular consumer was bound.

The inspected paths are consistent with this model: `AssetIdentity` combines package and GUID, optionally fileID, and uses a path fallback only when GUID is absent; provider selection distinguishes unique local and cross-package candidates; explicit material mappings filter by GUID/fileID and provider type; and Prefab material binding carries occurrence/slot receipt data. These are source observations at the listed SHA, not an approved universal specification.

## What the synthetic CPD run demonstrated

At the tested source content, one generated geometry package and separate appearance and texture packages were exercised in grouped import and in geometry-first/provider-first orders. The test asserted:

- grouped sibling discovery completed across three synthetic packages;
- the cross-package Material and texture were resolved and the witnessed Prefab renderer slot reported `BOUND`;
- repeating dependency resolution preserved the tested result;
- the geometry-first and provider-first `.blend` results passed their reopen checks using `bpy.ops.wm.open_mainfile` in the same Blender process.

The test uses a synthetic in-memory `ModelWitnessIndex`; this is not a Unity-generated witness or validation of public sidecar transport. This supports order independence for these fixtures and code paths. It does not establish order independence for duplicate providers, malformed mappings, multiple consumers, multiple renderer slots, or arbitrary package sets.

## Texture boundary and unresolved questions

Material resolution has explicit asset/provider identity checks. Texture resolution appears narrower: the inspected YAML texture target may have an empty fileID, fileID is retained separately in a texture reference, and the current bind path can select a consumer Material by GUID/package. The current fixture proves one synthetic texture binding and save/reopen path. It does not prove correct selection when multiple Blender Material datablocks carry the same consumer GUID/package, when subassets share an asset file, or when multiple package copies compete.

Before generalizing the behavior, add focused synthetic cases for duplicate local providers, duplicate cross-package providers, explicit null versus malformed references, multiple Material datablocks with the same consumer GUID/package referencing one texture GUID, same-GUID subassets with distinct fileIDs, and two renderer occurrences with different slot states. Each should assert provider choice, consumer receipt, slot/image identity, and state after a separate-process reopen.

## Persistence boundary

The CPD runner covers save/reopen in its scenarios by reopening with `bpy.ops.wm.open_mainfile` in the same process; the separate Nested Prefab QA explicitly used a fresh Blender process to create/save and another process to reopen and resolve twice. These runs show that their fixture receipts and bindings survived those tested persistence routes. They do not prove that every in-memory cache, source archive, external provider, or mutation rollback survives arbitrary reopen, process restart, or asset changes. Record source/package hashes and reopen observations per run; do not treat a successful save call alone as persistence evidence.

## Limits

- Blender-only synthetic tests; no Unity Editor or VRChat SDK execution.
- No claim about purchased or user-owned assets.
- The older Nested Prefab run used a distinct source snapshot; its evidence must not be attributed to `7057cbd`.
- No generic cross-package material/texture law is approved by this note. The identity model above is a testable design hypothesis grounded in the inspected implementation.
