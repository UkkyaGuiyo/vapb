# Independent holdout: Blender-side observation

Explicit restart authorized on 2026-10-08. Source base: `1e7ce8fd3f8a24f2daf6cb1cbdc76af3f290ac18`, branch `feature/r2-material-slot-reorder`. Requested implementation model/reasoning: GPT-6.1 Sol / Medium; actual runtime selection was not observable. This records a bounded non-Unity step toward coordinate validation, not product completion.

Four previously unobserved cases were preregistered, exported and imported in separate Blender 5.2.1 LTS background processes. Generation and capture both exited 0. Exact numeric version remains pinned to 5.2.1; the diagnostic display suffix is retained separately.

| Case | Authored world-corner maximum error | Verdict |
|---|---:|---|
| H0 | 4.229580680137346e-7 | PASS |
| H1 | 2.645640675424943e-7 | PASS |
| H2 | 4.128252689694634e-8 | PASS |
| H3 | 4.7272179171109485e-8 | PASS |

Frozen tolerance: 1e-4. H1 minus H0 world maximum: 2.4310324620024915e-7. H2 minus 0.1 H0 maximum: 3.933906478348348e-9. Both intervention checks PASS. All four synthetic face-membership checks PASS through fixture name keys; these keys do not prove external-package Material GUID/fileID association.

## Failure preservation and corrections

The first attempt stopped before export because the old version guard compared `5.2.1` to the runtime display `5.2.1 LTS`. The second stopped before export because Python tuple `cases` differed from the JSON-loaded list. Both failed registrations/logs remain locally preserved; they are not replaced or relabeled as successful runs.

The numeric-version guards and diagnostic version recording were corrected. `public_contract()` now supplies a list for `cases`. The canonical contract and authored-oracle SHA-256 values remained identical across all three registrations, so no geometry, axis/unit input, coordinate equation or tolerance changed. Source hashes were frozen again before the successful third attempt. A persisted-contract regression failed before the list correction and passed afterward; all 14 focused oracle/preregistration tests passed.

`preregistration.json` pins seven executable/test sources plus contract/oracle bytes. `manifest.json` binds all four generated FBX hashes to that registration. Source hashes and same-run FBX hashes were rechecked after capture. The original FBX files and raw process logs remain local; this directory publishes only path-free JSON and this report, without rewriting observed binary inputs. `blender-capture.json` SHA-256: `1c1941357bed53058d30e140b6ff79741844c035dfebafb17ea662292329b117`.

## Remaining gate

Candidate status is `NOT_RUN_UNITY_CAPTURE_REQUIRED`. No Unity process or Project was created in this step. Unity authored-world and paired candidate residuals remain UNKNOWN. The separate material identity gate, parent-child import, winding/normal transport and full Unitypackage round-trip remain unproven.

Next minimum: obtain the shared Unity pool turn from the coordinator, prepare/review the bounded four-case adapter, and pin its bytes before the first Unity observation using these exact four FBXs and frozen settings. Do not retune candidate equations/tolerance after capture. Keep unrelated checkouts and their dirty files untouched.

A fresh read-only review of only the four runtime-fix diffs was dispatched as GPT-6.1 Sol / Medium and returned no actionable findings. Historical reviews were not repeated; the reviewer did not independently rerun the capture.
