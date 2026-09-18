import unittest

from tools.shader_semantic_oracle.lifecycle import (
    FailureCategory,
    ImportState,
    LifecycleState,
    can_probe,
    observe_import,
    resume_action,
)


class LifecycleTests(unittest.TestCase):
    def test_life_001_state_round_trip_survives_reload_boundary(self):
        state = LifecycleState.new("package.unitypackage", 1)
        state = state.transition(ImportState.IMPORT_REQUESTED, "request")
        reloaded = LifecycleState.from_json(state.to_json())
        self.assertEqual(reloaded.status, ImportState.IMPORT_REQUESTED)
        self.assertEqual(resume_action(reloaded), "observe")

    def test_life_002_missing_callback_assets_present_is_distinct(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_REQUESTED, "request")
        observed = observe_import(state, assets=2, stable_frames=3, compiling=False, callback_received=False)
        self.assertEqual(observed.status, ImportState.IMPORT_STABLE)
        self.assertEqual(observed.classification, "IMPORT_CALLBACK_MISSING_BUT_ASSETS_PRESENT")

    def test_life_003_requested_is_not_complete(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_REQUESTED, "request")
        self.assertFalse(can_probe(state))

    def test_life_004_asset_discovery_required(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_REQUESTED, "request")
        observed = observe_import(state, assets=0, stable_frames=5, compiling=False, callback_received=True)
        self.assertEqual(observed.status, ImportState.IMPORT_REQUESTED)
        self.assertFalse(can_probe(observed))

    def test_life_005_compilation_blocks_probe(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_REQUESTED, "request")
        observed = observe_import(state, assets=1, stable_frames=3, compiling=True, callback_received=True)
        self.assertEqual(observed.status, ImportState.COMPILATION_PENDING)
        self.assertFalse(can_probe(observed))

    def test_life_006_stable_state_allows_probe(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_REQUESTED, "request")
        observed = observe_import(state, assets=1, stable_frames=3, compiling=False, callback_received=True)
        self.assertTrue(can_probe(observed))

    def test_life_007_phase_timeout_is_exact(self):
        state = LifecycleState.new("package.unitypackage", 1)
        failed = state.fail(FailureCategory.ASSET_DISCOVERY_TIMEOUT)
        self.assertEqual(failed.status, ImportState.FAILED)
        self.assertEqual(failed.failure_category, FailureCategory.ASSET_DISCOVERY_TIMEOUT)

    def test_life_008_resume_import_stable(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_STABLE, "stable")
        self.assertEqual(resume_action(state), "probe")

    def test_life_009_stable_is_not_reimported(self):
        state = LifecycleState.new("package.unitypackage", 1).transition(ImportState.IMPORT_STABLE, "stable")
        self.assertEqual(resume_action(state), "probe")


if __name__ == "__main__":
    unittest.main()
