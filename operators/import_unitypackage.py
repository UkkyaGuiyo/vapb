"""Blender File > Import operator for UnityPackage files."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import SimpleQueue
import shutil
import tempfile
from threading import Event
from time import perf_counter
from typing import Any
from uuid import uuid4

import bpy  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy.props import BoolProperty, EnumProperty, StringProperty  # type: ignore

from ..blender.fbx_importer import apply_import_options, import_fbx_files
from ..blender.hierarchy_builder import build_prefab_hierarchy
from ..blender.identity_registry import load_scene_registry, register_datablocks, register_package, save_scene_registry
from ..blender.material_builder import apply_materials_by_name, apply_prefab_materials, build_material_library
from ..blender.texture_loader import load_textures_from_database
from ..blender.dependency_resolver import capture_material_texture_dependencies, load_dependency_registry, resolve_after_import
from ..blender.performance import PerformanceTimer
from ..ui.import_panel import draw_import_options
from ..unity.asset_database import AssetDatabase
from ..unity.package_identity import PackageIdentity
from ..unity.package_reader import PackageIndex, UnityPackageError, UnityPackageReader, is_unitypackage
from ..unity.material_mapping import parse_external_objects
from ..unity.material_parser import parse_material
from ..unity.prefab_parser import parse_prefab
from ..unity.sibling_discovery import discover_siblings


_DEFAULT_PREFAB_ITEMS: list[tuple[str, str, str, int]] = [("AUTO", "Automatic", "Use the first prefab", 0)]
_SESSION_TIMEOUT_SECONDS = 300.0
_PREPARED_SESSIONS: dict[str, "_PreparedSession"] = {}


PREPARE_STATES = {
    "IDLE",
    "FILE_SELECTED",
    "PREPARING",
    "PREPARED",
    "IMPORTING",
    "FINISHED",
    "CANCELLED",
    "ERROR",
}


def _prefab_items(_self, _context):
    return getattr(_self, "_prefab_items", _DEFAULT_PREFAB_ITEMS)


@dataclass
class _PreparedImport:
    package_key: PackageIdentity
    extraction_dir: Path | None
    extraction: Any
    asset_db: AssetDatabase | None
    fbx_paths: list[Path]
    prefab_paths: list[Path]
    timings: dict[str, float]
    package_reader: UnityPackageReader | None = None
    package_index: PackageIndex | None = None
    reused: bool = False


@dataclass
class _PreparedSession:
    session_id: str
    operator: "UNITYPACKAGE_OT_import"
    created_at: float
    window_manager: Any = None


def _session_prefab_items(_self, _context):
    session = _PREPARED_SESSIONS.get(getattr(_self, "session_id", ""))
    if session is None:
        return _DEFAULT_PREFAB_ITEMS
    return session.operator._prefab_items


def _discard_prepared_session(session_id: str, context=None) -> None:
    session = _PREPARED_SESSIONS.pop(session_id, None)
    if session is None:
        return
    operator = session.operator
    operator._prepare_cancel.set()
    operator._stop_async_prepare(wait=True)
    operator._cleanup_prepared(remove=True)
    operator._modal_registered = False
    if context is not None:
        operator._finish_performance(context)
    else:
        if operator._progress_active and session.window_manager is not None:
            try:
                session.window_manager.progress_end()
            except (AttributeError, RuntimeError):
                pass
        operator._progress_active = False
        if operator._performance is not None:
            operator._performance.finish()
            operator._performance.emit()
            operator._performance = None


def _schedule_prepared_session(session_id: str, *, show_dialog: bool) -> None:
    launched = False

    def handoff():
        nonlocal launched
        session = _PREPARED_SESSIONS.get(session_id)
        if session is None:
            return None
        if perf_counter() - session.created_at > _SESSION_TIMEOUT_SECONDS:
            _discard_prepared_session(session_id)
            return None
        if not launched:
            launched = True
            try:
                if show_dialog:
                    bpy.ops.import_scene.unitypackage_prefab(
                        "INVOKE_DEFAULT", session_id=session_id
                    )
                else:
                    bpy.ops.import_scene.unitypackage_prepared(
                        "EXEC_DEFAULT", session_id=session_id
                    )
            except Exception as exc:
                print(f"[UnityPackage Importer] Prepared session handoff failed: {exc}")
                _discard_prepared_session(session_id)
                return None
        # Keep a lightweight watchdog while the user dialog is open.
        return 1.0

    timers = getattr(getattr(bpy, "app", None), "timers", None)
    if timers is None or not hasattr(timers, "register"):
        handoff()
        return
    timers.register(handoff, first_interval=0.0)


class UNITYPACKAGE_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.unitypackage"
    bl_label = "Import Unity Package / VRChat Avatar"
    bl_description = "Import FBX, textures, basic materials, and prefab transforms from a UnityPackage"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".unitypackage"
    filter_glob: StringProperty(default="*.unitypackage", options={"HIDDEN"})

    import_mode: EnumProperty(
        name="Import Mode",
        items=[
            ("RECONSTRUCT", "Reconstruct Prefab", "Use prefab hierarchy and transforms when available"),
            ("RAW_FBX", "Import Raw FBX", "Import detected FBX files without prefab reconstruction"),
        ],
        default="RECONSTRUCT",
    )
    prefab_choice: EnumProperty(name="Prefab", items=_prefab_items)
    use_armatures: BoolProperty(name="Armature", default=True)
    use_bone_weights: BoolProperty(name="Bone Weights", default=True)
    use_shape_keys: BoolProperty(name="Shape Keys", default=True)
    use_materials: BoolProperty(name="Materials", default=True)
    use_textures: BoolProperty(name="Textures", default=True)
    apply_prefab_transforms: BoolProperty(name="Apply Prefab Transforms", default=True)
    keep_extracted: BoolProperty(
        name="Keep Extracted Files",
        default=True,
        description="Keep the extracted source so external texture paths remain available",
    )
    include_sibling_packages: BoolProperty(
        name="Import uniquely matched sibling Packages",
        default=False,
        description="Discover and import same-directory Packages with unique GUID dependency matches",
    )
    group_child: BoolProperty(options={"HIDDEN"}, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_state = "IDLE"
        self._modal_registered = False
        self._prepare_result_consumed = False
        self._prefab_items = list(_DEFAULT_PREFAB_ITEMS)
        self._prepared_package_key: PackageIdentity | None = None
        self._extraction_dir: Path | None = None
        self._extraction = None
        self._asset_db = None
        self._fbx_paths: list[Path] = []
        self._prefab_paths: list[Path] = []
        self._package_reader: UnityPackageReader | None = None
        self._package_index: PackageIndex | None = None
        self._performance: PerformanceTimer | None = None
        self._progress_active = False
        self._prepare_executor: ThreadPoolExecutor | None = None
        self._prepare_future: Future | None = None
        self._prepare_timer = None
        self._prepare_window_manager = None
        self._prepare_cancel = Event()
        self._prepare_events: SimpleQueue[str] = SimpleQueue()

    def _ui_log(self, message: str) -> None:
        print(f"[UI] {message}")

    def _set_prepare_state(self, state: str) -> None:
        if state not in PREPARE_STATES:
            raise ValueError(f"Unknown prepare state: {state}")
        previous = self._prepare_state
        if previous != state:
            self._prepare_state = state
            self._ui_log(f"{previous} -> {state}")

    def draw(self, context):
        draw_import_options(self.layout, self)

    def _set_phase(self, context, phase: str, progress: float) -> None:
        if self._progress_active:
            context.window_manager.progress_update(progress)
        self.report({"INFO"}, f"UnityPackage: {phase}")

    def _begin_progress(self, context) -> None:
        if not self._progress_active:
            context.window_manager.progress_begin(0.0, 1.0)
            self._progress_active = True

    def _end_progress(self, context) -> None:
        if self._progress_active:
            context.window_manager.progress_end()
            self._progress_active = False

    def _cleanup_prepared(self, remove: bool) -> None:
        extraction_dir = self._extraction_dir
        self._prepared_package_key = None
        self._extraction_dir = None
        self._extraction = None
        self._asset_db = None
        self._fbx_paths = []
        self._prefab_paths = []
        self._package_reader = None
        self._package_index = None
        if remove and extraction_dir is not None:
            shutil.rmtree(extraction_dir, ignore_errors=True)

    def _finish_performance(self, context) -> None:
        self._end_progress(context)
        if self._performance is None:
            return
        self._performance.finish()
        self._performance.emit()
        self._performance = None

    def _prepare_worker(
        self,
        package_path: Path,
        existing_key: PackageIdentity | None,
        existing_ready: bool,
        existing_extraction_dir: Path | None,
        existing_extraction,
        existing_asset_db,
        existing_fbx_paths: list[Path],
        existing_prefab_paths: list[Path],
        existing_package_reader: UnityPackageReader | None,
        existing_package_index: PackageIndex | None,
        cancel_event: Event,
        events: SimpleQueue[str] | None,
    ) -> _PreparedImport:
        timings: dict[str, float] = {}

        def phase(message: str) -> None:
            if events is not None:
                events.put(message)

        def timed(name: str, function, *args, **kwargs):
            started = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                timings[name] = timings.get(name, 0.0) + perf_counter() - started

        phase("Checking Package identity")
        package_key = timed("package_identity", PackageIdentity.from_path, package_path)
        if existing_ready and existing_key == package_key:
            return _PreparedImport(
                package_key,
                existing_extraction_dir,
                existing_extraction,
                existing_asset_db,
                list(existing_fbx_paths),
                list(existing_prefab_paths),
                timings,
                existing_package_reader,
                existing_package_index,
                reused=True,
            )

        extraction_dir = Path(tempfile.mkdtemp(prefix="unitypackage_blender_importer_"))
        reader = UnityPackageReader(package_path)
        try:
            phase("Indexing UnityPackage in archive order")
            package_index = reader.build_index()
            planning_guids = {
                guid
                for guid, record in package_index.records.items()
                if Path(record.unity_path).suffix.lower() in {".prefab", ".mat"}
            }
            phase("Extracting dependency candidates")
            extraction = reader.extract_selective(
                extraction_dir,
                package_index,
                planning_guids,
                cancel_check=cancel_event.is_set,
            )
            for phase_name, seconds in reader.last_timings.items():
                timings[phase_name] = timings.get(phase_name, 0.0) + seconds

            phase("Building Asset Database")
            asset_db = timed(
                "asset_database",
                AssetDatabase.from_package_index,
                extraction.root,
                package_index,
                extraction.assets,
                package_key.source_package_id,
            )
            phase("Scanning meta files")
            timed("meta_scan", asset_db.scan_missing_meta)
            phase("Scanning FBX")
            fbx_paths = timed("fbx_scan", asset_db.fbxs)
            phase("Scanning Prefabs")
            prefab_paths = timed("prefab_scan", asset_db.prefabs)
        except Exception:
            shutil.rmtree(extraction_dir, ignore_errors=True)
            raise

        if cancel_event.is_set():
            shutil.rmtree(extraction_dir, ignore_errors=True)
            raise UnityPackageError("Import cancelled")

        return _PreparedImport(
            package_key,
            extraction_dir,
            extraction,
            asset_db,
            list(fbx_paths),
            list(prefab_paths),
            timings,
            reader,
            package_index,
        )

    def _apply_prepared(self, context, prepared: _PreparedImport) -> None:
        for phase, seconds in prepared.timings.items():
            self._performance.add(phase, seconds)
        if prepared.reused:
            self._prepared_package_key = prepared.package_key
            self._set_prepare_state("PREPARED")
            self._set_phase(context, "Reusing prepared asset index", 0.30)
            return
        if self._extraction is not None:
            self._cleanup_prepared(remove=True)
        self._prepared_package_key = prepared.package_key
        self._extraction_dir = prepared.extraction_dir
        self._extraction = prepared.extraction
        self._asset_db = prepared.asset_db
        self._fbx_paths = prepared.fbx_paths
        self._prefab_paths = prepared.prefab_paths
        self._package_reader = prepared.package_reader
        self._package_index = prepared.package_index
        self._set_prepare_state("PREPARED")
        self._set_phase(context, "Asset index ready", 0.30)

    def _prepare_import(self, context, package_path: Path) -> None:
        self._set_prepare_state("PREPARING")
        prepared = self._prepare_worker(
            package_path,
            self._prepared_package_key,
            self._extraction is not None,
            self._extraction_dir,
            self._extraction,
            self._asset_db,
            self._fbx_paths,
            self._prefab_paths,
            self._package_reader,
            self._package_index,
            Event(),
            None,
        )
        self._apply_prepared(context, prepared)

    def _start_async_prepare(self, context, package_path: Path) -> None:
        if self._prepare_state == "PREPARING" or self._prepare_future is not None:
            return
        if self._prepare_timer is not None or self._modal_registered:
            raise RuntimeError("Async prepare lifecycle is already active")
        self._set_prepare_state("PREPARING")
        self._prepare_result_consumed = False
        self._prepare_cancel = Event()
        self._prepare_events = SimpleQueue()
        self._prepare_window_manager = context.window_manager
        try:
            self._prepare_window_manager.modal_handler_add(self)
            self._modal_registered = True
            self._ui_log("modal handler registered")
            self._prepare_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="unitypackage-prepare")
            self._prepare_future = self._prepare_executor.submit(
                self._prepare_worker,
                package_path,
                self._prepared_package_key,
                self._extraction is not None,
                self._extraction_dir,
                self._extraction,
                self._asset_db,
                list(self._fbx_paths),
                list(self._prefab_paths),
                self._package_reader,
                self._package_index,
                self._prepare_cancel,
                self._prepare_events,
            )
            self._ui_log("worker submitted")
            self._prepare_timer = self._prepare_window_manager.event_timer_add(0.25, window=context.window)
            self._ui_log("timer registered")
        except Exception:
            self._stop_async_prepare()
            self._modal_registered = False
            raise
        self._set_phase(context, "Preparing UnityPackage in background", 0.05)

    def _discard_uncollected_prepare_result(self, future: Future | None) -> None:
        if future is None or not future.done():
            return
        try:
            prepared = future.result()
        except Exception:
            return
        if prepared.reused or prepared.extraction_dir is None:
            return
        if prepared.extraction_dir != self._extraction_dir:
            shutil.rmtree(prepared.extraction_dir, ignore_errors=True)

    def _stop_async_prepare(self, *, wait: bool = False) -> None:
        if self._prepare_timer is not None:
            try:
                if self._prepare_window_manager is not None:
                    self._prepare_window_manager.event_timer_remove(self._prepare_timer)
            except (AttributeError, RuntimeError):
                pass
            self._prepare_timer = None
            self._ui_log("timer removed")
        self._prepare_window_manager = None
        future = self._prepare_future
        executor = self._prepare_executor
        self._prepare_executor = None
        if executor is not None:
            executor.shutdown(wait=wait, cancel_futures=True)
            self._ui_log("executor shutdown")
        if wait:
            self._discard_uncollected_prepare_result(future)
        self._prepare_future = None

    def _drain_prepare_events(self, context) -> None:
        progress = {
            "Checking Package identity": 0.05,
            "Indexing UnityPackage in archive order": 0.10,
            "Extracting dependency candidates": 0.16,
            "Building Asset Database": 0.20,
            "Scanning meta files": 0.25,
            "Scanning FBX": 0.28,
            "Scanning Prefabs": 0.30,
        }
        while True:
            try:
                message = self._prepare_events.get_nowait()
            except Exception:
                return
            self._set_phase(context, message, progress.get(message, 0.10))

    def _complete_async_prepare(self, context):
        self._drain_prepare_events(context)
        future = self._prepare_future
        if self._prepare_state != "PREPARING" or future is None or self._prepare_result_consumed:
            return {"PASS_THROUGH"}
        if not future.done():
            return {"RUNNING_MODAL"}
        self._prepare_result_consumed = True
        try:
            prepared = future.result()
        except Exception as exc:
            self._stop_async_prepare()
            self._modal_registered = False
            self._set_prepare_state("CANCELLED" if self._prepare_cancel.is_set() else "ERROR")
            self._cleanup_prepared(remove=True)
            self._finish_performance(context)
            if not self._prepare_cancel.is_set():
                self.report({"ERROR"}, str(exc))
                print(f"[UnityPackage Importer] Import preparation failed: {exc}")
            return {"CANCELLED"}
        self._stop_async_prepare()
        if self._prepare_cancel.is_set():
            self._modal_registered = False
            self._set_prepare_state("CANCELLED")
            self._cleanup_prepared(remove=True)
            self._finish_performance(context)
            return {"CANCELLED"}
        self._ui_log("worker completed")
        self._apply_prepared(context, prepared)
        session_id = uuid4().hex
        self._prefab_items = [("AUTO", "Automatic (first prefab)", "Use the first detected prefab", 0)]
        self._prefab_items.extend(
            (f"PREFAB_{index}", path.name, str(path), index + 1)
            for index, path in enumerate(self._prefab_paths)
        )
        _PREPARED_SESSIONS[session_id] = _PreparedSession(
            session_id, self, perf_counter(), context.window_manager
        )
        show_dialog = self.import_mode == "RECONSTRUCT" and len(self._prefab_paths) > 1
        if show_dialog:
            self._set_prepare_state("PREPARED")
            self._set_phase(context, "Waiting for Prefab selection", 0.30)
        self._stop_async_prepare()
        # Returning FINISHED is the actual WindowManager modal-handler removal.
        self._modal_registered = False
        self._ui_log(f"prepare modal handoff session={session_id} dialog={show_dialog}")
        _schedule_prepared_session(session_id, show_dialog=show_dialog)
        return {"FINISHED"}

    def _selected_prefab(self, prefab_paths: list[Path]) -> Path | None:
        if not prefab_paths:
            return None
        if self.prefab_choice.startswith("PREFAB_"):
            try:
                return prefab_paths[int(self.prefab_choice.split("_", 1)[1])]
            except (ValueError, IndexError):
                pass
        return prefab_paths[0]

    def cancel(self, context):
        if self._prepare_state in {"CANCELLED", "FINISHED"}:
            return
        self._prepare_cancel.set()
        self._stop_async_prepare(wait=True)
        self._cleanup_prepared(remove=True)
        self._modal_registered = False
        self._set_prepare_state("CANCELLED")
        self._finish_performance(context)

    def modal(self, context, event):
        if event.type == "ESC" and self._prepare_state in {"PREPARING", "PREPARED", "IMPORTING"}:
            self.cancel(context)
            return {"CANCELLED"}
        event_timer = getattr(event, "timer", None)
        if (
            event.type == "TIMER"
            and self._prepare_timer is not None
            and (event_timer is None or event_timer == self._prepare_timer)
            and self._prepare_state == "PREPARING"
        ):
            return self._complete_async_prepare(context)
        return {"PASS_THROUGH"}

    def execute(self, context):
        package_path = Path(self.filepath)
        if not is_unitypackage(package_path):
            self.report({"ERROR"}, "Select a .unitypackage file")
            return {"CANCELLED"}
        if self._prepare_state == "PREPARING":
            return {"RUNNING_MODAL"}
        if self._prepare_state in {"IMPORTING", "FINISHED", "CANCELLED", "ERROR"}:
            return {"CANCELLED"}
        if self._performance is None:
            self._performance = PerformanceTimer()
        self._begin_progress(context)
        if not getattr(bpy.app, "background", False) and context.window is not None:
            self._set_prepare_state("FILE_SELECTED")
            self._start_async_prepare(context, package_path)
            return {"RUNNING_MODAL"}
        try:
            self._set_prepare_state("FILE_SELECTED")
            self._prepare_import(context, package_path)
            return self._run_import(context)
        except Exception as exc:
            self._set_prepare_state("ERROR")
            self.report({"ERROR"}, str(exc))
            print(f"[UnityPackage Importer] Import preparation failed: {exc}")
            self._cleanup_prepared(remove=True)
            self._finish_performance(context)
            return {"CANCELLED"}

    def _run_import(self, context):
        self._set_prepare_state("IMPORTING")
        return self._perform_import(context)

    def _collect_selective_guids(self, prefab, planning_db: AssetDatabase) -> set[str]:
        """Resolve the selected import's FBX, material, texture, and sidecar GUIDs."""
        index = self._package_index
        if index is None:
            raise UnityPackageError("Package dependency index is unavailable")

        def records_with_suffix(suffix: str) -> set[str]:
            return {
                guid
                for guid, record in index.records.items()
                if Path(record.unity_path).suffix.lower() == suffix
            }

        wanted: set[str] = set()
        fbx_guids: set[str] = set()
        material_guids: set[str] = set()
        if prefab is not None:
            selected_guid = planning_db.guid_for_path(prefab.path)
            if selected_guid:
                wanted.add(selected_guid.lower())
            for guid in prefab.referenced_fbx_guids():
                entry = planning_db.find_guid(guid)
                if entry is None:
                    continue
                suffix = entry.path.suffix.lower()
                if suffix == ".fbx":
                    fbx_guids.add(entry.guid.lower())
                elif suffix == ".mat":
                    material_guids.add(entry.guid.lower())
        if self.import_mode == "RAW_FBX" or not fbx_guids:
            fbx_guids = records_with_suffix(".fbx")
        wanted.update(fbx_guids)

        if self.use_materials:
            # The existing material library intentionally preserves every .mat,
            # including same-name materials that are not directly referenced by
            # the selected Prefab. Keep that observable behavior in Stage B.
            material_guids.update(records_with_suffix(".mat"))
            for fbx_guid in fbx_guids:
                record = index.records.get(fbx_guid)
                if record is None or not record.meta_bytes:
                    continue
                try:
                    meta_text = record.meta_bytes.decode("utf-8", errors="replace")
                except AttributeError:
                    continue
                material_guids.update(
                    guid.lower()
                    for guid in parse_external_objects(meta_text).values()
                    if guid.lower() in index.records
                    and Path(index.records[guid.lower()].unity_path).suffix.lower() == ".mat"
                )

            wanted.update(material_guids)

            if self.use_textures:
                for material_guid in sorted(material_guids):
                    entry = planning_db.find_guid(material_guid)
                    if entry is None or not entry.path.is_file():
                        continue
                    try:
                        material = parse_material(entry.path, planning_db)
                    except (OSError, UnicodeError, ValueError, RuntimeError):
                        continue
                    for texture in material.textures.values():
                        texture_guid = str(texture.guid).lower()
                        if texture_guid in index.records:
                            wanted.add(texture_guid)
        if self.use_textures and not fbx_guids and not material_guids:
            wanted.update(
                guid for guid, record in index.records.items()
                if Path(record.unity_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"}
            )
        return wanted

    def _extract_selected_dependencies(
        self,
        context,
        planning_db: AssetDatabase,
        planning_prefab,
    ) -> tuple[Any, AssetDatabase, list[Path], list[Path]]:
        reader = self._package_reader
        index = self._package_index
        if reader is None or index is None:
            raise UnityPackageError("Package dependency index is unavailable")
        wanted = self._collect_selective_guids(planning_prefab, planning_db)
        final_dir = Path(tempfile.mkdtemp(prefix="unitypackage_blender_importer_selected_"))
        previous_timings = dict(reader.last_timings)
        try:
            self._set_phase(context, "Extracting selected dependencies", 0.42)
            extraction = reader.extract_selective(
                final_dir,
                index,
                wanted,
                cancel_check=self._prepare_cancel.is_set,
            )
            for phase, seconds in reader.last_timings.items():
                self._performance.add(phase, max(0.0, seconds - previous_timings.get(phase, 0.0)))
            self._set_phase(context, "Building selected Asset Database", 0.47)
            asset_db = self._performance.measure(
                "asset_database",
                AssetDatabase.from_package_index,
                extraction.root,
                index,
                extraction.assets,
                self._prepared_package_key.source_package_id,
            )
            self._performance.measure("meta_scan", asset_db.scan_missing_meta)
            fbx_paths = self._performance.measure("fbx_scan", asset_db.fbxs)
            prefab_paths = self._performance.measure("prefab_scan", asset_db.prefabs)
        except Exception:
            shutil.rmtree(final_dir, ignore_errors=True)
            raise

        old_dir = self._extraction_dir
        self._extraction_dir = final_dir
        self._extraction = extraction
        self._asset_db = asset_db
        self._fbx_paths = list(fbx_paths)
        self._prefab_paths = list(prefab_paths)
        if old_dir is not None and old_dir != final_dir:
            shutil.rmtree(old_dir, ignore_errors=True)
        return extraction, asset_db, list(fbx_paths), list(prefab_paths)

    def _perform_import(self, context):
        package_path = Path(self.filepath)
        try:
            extraction = self._extraction
            extraction_dir = self._extraction_dir
            asset_db = self._asset_db
            fbx_paths = list(self._fbx_paths)
            prefab_paths = list(self._prefab_paths)
            if extraction is None or extraction_dir is None or asset_db is None:
                raise UnityPackageError("Prepared import state is unavailable")
            package_key = self._prepared_package_key
            if package_key is None:
                raise UnityPackageError("Package identity is unavailable")

            planning_prefab = None
            selected_planning_path = None
            selected_unity_path = None
            prefab_unity_path = ""
            if self.import_mode == "RECONSTRUCT" and prefab_paths:
                selected_planning_path = self._selected_prefab(prefab_paths)
                if selected_planning_path:
                    selected_unity_path = (
                        selected_planning_path.relative_to(extraction_dir).as_posix()
                    )
                    try:
                        self._set_phase(context, "Parsing Prefab", 0.35)
                        planning_prefab = self._performance.measure(
                            "prefab_parse", parse_prefab, selected_planning_path
                        )
                    except (OSError, UnicodeError, ValueError) as exc:
                        self.report({"WARNING"}, f"Prefab parse failed; importing all FBX: {exc}")
                        planning_prefab = None

            extraction, asset_db, fbx_paths, prefab_paths = self._extract_selected_dependencies(
                context,
                asset_db,
                planning_prefab,
            )
            extraction_dir = self._extraction_dir
            if planning_prefab is not None and selected_planning_path is not None:
                final_entry = asset_db.find_path(selected_unity_path or "")
                if final_entry is not None and final_entry.path.is_file():
                    prefab_unity_path = final_entry.unity_path
                    prefab = self._performance.measure("prefab_parse", parse_prefab, final_entry.path)
                else:
                    prefab = None
                    self.report({"WARNING"}, "Selected Prefab was not included in dependency extraction")
            else:
                prefab = None

            imported_objects = []
            if fbx_paths:
                self._set_phase(context, "Importing FBX", 0.55)
                imported_objects = self._performance.measure(
                    "fbx_import", import_fbx_files, fbx_paths, package_key.source_package_id
                )
                if not imported_objects:
                    raise UnityPackageError("FBX import produced no Blender objects")
                imported_objects = apply_import_options(
                    imported_objects,
                    use_armatures=self.use_armatures,
                    use_bone_weights=self.use_bone_weights,
                    use_shape_keys=self.use_shape_keys,
                )
            extracted_fbx_paths = {
                str(entry.path.resolve()): entry.unity_path
                for entry in asset_db.by_guid.values()
                if entry.path.suffix.lower() == ".fbx"
            }
            for obj in imported_objects:
                source_fbx = obj.get("unity_source_fbx", "")
                unity_path = extracted_fbx_paths.get(str(Path(str(source_fbx)).resolve()))
                if unity_path:
                    obj["unity_asset_path"] = unity_path
            material_library = {}
            if self.use_materials:
                self._set_phase(context, "Building Materials and Textures", 0.75)
                material_library = build_material_library(
                    asset_db,
                    pack_textures=not self.keep_extracted,
                    use_textures=self.use_textures,
                    timing=self._performance,
                )
                self._performance.measure(
                    "material_mapping", apply_materials_by_name, imported_objects,
                    material_library.values(), asset_db=asset_db,
                    material_library=material_library, scene=context.scene,
                )
                if not fbx_paths and not material_library:
                    self._performance.measure(
                        "texture_load", load_textures_from_database, asset_db,
                        pack=not self.keep_extracted,
                    )
                capture_material_texture_dependencies(context.scene, material_library.values())
            prefab_root = None
            prefab_object_map = {}
            if prefab is not None and self.apply_prefab_transforms:
                self._set_phase(context, "Reconstructing Prefab", 0.90)
                prefab_root, prefab_object_map = self._performance.measure(
                    "prefab_reconstruct",
                    build_prefab_hierarchy,
                    prefab,
                    imported_objects,
                    package_key.source_package_id,
                    prefab_unity_path,
                )
                if self.use_materials:
                    self._performance.measure(
                        "material_mapping",
                        apply_prefab_materials,
                        prefab,
                        prefab_object_map,
                        asset_db,
                        material_library,
                        context.scene,
                    )

            scene = context.scene
            supported_asset_count = len(fbx_paths) + len(prefab_paths) + len(material_library)
            supported_asset_count += sum(1 for image in bpy.data.images if image.get("unity_source_package_id") == package_key.source_package_id)
            if supported_asset_count == 0:
                raise UnityPackageError("UnityPackage contains no supported FBX, Prefab, Material, or Texture asset")
            existing_registry = load_scene_registry(scene)
            package_registry, package_status = register_package(
                scene,
                {
                    "source_package_id": package_key.source_package_id,
                    "package_sha256": package_key.sha256,
                    "source_package_path": package_key.path,
                    "source_package_name": package_key.package_name,
                    "import_sequence": len(existing_registry.packages) + 1,
                    "selected_prefab": str(prefab.path) if prefab else "",
                    "asset_counts": {
                        "fbx": len(fbx_paths),
                        "materials": len(material_library),
                        "images": sum(
                            1
                            for image in bpy.data.images
                            if image.get("unity_source_package_id") == package_key.source_package_id
                        ),
                    },
                },
            )
            if package_status != "NO_COLLISION":
                self.report({"WARNING"}, package_status)
            scene["unitypackage_source"] = str(package_path)
            scene["unitypackage_source_package_id"] = package_key.source_package_id
            scene["unitypackage_package_sha256"] = package_key.sha256
            scene["unitypackage_extracted_root"] = str(extraction_dir)
            scene["unitypackage_fbx_count"] = len(fbx_paths)
            scene["unitypackage_prefab"] = str(prefab.path) if prefab else ""
            scene["unitypackage_import_sequence"] = [
                package["source_package_id"] for package in package_registry.packages.values()
            ]
            object_registry_items = list(imported_objects) + list(prefab_object_map.values())
            if prefab_root is not None:
                object_registry_items.append(prefab_root)
            register_datablocks(scene, object_registry_items, package_key.source_package_id, "Object")
            register_datablocks(scene, material_library.values(), package_key.source_package_id, "Material")
            register_datablocks(
                scene,
                [image for image in bpy.data.images if image.get("unity_source_package_id") == package_key.source_package_id],
                package_key.source_package_id,
                "Image",
            )
            dependency_counts = resolve_after_import(scene)
            package_kind = "MIXED_PACKAGE" if fbx_paths and (material_library or supported_asset_count > len(fbx_paths)) else "GEOMETRY_PACKAGE" if fbx_paths else "ASSET_PROVIDER_PACKAGE"
            current_registry = load_scene_registry(scene)
            current_package = current_registry.packages.get(package_key.source_package_id)
            if current_package is not None:
                current_package["package_kind"] = package_kind
                current_package["dependency_refs_captured"] = len([
                    record for record in load_dependency_registry(scene).get("dependencies", [])
                    if record.get("consumer_package_id") == package_key.source_package_id
                ])
                current_package.update(dependency_counts)
                save_scene_registry(scene, current_registry)
            self.report({"INFO"}, f"Dependency resolution: local={dependency_counts['resolved_local']} cross-package={dependency_counts['resolved_cross_package']} unresolved={dependency_counts['unresolved']} ambiguous={dependency_counts['ambiguous']}")
            if self.include_sibling_packages and not self.group_child:
                discovery = discover_siblings(package_path)
                scene["unitypackage_sibling_discovery"] = {
                    "status": discovery.status,
                    "root_package": discovery.root_package,
                    "related_packages": [candidate.path for candidate in discovery.packages],
                    "unresolved_guids": sorted(discovery.unresolved_guids),
                    "ambiguous_guids": sorted(discovery.ambiguous_guids),
                }
                if discovery.status == "COMPLETE" and discovery.packages:
                    group_id = uuid4().hex
                    scene["unitypackage_group_import"] = {
                        "group_import_id": group_id,
                        "primary_package_id": package_key.source_package_id,
                        "related_package_ids": [candidate.package_id for candidate in discovery.packages],
                    }
                    for candidate in discovery.packages:
                        result = bpy.ops.import_scene.unitypackage(
                            filepath=candidate.path,
                            import_mode=self.import_mode,
                            prefab_choice="AUTO",
                            use_armatures=self.use_armatures,
                            use_bone_weights=self.use_bone_weights,
                            use_shape_keys=self.use_shape_keys,
                            use_materials=self.use_materials,
                            use_textures=self.use_textures,
                            apply_prefab_transforms=self.apply_prefab_transforms,
                            keep_extracted=self.keep_extracted,
                            include_sibling_packages=False,
                            group_child=True,
                        )
                        if "FINISHED" not in result:
                            self.report({"WARNING"}, f"Related Package import failed: {Path(candidate.path).name}")
                elif discovery.status in {"AMBIGUOUS", "PARTIAL"}:
                    self.report({"WARNING"}, f"Sibling discovery {discovery.status}; Import Together was not auto-selected")
            collisions = load_scene_registry(scene).detect_collisions()
            if collisions:
                self.report({"WARNING"}, f"Detected {len(collisions)} cross-package identity collision(s)")
            if extraction.errors:
                for error in extraction.errors:
                    print(f"[UnityPackage Importer] {error}")
                self.report({"WARNING"}, f"Imported with {len(extraction.errors)} extraction warning(s); see console")
            self.report({"INFO"}, f"Imported {len(fbx_paths)} FBX file(s)")
            self._set_phase(context, "Import complete", 1.0)
            self._set_prepare_state("FINISHED")
            self._modal_registered = False
            self._cleanup_prepared(remove=not self.keep_extracted)
            self._finish_performance(context)
            return {"FINISHED"}
        except Exception as exc:
            self._set_prepare_state("ERROR")
            self._modal_registered = False
            self.report({"ERROR"}, str(exc))
            print(f"[UnityPackage Importer] Import failed: {exc}")
            self._cleanup_prepared(remove=True)
            self._finish_performance(context)
            return {"CANCELLED"}


def menu_func_import(self, context):
    self.layout.operator(UNITYPACKAGE_OT_import.bl_idname, text="Unity Package / VRChat Avatar (.unitypackage)")


class UNITYPACKAGE_OT_import_prepared(bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_prepared"
    bl_label = "Import Prepared Unity Package"
    bl_options = {"REGISTER", "UNDO"}

    session_id: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        try:
            result = session.operator._run_import(context)
        except Exception:
            _discard_prepared_session(session.session_id, context)
            raise
        _PREPARED_SESSIONS.pop(self.session_id, None)
        return result

    def invoke(self, context, _event):
        return self.execute(context)

    def cancel(self, context):
        _discard_prepared_session(self.session_id, context)


class UNITYPACKAGE_OT_import_prefab(bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_prefab"
    bl_label = "Select Unity Prefab"

    session_id: StringProperty(options={"HIDDEN"})
    prefab_choice: EnumProperty(name="Prefab", items=_session_prefab_items)

    def draw(self, context):
        self.layout.prop(self, "prefab_choice")

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        session.operator.prefab_choice = self.prefab_choice
        _schedule_prepared_session(self.session_id, show_dialog=False)
        return {"FINISHED"}

    def invoke(self, context, _event):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=520)

    def cancel(self, context):
        _discard_prepared_session(self.session_id, context)


UNITYPACKAGE_CLASSES = (
    UNITYPACKAGE_OT_import,
    UNITYPACKAGE_OT_import_prepared,
    UNITYPACKAGE_OT_import_prefab,
)
