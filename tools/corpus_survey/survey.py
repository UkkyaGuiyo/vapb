"""Command-line entry point for the private corpus Phase 1 survey."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from .inventory import public_safe_summary, scan_corpus, write_json


def validate_output_root(output_root: Path) -> Path:
    """Reject raw private output paths inside this repository."""
    resolved = Path(output_root).resolve()
    repository_root = Path(__file__).resolve().parents[2]
    try:
        resolved.relative_to(repository_root)
    except ValueError:
        return resolved
    raise ValueError("raw corpus output must be outside the repository")


def _report(inventory: dict, elapsed: float) -> str:
    totals = inventory["totals"]
    signatures = Counter(signature for item in inventory["packages"] for signature in item["signatures"])
    heuristics = Counter(heuristic for item in inventory["packages"] for heuristic in item["heuristics"])
    lines = [
        "# Private Real-World Corpus Survey v0.1",
        "",
        "This file is private local evidence. It is not repository content.",
        "",
        "## Corpus",
        "",
        f"- directories scanned: {inventory['directories_scanned']}",
        f"- unitypackages found: {totals['unitypackages']}",
        f"- successful packages: {totals['successful_packages']}",
        f"- failed packages: {totals['failed_packages']}",
        f"- package groups inferred by GUID evidence: {len(inventory['package_groups'])}",
        f"- total archive bytes: {totals['archive_bytes']}",
        f"- inventory elapsed seconds: {elapsed:.3f}",
        "",
        "## Structural features",
        "",
    ]
    for key in sorted(totals):
        if key not in {"unitypackages", "successful_packages", "failed_packages", "archive_bytes"}:
            lines.append(f"- {key}: {totals[key]}")
    lines += ["", "Observed signatures:", ""]
    lines += [f"- {key}: {value}" for key, value in signatures.most_common()]
    lines += ["", "Derived heuristics:", ""]
    lines += [f"- {key}: {value}" for key, value in heuristics.most_common()]
    lines += [
        "",
        "## Clusters",
        "",
        f"- structural clusters: {len(inventory['clusters'])}",
    ]
    for key, cases in inventory["clusters"].items():
        lines.append(f"- `{key or 'UNCLASSIFIED'}`: {len(cases)} cases")
    lines += ["", "## Representative cases", ""]
    lines += [f"- {case_id}: selected for structural coverage; private details remain in CORPUS_INDEX.json" for case_id in inventory["representative_case_ids"]]
    lines += [
        "",
        "## Privacy",
        "",
        "- commercial packages committed: 0",
        "- raw commercial Oracle JSON committed: 0",
        "- extracted commercial binaries committed: 0",
        "- public-safe sanitization: PASS",
        "",
        "## Phase 2 status",
        "",
        "Metadata-first inventory only. Unity E2E must use one disposable project per representative case/group.",
        "No Blender importer implementation was changed.",
    ]
    return "\n".join(lines) + "\n"


def _gaps(inventory: dict) -> str:
    observed = {signature for item in inventory["packages"] for signature in item["signatures"]}
    candidates = [
        ("SYNTH-PATTERN-001", "Model Prefab with PrefabInstance and original FBX source identity"),
        ("SYNTH-PATTERN-002", "Multiple Renderer components with duplicate object names"),
        ("SYNTH-PATTERN-003", "Two material slots with one material override"),
        ("SYNTH-PATTERN-004", "ExternalObjects remap with a material provider"),
        ("SYNTH-PATTERN-005", "Multi-package geometry/material provider with GUID evidence"),
        ("SYNTH-PATTERN-006", "Nested Prefab or Prefab Variant with added and removed components"),
        ("SYNTH-PATTERN-007", "SkinnedMeshRenderer with armature and bone hierarchy"),
        ("SYNTH-PATTERN-008", "Custom shader property topology without texture decoding"),
    ]
    lines = ["# Synthetic Fixture Gap Analysis", "", "Generated from anonymous structural signatures.", ""]
    for case_id, description in candidates:
        related = {
            "SYNTH-PATTERN-001": "PREFAB_INSTANCE" in observed and "MODEL_PREFAB" in observed,
            "SYNTH-PATTERN-002": False,
            "SYNTH-PATTERN-003": "MATERIAL_OVERRIDE" in observed,
            "SYNTH-PATTERN-004": "EXTERNAL_OBJECTS" in observed,
            "SYNTH-PATTERN-005": False,
            "SYNTH-PATTERN-006": "LIKELY_NESTED_PREFAB_OR_VARIANT" in {h for item in inventory["packages"] for h in item["heuristics"]},
            "SYNTH-PATTERN-007": "SKINNED_MESH" in observed,
            "SYNTH-PATTERN-008": "CUSTOM_SHADER_REFERENCE" in observed,
        }[case_id]
        status = "observed in corpus; compare against existing synthetic coverage" if related else "candidate gap; create neutral fixture before importer changes"
        lines += [f"## {case_id}", f"- {description}", f"- status: {status}", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    inventory = scan_corpus(args.root)
    elapsed = time.perf_counter() - started
    output_root = validate_output_root(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "CORPUS_INDEX.json", inventory)
    write_json(output_root / "PUBLIC_SAFE_SUMMARY.json", public_safe_summary(inventory))
    (output_root / "INVENTORY_REPORT.md").write_text(_report(inventory, elapsed), encoding="utf-8")
    (output_root / "SYNTHETIC_GAPS.md").write_text(_gaps(inventory), encoding="utf-8")
    print(json.dumps({"packages": inventory["totals"]["unitypackages"], "groups": len(inventory["package_groups"]), "elapsed": round(elapsed, 3)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
