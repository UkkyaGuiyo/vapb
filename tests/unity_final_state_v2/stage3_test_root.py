"""Resolve only explicitly marked disposable Stage 3 Unity test roots."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
from typing import Union

ROOT_MARKER = ".vapb-stage3-owned-test-root"
ROOT_MARKER_VALUE = "VAPB_STAGE3_OWNED_TEST_ROOT_V1"
SOURCE_MARKER = ".vapb-stage3-owned-source-project"
SOURCE_MARKER_VALUE = "VAPB_STAGE3_OWNED_SOURCE_PROJECT_V1"
TARGET_MARKER = ".vapb-disposable-unity-test-project"
PathLike = Union[str, Path]


@dataclass(frozen=True)
class Stage3TestRoot:
    root: Path
    source_project: Path
    target_project: Path


def _read_marker(path: Path, expected: str | None = None) -> None:
    if not path.is_file():
        raise ValueError("required disposable-project marker is missing: " + path.name)
    if expected is not None:
        try:
            actual = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError("could not read disposable-project marker: " + path.name) from exc
        if actual != expected:
            raise ValueError("disposable-project marker has an unexpected value: " + path.name)


def _direct_child(root: Path, name: str) -> Path:
    candidate = root / name
    assert_owned_path(candidate, root)
    try:
        child = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("required project directory is missing: " + name) from exc
    if not child.is_dir() or child.parent != root:
        raise ValueError("project must be a direct child of the owned test root: " + name)
    assert_owned_path(child, root)
    return child


def _reject_reparse_components(components: tuple[Path, ...]) -> None:
    for component in components:
        try:
            info = os.lstat(component)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ValueError("could not inspect owned test path: " + component.name) from exc
        attrs = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError("reparse point is not allowed in an owned test path: " + component.name)


def assert_path_has_no_reparse_ancestors(path: PathLike) -> Path:
    """Reject reparse points anywhere in an explicitly supplied path."""
    absolute = Path(path).expanduser().absolute()
    _reject_reparse_components(tuple(reversed((absolute, *absolute.parents))))
    return absolute


def assert_owned_path(path: PathLike, boundary: Path) -> Path:
    """Reject symlinks/junctions between an owned boundary and a used path."""
    path = Path(path).absolute()
    boundary = boundary.resolve(strict=True)
    try:
        relative = path.relative_to(boundary)
    except ValueError as exc:
        raise ValueError("path escapes the owned test root") from exc
    if ".." in relative.parts:
        raise ValueError("path escapes the owned test root")
    prefixes = (boundary.joinpath(*relative.parts[:i]) for i in range(1, len(relative.parts) + 1))
    _reject_reparse_components((boundary, *prefixes))
    return path


def resolve_stage3_test_root(value: PathLike | None) -> Stage3TestRoot:
    """Resolve and validate an existing marked root; never create or clean projects."""
    if value is None or not str(value).strip():
        raise ValueError("an explicit Stage 3 test root is required")
    try:
        raw_root = assert_path_has_no_reparse_ancestors(value)
        root = raw_root.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Stage 3 test root does not exist") from exc
    if not root.is_dir():
        raise ValueError("Stage 3 test root must be a directory")
    if (root / ".git").exists():
        raise ValueError("a Git checkout cannot be used as the disposable test root")
    for ancestor in root.parents:
        if (ancestor / ".git").exists():
            raise ValueError("a test root inside a Git checkout cannot be used")
    assert_owned_path(root, root)
    assert_owned_path(root / ROOT_MARKER, root)
    _read_marker(root / ROOT_MARKER, ROOT_MARKER_VALUE)

    source = _direct_child(root, "SourceProject")
    target = _direct_child(root, "TargetProject")
    assert_owned_path(source / SOURCE_MARKER, root)
    assert_owned_path(target / TARGET_MARKER, root)
    _read_marker(source / SOURCE_MARKER, SOURCE_MARKER_VALUE)
    _read_marker(target / TARGET_MARKER)
    assert_owned_path(source / "Assets", root)
    assert_owned_path(target / "Assets", root)
    return Stage3TestRoot(root=root, source_project=source, target_project=target)
