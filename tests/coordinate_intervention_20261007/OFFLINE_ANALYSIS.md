# Exploratory decomposition of the seven existing observations

The original direct prediction `P_Unity = P_Blender` remains rejected: 126 corner deltas exceeded the fixed `1e-4` tolerance. Its capture and comparison files are immutable inputs to this analysis. No new Unity run or fixture was created for the analysis.

GPT-6 Astra medium proposed this decomposition after reading all seven observations. GPT-6 LUNA low implements only a diagnostic script and pure tests in this existing experiment folder. The candidate is inferred from the observed data; none of these seven cases is a holdout.

## Fixed exploratory candidate

Use column vectors and row-major serialized matrices. Define a world conversion `C(x,y,z) = (-x,z,-y)` and local conversion `D_case = hom(s_case * diag(-1,1,1))`, where `s_case = 0.01` for the authored unit condition and `1` for the other conditions. Record the raw FBX `UnitScaleFactor` ratio separately; do not estimate a new scale from residuals.

Evaluate three residuals independently for every authored UV corner:

```text
local vertex:  rV = V_Unity - D_case * V_Blender
root matrix:   RW = W_Unity * D_case - C * W_Blender
world point:   rP = W_Unity * V_Unity - C * W_Blender * V_Blender
```

The local and world frames differ. `W_Unity = C * W_Blender * inverse(C)` is not the candidate being tested. In the unit observation, Blender retains baseline local vertices and places approximately 0.01 in its root matrix; Unity places approximately 0.01 in its local vertices and retains its baseline root matrix scale. A local reflection without that unit factor does not explain both representations.

Compare the axis condition to baseline within each tool, and the unit world points to 0.01 times baseline within each tool. Translation, rotation, positive nonuniform scale, and negative scale use the same candidate without per-case adjustments. Matrix residuals compare observed matrices; they do not independently prove that raw authored TRS was preserved.

## Unproven boundaries

All seven observations have one root hierarchy row. They provide no nontrivial parent-child importer evidence. Pure tests of noncommuting matrices and composed parent-child transforms verify arithmetic only. A future runtime holdout must freeze this candidate, the tolerance, tag/receipt requirements, and rejection conditions before creating an unseen fixture. An unseen asymmetric geometry with noncommuting parent-child TRS combined with a different unit scale can distinguish remaining explanations; it has not been authored or executed here. Existing observations cannot be relabeled as held out.

Face membership and winding are separate properties. A reflection changes the ordered area-vector relation by `det(A) * inverse(A).transpose()`, and importer corner permutations contribute their own parity. This diagnostic does not adopt a winding correction or validate normal transport.

The existing face result connects authored UV tags to fixture logical material identities. Unity records imported FBX Material GUID/local file IDs, while logical identities are joined to raw FBX Material UIDs by unique fixture names. This does not independently connect a package Prefab's external Material GUID/fileID to native imported submesh faces. The production binding seam still carries `consumer_slot_index` from serialized Renderer records and assigns `plan[index]` to Blender slots. A coordinate candidate alone cannot supply the missing material correspondence. No slot swap, name/count fallback, mandatory source Project, or product contract change follows from this analysis.

The exploration must retain an exploratory status even when residuals are small. The fixed comparator remains unchanged and the product material-binding seam remains unproven.

## Observed exploratory residuals

The corrected report is `../evidence/coordinate_intervention_20261007/offline-analysis-01/report-authored-unit.json`, SHA256 `5efe96bc62561324111779516fcf75c9e1e2cf5af2bda927d24bdfc1f8010453`. It retains `EXPLORATORY_DATA_DERIVED_CANDIDATE_NO_HOLDOUT`, `holdout_validated: false`, and the original comparator's UNPROVEN status with `mapping: null`.

| Case | Maximum local vertex residual | Maximum matrix entry residual | Maximum world point component residual |
|---|---:|---:|---:|
| baseline | 0 | 5.960464478e-8 | 1.746037086e-7 |
| axis_only | 0 | 1.192092896e-7 | 3.933906498e-7 |
| unit_only | 1.192092897e-9 | 4.371137630e-10 | 1.766153390e-9 |
| translation_only | 0 | 5.960464478e-8 | 1.746037084e-7 |
| rotation_only | 0 | 7.450580597e-8 | 1.436471955e-7 |
| positive_nonuniform_scale_only | 0 | 1.192092896e-7 | 2.580691585e-7 |
| negative_scale_only | 0 | 5.960464478e-8 | 1.441603208e-7 |

Within-tool axis-versus-baseline world residuals are at most `3.111785027e-7` (Blender) and `3.415346086e-7` (Unity). Unit-world-versus-0.01-baseline residuals are at most `4.269185283e-10` and `1.192092897e-9`, respectively. These descriptive residuals support the candidate on the same observed data; they do not establish importer causality or change the original acceptance decision. Five new pure tests and the thirteen existing tests pass together (18 total).

## Artifact provenance gap

The first provisional offline report used the raw metadata ratio in `D_case`. It was generated and then deleted during the correction to the authored ratio; its original bytes and hash were not retained. It cannot be recovered as original evidence and is not part of the corrected report's lineage. No reconstructed report is presented as that missing original. The corrected report named and hashed above was created with exclusive-create output and is retained.

The four original pinned inputs (manifest, Blender capture, Unity capture, fixed comparison) were independently rehashed after analysis and match their original receipts. This proves those inputs remain intact; it does not prove every exploratory output was preserved. Development also included a corrected synthetic test frame-sign expectation and failed diagnostic attempts involving local variable shadowing and a manifest lookup, before the successful corrected output. Those development failures are reported from the implementer's account; original failure logs were not retained.

The reporter requires those exact input bytes. A checkout that converts JSON line endings will fail the hash gate; it does not silently normalize a receipt or substitute another capture. Its exclusive-create output refuses to replace an existing report.
