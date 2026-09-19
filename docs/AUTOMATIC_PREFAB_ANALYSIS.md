# Automatic Prefab Analysis

The analysis suite intentionally does not implement the production `Automatic (Recommended)` selector. It produces a candidate comparison and a safe classification only. A unique structural candidate may be reported, but production selection remains disabled until semantic evidence and user-facing acceptance criteria are separately approved.

Possible outcomes include `UNIQUE_STRUCTURAL_CANDIDATE`, `MULTIPLE_VALID_VARIANTS`, `USER_CHOICE_REQUIRED`, `NO_COMPLETE_CANDIDATE`, and `NO_CANDIDATE`.
