# Worker Failures

`FAILED` means an explicit worker-side failure. `CRASHED` means the process
ended without a valid terminal result. `TIMED_OUT` means heartbeat and semantic
progress thresholds expired while the process identity was still known.

The authored Supervisor will quarantine the workspace for all three. This
milestone's non-Unity harness records the quarantine state and blocks stale
attempts, but does not terminate processes or move/delete files. Retry creates
a new worker id, attempt id, workspace, request, and process. Retry is bounded. A malformed/partial result,
identity mismatch, wrong Unity version, stale heartbeat, path escape, missing
callback, or non-quiescent import is not promoted as isolated evidence.
