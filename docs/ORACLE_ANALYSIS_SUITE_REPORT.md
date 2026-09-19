# VAPB Oracle Analysis Suite Report

## Result

The private analysis suite is implemented on the research branch. It provides a versioned schema adapter, content-addressed raw vault, typed identity graph, structural/skeleton/mesh/package signatures, candidate comparison without production automatic selection, dependency and material-texture role analysis, anomaly and next-experiment output, SQLite indexing, CLI entry points, legacy/version/roundtrip helpers, and public-safe reports.

## Verification

- `tests.test_oracle_analysis`: 20 passed
- `tests.test_vapb_oracle`: 12 passed
- `tools/unity_semantic_oracle/tests`: 2 passed
- `compileall`: passed
- `python -m vapb_oracle_analysis --help`: passed
- no Unity process was launched
- no commercial or real-corpus payload was harvested or committed

The repository-wide discovery command is not a valid acceptance surface from this isolated `_vapb_oracle` worktree: legacy importer tests cannot import the original package name, and one pre-existing hygiene test reports a developer path in an older tracked file. The focused suites above are the directly relevant evidence for this change.

## Safety decisions

Raw input is validated before immutable content-addressed persistence. Derived adapter diagnostics remain separate from observed evidence. Ambiguous or incomplete candidates never become an automatic production selection. Public summaries use an allowlist and omit raw paths, names, GUIDs, payloads, and provenance details.

## Unity compliance

Unity was not used for this implementation turn. Therefore no Unity access route or semantic observation was claimed, and no Unity binary, private API, or commercial asset data was inspected or copied.

## Git

Branch: `research/vapb-unity-semantic-oracle-comprehensive-harvest`

The branch was pushed to the existing private remote. The final commit and remote branch verification are reported in the task result.
