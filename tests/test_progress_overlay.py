"""Unit tests for the foreground 3D View progress overlay."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.blender.progress_overlay import ImportProgressOverlay


class _FakeArea:
    type = "VIEW_3D"

    def __init__(self):
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class _FakeSpaceView3D:
    added = []
    removed = []

    @classmethod
    def draw_handler_add(cls, callback, args, region_type, draw_type):
        handle = SimpleNamespace(callback=callback, args=args, region_type=region_type, draw_type=draw_type)
        cls.added.append(handle)
        return handle

    @classmethod
    def draw_handler_remove(cls, handle, region_type):
        cls.removed.append((handle, region_type))


def _state(**overrides):
    values = {
        "stage": "ANALYZING_PREFABS",
        "stage_index": 2,
        "stage_count": 8,
        "current_item": "UV2.prefab",
        "current_index": 3,
        "current_total": 8,
        "elapsed_seconds": 23.4,
        "blocking_operation": False,
        "status": "WORKING",
    }
    values.update(overrides)
    return SimpleNamespace(snapshot=lambda: dict(values))


class ProgressOverlayTests(unittest.TestCase):
    def setUp(self):
        _FakeSpaceView3D.added.clear()
        _FakeSpaceView3D.removed.clear()
        self.area = _FakeArea()
        self.context = SimpleNamespace(area=self.area)

    def test_overlay_registers_handler_and_redraws_on_progress_update(self):
        overlay = ImportProgressOverlay(self.context, space_view_3d=_FakeSpaceView3D)

        overlay.start(_state())
        overlay.update(_state(current_item="UV3.prefab", current_index=4))

        self.assertTrue(overlay.active)
        self.assertEqual(1, len(_FakeSpaceView3D.added))
        self.assertGreaterEqual(self.area.redraws, 2)
        self.assertEqual("UV3.prefab", overlay.snapshot["current_item"])

    def test_overlay_falls_back_to_the_window_screen_view3d_area(self):
        area = _FakeArea()
        context = SimpleNamespace(
            area=None,
            window=SimpleNamespace(screen=SimpleNamespace(areas=[SimpleNamespace(type="OUTLINER"), area])),
        )
        overlay = ImportProgressOverlay(context, space_view_3d=_FakeSpaceView3D)

        overlay.start(_state())

        self.assertIs(area, overlay.area)
        self.assertTrue(overlay.active)

    def test_overlay_ignores_non_view3d_context_area_and_falls_back(self):
        area = _FakeArea()
        context = SimpleNamespace(
            area=SimpleNamespace(type="PROPERTIES"),
            window=SimpleNamespace(screen=SimpleNamespace(areas=[area])),
        )
        overlay = ImportProgressOverlay(context, space_view_3d=_FakeSpaceView3D)

        overlay.start(_state())

        self.assertIs(area, overlay.area)
        self.assertTrue(overlay.active)

    def test_overlay_matches_rna_area_by_pointer_not_python_identity(self):
        class PointerArea:
            type = "VIEW_3D"

            def as_pointer(self):
                return 1234

        self.assertTrue(ImportProgressOverlay._areas_match(PointerArea(), PointerArea()))

    def test_overlay_primary_and_diagnostic_copy_is_dominant_and_factual(self):
        overlay = ImportProgressOverlay(self.context, space_view_3d=_FakeSpaceView3D)
        overlay.start(_state())

        lines = overlay.text_lines()

        self.assertEqual("LOADING", lines[0])
        self.assertIn("UnityPackageを読み込んでいます", lines)
        self.assertIn("お待ちください", lines)
        self.assertIn("Analyzing Prefabs", lines)
        self.assertIn("3 / 8 — UV2.prefab", lines)
        self.assertIn("Elapsed: 23 sec", lines)

    def test_blocking_fbx_copy_explains_temporary_unresponsive_state(self):
        overlay = ImportProgressOverlay(self.context, space_view_3d=_FakeSpaceView3D)
        overlay.start(
            _state(
                stage="IMPORTING_FBX",
                current_item="Avatar.fbx",
                current_index=1,
                current_total=1,
                blocking_operation=True,
            )
        )

        lines = overlay.text_lines()

        self.assertEqual("LOADING", lines[0])
        self.assertIn("モデルを読み込んでいます", lines)
        self.assertIn("Importing FBX: Avatar.fbx", lines)
        self.assertIn("この処理中はBlenderが一時的に応答しなくなる場合があります。", lines)

    def test_finish_removes_handler_and_is_idempotent(self):
        overlay = ImportProgressOverlay(self.context, space_view_3d=_FakeSpaceView3D)
        overlay.start(_state())

        overlay.finish()
        overlay.finish()

        self.assertFalse(overlay.active)
        self.assertEqual(1, len(_FakeSpaceView3D.removed))
        self.assertIsNone(overlay.snapshot)

    def test_blender_sink_keeps_overlay_lifecycle_in_step_with_progress_sink(self):
        from unitypackage_blender_importer.tests.test_ui_lifecycle import FakeContext
        from unitypackage_blender_importer.operators import import_unitypackage as module
        from unitypackage_blender_importer.unity.import_progress import ImportProgressMonitor

        class FakeOverlay:
            active = False
            area = object()

            def __init__(self, _context):
                self.starts = 0
                self.updates = 0
                self.finishes = 0

            def start(self, _state):
                self.starts += 1
                self.active = True

            def update(self, _state):
                self.updates += 1

            def finish(self):
                self.finishes += 1
                self.active = False

        with patch.object(module, "ImportProgressOverlay", FakeOverlay):
            sink = module._BlenderProgressSink(FakeContext())
            monitor = ImportProgressMonitor(sink=sink, clock=lambda: 100.0)
            monitor.start()
            monitor.set_stage("ANALYZING_PREFABS", current_index=1, current_total=2)
            monitor.complete()

        self.assertEqual(1, sink.overlay.starts)
        self.assertEqual(2, sink.overlay.updates)
        self.assertEqual(1, sink.overlay.finishes)


if __name__ == "__main__":
    unittest.main()
