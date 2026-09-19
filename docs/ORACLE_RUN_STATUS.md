# Oracle Run Status

Status at 2026-09-19: `PREPARED_WAITING_FOR_HUMAN_RUN`.

Completed in this branch:

- public schema 0.2 with observed/derived separation;
- human-started Unity 2022.3 Editor runner;
- external package checkpoint and resume filtering;
- deterministic semantic diff including Unity camel-case identity fields;
- synthetic schema, privacy, checkpoint, diff, and grouped holdout tests;
- compliance, version, coverage, corpus, automatic-selection, and limitation docs.

Not claimed:

- real commercial corpus harvest;
- Unity 6 observations (official MCP unavailable in the current connector set);
- automatic prefab correctness;
- full round-trip differential results;
- Blender production fix or release artifact.

Next human action: in Unity 2022.3 open `Tools/VAPB/Unity Semantic Oracle
(Human Runner)`, choose an external output directory, provide the local test
inputs, and press `Run observation`. Do not commit the generated JSON.
