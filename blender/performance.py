"""Low-overhead phase timing for UnityPackage imports."""

from __future__ import annotations

from collections.abc import Callable
import json
from threading import Lock
from time import perf_counter
from typing import Any, TypeVar


T = TypeVar("T")

PHASE_ORDER = (
    "package_identity",
    "package_open",
    "archive_scan",
    "extract",
    "extract_sequential",
    "asset_database",
    "meta_scan",
    "fbx_scan",
    "prefab_scan",
    "prefab_parse",
    "prefab_candidate_analysis",
    "prefab_candidate_analysis_parse",
    "sibling_discovery",
    "selected_dependency_collection",
    "apply_import_options",
    "dependency_resolution",
    "registry_write",
    "fbx_import",
    "material_parse",
    "material_build",
    "texture_load",
    "material_mapping",
    "prefab_reconstruct",
    "total",
)

_DIAGNOSTIC_LOCK = Lock()
_DIAGNOSTIC_STATS: dict[str, int] = {}


def reset_diagnostic_stats() -> None:
    with _DIAGNOSTIC_LOCK:
        _DIAGNOSTIC_STATS.clear()


def diagnostic_add(name: str, value: int = 1) -> None:
    with _DIAGNOSTIC_LOCK:
        _DIAGNOSTIC_STATS[name] = _DIAGNOSTIC_STATS.get(name, 0) + int(value)


def diagnostic_snapshot() -> dict[str, int]:
    with _DIAGNOSTIC_LOCK:
        return dict(_DIAGNOSTIC_STATS)


class PerformanceTimer:
    """Accumulate named phase timings without collecting per-file telemetry."""

    def __init__(self) -> None:
        self._started = perf_counter()
        self.timings: dict[str, float] = {}
        self.diagnostics: dict[str, int] = {}

    def add(self, phase: str, seconds: float) -> None:
        self.timings[phase] = self.timings.get(phase, 0.0) + max(0.0, seconds)

    def measure(self, phase: str, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        started = perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            self.add(phase, perf_counter() - started)

    def finish(self) -> None:
        if "total" not in self.timings:
            self.timings["total"] = perf_counter() - self._started

    def emit(self, print_function: Callable[[str], None] = print) -> None:
        for phase in PHASE_ORDER:
            seconds = self.timings.get(phase)
            if seconds is None:
                print_function(f"[PERF] {phase}: UNKNOWN")
            else:
                print_function(f"[PERF] {phase}: {seconds:.3f}s")
        self.diagnostics = diagnostic_snapshot()
        print_function("[PERF] diagnostics: " + json.dumps(self.diagnostics, sort_keys=True))
