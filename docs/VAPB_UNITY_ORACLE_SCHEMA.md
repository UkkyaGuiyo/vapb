# VAPB Unity Semantic Oracle Schema

Schema `0.2` uses an envelope with `schemaVersion`, `runId`, `unityVersion`,
`accessMethod`, `caseId`, `checkpoint`, `observed`, `derived`, and
`limitations`. `observed` is populated only from documented Unity public APIs.
`derived` is produced by repository tooling and must not be presented as a
Unity observation. Raw output is local-only; public reports use aggregate-safe
summaries.

Identity fields are semantic values, not ordering rules. A diff reports changes
to GUID/local-file/global identity separately from ordinary value changes.
