from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .analysis import analyze_observation
from .index import build_sqlite_index
from .ingest import ingest_raw
from .model import adapt_observation, InputInvalid
from .report import write_reports


def _input(path: Path) -> Path:
    if path.is_file(): return path
    candidates = sorted(list(path.rglob("observation.json")) + list(path.rglob("unity-semantic-oracle.json")))
    if not candidates: raise InputInvalid(f"INPUT_INVALID: no observation JSON under {path}")
    return candidates[0]


def _canonical(path: Path, vault: Path) -> dict:
    selected = _input(path)
    record = ingest_raw(selected, vault)
    sealed = Path(record["vaultPath"])
    raw_bytes = sealed.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8"))
    return adapt_observation(raw, raw_sha256=record["rawSha256"], source_label=str(selected.name))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vapb_oracle_analysis")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest"); ingest.add_argument("input", type=Path); ingest.add_argument("--vault", type=Path, required=True)
    for name in ("validate", "analyze", "report"):
        p = sub.add_parser(name); p.add_argument("input", type=Path); p.add_argument("--vault", type=Path, required=True); p.add_argument("--output", type=Path, required=(name in {"analyze", "report"})); p.add_argument("--strict", action="store_true"); p.add_argument("--public-only", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "ingest":
        print(json.dumps(ingest_raw(args.input, args.vault), sort_keys=True)); return 0
    canonical = _canonical(args.input, args.vault)
    if args.command == "validate":
        print(json.dumps({"valid": True, "canonicalVersion": canonical["canonicalVersion"]})); return 0
    result = analyze_observation(canonical)
    if args.command == "analyze":
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return 0
    paths = write_reports(result, args.output, include_private=not args.public_only)
    build_sqlite_index(canonical, args.output / "index.sqlite")
    print(json.dumps({key: str(value) for key, value in paths.items()}, sort_keys=True)); return 0
