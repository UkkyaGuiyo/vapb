from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import tempfile
from time import perf_counter
import unittest
from unittest.mock import Mock, patch


def _install_blender_stubs() -> None:
    if "bpy" in sys.modules:
        return

    bpy = ModuleType("bpy")

    class Operator:
        def __init__(self, *args, **kwargs):
            self._blender_init_args = args
            self._blender_init_kwargs = kwargs

    bpy.types = SimpleNamespace(Operator=Operator, Material=object, Object=object)
    bpy.app = SimpleNamespace(background=False)

    props = ModuleType("bpy.props")
    props.StringProperty = lambda **kwargs: kwargs.get("default", "")
    props.BoolProperty = lambda **kwargs: kwargs.get("default", False)
    props.EnumProperty = lambda **kwargs: kwargs.get("default", "")
    bpy.props = props
    sys.modules["bpy"] = bpy
    sys.modules["bpy.props"] = props

    bpy_extras = ModuleType("bpy_extras")
    io_utils = ModuleType("bpy_extras.io_utils")

    class ImportHelper:
        pass

    class ExportHelper:
        pass

    io_utils.ImportHelper = ImportHelper
    io_utils.ExportHelper = ExportHelper
    bpy_extras.io_utils = io_utils
    sys.modules["bpy_extras"] = bpy_extras
    sys.modules["bpy_extras.io_utils"] = io_utils

    mathutils = ModuleType("mathutils")

    class Matrix:
        def __init__(self, *_args):
            pass

        def __matmul__(self, _other):
            return self

        def inverted(self):
            return self

        def to_quaternion(self):
            return self

    class Vector:
        def __init__(self, value):
            self.value = tuple(value)

        def to_tuple(self):
            return self.value

    class Quaternion:
        def __init__(self, value):
            self.value = value

        def to_matrix(self):
            return Matrix()

    mathutils.Matrix = Matrix
    mathutils.Vector = Vector
    mathutils.Quaternion = Quaternion
    sys.modules["mathutils"] = mathutils


_install_blender_stubs()

from unitypackage_blender_importer.blender.performance import PerformanceTimer
from unitypackage_blender_importer.operators import import_unitypackage as module


class FakeTimer:
    pass


class FakeWindowManager:
    def __init__(self):
        self.modal_calls = 0
        self.timer_add_calls = 0
        self.timer_remove_calls = 0
        self.dialog_calls = 0
        self.progress_end_calls = 0
        self.last_timer = None

    def modal_handler_add(self, _operator):
        self.modal_calls += 1

    def event_timer_add(self, _interval, window=None):
        self.timer_add_calls += 1
        self.last_timer = FakeTimer()
        return self.last_timer

    def event_timer_remove(self, timer):
        assert timer is self.last_timer
        self.timer_remove_calls += 1

    def invoke_props_dialog(self, _operator, width=0):
        self.dialog_calls += 1

    def progress_end(self):
        self.progress_end_calls += 1

    def progress_begin(self, *_args):
        pass

    def progress_update(self, _value):
        pass


class FakeContext:
    def __init__(self):
        self.window_manager = FakeWindowManager()
        self.window = object()
        self.scene = SimpleNamespace()


def _prepared():
    return module._PreparedImport(None, None, None, None, [], [], {})


def _operator() -> module.UNITYPACKAGE_OT_import:
    operator = module.UNITYPACKAGE_OT_import()
    operator.filepath = "avatar.unitypackage"
    operator.import_mode = "RECONSTRUCT"
    operator.prefab_choice = "AUTO"
    operator.use_armatures = True
    operator.use_bone_weights = True
    operator.use_shape_keys = True
    operator.use_materials = True
    operator.use_textures = True
    operator.apply_prefab_transforms = True
    operator.keep_extracted = True
    operator.report = Mock()
    operator._performance = PerformanceTimer()
    return operator


def _event(event_type: str, timer=None):
    return SimpleNamespace(type=event_type, timer=timer)


class UILifecycleTests(unittest.TestCase):
    def setUp(self):
        module.bpy.app.background = False

    def test_foreground_async_start_registers_modal_handler_exactly_once(self):
        operator = _operator()
        context = FakeContext()
        operator._start_async_prepare = Mock(wraps=operator._start_async_prepare)
        with patch.object(operator, "_prepare_worker", return_value=_prepared()):
            result = operator.execute(context)
            self.assertEqual({"RUNNING_MODAL"}, result)
            self.assertEqual(1, context.window_manager.modal_calls)
            self.assertTrue(operator._modal_registered)
            operator.execute(context)
        self.assertEqual(1, context.window_manager.modal_calls)
        operator.cancel(context)

    def test_blender_constructor_args_are_forwarded_and_state_is_initialized(self):
        sentinel = object()
        operator = module.UNITYPACKAGE_OT_import(sentinel, internal=True)
        self.assertEqual((sentinel,), operator._blender_init_args)
        self.assertEqual({"internal": True}, operator._blender_init_kwargs)
        self.assertEqual("IDLE", operator._prepare_state)
        self.assertFalse(operator._modal_registered)
        self.assertFalse(operator._prepare_result_consumed)
        self.assertEqual(module._DEFAULT_PREFAB_ITEMS, operator._prefab_items)

    def test_foreground_async_start_creates_one_timer(self):
        operator = _operator()
        context = FakeContext()
        with patch.object(operator, "_prepare_worker", return_value=_prepared()):
            operator.execute(context)
            operator._start_async_prepare(context, Path("second.unitypackage"))
        self.assertEqual(1, context.window_manager.timer_add_calls)
        operator.cancel(context)

    def test_timer_before_worker_completion_keeps_preparing(self):
        operator = _operator()
        context = FakeContext()
        pending = Future()
        operator._prepare_state = "PREPARING"
        operator._prepare_future = pending
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        self.assertEqual({"RUNNING_MODAL"}, operator.modal(context, _event("TIMER", operator._prepare_timer)))
        self.assertEqual("PREPARING", operator._prepare_state)
        pending.cancel()

    def test_completed_worker_timer_reaches_import(self):
        operator = _operator()
        context = FakeContext()
        future = Future()
        future.set_result(_prepared())
        operator._prepare_state = "PREPARING"
        operator._prepare_future = future
        operator._prepare_window_manager = context.window_manager
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        with patch.object(module, "_schedule_prepared_session") as schedule:
            result = operator.modal(context, _event("TIMER", operator._prepare_timer))
        self.assertEqual({"FINISHED"}, result)
        schedule.assert_called_once()
        self.assertEqual("PREPARED", operator._prepare_state)
        self.assertFalse(operator._modal_registered)

    def test_completed_worker_removes_timer_before_import(self):
        operator = _operator()
        context = FakeContext()
        future = Future()
        future.set_result(_prepared())
        operator._prepare_state = "PREPARING"
        operator._prepare_future = future
        operator._prepare_window_manager = context.window_manager
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        with patch.object(module, "_schedule_prepared_session"):
            operator.modal(context, _event("TIMER", operator._prepare_timer))
        self.assertEqual(1, context.window_manager.timer_remove_calls)
        self.assertIsNone(operator._prepare_timer)
        self.assertIsNone(operator._prepare_executor)

    def test_completed_worker_ends_modal_before_prefab_handoff(self):
        operator = _operator()
        context = FakeContext()
        future = Future()
        future.set_result(
            module._PreparedImport(
                None, None, None, None, [], [Path("one.prefab"), Path("two.prefab")], {}
            )
        )
        operator._prepare_state = "PREPARING"
        operator._prepare_future = future
        operator._prepare_window_manager = context.window_manager
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        with patch.object(module, "_schedule_prepared_session") as schedule:
            result = operator.modal(context, _event("TIMER", operator._prepare_timer))
        self.assertEqual({"FINISHED"}, result)
        self.assertEqual("PREPARED", operator._prepare_state)
        self.assertFalse(operator._modal_registered)
        schedule.assert_called_once()
        self.assertTrue(schedule.call_args.kwargs["show_dialog"])

    def test_prepared_operator_runs_session_and_removes_it(self):
        operator = _operator()
        context = FakeContext()
        operator._prepare_state = "PREPARED"
        operator._run_import = Mock(return_value={"FINISHED"})
        session_id = "session-test"
        module._PREPARED_SESSIONS[session_id] = module._PreparedSession(
            session_id, operator, 0.0
        )
        prepared = module.UNITYPACKAGE_OT_import_prepared()
        prepared.session_id = session_id
        self.assertEqual({"FINISHED"}, prepared.execute(context))
        operator._run_import.assert_called_once_with(context)
        self.assertNotIn(session_id, module._PREPARED_SESSIONS)

    def test_prefab_operator_defers_import_to_next_turn(self):
        operator = _operator()
        operator._prefab_items = [
            ("AUTO", "Automatic", "", 0),
            ("PREFAB_0", "one", "one.prefab", 1),
        ]
        session_id = "session-prefab"
        module._PREPARED_SESSIONS[session_id] = module._PreparedSession(
            session_id, operator, 0.0
        )
        selector = module.UNITYPACKAGE_OT_import_prefab()
        selector.session_id = session_id
        selector.prefab_choice = "PREFAB_0"
        with patch.object(module, "_schedule_prepared_session") as schedule:
            self.assertEqual({"FINISHED"}, selector.execute(FakeContext()))
        self.assertEqual("PREFAB_0", operator.prefab_choice)
        schedule.assert_called_once_with(session_id, show_dialog=False)
        module._PREPARED_SESSIONS.pop(session_id, None)

    def test_prefab_selection_runs_visual_discovery_and_opens_group_dialog(self):
        operator = _operator()
        with tempfile.NamedTemporaryFile(suffix=".unitypackage") as package_file:
            operator.filepath = package_file.name
            operator._prefab_paths = [Path("one.prefab")]
            operator._extraction_dir = None
            operator._discover_selected_visual_dependencies = Mock()
            operator._sibling_discovery = SimpleNamespace(packages=[object()], visual_status="COMPLETE")
            session_id = "session-grouped-prefab"
            module._PREPARED_SESSIONS[session_id] = module._PreparedSession(session_id, operator, 0.0)
            selector = module.UNITYPACKAGE_OT_import_prefab()
            selector.session_id = session_id
            selector.prefab_choice = "PREFAB_0"
            with patch.object(module, "_schedule_prepared_session") as schedule:
                self.assertEqual({"FINISHED"}, selector.execute(FakeContext()))
            operator._discover_selected_visual_dependencies.assert_called_once_with()
            schedule.assert_called_once_with(session_id, show_dialog=False, show_group_dialog=True)
            module._PREPARED_SESSIONS.pop(session_id, None)

    def test_prepared_session_watchdog_cleans_expired_session(self):
        operator = _operator()
        context = FakeContext()
        operator._progress_active = True
        session_id = "expired-session"
        module._PREPARED_SESSIONS[session_id] = module._PreparedSession(
            session_id,
            operator,
            perf_counter() - module._SESSION_TIMEOUT_SECONDS - 1.0,
            context.window_manager,
        )
        callbacks = []
        module.bpy.app.timers = SimpleNamespace(
            register=lambda callback, first_interval=0.0: callbacks.append(callback)
        )
        module._schedule_prepared_session(session_id, show_dialog=True)
        callbacks[0]()
        self.assertNotIn(session_id, module._PREPARED_SESSIONS)
        self.assertEqual(1, context.window_manager.progress_end_calls)

    def test_prepared_operator_exception_cleans_session_after_lookup(self):
        operator = _operator()
        context = FakeContext()
        operator._prepare_state = "PREPARED"
        operator._run_import = Mock(side_effect=RuntimeError("import failed"))
        session_id = "exception-session"
        module._PREPARED_SESSIONS[session_id] = module._PreparedSession(
            session_id, operator, perf_counter(), context.window_manager
        )
        prepared = module.UNITYPACKAGE_OT_import_prepared()
        prepared.session_id = session_id
        with self.assertRaises(RuntimeError):
            prepared.execute(context)
        self.assertNotIn(session_id, module._PREPARED_SESSIONS)

    def test_worker_exception_cancels_and_reports(self):
        operator = _operator()
        context = FakeContext()
        future = Future()
        future.set_exception(RuntimeError("worker failed"))
        operator._prepare_state = "PREPARING"
        operator._prepare_future = future
        operator._prepare_window_manager = context.window_manager
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        result = operator.modal(context, _event("TIMER", operator._prepare_timer))
        self.assertEqual({"CANCELLED"}, result)
        self.assertEqual("ERROR", operator._prepare_state)
        operator.report.assert_called_once()
        self.assertEqual(1, context.window_manager.timer_remove_calls)

    def test_escape_during_preparing_cancels_and_cleans(self):
        operator = _operator()
        context = FakeContext()
        temp_dir = Path(tempfile.mkdtemp())
        operator._prepare_state = "PREPARING"
        operator._extraction_dir = temp_dir
        operator._progress_active = True
        self.assertEqual({"CANCELLED"}, operator.modal(context, _event("ESC")))
        self.assertEqual("CANCELLED", operator._prepare_state)
        self.assertFalse(temp_dir.exists())

    def test_cancel_after_worker_finished_before_timer_collect_cleans_result(self):
        operator = _operator()
        context = FakeContext()
        temp_dir = Path(tempfile.mkdtemp())
        future = Future()
        future.set_result(
            module._PreparedImport(
                None,
                temp_dir,
                None,
                None,
                [],
                [],
                {},
            )
        )
        operator._prepare_state = "PREPARING"
        operator._prepare_future = future
        operator._prepare_window_manager = context.window_manager
        operator._prepare_timer = context.window_manager.event_timer_add(0.25, window=context.window)
        operator.cancel(context)
        self.assertEqual("CANCELLED", operator._prepare_state)
        self.assertFalse(temp_dir.exists())
        self.assertIsNone(operator._prepare_future)

    def test_non_timer_event_passes_through(self):
        operator = _operator()
        context = FakeContext()
        operator._prepare_state = "PREPARING"
        self.assertEqual({"PASS_THROUGH"}, operator.modal(context, _event("MOUSEMOVE")))

    def test_background_path_keeps_sync_prepare_without_modal_registration(self):
        operator = _operator()
        context = FakeContext()
        module.bpy.app.background = True
        operator.filepath = "avatar.unitypackage"
        operator._prepare_import = Mock()
        operator._run_import = Mock(return_value={"FINISHED"})
        result = operator.execute(context)
        self.assertEqual({"FINISHED"}, result)
        operator._prepare_import.assert_called_once_with(context, Path("avatar.unitypackage"))
        self.assertEqual(0, context.window_manager.modal_calls)

    def test_second_async_start_does_not_register_again(self):
        operator = _operator()
        context = FakeContext()
        with patch.object(operator, "_prepare_worker", return_value=_prepared()):
            operator._start_async_prepare(context, Path("avatar.unitypackage"))
            operator._start_async_prepare(context, Path("avatar.unitypackage"))
        self.assertEqual(1, context.window_manager.modal_calls)
        self.assertEqual(1, context.window_manager.timer_add_calls)
        operator.cancel(context)

    def test_new_operator_has_no_previous_prefab_state(self):
        first = _operator()
        first._prefab_items.append(("PREFAB_1", "old", "old", 1))
        second = _operator()
        self.assertEqual("IDLE", second._prepare_state)
        self.assertEqual(module._DEFAULT_PREFAB_ITEMS, second._prefab_items)
        self.assertNotIn("session_id", second.__dict__)


if __name__ == "__main__":
    unittest.main()
