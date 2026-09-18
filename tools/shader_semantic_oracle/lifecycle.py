"""Durable, public-observation state model for Unity import/probe sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ImportState(str, Enum):
    NEW = "NEW"
    IMPORT_REQUESTED = "IMPORT_REQUESTED"
    CALLBACK_RECEIVED = "IMPORT_CALLBACK_RECEIVED"
    ASSETS_OBSERVED = "ASSETS_OBSERVED"
    COMPILATION_PENDING = "COMPILATION_PENDING"
    IMPORT_STABLE = "IMPORT_STABLE"
    PROBE_STARTED = "PROBE_STARTED"
    PROBE_COMPLETE = "PROBE_COMPLETE"
    FAILED = "FAILED"


class FailureCategory(str, Enum):
    IMPORT_PROCESS_TIMEOUT = "IMPORT_PROCESS_TIMEOUT"
    IMPORT_CALLBACK_TIMEOUT = "IMPORT_CALLBACK_TIMEOUT"
    ASSET_DISCOVERY_TIMEOUT = "ASSET_DISCOVERY_TIMEOUT"
    COMPILATION_TIMEOUT = "COMPILATION_TIMEOUT"
    EDITOR_STABILIZATION_TIMEOUT = "EDITOR_STABILIZATION_TIMEOUT"
    PROBE_TIMEOUT = "PROBE_TIMEOUT"


@dataclass
class LifecycleState:
    package: str
    minimum_assets: int
    status: ImportState = ImportState.NEW
    classification: str | None = None
    failure_category: FailureCategory | None = None
    callback_received: bool = False
    assets_observed: int = 0
    stable_frames: int = 0
    compiling: bool = False
    events: list[dict] = field(default_factory=list)

    @classmethod
    def new(cls, package: str, minimum_assets: int) -> "LifecycleState":
        return cls(package, minimum_assets)

    def _event(self, name: str, **details) -> None:
        self.events.append({"at": datetime.now(timezone.utc).isoformat(), "event": name, **details})

    def transition(self, status: ImportState, event: str) -> "LifecycleState":
        self.status = status
        self._event(event, status=status.value)
        return self

    def fail(self, category: FailureCategory) -> "LifecycleState":
        self.failure_category = category
        self.status = ImportState.FAILED
        self._event("failure", category=category.value)
        return self

    def to_json(self) -> str:
        return json.dumps({
            "package": self.package,
            "minimum_assets": self.minimum_assets,
            "status": self.status.value,
            "classification": self.classification,
            "failure_category": self.failure_category.value if self.failure_category else None,
            "callback_received": self.callback_received,
            "assets_observed": self.assets_observed,
            "stable_frames": self.stable_frames,
            "compiling": self.compiling,
            "events": self.events,
        }, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "LifecycleState":
        data = json.loads(text)
        state = cls(data["package"], int(data["minimum_assets"]), ImportState(data["status"]))
        state.classification = data.get("classification")
        state.failure_category = FailureCategory(data["failure_category"]) if data.get("failure_category") else None
        state.callback_received = bool(data.get("callback_received"))
        state.assets_observed = int(data.get("assets_observed", 0))
        state.stable_frames = int(data.get("stable_frames", 0))
        state.compiling = bool(data.get("compiling"))
        state.events = list(data.get("events", []))
        return state


def observe_import(state: LifecycleState, *, assets: int, stable_frames: int, compiling: bool, callback_received: bool) -> LifecycleState:
    state.assets_observed = assets
    state.stable_frames = stable_frames
    state.compiling = compiling
    state.callback_received = state.callback_received or callback_received
    if compiling:
        state.status = ImportState.COMPILATION_PENDING
    elif assets < state.minimum_assets:
        state.status = ImportState.IMPORT_REQUESTED
    elif stable_frames < 3:
        state.status = ImportState.ASSETS_OBSERVED
    else:
        state.status = ImportState.IMPORT_STABLE
        state.classification = "CALLBACK_AND_ASSETS_STABLE" if state.callback_received else "IMPORT_CALLBACK_MISSING_BUT_ASSETS_PRESENT"
    state._event("observation", assets=assets, stable_frames=stable_frames, compiling=compiling, callback_received=callback_received, status=state.status.value)
    return state


def can_probe(state: LifecycleState) -> bool:
    return state.status == ImportState.IMPORT_STABLE and state.assets_observed >= state.minimum_assets and not state.compiling


def resume_action(state: LifecycleState) -> str:
    if state.status == ImportState.IMPORT_STABLE:
        return "probe"
    if state.status in {ImportState.IMPORT_REQUESTED, ImportState.ASSETS_OBSERVED, ImportState.COMPILATION_PENDING, ImportState.CALLBACK_RECEIVED}:
        return "observe"
    if state.status == ImportState.NEW:
        return "import"
    return "stop"
