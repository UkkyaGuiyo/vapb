# VAPB development handoff

This is a continuation handoff, not a product-completion statement. **STOPPED / INCOMPLETE** applies only to the earlier private-corpus compatibility campaign; it does not suspend public synthetic development. For the normal `.unitypackage`-to-Blender workflow, Unity project import and manual FBX export are not user prerequisites. The add-on handles temporary extraction/FBX interchange internally; Unity Editor/projects serve as development verification oracles, while importing the finished output package into Unity is a separate return step.

## ACTIVE USER STOP — implementation and execution paused (2026-10-06)

**Planning and documentation are authorized for the Avatar delivery/dependency-closure plan only. Product code edits, test execution, Blender/Unity runs, broader integration, and release work remain paused until a separate explicit execution instruction.** Do not auto-resume implementation during routine status checks. This is a bounded planning authorization, not a general restart.

- Repository: <https://github.com/UkkyaGuiyo/vapb>
- Branch and verified remote HEAD: `feature/r2-material-slot-reorder` / `cf45a3ec95af853c009fa446eaf76f8c5ea9af3b` (planning start; reverify after docs commit)
- Planning work root: `C:\\Users\\gkgkb\\Documents\\Codex\\2026-10-04\\task-3\\unitypackage_blender_importer`. The canonical remote, branch, and clean worktree were verified on TitanG14 before documentation changes.
- Public checkpoint: [`docs/R2_BUILTIN_MATERIAL_PREVIEW_CHECKPOINT_20261004.md`](docs/R2_BUILTIN_MATERIAL_PREVIEW_CHECKPOINT_20261004.md), including the CPD fixture diagnosis and SOL-reviewed ExternalObjects design gap.
- CPD remains unresolved: the runner is documented failing at its synthetic `Coat.data.materials` assertion. The same failure was observed at `ec81dc2c176f2b782eb96562e7476f1719c46023` and `d47091c2680b53ac0cb11041f5ece11cd851aa90`; this only shows the failure was not introduced between those revisions.
- No product code/test or Unity project was changed or run for this planning task. The plan is Avatar-first; World is independently gated. External VHS/OnlyYou contracts remain unverified.
- When separately authorized to execute, first verify the canonical remote, branch, HEAD, and worktree status. Read the checkpoint and plan before code changes. Keep `PREFAB_RENDERER_MATERIAL` and `FBX_EXTERNAL_MATERIAL` tests separate; do not substitute confirmation, names, or a unique-child guess for exact native receipt evidence.

Do not treat these planning documents as authorization to implement. Wait for a separate explicit execution instruction.

## Current public synthetic checkpoint (2026-10-04)

- Active development branch: `feature/r2-material-slot-reorder` (verify the current remote before continuing).
- Current bounded code/evidence update: [`docs/R2_BUILTIN_MATERIAL_PREVIEW_CHECKPOINT_20261004.md`](docs/R2_BUILTIN_MATERIAL_PREVIEW_CHECKPOINT_20261004.md).
- This checkpoint covers only the exact Unity built-in default Material identity stated in that note. The Blender preview is approximate and import outcome remains `PARTIAL`; it does not establish Material export restoration or general Renderer mapping.
- The source/evidence checkpoint below is historical handoff context. Retain it; it does not describe the current branch tip.

## Canonical source

- Repository: [UkkyaGuiyo/vapb](https://github.com/UkkyaGuiyo/vapb)
- Development branch: `feature/multi-package-identity`
- Source/evidence checkpoint before this handoff: `b8c8f6b5ce36a8050d6c6e17ed94158a6a405d4d`
- This handoff is documentation-only. At resume, fetch and verify the current branch HEAD and worktree before changing anything.
- An archived predecessor remains a separate private repository. Do not use it as the current source or publish its history.

## Read in this order

1. [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) — approved product authority, including the 2026-09-28 model update.
2. [`docs/VAPB_CORE_PRODUCT_MODEL_20260928.md`](docs/VAPB_CORE_PRODUCT_MODEL_20260928.md), [`docs/EXPORT_IDENTITY_MODEL.md`](docs/EXPORT_IDENTITY_MODEL.md), and [`docs/EXPORT_ARCHITECTURE_DECISION.md`](docs/EXPORT_ARCHITECTURE_DECISION.md) — source/export/post-import identity and Finalizer boundaries.
3. [`docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md`](docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md) — current implementation and evidence status. Read its opening and the 2026-10-01 campaign section; older dated checkpoints are historical, not current results.
4. [`docs/VAPB_CORPUS_CAMPAIGN_20261001.md`](docs/VAPB_CORPUS_CAMPAIGN_20261001.md), [`docs/corpus_campaign/20261001/matrix.md`](docs/corpus_campaign/20261001/matrix.md), [`docs/corpus_campaign/20261001/coverage.md`](docs/corpus_campaign/20261001/coverage.md), and [`docs/corpus_campaign/20261001/issues.md`](docs/corpus_campaign/20261001/issues.md) — anonymous campaign evidence and remaining populations.
5. [`TEST_STRATEGY.md`](TEST_STRATEGY.md) and [`TEST_RESULTS.md`](TEST_RESULTS.md) — supported public test commands and committed results.
6. The local-only companion `HANDOFF_PRIVATE_20261003.md` in the campaign run directory contains machine paths, private corpus copy instructions, and private evidence locations. It is not in GitHub. Never copy its private contents into this public repository.

## Product decisions to preserve

- VAPB bridges editable Blender state back to Unity. Source identity, VAPB transport/export identity, and Unity post-import identity are distinct.
- Blender's final edited geometry is authoritative for geometry export. Recreated geometry does not normally have to inherit the original Unity Mesh identity.
- Unity-specific state is retained as source serialized evidence/recipe where applicable. The current Blender Material slot and face assignment is the export-side authority.
- Exported packages contain required assets and VAPB helper/manifest data; declared third-party providers such as a shader framework can remain explicit external dependencies. Original input packages are not a normal runtime dependency of the output.
- Unity is an optional witness/finalization and test runtime, not a mandatory dependency for ordinary VAPB import.
- Names, ordering, and candidate counts are not identity. Ambiguity must remain visible and fail closed.
- Private/commercial assets, raw logs, GUID/fileID tables, and private identities stay outside GitHub. Minimize real evidence to public-safe synthetic regressions and anonymous aggregates.

## Current stop point

At source checkpoint `b8c8f6b5ce36a8050d6c6e17ed94158a6a405d4d`, the campaign has 24 inventoried package inputs / 418 files, latest normal-import health 24/24, 163/165 configured prefab roots captured, 1,351 known Skin occurrences plus a blocked UNKNOWN population, and Python 571 PASS with compileall exit 0. These counts are separate populations and health is not round-trip acceptance.

The exact-revision Unity importer policy disables vertex welding only when its existing source-revision checks match. The public zero-area-triangle control retains 3/3 triangles, UV and measured Skin numeric sets. In the representative real E0/E1 recheck, Unity Finalizer refused before target capture (`TOPOLOGY_OR_LAYOUT_CHANGED` / `FIRST_APPLY_FAILED`); target parity is **NOT_MEASURED**. A separate real Skin finding still has 2,414 missing positive influence associations out of 33,408. Neither issue is resolved by the other. Do not summarize this checkpoint as corpus round-trip success.

## Next action

1. From a clean `feature/multi-package-identity` checkout at its verified HEAD, build the smallest public synthetic RED for the Finalizer's source-layout versus Blender-final-topology boundary. Capture the exact pre-apply rejection predicate and preserve Bone/Cloth guards.
2. Only if that RED demonstrates a general defect, make a minimal fix and run its focused tests. Then replay the representative real E0/E1 case from the private handoff. Keep topology, Skin influence loss, and other observations separate.

Do not broaden into unrelated features, start wide corpus expansion, or claim completion without user resumption. Do not reset, clean, force-push, merge to `main`, tag, or publish a release as part of this handoff.

## Environment and reproduction

The current campaign used Windows 11, Python 3.14.6, Git 2.54.0, Blender 5.2.1 LTS, and Unity Editor 2022.3.22f1. Blender CLI/bpy and Unity batchmode/documented Editor API were used; Unity MCP, Blender MCP, and Computer Use were not used for this campaign. Unity/Blender are verification oracles, not normal VAPB import dependencies. Exact machine paths and manual asset transfer instructions are only in the private companion report.

From the repository parent directory, the recorded public checks are:

```powershell
python -m unittest discover -s unitypackage_blender_importer/tests -t . -p "test_*.py"
python -m compileall -q unitypackage_blender_importer/blender unitypackage_blender_importer/unity unitypackage_blender_importer/operators unitypackage_blender_importer/ui unitypackage_blender_importer/export unitypackage_blender_importer/validation unitypackage_blender_importer/tests
```

The campaign checkpoint recorded 571 tests PASS and compileall exit code 0. These results apply to the recorded source checkpoint, not automatically to a later revision. Re-run only after the user resumes work or relevant files change.

## Handoff boundary

This public file contains only project-level decisions, anonymous aggregates, and public repository paths. Hardware identity, personal/local paths, private corpus inventory, local validation outputs, and private-only evidence are in the untracked/local companion and must be manually transferred if the next Codex runs on another machine. The private data itself must be re-obtained from the user's legitimate source and never uploaded.
