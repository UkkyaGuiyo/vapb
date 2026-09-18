"""Private, metadata-first shader/material survey entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .material_inventory import public_safe_summary, scan_material_corpus
from .behavior_ir import classify_material_schema


def validate_output_root(output_root: Path) -> Path:
    resolved = Path(output_root).resolve()
    repository_root = Path(__file__).resolve().parents[2]
    try:
        resolved.relative_to(repository_root)
    except ValueError:
        return resolved
    raise ValueError("private shader survey output must be outside the repository")


def write_outputs(root: Path, output_root: Path) -> dict:
    result = scan_material_corpus(root)
    destination = validate_output_root(output_root)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "SHADER_INDEX.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (destination / "PUBLIC_SAFE_SUMMARY.json").write_text(json.dumps(public_safe_summary(result), indent=2, ensure_ascii=False), encoding="utf-8")
    ir = [classify_material_schema(item) for item in result["materials"]]
    (destination / "SHADER_PREVIEW_IR.json").write_text(json.dumps(ir, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = write_outputs(args.root, args.output_root)
    print(json.dumps({"materials": result["material_count"], "unique_shaders": result["unique_shader_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
