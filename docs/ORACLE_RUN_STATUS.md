# Oracle Run Status

Status at 2026-09-19: `FIRST_SMOKE_AUDITED_NEXT_CORPUS_PENDING`.

Dedicated Unity project: `LOCAL_PATH_REQUIRES_CONFIGURATION`.

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
(Human Runner)`, select the private corpus folder, choose an external output
directory, review the package preview, and press `Run observation`. Do not
commit the generated JSON.

The next runner version additionally supports recursive corpus-folder discovery,
deterministic package preview, canonical full-path resume keys, explicit
RUNNING/COMPLETE/FAILED timing fields, and stale-output rejection.
