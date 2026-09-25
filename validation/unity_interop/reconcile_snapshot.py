"""Offline skeleton for comparing canonical Full Semantic Snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    files = sorted(args.snapshot.rglob("*.json")) + sorted(args.snapshot.rglob("*.jsonl"))
    parsed = []
    for path in files:
        if path.suffix == ".jsonl":
            parsed.append((str(path), [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]))
        else:
            parsed.append((str(path), load_json(path)))
    print(json.dumps({"manifest_schema": manifest.get("schema"), "snapshot": str(args.snapshot), "parsed_files": len(parsed), "files": [name for name, _ in parsed]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
