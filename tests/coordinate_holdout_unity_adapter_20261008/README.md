# Four-case Unity input adapter

Source base: `f90c3756c427cfffbd8efb8247df92fc4180996f`; branch `feature/r2-material-slot-reorder`. Requested primary model/reasoning: GPT-6.1 Sol / Medium; actual runtime selection unobservable. This is test-only preparation; no VAPB product source changes.

The existing seven-case probe is reused through the explicit `-vapbCoordinateHoldout` flag. Default seven-case behavior is retained. Holdout mode requires the ordered H0–H3 set, the holdout input schema, and `-vapbCoordinateManifestSha256` matching the exact parsed manifest byte buffer. It requires one transform/renderer and all eight frozen importer settings. Observation status still does not accept the coordinate candidate.

`prepare_unity_manifest.py` validates the externally pinned original manifest, immutable preregistration/artifact/source hashes and all four same-run FBX hashes. It changes DTO layout only, checks the case set before any FBX path lookup, and records preparation-time adapter/probe source hashes. The frozen Blender subtree is unchanged. `prepared-input.json` is the final converted manifest: SHA-256 `0848806638b57e43f5ff1f245a9e42935ca0184e5df42f7e39f662b175f86af3`. The earlier prepared version remains local and is superseded, not overwritten.

## Verification and review

Four adapter tests PASS. The two review findings were reproduced as failing regressions, then fixed: hash/parse one byte buffer, and reject invalid cases before filesystem lookup. Existing output was refused without changing its bytes. Actual preparation using the four observed FBXs completed successfully; deployed source copies still require matching the recorded hashes before launch.

Fresh read-only scope/code review, dispatched as GPT-6.1 Sol / Medium, returned KEEP with those two binding fixes. The fixes were verified by regression tests, without repeating the completed review.

Source-only C# compilation PASS using the installed Unity 2022.3.22f1 Roslyn compiler, .NET Standard references, `UnityEditor.dll` and `UnityEngine.dll`; both probe source files compiled into a library. Two earlier manual-reference attempts failed (missing references, then duplicate type definitions when combining monolithic and split Engine assemblies). Their logs remain local; no source workaround was used. Compilation is not Unity Editor import or runtime acceptance.

## Coordinator boundary

No Unity Editor, Project or capture was launched. Wait for the coordinator's shared-pool assignment; user/VHS use has priority. In an owned disposable Project, copy these exact H0–H3 FBXs under `Assets/VapbCoordinateIntervention`, and the existing probe plus exit guard under an Editor folder. Confirm copied FBX and deployed source hashes before launch. Pass the prepared input manifest, its exact SHA, the explicit holdout flag and a fresh result path to the existing command-line probe. Keep the original contract/importer settings fixed; an observed mismatch rejects this run and does not permit retuning.

Unity authored-world and paired local/matrix/world-point residuals remain NOT_RUN. After the first valid four-case capture, evaluate them with the existing frozen scalar oracle; do not claim candidate acceptance from source compilation or fixture face-name matches. The separate external-package Material GUID/fileID gate and complete Unitypackage round-trip remain unproven.
