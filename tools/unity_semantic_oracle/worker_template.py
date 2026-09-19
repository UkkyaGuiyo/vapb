"""Prepare and verify a fresh public Oracle worker template.

This tool never launches Unity. It only materializes authored files and emits
an external manifest that a human-started Supervisor/Worker can verify.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import re
from pathlib import Path


UNITY_VERSION = "2022.3.62f3"
EXCLUDED = {"Library", "Temp", "Obj", "Logs", "UserSettings"}
FORBIDDEN_PAYLOAD_SUFFIXES = {".unitypackage", ".zip", ".blend"}


def _files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(root).parts):
            continue
        yield path


def _content_errors(root: Path) -> list[str]:
    errors = []
    for path in _files(root):
        if path.suffix.lower() in FORBIDDEN_PAYLOAD_SUFFIXES:
            errors.append(f"TEMPLATE_FORBIDDEN_PAYLOAD:{path.relative_to(root).as_posix()}")
    return errors


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unity_version(template_root: Path) -> str | None:
    version_file = template_root / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.is_file(): return None
    match = re.search(r"^m_EditorVersion:\s*(\S+)", version_file.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def template_manifest(template_root: Path, template_id: str = "vapb-worker-template-v1") -> dict:
    files = [{"path": path.relative_to(template_root).as_posix(), "sha256": _sha(path), "size": path.stat().st_size} for path in _files(template_root)]
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"schemaVersion": "1", "templateId": template_id, "unityVersion": _unity_version(template_root), "files": files, "templateHash": hashlib.sha256(canonical).hexdigest()}


def prepare(source_root: Path, destination: Path, manifest_path: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"TEMPLATE_DESTINATION_EXISTS:{destination}")
    if _unity_version(source_root) != UNITY_VERSION:
        raise ValueError("TEMPLATE_UNITY_VERSION_MISMATCH")
    content_errors = _content_errors(source_root)
    if content_errors:
        raise ValueError(";".join(content_errors))
    destination.parent.mkdir(parents=True, exist_ok=True)
    def ignore(directory: str, names: list[str]):
        return {name for name in names if name in EXCLUDED}
    shutil.copytree(source_root, destination, ignore=ignore)
    manifest = template_manifest(destination)
    if manifest["unityVersion"] != UNITY_VERSION:
        raise ValueError("TEMPLATE_UNITY_VERSION_MISMATCH")
    if any((destination / excluded).exists() for excluded in EXCLUDED):
        raise ValueError("TEMPLATE_CACHE_DIRECTORY_PRESENT")
    content_errors = _content_errors(destination)
    if content_errors:
        raise ValueError(";".join(content_errors))
    if manifest_path.exists():
        raise FileExistsError(f"TEMPLATE_MANIFEST_EXISTS:{manifest_path}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def check(template_root: Path, manifest_path: Path) -> list[str]:
    if not template_root.is_dir() or not manifest_path.is_file():
        return ["TEMPLATE_MISSING"]
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ["TEMPLATE_MANIFEST_MALFORMED"]
    if not isinstance(expected, dict):
        return ["TEMPLATE_MANIFEST_NOT_OBJECT"]
    if not isinstance(expected.get("templateId"), str) or not expected.get("templateId"):
        return ["TEMPLATE_ID_MISSING"]
    actual = template_manifest(template_root, expected.get("templateId", ""))
    errors = []
    if any((template_root / excluded).exists() for excluded in EXCLUDED):
        errors.append("TEMPLATE_CACHE_DIRECTORY_PRESENT")
    errors.extend(_content_errors(template_root))
    for key in ("schemaVersion", "templateId", "unityVersion", "templateHash"):
        if expected.get(key) != actual.get(key):
            errors.append(f"TEMPLATE_{key.upper()}_MISMATCH")
    if actual.get("unityVersion") != UNITY_VERSION:
        errors.append("TEMPLATE_UNITY_VERSION_MISMATCH")
    if expected.get("files") != actual.get("files"):
        errors.append("TEMPLATE_FILES_MISMATCH")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("source", type=Path)
    prepare_parser.add_argument("destination", type=Path)
    prepare_parser.add_argument("manifest", type=Path)
    check_parser = sub.add_parser("check")
    check_parser.add_argument("template", type=Path)
    check_parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.source, args.destination, args.manifest), indent=2))
        return 0
    errors = check(args.template, args.manifest)
    print(json.dumps({"valid": not errors, "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
