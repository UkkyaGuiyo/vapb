# Independent Unity ↔ Blender hierarchy baseline — 2026-09-30

**STATUS: PARTIAL / public synthetic RED.** Production source unchanged.
Starting local/remote HEAD: `0ae38f333dbc4f01fafdc4f88139b9f653d74223`, clean.
The exact package SHA-256 was verified before normal VAPB production Import:
`358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098`.
No Unity Oracle was read by the Blender snapshot script and no fixture-only
semantic correspondence or witness was injected.

| Observation | Unity | Blender |
| --- | ---: | ---: |
| Semantic nodes | 12 | 10 |
| Semantic parent edges | 11 | 9 |
| Proven semantic Renderer owner | 1 | UNPROVEN |
| Skin bones with occurrence bridge | 2 | UNPROVEN |
| Repeated accessory occurrences | 2 | 0 |
| Technical wrapper | n/a | 1 |
| Unmapped native Mesh/Armature Objects | n/a | 4 |

Blender background process exit: **0**, snapshot marker PASS, total Objects 15.
The source template and member-copy realizations remain distinguished by receipt
metadata in local evidence. Four native Objects are **unmapped**, not silently
counted as four extra semantic nodes or technical-only helpers.

`baseline_comparison.json` contains only synthetic identities and aggregates.
The raw Blender snapshot, source extraction, `.blend` and logs remain outside
Git because even public-fixture metadata contains developer absolute paths.

## Comparator scope and measured result

`tests/hierarchy_comparator.py` is an independent **partial comparator** for a
single selected composition's persistent prefab GO identity, Object parent
edges and local/world matrices. It uses package revision and asset GUID/signed
localID, never display names. The fixture's prefab-local IDs already distinguish
repeated occurrences. Shared source IDs lacking a distinct occurrence bridge
are AMBIGUOUS. Full root-context/ordered-edge native equivalence remains pending.

- EXACT: **40 checks**, consisting of 10 node identities, 10 parents,
  10 local matrices and 10 world matrices. These are not 40 matching nodes.
- MISSING: **2 nodes**, the two repeated accessory occurrences.
- MISSING_OCCURRENCE: **1 group**, recording lost multiplicity, not proving
  that the importer merged two Objects into one.
- UNSUPPORTED_REPRESENTATION: **5 checks**, Renderer owner, Mesh bridge,
  ordered native bones, rootBone and native Bone representation.
  These checks are **unimplemented in the comparator**, not a claim that
  production can never represent those relationships.
- WRONG_PARENT / EXTRA_SEMANTIC / TRANSFORM_MISMATCH: **0** in checked scope.
- EQUIVALENT_REPRESENTATION: unimplemented; no native equivalence claimed.
- Comparator process exit: **1** for this RED baseline.

Unity float32 decomposition versus Blender quaternion/TRS reconstruction at
scale 180 initially exceeded a fixed absolute 2e-5 matrix threshold. Matrix
comparison now documents absolute 2e-5 plus 1e-6 times matrix magnitude;
all ten observed local/world matrices pass this tolerance. This is numerical
comparison tolerance, not a geometry/axis/unit or production transform change.
No geometry parity claim follows from semantic Empty matrix agreement.

## Cause boundary

**OBSERVED:** independent Unity public API expands 12 GO occurrences. The same
serialized Majun prefab contains two PrefabInstance documents referencing one
Accessory source. Current `parse_prefab()` yields ten GameObjects and twelve
Transform documents. The resulting Blender semantic GO identities are those
ten direct prefab GameObjects; neither nested accessory GO is realized.

**DERIVED:** missing hierarchy coverage starts at the prefab-local GO table /
nested occurrence expansion boundary, before ordinary hierarchy parenting.
`hierarchy_builder` iterates `prefab.game_objects`; the import operator's nested
model instance construction handles model/Renderer realization paths. This
renderer-free nested source has no Renderer occurrence to drive that path.
This is a general unsupported nested semantic expansion gap, not an extra
native FBX Empty explanation. No private-specific fix is involved.

**UNKNOWN:** native Skin-to-semantic-owner/Bone identity equivalence. The
projection records source Skin intent, but those records alone do not prove
native Mesh/Armature attachment. Do not score source projection as realization.

## Reproduction

Run from the repository directory, supplying the exact phase 1 package:

```text
blender --background --factory-startup --python-exit-code 1 --python tests/blender_hierarchy_snapshot.py -- <Majun.unitypackage> 358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098 Assets/VapbHierarchy/Majun.prefab <local evidence directory>
python tests/hierarchy_comparator.py tests/unity_hierarchy_probe/unity_oracle.json <local evidence directory>/blender_snapshot.json 358df2fed2c0b00825c3aacde8f78f8d9027e0b55bf3855a96c4f2ccc6a22098 <local evidence directory>/comparison.json
```

From repository **parent**, focused comparator tests:

```text
python -m unittest unitypackage_blender_importer.tests.test_hierarchy_comparator -v
```

Ten tests PASS: names/rename ignored, missing node and repeated multiplicity,
duplicate identity, wrong parent including semantic Bone chain and attachment,
same-name unrelated technical Empty, extra semantic identity, transforms/NaN,
revision rejection, ambiguous shared-source occurrence, and no self-scoring of
native Skin from source projection. These are comparator unit controls;
**actual native Bone corruption detection is not yet implemented**.
Three new Python files compileall PASS. Scope reviewer PASS; its multiplicity
label caveat was addressed with MISSING_OCCURRENCE instead of collapse cause.

## Pending / convergence

No production fix; full Python/Blender regressions were not rerun because
production is unchanged. Actual Blender rename/save/reopen parity, native
representation comparator coverage and synthetic GREEN remain pending.
Real UnityPackage differential has **NOT RUN**, because the required preceding
public comparator/synthetic GREEN is not established. No private data was used,
no private input question was asked, no real-input failure was inferred.

Opening API balance: 18.2968137500. Within-turn balance is not reliable debit
evidence. Convergence preserves the hard 15-credit reserve conservatively;
final effective spendable balance is unconfirmed. One existing scope reviewer
was reused; Astra was not used. ZIP/Release and component restoration unstarted.

**Exact next action:** add a focused public test for renderer-free nested
Prefab GO expansion using this exact fixture, then minimally connect source
GameObject/Transform occurrences through instance identity into hierarchy
realization, without names or native correspondence injection.
