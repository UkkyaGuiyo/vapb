from __future__ import annotations

from typing import Any


def next_experiments(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    result = list(analysis.get("experiments", []))
    if analysis.get("candidateComparison", {}).get("classification") == "USER_CHOICE_REQUIRED":
        result.append({"code": "REQUEST_EXPLICIT_PREFAB_CHOICE", "status": "PROPOSED"})
    if any(x.get("status") == "OBSERVED_UNRESOLVED" for x in analysis.get("dependencies", [])):
        result.append({"code": "TRACE_UNRESOLVED_DEPENDENCY", "status": "PROPOSED"})
    return result
