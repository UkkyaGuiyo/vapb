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
retries completed: 10 bounded PASS, 1 geometry RED and 1 UNPROVEN/HARNESS_ERROR.
Five selected subjects pass both modes. The remaining E0 retains all triangles
in generated FBX but loses exact zero-area triangles in fresh Unity; its E1 is
refused before target measurement. Those modes are not combined into a single
verdict. The next short-output batch has completed two further subjects / four modes, all bounded PASS. Its six remaining subjects / twelve modes are READY_NOT_RUN. A separate four-subject / eight-mode batch is prepared but NOT_RUN. These pending modes do not contribute completed verdicts.
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
  save/reopen both PASS with source unchanged; its original E0/E1 replay finishes with separate Skin REDs.
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

Pass 2 is **NOT COMPLETE**: normal nested model-route attempts yield 2 export-only
successes and 4 other-package Material refusals; full target roundtrips remain
NOT_MEASURED.
Further Pass 3 expansion and final validation remain **PENDING**. No all-package representative
baseline completion is claimed. This report must be updated
from completed runtime evidence before any final acceptance claim.

## Post-checkpoint diagnostics

The original directory-affected subject finishes E0/E1 with Skin RED; topology,
UV and Material partitions are EXACT in both. An isolated Importer-lifecycle
control proves exact callback invocation and min-weight zero assignment. Forced
reimport after compiled helpers leaves the target associations unchanged, with
the same 2,414 missing positive influences. Callback absence/startup timing
alone is refuted; the importer/numeric mechanism remains UNPROVEN.

The explicit public zero-area fixture reaches generated-FBX and fresh Unity
capture. The unchanged D-only comparator measures D0 and production D1 as
3-to-2 topology RED with source unchanged. Full A/B/C/D comparison stops at a
separate C-side CP-marker/vertex alias assertion. This does not identify the
importer cause or prove a triangle-staging regression.

Read-only typed-caller nested controls preserve exact identity and serialized
payload and remove the diagnostic key-type mismatch. All three still refuse
missing semantic-owner identity. Independent registered model Export attempts
finish in six modes: two export-only successes and four
MODEL_MATERIAL_OTHER_PACKAGE_UNSUPPORTED refusals. Full roundtrips are unmeasured.

## Latest bounded controls and pending work

Two further selected subjects completed four short-output E0/E1 modes, all
bounded PASS. Earlier retries remain 10 PASS / 1 geometry RED / 1 UNPROVEN.
Original, supplementary and extra-subject denominators remain separate.

The public zero-area D1 control uses the same generated FBX and changes only
ModelImporter.weldVertices. Original true: 3-to-2 triangles, topology mismatch.
False: 3-to-3 triangles, topology EXACT. Both measured sampled surfaces are
SAMPLED_EXACT. Other settings and source FBX remain unchanged; original meta
bytes and settings are restored. This proves a causal flag effect for the
public control, not Unity's internal removal mechanism or full Skin acceptance.
No production importer change has been applied.

The separate real Skin control changes weldVertices to false with the same
generated FBX and policy. It still reports 2,414 missing positive associations
out of 33,408: Skin RED. Original meta is byte-restored. The first comparison
refused missing diagnostic-context files; byte-exact copies of the existing
manifest and policy completed that context, then the unchanged comparator
measured the RED. The public topology result does not solve this Skin issue.

Loss-pattern diagnostics refute a universal four-influence cap and a global
monotonic threshold in the examined raw/source-normalized weight domains.
A separate public two-influence parameter grid captures zero missing positive
labels after exact policy application and repeat import; capture success is
not full numeric or roundtrip acceptance. Real Skin loss remains unexplained.

The remaining next-batch six subjects / twelve modes and separately prepared
four subjects / eight modes are NOT_RUN. The overall corpus goal is NOT MET.
No deformation, tangent, broad VRC or whole-avatar acceptance is claimed.
