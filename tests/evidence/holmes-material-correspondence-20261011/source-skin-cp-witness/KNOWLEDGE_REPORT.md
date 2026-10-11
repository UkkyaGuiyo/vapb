# KNOWLEDGE_REPORT — Atlas remains read-only

Problem: normal Editor exit reported a remaining owned child.

Observation: an unrelated long-lived graphics service had the same ParentProcessId as the new Editor, but its creation time preceded that Editor by days. Editor exited normally, lock disappeared, fresh census had no Editor and mutex was available.

Cause: checking ParentProcessId alone confuses PID reuse with current child ownership.

Correction: retain the initial refusal and reconcile with actual PID/start/creation time and native census. Do not kill the older service or delete locks.

Reusable rule: bind process ownership to PID plus creation time; a child cannot predate its claimed parent instance. Treat uncertain ownership as blocked until read-only chronology establishes it.

Evidence level: confirmed single Windows process observation. Limitations: this does not prove arbitrary descendants are absent or authorize stopping any process. No Atlas mutation or persistence claimed.
