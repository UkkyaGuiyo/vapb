"""Deterministic local package planning; no package payload is opened."""

from __future__ import annotations

import ntpath
from pathlib import Path


def canonical_package_key(path: str | Path) -> str:
    """Return a Windows-stable key without stripping extensions or basenames."""
    raw = str(path).replace("/", "\\")
    if not ntpath.isabs(raw):
        raw = ntpath.abspath(raw)
    drive, tail = ntpath.splitdrive(raw)
    normalized = ntpath.normpath(ntpath.join(drive, tail))
    return ntpath.normcase(normalized)


def discover_packages(root: str | Path) -> list[Path]:
    root_path = Path(root)
    found = [path for path in root_path.rglob("*")
             if path.is_file() and path.suffix.casefold() == ".unitypackage"]
    return sorted(found, key=lambda path: canonical_package_key(path))
