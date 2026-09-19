"""Synchronize the authored Unity Oracle Editor sources to a dedicated project.

Only the managed VAPB Editor directory and C# files are touched. Unity is not
started by this command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


MANAGED_RELATIVE = ("HumanOracleRunnerWindow.cs", "SemanticOracle.cs", "SyntheticFixture.cs")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def synchronize(repo_root: Path, project_root: Path, *, check: bool = False) -> dict:
    canonical = repo_root / "tools" / "unity_semantic_oracle" / "Assets" / "Editor"
    deployed = project_root / "Assets" / "Editor" / "VAPB"
    records = []
    for relative in MANAGED_RELATIVE:
        source = canonical / relative
        target = deployed / relative
        if not source.is_file():
            raise FileNotFoundError(f"managed canonical source missing: {source}")
        before = sha256(target) if target.is_file() else None
        if not check and before != sha256(source):
            deployed.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=deployed, prefix=f".{relative}.", delete=False) as temporary:
                temporary_path = Path(temporary.name)
            try:
                shutil.copyfile(source, temporary_path)
                os.replace(temporary_path, target)
            finally:
                if temporary_path.exists(): temporary_path.unlink()
        after = sha256(target) if target.is_file() else None
        records.append({"file": relative, "canonicalSha256": sha256(source), "deployedSha256Before": before, "deployedSha256After": after, "equal": after == sha256(source)})
    result = {"canonicalRoot": str(canonical), "deployedRoot": str(deployed), "checkOnly": check, "managedFiles": records, "verified": all(item["equal"] for item in records)}
    if not result["verified"]:
        raise RuntimeError(json.dumps(result, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync managed VAPB Unity Oracle Editor sources")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true", help="verify only; do not copy")
    args = parser.parse_args(argv)
    print(json.dumps(synchronize(args.repo_root.resolve(), args.project_root.resolve(), check=args.check), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
