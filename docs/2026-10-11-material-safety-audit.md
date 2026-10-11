# Material safety audit — 2026-10-11

Branch: `feature/material-safety-audit-20261011`; base: `e675fe6432d8e085af8aa392ec6fd3d4a8a969f7`.
This is a bounded audit and correction, not whole-product completion. Private packages, logs, scenes and identifiers are excluded.

## Findings and changes

| Item | Classification | Evidence / action |
|---|---|---|
| P0-1 name-only Material assignment | CONFIRMED, fixed | Actual `apply_materials_by_name` assigned an unrelated sole same-name candidate without GUID/fileID evidence. Regression failed before, passed after removing the fallback. Native preview is retained; explicit externalObjects dependency capture and receipt-backed assignment remain. |
| P0-1 reverse reference relations | ALREADY_FIXED within existing scope; wider completeness UNKNOWN | Existing graph/projection retains package, GUID/fileID, source/occurrence, Mesh and ordered effective Material references. These relations can be enumerated in reverse. No new global reverse-reference framework or missing edge inferred from a sole candidate. |
| P0-2 ordinal face assignment | ALREADY_FIXED refusal; general correspondence UNKNOWN | Actual Blender import/Confirm of public ThreeSlotSource cancels at the existing distinct-Material guard; geometry, slots, polygon indices and binding remain unchanged. No automatic slot reversal was added. |
| P1-1 individual Assistant cancellation | CONFIRMED, fixed | Real Unity utility window with A/B: original CancelEntry closed the window and hid B. It now removes A and repaints; only cancellation of the final entry closes. |
| P1-2 repeated authorization work | CONFIRMED observation; optimization deferred | Same measured operation repeatedly scans/hashes. This audit changes no ModelSkin authorization code and claims no speedup there. |
| P1-2 remembered-prompt preflight | CONFIRMED, optimized | Full provider inspection ran before the remembered-state filter. Fresh manifest fingerprinting now precedes that filter; displayed entries and Apply still fully inspect current files. No authorization cache. |
| P1-3 strict source/edited Skin equivalence | UNKNOWN | Retained source/edited/repeat measurements establish several identities and repeat stability, but not an independent native CP/corner/influence correspondence. No strict transport PASS inferred from counts or aggregate similarity. |
| P2 README / distribution revision | CONFIRMED, clarified | Historical c5585a6 ZIP, newer local 7727a7d ZIP, audit source and published 7d21318 prerelease are now separated. Default-branch integration remains pending; no Release/default-branch change. |

## Tests and actual runtime observations

- Focused Python baseline: the new same-name regression failed; the other 63 tests passed. After the Material fix all 64 passed. Final relevant Material, face, graph/override and triangle controls: **95 tests PASS**.
- Blender 5.2.1: existing native Material mapping authority test **PASS**, exit 0; both missing explicit GUID and absent explicit mapping preserve the source preview. The obsolete test expectation approving name fallback was corrected after independent review.
- Unity 2022.3.22f1 normal Editor, same actual A/B cancellation handler: before `window_survives=false`, `remaining_entry_exact=false`; after both true. A is cancelled, B remains prompted, last-entry cancellation closes, and preexisting state bytes are restored. Window recreation confirms persisted B state. Actual Editor restart and user GUI button traversal are **NOT_RUN**; this is not GUI acceptance.
- Public ThreeSlotSource replay: import finishes, Confirm is refused, before/after Mesh snapshot is exact, input package unchanged. Retained revision-pinned Unity capture supplies the source side; no new Unity source capture was performed. Six-decimal diagnostic oriented matching has no unique direct map; reversing orientation diagnostically yields `{0:2, 1:1, 2:0}`. That diagnostic is not a production face witness or winding PASS.
- Normal Unity performance verification exits 0. Preexisting Project files: 3,041 protected, changed 0, unexpected 0; lease and mutex returned. Manifest bytes changed only temporarily for the revision-control test and were restored.

## Performance measurements

Single-run elapsed times, not a statistical benchmark. Hash counters instrumented only a private test copy of the existing Finalizer; instrumentation is not shipped.

| Operation | Before: reads / hashes / bytes / ms | After: reads / hashes / bytes / ms |
|---|---|---|
| Authorization, three property callbacks | 384 / 12 / 215,562 / 45.9432 | 384 / 12 / 215,562 / 53.5168 |
| Automatic open of remembered cancelled manifest | 1 / 8 / 107,720 / 11.4490 | 0 / 0 / 0 / 1.7416 |
| Changed manifest at the same path | not measured | 1 / 8 / 107,720 / 25.3722 |

Counters above are Finalizer manifest reads and provider hashes, not all Assistant I/O. The Assistant still reads/fingerprints the on-disk manifest to identify its current revision. A whitespace revision change triggers full provider inspection, rather than reusing remembered approval. Apply's independent fresh inspection/hash checks are unchanged.

The measured path resolves the existing two-Bone manifest; its actual after-run manifest SHA matches the before-run backed-up manifest. The supplied import package contains a different 24-Bone task. Therefore these numbers prove only the measured two-Bone operation and remembered-prompt saving, **not** CASE0024 authorization scaling or package-wide callbacks. No ModelSkin caching optimization was adopted.

## Reverse lookup and face proof limits

- `export/semantic_graph.py`: package-scoped source identities and Renderer-to-Mesh / Renderer-to-Material edges. Asset dependency alone does not identify a receiver occurrence or face.
- `unity/effective_prefab.py` and `unity/occurrence_projection.py`: exact source chain and effective occurrence projection, Mesh GUID/fileID, ordered Material references, null slots and unresolved states. Raw source values, remaps and occurrence overrides are distinct evidence.
- `unity/material_mapping.py`: explicit importer remap identities. Its legacy standalone name lookup utility is not used by the corrected import assignment helper.
- `blender/material_owner_usage.py`: retained package/revision/occurrence/provider usage supports owner labels. It is not an independent native face proof.
- Existing exact-reference, nested/Variant, package, null/missing, duplicate/empty/unused and uniform-Material regression controls remain. Safe uniform assignment does not establish a distinct-Material face join. General overlay/null/exporter behavior is not proved by this audit.

Retained CASE0024 first/repeat native output is byte-exact for measured positions, weights, bindposes and identities, with the intended Material identity and available target shader retained. Source has 11,602 vertices / 13,602 positive influences; edited has 10,992 / 12,992. Independent correspondence is missing, so these differences do not establish lost vertices/influences or safe loss. Bindpose comparison observes 235 changed float components, maximum absolute difference 2.8461217880249023e-6; no epsilon PASS. Missing-shader/texture and deformation cases beyond the retained observations are not promoted to PASS. See the retained [CASE0024 record](../TEST_RESULTS.md).

## Official evidence applied to code

Read the three applicable summaries at official-document checkpoint `ca8fdf6912fd63594c019f27661000700a5b5e0b`: UNITY-MATERIAL-MESH, VERTEX-CORRESPONDENCE and BLENDER-SUPPLEMENT. They distinguish documented API, official source, inference and unavailable pages.

- [Unity sharedMaterials](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Renderer-sharedMaterials.html): references belong to Renderer usage; shared Material objects must not be mutated as a lookup shortcut. Current correction preserves preview objects and requires exact-reference resolution.
- [Unity GetExternalObjectMap](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.GetExternalObjectMap.html): importer remap evidence is distinct from receiver occurrence and native face correspondence. Existing receipt resolution remains authoritative.
- [Unity GetTriangles](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetTriangles.html): corner order and submesh partition matter. Diagnostic reversal does not authorize ordinal Material assignment.
- [Unity MeshRenderer materials](https://docs.unity3d.com/2022.3/Documentation/Manual/class-MeshRenderer.html): excess Material entries can overdraw the final submesh. No extra slot is discarded as unused by this correction.
- Blender v5.2.1 official source summary distinguishes Object-linked slots from Mesh material lists, importer index correction and exporter connection deduplication. Valid indices/counts alone remain insufficient proof. Unacquired rendered Manual/API pages and latest-patch status are not claimed verified.

## Independent review and remaining work

GPT-6.1 SOL, medium, separate read-only execution context: **KEEP** production changes. Required correction: obsolete native name-fallback test expectation; corrected. No other important defect identified. Optional unused-helper cleanup deferred.

Remaining: full native restart/GUI acceptance; general distinct-Material correspondence; strict CP/influence transport beyond bounded accepted cases; repeated authorization optimization with correctly scoped measurement; newer installation ZIP; default-branch integration. Edited Animation return remains outside these fixes. Source assets, GUID/meta, existing scenes and private corpus remain protected.
