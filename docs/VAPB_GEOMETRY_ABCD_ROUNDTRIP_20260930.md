# Geometry A/B/C/D round-trip experiment — 2026-09-30

Status: **GOAL_VERIFIED for the bounded characterization experiment**.
This is not a claim that Geometry, all export attributes, or VAPB are complete.
Production Geometry code and PRODUCT_SPEC are unchanged. Starting checkpoint:
`ae178b5c1f0e39162ef384147bf86c12e3f519cc`.

## Authority and scope

The approved 2026-09-28 product model already makes Blender final geometry the
export authority. Source identity and export identity are separate; recreating
Unity's source Mesh identity or its original opaque n-gon diagonal is not a
normal export requirement. This experiment tests that existing contract rather
than inventing a replacement. Import preview fidelity is a separate question.

- A: exact raw FBX, Unity **2022.3.22f1** public API observation.
- B: the same raw FBX, Blender **5.2.1** native importer.
- C: A through the official Unity **com.unity.formats.fbx 5.1.1** binary exporter,
  then Blender. Other official options retain defaults, including LocalCentered.
- D0: B through the existing VAPB FBX preset, then fresh Unity import.
- D1: B's `calc_loop_triangles` frozen in a disposable export copy, then the
  same preset and fresh Unity import. No Unity-selected diagonal is injected.

All Shape weights are fixed zero. Frame geometry is measured separately.
Diagnostic UV carries explicit source CP IDs; D also uses export labels assigned
to actual native Bone/Shape handles. Labels are not inferred from original names.
Output FBX hashes gate each post-import comparison. Source scenes/files remain
unchanged. Position/surface threshold remains **3e-5**, the existing diagnostic
threshold. Winding includes the existing handedness conversion; multiplicity and
face-to-material-slot partitions are retained. Finite surface samples do not
constitute a continuous-surface proof. Attribute distances do not establish
identity or add a new acceptance tolerance.

Exact public artifact and observation hashes, counts, distances and verdicts:
[public_measurements.json](../tests/unity_geometry_abcd_probe/public_measurements.json).
Raw/private reports are external to Git.

## OBSERVED: public matrix

All five A/B/C/D imports executed. All final Unity capture methods completed
with zero errors and warnings. C is binary FBX from the official exporter.

| Public fixture | A vertices / triangles | B vertices / triangles | A vs B topology / surface | A vs C topology / surface | D0 topology / surface | D1 topology / surface |
|---|---:|---:|---|---|---|---|
| Nonplanar n-gons | 30 / 18 | 30 / 18 | RED / RED | EXACT / RED | RED / RED | EXACT / sampled EXACT |
| Known-GREEN three-Shape Skin | 24 / 12 | 8 / 12 | EXACT / sampled EXACT | EXACT / RED | EXACT / sampled EXACT | EXACT / sampled EXACT |
| Planar n-gon | 5 / 3 | 5 / 3 | RED / sampled EXACT | EXACT / RED | RED / sampled EXACT | EXACT / sampled EXACT |
| Concave n-gon | 5 / 3 | 5 / 3 | EXACT / sampled EXACT | EXACT / RED | EXACT / sampled EXACT | EXACT / sampled EXACT |
| Triangle-only | 6 / 2 | 4 / 2 | EXACT / sampled EXACT | EXACT / RED | EXACT / sampled EXACT | EXACT / sampled EXACT |

Vertex counts differ legitimately through Unity splits; counts are not identity
evidence. Explicit CP correspondence proves vertex positions for A/B and all D.
All five D1 cases preserve triangle connectivity, winding, material-slot
partitions and sampled base surface. The measured nonplanar A/B maximum surface
distance is **0.0654085**; D0 repeats that discrepancy. Nonplanar D1 base distance
is at most **2.54e-7**, and its independently baked surface is at most **2.65e-7**.
Planar diagonal changes have no sampled surface difference at the unchanged
threshold. Neither kind of changed diagonal causes Unity import rejection.

For the public Skin/Shape fixture, both D variants retain three independently
transported Shape frames: maximum delta error **8.17e-8**, numeric weights and
their explicit Bone-label bindings EXACT. Public D bind-pose BakeMesh positions
agree with independent CPU weighted bindpose positions within **1.864e-7**.
Public nonplanar D Skin bindings are also EXACT. Static controls have no Skin or
Shape claim. Public D UV sets are retained. D1 nonplanar rounded normal sets
report a difference, while measured normal-vector distance is **2.33e-7**;
the rounded-set verdict is retained rather than silently relaxed.

Tangents are captured on the Unity side but not proven across every route.
Blender D0 warns that tangent space cannot be exported for faces above four
vertices. Marker-only UV is not evidence of meaningful texture tangent fidelity.

## OBSERVED: C is not universal truth

C transports Unity's realized triangle connectivity: **5/5 EXACT** in Blender.
It does not preserve the complete measured surface/transform state in these
default official exports. Static controls have maximum sampled surface distances
around **0.000691–0.000699**. The two Skin controls have additional large Blender
placement/scale discrepancies, around **181.56–190.61** sampled distance.

Reimporting the exact C FBX into Unity isolates this from B/D: mandatory Skin
controls retain their CP mapping and local positions (error at most **9.32e-10**)
but already change raw world positions by about **0.000315–0.000337**. Raw FBX
inspection records unchanged centimeter unit declarations and nearly unchanged
control-point arrays, while export changes model hierarchy and Euler transform
values. For example, the source rotation near -90 degrees becomes approximately
-89.9802. No fitted scale, guessed alignment or relaxed tolerance is applied.

The much larger C Blender discrepancy is a separate realization/transform
boundary; its complete skeleton/importer cause remains **UNKNOWN**. Original
Shape/Bone identity through C is not proven by frame counts or names. These
findings cannot establish that every manual Unity-to-Blender workflow is broken,
or that the conventional path universally conceals the original 20 REDs.

The initial official 4.2.1 API emitted ASCII FBX, which the native Blender reader
cannot use. Its format setting was internal. Only new isolated projects were
switched to the released 5.1.1 public `ExportModelOptions` binary API. One stale
package-cache compilation failure occurred during resolution; final fresh
invocations compiled and ran. Both trials remain in external evidence.
The official exporter is Unity Companion licensed; it and its Autodesk dependency
are Oracle tools, not redistributed VAPB code or production dependencies.

## OBSERVED: bounded real D

One previously EXACT Skin and three previously MISMATCH Skins were selected by
proven occurrence identity, with n-gon-heavy members included. Four cases/eight
imports were executed; private inputs, identities and raw reports remain outside
Git. All imports succeeded, zero errors, **two unclassified import warnings**.

| Measurement | D0 | D1 |
|---|---:|---:|
| CP world positions EXACT | 4/4 | 4/4 |
| Triangle connectivity EXACT | 1/4 | 4/4 |
| Sampled base surface EXACT | 3/4 | 4/4 |
| Baked vertex positions EXACT | 4/4 | 4/4 |
| Bone-label/weight bindings EXACT | 2/4 | 2/4 |
| Shape geometry | 2 measured EXACT; 2 N/A | 2 measured EXACT; 2 N/A |

The largest D0 surface discrepancy is about **0.000664**; D1 removes it. D1
normal-vector set distances include genuine differences of approximately
**0.0330** and **0.0184** on two cases; the other two are below **2.17e-7**.
Maximum observed UV-set distances reach **1.80e-6**; rounded UV verdicts remain
recorded as differences. This is not complete appearance or deformation parity.

The original false-scale `BakeMesh(false)` measurement produced very large
spurious distances. Existing repository knowledge requires `BakeMesh(true)` plus
`TransformPoint`; the corrected public API measurement agrees with independent
CPU skinning within **7.178e-7** across all eight private captures. Both readings
are retained. A measurement bug cannot be used to declare broken production Skin.

## OBSERVED: small-weight DATA_LOSS control

Two real cases lose positive Bone influences below the observed importer
threshold **0.001**. This is distinct from triangulation. A first-party public
three-vertex/two-Bone fixture reproduces it: **0.0005 is discarded**, while
**0.0015 and 0.25 remain**. The first fixture used Rig None and imported as a
static Mesh; it was rejected as evidence. A new exact revision using Generic Rig
reproduces the actual Skin RED.

Public `ModelImporter` controls attempted Standard/zero and Custom/zero, then a
bounded Custom/**1e-8** threshold, including explicit synchronous reimport.
Assigned/stored metadata values and actual post-import settings are different:
the lower value persists in metadata, but post-import getter reports **0.001**
and the influence remains absent. This is **not GREEN**. Original metadata bytes,
settings and input FBX hashes are restored. No corresponding private threshold
mutation was attempted because the public control did not prove retention.

[Unity minBoneWeight documentation](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-minBoneWeight.html)
documents trimming below the threshold. The complete cause of the observed
stored/runtime discrepancy is **UNKNOWN**; no production workaround is shipped.

## DERIVED / recommendation

1. **Import fidelity:** A/B nonplanar RED includes a real surface difference,
   not merely cosmetic diagonal identity. Preserve this diagnostic. Planar
   topology differences may be representation-dependent without measured surface
   loss. Do not erase all 20 original REDs or label them universally equivalent.
2. **Edit authority:** Blender final state remains authoritative under the
   existing product model. These results do not restore source Mesh lineage as
   an export requirement.
3. **Export fidelity:** leaving n-gons in an output FBX allows Unity to choose
   a different final surface. Exact Blender triangle freezing is justified by
   D0/D1 evidence, not by a fourth guess at Unity's opaque algorithm. D1 is an
   experimental staging implementation, not a deployed export fix.
4. **Fatality:** a different valid triangle connection does not cause observed
   Unity rejection. Classify nonplanar D0 as **VISUAL_SURFACE_DIFFERENCE**, and
   planar connection-only differences as representation-dependent at the measured
   scope. D1 base Geometry has **NO_FATAL_ERROR**, while small-weight trimming is
   separate **DATA_LOSS**. Normals/UV/tangents and full deformation still have limits.
5. **Conventional route:** official C writes explicit A triangles, reducing
   ambiguity at that boundary, but is not a universal preservation oracle.
   Default C surface/transform RED plus D1 base GREEN is bounded Case 3 evidence.
   Default D0 nonplanar RED is a separate unresolved export route.

## UNKNOWN / non-goals

No arbitrary pose/animation, complete Skin restoration, shader/rendering campaign,
all private corpus coverage, fourth triangulation algorithm, Unity mandatory
runtime, guessed normalization, production fix, main merge, tag or release.
Production Hierarchy **1,274 EXACT**, Shape identity **171 EXACT**, and original
Geometry **14 EXACT / 20 MISMATCH** remain the earlier committed measurements.

## Verification / exact next action

Repository-parent Python discovery: **484 PASS**; compileall: **PASS**.
The final real comparator ran under Blender with explicit nonzero Python-error
exit handling. Ten new metrics/negative controls cover explicit CP reorder, wrong
labels, missing markers, split-vertex disagreement, diagonal and winding REDs,
Shape delta/label corruption and wrong Bone bindings. Final read-only scope
review: **PASS — no unnecessary implementation found.** Publication scans found
zero tested private identities, local paths and credential patterns. The four
private report source-blend hashes match the unchanged original file.

**Next exact automatic action:** implement and verify explicit Blender-triangle
staging in the existing supported production export route using these public
D0 RED/D1 GREEN controls; retain separate Skin-weight and normal limitations.
Do not attempt to recover Unity's original n-gon diagonal.
