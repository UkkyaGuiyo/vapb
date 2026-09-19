# Oracle Observation Isolation

Authoritative package evidence uses one fresh disposable Unity project per package. The human starts Unity 2022.3, establishes and fingerprints the Oracle baseline, imports exactly one package, waits for the public import callbacks, probes the imported prefab paths immediately, writes one immutable package result, and discards the project before the next package.

The managed runner rejects multi-package input unless `Merged corpus (non-isolated research)` is explicitly enabled. `MERGED_CORPUS` and `CONTROLLED_COLLISION` are valid research contexts, but are never valid evidence for isolated prefab, identity, dependency, or clustering analysis.

The Unity-side output records `observationContext`, package hash/provenance, baseline identifiers, isolation attestation, and public path/GUID collision observations. `isolationVerified` is false unless the human provides a verified baseline attestation; this is intentional fail-closed behavior. CLI `validate`, `analyze`, and `report` also fail closed by default; use `--allow-contaminated` only for an explicitly labeled merged/collision research report.

The project baseline helper excludes `Library`, `Temp`, `Obj`, `Logs`, and `UserSettings` and tracks authored project files and hashes:

```powershell
python tools/unity_semantic_oracle/baseline_manifest.py create <project> <baseline.json>
python tools/unity_semantic_oracle/baseline_manifest.py verify <project> <baseline.json>
```

Deleting imported assets inside one long-lived project is not the authoritative isolation strategy because public APIs cannot guarantee restoration of overwritten `.meta` identities, importer state, package scripts, or Library artifacts.
