# R2 Stage 3 Implementation Checkpoint

Date: 2026-10-04
Project: VAPB
Branch: `feature/r2-material-slot-reorder`
Reviewed base SHA: `723a831390b8e85d40a7723587fc369f207279d6`

This checkpoint records the Stage 3 material-slot identity transport implementation. It is not a completion or release statement. The earlier corpus handoff remains stopped/incomplete.

## Contract

- Blender emits `BUILD_EXPORTED_STATIC_V2` with `material_transport_version: 2`.
- Each `material_slots[].slot_index` is a canonical decimal string (`"0"`, `"1"`, ...).
- The Unity Finalizer uses `JsonUtility` and accepts a slot only when its deserialized string exactly equals the expected invariant-culture slot number.
- The custom raw-JSON scanner was removed. Existing GUID, hash, slot-count, label-multiplicity, dependency, and native-submesh guards remain.
- Bone and Cloth protections remain in force.

## Verification recorded for this checkpoint

- Blender 5.2.1 background regression: 64 tests passed across `test_final_state_v2_payload`, `test_final_state_material_ids`, `test_final_state_fbx_carriers`, `test_final_state_dependency_providers`, `test_material_export_reference_safety`, `test_triangle_material_transport`, and `test_export_materialization`.
- C# reference-only compile: passed with the installed Roslyn compiler and existing Unity managed, Unity Test Runner, and NUnit assemblies. JsonUtility field initialization warnings (`CS0649`) were emitted. This was not a Unity Editor compilation or test run.
- `git diff --check`: passed with line-ending conversion warnings on existing Python/C# files.

## Required Unity gate still open

The Unity Editor was not started. Unity assembly compilation, EditMode test discovery/execution, ModelImporter reimport behavior, native FBX material-slot topology, and first/repeat Apply behavior remain unverified. JsonUtility behavior for raw numeric tokens targeting a string field and duplicate raw JSON keys also remains unverified; no duplicate-key rejection is claimed. Any ambiguous Unity behavior blocks release until characterized.

The EditMode V1 rejection test writes a manifest and therefore requires a throwaway Unity project containing `.vapb-disposable-unity-test-project` at its project root. It compares pre/post Apply hashes for the manifest, manifest metadata, expected generated prefab, and its metadata, then restores and rechecks their original hashes.

Before Unity verification, identify separate SourceProject and TargetProject candidates, confirm their versions and purposes, and run the suite only in an isolated disposable test project. Characterize raw numeric/string coercion and duplicate-key behavior separately from the canonical-string contract tests. Do not treat the 64 Python/Blender passes or reference-only compile as Stage 3 proof or release readiness.
