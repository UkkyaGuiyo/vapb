from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def public_report(analysis: dict[str, Any]) -> dict[str, Any]:
    allowed_anomalies = {"IDENTITY_COLLISION", "MAT_SLOT_EMPTY", "MAT_TEXTURE_REFERENCE_UNRESOLVED", "PROPERTY_REFERENCE_UNRESOLVED"}
    allowed_experiments = {"COMPARE_CANDIDATE_SEMANTICS", "TRACE_UNRESOLVED_DEPENDENCY", "REQUEST_EXPLICIT_PREFAB_CHOICE"}
    deps = {}
    for item in analysis.get("dependencies", []):
        key = (item.get("kind"), item.get("status")); deps["%s:%s" % key] = deps.get("%s:%s" % key, 0) + 1
    return {
        "analysisVersion": analysis.get("analysisVersion"),
        "coverage": {"supported": list(analysis.get("coverage", {}).get("supported", [])), "unknown": list(analysis.get("coverage", {}).get("unknown", [])), "unsupported": list(analysis.get("coverage", {}).get("unsupported", []))},
        "candidateComparison": {"classification": analysis.get("candidateComparison", {}).get("classification"), "candidateCount": analysis.get("candidateComparison", {}).get("candidateCount"), "automaticSelection": False},
        "clusterCount": len(analysis.get("clusters", [])),
        "dependencyCounts": deps,
        "materialTextureGraph": analysis.get("materialTextureGraph", {"roleCounts": {}, "resolvedRoleCounts": {}, "unknownRoleCount": 0}),
        "anomalyCodes": sorted({x.get("code") for x in analysis.get("anomalies", []) if x.get("code") in allowed_anomalies}),
        "experimentCodes": sorted({x.get("code") for x in analysis.get("experiments", []) if x.get("code") in allowed_experiments}),
    }


def write_reports(analysis: dict[str, Any], output_dir: Path, *, include_private: bool = True) -> dict[str, Path]:
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    private = output_dir / "analysis.json"; public = output_dir / "public_summary.json"; markdown = output_dir / "analysis.md"
    if include_private: private.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    safe = public_report(analysis); public.write_text(json.dumps(safe, indent=2, sort_keys=True), encoding="utf-8")
    markdown.write_text("# VAPB Oracle Analysis\n\n```json\n" + json.dumps(safe, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")
    result = {"public": public, "markdown": markdown}
    if include_private: result["private"] = private
    return result
