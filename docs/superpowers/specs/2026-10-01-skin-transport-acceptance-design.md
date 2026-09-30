# VAPB Skin Transport Acceptance Contract — Design

Date: 2026-10-01  
Branch: `feature/multi-package-identity`  
Design authority: user-approved product policy derived from the verified Skin transport evidence through HEAD `fdf77d8cbf2b1a85be393c3841f6eba308c8963e`.

## 1. Purpose

Define when VAPB may call a Skin transport successful without pretending that Blender/FBX raw Bone Weight numbers are bit-identical to Unity's imported representation.

The contract must preserve three distinct facts simultaneously:

1. Blender-authored / FBX canonical Skin data may numerically differ from Unity's stored BoneWeight values.
2. The measured Unity 2022.3.22f1 representation is deterministic in the proven scope and can be predicted bit-for-bit.
3. Measured Blender/Unity deformation differences are nonzero and must remain independently visible rather than being inferred away from numeric representation parity.

This specification changes the product-level acceptance meaning of supported Skin transport. It does not change Skin production data, FBX output, Unity importer policy, numeric tolerance, or measured evidence.

## 2. Existing product authority

This contract extends the existing core rule:

> Blender Final State Authority: weights, geometry, Shape Keys, hierarchy and other editable final-state data are taken from Blender at export.

It does not require Unity to store the same raw decimal/bit pattern as Blender when Unity deterministically canonicalizes the Skin representation during import.

It also does not permit unexplained transformation, dropped positive influences, guessed Bone identity, stale evidence, or tolerance-based acceptance.

## 3. Evidence baseline

The accepted policy is grounded in the verified measured scope:

- Blender source → disposable staging → raw FBX: no Bone Weight changes in the public normalization controls.
- Small positive influence retention is preserved by the existing generated-Skin preprocessing policy.
- Public normalization evidence: 183 / 183 influences match the expected Unity representation bitwise.
- Bounded real evidence: 6,636 / 6,636 influences match the expected Unity representation bitwise.
- Missing positive influences after the production preprocessing policy: 0 in the measured public and bounded-real scope.
- Raw FBX → Unity changes remain visible: 60 public influences and 1,002 bounded-real influences differ numerically from raw values.
- Expected Unity representation → actual Unity representation: maximum 0 ULP in the measured scope.
- Measured deformation differences are nonzero and remain separate evidence.
- Source Renderer owner is not established by the Skin numeric report itself; Renderer ownership remains the responsibility of the separate Hierarchy/occurrence proof.

## 4. Selected policy

VAPB adopts **representation-exact Skin transport** for the proven supported context.

A Skin transport may pass even when raw Blender/FBX Bone Weight values differ from Unity's stored values, provided all mandatory acceptance conditions below pass.

This is explicitly different from:

- raw-number equality;
- epsilon-based numeric forgiveness;
- deformation identity;
- visual equivalence;
- a claim about Unity's internal implementation.

## 5. Mandatory acceptance dimensions

The report must retain these dimensions independently.

### 5.1 Identity parity

Required result: `EXACT`.

The exported Skin must have authoritative correspondence for:

- exported Mesh identity;
- control-point / vertex identity in the measured transport;
- Bone identity;
- Bone-to-influence association.

Names, array position and candidate count are not sufficient identity evidence.

Renderer-owner identity is not supplied by this numeric dimension. Final product acceptance must obtain Renderer ownership from the existing Hierarchy/occurrence evidence where that relationship is required.

### 5.2 Influence retention

Required result: `EXACT`.

Requirements:

- no supported positive influence is missing;
- no unexpected influence is introduced;
- duplicate or ambiguous Bone claims reject;
- the exact generated model revision and the proven Skin import policy are in scope.

A dropped positive influence is a transport failure even when the resulting deformation difference is numerically small.

### 5.3 Raw numeric parity

This is diagnostic evidence, not the supported-transport pass criterion.

Allowed result in an otherwise successful transport:

- `EXACT`, or
- `DIFFERENT`.

When different, the report must preserve the count and measured magnitude of the raw differences. It must not rewrite `DIFFERENT` to `EXACT`.

The historical raw Skin RED remains valid evidence.

### 5.4 Unity representation parity

Required result: `BITWISE_EXACT`.

For the supported measured numeric context:

1. derive the expected Unity float32 representation from the raw FBX canonical Skin weights using the proven representation model;
2. bind expected and actual values by authoritative Bone and CP identity;
3. compare expected and actual float32 bits exactly.

A one-ULP difference is a failure.

No epsilon or ULP acceptance window is permitted.

The current experimentally equivalent representation model is evidence for Unity 2022.3.22f1 in its measured scope; it is not described as Unity's internal source algorithm.

### 5.5 Deformation evidence

Deformation is reported independently.

Allowed states include:

- `MEASURED_ZERO`;
- `MEASURED_NONZERO`;
- `UNMEASURED`.

A supported Skin transport `PASS` does **not** mean deformation is mathematically identical in every pose.

When deformation is measured, the report must retain:

- metric type;
- coordinate/frame convention;
- pose/control used;
- maximum measured difference.

Known nonzero measurements must not be hidden by representation parity.

## 6. Supported Skin transport verdict

The product-level field becomes:

`SUPPORTED_SKIN_TRANSPORT: PASS`

only when all of the following are true:

- identity parity is `EXACT`;
- influence retention is `EXACT`;
- Unity representation parity is `BITWISE_EXACT`;
- unexplained influence transformation count is zero;
- no stale, ambiguous or unsupported evidence was consumed;
- the current Unity/runtime/numeric context is within a proven supported scope.

Raw numeric parity may be `DIFFERENT` without failing this verdict.

Measured deformation may be `MEASURED_NONZERO` without failing this verdict, because deformation evidence is a separate measured consequence of the deterministic representation change. The report must still expose it and must not claim deformation identity or general visual harmlessness.

## 7. Fail-closed states

The report must not emit supported-transport `PASS` when any mandatory condition is unresolved.

Examples:

- unsupported Unity version;
- unsupported numeric origin/context;
- influence count outside the proven scope;
- unresolved Mesh / CP / Bone identity;
- missing positive influence;
- unexpected influence;
- duplicate Bone claim;
- stale FBX or policy revision;
- incomplete representation-model input;
- expected/actual Unity bits differ;
- unexplained transformation remains.

These must produce an explicit RED / unsupported state rather than falling back to approximate comparison.

## 8. Current proven scope

The initial supported representation-aware contract is bounded to the context already proven by the numeric investigation, including:

- Unity 2022.3.22f1;
- generated Skin Package route using the existing verified preprocessing policy;
- raw FBX weights originating from measured Blender float32 values;
- authoritative Mesh / CP / Bone correspondence;
- currently proven influence-count and numeric conditions documented in `docs/VAPB_SKIN_WEIGHT_NORMALIZATION_20260930.md`.

The implementation must reference the focused numeric evidence rather than duplicating or silently broadening that scope.

A future Unity version or broader numeric context requires independent proof before receiving the same supported verdict.

## 9. Reporting shape

The integrated Skin report should expose at least:

```text
SKIN TRANSPORT
  supported_transport: PASS | RED | UNSUPPORTED

  identity:
    verdict: EXACT | ...

  influence_retention:
    verdict: EXACT | ...
    missing_positive: N

  raw_numeric:
    verdict: EXACT | DIFFERENT
    changed: N
    max_abs_difference: ...

  unity_representation:
    verdict: BITWISE_EXACT | NUMERIC_MISMATCH | UNSUPPORTED
    explained: N
    unexplained: N
    max_expected_actual_ulp: N

  deformation:
    verdict: MEASURED_ZERO | MEASURED_NONZERO | UNMEASURED
    metric: ...
    max_difference_m: ...
```

The report must allow the state:

```text
supported_transport: PASS
identity: EXACT
influence_retention: EXACT
raw_numeric: DIFFERENT
unity_representation: BITWISE_EXACT
deformation: MEASURED_NONZERO
```

This is not contradictory. It is the intended semantic separation.

## 10. Relationship to overall VAPB acceptance

This contract defines Skin transport only.

It does not by itself declare:

- complete Avatar round-trip support;
- complete Geometry parity;
- Renderer-owner parity;
- arbitrary-pose deformation equivalence;
- Normal/Tangent parity;
- VRChat runtime completion;
- all Unity versions supported.

Overall product acceptance must combine this Skin verdict with the relevant independent Hierarchy, Geometry, Material, Shape, Unity/VRC state and dependency evidence.

## 11. Implementation scope

The next implementation should be limited to:

1. adding this acceptance contract to `PRODUCT_SPEC.md`;
2. promoting the existing integrated report field from `NOT_ASSESSED_PRODUCT_POLICY` to the explicit supported Skin transport verdict defined here;
3. preserving all existing raw, representation and deformation fields;
4. adding positive and fail-closed tests for the policy decision;
5. updating Current State and focused Skin documentation.

No production Skin data mutation is required.

No epsilon change is permitted.

No existing historical RED evidence is deleted.

## 12. Acceptance tests for the policy

At minimum:

- raw numeric different + representation bitwise exact + no missing influences + valid identity/context → supported Skin transport PASS;
- raw numeric exact + representation bitwise exact + valid identity/context → PASS;
- one-ULP representation deviation → RED;
- one missing positive influence → RED;
- swapped/unresolved Bone identity → RED;
- stale FBX/policy revision → RED;
- unsupported Unity/numeric context → UNSUPPORTED, not PASS;
- measured nonzero deformation is retained in the report and does not silently become `MEASURED_ZERO`;
- source Renderer owner remains explicitly external to this Skin numeric acceptance unless supplied by the independent Hierarchy evidence.

## 13. Non-goals

This policy does not:

- declare raw Blender/Unity Bone Weight numbers equal;
- declare measured deformation zero;
- define a visual-error tolerance;
- reverse-engineer Unity internal source code;
- support every Unity version;
- expand the proven influence-count/numeric scope;
- change production Bone Weight data;
- reopen triangle staging, Shape identity, Material naming or Hierarchy Parity.

## 14. Documentation language

User-facing and developer-facing wording must avoid ambiguous claims such as:

- "Skin is identical";
- "weights are unchanged";
- "deformation is exact".

Preferred wording:

> Supported Skin transport passed: Bone/influence identity and retention are exact, and Unity's imported numeric representation matches the proven expected representation bit-for-bit. Raw Bone Weight values differ because Unity deterministically re-represents them in the measured scope; measured deformation differences remain reported separately.

