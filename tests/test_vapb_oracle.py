import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.vapb_oracle.checkpoint import CheckpointStore, RunState
from tools.vapb_oracle.diff import semantic_diff
from tools.vapb_oracle.corpus import holdout_groups
from tools.vapb_oracle.runner_plan import canonical_package_key, discover_packages
from tools.vapb_oracle.runner_state import classify_status, RetryPolicy
from tools.vapb_oracle.schema import (
    build_envelope,
    public_safe_summary,
    validate_derived_counts,
    validate_envelope,
)
from tools.unity_semantic_oracle.clean_unity_oracle_project import build_cleanup_plan, apply_cleanup, check_clean
from tools.unity_semantic_oracle.quiescence import CleanupGate
from tools.unity_semantic_oracle.worker_protocol import WorkerRequest, WorkerResult, atomic_json_write, request_from_dict, result_from_dict, validate_request, write_once_json
from tools.unity_semantic_oracle.supervisor_harness import SupervisorHarness
from tools.unity_semantic_oracle.worker_template import check as check_template, prepare as prepare_template


class VapbOracleTests(unittest.TestCase):
    def _harness(self, root):
        source = root / "template-source"
        destination = root / "template"
        manifest = root / "template-manifest.json"
        (source / "Packages").mkdir(parents=True)
        (source / "ProjectSettings").mkdir(parents=True)
        (source / "Packages" / "manifest.json").write_text("{}", encoding="utf-8")
        (source / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.62f3\n", encoding="utf-8")
        prepare_template(source, destination, manifest)
        harness = SupervisorHarness(root / "scratch", destination, manifest)
        harness.confirm_human_run()
        return harness

    def test_worker_protocol_identity_and_atomic_result_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "same basename.unitypackage"
            package.write_bytes(b"synthetic-package")
            harness = self._harness(root)
            request, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            self.assertEqual(validate_request(request.to_dict()), [])
            atomic_json_write(attempt.workspace / "worker-status.json", {"state": "IMPORTING"})
            observation = attempt.workspace / "observation.json"
            observation.write_text("{}", encoding="utf-8")
            result = WorkerResult(request.run_id, request.worker_id, request.package_index, request.package_sha256, request.template_id, request.template_hash, request.unity_version, "ISOLATED_PACKAGE", "COMPLETE", str(observation), attempt_id=request.attempt_id, nonce=request.nonce, isolation_verified=True)
            write_once_json(attempt.workspace / "worker-result.json", result.__dict__)
            harness.accept_result_file(request, attempt.workspace / "worker-result.json")
            self.assertEqual(harness.package_states[1], "COMPLETE")
            self.assertEqual(json.loads((attempt.workspace / "worker-status.json").read_text(encoding="utf-8"))["state"], "IMPORTING")

    def test_worker_retry_always_allocates_fresh_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package = root / "p.unitypackage"; package.write_bytes(b"p")
            harness = self._harness(root)
            first, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            harness.quarantine(attempt)
            second, _ = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            self.assertNotEqual(first.worker_id, second.worker_id)
            self.assertTrue(harness.fresh_retry(1))

    def test_worker_protocol_rejects_malformed_identity_and_escaped_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package = root / "p.unitypackage"; package.write_bytes(b"p")
            harness = self._harness(root)
            request, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            self.assertTrue(validate_request({**request.to_dict(), "package_index": True, "run_id": "../escape", "package_sha256": "x"}))
            observation = root / "outside.json"; observation.write_text("{}", encoding="utf-8")
            result = WorkerResult(request.run_id, request.worker_id, request.package_index, request.package_sha256, request.template_id, request.template_hash, request.unity_version, "ISOLATED_PACKAGE", "COMPLETE", str(observation), attempt_id=request.attempt_id, nonce=request.nonce, isolation_verified=True)
            with self.assertRaises(ValueError): harness.accept_result(request, result)

    def test_supervisor_binds_result_to_original_request_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package = root / "p.unitypackage"; package.write_bytes(b"p")
            harness = self._harness(root)
            request, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            forged = WorkerRequest(request.run_id, "other-worker", request.package_index,
                                   request.package_path, request.package_sha256,
                                   request.template_id, request.template_hash,
                                   request.unity_version, request.output_directory,
                                   attempt_id=request.attempt_id, nonce="other-nonce")
            result = WorkerResult(request.run_id, forged.worker_id, 1,
                                  request.package_sha256, request.template_id,
                                  request.template_hash, request.unity_version,
                                  "ISOLATED_PACKAGE", "COMPLETE",
                                  str(attempt.workspace / "observation.json"),
                                  attempt_id=request.attempt_id, nonce="other-nonce",
                                  isolation_verified=True)
            (attempt.workspace / "observation.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "REQUEST_IDENTITY_MISMATCH"):
                harness.accept_result(forged, result)

    def test_protocol_rejects_unknown_camel_case_fields(self):
        value = {
            "run_id": "run", "worker_id": "worker", "package_index": 1,
            "package_path": "package.unitypackage", "package_sha256": "a" * 64,
            "template_id": "template", "template_hash": "b" * 64,
            "unity_version": "2022.3.62f3", "output_directory": str(Path.cwd()),
            "attempt_id": "attempt", "nonce": "nonce", "protocol_version": "1",
            "runId": "wrong",
        }
        self.assertIn("REQUEST_UNKNOWN_FIELD:runId", validate_request(value))

    def test_worker_protocol_rejects_partial_json(self):
        from tools.unity_semantic_oracle.worker_protocol import read_json
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.json"; path.write_text('{"state":', encoding="utf-8")
            with self.assertRaises(ValueError): read_json(path)

    def test_worker_protocol_rejects_non_text_paths_and_result_fields(self):
        request = {
            "run_id": "run", "worker_id": "worker", "package_index": 1,
            "package_path": 12, "package_sha256": "a" * 64,
            "template_id": "template", "template_hash": "b" * 64,
            "unity_version": "2022.3.62f3", "output_directory": 99,
            "attempt_id": "attempt", "nonce": "nonce", "protocol_version": "1",
        }
        with self.assertRaisesRegex(ValueError, "REQUEST_TEXT_INVALID:package_path"):
            request_from_dict(request)
        result = {
            "run_id": "run", "worker_id": "worker", "package_index": 1,
            "package_sha256": "a" * 64, "template_id": "template",
            "template_hash": "b" * 64, "unity_version": "2022.3.62f3",
            "observation_context": "ISOLATED_PACKAGE", "state": "COMPLETE",
            "observation_path": 7, "protocol_version": "1",
            "attempt_id": "attempt", "nonce": "nonce",
            "isolation_verified": True,
        }
        with self.assertRaisesRegex(ValueError, "RESULT_TEXT_INVALID:observation_path"):
            result_from_dict(result)

    def test_terminal_result_is_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            write_once_json(path, {"state": "COMPLETE"})
            with self.assertRaises(FileExistsError): write_once_json(path, {"state": "FAILED"})

    def test_terminal_result_has_one_winner_under_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            barrier = threading.Barrier(2)
            outcomes = []

            def write(value):
                barrier.wait()
                try:
                    write_once_json(path, {"state": value})
                    outcomes.append("won")
                except FileExistsError:
                    outcomes.append("lost")

            threads = [threading.Thread(target=write, args=(state,)) for state in ("COMPLETE", "FAILED")]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(sorted(outcomes), ["lost", "won"])

    def test_worker_template_hash_detects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; destination = root / "template"; manifest = root / "template.json"
            (source / "Packages").mkdir(parents=True); (source / "ProjectSettings").mkdir()
            (source / "Packages" / "manifest.json").write_text("{}", encoding="utf-8")
            (source / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.62f3\n", encoding="utf-8")
            prepare_template(source, destination, manifest)
            self.assertEqual(check_template(destination, manifest), [])
            (destination / "Packages" / "manifest.json").write_text("{\"drift\":true}", encoding="utf-8")
            self.assertTrue(check_template(destination, manifest))

    def test_worker_template_rejects_wrong_unity_version_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; destination = root / "template"; manifest = root / "template.json"
            (source / "ProjectSettings").mkdir(parents=True)
            (source / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.99f1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TEMPLATE_UNITY_VERSION_MISMATCH"):
                prepare_template(source, destination, manifest)
            self.assertFalse(destination.exists())

    def test_worker_template_rejects_distribution_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; destination = root / "template"; manifest = root / "template.json"
            (source / "ProjectSettings").mkdir(parents=True)
            (source / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.62f3\n", encoding="utf-8")
            (source / "payload.blend").write_bytes(b"private")
            with self.assertRaisesRegex(ValueError, "TEMPLATE_FORBIDDEN_PAYLOAD"):
                prepare_template(source, destination, manifest)

    def test_supervisor_requires_human_run_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = self._harness(root)
            harness.human_run_confirmed = False
            package = root / "package.unitypackage"; package.write_bytes(b"synthetic")
            with self.assertRaisesRegex(RuntimeError, "HUMAN_CONFIRMATION_REQUIRED"):
                harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)

    def test_isolated_run_cannot_finalize_before_stable_cleanup(self):
        gate = CleanupGate(required_ticks=3)
        gate.observe_output()
        self.assertEqual(gate.state, "WAITING_FOR_CLEANUP")
        self.assertFalse(gate.tick(compiling=False, updating=False, clean=False))
        self.assertFalse(gate.tick(compiling=True, updating=False, clean=True))
        self.assertFalse(gate.tick(compiling=False, updating=False, clean=True))
        self.assertFalse(gate.tick(compiling=False, updating=False, clean=True))
        self.assertTrue(gate.tick(compiling=False, updating=False, clean=True))
        self.assertEqual(gate.state, "RUN_COMPLETE")

    def test_envelope_separates_observed_and_derived(self):
        envelope = build_envelope(
            run_id="run-synthetic",
            unity_version="synthetic",
            access_method="synthetic_fixture",
            case_id="case-noop",
            observed={"objects": [{"path": "Root/Body", "type": "SkinnedMeshRenderer"}]},
            derived={"renderer_count": 1},
        )
        self.assertEqual(validate_envelope(envelope), [])
        self.assertIn("observed", envelope)
        self.assertIn("derived", envelope)
        self.assertNotIn("LOCAL_PATH_REQUIRES_CONFIGURATION", json.dumps(public_safe_summary(envelope)))

    def test_validation_rejects_unsanitized_machine_path(self):
        envelope = build_envelope(
            run_id="run-bad",
            unity_version="synthetic",
            access_method="synthetic_fixture",
            case_id="case-bad",
            observed={"path": r"LOCAL_PATH_REQUIRES_CONFIGURATION"},
            derived={},
        )
        self.assertTrue(any("machine path" in error for error in validate_envelope(envelope)))

    def test_checkpoint_is_resumable_and_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CheckpointStore(Path(directory) / "checkpoint.json")
            store.start(["case-a", "case-b"])
            self.assertEqual(store.state(), RunState.RUNNING)
            store.complete_case("case-a", {"status": "complete"})
            self.assertEqual(store.pending_cases(), ["case-b"])
            store.finish(RunState.COMPLETE)
            self.assertEqual(store.state(), RunState.COMPLETE)

    def test_diff_is_deterministic_and_marks_identity_change(self):
        before = {"observed": {"object": {"global_id": "A", "name": "Body"}}}
        after = {"observed": {"object": {"global_id": "B", "name": "Body"}}}
        first = semantic_diff(before, after)
        second = semantic_diff(before, after)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["kind"], "identity_changed")

    def test_diff_marks_unity_camel_case_identity_change(self):
        before = {"observed": {"object": {"globalObjectId": "A", "localFileID": "1"}}}
        after = {"observed": {"object": {"globalObjectId": "B", "localFileID": "2"}}}
        self.assertTrue(all(item["kind"] == "identity_changed" for item in semantic_diff(before, after)))

    def test_holdout_split_is_grouped_and_order_invariant(self):
        records = [
            {"group": "g1", "case": "b"},
            {"group": "g1", "case": "a"},
            {"group": "g2", "case": "c"},
            {"group": "g3", "case": "d"},
        ]
        first = holdout_groups(records, holdout_count=1)
        second = holdout_groups(list(reversed(records)), holdout_count=1)
        self.assertEqual(first, second)
        self.assertEqual(first["holdoutGroups"], ["g3"])
        self.assertFalse(set(first["trainGroups"]) & set(first["holdoutGroups"]))

    def test_package_key_preserves_distinct_paths_and_extensions(self):
        self.assertNotEqual(canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"), canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"))
        self.assertNotEqual(canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"), canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"))
        self.assertEqual(canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"), canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"))
        self.assertEqual(canonical_package_key("LOCAL_PATH_REQUIRES_CONFIGURATION"), canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"))
        self.assertNotEqual(canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"), canonical_package_key(r"LOCAL_PATH_REQUIRES_CONFIGURATION"))

    def test_folder_discovery_is_recursive_filtered_and_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b" ).mkdir()
            (root / "a" ).mkdir()
            (root / "b" / "two.UNITYPACKAGE").write_text("", encoding="utf-8")
            (root / "a" / "one.unitypackage").write_text("", encoding="utf-8")
            (root / "a" / "ignore.zip").write_text("", encoding="utf-8")
            result = discover_packages(root)
            self.assertEqual([p.name for p in result], ["one.unitypackage", "two.UNITYPACKAGE"])

    def test_derived_counts_are_recomputed_from_observed_records(self):
        envelope = {
            "observed": {"prefabs": [{"objects": [{"materials": [{}, {}]}]}]},
            "derived": {"prefabCount": 1, "objectCount": 1, "materialSlotCount": 2},
        }
        self.assertEqual(validate_derived_counts(envelope), [])

    def test_human_runner_contract_covers_folder_resume_and_failure_paths(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        self.assertIn("Select corpus folder", source)
        self.assertIn("CreateNewRunFiles", source)
        self.assertIn("PackageFailedCallback", source)
        self.assertIn("CanonicalPackageKey", source)
        self.assertIn("runStartedAtUtc", source)
        self.assertIn("WAITING_FOR_UNITY", source)
        self.assertIn("STALLED", source)
        self.assertIn("Open error log folder", source)
        self.assertIn("Abort safely", source)

    def test_human_runner_uses_durable_state_for_ui_and_actions(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        self.assertIn("private HumanOracleCheckpoint durableState", source)
        self.assertIn("private string currentPackage { get { return durableState.currentPackage; }", source)
        self.assertIn("durableState = previous;", source)
        self.assertIn("durableState = checkpoint;", source)
        self.assertNotRegex(source, r"private\s+(?:string|int)\s+(?:currentPackage|currentPackageIndex|runState|currentPhase|retryCount|lastError|lastHeartbeatAtUtc|lastProgressAtUtc)\s*;")

    def test_unity_deployment_sync_is_explicit_and_managed(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "sync_unity_oracle_project.py").read_text(encoding="utf-8")
        self.assertIn("MANAGED_RELATIVE", source)
        self.assertIn("--check", source)
        self.assertIn("os.replace", source)
        self.assertIn("Assets", source)
        self.assertIn("verified", source)

    def test_runner_has_no_property_as_out_argument(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        for property_name in ("runStartedAtUtc", "packageStartedAtUtc", "lastHeartbeatAtUtc", "lastProgressAtUtc"):
            self.assertNotIn("out " + property_name, source)
        self.assertIn("out result", source)

    def test_baseline_manifest_excludes_library_and_detects_drift(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "baseline_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"Library"', source)
        self.assertIn("BASELINE_DRIFT", source)
        self.assertIn("BASELINE_ADDED", source)

    def test_oracle_isolation_and_scene_cleanup_contract(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "SemanticOracle.cs").read_text(encoding="utf-8")
        self.assertIn("UNITY_ORACLE_OBSERVATION_CONTEXT", source)
        self.assertIn("onImportPackageItemsCompleted", source)
        self.assertIn("ProbeImportedPackageAndFinish", source)
        self.assertIn("NewPreviewScene", source)
        self.assertIn("ClosePreviewScene", source)
        self.assertIn("GUID_REASSIGNED", source)
        self.assertNotIn("NewSceneMode.Single", source)
        self.assertIn("WriteTextAtomically", source)
        self.assertIn("pendingProbeStartedAtUtc", source)
        self.assertIn("packageSequenceIndex", source)
        self.assertIn("pendingPackages.Length == 0", source)
        self.assertIn("PackageCompletedCallback?.Invoke(pendingPackages[0])", source)
        self.assertIn("IMMUTABLE_OUTPUT_ALREADY_EXISTS", source)

    def test_runner_fails_closed_after_isolated_domain_reload(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        self.assertIn('runState = "ISOLATION_FAILED"', source)
        self.assertIn("discard the disposable project", source)
        self.assertIn('resume && string.Equals(runState, "ISOLATION_FAILED"', source)
        self.assertIn("pendingItemsCompleted", (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" / "Assets" / "Editor" / "SemanticOracle.cs").read_text(encoding="utf-8"))
        self.assertIn("VerifyBaselineAttestation", (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" / "Assets" / "Editor" / "SemanticOracle.cs").read_text(encoding="utf-8"))
        self.assertIn("mergedCorpusMode && resume", source)
        self.assertIn("ISOLATION_FAILED", source)

    def test_analysis_cli_defaults_to_isolated_evidence(self):
        source = (Path(__file__).parents[1] / "tools" / "vapb_oracle_analysis" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("allow-contaminated", source)
        self.assertIn("not args.allow_contaminated", source)

    def test_cleanup_allowlist_removes_unexpected_unicode_assets_only(self):
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("Assets/Editor/VAPB", "Packages", "ProjectSettings"):
                (root / relative).mkdir(parents=True, exist_ok=True)
            for name in ("HumanOracleRunnerWindow.cs", "SemanticOracle.cs", "SyntheticFixture.cs"):
                (root / "Assets/Editor/VAPB" / name).write_text((repo / "tools/unity_semantic_oracle/Assets/Editor" / name).read_text(encoding="utf-8"), encoding="utf-8")
            (root / "Assets/RepresentativeAvatar-Test" / "nested").mkdir(parents=True)
            (root / "Assets/RepresentativeAvatar-Test" / "nested" / "asset.txt").write_text("private", encoding="utf-8")
            (root / "Packages/manifest.json").write_text("{}", encoding="utf-8")
            plan = build_cleanup_plan(root, repo)
            self.assertIn(Path("Assets/RepresentativeAvatar-Test/nested/asset.txt"), plan.unexpected_files)
            with patch("tools.unity_semantic_oracle.clean_unity_oracle_project.active_unity_use", return_value="NO"):
                apply_cleanup(plan)
            self.assertFalse((root / "Assets/RepresentativeAvatar-Test").exists())
            self.assertTrue((root / "Assets/Editor/VAPB/SemanticOracle.cs").exists())
            self.assertTrue((root / "Packages/manifest.json").exists())
            self.assertEqual(check_clean(build_cleanup_plan(root, repo)), [])

    def test_cleanup_dry_plan_has_no_side_effect(self):
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "Assets/Editor/VAPB").mkdir(parents=True)
            for name in ("HumanOracleRunnerWindow.cs", "SemanticOracle.cs", "SyntheticFixture.cs"):
                (root / "Assets/Editor/VAPB" / name).write_text("managed", encoding="utf-8")
            unexpected = root / "Assets/UnexpectedImportedAsset"; unexpected.mkdir(); (unexpected / "x").write_text("x", encoding="utf-8")
            plan = build_cleanup_plan(root, repo)
            self.assertTrue(unexpected.exists())
            self.assertGreater(plan.unexpected_count, 0)

    def test_runner_blocks_isolated_mode_without_clean_baseline(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        for token in ("baselineManifestPath", "baselineStatus", "VerifyBaselineStatus", "BASELINE_DIRTY", "Isolation ready", "UNITY_ORACLE_BASELINE_MANIFEST"):
            self.assertIn(token, source)

    def test_runner_completion_requires_cleanup_finalization(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        self.assertIn('runState = "WAITING_FOR_CLEANUP"', source)
        self.assertIn('WriteCheckpoint("PENDING_CLEANUP"', source)
        self.assertIn("baselineStableTicks < 3", source)
        self.assertIn("WriteFinalizationMarker", source)
        self.assertIn('Environment.SetEnvironmentVariable("UNITY_ORACLE_ISOLATION_VERIFIED", "0")', source)

    def test_runner_scroll_and_output_pointer_contract(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "Assets" / "Editor" / "HumanOracleRunnerWindow.cs").read_text(encoding="utf-8")
        self.assertIn("EditorGUILayout.BeginScrollView", source)
        self.assertIn("EditorGUILayout.EndScrollView", source)
        self.assertIn("active-run.json", source)
        self.assertIn("checkpoint_" + '" + stem + "' + ".json", source)
        self.assertIn("unity-semantic-oracle_", source)
        self.assertIn("EditorPrefs.SetString(OutputDirectoryPref", source)
        self.assertIn("WriteTextAtomically", source)
        self.assertIn("ACTIVE_RUN_MISMATCH", source)
        self.assertIn("packageTimings", source)
        self.assertIn("runTimestamp", source)

    def test_cleanup_tool_is_allowlist_and_root_guarded(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" /
                  "clean_unity_oracle_project.py").read_text(encoding="utf-8")
        for token in ("--dry-run", "--apply", "--check", "PATH_ESCAPE", "CLEANUP_BLOCKED_REPARSE_POINT", "UNITY_PROJECT_ACTIVE_", "Packages", "ProjectSettings"):
            self.assertIn(token, source)

    def test_baseline_manifest_requires_schema_two_and_root_identity(self):
        source = (Path(__file__).parents[1] / "tools" / "unity_semantic_oracle" / "baseline_manifest.py").read_text(encoding="utf-8")
        self.assertIn('"manifestVersion": "2"', source)
        self.assertIn("projectRootIdentity", source)
        self.assertIn("BASELINE_SCHEMA_MISMATCH", source)

    def test_watchdog_distinguishes_waiting_stalled_and_running(self):
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=200, unity_busy=True), "WAITING_FOR_UNITY")
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=200, unity_busy=False), "STALLED")
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=20, unity_busy=False), "RUNNING")

    def test_retry_policy_is_bounded(self):
        policy = RetryPolicy(max_retries=1)
        self.assertTrue(policy.can_retry("pkg"))
        policy.record("pkg")
        self.assertFalse(policy.can_retry("pkg"))

    def test_supervisor_processes_23_packages_in_any_order_with_one_fresh_worker_each(self):
        from tools.unity_semantic_oracle.supervisor_harness import SupervisorHarness
        from tools.unity_semantic_oracle.worker_protocol import WorkerResult

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = []
            for index in range(1, 24):
                package = root / f"package-{index:02d}.unitypackage"
                package.write_bytes(f"synthetic-package-{index}".encode("ascii"))
                packages.append(package)
            harness = self._harness(root)
            for package_index in reversed(range(1, 24)):
                request, attempt = harness.allocate(package_index, packages[package_index - 1], "vapb-worker-template-v1", harness.template_hash)
                with self.assertRaisesRegex(RuntimeError, "PACKAGE_ATTEMPT_ALREADY_ACTIVE"):
                    harness.allocate(package_index, packages[package_index - 1], "vapb-worker-template-v1", harness.template_hash)
                observation = attempt.workspace / "observation.json"
                observation.write_text("{}", encoding="utf-8")
                harness.accept_result(request, WorkerResult(
                    request.run_id, request.worker_id, request.package_index,
                    request.package_sha256, request.template_id, request.template_hash,
                    request.unity_version, "ISOLATED_PACKAGE", "COMPLETE",
                    str(observation), attempt_id=request.attempt_id,
                    nonce=request.nonce, isolation_verified=True,
                ))
                harness.dispose(attempt)
            self.assertEqual(len(harness.attempts), 23)
            self.assertEqual(set(harness.package_states.values()), {"COMPLETE"})
            self.assertEqual(len({item.worker_id for item in harness.attempts}), 23)

    def test_supervisor_allows_only_one_active_worker_across_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package_a = root / "a.unitypackage"; package_b = root / "b.unitypackage"
            package_a.write_bytes(b"a"); package_b.write_bytes(b"b")
            harness = self._harness(root)
            harness.allocate(1, package_a, "vapb-worker-template-v1", harness.template_hash)
            with self.assertRaisesRegex(RuntimeError, "WORKER_ALREADY_ACTIVE"):
                harness.allocate(2, package_b, "vapb-worker-template-v1", harness.template_hash)

    def test_quarantine_rejects_late_result_and_retry_uses_fresh_workspace(self):
        from tools.unity_semantic_oracle.supervisor_harness import SupervisorHarness
        from tools.unity_semantic_oracle.worker_protocol import WorkerResult

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package.unitypackage"
            package.write_bytes(b"synthetic")
            harness = self._harness(root)
            request, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            harness.quarantine(attempt, "CRASHED")
            retry_request, retry_attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            observation = retry_attempt.workspace / "observation.json"
            observation.write_text("{}", encoding="utf-8")
            late = WorkerResult(
                request.run_id, request.worker_id, request.package_index,
                request.package_sha256, request.template_id, request.template_hash,
                request.unity_version, "ISOLATED_PACKAGE", "COMPLETE",
                str(observation), attempt_id=request.attempt_id,
                nonce=request.nonce, isolation_verified=True,
            )
            with self.assertRaisesRegex(ValueError, "STALE_OR_QUARANTINED_ATTEMPT"):
                harness.accept_result(request, late)
            self.assertNotEqual(attempt.workspace, retry_attempt.workspace)
            self.assertEqual(retry_request.attempt_id, retry_attempt.attempt_id)

    def test_late_quarantine_cannot_remove_new_retry_from_active_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package = root / "package.unitypackage"; package.write_bytes(b"synthetic")
            harness = self._harness(root)
            _, first = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            harness.quarantine(first, "CRASHED")
            _, second = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            with self.assertRaisesRegex(ValueError, "STALE_OR_QUARANTINED_ATTEMPT"):
                harness.quarantine(first, "TIMED_OUT")
            self.assertEqual(harness.active_attempts[1], second.attempt_id)

    def test_quarantine_rejects_invalid_state_without_mutating_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package = root / "package.unitypackage"; package.write_bytes(b"synthetic")
            harness = self._harness(root)
            _, attempt = harness.allocate(1, package, "vapb-worker-template-v1", harness.template_hash)
            with self.assertRaisesRegex(ValueError, "INVALID_QUARANTINE_STATE"):
                harness.quarantine(attempt, "COMPLETE")
            self.assertEqual(attempt.state, "CREATED")

    def test_worker_result_rejects_symlinked_observation_path(self):
        from tools.unity_semantic_oracle.worker_protocol import WorkerResult

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            link = output / "link.json"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            request = WorkerRequest(
                "run", "worker", 1, str(root / "package.unitypackage"), "c" * 64,
                "template", "d" * 64, "2022.3.62f3", str(output),
                attempt_id="attempt", nonce="nonce",
            )
            result = WorkerResult(
                "run", "worker", 1, "c" * 64, "template", "d" * 64,
                "2022.3.62f3", "ISOLATED_PACKAGE", "COMPLETE", str(link),
                attempt_id="attempt", nonce="nonce", isolation_verified=True,
            )
            self.assertIn("OBSERVATION_PATH_ESCAPE", result.validate_against(request))


if __name__ == "__main__":
    unittest.main()
