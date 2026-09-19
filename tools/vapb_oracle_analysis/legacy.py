from __future__ import annotations

from typing import Any


def legacy_assertions(current: dict[str, Any], baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if baseline is None:
        return [{"status": "UNRESOLVED", "code": "NO_BASELINE", "reason": "legacy comparison requires an explicit baseline"}]
    if not current.get("inputProvenance") or not baseline.get("inputProvenance"):
        return [{"status": "NOT_COMPARABLE", "code": "PROVENANCE_MISSING"}]
    results = []
    for key in ("coverage", "candidateComparison", "dependencies", "anomalies"):
        if key not in baseline or key not in current:
            results.append({"status": "NOT_COMPARABLE", "code": key.upper() + "_MISSING"})
        elif baseline[key] == current[key]:
            results.append({"status": "CONFIRMED", "code": key.upper() + "_STABLE"})
        else:
            results.append({"status": "SUPERSEDED", "code": key.upper() + "_CHANGED"})
    return results
