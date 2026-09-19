"""Large, non-modal foreground progress overlay for Blender 3D Views."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
import threading
from typing import Any


_STAGE_LABELS = {
    "READING_PACKAGE": "Reading package metadata",
    "ANALYZING_PREFABS": "Analyzing Prefabs",
    "RESOLVING_PACKAGES": "Resolving related packages",
    "IMPORTING_FBX": "Importing FBX",
    "BUILDING_HIERARCHY": "Building avatar hierarchy",
    "CREATING_VISUALS": "Creating materials and textures",
    "RESOLVING_DEPENDENCIES": "Resolving dependencies",
    "FINALIZING": "Finalizing import",
}
_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\meiryo.ttc"),
    Path(r"C:\Windows\Fonts\YuGothM.ttc"),
    Path(r"C:\Windows\Fonts\msgothic.ttc"),
)


class ImportProgressOverlay:
    """Own one 3D View draw handler for one foreground import session."""

    def __init__(self, context: Any, *, space_view_3d: Any = None):
        self.context = context
        self.area = getattr(context, "area", None)
        if getattr(self.area, "type", "") != "VIEW_3D":
            window = getattr(context, "window", None)
            screen = getattr(window, "screen", None)
            self.area = next(
                (
                    area
                    for area in getattr(screen, "areas", ())
                    if getattr(area, "type", "") == "VIEW_3D"
                ),
                None,
            )
        self.space_view_3d = space_view_3d or self._default_space_view_3d()
        self._handle = None
        self._snapshot: dict[str, Any] | None = None
        self._font_id: int | None = None
        self._font_path: str | None = None
        self.install_count = 0
        self.draw_callback_count = 0
        self.gpu_draw_count = 0
        self.last_draw_time: float | None = None
        self.last_draw_thread: int | None = None
        self.removed_count = 0
        self.debug_events: list[str] = []
        self._debug_once: set[str] = set()
        self._debug(
            f"target area={self._area_debug_name(self.area)} "
            f"area_type={getattr(self.area, 'type', None)} "
            f"thread={threading.get_ident()}"
        )

    @staticmethod
    def _area_debug_name(area: Any) -> str:
        if area is None:
            return "None"
        try:
            return f"{getattr(area, 'type', '?')}@{area.as_pointer():x}"
        except (AttributeError, TypeError, ValueError):
            return f"{getattr(area, 'type', '?')}@{id(area):x}"

    @staticmethod
    def _areas_match(target: Any, current: Any) -> bool:
        if target is current:
            return True
        try:
            target_pointer = target.as_pointer()
            current_pointer = current.as_pointer()
        except (AttributeError, TypeError, ValueError):
            return False
        return bool(target_pointer and target_pointer == current_pointer)

    def _debug(self, message: str, *, once: str | None = None) -> None:
        if once is not None:
            if once in self._debug_once:
                return
            self._debug_once.add(once)
        entry = f"[ProgressOverlay] {message}"
        self.debug_events.append(entry)
        print(entry)

    @staticmethod
    def _default_space_view_3d():
        try:
            import bpy  # type: ignore

            return bpy.types.SpaceView3D
        except (ImportError, AttributeError):
            return None

    @property
    def active(self) -> bool:
        return self._handle is not None

    @property
    def snapshot(self) -> dict[str, Any] | None:
        return dict(self._snapshot) if self._snapshot is not None else None

    def start(self, state: Any) -> None:
        if self.area is None:
            self._debug("install skipped: no VIEW_3D target", once="no-target")
            return
        self.install_count += 1
        self._debug(
            f"install target area={self._area_debug_name(self.area)} "
            f"thread={threading.get_ident()}"
        )
        self._snapshot = state.snapshot()
        if self._handle is None and self.space_view_3d is not None:
            try:
                self._handle = self.space_view_3d.draw_handler_add(
                    self._draw_callback,
                    (),
                    "WINDOW",
                    "POST_PIXEL",
                )
                self._debug(f"handler={self._handle!r}")
            except (AttributeError, RuntimeError, TypeError):
                self._handle = None
                self._debug("handler registration failed")
        elif self.space_view_3d is None:
            self._debug("handler registration skipped: SpaceView3D unavailable")
        self._tag_redraw()

    def update(self, state: Any) -> None:
        if not self.active:
            self.start(state)
            return
        self._snapshot = state.snapshot()
        self._tag_redraw()

    def finish(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None and self.space_view_3d is not None:
            try:
                self.space_view_3d.draw_handler_remove(handle, "WINDOW")
                self.removed_count += 1
                self._debug(f"remove handler={handle!r} thread={threading.get_ident()}")
            except (AttributeError, RuntimeError):
                pass
        self._unload_font()
        self._snapshot = None
        self._tag_redraw()

    def text_lines(self) -> tuple[str, ...]:
        """Return the user-facing and diagnostic lines for the current state."""
        snapshot = self._snapshot or {}
        blocking = bool(snapshot.get("blocking_operation"))
        if blocking:
            primary = (
                "LOADING",
                "モデルを読み込んでいます",
                "お待ちください",
                "操作不要です。Blenderを閉じないでください。",
            )
        else:
            primary = (
                "LOADING",
                "UnityPackageを読み込んでいます",
                "お待ちください",
                "操作不要です。Blenderを閉じないでください。",
            )
        stage = _STAGE_LABELS.get(str(snapshot.get("stage", "")), str(snapshot.get("stage", "")))
        item = str(snapshot.get("current_item") or "")
        index = snapshot.get("current_index")
        total = snapshot.get("current_total")
        if index is not None and total is not None and item:
            detail = f"{index} / {total} — {item}"
        elif item:
            detail = item
        else:
            detail = ""
        elapsed = int(max(0.0, float(snapshot.get("elapsed_seconds") or 0.0)))
        diagnostics = (stage, detail, f"Elapsed: {elapsed} sec")
        if blocking and item:
            diagnostics = (
                stage,
                f"Importing FBX: {item}",
                "この処理中はBlenderが一時的に応答しなくなる場合があります。",
                f"Elapsed: {elapsed} sec",
            )
        return primary + ("",) + diagnostics

    def _tag_redraw(self) -> None:
        if self.area is not None:
            try:
                self.area.tag_redraw()
            except (AttributeError, RuntimeError):
                pass

    def _load_font(self, blf) -> int:
        if self._font_id is not None:
            return self._font_id
        for path in _FONT_CANDIDATES:
            if not path.is_file():
                continue
            try:
                self._font_id = blf.load(str(path))
                self._font_path = str(path)
                return self._font_id
            except (OSError, RuntimeError):
                continue
        self._font_id = 0
        return self._font_id

    def _unload_font(self) -> None:
        if self._font_path is None:
            self._font_id = None
            return
        try:
            import blf  # type: ignore

            blf.unload(self._font_path)
        except (ImportError, OSError, RuntimeError):
            pass
        self._font_id = None
        self._font_path = None

    @staticmethod
    def _draw_panel(gpu, batch_for_shader, width: float, height: float) -> None:
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        panel_width = min(max(680.0, width * 0.58), max(300.0, width - 80.0))
        panel_height = min(310.0, max(210.0, height - 80.0))
        left = (width - panel_width) / 2.0
        bottom = (height - panel_height) / 2.0
        vertices = (
            (left, bottom),
            (left + panel_width, bottom),
            (left + panel_width, bottom + panel_height),
            (left, bottom),
            (left + panel_width, bottom + panel_height),
            (left, bottom + panel_height),
        )
        batch = batch_for_shader(shader, "TRIS", {"pos": vertices})
        gpu.state.blend_set("ALPHA")
        shader.bind()
        shader.uniform_float("color", (0.01, 0.015, 0.025, 0.90))
        batch.draw(shader)
        gpu.state.blend_set("NONE")

    def _draw_callback(self) -> None:
        self.draw_callback_count += 1
        self.last_draw_time = perf_counter()
        self.last_draw_thread = threading.get_ident()
        self._debug(
            f"draw callback count={self.draw_callback_count} "
            f"thread={self.last_draw_thread}",
            once="draw-callback",
        )
        snapshot = self._snapshot
        if not snapshot or snapshot.get("status") != "WORKING":
            self._debug("draw skipped: no WORKING snapshot", once="skip-state")
            return
        try:
            import blf  # type: ignore
            import bpy  # type: ignore
            import gpu  # type: ignore
            from gpu_extras.batch import batch_for_shader  # type: ignore

            current_area = getattr(bpy.context, "area", None)
            if self.area is not None and not self._areas_match(self.area, current_area):
                self._debug(
                    "draw skipped: context area identity mismatch "
                    f"target={self._area_debug_name(self.area)} "
                    f"current={self._area_debug_name(current_area)}",
                    once="area-mismatch",
                )
                return
            region = getattr(bpy.context, "region", None)
            if region is None or not getattr(region, "width", 0) or not getattr(region, "height", 0):
                self._debug("draw skipped: invalid WINDOW region", once="invalid-region")
                return
            self._debug(
                f"draw target area={self._area_debug_name(current_area)} "
                f"region={region.width}x{region.height}",
                once="valid-region",
            )
            width = float(region.width)
            height = float(region.height)
            self._draw_panel(gpu, batch_for_shader, width, height)
            self.gpu_draw_count += 1
            self._debug("draw LOADING", once="draw-loading")
            font_id = self._load_font(blf)
            lines = self.text_lines()
            panel_center = height / 2.0
            line_specs = (
                (58, (1.0, 1.0, 1.0, 1.0)),
                (34, (0.96, 0.98, 1.0, 1.0)),
                (34, (0.96, 0.98, 1.0, 1.0)),
                (18, (0.78, 0.82, 0.88, 1.0)),
                (25, (0.70, 0.75, 0.82, 1.0)),
                (22, (0.84, 0.87, 0.92, 1.0)),
                (19, (1.0, 0.72, 0.36, 1.0)),
                (18, (0.70, 0.74, 0.80, 1.0)),
                (18, (0.70, 0.74, 0.80, 1.0)),
            )
            visible = [(line, line_specs[index]) for index, line in enumerate(lines) if line]
            total_height = sum(size * 1.25 for _, (size, _color) in visible)
            cursor = panel_center + total_height / 2.0 - 8.0
            for line, (size, color) in visible:
                blf.size(font_id, size)
                _width, line_height = blf.dimensions(font_id, line)
                cursor -= line_height
                blf.color(font_id, *color)
                blf.position(font_id, (width - _width) / 2.0, cursor, 0)
                blf.draw(font_id, line)
                cursor -= size * 0.25
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
            # A draw handler must never make Blender's viewport unusable.
            self._debug(f"draw failed: {type(exc).__name__}: {exc}", once="draw-error")
            return
