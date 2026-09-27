# Unknown Boundary / Fault Discovery checkpoint — 2026-09-27

This is a bounded investigation, not a claim that Core round-trip is complete.
Only public synthetic fixtures and sanitized private aggregates are recorded here.

## Hypotheses and discriminating experiments

| ID | Hypothesis | If true | If false | Cheapest experiment | User impact | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| U | A lost Renderer target can be safely treated as inert by package-only rules | Public S3 would justify a general rule | Unity observation remains revision-scoped | Unity-authored source-Renderer removal, then package projection | Wrong Material assignment | Medium |
| T1 | Texture dependency identity omits semantic role | Shared Image collapses two uses | Two records survive | One Material, one Image, Base Color plus Emission | Missing texture role | Low |
| T2 | Re-resolution overwrites a user's Image or node link | Edited binding reverts | Edit survives with explicit status | Edit, resolve, save/reopen, resolve | Lost edits | Low |
| T3 | Repeated resolve changes semantic state | R1 differs from R2/R3 | Stable state | Three resolves and fresh-process reopen | Nonrepeatable Import | Low |
| T4 | Provider order changes an otherwise unique binding | Final status/provider differs | Same final binding | Consumer before provider versus reverse | Order-sensitive setup | Low |
| M | Null/array/precedence holes alter projected Material slots | Unity-authored cases differ | Projection matches public API | Minimal Unity authored fixtures | Wrong Avatar appearance | Medium |

## U boundary

An attempt to use `PrefabUtility.RemoveUnusedOverrides` in Unity 2022.3.22f1
failed compilation because that public method is absent in this Editor. The
Inspector's **Unused Overrides** classification and remove action were not
observed; U-1 remains `NOT_OBSERVED`. No private source was changed. This is
not evidence that the residual private override is active or inactive beyond
the earlier exact-revision causal audit.

Public synthetic S3 was authored by Unity 2022.3.22f1 public Prefab APIs:
one Renderer had an active Material override, its source Renderer was removed,
and Unity retained one serialized Material modification with a lost target.
After reimport, the source and Variant had zero Renderer components under
`GetComponentsInChildren<Renderer>(true)`. A separate Unity run verified the
committed public fixtures without changing them. The package projection
reports `UNRESOLVED_OVERRIDE` and zero Renderer records. Inspector classification
was not observed for S3 either. Production keeps the package-only override
fail-closed; no name or candidate-count inference was introduced. U history
investigation stops here.

## B-QA-004 and Texture resolution

An existing saved private split-package scene was reopened read-only. Before
explicit re-resolution, 243 Texture records were marked `BOUND`. Of those,
141 were `Preserve Only` properties whose Image provider datablocks were not
present in the reopened scene. Explicit re-resolution changed these 141 to
`UNRESOLVED`; the count of populated Image Texture nodes stayed constant.
The 102 visible-role records had providers present. This explains the prior
243→102 `BOUND` registry count without demonstrating loss of visible Texture
binding. `Preserve Only` records are excluded from Import Outcome counts;
the export modules do not read the dependency registry. An exact export before
and after was not run, so full export impact remains unverified. Severity of
the observed count drift is lower than a proven visible Core defect.

Two independent public synthetic defects were found:

1. **T1 role collision:** `_record_key` omitted Texture role/property, and a
   GUID-to-role dict let the same Image GUID collapse Base Color and Emission.
   The minimal RED retained only one record. The fix keys Texture dependencies
   by role and property and classifies canonical properties before GUID
   fallback. Both bindings survive fresh-process save/reopen and repeated
   resolve. This does not claim to explain the 141 `Preserve Only` drift.
2. **T2 edit overwrite:** Texture re-resolution had no applied-state guard.
   A user-selected Image was replaced, and a user node connection was rewired
   after save/reopen. Both failed before the fix. The resolver now records a
   scoped Image/node-link signature when it applies a binding, checks that
   signature before changing it, and records `USER_EDIT_PRESERVED` on mismatch.
   Validation of a user-selected Image does not write to that Image.

For saved scenes from older builds, an already `BOUND` visible Texture record
has no applied-state signature. Re-resolution preserves its current nodes and
reports `UNVERIFIED_TEXTURE_STATE`, rather than silently claiming that no user
edit occurred. The three private scene observations (normal, split, and
variant-heavy) retained their populated Image Texture node counts in memory;
the old records were not upgraded or saved. Fresh Import and exact export are
separate validation gates. A fresh normal-case private Import
with the current source kept 18 `BOUND` Texture records and 354 populated
Image-node occurrences across Mesh material slots through two resolves and
save/reopen. Unused Material datablocks were pruned on reopen, explaining a
35→32 change in the count across *all* Materials; the Mesh-slot count was
stable. A fresh split-package Import without a model witness retained 188
populated Image nodes, while 149 `Preserve Only` records went from `BOUND` to
`UNRESOLVED` on explicit post-reopen resolve because their Image providers
were absent. Its Mesh material slots were not bound in that no-witness probe,
so this is not a proof of final visual fidelity. Exact export remains unrun.

## Metamorphic and stateful results

| Relation | Result and scope |
| --- | --- |
| MR-1 display-name rename | Not run in this checkpoint. |
| MR-2 unrelated provider | PASS in one synthetic non-colliding Texture dependency. |
| MR-3 repeated resolve | PASS for dual-role record/provider/binding state, nodes, slot, and Import Outcome counts. |
| MR-4 save/reopen | PASS for dual-role Texture binding and preserved user node connection. |
| MR-5 provider order | PASS for one unique cross-package Texture dependency; full Package Import order not retested. |
| MR-6 user edit | PASS for Image change, connection change, provider addition, provider loss and re-addition in synthetic Blender scenes. |
| MR-7 unrelated U | Prior scoped projection control; not rerun here. |

Minimal failing sequences before the T2 fix were `bind → edit Image → resolve`
and `bind → edit connection → save → reopen → resolve`. A negative control
showed that an unedited resolver-owned Image binding is unbound on provider
loss while an unrelated user node remains. An older receipt-free Texture
binding stays unverified across two resolves and does not overwrite the edit.

## M1 — explicit null Material

Unity 2022.3.22f1 authored a public synthetic Variant whose base Renderer
has one Material slot and whose Variant `sharedMaterials[0]` is explicitly
null. Its Prefab serialization uses `m_Materials.Array.data[0]` with
`objectReference: {fileID: 0}`. Before the fix, the parser discarded that
reference and projection emitted `UNRESOLVED_OVERRIDE`, conflating known null
with malformed input. The Unity-authored fixture was RED. The narrow parser
now retains `{"fileID": 0}`, and projection records a known null slot with
`material_status=EXACT`; malformed nonzero references without GUID remain
unresolved. A zero fileID mixed with an invalid GUID also remains unresolved.
The public fixture and focused tests are GREEN.

This proves Unity semantics and VAPB projection only. Automatic Blender
null-slot realization on a proven native Object was not exercised with this
fixture. Import Outcome therefore reports
`NULL_MATERIAL_REALIZATION_UNVERIFIED` as `PARTIAL` instead of claiming a
completed Import. Null binding requires a separate native realization probe.

The current full Python suite ran 392 tests with no failures. Blender 5.2.1
passed the dual-role save/reopen probe, provider-order probe, all user-edit
phases, Import Outcome write/read, and late Object-slot probe. These checks
do not establish native realization of the null Material override.

## Mutation sensitivity, coverage, and remaining work

The pre-fix T1 and T2 implementations failed their new tests. Two additional
in-memory mutations (drop role/property from the key; make the edit-signature
check always accept) each made its focused Blender test fail with nonzero exit
(`TEST_KILLS_MUTATION`). Repository source was not altered by these mutations.
No isolated mutation was run for witness revisions,
Object slots, or unrelated U propagation in this checkpoint.

M2 array size, M3 precedence, independent Unity Renderer population coverage,
and fresh private exploratory Imports beyond the two relevant texture cases
were not executed here. Existing public synthetic coverage is not a substitute for independent
Unity population or multiple real round-trips. An older broad Blender
cross-package integration script currently fails at a missing Mesh datablock
in its grouped fixture; this was not attributed to the Texture resolver patch.

**Next action:** Use a public native Mesh/Renderer bridge to check that an
explicit Unity null Material override clears the corresponding Blender Object
slot, then recheck Import Outcome after save/reopen.
