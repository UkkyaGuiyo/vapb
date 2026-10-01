# Corpus campaign — 2026-10-01

**Status: IN_PROGRESS.** This is a provisional, anonymous evidence report. The
expansion queue and remaining validation are unfinished; no final success rate
or corpus roundtrip completion is claimed.

## Population and observations

| Scope | Recorded evidence | Limit |
| --- | --- | --- |
| Input inventory | 418 files; 24 unique package inputs | Inventory is not semantic acceptance. |
| Blender health | Latest result: 24/24 PASS | The earlier 23 PASS and 1 directory discovery failure are retained. Health covers import and unchanged save/reopen, not roundtrip equivalence. |
| Independent source capture | 19 PASS; 4 metadata-only NOT_APPLICABLE; 1 dependency composition conflict | The conflict leaves its source population UNKNOWN. |
| Prefab roots | 163 loaded of 165 configured roots | 163 were captured; 2 remain blocked. Counts do not establish cross-runtime identity. |
| Source Skin occurrences | 1,351 known, plus an UNKNOWN population in the blocked composition | These are occurrences across captured prefab roots, not unique Blender meshes. |
| Exact source witness chains | 12 additional chains PASS | Source control, identity and restoration evidence only; not roundtrip PASS. |

No scene assets were found in the package inventory. Native Blender mesh counts,
renderer records and source Skin counts are separate populations; their counts
cannot prove missing imports or matching identities.
All 418 inventoried source files remain hash-unchanged; missing files: 0.

## Representative evidence

The original first representative remains **HARNESS_UNSUPPORTED**. A supplementary
capture has separate dependency-blocked destination evidence. It does not replace
the original subject or establish roundtrip acceptance for that input.

One other exact representative has **bounded Skin PASS in both E0 and E1**,
with five of five evidence-corruption controls rejected and initial/repeated
finalizer controls passing. Deformation remains **UNMEASURED**. This evidence is
limited to that selected occurrence and the measured contract.

The original selected-subject baseline has 26 attempted modes: 2 bounded Skin
PASS, 14 UNPROVEN/HARNESS_ERROR, 8 BLOCKED/DEPENDENCY_MISSING and 2
UNSUPPORTED/HARNESS_UNSUPPORTED. Earlier failed attempts remain evidence; these
counts describe original subjects and exclude supplementary subjects and retries.
Two fresh retries of one original subject both report UNSUPPORTED_STRUCTURE for
MODEL_UNASSIGNED_MATERIAL_SCOPE_UNSUPPORTED. They do not erase its earlier errors.

The first extra-subject batch completed 16 modes: 4 BLOCKED/DEPENDENCY_MISSING
across two subjects with actual destination refusal, and 12
UNPROVEN/HARNESS_ERROR across six subjects during package extraction. These
results remain separate from the original baseline. Twelve fresh short-output
retries are IN_PROGRESS; a further eight subjects / sixteen modes are READY_NOT_RUN.
Neither unfinished group contributes completed verdicts.
Selected-subject witnesses do not cover all source roots, Skin occurrences,
shapes, scripts or destination behaviors. See the [completed matrix](corpus_campaign/20261001/matrix.md),
[coverage](corpus_campaign/20261001/coverage.md) and [issues](corpus_campaign/20261001/issues.md).

## Open findings

- A frame diagnostic measures 41 exact bone records. Source-template and member
  rest data agree, while their comparison with the standalone witness fails the
  existing translation tolerance. Placement has not been proved as the cause;
  this is not a demonstrated production defect.
- Unassigned Material slots now have an explicit adapter refusal before editing
  or injected export failure. Two fresh runtime retries confirm that unsupported
  scope; earlier rollback-guard errors remain recorded.
- Directory candidates are filtered at both discovery entry points. The focused
  public suite has 39 PASS. The affected package's fresh normal import and
  save/reopen both PASS with source unchanged; its original E0/E1 replay is NOT_RUN.
- Three fresh witness-equipped normal health imports PASS. Three subsequent
  read-only nested observers prove native witness joins, while stored projection
  binding remains UNPROVEN. These observations do not establish full roundtrip.
- An extraction environment control reproduces four errors on targets of
  279–282 characters. The same package extracts 248 assets with zero errors under
  a short output root. This identifies a harness path-length limit, not product PASS.

The full Python suite records 571 PASS and compileall exits 0. These checks do not
replace runtime corpus acceptance.
The second and final scope review reports PASS; it is a scope review, not semantic
acceptance of pending runtime jobs.

## Remaining status

Pass 2 is **NOT COMPLETE**: three nested subjects have unexecuted E0/E1 modes.
Pass 3, final validation and push remain **PENDING**. No all-package representative
baseline completion is claimed. This report must be updated
from completed runtime evidence before any final acceptance claim.
