from types import SimpleNamespace
import unittest

from unitypackage_blender_importer.blender.physbone_runtime import (
    PREVIEW_IDLE,
    PREVIEW_RUNNING,
    PhysicsPreviewController,
    PreviewChain,
)
from unitypackage_blender_importer.blender.physbone_preview import PhysBonePreviewSolver


class FakeAdapter:
    def __init__(self):
        self.positions = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 2.0, 0.0))
        self.parent = (0.0, 0.0, 0.0)
        self.applied = []
        self.restored = False

    def create_state(self, solver):
        return solver.create_state(self.positions)

    def parent_position(self):
        return self.parent

    def apply_positions(self, positions):
        self.positions = positions
        self.applied.append(positions)

    def restore_preview_pose(self):
        self.restored = True


class PhysBoneRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.now = [0.0]
        self.callback = [None]
        self.registered = [False]
        self.adapter = FakeAdapter()
        self.scene = SimpleNamespace(
            vapb_physbone_unmatched=2,
            vapb_physics_preview=SimpleNamespace(strength=1.0, gravity_scale=0.0),
        )

        def discover(_scene):
            return [PreviewChain(self.adapter, "Root", 3, 0)]

        self.controller = PhysicsPreviewController(
            discover,
            timer_register=self._register,
            timer_unregister=self._unregister,
            timer_is_registered=lambda _callback: self.registered[0],
            clock=lambda: self.now[0],
            solver=PhysBonePreviewSolver(),
        )

    def _register(self, callback, **_kwargs):
        self.callback[0] = callback
        self.registered[0] = True

    def _unregister(self, _callback):
        self.registered[0] = False

    def test_enable_update_reset_disable_lifecycle(self):
        self.assertEqual(PREVIEW_RUNNING, self.controller.enable(self.scene))
        self.assertTrue(self.registered[0])
        self.now[0] = 1.0 / 60.0
        self.adapter.parent = (1.0, 0.0, 0.0)
        self.callback[0]()
        self.assertTrue(self.adapter.applied)
        self.assertNotEqual(self.adapter.applied[-1], ((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (1.0, 2.0, 0.0)))
        self.controller.reset()
        self.assertEqual(self.adapter.positions, self.controller.chains[0].state.positions)
        self.assertEqual(PREVIEW_IDLE, self.controller.disable())
        self.assertFalse(self.registered[0])
        self.assertTrue(self.adapter.restored)

    def test_enable_twice_does_not_register_second_timer(self):
        self.controller.enable(self.scene)
        self.controller.enable(self.scene)
        self.assertTrue(self.registered[0])

    def test_update_failure_restores_pose_and_unregisters_timer(self):
        class BrokenAdapter(FakeAdapter):
            def apply_positions(self, positions):
                raise RuntimeError("synthetic update failure")

        self.adapter = BrokenAdapter()
        # Use a fresh controller so the discovery callback returns the broken adapter.
        controller = PhysicsPreviewController(
            lambda _scene: [PreviewChain(self.adapter, "Root", 3, 0)],
            timer_register=self._register,
            timer_unregister=self._unregister,
            timer_is_registered=lambda _callback: self.registered[0],
            clock=lambda: self.now[0],
        )
        controller.enable(self.scene)
        self.now[0] = 1.0 / 60.0
        self.callback[0]()
        self.assertFalse(controller.running)
        self.assertFalse(self.registered[0])
        self.assertTrue(self.adapter.restored)
        self.assertEqual("ERROR", controller.status)


if __name__ == "__main__":
    unittest.main()
