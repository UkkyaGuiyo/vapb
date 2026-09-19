from __future__ import annotations

from typing import Any

from tools.vapb_oracle.diff import semantic_diff


def roundtrip_diff(before: dict[str, Any], after: dict[str, Any], correspondence: dict[str, str] | None = None) -> dict[str, Any]:
    changes = semantic_diff(before, after)
    identity = [x for x in changes if x.get("kind") == "identity_changed"]
    ordinary = [x for x in changes if x.get("kind") != "identity_changed"]
    status = "EXPECTED_CHANGE" if identity and not ordinary and correspondence else ("UNCHANGED" if not changes else ("NOT_COMPARABLE" if identity and not correspondence else "DIFFERENT"))
    return {"status": status, "identityRegenerationCount": len(identity), "changes": changes}
