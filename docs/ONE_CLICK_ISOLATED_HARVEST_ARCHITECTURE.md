# One-Click Isolated Harvest Architecture

## Decision

The Human Runner is a supervisor. It may be started manually once, but an
arbitrary `.unitypackage` is observed in a fresh disposable Unity worker
workspace and process. The worker imports exactly one package, waits for public
import/quiescence evidence, probes it, commits a candidate observation, exits,
and is then disposed or quarantined. The supervisor validates the candidate and
advances to the next package. This is the only design that preserves process-
level isolation using documented Unity APIs.

The current in-process `PENDING_CLEANUP` flow remains fail-closed migration
behavior. It is not authoritative multi-package isolation.

## Rejected alternatives

- Deleting imported paths cannot restore overwritten files, `.meta` identities,
  loaded objects, assemblies, importer caches, or external side effects.
- Restoring byte snapshots inside one Editor cannot restore process state,
  native plug-ins, static handlers, or Library/importer state.
- Staging under another Assets directory changes package semantics; Unity's
  public package import API has no supported path-rebase operation.
- Suppressing domain reload delays state changes but does not roll them back.
- Matching disk bytes after cleanup does not prove matching process state and
  would reproduce the false-clean failure.

## State machines

Supervisor:

```text
IDLE/RECOVER -> PREFLIGHT -> ALLOCATE_RUN -> PREPARE_WORKSPACE
-> LAUNCH_WORKER -> MONITOR_WORKER -> VALIDATE_AND_PROMOTE
-> DISPOSE_OR_QUARANTINE -> NEXT_PACKAGE | COMPLETE
```

Worker:

```text
BOOTSTRAP -> VERIFY_BASELINE -> IMPORT_ARMED -> IMPORT_CALL_ENTERED
-> IMPORTING/RELOADING -> QUIESCING -> PROBING -> COMMIT_CANDIDATE -> EXIT
```

Every non-idempotent transition is persisted atomically first. If import-call
ownership is uncertain, the worker workspace is discarded and a fresh worker
is used; import is never repeated in an uncertain workspace.

## Isolation invariants

An observation is promotable only when the worker has an exact entry baseline,
one package SHA-256, complete import callback evidence, a stable read-only
probe, an intact harness, and a fresh workspace/process boundary from every
other package. `RUN_COMPLETE` additionally requires every package to be
promoted and every workspace disposed or quarantined. Output-file existence is
never a terminal condition.

## Ownership model

The worker records pre/post file and GUID maps plus public import callback
items. Changes are classified as `ADDED`, `MODIFIED`, `REPLACED`, `DELETED`,
`GUID_CHANGED`, `META_CHANGED`, `PATH_COLLISION`, or `UNKNOWN_CHANGE`.
Missing callback evidence or an attribution gap is `UNKNOWN_CHANGE` and cannot
be promoted as isolated evidence.

Authoritative restoration is workspace disposal. Per-file deletion or byte
restoration is diagnostic-only and must never claim process-level restoration.

## Quiescence and reload recovery

Quiescence requires import completion and imported-item callbacks, no compiling
or updating, synchronous refresh completion, two unchanged postprocessor/GUID
barrier rounds across `delayCall`, no later domain reload, and an unchanged
harness. Probe output is discarded and the worker returns to quiescing if the
project changes during probing. A bounded failure becomes `NON_QUIESCENT`.

The external worker checkpoint is authoritative across reload. Initialize-on-
load re-registers handlers; assembly reload callbacks persist intent; static
delegates and EditorWindow lifetime are not recovery mechanisms.

## Output and timestamps

One fixed external output directory is remembered in private `EditorPrefs`.
Each run has a `runId` and one UTC `runTimestamp`; checkpoint and observation
filenames share that timestamp and are never overwritten. `active-run.json`
points to the exact unfinished pair for explicit Resume. Completed history is
never selected implicitly for a new run.

Event timestamps are write-once and remain null when an event was not observed:
run start, package start, import start/completion, probe start/completion,
cleanup start/completion, stability, baseline verification, finalization, and
run completion. Durations state their scope and are not reconstructed from an
unrelated later transition.

## Human intervention

Intervention is limited to baseline/harness mismatch, Unity version or license
startup, storage/concurrency problems, unsafe paths, persistent worker launch
failure, package UI interaction, explicit abort, or legacy dirty
`PENDING_CLEANUP`. Package-local failures are recorded and the disposable
worker is quarantined before the supervisor decides whether to continue.

## Migration and tests

Pre-fix `COMPLETE` and existing `PENDING_CLEANUP` checkpoints remain
provisional. They are never converted directly to authoritative completion;
they require a fresh exact baseline and finalization marker or are marked
`REOBSERVATION_REQUIRED`.

Synthetic coverage must exercise ownership classes, overwrite/GUID/meta drift,
late callbacks, compilation/reload, partial cleanup, crash recovery, active
pointer validation, timestamp ordering, and multi-package order independence.
Real acceptance proceeds from a simple package to repeated package, collision
pair, small corpus, and only then the full corpus.
