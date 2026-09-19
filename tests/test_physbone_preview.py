import unittest

from unitypackage_blender_importer.blender.physbone_preview import PhysBonePreviewSolver


class PhysBonePreviewTests(unittest.TestCase):
    def setUp(self):
        self.solver = PhysBonePreviewSolver()
        self.rest = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 2.0, 0.0))

    def test_parent_motion_inertia_and_gravity_are_stable(self):
        state = self.solver.create_state(self.rest)
        moved = self.solver.step(state, (1.0, 0.0, 0.0), 1.0 / 60.0, gravity_scale=0.0)
        self.assertNotEqual(moved.positions, self.rest)
        settled = self.solver.step(state, (1.0, 0.0, 0.0), 1.0 / 60.0, gravity_scale=1.0)
        self.assertTrue(all(abs(value) < 100.0 for point in settled.positions for value in point))

    def test_large_timestep_is_clamped_and_reset_restores_rest_pose(self):
        state = self.solver.create_state(self.rest)
        self.solver.step(state, (10.0, 0.0, 0.0), 10.0)
        self.assertLessEqual(state.last_dt, self.solver.max_dt)
        self.solver.reset(state)
        self.assertEqual(self.rest, state.positions)

    def test_preview_off_does_not_change_state(self):
        state = self.solver.create_state(self.rest)
        before = state.positions
        result = self.solver.step(state, (2.0, 0.0, 0.0), 1.0 / 60.0, enabled=False)
        self.assertEqual(before, result.positions)


if __name__ == "__main__":
    unittest.main()
