"""Deterministic semantic diff for sanitized Oracle envelopes."""

from __future__ import annotations

from typing import Any


def semantic_diff(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}"
            if key not in before:
                changes.append({"kind": "added", "path": child, "after": after[key]})
            elif key not in after:
                changes.append({"kind": "removed", "path": child, "before": before[key]})
            else:
                changes.extend(semantic_diff(before[key], after[key], child))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before):
                changes.append({"kind": "added", "path": child, "after": after[index]})
            elif index >= len(after):
                changes.append({"kind": "removed", "path": child, "before": before[index]})
            else:
                changes.extend(semantic_diff(before[index], after[index], child))
        return changes
    if before != after:
        identity_fields = (".global_id", ".guid", ".local_file_id", ".globalObjectId",
                           ".localFileID", ".meshGuid", ".sourceGuid", ".originalSourceGuid")
        kind = "identity_changed" if path.endswith(identity_fields) else "changed"
        changes.append({"kind": kind, "path": path, "before": before, "after": after})
    return changes
