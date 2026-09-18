"""Build private representative and fingerprint artifacts from an inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .behavior_fingerprint import aggregate_prevalence, fingerprint_from_metadata, schema_signature, select_representatives


def validate_output(root: Path) -> Path:
    root = root.resolve()
    repository = Path(__file__).resolve().parents[2]
    try:
        root.relative_to(repository)
    except ValueError:
        return root
    raise ValueError("behavior corpus output must be outside the repository")


def build(index_path: Path, output_root: Path, limit: int = 16) -> dict:
    inventory = json.loads(index_path.read_text(encoding="utf-8"))
    records = inventory["materials"]
    representatives = select_representatives(records, limit)
    fingerprints = [fingerprint_from_metadata(item) for item in representatives]
    result = {
        "schema_version": "0.1",
        "material_count": len(records),
        "unique_shader_identities": len({item.get("shader_guid") for item in records}),
        "unique_schema_signatures": len({schema_signature(item) for item in records}),
        "representative_count": len(representatives),
        "representatives": representatives,
        "fingerprints": fingerprints,
        "prevalence": aggregate_prevalence(fingerprints),
        "coverage_buckets": {
            "GENERIC_PROPERTY_PREVIEW": len([item for item in fingerprints if item["base_texture"]["state"] == "DETECTED" or item["base_color"]["state"] == "DETECTED"]),
            "GENERIC_BEHAVIOR_PREVIEW": len([item for item in fingerprints if item["normal"]["state"] == "DETECTED" or item["emission"]["state"] == "DETECTED"]),
            "PARTIAL_ONLY": len([item for item in fingerprints if any(value["state"] == "NOT_TESTED" for value in item.values())]),
        },
    }
    destination = validate_output(output_root)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "REPRESENTATIVES.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=16)
    args = parser.parse_args()
    result = build(args.index, args.output_root, args.limit)
    print(json.dumps({key: result[key] for key in ("material_count", "unique_shader_identities", "unique_schema_signatures", "representative_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
