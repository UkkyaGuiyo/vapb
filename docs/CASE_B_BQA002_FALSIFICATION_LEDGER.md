# B-QA-002 falsification ledger (2026-09-27)

Scope: the two explicit Material overrides (R1/R2) and one unresolved
override (U) in Case B. Private commercial assets, identifiers, witness rows,
screenshots, and raw logs remain outside this repository. The actual source
is `feature/multi-package-identity` at `c8718a3` before this audit; the
historical projection source is `41c081a` (Git blob `3b0bc1b0`).

## Nested/Variant stripped-alias counterexample (2026-09-27)

This is a **different public synthetic** from the Case B R1/R2/U experiment
below. The source, first-party FBX generator, Unity-authored Prefabs, public-API
Oracle, and machine-readable identity edges are in `tests/unity_alias_oracle/`.
Unity 2022.3.22f1 saved and reopened the Prefabs before recording
`Renderer.sharedMaterials[0]`, source chains, and signed local IDs.

| Case | Independent Unity observation | Previous VAPB projection | Repaired package-only projection |
| --- | --- | --- | --- |
| E0 direct model override | R1 slot changes | Same changed Material | Same changed Material |
| E1 stripped alias override | Target instance R1 slot changes; other instance R1 and sibling R2 retain Base | Alias U unresolved; affected R1 incorrectly stays usable with Base | Alias U remains unresolved; class-compatible rows in only its nested instance become `UNKNOWN`; other instance remains usable |
| E2 override on other nested instance | Target instance R1 and R2 stay Base; other instance R1 changes | Other instance U unresolved and wrongly usable with Base | Only other instance's class-compatible rows become `UNKNOWN`; target instance stays usable |
| E3 missing alias source edge | Not run in Unity; malformed-source negative control only | U silently treated as unrelated | `UNKNOWN` bounded to the child Prefab's compatible Renderer class |
| E4/E5 repeated source and sibling Renderer | Unity changes one R1 occurrence; the second R1 occurrence and the observed sibling R2 slot stay Base | All projected rows stay usable with incomplete state | Other occurrence stays usable; R2 in the affected instance also remains `UNKNOWN` because package-only evidence does not identify which Variant-local Renderer alias is R1 |

The key serialized chain is root Material modification target → child Prefab
stripped Renderer document → `m_PrefabInstance` (one nested instance) and
`m_CorrespondingSourceObject` (Variant-local ID). Unity's documented public
Prefab API continues that exact source chain to the model R1 Renderer and
confirms the final slot. The Variant-local ID is absent from the serialized
Variant Prefab and `.meta`, so the Package itself cannot complete that join.
`alias_graph.json` records each edge's authority and this exact gap; names,
order, and candidate count are not joins. The model IDs used by the Python
projection test come from public `AssetDatabase` on the exact synthetic FBX;
its dummy native UIDs are unused by projection and do not prove native binding.

**Result A plus C:** the unmatched-equals-unrelated generalization is
falsified, while exact R1-versus-R2 package-only attribution remains unproven.
The repair recognizes a serialized stripped Renderer alias and withholds only
class-compatible projected rows within its proven nested instance. If that
instance/corresponding-source edge is malformed, it withholds the compatible
rows under that child Prefab. It never copies U's Material to a guessed row.
This is the smallest safe scope expressible by the current record-level
`material_status` and available serialized identity. A future revision-bound
alias bridge could keep unaffected R2 usable, but this audit has not created
one. A no-alias unmatched U still follows the earlier Case B behavior below.

Negative controls: wrong override source GUID/local ID is not bound; wrong
corresponding source or missing nested edge cannot bind; wrong model witness
revision creates no model rows; duplicate native candidate remains withheld by
the existing witness tests. The two same-source nested occurrences are checked
separately. Mutation tests prove no guessed binding on malformed inputs; they
are not claims about Unity's behavior on those malformed inputs.

At the `ea0dca4` checkpoint, the exact-commit ZIP passed isolated Blender
5.2.1 install/enable/disable. Fresh private Case B witness-assisted Import,
save/reopen, and identity-bound Object-slot re-resolution preserved the prior
validated binding scope; its unrelated override remains unresolved. The
normal Case A control also preserved its prior Material result after fresh
Import and reopen. Only aggregate success status is recorded publicly;
commercial input, local scene, raw logs, and identities stay outside Git.

## Discriminating experiments

The fixed synthetic base has two identified Renderer components, distinct
serialized slot-0 Material references, one model source, and a revision-bound
model witness. A third identified Renderer is reserved for the direct-invalid
control. Predictions were chosen from the reported failure: if U causes broad
invalidation, E1/E3/E4 remove both dependencies; if it is scoped to its target,
R1/R2 remain available. E6 must still withhold the truly affected R1; E7 must
withhold any binding for which model or native identity is unproven.

| Experiment | Changed variable | Expected discriminator | Observed with repaired production source |
| --- | --- | --- | --- |
| E0 | Valid R1/R2 only | Both `PARTIAL`, 2 dependencies | PASS: both `PARTIAL`, 2 dependencies |
| E1 | Add unmatched Material U | Broad poisoning: both `UNKNOWN`; scoped behavior: both `PARTIAL` | PASS: both `PARTIAL`, U issue retained, 2 dependencies |
| E2/E3 | Remove/reinsert U | Results switch only if U is causal | PASS: R1/R2 unchanged; U issue switches 0/1 |
| E4 | Move independent U before R1/R2 | Dependency result should not depend on this order | PASS: same 2 identity-bound dependencies |
| E5 | U on same instance, second instance, or another source GUID | Change only proven target scope | PASS: all identified R1/R2 rows retain their references; U remains unresolved |
| E6 | Invalid reference directly targeting R1 | R1 withheld, R2 usable | PASS: R1 `UNKNOWN`, R2 `PARTIAL`, only R2 dependency |
| E7 | No witness, wrong source revision, duplicate native candidate | No guessed binding | PASS: no projected model rows without witness/revision; duplicate native withholds that dependency |

The public replay is
`python -m unittest -v unitypackage_blender_importer.tests.test_unrelated_model_override`
from the repository parent import context. The fixture uses fixed synthetic
Renderer-to-native receipt expectations, independent of record ordering;
reversed record order and swapped R1/R2 Material references do not swap native
targets. A separate Blender probe checks actual Object slots and new-process
reopen. These tests do **not** establish complete source Renderer enumeration,
stripped alias resolution, or Unity-expanded state for arbitrary assets.

The historical `41c081a` projection blob, loaded in isolation against the
same public fixture and current dependency planner, produced:

| Input | Historical R1/R2 | Historical planned dependencies |
| --- | --- | ---: |
| E0 valid only | `PARTIAL` / `PARTIAL` | 2 |
| E1 add U | `UNKNOWN` / `UNKNOWN` | 0 |
| E2 remove U | `PARTIAL` / `PARTIAL` | 2 |
| E3 reinsert U | `UNKNOWN` / `UNKNOWN` | 0 |
| E4 move U first | `UNKNOWN` / `UNKNOWN` | 0 |

This isolates the historical `matches if matches else child_records` branch
in `project_occurrences` as the cause of the two-row projection poisoning for
this fixed base. The current branch changes only matched records to `UNKNOWN`
and retains the U issue. The minimized extra input is one unmatched Material
override **under the fixed valid R1/R2 source and witness**; it is not a
global minimality or uniqueness claim.

## Hypothesis ledger

Verdicts apply to the stated input and revision. `REJECTED_IN_SCOPE` does not
mean a subsystem is universally correct.

| ID | Required observation / falsifier and smallest test | Evidence and verdict | Scope / reopen condition |
| --- | --- | --- | --- |
| H0 stale ZIP or environment | Same failure only on a different runtime; compare exact source and installed ZIP | `REJECTED_IN_SCOPE`: prior exact-HEAD ZIP and this audit use the same repaired projection; historical source replay alone reproduces the old transition | Reopen if installed code hash or Blender version differs |
| H1 R1/R2 override not parsed | No explicit reference or wrong Oracle value; inspect serialized projection and independent Unity API result | `REJECTED_IN_SCOPE`: both references exist, and exact-revision Oracle `sharedMaterials[0]` matches 2/2 | Reopen on a different Prefab revision |
| H2 missing witness, alias, or instance scope | No exact native bridge, or U aliases an affected Renderer; compare witness, instance edge, and Unity expansion | `SUPPORTED` for no-witness withholding; exact Case B witness resolves R1/R2. General alias and witness-completeness proof remains `INCONCLUSIVE` | Reopen on nested/stripped source or incomplete witness evidence |
| H3 U invalidates unrelated projected rows | Adding only U changes R1/R2 status and dependency count; removal reverses it | `CAUSALLY_CONFIRMED` for historical projection: E0/E1/E2/E3/E4 = 2/0/2/0/0 dependencies. Current code preserves 2/2 and keeps U unresolved | Reopen if a new property or source relation can affect the same target slot |
| H4 downstream planner independently stops R1/R2 | Planner would stop `PARTIAL` rows even when supplied exact witness/native identities | `REJECTED_IN_SCOPE`: planner emits two dependencies when R1/R2 remain `PARTIAL`; its skip of historical `UNKNOWN` is a downstream consequence | Reopen on provider/consumer failure with `PARTIAL` rows |
| H5 wrong DATA/OBJECT slot | Dependency says bound but actual Object slot differs | `REJECTED_IN_SCOPE`: prior installed-ZIP Case B had 114/114 dependency/actual Object-slot identity matches after reopen; synthetic Blender probe confirms `OBJECT` links | Reopen on shared-Mesh or edited-slot variant |
| H6 save/cache/re-resolve changes this binding | R1/R2 lost after fresh process or resolve | `REJECTED_IN_SCOPE` for these two slots: prior 114/114 remained after reopen/resolve. Texture registry status drift is separate B-QA-004 | Reopen if exact Object-slot identity changes |
| H7 display-only error | Correct slots before and after, yet observed white surface | `REJECTED_IN_SCOPE` for the original R1/R2 white slots: before repair they lacked those references; after repair saved target render showed texture. Material Preview discrepancy remains B-QA-003 | Reopen on stable Preview mismatch with correct slots |

## Private Case B boundary

An aggregate-only comparison of the saved installed-ZIP scene, the accepted
model witness, and the **same root Prefab revision** in a Unity 2022.3.22f1
public-API Oracle found: two projected target rows, two corresponding expanded
Renderer rows, and two matching slot-0 Material identities. U shares their
source asset and instance edge, but matches zero projected rows, zero witness
Renderer rows, and zero expanded Oracle Renderers in that selected Prefab.
The Oracle enumerated all `Renderer` components in the loaded Prefab contents.
This supports noninterference with R1/R2 for this exact revision; the package
projection itself cannot treat Oracle-only completeness as general knowledge.

Prior installed-ZIP QA for the same runtime found witness-assisted Case B
114/114 Object-slot identity matches after import, save/reopen, and re-resolve;
U remained one unresolved issue. Without the witness, model-source identity
stayed unresolved, so no automatic R1/R2 native binding is claimed. Case A
normal control retained 147/148 Unity-GUID slots and 144 image-node slots.
These are prior QA observations, not a new full Import performed by this audit.
This audit reopened that saved private scene in another Blender process and
confirmed both model-source slots and all 112 other witness slots still bound
to their expected Object-slot identities after explicit re-resolution; U stayed
unresolved. Three other, non-witness missing-consumer entries remain outside
B-QA-002. No private source file or saved scene was modified.

Audit worktree validation: focused Python 5 PASS; full public Python 366 PASS,
0 FAIL/ERROR; `compileall` PASS; Blender 5.2.1 synthetic Object-slot probe
and new-process reopen PASS, with exit code 0 in both processes. The first
Blender probe emitted a nonfatal extension-cache warning; the isolated reopen
did not. The exact new-commit ZIP installation and release verification are
recorded separately at the final checkpoint.

**Decision:** no further production change is justified by this audit. The
existing repair is confirmed for exact Case B and the tested synthetic scopes.
It does not prove that every future unmatched U is independent, nor that
package-only model identity can be reconstructed. The next discriminating
experiment is a synthetic nested/stripped Prefab whose U target follows a
corresponding-source alias to R1 while the model witness lists R1/R2: compare
Unity's expanded slot and VAPB's projection before deciding whether alias-aware
invalidation is required.
