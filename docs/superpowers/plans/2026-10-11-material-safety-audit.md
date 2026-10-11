# Material safety audit implementation plan

Goal: independently classify the requested Material/Assistant/performance concerns and fix only reproduced defects on an isolated branch.

Authority: latest explicit audit request, PRODUCT_SPEC.md, existing R2 face diagnostic and retained round-trip observations. Normal package Import must remain independent of Unity Editor. Source assets, GUID/fileID and strict unresolved boundaries remain intact.

- [x] Read actual global/repo instructions, source/specification and relevant Failure Atlas lessons; isolate from saved e675fe6.
- [x] Trace semantic_graph, effective_prefab, occurrence_projection, material_mapping and material_owner_usage. Reuse exact package/asset/occurrence relations; no new reverse-reference framework.
- [x] Reproduce the remaining name-only Material assignment with the actual helper; remove only that unsupported automatic assignment. Test explicit-reference and uniform-Material paths.
- [x] Reproduce A/B cancellation with the actual Unity window handlers; keep individual cancellation from closing unrelated entries. Retain project-local persisted state and fresh Apply checks. Actual Editor restart remains NOT_RUN.
- [x] Replay the public ThreeSlotSource face diagnostic against current source. Preserve original historical results; distinct unproved correspondence remains unresolved.
- [x] Measure existing manifest authorization reads/hash work and Assistant inspections. Adopt only remembered-prompt preflight reduction with native changed-file inspection proof; defer authorization caching.
- [x] Retain CASE0024 source/edited/repeat observations; explicitly distinguish native repeated equality from missing cross-runtime per-CP correspondence.
- [x] Reconcile README, local checked ZIP provenance, Release and default-branch links; no Release/default-branch change.
- [x] Independent safety/compatibility review and focused regressions; purpose-specific commits and remote readback are the final save step. No merge.

Results and proof limits: [classified audit](../../2026-10-11-material-safety-audit.md).

Review focus: same-name unrelated assets; shared Material across package/occurrence scopes; null/missing/unused/ambiguous face partitions; another Assistant entry surviving cancellation; changed files never receiving stale authorization.
