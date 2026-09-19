# Supervisor State Machine

```text
IDLE/RECOVER
  -> HUMAN_RUN_CONFIRMED
  -> VALIDATE_RUN
  -> PREPARE_WORKER
  -> START_WORKER
  -> WAIT_FOR_WORKER
  -> VALIDATE_WORKER_RESULT
  -> FINALIZE_PACKAGE
  -> DISPOSE_OR_QUARANTINE
  -> NEXT_PACKAGE | FINAL_CORPUS_VERIFY | RUN_COMPLETE
```

The Supervisor has one active worker at a time. It writes the request before
launch, records PID/nonce/heartbeat, and refuses to advance until the worker
result is identity-validated and the workspace is disposed or quarantined.
Resume reads the exact unfinished active run; it never selects the newest file
and never reruns a promoted package.

`HUMAN_RUN_CONFIRMED` is a hard gate. The Supervisor may not start a worker
until the human has manually opened the Supervisor Editor and explicitly
approved the run summary. The prototype harness models and tests these
transitions; it does not launch Unity, terminate processes, or physically
delete/move workspaces. Those side effects belong to the later authored
Supervisor implementation and are not claimed by this milestone.
