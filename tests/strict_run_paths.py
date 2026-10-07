"""Fail-closed path validation for the strict Blender evidence runner."""

import os
from pathlib import Path
from typing import Mapping


def _canonical(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def validate_run_paths(inputs: Mapping[str, Path], outputs: Mapping[str, Path]) -> None:
    """Reject output aliases and existing output files before the runner reads inputs."""
    input_paths = {_canonical(path): name for name, path in inputs.items()}
    seen_outputs = {}
    for name, path in outputs.items():
        canonical = _canonical(path)
        if canonical in input_paths:
            raise ValueError(f"output {name!r} aliases protected input {input_paths[canonical]!r}")
        if canonical in seen_outputs:
            raise ValueError(f"output paths alias: {seen_outputs[canonical]!r} and {name!r}")
        if path.exists():
            raise FileExistsError(f"output already exists: {name} ({path})")
        seen_outputs[canonical] = name


def validate_strict_runner_paths(package: Path, oracle: Path, witness: Path,
                                 result: Path, blend: Path, t0b_report: Path) -> None:
    """Validate all user paths and derived T0-B files before the runner reads anything."""
    validate_run_paths(
        {"package": package, "native oracle": oracle, "model witness": witness},
        {"T0-A report": result, "saved blend": blend, "T0-B report": t0b_report,
         "export package": t0b_report.with_suffix(".unitypackage")},
    )


def write_json_exclusive(path: Path, contents: str) -> None:
    """Create a UTF-8 evidence file without replacing an existing file."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(contents)
