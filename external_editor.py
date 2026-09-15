"""Best-effort Windows editor discovery and safe texture launching."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Iterable


EDITOR_NOT_FOUND = "EDITOR_NOT_FOUND"
EDITOR_LAUNCH_FAILED = "EDITOR_LAUNCH_FAILED"
LAUNCH_OK = "OK"

KNOWN_EDITORS = (
    ("Krita", ("krita.exe",)),
    ("Adobe Photoshop", ("Photoshop.exe",)),
    ("CLIP STUDIO PAINT", ("CLIPStudioPaint.exe",)),
    ("GIMP", ("gimp.exe", "gimp-3.exe")),
    ("paint.net", ("paintdotnet.exe", "PaintDotNet.exe")),
    ("Paint", ("mspaint.exe",)),
)


def _registry_paths() -> dict[str, list[Path]]:
    """Read only App Paths entries; registry access is intentionally narrow."""
    result: dict[str, list[Path]] = {}
    try:
        import winreg
    except ImportError:
        return result
    roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    subkeys = (
        r"Software\Microsoft\Windows\CurrentVersion\App Paths\{}",
        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{}",
    )
    for display_name, executable_names in KNOWN_EDITORS:
        paths: list[Path] = []
        for executable_name in executable_names:
            for root in roots:
                for template in subkeys:
                    try:
                        with winreg.OpenKey(root, template.format(executable_name)) as key:
                            value, _ = winreg.QueryValueEx(key, None)
                        if value:
                            paths.append(Path(os.path.expandvars(str(value))))
                    except (OSError, FileNotFoundError):
                        continue
        result[display_name] = paths
    return result


def _common_paths() -> dict[str, list[Path]]:
    roots = [Path(value) for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")) if value]
    paths: dict[str, list[Path]] = {name: [] for name, _ in KNOWN_EDITORS}
    for root in roots:
        paths["Krita"].extend((root / "Krita (x64)" / "bin" / "krita.exe", root / "Krita" / "bin" / "krita.exe"))
        paths["GIMP"].extend((root / "GIMP 3" / "bin" / "gimp-3.exe", root / "GIMP 2" / "bin" / "gimp.exe"))
        paths["paint.net"].append(root / "paint.net" / "PaintDotNet.exe")
        paths["CLIP STUDIO PAINT"].append(root / "CELSYS" / "CLIP STUDIO 1.5" / "CLIP STUDIO PAINT" / "CLIPStudioPaint.exe")
    if os.environ.get("WINDIR"):
        paths["Paint"].append(Path(os.environ["WINDIR"]) / "System32" / "mspaint.exe")
    return paths


def _candidate(path: str | os.PathLike[str], name: str) -> dict[str, str] | None:
    resolved = Path(path).expanduser()
    if not resolved.is_file():
        return None
    return {"name": name, "path": str(resolved.resolve())}


def discover_editors(
    *,
    which: Callable[[str], str | None] | None = None,
    registry_paths: dict[str, Iterable[Path]] | None = None,
    common_paths: dict[str, Iterable[Path]] | None = None,
) -> list[dict[str, str]]:
    """Return known installed editors without recursive filesystem scanning."""
    which = which or shutil.which
    registry_paths = registry_paths if registry_paths is not None else _registry_paths()
    common_paths = common_paths if common_paths is not None else _common_paths()
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, executable_names in KNOWN_EDITORS:
        paths: list[Path] = []
        for executable_name in executable_names:
            located = which(executable_name)
            if located:
                paths.append(Path(located))
        paths.extend(Path(path) for path in registry_paths.get(name, ()))
        paths.extend(Path(path) for path in common_paths.get(name, ()))
        for path in paths:
            item = _candidate(path, name)
            if item and item["path"].casefold() not in seen:
                seen.add(item["path"].casefold())
                found.append(item)
                break
    return found


def validate_editor_path(path: str | os.PathLike[str]) -> Path | None:
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_file() else None


def launch_editor(editor_path: str | os.PathLike[str], texture_path: str | os.PathLike[str], *, popen=None) -> str:
    """Launch one existing executable with one existing texture argument."""
    editor = validate_editor_path(editor_path)
    texture = Path(texture_path).expanduser()
    if editor is None:
        return EDITOR_NOT_FOUND
    if not texture.is_file():
        return "MISSING_SOURCE"
    process_factory = popen or subprocess.Popen
    try:
        process_factory([str(editor), str(texture.resolve())], shell=False)
    except OSError:
        return EDITOR_LAUNCH_FAILED
    return LAUNCH_OK
