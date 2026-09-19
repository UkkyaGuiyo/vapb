"""Safely restore the authored Assets surface of the dedicated Oracle project."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from .baseline_manifest import verify
    from .sync_unity_oracle_project import MANAGED_RELATIVE
except ImportError:  # direct script execution from the repository root
    from baseline_manifest import verify
    from sync_unity_oracle_project import MANAGED_RELATIVE


ORACLE_ASSETS = Path("Assets")
PROTECTED_DIR = Path("Assets/Editor/VAPB")
INFRASTRUCTURE = (Path("Packages"), Path("ProjectSettings"))


@dataclass(frozen=True)
class CleanupPlan:
    project_root: Path
    protected_files: tuple[Path, ...]
    unexpected_files: tuple[Path, ...]
    unexpected_directories: tuple[Path, ...]
    reparse_points: tuple[Path, ...]

    @property
    def unexpected_count(self) -> int:
        return len(self.unexpected_files) + len(self.unexpected_directories)

    def as_dict(self) -> dict:
        return {
            "projectRoot": str(self.project_root),
            "protectedFiles": [p.as_posix() for p in self.protected_files],
            "unexpectedFiles": [p.as_posix() for p in self.unexpected_files],
            "unexpectedDirectories": [p.as_posix() for p in self.unexpected_directories],
            "reparsePoints": [p.as_posix() for p in self.reparse_points],
            "unexpectedCount": self.unexpected_count,
        }


def _resolve_under(root: Path, relative: Path) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"PATH_ESCAPE: {relative}") from exc
    return candidate


def _reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.stat().st_file_attributes & 0x400)
    except (AttributeError, OSError):
        return False


def _protected_files(repo_root: Path, project_root: Path) -> set[Path]:
    canonical = repo_root / "tools" / "unity_semantic_oracle" / "Assets" / "Editor"
    protected = {_resolve_under(project_root, PROTECTED_DIR / name) for name in MANAGED_RELATIVE}
    for relative in tuple(PROTECTED_DIR / name for name in MANAGED_RELATIVE):
        protected.add(_resolve_under(project_root, Path(str(relative) + ".meta")))
    for parent in (Path("Assets"), Path("Assets/Editor"), PROTECTED_DIR):
        protected.add(_resolve_under(project_root, Path(str(parent) + ".meta")))
    for relative in MANAGED_RELATIVE:
        if not (canonical / relative).is_file():
            raise FileNotFoundError(f"managed canonical source missing: {canonical / relative}")
    return protected


def build_cleanup_plan(project_root: Path, repo_root: Path) -> CleanupPlan:
    root = project_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    protected = _protected_files(repo_root.resolve(), root)
    unexpected_files: list[Path] = []
    unexpected_directories: list[Path] = []
    reparse_points: list[Path] = []
    assets = _resolve_under(root, ORACLE_ASSETS)
    if not assets.is_dir():
        raise FileNotFoundError(assets)
    for current, directories, files in os.walk(assets, topdown=True, followlinks=False):
        current_path = Path(current).resolve()
        for name in list(directories):
            path = current_path / name
            if _reparse(path):
                reparse_points.append(path.relative_to(root))
                directories.remove(name)
                continue
            if not any(candidate == path.resolve() or candidate.is_relative_to(path.resolve()) for candidate in protected):
                unexpected_directories.append(path.relative_to(root))
        for name in files:
            path = current_path / name
            if _reparse(path):
                reparse_points.append(path.relative_to(root))
            elif path.resolve() not in protected:
                unexpected_files.append(path.relative_to(root))
    return CleanupPlan(root, tuple(sorted(p.relative_to(root) for p in protected if p.exists())), tuple(sorted(unexpected_files)), tuple(sorted(unexpected_directories)), tuple(sorted(reparse_points)))


def active_unity_use(project_root: Path) -> str:
    """Return NO, YES, or UNKNOWN without launching or controlling Unity."""
    if os.name != "nt":
        return "NO"
    script = "Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | ForEach-Object { $_.CommandLine }"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "NO"
    root_text = str(project_root.resolve()).lower()
    return "YES" if any(root_text in line.lower() for line in lines) else "UNKNOWN"


def apply_cleanup(plan: CleanupPlan) -> None:
    if plan.reparse_points:
        raise RuntimeError("CLEANUP_BLOCKED_REPARSE_POINT: " + ", ".join(p.as_posix() for p in plan.reparse_points))
    status = active_unity_use(plan.project_root)
    if status != "NO":
        raise RuntimeError(f"UNITY_PROJECT_ACTIVE_{status}: close Unity before applying cleanup")
    for relative in sorted(plan.unexpected_files, key=lambda p: (len(p.parts), p.as_posix()), reverse=True):
        target = _resolve_under(plan.project_root, relative)
        if target.exists() or target.is_symlink(): target.unlink()
    for relative in sorted(plan.unexpected_directories, key=lambda p: (len(p.parts), p.as_posix()), reverse=True):
        target = _resolve_under(plan.project_root, relative)
        if target.exists(): shutil.rmtree(target)


def check_clean(plan: CleanupPlan, baseline: dict | None = None) -> list[str]:
    errors = []
    if plan.reparse_points: errors.append("BASELINE_DIRTY: reparse points under Assets")
    if plan.unexpected_count: errors.append("BASELINE_DIRTY: unexpected non-Oracle Assets detected")
    if baseline is not None: errors.extend(verify(plan.project_root, baseline))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--baseline-manifest", type=Path)
    args = parser.parse_args(argv)
    plan = build_cleanup_plan(args.project_root, args.repo_root)
    if args.apply: apply_cleanup(plan)
    baseline = json.loads(args.baseline_manifest.read_text(encoding="utf-8")) if args.baseline_manifest else None
    errors = check_clean(build_cleanup_plan(args.project_root, args.repo_root), baseline) if args.apply else check_clean(plan, baseline)
    print(json.dumps({"mode": "apply" if args.apply else "dry-run" if args.dry_run else "check", "plan": plan.as_dict(), "errors": errors, "clean": not errors}, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if args.check and errors else 0


if __name__ == "__main__": raise SystemExit(main())
