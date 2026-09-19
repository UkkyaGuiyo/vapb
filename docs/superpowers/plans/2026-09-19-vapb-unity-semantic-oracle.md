# VAPB Unity Semantic Oracle Implementation Plan

## Goal

Create a compliant, resumable Unity observation boundary and deterministic
semantic round-trip tooling without importing commercial assets into Git.

## Work units

1. Add Python envelope validation, privacy sanitization, checkpoint state, and
   semantic diff utilities.
2. Add synthetic tests first for valid envelopes, rejected raw paths/GUID
   leakage, checkpoint transitions, no-op diffs, and controlled mutations.
3. Extend the Unity 2022.3 Oracle with a human-started Editor runner and
   external resumable checkpoint output while preserving public API usage.
4. Add public coverage/compliance/version/corpus/automatic findings/round-trip
   documents that explicitly separate observed, derived, and unavailable data.
5. Add aggregate corpus holdout tooling and tests for group/order/name
   invariance using synthetic records only.
6. Run focused and full Python tests, compile checks, and static C# consistency
   checks available without starting Unity. Record human-gated Unity 2022.3
   and unavailable Unity 6 observations as incomplete rather than fabricating
   results.

## Acceptance

- New Python tests fail before implementation and pass afterward.
- Public output validation rejects machine paths, raw commercial payloads, and
  unsanitized GUID tables.
- Diff output is deterministic and distinguishes identity changes from value
  changes.
- Runner is human-started, resumable, and writes external checkpoints.
- Documentation states the exact access route and current unavailable gates.
- Existing tests remain passing; no production importer code is changed.
