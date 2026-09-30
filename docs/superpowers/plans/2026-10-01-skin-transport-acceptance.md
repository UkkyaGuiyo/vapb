# Skin Transport Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the verified representation-aware Skin evidence into an explicit product-level supported Skin transport verdict without hiding raw numeric differences or nonzero deformation measurements.

**Architecture:** Keep the existing `skin_parity_report()` as the single evidence-producing path. Add one pure policy reducer that converts its already-separated dimensions into `PASS / RED / UNSUPPORTED`, then wire that verdict back into the same report. Preserve legacy raw Skin REDs and the lower-level numeric model unchanged. Document the acceptance contract in `PRODUCT_SPEC.md` and refresh the sanitized evidence/docs from the actual integrated report.

**Tech Stack:** Python 3, unittest, Blender 5.2.1 LTS test harness, Unity 2022.3.22f1 public API evidence, Markdown.

**Spec:** `docs/superpowers/specs/2026-10-01-skin-transport-acceptance-design.md`

## Global Constraints

- Blender final state remains the export authority.
- Unity representation acceptance is bounded to the proven Unity 2022.3.22f1 numeric context.
- No production Bone Weight mutation, FBX rewrite, importer-policy change, epsilon relaxation, or ULP tolerance window.
- Raw numeric differences remain visible and are not reclassified as raw equality.
- Deformation remains a separate measured dimension and may be `MEASURED_NONZERO` while supported Skin transport passes.
- A one-ULP expected/actual Unity representation difference is RED.
- Unsupported numeric/version/context inputs fail closed; no fallback approximation.
- Source Renderer-owner identity remains external to this Skin numeric acceptance and continues to come from the independent Hierarchy/occurrence proof where required.
- Private asset names, raw private weight tables, GUID/fileID inventories, paths, screenshots and commercial bytes must not enter Git.

## Review Focus

- Unsupported Unity version or numeric scope must yield `UNSUPPORTED`, never `PASS`; pin this in Task 1.
- Stale FBX/policy revision or unresolved identity must yield `RED`, not `UNSUPPORTED` or `PASS`; pin this in Task 1.
- `RAW_NUMERIC_DIFFERENCE + BITWISE_EXACT + MEASURED_NONZERO` must still produce supported transport `PASS`; pin this in Task 1.
- Missing positive influence or a 1-ULP representation mutation must produce `RED`; pin this in Task 1.
- `source_renderer_owner = UNMEASURED` must remain explicit and must not be silently promoted by the Skin report; pin this in Task 1 and document it in Task 2.

---

### Task 1: Add the Skin transport policy reducer and TDD coverage

**Files:**
- Modify: `tests/blender_geometry_abcd_compare.py:127-225`
- Modify: `tests/test_skin_parity_report.py:11-91`

**Interfaces:**
- Consumes: the existing `skin_report` dictionary fields `identity`, `influence_retention`, `raw_numeric`, `unity_representation`, `deformation`, `total_influences`, `unexplained_influences`, and `reason`.
- Produces: `supported_skin_transport_verdict(report: dict) -> str`, returning exactly `PASS`, `RED`, or `UNSUPPORTED`; `skin_parity_report(...)` stores that result in `overall_supported_transport`.
- Report terminology: the integrated Skin report exposes bitwise-success as `BITWISE_EXACT`; the lower-level `representation_compare()` may continue returning its existing `EXACT` value internally.

- [ ] **Step 1: Write failing policy tests in `tests/test_skin_parity_report.py`**

Add tests with these assertions:

```python
def test_supported_transport_passes_with_raw_difference_and_nonzero_deformation():
    b, o, c = self.fixture()
    r = self.report(b, o, c)
    self.assertEqual(r["raw_numeric"], "RAW_NUMERIC_DIFFERENCE")
    self.assertEqual(r["unity_representation"], "BITWISE_EXACT")
    self.assertEqual(r["deformation"]["status"], "MEASURED_NONZERO")
    self.assertEqual(r["source_renderer_owner"], "UNMEASURED")
    self.assertEqual(r["overall_supported_transport"], "PASS")

def test_one_ulp_and_missing_influence_make_supported_transport_red():
    # Reuse the existing 1-ULP and missing-influence mutations.
    # Assert overall_supported_transport == "RED" for each.

def test_stale_revision_and_swapped_bone_make_supported_transport_red():
    # Reuse existing stale hash and swapped Bone mutations.
    # Assert overall_supported_transport == "RED".

def test_unsupported_numeric_context_is_not_pass():
    # unsupported Unity version and >4 influences
    # assert overall_supported_transport == "UNSUPPORTED"

def test_unmeasured_deformation_does_not_block_supported_transport():
    b, o, c = self.fixture()
    c.pop("deformation")
    r = self.report(b, o, c)
    self.assertEqual(r["deformation"]["status"], "UNMEASURED")
    self.assertEqual(r["overall_supported_transport"], "PASS")
```

Also update the existing `test_raw_red_and_bitwise_exact_remain_independent` expectation from `NOT_ASSESSED_PRODUCT_POLICY` to the new policy semantics.

- [ ] **Step 2: Run the focused test and verify RED**

Run from the repository parent:

```bash
python -m unittest unitypackage_blender_importer.tests.test_skin_parity_report -q
```

Expected: FAIL because `overall_supported_transport` is still `NOT_ASSESSED_PRODUCT_POLICY` and the integrated report still says `EXACT` rather than `BITWISE_EXACT`.

- [ ] **Step 3: Implement `supported_skin_transport_verdict(report: dict) -> str` in `tests/blender_geometry_abcd_compare.py`**

Place it immediately before `skin_parity_report()`.

Use this exact policy:

- Return `UNSUPPORTED` when `reason` is one of:
  - `NUMERIC_CONTEXT_MISSING`
  - `NUMERIC_CONTEXT_INCOMPLETE`
  - `UNSUPPORTED_REPRESENTATION`
  - `UNPROVEN_NUMERIC_SCOPE`
  - `UNPROVEN_WEIGHT_REPRESENTATION`
- Return `RED` for any other non-`NONE` reason, including stale revision, unresolved identity, missing/unexpected influences, staging/canonical changes and Bone-set mismatches.
- Return `UNSUPPORTED` if `total_influences <= 0`.
- Return `PASS` only when all are true:
  - `identity == "EXACT"`
  - `influence_retention == "EXACT"`
  - `unity_representation == "BITWISE_EXACT"`
  - `unexplained_influences == 0`
  - `reason == "NONE"`
- Otherwise return `RED`.
- Do not consult `raw_numeric` or `deformation.status` when determining `PASS`.

In `skin_parity_report()`:

- change only the integrated report's exact-success label from `EXACT` to `BITWISE_EXACT`;
- leave `tests/weight_numeric_models.py:representation_compare()` unchanged;
- after the existing `try/except`, set:
  `result["overall_supported_transport"] = supported_skin_transport_verdict(result)`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
python -m unittest unitypackage_blender_importer.tests.test_skin_parity_report -q
python -m unittest unitypackage_blender_importer.tests.test_weight_numeric_models -q
```

Expected: both PASS. The lower-level numeric comparator still reports its existing `EXACT`; the integrated Skin report reports `BITWISE_EXACT`.

- [ ] **Step 5: Commit Task 1**

```bash
git add tests/blender_geometry_abcd_compare.py tests/test_skin_parity_report.py
git commit -m "test: define supported Skin transport verdict"
```

---

### Task 2: Formalize the policy in the product specification and reporting docs

**Files:**
- Modify: `PRODUCT_SPEC.md:52-62`
- Modify: `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md:190-265`
- Modify: `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md:1-35`
- Reference, do not rewrite: `docs/superpowers/specs/2026-10-01-skin-transport-acceptance-design.md`

**Interfaces:**
- Consumes: the exact policy implemented by Task 1.
- Produces: normative product wording that defines supported Skin transport without redefining raw numeric equality or deformation identity.

- [ ] **Step 1: Add `## Skin Transport Acceptance Contract (2026-10-01)` to `PRODUCT_SPEC.md` immediately after `## High-Fidelity Requirements`**

The section must state, in compact normative form:

- Skin transport `PASS` requires exact Mesh/CP/Bone/influence identity, exact positive-influence retention, bitwise-exact expected Unity representation, zero unexplained transformations and supported evidence context.
- Raw Blender/FBX vs Unity numeric differences remain separately reported and may be `DIFFERENT` in a passing transport.
- Measured deformation remains separately reported and may be `MEASURED_NONZERO` in a passing transport.
- No epsilon/ULP acceptance window is used.
- Source Renderer-owner proof remains supplied by the independent Hierarchy/occurrence contract, not by the Skin numeric report.
- Unsupported version/numeric scope does not receive `PASS`.
- Link the detailed design spec and the numeric evidence document.

Do not duplicate the entire 14-section design document into `PRODUCT_SPEC.md`.

- [ ] **Step 2: Update the focused numeric report**

In `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md`, append a product-policy closure to the existing “Integrated full Skin parity report” section:

- `overall_supported_transport` is now product-authorized and may be `PASS / RED / UNSUPPORTED`;
- public and bounded-real proven evidence should report `PASS`;
- raw numeric RED remains historical/diagnostic evidence;
- deformation remains `MEASURED_NONZERO`;
- source Renderer owner remains outside this report;
- no production weight mutation was added.

Replace the old “Next exact action: evaluate the product-level Skin transport acceptance policy” wording with the next engineering action derived from the completed policy.

- [ ] **Step 3: Update Current State**

At the top of `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md`, add a new checkpoint above the previous report-integration checkpoint recording:

- policy accepted;
- exact pass conditions;
- public 183/183 and bounded-real 6,636/6,636 representation evidence;
- missing influences 0;
- raw differences retained;
- deformation nonzero retained;
- production change none;
- exact next action after this policy closure.

Do not rewrite older checkpoint history.

- [ ] **Step 4: Verify documentation consistency**

Run:

```bash
git diff --check
```

Then search the changed files and verify:

- no changed line claims “weights are unchanged” for Unity;
- no changed line claims “deformation is exact”;
- `NOT_ASSESSED_PRODUCT_POLICY` remains only in historical text where explicitly described as prior state, not in the new current policy;
- no private identifiers/paths were added.

- [ ] **Step 5: Commit Task 2**

```bash
git add PRODUCT_SPEC.md docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md
git commit -m "docs: define Skin transport acceptance"
```

---

### Task 3: Refresh the integrated evidence and prove the policy through the full entry point

**Files:**
- Modify: `tests/unity_small_weight_probe/skin_parity_measurements.json`
- Modify if needed for deterministic generation only: `tests/blender_weight_numeric_real.py`
- Test: `tests/test_skin_parity_report.py`

**Interfaces:**
- Consumes: `d_identity_metrics(before, observed, skin_context=...)` from Task 1.
- Produces: the committed public-safe integrated evidence showing the new product verdict while preserving raw and deformation dimensions.

- [ ] **Step 1: Re-run the public integrated report**

Use the existing public normalization fixture and first/repeated Unity captures through the actual `d_identity_metrics()` entry point.

Expected public aggregate:

```text
identity                  EXACT
influence_retention       EXACT
raw_numeric               RAW_NUMERIC_DIFFERENCE
unity_representation      BITWISE_EXACT
overall_supported_transport PASS
total_influences          183
missing_influences        0
raw_changed_influences    60
representation_exact      183
unexplained               0
max_expected_actual_ULP   0
deformation               MEASURED_NONZERO
source_renderer_owner     UNMEASURED
```

- [ ] **Step 2: Reprocess the same bounded-real evidence through the full entry point**

Use the existing external exact-revision evidence locations from the previous numeric checkpoint; do not copy them into Git.

Expected aggregate:

```text
total influences        6636
missing                 0
raw changed             1002
representation exact    6636
unexplained             0
max expected/actual ULP 0
overall supported       PASS
```

Both first/repeated captures must agree.

If any value is no longer explained, stop the evidence refresh and reduce the new mismatch to a public RED rather than hand-editing the committed JSON.

- [ ] **Step 3: Refresh `tests/unity_small_weight_probe/skin_parity_measurements.json` from actual report output**

Update the sanitized committed evidence so:

- public and both bounded-real `overall_supported_transport` values are `PASS`;
- integrated `unity_representation` values are `BITWISE_EXACT`;
- raw numeric difference counts remain unchanged;
- deformation metrics remain unchanged and nonzero;
- `source_renderer_owner` remains `UNMEASURED`;
- policy metadata identifies the accepted representation-aware Skin transport contract rather than `FACT_REPORT_ONLY_NO_NEW_SUPPORTED_TRANSPORT_VERDICT`.

Do not include private per-influence rows.

- [ ] **Step 4: Add/adjust a test that reads the committed sanitized evidence**

In `tests/test_skin_parity_report.py`, add one regression that loads `skin_parity_measurements.json` and asserts:

- public supported transport is `PASS`;
- both real aggregate-only rows are `PASS`;
- raw differences remain >0;
- representation unexplained count is 0;
- max expected/actual ULP is 0;
- deformation status remains `MEASURED_NONZERO`;
- source Renderer owner remains `UNMEASURED`.

- [ ] **Step 5: Run the focused and full Python suites**

Run from repository parent:

```bash
python -m unittest unitypackage_blender_importer.tests.test_skin_parity_report -q
python -m unittest discover -s unitypackage_blender_importer/tests -t . -p "test_*.py" -q
```

Expected: focused PASS; full suite at least the prior **505 PASS** plus the newly added policy/evidence tests, zero failures/errors.

- [ ] **Step 6: Commit Task 3**

```bash
git add tests/unity_small_weight_probe/skin_parity_measurements.json tests/test_skin_parity_report.py tests/blender_weight_numeric_real.py
git commit -m "test: verify Skin transport acceptance evidence"
```

Only include `tests/blender_weight_numeric_real.py` if deterministic evidence generation actually required a code change.

---

### Task 4: Run bounded integration regressions and close the checkpoint

**Files:**
- Modify only if results require factual updates: `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md`
- Modify only if results require factual updates: `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md`

**Interfaces:**
- Consumes: the product verdict and evidence from Tasks 1–3.
- Produces: a clean pushed checkpoint with no Skin production mutation and no regression in previously verified supported routes.

- [ ] **Step 1: Run compile validation**

From repository root:

```bash
python -m compileall -q blender unity operators ui export validation tests
```

Expected: exit 0.

- [ ] **Step 2: Run the existing Blender Skin/triangle/source-preservation regressions**

Use the same commands and synthetic inputs documented in `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md`:

```text
tests/blender_weight_normalization_fixture.py
tests/blender_triangle_staging_test.py
tests/blender_skin_package_test.py --small-weights
```

Run with Blender background/factory settings and `--python-exit-code 1`.

Expected:

- Skin package PASS;
- tiny positive weights retained;
- triangle staging PASS;
- Shape PASS;
- source success preservation PASS;
- injected failure rollback PASS;
- save/reopen PASS.

- [ ] **Step 3: Run fresh Unity 2022.3.22f1 package regression**

Use the existing first-party `VapbSkinWeightImporter.cs` and current generated Skin package.

Expected:

- 54-vertex / 2-Bone public package control PASS;
- repeated import/Apply PASS;
- invalid mapping rejects;
- no change to raw production Skin data beyond the already-proven importer representation;
- integrated Skin report emits supported transport `PASS`.

- [ ] **Step 4: Final scope/privacy review**

Verify changed files contain no private asset names, local paths, raw private tables, credentials or commercial bytes.

Confirm production implementation diff contains no new Bone Weight mutation, no new FBX rewrite, no epsilon change and no importer-policy change.

- [ ] **Step 5: Update factual checkpoint text if the final run changed counts**

If the Python test count or measured checkpoint facts changed, update only the current checkpoint sections in:

- `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md`
- `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md`

Do not rewrite historical checkpoints.

- [ ] **Step 6: Commit and push the final closure**

```bash
git add docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md
git commit -m "docs: close Skin transport acceptance"
git push
git status --short
```

Expected:

- remote HEAD equals local HEAD;
- worktree clean.

Final report must state separately:

```text
SUPPORTED_SKIN_TRANSPORT
Identity
Influence retention
Raw numeric
Unity representation
Deformation
Source Renderer owner scope
Production change
Python / compileall / Blender / Unity regressions
Remaining Skin RED / UNKNOWN
```

Do not state “Skin is identical”, “weights are unchanged”, or “deformation is exact”.
