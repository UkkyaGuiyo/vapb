"""Thread-safe, Blender-independent progress state for UnityPackage imports.

The model only reports work that the importer is already doing.  UI adapters
may render ``status_text`` and ``progress_fraction``; unknown-duration work
intentionally has no percentage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable, Protocol


class ImportProgressStatus:
    IDLE = "IDLE"
    WORKING = "WORKING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ImportProgressStage:
    IDLE = "IDLE"
    READING_PACKAGE = "READING_PACKAGE"
    ANALYZING_PREFABS = "ANALYZING_PREFABS"
    RESOLVING_PACKAGES = "RESOLVING_PACKAGES"
    IMPORTING_FBX = "IMPORTING_FBX"
    BUILDING_HIERARCHY = "BUILDING_HIERARCHY"
    CREATING_VISUALS = "CREATING_VISUALS"
    RESOLVING_DEPENDENCIES = "RESOLVING_DEPENDENCIES"
    FINALIZING = "FINALIZING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


_STAGES = (
    ImportProgressStage.READING_PACKAGE,
    ImportProgressStage.ANALYZING_PREFABS,
    ImportProgressStage.RESOLVING_PACKAGES,
    ImportProgressStage.IMPORTING_FBX,
    ImportProgressStage.BUILDING_HIERARCHY,
    ImportProgressStage.CREATING_VISUALS,
    ImportProgressStage.RESOLVING_DEPENDENCIES,
    ImportProgressStage.FINALIZING,
)
_STAGE_LABELS = {
    ImportProgressStage.READING_PACKAGE: "Reading package metadata",
    ImportProgressStage.ANALYZING_PREFABS: "Analyzing Prefabs",
    ImportProgressStage.RESOLVING_PACKAGES: "Resolving related packages",
    ImportProgressStage.IMPORTING_FBX: "Importing FBX",
    ImportProgressStage.BUILDING_HIERARCHY: "Building avatar hierarchy",
    ImportProgressStage.CREATING_VISUALS: "Creating materials and textures",
    ImportProgressStage.RESOLVING_DEPENDENCIES: "Resolving dependencies",
    ImportProgressStage.FINALIZING: "Finalizing import",
    ImportProgressStage.COMPLETE: "Import complete",
    ImportProgressStage.FAILED: "Import failed",
}
_STAGE_INDEX = {stage: index for index, stage in enumerate(_STAGES, 1)}


class ImportProgressSink(Protocol):
    def update(self, state: "ImportProgressState") -> None: ...

    def clear(self) -> None: ...


@dataclass
class ImportProgressState:
    stage: str = ImportProgressStage.IDLE
    stage_index: int = 0
    stage_count: int = len(_STAGES)
    current_item: str = ""
    current_index: int | None = None
    current_total: int | None = None
    started_at: float | None = None
    last_activity_at: float | None = None
    ended_at: float | None = None
    message: str = ""
    blocking_operation: bool = False
    status: str = ImportProgressStatus.IDLE
    failure_message: str = ""

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else monotonic()
        return max(0.0, end - self.started_at)

    @property
    def seconds_since_activity(self) -> float | None:
        if self.last_activity_at is None:
            return None
        end = self.ended_at if self.ended_at is not None else monotonic()
        return max(0.0, end - self.last_activity_at)

    @property
    def progress_fraction(self) -> float | None:
        if self.current_index is None or self.current_total in (None, 0):
            return None
        return min(1.0, max(0.0, self.current_index / self.current_total))

    def status_text(self, now: float | None = None) -> str:
        if self.status == ImportProgressStatus.IDLE:
            return ""
        label = _STAGE_LABELS.get(self.stage, self.stage)
        parts = [f"UnityPackage Import — {label}"]
        if self.stage_index and self.status == ImportProgressStatus.WORKING:
            parts.append(f"Stage {self.stage_index}/{self.stage_count}")
        if self.current_index is not None and self.current_total is not None:
            parts.append(f"{self.current_index}/{self.current_total}")
        if self.current_item:
            parts.append(self.current_item)
        if self.blocking_operation:
            parts.append("Blender may temporarily stop responding during this step.")
        elapsed = self.elapsed_seconds if now is None else max(0.0, now - (self.started_at or now))
        parts.append(f"Elapsed: {elapsed:.1f}s")
        return " — ".join(parts)

    def snapshot(self, now: float | None = None) -> dict[str, object]:
        return {
            "stage": self.stage,
            "stage_index": self.stage_index,
            "stage_count": self.stage_count,
            "current_item": self.current_item,
            "current_index": self.current_index,
            "current_total": self.current_total,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "elapsed_seconds": self.elapsed_seconds,
            "message": self.message,
            "blocking_operation": self.blocking_operation,
            "status": self.status,
            "failure_message": self.failure_message,
            "status_text": self.status_text(now),
            "progress_fraction": self.progress_fraction,
        }


@dataclass
class ImportProgressMonitor:
    sink: ImportProgressSink | None = None
    clock: Callable[[], float] = monotonic
    logger: Callable[[str], None] | None = None
    state: ImportProgressState = field(default_factory=ImportProgressState)
    history: list[dict[str, object]] = field(default_factory=list)

    def _now(self) -> float:
        return float(self.clock())

    def _publish(self, *, emit_log: bool = True) -> None:
        snapshot = self.state.snapshot(self._now())
        self.history.append(snapshot)
        if emit_log and self.logger is not None:
            item = self.state.current_item or "-"
            current = (
                f"{self.state.current_index}/{self.state.current_total}"
                if self.state.current_index is not None and self.state.current_total is not None
                else "-"
            )
            self.logger(
                "[UnityPackage Importer] "
                f"stage={self.state.stage} current={current} item={item} "
                f"status={self.state.status}"
            )
        if self.sink is not None:
            self.sink.update(self.state)

    def start(self) -> "ImportProgressMonitor":
        now = self._now()
        self.state = ImportProgressState(
            stage=ImportProgressStage.READING_PACKAGE,
            stage_index=_STAGE_INDEX[ImportProgressStage.READING_PACKAGE],
            started_at=now,
            last_activity_at=now,
            message=_STAGE_LABELS[ImportProgressStage.READING_PACKAGE],
            status=ImportProgressStatus.WORKING,
        )
        self._publish()
        return self

    def set_stage(
        self,
        stage: str,
        *,
        message: str | None = None,
        current_item: str | None = None,
        current_index: int | None = None,
        current_total: int | None = None,
        blocking_operation: bool = False,
    ) -> None:
        if stage not in _STAGE_INDEX:
            raise ValueError(f"Unknown progress stage: {stage}")
        now = self._now()
        self.state.stage = stage
        self.state.stage_index = _STAGE_INDEX[stage]
        self.state.message = message or _STAGE_LABELS[stage]
        if current_item is not None:
            self.state.current_item = current_item
        if current_index is not None or current_total is not None:
            self.state.current_index = current_index
            self.state.current_total = current_total
        self.state.blocking_operation = blocking_operation
        self.state.last_activity_at = now
        self._publish()

    def heartbeat(self, *, message: str | None = None) -> None:
        self.state.last_activity_at = self._now()
        if message is not None:
            self.state.message = message
        # The UI sink and diagnostic history still receive the heartbeat, but
        # a one-line console log for every timer tick would obscure real phase
        # transitions during long imports.
        self._publish(emit_log=False)

    def complete(self, message: str = "Import complete") -> None:
        now = self._now()
        self.state.stage = ImportProgressStage.COMPLETE
        self.state.stage_index = self.state.stage_count
        self.state.status = ImportProgressStatus.COMPLETE
        self.state.message = message
        self.state.blocking_operation = False
        self.state.ended_at = now
        self.state.last_activity_at = now
        self._publish()
        if self.sink is not None:
            self.sink.clear()

    def fail(self, reason: str) -> None:
        now = self._now()
        self.state.stage = ImportProgressStage.FAILED
        self.state.stage_index = 0
        self.state.status = ImportProgressStatus.FAILED
        self.state.failure_message = str(reason)
        self.state.message = str(reason)
        self.state.blocking_operation = False
        self.state.ended_at = now
        self.state.last_activity_at = now
        self._publish()
        if self.sink is not None:
            self.sink.clear()

    def child(self, label: str) -> "ImportProgressChild":
        return ImportProgressChild(self, label)


class ImportProgressChild:
    """A grouped child view that can update the parent without closing it."""

    def __init__(self, parent: ImportProgressMonitor, label: str):
        self.parent = parent
        self.label = label

    @property
    def state(self) -> ImportProgressState:
        return self.parent.state

    def set_stage(self, stage: str, **kwargs) -> None:
        kwargs.setdefault("current_item", self.label)
        self.parent.set_stage(stage, **kwargs)

    def heartbeat(self, **kwargs) -> None:
        self.parent.heartbeat(**kwargs)

    def close(self) -> None:
        self.parent.heartbeat(message=f"Finished {self.label}")
