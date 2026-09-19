# Dedicated Oracle Project Cleanup

The Unity 2022.3 Semantic Oracle project is an external, disposable observation surface. Its authored baseline is an allowlist, not a package-name blacklist:

- managed `Assets/Editor/VAPB` Oracle sources and their required `.meta` files;
- `Packages/` and `ProjectSettings/` infrastructure;
- no other `Assets/` content.

`clean_<PRIVATE_WORKSPACE>_project.py` never launches or controls Unity. It detects an active or unknown Unity process and refuses destructive apply in either case. It rejects reparse-point escapes and resolves every deletion under the supplied project root.

Use the following sequence only after confirming Unity is closed:

```text
[private command or output omitted; narrative finding retained]
```

The baseline manifest is schema 2, targets Unity `2022.3.62f3`, excludes `Library`, `Temp`, `Obj`, `Logs`, and `UserSettings`, and records file hashes, directories, protected files, and `unexpectedAssetCount`. The manifest must remain outside the Unity project and outside public Git history when it contains machine-local state.

The Human Runner displays `CLEAN`, `DIRTY`, `UNKNOWN`, or `VERIFYING`. Isolated observation is blocked unless the external manifest matches the current authored project and the managed deployment is synchronized. A mismatch is `BASELINE_DIRTY` / `ISOLATION_FAILED`; the runner does not continue to another package.

This cleanup does not delete `Library` and does not delete private historical merged-corpus evidence.
