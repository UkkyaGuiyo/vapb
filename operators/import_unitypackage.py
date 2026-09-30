"""Blender File > Import operator for UnityPackage files."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from queue import SimpleQueue
import re
import shutil
import tempfile
from threading import Event
from time import perf_counter
from typing import Any
from uuid import uuid4

import bpy  # type: ignore
from mathutils import Matrix  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy.props import BoolProperty, EnumProperty, StringProperty  # type: ignore

from ..blender.fbx_importer import apply_import_options, import_fbx_files
from ..blender.fbx_receipt import copy_with_receipt, source_sha256, validate_receipt_continuity
from ..blender.direct_mesh_frame import root_direct_mesh_file_id, verified_direct_mesh_frame
from ..blender.model_witness_bridge import matches_witnessed_source, plan_witness_realizations, plan_witness_material_dependencies, reserve_witness_slots
from ..blender.renderer_binding import semantic_owner_id
from ..blender.hierarchy_builder import apply_transform, build_prefab_hierarchy
from ..blender.identity_registry import load_scene_registry, register_datablocks, register_package, save_scene_registry
from ..blender.material_builder import apply_materials_by_name, apply_prefab_materials, apply_prefab_modification_materials, build_material_library
from ..blender.texture_loader import load_textures_from_database
from ..blender.dependency_resolver import capture_dependency, capture_material_texture_dependencies, load_dependency_registry, resolve_after_import
from ..blender.performance import PerformanceTimer, diagnostic_add, reset_diagnostic_stats
from ..blender.progress_overlay import ImportProgressOverlay
from ..ui.import_panel import draw_import_options
from ..blender.import_outcome import scene_import_outcome
from ..unity.asset_database import AssetDatabase
from ..unity.package_identity import PackageIdentity
from ..unity.source_store import archive_source
from ..unity.package_reader import PackageIndex, UnityPackageError, UnityPackageReader, is_unitypackage
from ..unity.material_mapping import parse_external_objects
from ..unity.material_parser import parse_material
from ..unity.prefab_parser import parse_prefab, ref_guid
from ..unity.effective_prefab import EffectivePrefabResolver, ModelSourceSemanticIndex
from ..unity.occurrence_projection import PrefabSource, project_occurrences, model_instance_plans
from ..unity.prefab_instance_transform import has_complete_transform, resolve_instance_transform
from ..unity.model_identity_witness import load_model_witness
from ..unity.physbone_parser import extract_physbone_snapshot
from ..unity.prefab_candidate_analyzer import (
    PackageCompositionPlan,
    PrefabCandidateAnalysis,
    PrefabCandidateAnalyzer,
    PrefabSelection,
)
from ..unity.sibling_discovery import discover_siblings, inspect_provider_folder, inspect_provider_package
from ..unity.import_progress import ImportProgressMonitor, ImportProgressStage, ImportProgressStatus


_DEFAULT_PREFAB_ITEMS: list[tuple[str, str, str, int]] = [("AUTO", "Automatic (Recommended)", "Analyze Prefab structure and visual completeness", 0)]
_SESSION_TIMEOUT_SECONDS = 300.0
_PREPARED_SESSIONS: dict[str, "_PreparedSession"] = {}
_ACTIVE_PROGRESS_MONITOR: ImportProgressMonitor | None = None


PREPARE_STATES = {
    "IDLE",
    "FILE_SELECTED",
    "PREPARING",
    "PREPARED",
    "WAITING_MISSING_DEPENDENCY_RESOLUTION",
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
    candidate_analyses: list[PrefabCandidateAnalysis] = field(default_factory=list)
    candidate_selection: PrefabSelection | None = None
    composition_plan: PackageCompositionPlan | None = None
    candidate_prefabs: dict[str, Any] = field(default_factory=dict)
    candidate_archive_cache: Any = None


@dataclass
class _PreparedSession:
    session_id: str
    operator: "UNITYPACKAGE_OT_import"
    created_at: float
    window_manager: Any = None
    pending_stage: str = ""
    active_stage: str = ""
    pump_registered: bool = False
    handoff_attempts: int = 0


def _session_prefab_items(_self, _context):
    session = _PREPARED_SESSIONS.get(getattr(_self, "session_id", ""))
    if session is None:
        return _DEFAULT_PREFAB_ITEMS
    return session.operator._prefab_items


class _BlenderProgressSink:
    """Render factual stage progress without owning importer control flow."""

    def __init__(self, context):
        self.context = context
        self.started = False
        self.overlay = None
        if not getattr(bpy.app, "background", False):
            candidate = ImportProgressOverlay(context)
            if candidate.area is not None:
                self.overlay = candidate

    def update(self, state) -> None:
        window_manager = getattr(self.context, "window_manager", None)
        if window_manager is not None:
            if not self.started:
                window_manager.progress_begin(0, state.stage_count)
                self.started = True
            # The only percentage-like value is the factual stage index.  No
            # fractional progress is invented for an unknown-duration stage.
            window_manager.progress_update(state.stage_index)
        if self.overlay is not None:
            if self.overlay.active:
                self.overlay.update(state)
            else:
                self.overlay.start(state)
        workspace = getattr(self.context, "workspace", None)
        status_text_set = getattr(workspace, "status_text_set", None)
        if callable(status_text_set):
            status_text_set(state.status_text())

    def clear(self) -> None:
        window_manager = getattr(self.context, "window_manager", None)
        if self.started and window_manager is not None:
            try:
                window_manager.progress_end()
            except (AttributeError, RuntimeError):
                pass
        self.started = False
        workspace = getattr(self.context, "workspace", None)
        status_text_set = getattr(workspace, "status_text_set", None)
        if callable(status_text_set):
            status_text_set(None)
        if self.overlay is not None:
            self.overlay.finish()


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
        if operator._progress_owner and operator._progress_monitor is not None:
            operator._progress_monitor.fail("Import session discarded")
        elif operator._progress_active and session.window_manager is not None:
            try:
                session.window_manager.progress_end()
            except (AttributeError, RuntimeError):
                pass
        operator._end_progress(None)
        if operator._performance is not None:
            operator._performance.finish()
            operator._performance.emit()
            operator._performance = None


def _schedule_prepared_session(session_id: str, *, show_dialog: bool, show_group_dialog: bool = False, show_missing_dialog: bool = False) -> None:
    session = _PREPARED_SESSIONS.get(session_id)
    if session is None:
        return
    stage = "MISSING" if show_missing_dialog else "SIBLINGS" if show_group_dialog else "PREFAB" if show_dialog else "IMPORT"
    if session.active_stage == stage and not session.pending_stage:
        return
    if session.pending_stage != stage:
        session.pending_stage = stage
        session.handoff_attempts = 0
    session.active_stage = ""
    if session.pump_registered:
        return
    session.pump_registered = True

    def handoff():
        session = _PREPARED_SESSIONS.get(session_id)
        if session is None:
            return None
        if perf_counter() - session.created_at > _SESSION_TIMEOUT_SECONDS:
            _discard_prepared_session(session_id)
            return None
        if session.pending_stage:
            next_stage = session.pending_stage
            session.pending_stage = ""
            session.handoff_attempts += 1
            try:
                if next_stage == "MISSING":
                    result = bpy.ops.import_scene.unitypackage_missing_dependencies(
                        "INVOKE_DEFAULT", session_id=session_id
                    )
                elif next_stage == "SIBLINGS":
                    result = bpy.ops.import_scene.unitypackage_siblings(
                        "INVOKE_DEFAULT", session_id=session_id
                    )
                elif next_stage == "PREFAB":
                    result = bpy.ops.import_scene.unitypackage_prefab(
                        "INVOKE_DEFAULT", session_id=session_id
                    )
                else:
                    result = bpy.ops.import_scene.unitypackage_prepared(
                        "EXEC_DEFAULT", session_id=session_id
                    )
            except Exception as exc:
                print(f"[UnityPackage Importer] Prepared session handoff failed: {exc}")
                _discard_prepared_session(session_id)
                return None
            if session_id not in _PREPARED_SESSIONS:
                return None
            if "RUNNING_MODAL" in result or "FINISHED" in result:
                # execute() may have queued the following stage during invoke.
                if not session.pending_stage:
                    session.active_stage = next_stage
            elif not session.pending_stage:
                # A rejected invoke is NOT an opened dialog. Retry only while
                # the same session remains alive; user cancel removes it.
                if session.handoff_attempts >= 3:
                    print("[UnityPackage Importer] Prepared dialog was rejected three times")
                    _discard_prepared_session(session_id)
                    return None
                session.pending_stage = next_stage
        # One pump owns every transition; no independent, stale stage timers.
        # Pending work runs on the next event-loop tick, not after a UI sleep.
        return 0.0 if session.pending_stage else 0.1

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
    # This is transport state for background/programmatic callers.  The
    # foreground picker has its own dynamic EnumProperty below; keeping this
    # value as a string avoids assigning a token from one RNA enum context to
    # another one with a different item callback.
    prefab_choice: StringProperty(name="Prefab", default="AUTO", options={"HIDDEN"})
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
    source_storage_directory: StringProperty(
        name="原本の保管先", subtype="DIR_PATH", default="",
        description="UnityPackage原本を保管します。空欄ならBlenderユーザーデータ内のVAPB保管先を使用",
    )
    model_witness_path: StringProperty(
        name="Unity Model Witness (optional)", subtype="FILE_PATH", default="",
        description="Exact source-revision identity bridge generated by the public Unity Editor probe",
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
        self._progress_monitor: ImportProgressMonitor | None = None
        self._progress_owner = False
        self._progress_context = None
        self._progress_failure_message = ""
        self._prepare_executor: ThreadPoolExecutor | None = None
        self._prepare_future: Future | None = None
        self._prepare_timer = None
        self._prepare_window_manager = None
        self._prepare_cancel = Event()
        self._prepare_events: SimpleQueue[str] = SimpleQueue()
        self._selected_prefab_choice: str | None = None
        self._sibling_discovery = None
        self._sibling_import_together = True
        self._manual_provider_paths: set[str] = set()
        self._provider_provenance: dict[str, str] = {}
        self._candidate_analyses: list[PrefabCandidateAnalysis] = []
        self._candidate_selection: PrefabSelection | None = None
        self._composition_plan: PackageCompositionPlan | None = None
        self._candidate_prefabs: dict[str, Any] = {}
        self._candidate_archive_cache = None

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

    def _set_phase(
        self,
        context,
        phase: str,
        progress: float = 0.0,
        *,
        current_item: str | None = None,
        current_index: int | None = None,
        current_total: int | None = None,
        blocking_operation: bool = False,
    ) -> None:
        del progress  # Kept for compatibility with existing phase callers.
        if self._progress_monitor is not None:
            stage = self._stage_for_phase(phase)
            self._progress_monitor.set_stage(
                stage,
                message=phase,
                current_item=current_item,
                current_index=current_index,
                current_total=current_total,
                blocking_operation=blocking_operation,
            )
        self.report({"INFO"}, f"UnityPackage: {phase}")

    @staticmethod
    def _stage_for_phase(phase: str) -> str:
        if phase in {"Checking Package identity", "Indexing UnityPackage in archive order", "Extracting dependency candidates", "Building Asset Database", "Scanning meta files", "Scanning FBX", "Scanning Prefabs", "Preparing UnityPackage in background", "Reusing prepared asset index", "Asset index ready", "Extracting selected dependencies", "Building selected Asset Database"}:
            return ImportProgressStage.READING_PACKAGE
        if phase in {"Analyzing Prefab candidates", "Waiting for Prefab selection", "Parsing Prefab"}:
            return ImportProgressStage.ANALYZING_PREFABS
        if phase in {"Discovering sibling Packages", "Resolving related packages"}:
            return ImportProgressStage.RESOLVING_PACKAGES
        if phase == "Importing FBX":
            return ImportProgressStage.IMPORTING_FBX
        if phase == "Reconstructing Prefab":
            return ImportProgressStage.BUILDING_HIERARCHY
        if phase == "Building Materials and Textures":
            return ImportProgressStage.CREATING_VISUALS
        if phase == "Resolving dependencies":
            return ImportProgressStage.RESOLVING_DEPENDENCIES
        if phase in {"Import complete", "Finalizing import"}:
            return ImportProgressStage.FINALIZING
        return ImportProgressStage.READING_PACKAGE

    def _begin_progress(self, context) -> None:
        if not self._progress_active:
            self._progress_context = context
            global _ACTIVE_PROGRESS_MONITOR
            if getattr(self, "group_child", False) and _ACTIVE_PROGRESS_MONITOR is not None:
                self._progress_monitor = _ACTIVE_PROGRESS_MONITOR
                self._progress_owner = False
            else:
                reset_diagnostic_stats()
                self._progress_monitor = ImportProgressMonitor(
                    sink=_BlenderProgressSink(context),
                    logger=print,
                )
                self._progress_owner = True
                _ACTIVE_PROGRESS_MONITOR = self._progress_monitor
            self._progress_active = True
            if self._progress_owner:
                self._progress_monitor.start()

    def _end_progress(self, context) -> None:
        if self._progress_active:
            global _ACTIVE_PROGRESS_MONITOR
            if self._progress_owner and self._progress_monitor is not None:
                if self._progress_monitor.state.status == ImportProgressStatus.WORKING:
                    self._progress_monitor.sink.clear() if self._progress_monitor.sink else None
                if _ACTIVE_PROGRESS_MONITOR is self._progress_monitor:
                    _ACTIVE_PROGRESS_MONITOR = None
            self._progress_active = False
            self._progress_monitor = None
            self._progress_owner = False
            self._progress_context = None

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
        if self._progress_owner and self._progress_monitor is not None:
            if self._prepare_state == "FINISHED":
                self._progress_monitor.complete()
            elif self._prepare_state == "ERROR":
                self._progress_monitor.fail(getattr(self, "_progress_failure_message", "Import failed"))
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
        events: SimpleQueue[object] | None,
    ) -> _PreparedImport:
        timings: dict[str, float] = {}
        candidate_prefabs: dict[str, Any] = {}

        def phase(
            message: str,
            *,
            stage: str | None = None,
            current_item: str | None = None,
            current_index: int | None = None,
            current_total: int | None = None,
            blocking_operation: bool = False,
        ) -> None:
            if events is not None:
                events.put({
                    "message": message,
                    "stage": stage,
                    "current_item": current_item,
                    "current_index": current_index,
                    "current_total": current_total,
                    "blocking_operation": blocking_operation,
                })

        def candidate_progress(index: int, total: int, item: Path) -> None:
            phase(
                "Analyzing Prefab candidates",
                stage=ImportProgressStage.ANALYZING_PREFABS,
                current_item=item.name,
                current_index=index,
                current_total=total,
            )

        def timed(name: str, function, *args, **kwargs):
            started = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                timings[name] = timings.get(name, 0.0) + perf_counter() - started

        phase("Checking Package identity")
        package_key = timed("package_identity", PackageIdentity.from_path, package_path)
        if existing_ready and existing_key == package_key:
            candidate_analyses: list[PrefabCandidateAnalysis] = []
            candidate_selection: PrefabSelection | None = None
            if self.import_mode == "RECONSTRUCT" and existing_prefab_paths and existing_extraction_dir and existing_package_index:
                analyzer = timed(
                    "prefab_candidate_analysis",
                    PrefabCandidateAnalyzer,
                    package_path,
                    existing_package_index,
                    existing_extraction_dir,
                    existing_prefab_paths,
                    existing_asset_db,
                    self._manual_provider_paths,
                )
                candidate_analyses = timed(
                    "prefab_candidate_analysis_parse",
                    analyzer.analyze,
                    candidate_progress,
                )
                candidate_prefabs = dict(analyzer.parsed_prefabs)
                candidate_selection = analyzer.select(candidate_analyses)
                composition_plan = analyzer.compose(candidate_analyses)
            else:
                composition_plan = None
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
                candidate_analyses=candidate_analyses,
                candidate_selection=candidate_selection,
                composition_plan=composition_plan,
                candidate_prefabs=candidate_prefabs,
                candidate_archive_cache=getattr(analyzer, "cache", None) if 'analyzer' in locals() else None,
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
            candidate_analyses: list[PrefabCandidateAnalysis] = []
            candidate_selection: PrefabSelection | None = None
            if self.import_mode == "RECONSTRUCT" and prefab_paths:
                phase("Analyzing Prefab candidates")
                analyzer = timed(
                    "prefab_candidate_analysis",
                    PrefabCandidateAnalyzer,
                    package_path,
                    package_index,
                    extraction.root,
                    prefab_paths,
                    asset_db,
                    self._manual_provider_paths,
                )
                candidate_analyses = timed(
                    "prefab_candidate_analysis_parse",
                    analyzer.analyze,
                    candidate_progress,
                )
                candidate_prefabs = dict(analyzer.parsed_prefabs)
                candidate_selection = analyzer.select(candidate_analyses)
                composition_plan = analyzer.compose(candidate_analyses)
            else:
                composition_plan = None
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
            False,
            candidate_analyses,
            candidate_selection,
            composition_plan,
            candidate_prefabs,
            getattr(analyzer, "cache", None) if 'analyzer' in locals() else None,
        )

    def _apply_prepared(self, context, prepared: _PreparedImport) -> None:
        for phase, seconds in prepared.timings.items():
            self._performance.add(phase, seconds)
        if prepared.reused:
            self._prepared_package_key = prepared.package_key
            self._candidate_analyses = list(prepared.candidate_analyses or [])
            self._candidate_selection = prepared.candidate_selection
            self._composition_plan = prepared.composition_plan
            self._candidate_prefabs = dict(prepared.candidate_prefabs)
            self._candidate_archive_cache = prepared.candidate_archive_cache
            if (
                self._selected_prefab_choice is None
                and self.prefab_choice == "AUTO"
                and self._candidate_selection
                and self._candidate_selection.mode == "AUTO_SELECTED"
                and self._composition_plan is None
            ):
                self._selected_prefab_choice = self._candidate_selection.token
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
        self._candidate_analyses = list(prepared.candidate_analyses or [])
        self._candidate_selection = prepared.candidate_selection
        self._composition_plan = prepared.composition_plan
        self._candidate_prefabs = dict(prepared.candidate_prefabs)
        self._candidate_archive_cache = prepared.candidate_archive_cache
        if (
            self._selected_prefab_choice is None
            and self.prefab_choice == "AUTO"
            and self._candidate_selection
            and self._candidate_selection.mode == "AUTO_SELECTED"
            and self._composition_plan is None
        ):
            self._selected_prefab_choice = self._candidate_selection.token
        defer_discovery = (
            not getattr(bpy.app, "background", False)
            and self.import_mode == "RECONSTRUCT"
            and self._composition_plan is not None
            and self._composition_plan.chooser_required
            and self._selected_prefab_choice is None
        )
        if not getattr(self, "group_child", False) and Path(self.filepath).is_file() and not defer_discovery:
            self._set_phase(context, "Discovering sibling Packages", 0.32)
            effective_candidate_token = self._selected_prefab_choice or self.prefab_choice
            selected_candidate = next((item for item in self._candidate_analyses if item.token == effective_candidate_token), None)
            if (self._selected_prefab_choice or self.prefab_choice) == "AUTO" and self._composition_plan is not None:
                selected_paths = {item.unity_path for item in self._candidate_analyses if item.has_visual_source}
                extra_paths = set().union(*(item.provider_packages for item in self._candidate_analyses if item.has_visual_source))
                required_visual_guids = set().union(*(item.required_visual_guids for item in self._candidate_analyses if item.has_visual_source))
            else:
                selected_paths = {selected_candidate.unity_path} if selected_candidate else set()
                extra_paths = set(selected_candidate.provider_packages) if selected_candidate else set()
                required_visual_guids = set(selected_candidate.required_visual_guids) if selected_candidate else set()
            ambiguous_visual_guids = set().union(*(item.ambiguous_visual_guids for item in self._candidate_analyses if item.has_visual_source))
            required_visual_guids = (required_visual_guids - set(self._package_index.records)) | ambiguous_visual_guids
            self._sibling_discovery = self._performance.measure(
                "sibling_discovery",
                discover_siblings,
                self.filepath,
                selected_asset_paths=selected_paths,
                extra_package_paths=extra_paths,
                required_visual_guids=required_visual_guids,
                ambiguous_visual_guids=ambiguous_visual_guids,
                prebuilt_indexes={source.path: source.index for source in self._candidate_archive_cache.sources} if self._candidate_archive_cache is not None else None,
                progress=lambda index, total, item: self._set_phase(
                    context,
                    "Resolving related packages",
                    current_item=item.name,
                    current_index=index,
                    current_total=total,
                ),
            )
            discovery = self._sibling_discovery
            print(
                "[UnityPackage Importer] Sibling discovery: "
                f"status={discovery.status} providers={len(discovery.packages)} "
                f"resolved={sum(item.match_count for item in discovery.packages)} "
                f"unresolved={len(discovery.unresolved_guids)} "
                f"ambiguous={len(discovery.ambiguous_guids)}"
            )
            self._sibling_import_together = discovery.status == "COMPLETE"
        self._set_prepare_state("PREPARED")
        self._set_phase(context, "Asset index ready", 0.30)

    def _discover_selected_visual_dependencies(self) -> None:
        """Run bounded discovery after foreground Prefab selection."""
        if getattr(self, "group_child", False) or not Path(self.filepath).is_file():
            return
        selected_paths: set[str] = set()
        if (self._selected_prefab_choice or self.prefab_choice) == "AUTO" and self._composition_plan is not None:
            selected_paths.update(item.unity_path for item in self._candidate_analyses if item.has_visual_source)
            required_visual_guids = set().union(*(item.required_visual_guids for item in self._candidate_analyses if item.has_visual_source))
        else:
            selected = self._selected_prefab(self._prefab_paths)
            if selected is not None and self._extraction_dir is not None:
                try:
                    selected_paths.add(selected.relative_to(self._extraction_dir).as_posix())
                except ValueError:
                    pass
            selected_candidate_for_requirements = next(
                (item for item in self._candidate_analyses if item.token == (self._selected_prefab_choice or self.prefab_choice)),
                None,
            )
            required_visual_guids = set(selected_candidate_for_requirements.required_visual_guids) if selected_candidate_for_requirements else set()
        ambiguous_visual_guids = set().union(*(item.ambiguous_visual_guids for item in self._candidate_analyses if item.has_visual_source))
        required_visual_guids = (required_visual_guids - set(self._package_index.records)) | ambiguous_visual_guids
        selected_candidate = next(
            (item for item in self._candidate_analyses if item.token == self._selected_prefab_choice),
            None,
        )
        extra_paths = {Path(path) for path in self._manual_provider_paths}
        if selected_candidate and (self._selected_prefab_choice or self.prefab_choice) != "AUTO":
            extra_paths.update(selected_candidate.provider_packages)
        elif self._composition_plan is not None:
            extra_paths.update(path for item in self._candidate_analyses for path in item.provider_packages)
        self._sibling_discovery = self._performance.measure(
            "sibling_discovery",
            discover_siblings,
            self.filepath,
            selected_asset_paths=selected_paths,
            extra_package_paths=extra_paths,
            required_visual_guids=required_visual_guids,
            ambiguous_visual_guids=ambiguous_visual_guids,
            provenance_by_path=self._provider_provenance,
            prebuilt_indexes={source.path: source.index for source in self._candidate_archive_cache.sources} if self._candidate_archive_cache is not None else None,
            progress=(
                (lambda index, total, item: self._set_phase(
                    self._progress_context,
                    "Resolving related packages",
                    current_item=item.name,
                    current_index=index,
                    current_total=total,
                ))
                if self._progress_context is not None
                else None
            ),
        )
        self._sibling_import_together = self._sibling_discovery.visual_status == "COMPLETE"

    def _accept_manual_package(self, package_path: Path) -> bool:
        discovery = self._sibling_discovery
        unresolved = set(getattr(discovery, "unresolved_visual_guids", set())) if discovery else set()
        candidate = inspect_provider_package(package_path, unresolved)
        if not candidate.matched_guids:
            return False
        self._manual_provider_paths.add(candidate.path)
        self._provider_provenance[candidate.path] = candidate.resolution_provenance
        self._discover_selected_visual_dependencies()
        return True

    def _accept_manual_folder(self, folder: Path) -> tuple[int, set[str]]:
        discovery = self._sibling_discovery
        unresolved = set(getattr(discovery, "unresolved_visual_guids", set())) if discovery else set()
        candidates, ambiguous = inspect_provider_folder(folder, unresolved)
        for candidate in candidates:
            if candidate.ambiguous_guids:
                continue
            self._manual_provider_paths.add(candidate.path)
            self._provider_provenance[candidate.path] = "USER_SELECTED_FOLDER"
        self._discover_selected_visual_dependencies()
        return len(candidates), ambiguous

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
        while True:
            try:
                event = self._prepare_events.get_nowait()
            except Exception:
                return
            if isinstance(event, str):
                self._set_phase(context, event)
                continue
            self._set_phase(
                context,
                event.get("message", "Working"),
                current_item=event.get("current_item"),
                current_index=event.get("current_index"),
                current_total=event.get("current_total"),
                blocking_operation=bool(event.get("blocking_operation", False)),
            )

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
            self._progress_failure_message = str(exc)
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
        self._prefab_items = [("AUTO", "Automatic (Recommended)", "Use deterministic structural and completeness analysis", 0)]
        analysis_by_token = {item.token: item for item in self._candidate_analyses}
        self._prefab_items.extend(
            (
                f"PREFAB_{index}",
                analysis_by_token.get(f"PREFAB_{index}").display_name if analysis_by_token.get(f"PREFAB_{index}") else path.name,
                ", ".join(analysis_by_token.get(f"PREFAB_{index}").reasons) if analysis_by_token.get(f"PREFAB_{index}") else str(path),
                index + 1,
            )
            for index, path in enumerate(self._prefab_paths)
        )
        _PREPARED_SESSIONS[session_id] = _PreparedSession(
            session_id, self, perf_counter(), context.window_manager
        )
        show_dialog = (
            self.import_mode == "RECONSTRUCT"
            and (
                (self._composition_plan is not None and self._composition_plan.chooser_required)
                or (self._composition_plan is None and len(self._prefab_paths) > 1)
            )
            and self._selected_prefab_choice is None
        )
        show_group_dialog = (
            not getattr(bpy.app, "background", False)
            and self._sibling_discovery is not None
            and self._sibling_discovery.status in {"COMPLETE", "PARTIAL"}
            and bool(self._sibling_discovery.packages)
            and not show_dialog
        )
        show_missing_dialog = (
            not getattr(bpy.app, "background", False)
            and self._sibling_discovery is not None
            and bool(getattr(self._sibling_discovery, "unresolved_visual_guids", set()))
            and not show_dialog
        )
        if show_dialog:
            self._set_prepare_state("PREPARED")
            self._set_phase(context, "Waiting for Prefab selection", 0.30)
        self._stop_async_prepare()
        # Returning FINISHED is the actual WindowManager modal-handler removal.
        self._modal_registered = False
        self._ui_log(
            f"prepare modal handoff session={session_id} "
            f"dialog={show_dialog or show_group_dialog}"
        )
        if show_group_dialog:
            if show_missing_dialog:
                self._set_prepare_state("WAITING_MISSING_DEPENDENCY_RESOLUTION")
                _schedule_prepared_session(session_id, show_dialog=False, show_missing_dialog=True)
            else:
                _schedule_prepared_session(session_id, show_dialog=False, show_group_dialog=True)
        elif show_missing_dialog:
            self._set_prepare_state("WAITING_MISSING_DEPENDENCY_RESOLUTION")
            _schedule_prepared_session(session_id, show_dialog=False, show_missing_dialog=True)
        else:
            _schedule_prepared_session(session_id, show_dialog=show_dialog)
        return {"FINISHED"}

    def _selected_prefab(self, prefab_paths: list[Path]) -> Path | None:
        if not prefab_paths:
            return None
        choice = self._selected_prefab_choice
        if choice is None:
            choice = self.prefab_choice
        if choice.startswith("PREFAB_"):
            try:
                return prefab_paths[int(choice.split("_", 1)[1])]
            except (ValueError, IndexError) as exc:
                raise UnityPackageError(f"Invalid Prefab selection: {choice}") from exc
        selection = self._candidate_selection
        if choice == "AUTO" and selection and selection.mode == "AUTO_SELECTED" and selection.token:
            try:
                return prefab_paths[int(selection.token.split("_", 1)[1])]
            except (ValueError, IndexError) as exc:
                raise UnityPackageError("Automatic Prefab selection points to an invalid candidate") from exc
        if choice == "AUTO" and selection and selection.mode != "AUTO_SELECTED":
            raise UnityPackageError(f"Automatic Prefab selection is ambiguous ({selection.reason}); choose a Prefab explicitly")
        if len(prefab_paths) == 1 and choice in {None, "AUTO"}:
            return prefab_paths[0]
        if choice == "AUTO":
            reason = selection.reason if selection else "ANALYSIS_UNAVAILABLE"
            raise UnityPackageError(f"Automatic Prefab selection is ambiguous ({reason}); choose a Prefab explicitly")
        raise UnityPackageError(f"Prefab selection is unavailable: {choice}")

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
        if (
            event.type == "TIMER"
            and self._progress_monitor is not None
            and self._progress_monitor.state.status == ImportProgressStatus.WORKING
        ):
            # Keep elapsed time and the current stage visible while the
            # background preparation timer is waiting for new work events.
            self._progress_monitor.heartbeat()
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
        if not getattr(self, "group_child", False) and not getattr(bpy.app, "background", False) and context.window is not None:
            self._set_prepare_state("FILE_SELECTED")
            self._start_async_prepare(context, package_path)
            return {"RUNNING_MODAL"}
        try:
            self._set_prepare_state("FILE_SELECTED")
            self._prepare_import(context, package_path)
            return self._run_import(context)
        except Exception as exc:
            self._set_prepare_state("ERROR")
            self._progress_failure_message = str(exc)
            self.report({"ERROR"}, str(exc))
            print(f"[UnityPackage Importer] Import preparation failed: {exc}")
            self._cleanup_prepared(remove=True)
            self._finish_performance(context)
            return {"CANCELLED"}

    def _run_import(self, context):
        self._set_prepare_state("IMPORTING")
        return self._perform_import(context)

    def _collect_selective_guids(self, prefabs, planning_db: AssetDatabase) -> set[str]:
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
        if prefabs is not None:
            if not isinstance(prefabs, (list, tuple, set)):
                prefabs = [prefabs]
            for prefab in prefabs:
                selected_guid = planning_db.guid_for_path(prefab.path)
                if selected_guid:
                    wanted.add(selected_guid.lower())
                selected_analysis = next((item for item in self._candidate_analyses
                                          if (selected_guid and item.guid.lower() == selected_guid.lower())
                                          or Path(item.prefab_path).resolve() == Path(prefab.path).resolve()), None)
                if selected_analysis is not None:
                    for guid in selected_analysis.required_visual_guids:
                        record = index.records.get(guid)
                        if record is None:
                            continue
                        suffix = Path(record.unity_path).suffix.lower()
                        if suffix == ".prefab":
                            wanted.add(guid)
                        elif suffix == ".fbx":
                            fbx_guids.add(guid)
                for guid in prefab.referenced_fbx_guids():
                    entry = planning_db.find_guid(guid)
                    if entry is None:
                        continue
                    suffix = entry.path.suffix.lower()
                    if suffix == ".fbx":
                        fbx_guids.add(entry.guid.lower())
                    elif suffix == ".mat":
                        material_guids.add(entry.guid.lower())
        diagnostic_add("selected_prefab_count", len(prefabs) if isinstance(prefabs, (list, tuple, set)) else (1 if prefabs is not None else 0))
        diagnostic_add("selected_fbx_guids", len(fbx_guids))
        if self.import_mode == "RAW_FBX" or (not fbx_guids and not prefabs):
            fbx_guids = records_with_suffix(".fbx")
        elif not fbx_guids:
            # Some Unity prefab exports omit the MeshFilter reference while
            # still shipping one unambiguous model representation.  Use that
            # representation only when package structure proves uniqueness;
            # never guess among multiple FBX candidates.
            package_fbxs = records_with_suffix(".fbx")
            if len(package_fbxs) == 1:
                fbx_guids = package_fbxs
                diagnostic_add("unique_package_fbx_fallback")
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
        planning_prefabs,
    ) -> tuple[Any, AssetDatabase, list[Path], list[Path]]:
        reader = self._package_reader
        index = self._package_index
        if reader is None or index is None:
            raise UnityPackageError("Package dependency index is unavailable")
        wanted = self._performance.measure(
            "selected_dependency_collection",
            self._collect_selective_guids,
            planning_prefabs,
            planning_db,
        )
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
            storage_root = (
                Path(bpy.path.abspath(self.source_storage_directory))
                if self.source_storage_directory else
                Path(bpy.utils.user_resource('DATAFILES')) / 'vapb' / 'sources'
            )
            self._set_phase(context, "UnityPackage原本を保管中")
            archived_source = archive_source(package_path, storage_root, package_key.sha256)

            planning_prefabs = []
            planning_unity_paths: list[str] = []
            selected_planning_path = None
            effective_prefab_choice = self._selected_prefab_choice or self.prefab_choice
            if (
                effective_prefab_choice == "AUTO"
                and self._composition_plan is not None
                and self._composition_plan.chooser_required
            ):
                raise UnityPackageError(
                    "Automatic composition requires an explicit choice: "
                    f"{self._composition_plan.chooser_reason or 'ambiguous composition'}"
                )
            if self.import_mode == "RECONSTRUCT" and prefab_paths:
                if effective_prefab_choice == "AUTO" and self._composition_plan is not None:
                    selected_paths = {
                        item.unity_path for item in self._candidate_analyses
                        if item.has_visual_source
                    }
                    planning_paths = [
                        path for path in prefab_paths
                        if path.relative_to(extraction_dir).as_posix() in selected_paths
                    ]
                else:
                    selected_planning_path = self._selected_prefab(prefab_paths)
                    planning_paths = [selected_planning_path] if selected_planning_path else []
                for planning_path in planning_paths:
                    try:
                        self._set_phase(context, "Parsing Prefab", 0.35, current_item=planning_path.name)
                        cached = self._candidate_prefabs.get(str(planning_path.resolve()))
                        if cached is not None:
                            planning_prefabs.append(cached)
                            diagnostic_add("prepared_prefab_reuses")
                        else:
                            planning_prefabs.append(self._performance.measure("prefab_parse", parse_prefab, planning_path))
                        planning_unity_paths.append(planning_path.relative_to(extraction_dir).as_posix())
                    except (OSError, UnicodeError, ValueError) as exc:
                        self.report({"WARNING"}, f"Prefab parse failed; skipping {planning_path.name}: {exc}")

            extraction, asset_db, fbx_paths, prefab_paths = self._extract_selected_dependencies(
                context,
                asset_db,
                planning_prefabs,
            )
            model_witness = (
                load_model_witness(Path(bpy.path.abspath(self.model_witness_path)),
                                   package_key.sha256, asset_db)
                if self.model_witness_path else None
            )
            extraction_dir = self._extraction_dir
            prefabs = []
            for planning_prefab, planning_unity_path in zip(planning_prefabs, planning_unity_paths):
                final_entry = asset_db.find_path(planning_unity_path)
                if final_entry is not None and final_entry.path.is_file():
                    prefab_data = replace(
                        planning_prefab,
                        path=final_entry.path,
                        asset_guid=final_entry.guid.lower(),
                    )
                    prefabs.append((prefab_data, final_entry.unity_path))
                else:
                    self.report({"WARNING"}, f"Prefab was not included in dependency extraction: {planning_prefab.path.name}")
            prefab = prefabs[0][0] if prefabs else None
            prefab_unity_path = prefabs[0][1] if prefabs else ""

            imported_objects = []
            if fbx_paths:
                self._set_phase(context, "Importing FBX", 0.55)

                def fbx_progress(path: Path, index: int, total: int, blocking: bool) -> None:
                    self._set_phase(
                        context,
                        "Importing FBX",
                        current_item=path.name,
                        current_index=index,
                        current_total=total,
                        blocking_operation=blocking,
                    )

                imported_objects = self._performance.measure(
                    "fbx_import",
                    import_fbx_files,
                    fbx_paths,
                    package_key.source_package_id,
                    fbx_progress,
                    {
                        str(path.resolve()): (asset_db.guid_for_path(path) or "").lower()
                        for path in fbx_paths
                    },
                )
                if not imported_objects:
                    raise UnityPackageError("FBX import produced no Blender objects")
                imported_objects = self._performance.measure(
                    "apply_import_options",
                    apply_import_options,
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
                    source_guid = asset_db.guid_for_path(Path(str(source_fbx)))
                    if source_guid:
                        # Native FBX import does not expose Unity local IDs;
                        # preserve the source asset identity so later joins
                        # can only use explicit semantic provenance.
                        obj["unity_source_fbx_guid"] = source_guid.lower()
            material_library = {}
            if self.use_materials:
                self._set_phase(context, "Building Materials and Textures", 0.75)
                material_library = self._performance.measure(
                    "material_build",
                    build_material_library,
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
                if material_library:
                    self._set_phase(
                        context,
                        "Building Materials and Textures",
                        current_index=len(material_library),
                        current_total=len(material_library),
                    )
                # Provider-only packages still need their non-canonical image
                # datablocks available for preserve-only dependency status.
                # They are not connected to Principled sockets, but loading
                # them is part of actual import rather than discovery.
                if not fbx_paths:
                    self._performance.measure(
                        "texture_load", load_textures_from_database, asset_db,
                        pack=not self.keep_extracted,
                    )
                self._performance.measure(
                    "dependency_capture",
                    capture_material_texture_dependencies,
                    context.scene,
                    material_library.values(),
                )
            prefab_roots = []
            prefab_object_maps = []
            composition_started = perf_counter()
            if prefabs and self.apply_prefab_transforms:
                package_label = package_key.package_name or "UnityPackage"
                package_collection = bpy.data.collections.new(f"VAPB Import — {package_label}")
                context.scene.collection.children.link(package_collection)
                members_collection = bpy.data.collections.new("Members")
                shared_collection = bpy.data.collections.new("Shared")
                package_collection.children.link(members_collection)
                package_collection.children.link(shared_collection)
                representation_paths: dict[str, list[Any]] = {}
                for obj in imported_objects:
                    representation_paths.setdefault(str(obj.get("unity_asset_path", "")), []).append(obj)
                representation_member_bindings: dict[str, list[dict[tuple[str, int, int], str]]] = {}
                prefab_by_guid = {
                    prefab.asset_guid.lower(): prefab
                    for prefab, _ in prefabs
                    if prefab.asset_guid
                }
                projection_sources = {}

                def projection_source(package_id, guid):
                    # This import owns one package database. Never select a
                    # different provider from a package-wide name/GUID search.
                    if package_id != package_key.source_package_id:
                        return None
                    if guid not in projection_sources:
                        entry = asset_db.find_guid(guid)
                        if entry is None or not entry.path.is_file():
                            return None
                        parsed = prefab_by_guid.get(guid)
                        if parsed is None and entry.path.suffix.lower() == '.prefab':
                            parsed = parse_prefab(entry.path)
                        projection_sources[guid] = (
                            PrefabSource.from_prefab(parsed, entry.source_package_id, guid)
                            if parsed is not None else PrefabSource(
                                None, entry.source_package_id, guid,
                                source_sha256(entry.path), guid,
                            )
                        )
                    return projection_sources[guid]
                model_source_index = ModelSourceSemanticIndex.from_prefabs(
                    prefab for prefab, _ in prefabs
                )
                effective_prefabs = [
                    (EffectivePrefabResolver(
                        lambda guid: prefab_by_guid.get(str(guid).lower()),
                        model_source_index=model_source_index,
                    ).resolve(prefab), path)
                    for prefab, path in prefabs
                ]
                for effective_prefab, _ in effective_prefabs:
                    bindings = effective_prefab.effective_material_bindings()
                    for representation_guid in effective_prefab.referenced_source_guids:
                        representation_member_bindings.setdefault(representation_guid, []).append(bindings)
                representation_needs_object_slots = {
                    guid: len({tuple(sorted(binding.items())) for binding in binding_sets}) > 1
                    for guid, binding_sets in representation_member_bindings.items()
                }
                used_source_templates = set()
                pending_witness_dependencies = []
                for prefab, prefab_unity_path in prefabs:
                    self._set_phase(context, "Reconstructing Prefab", current_item=prefab_unity_path or prefab.path.name)
                    member_collection = bpy.data.collections.new(prefab.display_name)
                    members_collection.children.link(member_collection)
                    member_analysis = next(
                        (item for item in self._candidate_analyses if item.unity_path == prefab_unity_path), None,
                    )
                    member_id = member_analysis.guid if member_analysis else prefab_unity_path
                    root_context_id = str(uuid4())
                    projection = project_occurrences(
                        PrefabSource.from_prefab(prefab, package_key.source_package_id, member_id),
                        root_context_id, projection_source, model_witness=model_witness,
                    )
                    for record in projection.records:
                        mesh_entry = asset_db.find_guid(record['mesh']['mesh_guid'])
                        if mesh_entry is not None and mesh_entry.path.is_file():
                            record['mesh']['source_package_id'] = mesh_entry.source_package_id
                            record['mesh']['source_sha256'] = source_sha256(mesh_entry.path)
                    member_objects = []
                    member_object_map = {}
                    model_instances = []
                    direct_sources = [(guid.lower(), None, None) for guid in sorted({
                        ref_guid(document.data.get("m_Mesh"))
                        for document in prefab.renderer_documents() + prefab.mesh_filter_documents()
                        if ref_guid(document.data.get("m_Mesh"))
                    })]
                    model_sources = model_instance_plans(projection, model_witness)
                    for guid, edge_path, target_uids in direct_sources + model_sources:
                        entry = asset_db.find_guid(guid)
                        if entry is None or entry.path.suffix.lower() != ".fbx" or not entry.path.is_file():
                            continue
                        candidates = representation_paths.get(entry.unity_path, [])
                        if target_uids is not None:
                            source_sha = model_witness.source_shas[guid]
                            candidates = [obj for obj in candidates
                                          if matches_witnessed_source(obj, guid, source_sha, target_uids)]
                        instance_object_map = {}
                        for source_object in candidates:
                            if source_object.name not in shared_collection.objects:
                                shared_collection.objects.link(source_object)
                            # Every effective composition member owns an Object
                            # realization.  Mesh data remains shared; renderer
                            # material state is assigned through OBJECT slots.
                            member_object = copy_with_receipt(source_object)
                            context.scene.collection.objects.link(member_object)
                            member_object["_vapb_use_object_material_slots"] = (
                                representation_needs_object_slots.get(entry.guid.lower(), False)
                            )
                            instance_object_map[source_object] = member_object
                            if edge_path is None:
                                member_object_map[source_object] = member_object
                            else:
                                member_object["_vapb_model_instance_edge_path"] = json.dumps(edge_path, sort_keys=True)
                                member_object["_vapb_model_transform_status"] = "UNRESOLVED"
                            if member_object.name not in member_collection.objects:
                                member_collection.objects.link(member_object)
                            member_objects.append(member_object)
                            used_source_templates.add(source_object)
                        for source_object, member_object in instance_object_map.items():
                            if source_object.parent in instance_object_map:
                                member_object.parent = instance_object_map[source_object.parent]
                            for modifier in member_object.modifiers:
                                if getattr(modifier, "object", None) in instance_object_map:
                                    modifier.object = instance_object_map[modifier.object]
                        if edge_path is not None and instance_object_map:
                            model_instances.append((edge_path, instance_object_map, entry, target_uids))
                    for source_object, member_object in member_object_map.items():
                        if source_object.parent in member_object_map:
                            member_object.parent = member_object_map[source_object.parent]
                        for modifier in member_object.modifiers:
                            if getattr(modifier, "object", None) in member_object_map:
                                modifier.object = member_object_map[modifier.object]
                    prefab_root, prefab_object_map = self._performance.measure(
                        "prefab_reconstruct",
                        build_prefab_hierarchy,
                        prefab,
                        member_objects,
                        package_key.source_package_id,
                        prefab_unity_path,
                        member_collection,
                        source_loader=projection_source,
                        root_context_id=root_context_id,
                        semantic_issues=projection.issues,
                    )
                    physics_snapshot = self._performance.measure("physbone_snapshot", extract_physbone_snapshot, prefab)
                    prefab_root["unity_physbone_source_schema"] = 1
                    prefab_root["unity_physbone_source_authority"] = "UNITY_SERIALIZED_MONOBEHAVIOUR"
                    prefab_root["unity_physbone_source_json"] = json.dumps(
                        physics_snapshot.to_dict(), ensure_ascii=False, sort_keys=True
                    )
                    prefab_root["unity_physbone_component_count"] = len(physics_snapshot.physbones)
                    prefab_root["unity_physbone_collider_count"] = len(physics_snapshot.colliders)
                    prefab_roots.append(prefab_root)
                    prefab_object_maps.append(prefab_object_map)
                    instance_nodes = {}
                    resolved_instance_nodes = set()
                    attached_native = {}
                    for edge_path, copied, model_entry, target_uids in model_instances:
                        parent = prefab_root
                        for depth, step in enumerate(edge_path, 1):
                            prefix = json.dumps(edge_path[:depth], sort_keys=True)
                            node = instance_nodes.get(prefix)
                            if node is None:
                                node = bpy.data.objects.new(f"PrefabInstance {step['prefab_instance_file_id']}", None)
                                member_collection.objects.link(node)
                                node["_vapb_model_instance_edge_path"] = prefix
                                node["_vapb_model_transform_status"] = "UNRESOLVED"
                                if depth == 1:
                                    instance_doc = next((doc for doc in prefab.documents
                                                         if doc.class_id == 1001
                                                         and doc.file_id == step["prefab_instance_file_id"]), None)
                                    match = re.search(r"m_TransformParent:\s*\{\s*fileID:\s*(-?\d+)",
                                                      instance_doc.raw) if instance_doc else None
                                    if match:
                                        transform_id = int(match.group(1))
                                        owner_id = (prefab.transforms[transform_id].game_object_id
                                                    if transform_id in prefab.transforms else None)
                                        mapped = prefab_object_map.get(owner_id)
                                        if transform_id == 0 or (mapped is not None and mapped.type == "EMPTY"
                                                                 and has_complete_transform(prefab, transform_id)):
                                            parent = mapped or prefab_root
                                            node["_vapb_model_parent_status"] = "EXACT"
                                            source = projection_source(step["source_package_id"],
                                                                       step["source_prefab_guid"])
                                            if (source is not None and source.prefab is not None
                                                    and step["container_asset_guid"] == prefab.asset_guid
                                                    and step["container_package_id"] == package_key.source_package_id
                                                    and step["container_revision_sha256"] == source_sha256(prefab.path)
                                                    and source.revision_sha256 == step["source_revision_sha256"]
                                                    and source_sha256(source.prefab.path) == source.revision_sha256
                                                    and source.prefab.asset_guid == step["source_prefab_guid"]
                                                    and source.package_id == step["source_package_id"]):
                                                effective = resolve_instance_transform(
                                                    prefab, step["prefab_instance_file_id"], source.prefab)
                                                if effective is not None:
                                                    apply_transform(node, effective)
                                                    resolved_instance_nodes.add(node)
                                                    node["_vapb_source_root_transform_id"] = str(
                                                        effective.source_transform_id)
                                else:
                                    node["_vapb_model_parent_status"] = "CONTAINER_EDGE_ONLY"
                                node.parent = parent
                                instance_nodes[prefix] = node
                            parent = node
                        for source_object, member_object in copied.items():
                            if source_object.parent not in copied:
                                proven = (len(edge_path) == 1 and parent in resolved_instance_nodes
                                          and validate_receipt_continuity(source_object)
                                          and validate_receipt_continuity(member_object)
                                          and member_object.get("_vapb_fbx_source_realization_id")
                                          == source_object.get("_vapb_fbx_realization_id"))
                                attached_native.setdefault(parent, []).append(proven)
                                if proven:
                                    bpy.context.view_layer.update()
                                    native_local = member_object.matrix_local.copy()
                                    source = projection_source(
                                        edge_path[0]["source_package_id"],
                                        edge_path[0]["source_prefab_guid"])
                                    direct_file_id = (root_direct_mesh_file_id(source.prefab, model_entry.guid)
                                                      if source is not None and source.prefab is not None else None)
                                    direct_mesh = direct_file_id is not None
                                    matching_records = [record for record in projection.records
                                                        if record["instance_edge_path"] == edge_path
                                                        and record["source_key"]["source_kind"] == "PREFAB_LOCAL"
                                                        and record["mesh"]["mesh_guid"].lower() == model_entry.guid.lower()
                                                        and record["mesh"]["mesh_file_id"] == direct_file_id]
                                    witnessed_mesh = (model_witness.mesh(model_entry.guid, direct_file_id)
                                                      if direct_mesh and model_witness is not None else None)
                                    frame_proven = (direct_mesh and len(copied) == 1
                                                    and target_uids is not None and len(target_uids) == 1
                                                    and len(matching_records) == 1
                                                    and witnessed_mesh is not None
                                                    and (witnessed_mesh.model_uid, witnessed_mesh.geometry_uid)
                                                    == target_uids[0])
                                    frame = (verified_direct_mesh_frame(model_entry.path, source_object)
                                             if frame_proven else None)
                                    member_object.parent = parent
                                    member_object.matrix_parent_inverse = Matrix.Identity(4)
                                    member_object.matrix_basis = frame if frame is not None else native_local
                                    if direct_mesh:
                                        member_object["_vapb_geometry_frame_status"] = (
                                            "EXACT" if frame is not None else "UNVERIFIED")
                                    member_object["_vapb_model_transform_status"] = "EXACT"
                                else:
                                    world = member_object.matrix_world.copy()
                                    member_object.parent = parent
                                    member_object.matrix_world = world
                    for node, results in attached_native.items():
                        if node in resolved_instance_nodes and results and all(results):
                            node["_vapb_model_transform_status"] = "EXACT"
                    composition_member = next(
                        (item for item in self._composition_plan.members
                         if item.unity_path == prefab_unity_path),
                        None,
                    ) if self._composition_plan else None
                    classification = (
                        composition_member.classification
                        if composition_member is not None
                        else (member_analysis.candidate_kind if member_analysis else "UNKNOWN_EDITABLE")
                    )
                    member_collection["unity_composition_member_id"] = member_id
                    member_collection["unity_composition_classification"] = classification
                    prefab_root["unity_composition_member_id"] = member_id
                    prefab_root["unity_composition_classification"] = classification
                    for member_object in member_objects:
                        member_object["unity_composition_member_id"] = member_id
                        member_object["unity_composition_classification"] = classification
                    prefab_root['_vapb_root_context_id'] = root_context_id
                    if model_witness is not None:
                        prefab_root['_vapb_witness_package_sha256'] = package_key.sha256
                    for record in projection.records:
                        # Nested semantic owners need their own realization;
                        # do not map them onto same-fileID root GameObjects.
                        if not record['instance_edge_path']:
                            owner = prefab_object_map.get(record['owner']['owner_game_object_id'])
                            if owner is not None:
                                owner['_vapb_semantic_owner_id'] = semantic_owner_id(record)
                                owner['_vapb_root_context_id'] = root_context_id
                    prefab_root['_vapb_renderer_occurrences'] = json.dumps(projection.to_dict(), sort_keys=True)
                    from ..blender.material_owner_usage import capture_owner_usage
                    prefab_root['_vapb_material_owner_label'] = prefab.display_name
                    capture_owner_usage(projection.records, prefab.display_name, bpy.data.materials)
                    for member_object in member_objects:
                        member_object['_vapb_root_context_id'] = root_context_id
                        member_object['_vapb_native_object_id'] = str(uuid4())
                        member_object['unity_source_package_id'] = package_key.source_package_id
                    if self.use_materials:
                        self._performance.measure(
                            "material_mapping", apply_prefab_materials,
                            prefab, prefab_object_map, asset_db, material_library, context.scene,
                            imported_objects, member_id,
                        )
                        self._performance.measure(
                            "material_mapping", apply_prefab_modification_materials,
                            prefab, member_object_map, asset_db, material_library, context.scene,
                            member_id=member_id,
                        )
                        if model_witness is not None:
                            scoped_records = [record for record in projection.records
                                              if record.get('mesh', {}).get('mesh_guid')
                                              in model_witness.source_shas]
                            bindings, bridge_issues = plan_witness_realizations(
                                scoped_records,
                                [obj for obj in member_objects if validate_receipt_continuity(obj)],
                                model_witness,
                            )
                            for issue in bridge_issues:
                                projection.issues.append({"code": issue["code"],
                                                          "root_context_id": root_context_id,
                                                          "occurrence_id": issue["occurrence_id"]})
                            from ..blender.model_witness_bridge import plan_witness_skin_carriers, realize_witness_skin_carriers
                            context.view_layer.update()
                            skin_plans, skin_issues = plan_witness_skin_carriers(
                                bindings, model_witness, prefab, prefab_object_map)
                            projection.issues.extend(skin_issues)
                            if not realize_witness_skin_carriers(skin_plans, member_collection, bindings, prefab_object_map, prefab):
                                projection.issues.append({'code': 'SKIN_POSE_FRAME_UNSUPPORTED',
                                                          'root_context_id': root_context_id})
                            pending_witness_dependencies.extend(
                                plan_witness_material_dependencies(bindings, package_key.sha256)
                            )
                            prefab_root['_vapb_renderer_occurrences'] = json.dumps(projection.to_dict(), sort_keys=True)
                if pending_witness_dependencies:
                    ready, rejected = reserve_witness_slots(pending_witness_dependencies, bpy.data.objects)
                    for dependency in ready:
                        capture_dependency(context.scene, dependency)
                    if rejected:
                        self.report({"WARNING"}, f"Unity model witness: {len(rejected)} consumer slot(s) unresolved")
                for source_object in used_source_templates:
                    source_object.hide_set(True)
                    source_object.hide_render = True
            self._performance.add("package_composition", perf_counter() - composition_started)
            prefab_root = prefab_roots[0] if prefab_roots else None
            prefab_object_map = prefab_object_maps[0] if prefab_object_maps else {}

            scene = context.scene
            scene_metadata_started = perf_counter()
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
                    "source_archive_path": str(archived_source),
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
            scene["unitypackage_source_archive"] = str(archived_source)
            scene["unitypackage_source_package_id"] = package_key.source_package_id
            scene["unitypackage_package_sha256"] = package_key.sha256
            scene["unitypackage_extracted_root"] = str(extraction_dir)
            scene["unitypackage_fbx_count"] = len(fbx_paths)
            scene["unitypackage_prefab"] = str(prefab.path) if prefab else ""
            if not getattr(self, "group_child", False) and self._composition_plan is not None:
                automatic_composition = (self._selected_prefab_choice or self.prefab_choice) == "AUTO"
                composition_members = (
                    self._composition_plan.members
                    if automatic_composition
                    else tuple(item for item in self._composition_plan.members if item.unity_path == prefab_unity_path)
                )
                composition_member_ids = {item.member_id for item in composition_members}
                scene["unitypackage_composition"] = json.dumps({
                    "mode": "AUTOMATIC_COMPOSITION" if automatic_composition else "EXPLICIT_SINGLE_MEMBER",
                    "members": [
                        {
                            "member_id": member.member_id,
                            "unity_asset_path": member.unity_path,
                            "classification": member.classification,
                            "representation_ids": sorted(member.referenced_representation_ids),
                        }
                        for member in composition_members
                    ],
                    "helpers": [
                        {
                            "guid": item.guid,
                            "unity_asset_path": item.unity_path,
                            "display_name": item.display_name,
                            "candidate_kind": item.candidate_kind,
                            "nested_prefab_guids": sorted(item.nested_prefab_guids),
                            "reasons": list(item.reasons),
                        }
                        for item in self._composition_plan.helpers
                    ] if automatic_composition else [],
                    "representations": [
                        {"asset_guid": item.asset_guid, "member_ids": sorted(item.member_ids)}
                        for item in self._composition_plan.representations
                        if automatic_composition or item.member_ids & composition_member_ids
                    ],
                    "chooser_required": self._composition_plan.chooser_required,
                    "chooser_reason": self._composition_plan.chooser_reason,
                    "conflicting_visual_guids": sorted(self._composition_plan.conflicting_visual_guids),
                }, sort_keys=True)
            scene["unitypackage_import_sequence"] = [
                package["source_package_id"] for package in package_registry.packages.values()
            ]
            object_registry_items = list(imported_objects)
            for object_map in prefab_object_maps:
                object_registry_items.extend(object_map.values())
            object_registry_items.extend(prefab_roots)
            register_datablocks(scene, object_registry_items, package_key.source_package_id, "Object")
            register_datablocks(scene, material_library.values(), package_key.source_package_id, "Material")
            register_datablocks(
                scene,
                [image for image in bpy.data.images if image.get("unity_source_package_id") == package_key.source_package_id],
                package_key.source_package_id,
                "Image",
            )
            if not getattr(self, "group_child", False) and self._sibling_discovery is not None:
                scene["unitypackage_provider_provenance"] = json.dumps(
                    getattr(self._sibling_discovery, "resolution_provenance", {}), sort_keys=True
                )
            if not getattr(self, "group_child", False):
                discovery = self._sibling_discovery
                if discovery is None:
                    discovery = discover_siblings(package_path)
                scene["unitypackage_sibling_discovery"] = {
                    "status": discovery.status,
                    "visual_status": getattr(discovery, "visual_status", discovery.status),
                    "root_package": discovery.root_package,
                    "related_packages": [candidate.path for candidate in discovery.packages],
                    "unresolved_guids": sorted(discovery.unresolved_guids),
                    "unresolved_visual_guids": sorted(getattr(discovery, "unresolved_visual_guids", discovery.unresolved_guids)),
                    "ambiguous_guids": sorted(discovery.ambiguous_guids),
                    "ambiguous_visual_guids": sorted(getattr(discovery, "ambiguous_visual_guids", discovery.ambiguous_guids)),
                    "unresolved_external_guids": sorted(getattr(discovery, "unresolved_external_guids", set())),
                    "manifest_entries": getattr(discovery, "manifest_entries", 0),
                    "accounting": getattr(discovery, "accounting", {}),
                }
                visual_status = getattr(discovery, "visual_status", discovery.status)
                if visual_status in {"COMPLETE", "PARTIAL", "AMBIGUOUS"} and discovery.packages and self._sibling_import_together:
                    group_id = uuid4().hex
                    scene["unitypackage_group_import"] = {
                        "group_import_id": group_id,
                        "primary_package_id": package_key.source_package_id,
                        "related_package_ids": [candidate.package_id for candidate in discovery.packages],
                    }
                    scene["unitypackage_provider_provenance"] = json.dumps(
                        getattr(discovery, "resolution_provenance", {}), sort_keys=True
                    )
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
                            source_storage_directory=self.source_storage_directory,
                            group_child=True,
                        )
                        if "FINISHED" not in result:
                            raise UnityPackageError(f"Related Package import did not finish: {Path(candidate.path).name}")
                elif visual_status in {"AMBIGUOUS", "PARTIAL"}:
                    self.report({"WARNING"}, f"Sibling discovery {discovery.status}; Import Together was not auto-selected")
            # Group children are synchronous; only resolve the primary after
            # every selected provider has created its materials and images.
            self._set_phase(context, "Resolving dependencies")
            dependency_counts = self._performance.measure("dependency_resolution", resolve_after_import, scene)
            from ..blender.material_owner_usage import capture_scene_owner_usage
            capture_scene_owner_usage(scene.objects, bpy.data.materials)
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
            outcome = scene_import_outcome(scene)
            if outcome["overall"] == "PARTIAL":
                self.report({"WARNING"},
                    "Scene内のImport記録に未解決項目があります。"
                    "3DビューのNキー > VAPB Result > Import結果を確認してください")
            collisions = load_scene_registry(scene).detect_collisions()
            if collisions:
                self.report({"WARNING"}, f"Detected {len(collisions)} cross-package identity collision(s)")
            if extraction.errors:
                for error in extraction.errors:
                    print(f"[UnityPackage Importer] {error}")
                self.report({"WARNING"}, f"Imported with {len(extraction.errors)} extraction warning(s); see console")
            self.report({"INFO"}, f"Imported {len(fbx_paths)} FBX file(s)")
            self._performance.add("scene_metadata", perf_counter() - scene_metadata_started)
            self._set_phase(context, "Finalizing import")
            self._set_phase(context, "Import complete")
            self._set_prepare_state("FINISHED")
            self._modal_registered = False
            self._cleanup_prepared(remove=not self.keep_extracted)
            self._finish_performance(context)
            return {"FINISHED"}
        except Exception as exc:
            self._set_prepare_state("ERROR")
            self._progress_failure_message = str(exc)
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
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            return
        selected = session.operator._candidate_selection
        composition = session.operator._composition_plan
        if composition is not None and not composition.chooser_required:
            self.layout.label(text=(
                f"Automatic composition: {len(composition.members)} editable member(s), "
                f"{len(composition.representations)} shared representation(s)"
            ))
        elif selected is not None:
            self.layout.label(text=f"Automatic result: {selected.reason}")
        for candidate in session.operator._candidate_analyses:
            row = self.layout.row()
            marker = "Recommended" if selected and selected.token == candidate.token else candidate.visual_status
            row.label(text=f"{candidate.display_name}: {candidate.candidate_kind}, {marker}")
            detail = self.layout.row()
            detail.label(
                text=(
                    f"Renderers {candidate.renderer_count}, material slots {candidate.material_slot_count}, "
                    f"missing {len(candidate.unresolved_visual_guids)}, ambiguous {len(candidate.ambiguous_visual_guids)}"
                )
            )

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        session.operator._selected_prefab_choice = self.prefab_choice
        session.operator._discover_selected_visual_dependencies()
        discovery = session.operator._sibling_discovery
        if discovery and getattr(discovery, "unresolved_visual_guids", set()):
            session.operator._set_prepare_state("WAITING_MISSING_DEPENDENCY_RESOLUTION")
            _schedule_prepared_session(self.session_id, show_dialog=False, show_missing_dialog=True)
        elif discovery and discovery.packages:
            _schedule_prepared_session(self.session_id, show_dialog=False, show_group_dialog=True)
        else:
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


class UNITYPACKAGE_OT_missing_dependencies(bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_missing_dependencies"
    bl_label = "Missing Visual Dependencies"

    session_id: StringProperty(options={"HIDDEN"})
    action: EnumProperty(
        name="Action",
        items=[
            ("CONTINUE", "Continue With Missing Assets", "Import all currently resolved assets"),
            ("CANCEL", "Cancel", "Cancel this prepared import"),
        ],
        default="CONTINUE",
    )

    def draw(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.layout.label(text="Prepared UnityPackage session expired")
            return
        discovery = session.operator._sibling_discovery
        missing = sorted(getattr(discovery, "unresolved_visual_guids", set())) if discovery else []
        self.layout.label(text=f"Missing visual dependencies: {len(missing)}")
        self.layout.label(text="Materials and textures are validated by GUID.")
        self.layout.operator("import_scene.unitypackage_locate_provider", text="Locate UnityPackage...").session_id = self.session_id
        self.layout.operator("import_scene.unitypackage_locate_folder", text="Locate Folder...").session_id = self.session_id
        self.layout.prop(self, "action", expand=True)

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        if self.action == "CANCEL":
            _discard_prepared_session(self.session_id, context)
            return {"CANCELLED"}
        session.operator._sibling_import_together = True
        _schedule_prepared_session(self.session_id, show_dialog=False)
        return {"FINISHED"}

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=640)

    def cancel(self, context):
        _discard_prepared_session(self.session_id, context)


class UNITYPACKAGE_OT_locate_provider(ImportHelper, bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_locate_provider"
    bl_label = "Locate UnityPackage Provider"
    filename_ext = ".unitypackage"
    filter_glob: StringProperty(default="*.unitypackage", options={"HIDDEN"})
    session_id: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        if not session.operator._accept_manual_package(Path(self.filepath)):
            self.report({"WARNING"}, "Selected UnityPackage provides none of the missing visual dependencies")
            return {"CANCELLED"}
        if session.operator._sibling_discovery and session.operator._sibling_discovery.unresolved_visual_guids:
            _schedule_prepared_session(self.session_id, show_dialog=False, show_missing_dialog=True)
        else:
            session.operator._sibling_import_together = True
            _schedule_prepared_session(self.session_id, show_dialog=False)
        return {"FINISHED"}


class UNITYPACKAGE_OT_locate_folder(bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_locate_folder"
    bl_label = "Locate UnityPackage Folder"
    directory: StringProperty(subtype="DIR_PATH")
    session_id: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        count, ambiguous = session.operator._accept_manual_folder(Path(self.directory))
        if not count:
            self.report({"WARNING"}, "No selected-folder UnityPackage provides a missing visual dependency")
            return {"CANCELLED"}
        if ambiguous:
            self.report({"WARNING"}, f"Ambiguous providers require explicit package selection: {len(ambiguous)} GUID(s)")
        _schedule_prepared_session(self.session_id, show_dialog=False, show_missing_dialog=bool(session.operator._sibling_discovery.unresolved_visual_guids))
        return {"FINISHED"}

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class UNITYPACKAGE_OT_import_siblings(bpy.types.Operator):
    bl_idname = "import_scene.unitypackage_siblings"
    bl_label = "Related UnityPackages detected"

    session_id: StringProperty(options={"HIDDEN"})
    import_action: EnumProperty(
        name="Action",
        items=[
            ("TOGETHER", "Import Together", "Import the primary and uniquely related Packages"),
            ("PRIMARY_ONLY", "Import Selected Only", "Import only the primary Package"),
        ],
        default="TOGETHER",
    )

    def draw(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        layout = self.layout
        if session is None or session.operator._sibling_discovery is None:
            layout.label(text="Prepared UnityPackage session expired")
            return
        discovery = session.operator._sibling_discovery
        layout.label(text=f"Discovery status: {discovery.status}")
        layout.label(text=f"Primary: {Path(session.operator.filepath).name}")
        layout.label(text="Related:")
        for candidate in discovery.packages:
            layout.label(text=f"  {Path(candidate.path).name}")
        layout.label(text=f"Resolved dependencies: {sum(item.match_count for item in discovery.packages)}")
        layout.prop(self, "import_action", expand=True)

    def execute(self, context):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is None:
            self.report({"ERROR"}, "Prepared UnityPackage session expired")
            return {"CANCELLED"}
        session.operator._sibling_import_together = self.import_action == "TOGETHER"
        _schedule_prepared_session(self.session_id, show_dialog=False)
        return {"FINISHED"}

    def invoke(self, context, _event):
        session = _PREPARED_SESSIONS.get(self.session_id)
        if session is not None and session.operator._sibling_discovery.status == "PARTIAL":
            self.import_action = "PRIMARY_ONLY"
        return context.window_manager.invoke_props_dialog(self, width=620)

    def cancel(self, context):
        _discard_prepared_session(self.session_id, context)


UNITYPACKAGE_CLASSES = (
    UNITYPACKAGE_OT_import,
    UNITYPACKAGE_OT_import_prepared,
    UNITYPACKAGE_OT_import_prefab,
    UNITYPACKAGE_OT_missing_dependencies,
    UNITYPACKAGE_OT_locate_provider,
    UNITYPACKAGE_OT_locate_folder,
    UNITYPACKAGE_OT_import_siblings,
)
