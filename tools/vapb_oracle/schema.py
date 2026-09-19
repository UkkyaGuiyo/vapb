"""Schema and public-output guards for Unity Semantic Oracle observations."""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

_MACHINE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|LOCAL_PATH_REQUIRES_CONFIGURATION")
_GUID = re.compile(r"(?i)\b[0-9a-f]{32}\b")


def build_envelope(*, run_id: str, unity_version: str, access_method: str,
                   case_id: str, observed: dict[str, Any], derived: dict[str, Any],
                   limitations: list[str] | None = None,
                   checkpoint: str = "COMPLETE") -> dict[str, Any]:
    return {
        "schemaVersion": "0.2",
        "runId": run_id,
        "unityVersion": unity_version,
        "accessMethod": access_method,
        "caseId": case_id,
        "checkpoint": checkpoint,
        "observed": copy.deepcopy(observed),
        "derived": copy.deepcopy(derived),
        "limitations": list(limitations or []),
        "observedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


def _find_leaks(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_find_leaks(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_find_leaks(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        if _MACHINE_PATH.search(value):
            errors.append(f"machine path at {path}")
        if _GUID.search(value) and not path.endswith(".syntheticGuid"):
            errors.append(f"raw GUID at {path}")
    return errors


def validate_envelope(envelope: dict[str, Any]) -> list[str]:
    required = ("schemaVersion", "runId", "unityVersion", "accessMethod",
                "caseId", "checkpoint", "observed", "derived", "limitations")
    errors = [f"missing field: {key}" for key in required if key not in envelope]
    if "observed" in envelope and not isinstance(envelope["observed"], dict):
        errors.append("observed must be an object")
    if "derived" in envelope and not isinstance(envelope["derived"], dict):
        errors.append("derived must be an object")
    errors.extend(_find_leaks(envelope.get("observed", {}), ".observed"))
    errors.extend(_find_leaks(envelope.get("derived", {}), ".derived"))
    return errors


def public_safe_summary(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return aggregate-safe fields, never raw observed payload."""
    return {
        "schemaVersion": envelope.get("schemaVersion"),
        "unityVersion": envelope.get("unityVersion"),
        "accessMethod": envelope.get("accessMethod"),
        "caseId": envelope.get("caseId"),
        "checkpoint": envelope.get("checkpoint"),
        "observedKeys": sorted(envelope.get("observed", {}).keys()),
        "derived": copy.deepcopy(envelope.get("derived", {})),
        "limitations": list(envelope.get("limitations", [])),
    }


def validate_derived_counts(envelope: dict[str, Any]) -> list[str]:
    """Cross-check the compact counts against observed prefab records."""
    prefabs = envelope.get("observed", {}).get("prefabs", [])
    object_count = sum(len(prefab.get("objects", [])) for prefab in prefabs)
    material_count = sum(
        len(obj.get("materials", []))
        for prefab in prefabs
        for obj in prefab.get("objects", [])
    )
    expected = {
        "prefabCount": len(prefabs),
        "objectCount": object_count,
        "materialSlotCount": material_count,
    }
    return [
        f"derived mismatch: {key} expected {value} got {envelope.get('derived', {}).get(key)}"
        for key, value in expected.items()
        if envelope.get("derived", {}).get(key) != value
    ]
