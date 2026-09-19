# VAPB Oracle Analysis Architecture

The analysis suite is a read-only pipeline: immutable raw JSON vault, versioned schema adapter, CanonicalObservation v1, SQLite indexes, derived signatures and reports. Raw observations are evidence; signatures, clusters, candidate classifications, dependency classes and experiments are derived data.

The suite does not select a production prefab automatically. Ambiguous or structurally distinct candidates remain explicit user-choice outcomes.

## Commands

`python -m vapb_oracle_analysis ingest INPUT --vault VAULT`

`python -m vapb_oracle_analysis validate INPUT --vault VAULT`

`python -m vapb_oracle_analysis analyze INPUT --vault VAULT --output ANALYSIS.json`

`python -m vapb_oracle_analysis report INPUT --vault VAULT --output REPORT_DIR --public-only`

The input is never modified. Public summaries use an allowlist and do not publish source paths, names, GUIDs, or raw provenance.
