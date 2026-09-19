"""Create/verify a small authored-state baseline for a disposable Unity project."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXCLUDED = {"Library", "Temp", "Obj", "Logs", "UserSettings"}


def _files(project_root: Path, exclude_paths: set[Path] | None = None):
    excluded = {path.resolve() for path in (exclude_paths or set())}
    for path in sorted(project_root.rglob("*")):
        if not path.is_file(): continue
        relative = path.relative_to(project_root)
        if any(part in EXCLUDED for part in relative.parts): continue
        if path.resolve() in excluded: continue
        yield relative


def manifest(project_root: Path, exclude_paths: set[Path] | None = None) -> dict:
    entries = []
    for relative in _files(project_root, exclude_paths):
        digest = hashlib.sha256((project_root / relative).read_bytes()).hexdigest()
        entries.append({"path": relative.as_posix(), "sha256": digest, "bytes": (project_root / relative).stat().st_size})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"manifestVersion": "1", "projectRootLabel": "private-local", "baselineHash": hashlib.sha256(payload).hexdigest(), "files": entries}


def verify(project_root: Path, expected: dict) -> list[str]:
    actual = manifest(project_root)
    errors = []
    if actual["baselineHash"] != expected.get("baselineHash"):
        errors.append("BASELINE_DRIFT: manifest hash differs")
    expected_files = {item["path"]: item for item in expected.get("files", [])}
    actual_files = {item["path"]: item for item in actual["files"]}
    for path in sorted(set(expected_files) - set(actual_files)): errors.append(f"BASELINE_MISSING: {path}")
    for path in sorted(set(actual_files) - set(expected_files)): errors.append(f"BASELINE_ADDED: {path}")
    for path in sorted(set(expected_files) & set(actual_files)):
        if expected_files[path]["sha256"] != actual_files[path]["sha256"]: errors.append(f"BASELINE_CHANGED: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create"); create.add_argument("project_root", type=Path); create.add_argument("output", type=Path)
    check = sub.add_parser("verify"); check.add_argument("project_root", type=Path); check.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    if args.command == "create":
        project_root = args.project_root.resolve()
        output = args.output.resolve()
        try:
            output.relative_to(project_root)
        except ValueError:
            pass
        else:
            raise SystemExit("BASELINE_OUTPUT_MUST_BE_EXTERNAL_TO_PROJECT")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest(project_root), indent=2, sort_keys=True), encoding="utf-8")
        return 0
    errors = verify(args.project_root.resolve(), json.loads(args.manifest.read_text(encoding="utf-8")))
    if errors:
        for error in errors: print(error)
        return 1
    print("BASELINE_OK")
    return 0


if __name__ == "__main__": raise SystemExit(main())
