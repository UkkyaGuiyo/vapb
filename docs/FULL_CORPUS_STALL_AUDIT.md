# Full-Corpus Runner Stall Audit

The private full-corpus checkpoint stopped after four completed packages. The
private Unity Editor log shows the fifth package import was requested, followed
by script compilation and a domain reload. There is no evidence of a fatal
Oracle exception; the Editor remained alive and package/content warnings were
not treated as failures.

## Root cause classification

`STRONGLY_SUPPORTED`: continuation state was held in static fields and static
`AssetDatabase.importPackageCompleted` subscriptions. Importing a package with
script changes triggered compilation/domain reload, which can discard those
fields and subscriptions. The durable checkpoint remained `RUNNING`, so the
window had no valid continuation signal and appeared alive forever.

The log does not prove every callback ordering detail, so this is not labelled
`CONFIRMED` at the Unity internal lifecycle level. The next human retest is
required for empirical confirmation.

## Fix

The Runner now persists run/package phase, current package, timestamps,
heartbeat/progress, retry/error state, package status sets, schema versions, and
runId. Domain reload inspection detects a durable RUNNING checkpoint, while a
human `Resume run` action restarts from an idempotent package boundary. The
current package is retried rather than waiting forever for a lost callback.

The previous four completions are explicitly marked
`REOBSERVATION_REQUIRED` on resume because the observation schema gained
structural and texture-property facts. They are not silently treated as valid
under the new coverage.
