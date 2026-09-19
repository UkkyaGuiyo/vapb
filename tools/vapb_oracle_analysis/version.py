from __future__ import annotations

from typing import Any


def compare_versions(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    stable = ("coverage", "candidateComparison", "dependencies")
    unknown = []
    changes = []
    for key in stable:
        if key not in before or key not in after:
            unknown.append(key)
        elif before[key] != after[key]:
            changes.append(key)
    if unknown and not changes: status = "UNKNOWN"
    elif before.get("coverage", {}).get("unknown") or after.get("coverage", {}).get("unknown"): status = "UNKNOWN"
    elif changes: status = "VERSION_SENSITIVE"
    else: status = "VERSION_STABLE"
    return {"status": status, "changedFields": changes, "unknownFields": unknown}
