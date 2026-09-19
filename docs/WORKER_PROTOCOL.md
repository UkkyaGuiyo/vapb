# Worker Protocol

Milestone 2 uses an external, atomic file protocol. The Supervisor writes one
`worker-request.json` per fresh attempt. The Worker writes status updates and a
terminal result only in its own workspace. A result is accepted only when its
`runId`, `workerId`, `attemptId`, package index/hash, template id/hash, Unity
version, protocol version, observation context, and terminal state match the
request. Output-file existence or process exit alone is never success.

The prototype wire format uses `snake_case` JSON keys. Required request
identity fields:

`run_id`, `worker_id`, `attempt_id`, `nonce`, `package_index`, `package_path`,
`package_sha256`, `template_id`, `template_hash`, `unity_version`,
`output_directory`, and `protocol_version`.

Worker states are `CREATED`, `STARTING`, `UNITY_STARTING`, `IMPORTING`,
`WAITING_FOR_UNITY`, `PROBING`, `WRITING_RESULT`, `COMPLETE`, `FAILED`,
`TIMED_OUT`, and `CRASHED`. JSON is written through a same-directory temporary
file and atomic replace. A failed or uncertain attempt is quarantined and is
never retried in the same workspace.

Request and terminal-result JSON is fail-closed: malformed JSON, missing or
wrongly typed identity fields, invalid hashes, path escapes, and observations
through a symlink/reparse boundary are rejected. Terminal results are
write-once and late results from quarantined attempts are rejected.
