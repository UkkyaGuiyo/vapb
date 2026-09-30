# Small Bone Weight Import Fidelity — 2026-09-30

## Request and acceptance boundary

Original request: locate the Blender → raw FBX → Unity Mesh small-weight loss,
characterize settings/lifecycle/renormalization/deformation, then transport a
proven documented configuration into generated Skin packages. Triangle staging,
Hierarchy, Material/Shader production and broad VRC restoration are out of scope.
Starting remote HEAD: `d3e65b23d10b9dabe712d2a30ebed5d6f3f109fa`.

**GOAL_VERIFIED for small positive influence retention in the measured generated
Skin package route. Full real Skin numeric parity remains RED.** No post-import
Mesh reconstruction was needed or implemented. Source geometry lineage is not a
new export prerequisite; Blender final state remains Geometry authority.

## OBSERVED: independent source and native data

First-party triangle-only Generic Skin: exactly two Bones, 14 weight thresholds,
three independent CPs per threshold, one Mesh, no Shape/Material complexity.
An authored CP UV channel and Bone/Mesh custom-property labels bind raw FBX
Cluster edges to public Unity API observations. Original names and object order
are not correspondence evidence. Exact FBX SHA gates every observation.

Actual raw Cluster weights match Blender's authored float32 values on all 42 CPs.
The positive ladder is 1e-8, 1e-6, 1e-5, 1e-4, .00025, .0005, .0009,
.000999, .001, .001001, .0015, .005, .01; zero is an independent control.
Complementary weights are Blender float32 values of `1 - authored threshold`.
Their double-precision sums may differ slightly from one; this is retained in
the source evidence rather than replaced with ideal decimal values.

Unity 2022.3.22f1 actual `GetBonesPerVertex` / `GetAllBoneWeights`:

| Lifecycle | Requested min | Immediate setter / preprocess getter | Stored .meta after import | Post-import getter | Actual Mesh |
|---|---:|---:|---:|---:|---|
| Default / Standard / Custom default | .001 | .001 | .001 | .001 | Below .001 discarded |
| Setter → SaveAndReimport | 0, 1e-8, .0001, .0005, .000999 | Requested value | .001 | .001 | Below .001 discarded |
| Setter → write settings + force synchronous import | Same five values | Requested value | .001 | .001 | Below .001 discarded |
| Either post-import path | .001 / .001001 | Requested value | Requested value | Requested value | Corresponding threshold applied |
| OnPreprocessModel, first import | 0 / 1e-8 | Requested value | Requested value | .001 | All 42 CPs exact float32 weights |
| OnPreprocessModel, first import | .0001 / .0005 / .000999 | Requested value | Requested value | .001 | Requested threshold actually applied |
| OnPreprocessModel | .001 / .001001 | Requested value | Requested value | Requested value | Corresponding threshold applied |
| Copied .meta with Custom/min=0, first import | 0 in metadata | .001 at preprocessing | .001 | .001 | Small weights discarded |
| Explicit preprocess=0 on reimport | 0 | 0 | 0 | .001 | Small weights retained |

The threshold is inclusive in this control: .000999 is lost at default .001;
.001 and .001001 survive. Request .001001 also trims .001. These are measured
raw float32 values, not Inspector rounding.

## DERIVED: boundary and root cause

- Blender → FBX: no loss in the public ladder.
- FBX → ModelImporter realization → imported Mesh: trimming occurs here.
- **CASE B — UNITY CONFIGURABLE.** A universal .001 native-import hard floor is
  refuted by first-preprocess and reimport-preprocess controls.
- Setter acceptance, serialized state and post-import getter are distinct states.
  The getter cannot be used as proof of the threshold actually used for import.
- A setter after import and .meta-only transport are insufficient in the tested
  path. Setting Custom/min=0 during every documented model preprocessing is effective.
- Below-threshold removal changes the retained channel: .0005/.9995 becomes
  one channel of 1.0. Threshold-adjacent discarded channels behave similarly.
  Retained channels in the zero-preprocess public control match raw float32 bits.
- Imported influence entries are descending by weight; explicit Bone labels
  prove bindings independently of list order. The public Bone index-to-label
  mapping is unchanged across this matrix.

## Observable deformation control

Move the low-weight Bone by .5m on an instantiated synthetic model. Expected CPU
skinning uses raw Cluster weights, actual corresponding Bone matrices and native
bindposes. `BakeMesh(..., true)` is measured in the same world frame.

At .0005, trimming produces a measured ~.000250816m discrepancy; preprocess=0
and the production helper produce zero discrepancy at this controlled CP.
Classification: **OBSERVABLE_DEFORMATION_LOSS** in this synthetic control.
This establishes a consequence, not a claim about typical avatar visual severity.
An initial diagnostic used scale-excluding BakeMesh and was rejected for frame
mismatch; the scale-correct measurement above is the acceptance evidence.

## Minimal production change

Only generated Skin tasks opt in. Export packages contain:

- `SkinWeightPolicy_<generated GUID>.json`: schema version, exact generated
  model GUID and SHA-256. No original source model is opted in.
- First-party MIT `VapbSkinWeightImporter.cs`: public AssetPostprocessor verifies
  GUID and bytes, then sets Custom/maxBonesPerVertex=255/minBoneWeight=0 during
  every model preprocessing. Revision mismatch explicitly rejects import.

The helper runs after the default-order import callbacks. Arbitrary third-party
callbacks which subsequently replace settings are outside the measured scope.
No source Mesh patch, alternate Mesh asset, weight amplification, threshold
guessing or Unity-internal API is used. The existing Finalizer's model reimport
provides the application point when scripts compile after package import.
Finalizer source code and triangle staging remain unchanged.

## PUBLIC RED → GREEN and negative controls

Actual production helper on the same hashed FBX: no-policy 18/42 exact CPs;
policy 42/42; repeated policy import 42/42. Stale policy SHA is rejected at actual
Unity import; restored valid policy again retains 42/42.

Comparator negatives reject changed source weight, swapped Bone/Cluster labels,
corrupted source CP mapping, swapped imported Bone index, changed imported weight,
stale FBX hash, wrong Mesh label and corrupted imported CP correspondence.
Threshold-adjacent values are independent runtime observations.

Actual Blender operator produces a Skin UnityPackage containing both policy and
helper. Fresh Unity Finalizer PASS: 54 vertices retain exact .0005 float32 root
weight; Bone identities, Material, changed topology/weights, deformation,
source-model bytes, unrelated state, repeated Apply and invalid mapping rejection
all PASS. Source editing scene is retained and source save/reopen succeeds.

## Bounded real recheck — aggregates only

Same two prior RED cases, exact previously generated D1 bytes, new external Unity
projects; no commercial input or source project changed.

| Case | No-policy positive influences omitted | Policy omitted | Reimport omitted | Max raw/native weight difference after policy |
|---|---:|---:|---:|---:|
| First bounded case | 26 | 0 | 0 | 1.1920928955078125e-7 |
| Second bounded case | 684 | 0 | 0 | 1.1920928955078125e-7 |

Both retain all previously missing positive influences. Each bounded case reports
three warnings and zero errors across the three captured imports; warning text
remains private/unclassified. Existing rounded total
Skin-binding comparator remains **SKIN_BINDING_MISMATCH**, including differences
between Blender pre-export weights, FBX normalization and Unity float storage.
No tolerance was relaxed and no total Skin parity GREEN is claimed. Supported
Shape result remains EXACT / NOT_APPLICABLE. Raw CP UV, explicit temporary Bone
labels, exact FBX SHA and Cluster graph establish correspondence. Repeated
diagnostics first disable the prior policy, preventing a contaminated no-policy RED.

## Verification and UNKNOWN

- Python 492 PASS, compileall PASS.
- Triangle staging regression PASS: Skin/Shape/UV/Material/IDs, source invariants,
  injected export failure rollback and separate source save/reopen.
- Actual Skin package export, source preservation/save-reopen, fresh Finalizer
  and idempotence PASS. One bounded read-only scope review PASS.
- Historical Hierarchy 1,274 / Shape identity 171 totals are not new full runs.
- Complete Unity internal reason for the getter/serialization lifecycle behavior
  remains UNKNOWN; public APIs prove the effective configuration independently.
- Arbitrarily tiny/different rigs/other Unity versions or third-party importer
  callback interference are not proven. Small-weight retention does not solve
  remaining weight normalization, normal/tangent or source Import-preview REDs.

## Reproduction

Blender CLI `tests/blender_small_weight_fixture.py -- <new external source dir>`.
Create isolated Unity 2022.3.22f1 project with native animation/json modules,
copy `WeightMarker.cs` and `Editor/SmallWeightProbe.cs`, and place generated
`Ladder.fbx` and `Source.json` at its root. Execute `SmallWeightProbe.Run`.
For production control also install the actual first-party Skin importer helper,
then execute `ProductionControl` and `PolicyNegative`. Keep each project isolated.
Unity probes explicitly exit nonzero on failure; acceptance also checks the
written result and source hashes, never process exit alone.

[Public source and measured matrix](../tests/unity_small_weight_probe/measurements.json).

Official APIs used: [minBoneWeight](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-minBoneWeight.html),
[OnPreprocessModel](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetPostprocessor.OnPreprocessModel.html).
Documentation formed experiments; imported Mesh data established the conclusions.

## Exact next action

Isolate the remaining bounded Skin numeric mismatch into a public normalization
control, separating Blender→raw FBX normalization from raw FBX→Unity float storage.
