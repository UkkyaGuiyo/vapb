"""Focused unit tests for the importer progress model."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from unitypackage_blender_importer.unity.import_progress import (
    ImportProgressMonitor,
    ImportProgressStage,
    ImportProgressStatus,
)


class _Sink:
    def __init__(self):
        self.updates = []
        self.cleared = 0

    def update(self, state):
        self.updates.append(state.snapshot())

    def clear(self):
        self.cleared += 1


class ImportProgressModelTests(unittest.TestCase):
    def test_ipm_001_progress_state_initializes_idle(self):
        monitor = ImportProgressMonitor(clock=lambda: 100.0)
        self.assertEqual(ImportProgressStatus.IDLE, monitor.state.status)
        self.assertEqual(ImportProgressStage.IDLE, monitor.state.stage)
        self.assertEqual(0, monitor.state.stage_index)
        self.assertIsNone(monitor.state.started_at)

    def test_ipm_002_start_transitions_to_working(self):
        monitor = ImportProgressMonitor(clock=lambda: 100.0)
        monitor.start()
        self.assertEqual(ImportProgressStatus.WORKING, monitor.state.status)
        self.assertEqual(ImportProgressStage.READING_PACKAGE, monitor.state.stage)
        self.assertEqual(100.0, monitor.state.started_at)

    def test_ipm_003_stage_transition_updates_last_activity(self):
        now = [100.0]
        monitor = ImportProgressMonitor(clock=lambda: now[0])
        monitor.start()
        now[0] = 101.5
        monitor.set_stage(ImportProgressStage.ANALYZING_PREFABS)
        self.assertEqual(101.5, monitor.state.last_activity_at)
        self.assertEqual(ImportProgressStage.ANALYZING_PREFABS, monitor.state.stage)
        now[0] = 103.0
        monitor.heartbeat()
        self.assertEqual(103.0, monitor.state.last_activity_at)
        self.assertEqual(103.0, monitor.history[-1]["last_activity_at"])

    def test_ipm_004_known_count_preserves_current_and_total(self):
        sink = _Sink()
        monitor = ImportProgressMonitor(sink=sink, clock=lambda: 100.0)
        monitor.start()
        monitor.set_stage(
            ImportProgressStage.ANALYZING_PREFABS,
            current_item="UV3.prefab",
            current_index=3,
            current_total=8,
        )
        self.assertEqual(3, monitor.state.current_index)
        self.assertEqual(8, monitor.state.current_total)
        self.assertIn("3/8", sink.updates[-1]["status_text"])

    def test_ipm_005_completion_clears_foreground_status(self):
        sink = _Sink()
        monitor = ImportProgressMonitor(sink=sink, clock=lambda: 100.0)
        monitor.start()
        monitor.complete()
        self.assertEqual(ImportProgressStatus.COMPLETE, monitor.state.status)
        self.assertEqual(1, sink.cleared)
        self.assertEqual(monitor.state.stage_count, monitor.state.stage_index)

    def test_ipm_006_failure_records_stage_and_reason(self):
        sink = _Sink()
        monitor = ImportProgressMonitor(sink=sink, clock=lambda: 100.0)
        monitor.start()
        monitor.set_stage(ImportProgressStage.BUILDING_HIERARCHY)
        monitor.fail("hierarchy failed")
        self.assertEqual(ImportProgressStatus.FAILED, monitor.state.status)
        self.assertEqual(ImportProgressStage.FAILED, monitor.state.stage)
        self.assertEqual("hierarchy failed", monitor.state.failure_message)
        self.assertEqual(1, sink.cleared)

    def test_ipm_007_child_does_not_destroy_parent_session(self):
        sink = _Sink()
        parent = ImportProgressMonitor(sink=sink, clock=lambda: 100.0)
        parent.start()
        child = parent.child("Provider.unitypackage")
        child.set_stage(ImportProgressStage.CREATING_VISUALS, current_item="Material.mat")
        child.close()
        self.assertEqual(ImportProgressStatus.WORKING, parent.state.status)
        self.assertEqual(0, sink.cleared)
        parent.complete()
        self.assertEqual(1, sink.cleared)

    def test_ipm_008_background_mode_requires_no_ui_context(self):
        monitor = ImportProgressMonitor(clock=lambda: 100.0)
        monitor.start()
        monitor.set_stage(ImportProgressStage.IMPORTING_FBX, current_item="Avatar.fbx", blocking_operation=True)
        monitor.complete()
        self.assertEqual(ImportProgressStatus.COMPLETE, monitor.state.status)

    def test_ipm_014_unknown_duration_has_no_fake_percentage(self):
        monitor = ImportProgressMonitor(clock=lambda: 100.0)
        monitor.start()
        monitor.set_stage(ImportProgressStage.IMPORTING_FBX, current_item="Avatar.fbx")
        self.assertIsNone(monitor.state.progress_fraction)

    def test_ipm_015_final_state_contains_elapsed_duration(self):
        now = [100.0]
        monitor = ImportProgressMonitor(clock=lambda: now[0])
        monitor.start()
        now[0] = 112.25
        monitor.complete()
        self.assertEqual(12.25, monitor.state.elapsed_seconds)

    def test_ipm_009_fbx_blocking_stage_is_published_before_native_call(self):
        from unitypackage_blender_importer.tests.test_ui_lifecycle import _install_blender_stubs
        _install_blender_stubs()
        from unitypackage_blender_importer.blender import fbx_importer

        events = []
        fake_bpy = SimpleNamespace(
            data=SimpleNamespace(objects=set()),
            ops=SimpleNamespace(import_scene=SimpleNamespace(fbx=lambda **_kwargs: events.append("native"))),
        )

        def progress(_path, _index, _total, blocking):
            events.append(("progress", blocking))

        with patch.object(fbx_importer, "bpy", fake_bpy):
            fbx_importer.import_fbx_files([Path("Avatar.fbx")], progress=progress)
        self.assertEqual([("progress", True), "native", ("progress", False)], events)

    def test_ipm_010_fbx_blocking_flag_clears_after_success(self):
        from unitypackage_blender_importer.tests.test_ui_lifecycle import _install_blender_stubs
        _install_blender_stubs()
        from unitypackage_blender_importer.blender import fbx_importer

        events = []
        fake_bpy = SimpleNamespace(
            data=SimpleNamespace(objects=set()),
            ops=SimpleNamespace(import_scene=SimpleNamespace(fbx=lambda **_kwargs: None)),
        )
        with patch.object(fbx_importer, "bpy", fake_bpy):
            fbx_importer.import_fbx_files(
                [Path("Avatar.fbx")],
                progress=lambda _path, _index, _total, blocking: events.append(blocking),
            )
        self.assertEqual([True, False], events)

    def test_ipm_011_fbx_failure_still_clears_blocking_flag(self):
        from unitypackage_blender_importer.tests.test_ui_lifecycle import _install_blender_stubs
        _install_blender_stubs()
        from unitypackage_blender_importer.blender import fbx_importer

        fake_bpy = SimpleNamespace(
            data=SimpleNamespace(objects=set()),
            ops=SimpleNamespace(import_scene=SimpleNamespace(fbx=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("native failure")))),
        )
        events = []
        with patch.object(fbx_importer, "bpy", fake_bpy):
            fbx_importer.import_fbx_files(
                [Path("Avatar.fbx")],
                progress=lambda _path, _index, _total, blocking: events.append(blocking),
            )
        self.assertEqual([True, False], events)

    def test_ipm_012_prefab_analysis_emits_actual_candidate_count(self):
        from unitypackage_blender_importer.unity import prefab_candidate_analyzer as module

        analyzer = object.__new__(module.PrefabCandidateAnalyzer)
        analyzer.prefab_paths = [Path("UV1.prefab"), Path("UV2.prefab")]
        analyzer.asset_db = None
        analyzer.extraction_root = Path(".")
        analyzer.package_path = Path("primary.unitypackage")
        fake_prefab = SimpleNamespace(
            renderer_documents=lambda: [SimpleNamespace(class_id=0)],
            display_name="Avatar",
            game_objects=[object()],
            transforms=[object()],
        )
        analyzer._prefab_refs = lambda _prefab: ({"f"}, set(), 1)
        analyzer._closure = lambda _direct: ({"f"}, {"f"}, set(), set(), set())
        analyzer._kind = lambda _prefab, _renderers, _skinned: "AVATAR_LIKE"
        analyzer._primary_record = lambda _path: ("a", None)
        analyzer._unity_path = lambda path: path.as_posix()
        events = []
        with patch.object(module, "parse_prefab", return_value=fake_prefab):
            analyzer.analyze(progress=lambda index, total, item: events.append((index, total, item.name)))
        self.assertEqual([(1, 2, "UV1.prefab"), (2, 2, "UV2.prefab")], events)

    def test_ipm_013_provider_discovery_emits_actual_provider_count(self):
        from unitypackage_blender_importer.unity import sibling_discovery as module

        root = Path("primary.unitypackage")
        provider = Path("provider.unitypackage")
        root_entries = [module.PackageManifestEntry("prefab", "Assets/Main.prefab", ".prefab", True, False)]
        provider_entries = [module.PackageManifestEntry("dep", "Assets/Surface.mat", ".mat", True, False)]
        calls = []

        with patch.object(module, "_manifest", side_effect=[root_entries, provider_entries]), \
                patch.object(module, "_candidate_paths", return_value=[provider]), \
                patch.object(module, "_visual_requirements_for_guids", side_effect=[{"dep"}, set()]), \
                patch.object(module.PackageIdentity, "from_path", return_value=SimpleNamespace(source_package_id="provider-id")):
            result = module.discover_siblings(root, progress=lambda index, total, item: calls.append((index, total, item.name)))
        self.assertEqual("COMPLETE", result.visual_status)
        self.assertEqual([(1, 1, "provider.unitypackage")], calls)


if __name__ == "__main__":
    unittest.main()
