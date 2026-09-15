"""Low-overhead phase timing for UnityPackage imports."""

from __future__ import annotations

from collections.abc import Callable
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
    "fbx_import",
    "material_parse",
    "material_build",
    "texture_load",
    "material_mapping",
    "prefab_reconstruct",
    "total",
)


class PerformanceTimer:
    """Accumulate named phase timings without collecting per-file telemetry."""

    def __init__(self) -> None:
        self._started = perf_counter()
        self.timings: dict[str, float] = {}

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
