import json
import tempfile
import unittest
from pathlib import Path

from tools.vapb_oracle.checkpoint import CheckpointStore, RunState
from tools.vapb_oracle.diff import semantic_diff
from tools.vapb_oracle.corpus import holdout_groups
from tools.vapb_oracle.schema import build_envelope, public_safe_summary, validate_envelope


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


if __name__ == "__main__":
    unittest.main()
