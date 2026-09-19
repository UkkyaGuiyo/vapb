import json
import tempfile
import unittest
from pathlib import Path

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


class VapbOracleTests(unittest.TestCase):
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
        self.assertIn("File.Delete(outputPath)", source)
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

    def test_watchdog_distinguishes_waiting_stalled_and_running(self):
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=200, unity_busy=True), "WAITING_FOR_UNITY")
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=200, unity_busy=False), "STALLED")
        self.assertEqual(classify_status(heartbeat_age=2, progress_age=20, unity_busy=False), "RUNNING")

    def test_retry_policy_is_bounded(self):
        policy = RetryPolicy(max_retries=1)
        self.assertTrue(policy.can_retry("pkg"))
        policy.record("pkg")
        self.assertFalse(policy.can_retry("pkg"))


if __name__ == "__main__":
    unittest.main()
