# Material safety audit — 2026-10-11

Branch: `feature/material-safety-audit-20261011`; base: `e675fe6432d8e085af8aa392ec6fd3d4a8a969f7`.
This is a bounded audit and correction, not whole-product completion. Private packages, logs, scenes and identifiers are excluded.

## Findings and changes

| Item | Classification | Evidence / action |
|---|---|---|
| P0-1 name-only Material assignment | CONFIRMED, fixed | Actual `apply_materials_by_name` assigned an unrelated sole same-name candidate without GUID/fileID evidence. Regression failed before, passed after removing the fallback. Native preview is retained; explicit externalObjects dependency capture and receipt-backed assignment remain. |
| P0-1 reverse reference relations | ALREADY_FIXED within existing scope; wider completeness UNKNOWN | Existing graph/projection retains package, GUID/fileID, source/occurrence, Mesh and ordered effective Material references. These relations can be enumerated in reverse. No new global reverse-reference framework or missing edge inferred from a sole candidate. |
| P0-2 unsafe ordinal face assignment | ALREADY_FIXED prevention only | Actual Blender import/Confirm of public ThreeSlotSource cancels at the existing distinct-Material guard; geometry, slots, polygon indices and binding remain unchanged. This prevents guessed assignment; it does not restore correct distinct-Material face correspondence. |
| P0-2 correct distinct-Material face correspondence | Bounded ThreeSlotSource membership proved; ordinary product UNRESOLVED | Fresh matching original FBX/meta, native Mesh and Prefab occurrence yield 12 unique exact UV triangle/corner joins. Ordinary input has no native submesh face-partition carrier consumed by Confirm. No automatic slot reversal or guard removal. |
| P1-1 individual Assistant cancellation | CONFIRMED, fixed | Real Unity utility window with A/B: original CancelEntry closed the window and hid B. It now removes A and repaints; only cancellation of the final entry closes. |
| P1-2 repeated authorization work | CONFIRMED observation; optimization deferred | Same measured operation repeatedly scans/hashes. This audit changes no ModelSkin authorization code and claims no speedup there. |
| P1-2 remembered-prompt preflight | CONFIRMED, optimized | Full provider inspection ran before the remembered-state filter. Fresh manifest fingerprinting now precedes that filter; displayed entries and Apply still fully inspect current files. No authorization cache. |
| P1-3 strict source/edited Skin equivalence | UNKNOWN | Retained source/edited/repeat measurements establish several identities and repeat stability, but not an independent native CP/corner/influence correspondence. No strict transport PASS inferred from counts or aggregate similarity. |
| P2 README / distribution revision | CONFIRMED, clarified | Historical c5585a6 ZIP, newer local 7727a7d ZIP, audit source and published 7d21318 prerelease are now separated. Default-branch integration remains pending; no Release/default-branch change. |

## Tests and actual runtime observations

- Focused Python baseline: the new same-name regression failed; the other 63 tests passed. After the Material fix all 64 passed. Final relevant Material, face, graph/override and triangle controls: **95 tests PASS**.
- Blender 5.2.1: existing native Material mapping authority test **PASS**, exit 0; both missing explicit GUID and absent explicit mapping preserve the source preview. The obsolete test expectation approving name fallback was corrected after independent review.
- Unity 2022.3.22f1 normal Editor, same actual A/B cancellation handler: before `window_survives=false`, `remaining_entry_exact=false`; after both true. A is cancelled, B remains prompted, last-entry cancellation closes, and preexisting state bytes are restored. Window recreation confirms persisted B state. The actual restart follow-up below adds API-level persistence/rehydration proof; user GUI button traversal remains **NOT_RUN**.
- Historical public ThreeSlotSource replay (superseded for the bounded current-context membership conclusion below): import finishes, Confirm is refused, before/after Mesh snapshot is exact, input package unchanged. Retained revision-pinned Unity capture supplies the source side; no new Unity source capture was performed. Six-decimal diagnostic oriented matching has no unique direct map; reversing orientation diagnostically yields `{0:2, 1:1, 2:0}`. That diagnostic is not a production face witness or winding PASS.
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

## P1-3 minimum existing-resource CP inspection

One new offline inspection reads a fresh exact copy of the already-successful real direct-Skin output package and source FBX bytes recovered by exact GUID/hash from the existing protected input archives. It reuses the pinned installed FBX parser; no new export, Unity session, Apply, asset edit or production source/test change. Source archives, checkpoints and retained captures are unchanged. Purchased FBX copies, identifiers, raw geometry/influences and the private inspection script remain local; only aggregate findings are recorded here.

- Source and output raw FBX each contain **9,044 control points**, with no duplicate raw CP positions. Source polygon corners: 35,736; triangulated output corners: 53,400. These are observed structures, not correspondence or fidelity proof.
- Both raw UV layers use ByPolygonVertex/IndexToDirect. **Zero corners** have the existing diagnostic CP-marker pattern (integer x >= 1, y exactly 0.375). This checks that particular existing marker route, not every possible derivation.
- Retained native source: 11,602 vertices / 9,044 distinct float32 position groups; native output: 10,992 / 9,044. Neither capture contains CP labels, UV capture or effective native import-policy observation. Native splits do not by themselves rule out a many-to-one CP join when raw CP positions are unique.
- The output package contains the existing weight-policy JSON matching the exact generated model revision. Payload presence proves no effective importer setting or expected Unity influence representation. No frame was fitted, native index reused, epsilon accepted or Material assignment changed.

**Result: strict comparison remains UNSUPPORTED.** Missing relationships are source raw CP -> native original vertex, Blender final-state CP -> generated raw CP -> native output vertex, and an independently validated coordinate/import-policy/numeric representation scope for expected positions and positive influences. Existing marker-based numeric tools need those fields; the retained checkpoint/native captures cannot supply them. Counts, unchanged Apply output and unique raw positions do not fill these relationships. This inspection identifies missing evidence; it neither proves loss nor establishes a product defect.

Within the existing 24-input resources and current operators, no additional independent ordinary real-data step was identified: remaining Texture/Script cases need exact providers absent from the inspected catalog; embedded-Material/extra-slot cases need identity/face proof or specified meaning. The successful existing edited Variant remains available for the separate human GUI/render acceptance gate. Supported single Bone-TRS Action return as an independent Clip is already implemented; this real case's Animation return and human GUI assignment have not been verified. This bounded inspection does not prohibit a newly authorized supported route or declare absence outside the inspected catalog.

Independent review: GPT-6.1 SOL, medium, separate read-only context: **KEEP** the current-evidence UNSUPPORTED conclusion. The report preserves the possible many-to-one join and identifies missing validated frame/numeric conversion, group correspondence and expected influence representation; no product defect or new runtime/framework step is justified.

## Official evidence applied to code

Read the three applicable summaries at official-document checkpoint `ca8fdf6912fd63594c019f27661000700a5b5e0b`: UNITY-MATERIAL-MESH, VERTEX-CORRESPONDENCE and BLENDER-SUPPLEMENT. They distinguish documented API, official source, inference and unavailable pages.

- [Unity sharedMaterials](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Renderer-sharedMaterials.html): references belong to Renderer usage; shared Material objects must not be mutated as a lookup shortcut. Current correction preserves preview objects and requires exact-reference resolution.
- [Unity GetExternalObjectMap](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.GetExternalObjectMap.html): importer remap evidence is distinct from receiver occurrence and native face correspondence. Existing receipt resolution remains authoritative.
- [Unity GetTriangles](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetTriangles.html): corner order and submesh partition matter. Diagnostic reversal does not authorize ordinal Material assignment.
- [Unity MeshRenderer materials](https://docs.unity3d.com/2022.3/Documentation/Manual/class-MeshRenderer.html): excess Material entries can overdraw the final submesh. No extra slot is discarded as unused by this correction.
- Blender v5.2.1 official source summary distinguishes Object-linked slots from Mesh material lists, importer index correction and exporter connection deduplication. Valid indices/counts alone remain insufficient proof. Unacquired rendered Manual/API pages and latest-patch status are not claimed verified.

## Independent review and remaining work

GPT-6.1 SOL, medium, separate read-only execution context: **KEEP** production changes. Required correction: obsolete native name-fallback test expectation; corrected. No other important defect identified. Optional unused-helper cleanup deferred.

### Actual Editor restart follow-up

An isolated self-authored A/B manifest pair uses a display-only fixture provider and the actual Assistant `Inspect`, `Remember`, `CancelEntry`, `Show` and `RestoreDisplayedPrompt` paths. No package import, provider Apply or Scene save. One normal Editor process exits, then a distinct normal Editor process starts in the same dedicated Project: exactly one restart.

- Before exit: A cancelled, B prompted, A hidden, B visible; actual selected-manifest reopening shows B.
- After restart: A cancelled and hidden, B prompted and visible; explicitly invoking the existing restoration handler rehydrates B from project-local persisted state. Both native process exits are 0.
- Original 3,041 Project files unchanged; unexpected files 0. Preexisting Assistant state bytes restored exactly. Owned children/lock absent and lease/mutex returned.
- This proves restart persistence plus API-invoked rehydration. Automatic startup reopening, user menu/button clicks, full GUI presentation and successful Apply are **NOT_RUN**. The test does not claim an error-free real provider/asset restoration.
- GPT-6.1 SOL medium targeted read-only review: **KEEP**, no important defect in the added probe. Production source is unchanged in this follow-up; prior tests/performance evidence remain scoped to their original runs.

### P0-2 completed current-context investigation

The original public, self-authored `tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage` was observed in a fresh normal Unity 2022.3.22f1 process and then imported through normal VAPB RECONSTRUCT in Blender 5.2.1. The existing FBX parser, Renderer capture and Unity coordinate probe were reused. No old explicit-remap observation, new production witness, ad hoc face-map injection or source asset change was used. Private launch scripts and raw logs remain local.

- Package SHA256 `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`; FBX SHA256 `fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5`; original meta SHA256 `ed9bb63c5bbc23e8dc2fa01353a037fef0b907b2842992598c1e1db911c8240d`. FBX/meta hashes before and after native capture are identical. This meta has no explicit remap and an empty identity-name table. The older remapped observation is a different context and supplies no evidence here.
- Exact Prefab source GUID/local Renderer ID, Mesh GUID/fileID and ordered effective Material GUID/fileIDs agree between native Unity and normal Blender projection. The native Model Mesh is the referenced Prefab Mesh. Actual import policy is captured, including welding and vertex/polygon optimization.
- All **12 triangles** have distinct exact unordered UV signatures in raw FBX, Blender and Unity. Each triangle has three distinct exact UV corners; multiplicity is preserved and the unique corner permutation is computed separately from membership and orientation counts are recorded. The observed Blender-slot to native-submesh join is **2 -> 0, 1 -> 1, 0 -> 2**. This is derived from faces, not assigned from slot order. The three resulting Material references are the exact native Prefab array entries.
- Raw-to-Blender orientation is +1 on all 12 triangles; raw-to-Unity orientation is -1 on all 12. Winding reversal is observed, not approved as oriented equivalence. Raw-to-Blender local position difference is 0; under the declared `0.01 * reflectX` raw-to-Unity transform, maximum absolute difference is `6.332993504609696e-10`. This is an observation, **not** strict numeric transport PASS or an epsilon acceptance.
- Diagnostic duplicate-face, missing-face and duplicate-corner mutations are rejected. Deliberate reversal changes the observed orientation. Existing focused empty/unused/uniform, triangle and override-reference controls: **15 tests PASS**. These are the already-run checks; no remeasurement or production test change was needed for this record.
- Actual Confirm remains **CANCELLED** and its full captured Mesh before/after is unchanged. Native capture completed with 3,041 protected Project files unchanged and no unexpected files. There is no new user-usable distinct-Material restoration capability.

**Precise existing-scope limit:** the package's raw FBX supplies raw material layers and UV faces, and the Prefab supplies native Mesh identity plus effective Material references, but neither supplies the generated Unity submesh UV/triangle partition needed to join those two sides. `ModelIdentityRow` carries identity, skin/frame and shape information; it has no native submesh/UV face-partition fields, and its validator rejects unknown fields. `plan_witness_realizations` cannot supply an absent face partition. `_material_plan` therefore has no current production face proof to consume for distinct Materials. This one-fixture native observation demonstrates the missing join, but cannot establish a general source-only Unity partition rule or become mandatory Unity preprocessing for ordinary Import.

No safe minimal production correction through an existing carrier is demonstrated. Production source, guard, schemas and tests are unchanged in this follow-up. Ordinary distinct-Material restoration remains **UNRESOLVED**; the bounded original ThreeSlotSource membership is now proved. Duplicate UV signatures, other import policies, other occurrences/remaps, overlays and general winding/frame equivalence remain unproved. The exact missing datum is an identity/revision/import-policy-scoped native face partition (or an independently proved existing source-only derivation); defining a new carrier is outside this bounded task.

Public synthetic observations: [face join](../tests/evidence/inbound-material-face-membership-20261007/current-context-20261011/face-join.json), [native context](../tests/evidence/inbound-material-face-membership-20261007/current-context-20261011/unity-context.json), [native coordinate capture](../tests/evidence/inbound-material-face-membership-20261007/current-context-20261011/unity-coordinate.json). The coordinate capture's `pass` denotes capture validity/input preservation only, not cross-runtime transport or Material restoration PASS. The face-join summary records assertions from the private diagnostic execution; it does not contain the complete Blender corner capture or a replayable production witness.

Independent review: GPT-6.1 SOL, medium, separate read-only context: **KEEP** bounded membership conclusion and no production patch. The evidence-description correction distinguishes transient computed corner permutations from persisted orientation counts; applied. No remeasurement or broader source change requested.

Remaining: automatic restart/GUI acceptance; general distinct-Material correspondence; strict CP/influence transport beyond bounded accepted cases; repeated authorization optimization with correctly scoped measurement; newer installation ZIP; default-branch integration. Supported independent Bone Action Clip return was already implemented before this audit; general Animation/Avatar return and human GUI assignment remain unverified. Source assets, GUID/meta, existing scenes and private corpus remain protected.

## Approved independent Action return: existing implementation reconciled

The 2026-10-10 approved single edited Bone Action -> independent AnimationClip -> manual Unity assignment route is already connected in current source. The earlier blanket "Animation return unimplemented" statement in this audit was incorrect. Historical 2026-10-09 plan checkpoints predate the implemented normal-package path and must not reopen completed implementation.

- `export/action_carrier.py` validates one active layered Action/slot and supported Bone TRS channels against existing complete Bone realization mappings, exporting a separate carrier from copies while preserving the original Action/rig.
- `operators/export_unitypackage.py::_prepare_model_skin` emits the carrier asset, exact-revision `action_clip` task and importer-unit metadata alongside rest-pose Skin. The normal package includes `VapbActionClipFinalizer.cs`; the existing ZIP builder includes that helper too. Normal Blender Import still requires no Unity Editor preprocessing.
- `VapbModelSkinFinalizer` parses and validates that task and calls `ApplyVariantWithActionClips`. The existing Clip consumer validates carrier hash/units/take, transported Bone identities, target rest/hierarchy and unique binding paths, then uses `AnimationUtility.GetCurveBindings`, `GetEditorCurve`, `CalculateTransformPath` and `SetEditorCurve` to create an independent non-Legacy `.anim` via `AssetDatabase.CreateAsset`. It reports the Clip plus Variant-root playback context in the existing Apply prompt. It assigns no Controller/Animator and guesses no Bone correspondence.
- Saved native acceptance, [normal package independent Bone Clip return](../TEST_RESULTS.md#normal-package-independent-bone-clip-return-2026-10-10), already proves the owned two-Bone source-model case: ordinary package import, Clip/linked Variant creation, unchanged repeat, occupied/altered Clip refusal, reload, and three sampled final-Variant Skin poses matching the carrier with maximum observed vertex difference zero. Those measurements were not rerun. Continuous-time or bitwise Animation equivalence, general Avatar retargeting, nested/direct Prefab Action runtime, this real CASE0024 Animation and human GUI assignment remain unverified. Existing sampled/rest tolerances are not Skin numeric transport acceptance.

No missing connection in this supported route was identified. No production source/tests, schemas, assets, Action, Controller or output packages changed in this reconciliation; only contradictory current documentation and the saved plan checkpoint were corrected. P0-2/P1-3 limits and independent input/identity refusal remain intact. The next user-facing step for this supported route is the separately gated manual Clip assignment; extending unsupported Action contexts would require separate concrete authority/proof, not a new foundation under this task.

Focused code check: current independent Clip consumer matches the previously native-verified normal package consumer after line-ending normalization. No runtime or completed regression was repeated. Independent GPT-6.1 SOL, medium, read-only wiring review: **KEEP** documentation-only correction; no missing bounded product connection or code fix identified.
