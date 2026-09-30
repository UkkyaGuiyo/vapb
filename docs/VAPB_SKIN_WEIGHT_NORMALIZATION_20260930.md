# Skin Weight Numeric Normalization — 2026-09-30

## Authority and outcome

Starting feature branch remote: `36910d5f8a4a496e7a547a248a2fd7a95730c8c5`.
**GOAL_VERIFIED for this bounded numeric investigation.** No production changes.
This does not declare full Skin parity or zero deformation error.
Blender 5.2.1 LTS; Unity 2022.3.22f1; triangle-only Generic Skin, production
preprocessing policy Custom/minBoneWeight=0/maxBonesPerVertex=255.
Existing triangle staging, tiny-weight retention, Finalizers and raw comparator remain intact.

## OBSERVED

20 first-party controls, 60 control points, 183 positive influences. Controls cover
2/3/4 influences, exact unit sums, binary-awkward sums, under/over sums, adjacent
float32 values near one, .0005 retained weights, Bone assignment permutations,
and independently generated seed-930/9302/9303 counterexamples.

- B0 authored Blender float32 -> B1 actual disposable production export Mesh:
  183/183 unchanged; source restored/unchanged after export and pose measurement.
- B1 -> actual FBX Cluster doubles: 183/183 exact copies; no normalization.
- Unity GetAllBoneWeights: all 183 positive influences retained. First and forced
  repeated import produce identical Bone-bound float32 bits. Console errors 0,
  warnings 0 for the observed probe interval; input FBX SHA unchanged.
- Each influence has explicit CP metadata and Bone custom-property receipts.
  CP UV labels are carried through the actual FBX graph; native Unity vertices
  are joined by those labels. Bone names, array position and candidate count
  are not matching evidence. Capture fails on identity conflicts.
- Near-one sums from exact stored values: below 0.9999999701976776, exactly 1,
  above 1.0000000596046448. Accumulating these in float32 can give exactly 1.
- Raw values and Unity values differ even when all influences survive. Under/over
  controls intentionally normalize substantially (public maximum raw/native ULP
  23,108,010); these are not all one-ULP noise.

[Public numeric capture](../tests/unity_small_weight_probe/numeric_measurements.json)
contains all 60 B0/B1 rows, raw Cluster graph/float64 hex/bits, all first/repeated
Unity rows with float32 bits/order/sums, actual rest/posed evaluated positions,
and private aggregate counts only. Private raw tables stay outside Git.

## DERIVED — exact output model

Each operation below rounds to IEEE float32, round-to-nearest ties-to-even:

1. q_i = float32(raw FBX weight_i).
2. s1 = sequential float32 accumulation of q sorted by descending weight.
3. p_i = float32(q_i / s1), retaining its Bone identity.
4. s2 = sequential float32 accumulation of p sorted descending.
5. expected_i = float32(p_i * float32(1 / s2)).

This M5 is an experimentally equivalent numeric model, **not a claim about
Unity's internal algorithm**. Only documented public APIs and captured FBX bytes
were used. Sorting participates in the numeric result: identity-bound sensitive
permutations reject original-order accumulation; two-pass controls reject all
single-pass candidates. Equal weights do not introduce an identity tie-breaker.

| Model | Exact imported float32 bits |
| --- | --- |
| M0_float32 | 123 / 183 |
| M1_double_normalize | 153 / 183 |
| M2_float_divide | 126 / 183 |
| M3_quantize_double_normalize | 153 / 183 |
| M4_sorted_float_divide | 156 / 183 |
| M4_sorted_float_reciprocal | 147 / 183 |
| M5_divide_then_reciprocal | 183 / 183 |

M1 and M3 coincide here because the raw doubles are exact float32 values.
M0 plain quantization, M1/M3 double normalization, M2 original-order float32
normalization and both single-pass sorted variants are rejected as global models.
M5 expected-vs-actual maximum ULP = 0 on public and bounded real captures.
Root-cause class: **CASE C — Unity renormalization**, including float representation.
It is neither Blender exporter normalization nor plain float storage alone.

## REAL bounded classification

Counts use unique authoritative CP/Bone influences, not duplicated native split
vertices. A = B0 differs from F; B = B0 equals F but F differs from U;
C = both boundaries change; unexplained = no exact M5 explanation.

| Anonymous case | CP | Influences | B0->F exact / changed | F->U changed | A / B / C | M5 exact / unexplained | max raw F->U ULP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 288 | 626 | 626 / 0 | 54 | 0 / 54 / 0 | 626 / 0 | 2 |
| 2 | 2360 | 6010 | 6010 / 0 | 948 | 0 / 948 / 0 | 6010 / 0 | 4 |

Total: 6,636 explained, 1,002 raw-changed, 0 unexplained, 0 missing positive
influences. Max B0->F absolute/ULP error 0; max raw F->U absolute error
1.1920928955078125e-7. Same exact-revision FBX/native captures from the prior
bounded mission were re-read and hash-validated; no private asset was modified.
B1 exactness is directly measured by public staging; existing private B0/F equality
is measured, not a retrospective direct capture of every private B1 object.

## Deformation consequence

Blender's actual evaluated Armature normalizes group ratios, while its stored
vertex-group values remain unchanged. Under-sum .2/.3 moves approximately .2m,
not the .1m unnormalized weighted translation; over-sum controls corroborate this.
Independent CPU calculations use captured public bone matrices/bindposes and
float64 arithmetic. Unity reference is actual BakeMesh(true) + TransformPoint.
Bones move by .125/.25/.375/.5m; Unity/Blender X handedness is aligned explicitly.

Maximum measured distances across all 60 CP, in metres:

| Comparison | max metres |
| --- | --- |
| B0_normalized_F_normalized_CPU | 0 |
| F_normalized_U_CPU | 1.2102460866803e-08 |
| U_CPU_Unity_BakeMesh | 5.9607090818758479e-08 |
| Blender_evaluated_B0_CPU | 3.6137122294555013e-08 |
| Blender_Unity_evaluated | 1.1920928955078125e-07 |
| F_normalized_U_CPU_position | 4.2782396736384953e-08 |
| U_CPU_Unity_BakeMesh_position | 1.4081841870350331e-07 |

Entries without `_position` compare displacement vectors; position entries compare
rest and posed world positions. Distinct quantities are retained separately.
B0/F normalized CPU representations coincide. Unity renormalization changes
finite float32 values and measured deformation; no general visual-harmlessness,
all-pose equivalence or zero error claim follows from these small magnitudes.

## COMPARATOR CHANGE

`tests/weight_numeric_models.py` provides diagnostic `representation_compare`:
AUTHORED, STAGED, FBX_CANONICAL, UNITY_EXPECTED and UNITY_ACTUAL remain separate.
Raw changes stay visible. Expected and actual Unity bits must match exactly;
a one-ULP injected deviation is RED. Wrong Bone identity, different Unity version,
non-float32 raw context and unsupported influence count reject fail-closed.
Measured scope is Unity 2022.3.22f1 with 1..4 positive float32-origin influences;
The second bounded real capture includes 304 one-influence CP with bitwise-exact
model results; public controls independently cover 2..4. No epsilon or ULP
acceptance threshold is added.
The old total raw Skin comparator is **still RED** and is not overridden.

## Reproduction and engineering validation

From repository parent:

```text
python -m unittest discover -s unitypackage_blender_importer/tests -t . -p "test_*.py" -q
```

496 PASS (492 existing + 4 added). Without `-t .`, relative-import tests are loaded
outside package context and error; that invocation is not the correct baseline.
`python -m compileall -q blender unity operators ui export validation tests` PASS.

Blender factory/background with `--python-exit-code 1`:

```text
--python tests/blender_weight_normalization_fixture.py -- <new-external-output>
--python tests/blender_triangle_staging_test.py -- <external-output.fbx>
--python tests/blender_skin_package_test.py -- <external-synthetic-input-folder> --small-weights
```

Run `WeightNumericProbe.Run` in a disposable fresh Unity 2022.3.22f1 project.
Copy Ladder.fbx/Source.json to its root, the diagnostic probe to Assets/Editor,
and existing first-party VapbSkinWeightImporter.cs to Assets/VAPBExport/Editor.
Animation/JSON/image-conversion Unity modules are enabled. Script compiles;
version, hash, Bone/CP receipts gate capture; first/repeated imports PASS.

Current fresh packaged Skin regression: Blender export PASS; Unity explicit exit
0 and result pass=true, 54 vertices / 2 Bones, .0005 retained, Bone identities,
Material, deformation, source Model/unrelated state unchanged, repeated Apply,
invalid mapping rejected and rollback PASS. Triangle staging actual regression:
Skin, Shape, UV, Material, Export IDs, shared Mesh, source success preservation,
injected export failure rollback and save/reopen PASS.

## UNKNOWN / retained RED

- Internal Unity implementation and other Unity versions are unproven.
- More than four influences, arbitrary non-float32 FBX weights, extreme/subnormal
  distributions and all rig/pose deformation equivalence are outside measured scope.
- Raw Skin value equality remains RED; measured deformation differences are nonzero.
- Normal differences, tangent unknown and import-preview nonplanar differences
  are separate prior boundaries, not repaired by this investigation.
- Broad Unity/VRC restoration and Blender import changes were not undertaken.

## PRODUCTION CHANGE

NONE. Only first-party diagnostic fixtures/probes, pure numeric model tests,
raw-reader extraction and evidence documentation changed. No third-party source copy. One independent read-only scope review PASS;
changed-file private identity/path/credential-pattern scan: zero matches.
Official context: [Blender weight normalization](https://docs.staging.blender.org/manual/en/latest/sculpt_paint/weight_paint/introduction.html),
[Unity GetAllBoneWeights](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetAllBoneWeights.html),
[Unity SetBoneWeights](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.SetBoneWeights.html).
Actual bytes and public API observations, rather than manual precision claims,
are the acceptance evidence.

**Exact next action:** connect the bounded bitwise numeric diagnostic to the
existing full Skin parity report, retaining raw numeric RED and deformation
measurements separately from expected Unity representation.


## Integrated full Skin parity report — 2026-09-30

Starting remote `e8f227afbca3c210c41f2dfa4dd86dae2caa71c9`.
The existing `tests/blender_geometry_abcd_compare.py:d_identity_metrics` now
consumes the exact representation comparator. Existing public/real aggregate
experiment callers use this same entry point. The numeric real-evidence adapter
also stores the **full** entry-point result, including the unchanged legacy
Shape and Skin-binding verdicts. It is not a competing truth system.

`skin_report` separates these facts:

| Dimension | Public | Bounded real |
| --- | --- | --- |
| Export Mesh/CP/Bone/influence associations | EXACT | EXACT / EXACT |
| Positive influence retention | EXACT, missing 0 | EXACT, missing 0 |
| Raw FBX/Unity values | RAW_NUMERIC_DIFFERENCE, 60 changed | RAW_NUMERIC_DIFFERENCE, 54 + 948 changed |
| Expected Unity representation | EXACT, 183 / 183, 0 ULP | EXACT, 626 + 6010 / 6636, 0 ULP |
| Actual deformation measurement | MEASURED_NONZERO | MEASURED_NONZERO / MEASURED_NONZERO |

Identity scope is explicitly `EXPORTED_MESH_CP_BONE_INFLUENCE_ASSOCIATIONS`.
**Source Renderer owner is UNMEASURED by these export captures**; this result does
not replace the separate Hierarchy/Renderer-occurrence comparator. Private B1
was not directly recaptured; its `staging` is UNMEASURED and STAGED numeric rows
are null, rather than inferred. Public B1 remains the measured exact stage.

Before representation acceptance, the full report checks actual FBX SHA against
export and Unity capture revisions, Unity version, exact GUID/hash preprocessing
policy, public API Mesh GUID/local ID, CP labels/coverage/split consistency,
unique Bone claims and positive influence associations. It rejects missing or
unexpected influences, duplicate claims, invalid/stale context and unsupported
numeric scope. A 1-ULP expected/actual difference is NUMERIC_MISMATCH. No fallback
to epsilon, weight mutation, FBX rewrite or Unity patch is added.

The old `skin_bone_weight_binding` is unchanged: **both real cases still report
SKIN_BINDING_MISMATCH**. The new fields explain those REDs without overwriting
them. Raw values and expected Unity values remain independently available per
CP/Bone; private numeric rows are external, not part of committed evidence.

Deformation is never inferred from representation. The public controlled-pose
Blender/Unity displacement maximum remains 1.1920928955078125e-7m. In the two real
existing-pose captures, Blender/Unity evaluated **position** maxima are
1.3486690062364894e-6m and 1.8098327157498704e-6m; CPU/BakeMesh position maxima
are 6.016545663244253e-7m and 5.994014085373077e-7m. These are different measurements
and poses, not a worsening of the public controlled-pose metric or a general
all-pose equivalence claim. Metric provenance is retained in each report.
Absent deformation evidence stays UNMEASURED even with exact representation.

`overall_supported_transport = NOT_ASSESSED_PRODUCT_POLICY` explicitly means this
report contains facts only and makes no product-level success decision. No
PRODUCT_SPEC change or new definition of successful Skin transport was made.
A future promotion to supported transport would require a separately authorized
policy decision; this reporting-only mission does not require one.

Acceptance A–H: normal M5 / 1-ULP mutation / swapped Bone / missing influence /
unsupported Unity / >4 influences / stale hash / raw RED + representation EXACT
all covered, plus duplicate claims, unexpected Bone, unresolved CP, changed
staging, missing policy/context, non-float32 origin and unmeasured deformation.
9 integration tests added. Python full suite 505 PASS; compileall PASS. Actual
Blender Skin Package and triangle regression PASS, including tiny weights, Skin,
Shape, UV/Material/IDs, source preservation, injected failure rollback and
save/reopen. Fresh Unity 2022.3.22f1 package regression PASS: 54 vertices, two
Bones, retention, Material, deformation, repeated Apply and invalid mapping.

Exact-revision first **and repeated** native snapshots were reprocessed through
the full entry point: public 183 and real 626 + 6010 bitwise exact each time.
Fresh Unity package runtime was rerun; unrelated heavy campaigns were not.
One independent read-only scope review PASS. Production changes NONE.

[Sanitized integrated report](../tests/unity_small_weight_probe/skin_parity_measurements.json)
contains public and real aggregate counts/metrics only. Original private identity,
raw weights, asset names and paths are absent.

The preceding 2026-09-30 integration section records the prior policy state;
`NOT_ASSESSED_PRODUCT_POLICY` there is historical, superseded by the contract below.


## Product-authorized Skin transport acceptance — 2026-10-01

The user approved the [design](superpowers/specs/2026-10-01-skin-transport-acceptance-design.md)
and [four-task plan](superpowers/plans/2026-10-01-skin-transport-acceptance.md).
`PRODUCT_SPEC.md` now defines the normative Skin Transport Acceptance Contract.
`overall_supported_transport` is `PASS / RED / UNSUPPORTED`. The integrated
report exposes `BITWISE_EXACT`; lower-level `representation_compare()` retains
its internal `EXACT` label. Neither the numeric model nor production data changed.

The pure reducer requires identity and retention EXACT, representation
BITWISE_EXACT, unexplained=0, reason=NONE and a positive influence population.
Unsupported version/numeric scope/incomplete context yields UNSUPPORTED;
stale/ambiguous identity, missing/unexpected influences and unexplained output
are RED. Raw numeric parity and deformation are independent of this reducer.
Known raw RED and MEASURED_NONZERO remain visible. UNMEASURED deformation alone
also does not block this bounded transport verdict. Source Renderer ownership
remains UNMEASURED here and must come from independent occurrence proof where
needed. PASS makes no arbitrary-pose, visual-harmlessness or whole-Avatar claim.

Actual first/repeated evidence refresh through the full entry point: public183
and real626+6010 BITWISE_EXACT, transport PASS, missing0, unexplained0, max
expected/actual ULP0. Raw changed60/public and1002/real remain unchanged; the
legacy raw real RED remains in both cases. Deformation metrics and source
Renderer owner UNMEASURED are preserved. No private raw rows enter Git.

Task4 bounded regression: Python510 PASS; final reviewed suite511 PASS, compileall PASS; actual Blender Skin
Package, tiny weights, triangle staging, Shape/UV/Material/IDs, source success
preservation, injected failure rollback and save/reopen PASS. Fresh public Unity
2022.3.22f1: 54 vertices/two Bones, repeated Apply, invalid mapping, source-model
and unrelated-state preservation PASS. Fresh normalization source and fresh
Unity numeric first/repeated imports were also run:183/183 BITWISE_EXACT each,
transport PASS, errors0/warnings0, measured displacement delta1.1920928955078125e-7m.
Final whole-branch review: Critical0, Important1 fixed, deferred minors0.
Smallest/largest float32 subnormal controls demonstrated an unsupported-scope
false PASS before the fix. The report now rejects positive subnormal raw weights
as UNSUPPORTED, without changing the numeric model or production data. Focused19
and full511 tests PASS; actual bounded real reports remain PASS/BITWISE_EXACT.
No weight mutation, FBX rewrite, importer-policy change or epsilon window is added.

**Next exact action after policy closure:** combine the approved Skin transport
verdict with the existing independent Hierarchy/Renderer-occurrence evidence in
a bounded round-trip acceptance report, retaining deformation and remaining
Geometry/Normal/Tangent boundaries separately.
