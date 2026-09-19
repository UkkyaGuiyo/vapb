from __future__ import annotations

from enum import Enum
import re
from typing import Any


class ObservationContext(str, Enum):
    ISOLATED_PACKAGE = "ISOLATED_PACKAGE"
    MERGED_CORPUS = "MERGED_CORPUS"
    CONTROLLED_COLLISION = "CONTROLLED_COLLISION"
    ROUNDTRIP = "ROUNDTRIP"
    UNKNOWN = "UNKNOWN"


def context_of(value: dict[str, Any]) -> ObservationContext:
    raw = value.get("observationContext", value.get("provenance", {}).get("observationContext", "UNKNOWN"))
    try:
        return ObservationContext(str(raw))
    except ValueError:
        return ObservationContext.UNKNOWN


def require_isolated(value: dict[str, Any]) -> None:
    context = context_of(value)
    if context is not ObservationContext.ISOLATED_PACKAGE:
        raise ValueError(f"ISOLATION_REQUIRED: got observation context {context.value}")
    provenance = value.get("provenance", {}).get("packageProvenance", {})
    if not provenance or provenance.get("isolationVerified") is not True:
        raise ValueError("ISOLATION_UNVERIFIED: package baseline was not attested")
    for field in ("baselineId", "baselineHash", "packageSha256"):
        if not provenance.get(field):
            raise ValueError(f"ISOLATION_UNVERIFIED: missing {field}")
    for field in ("baselineHash", "packageSha256"):
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(provenance[field])):
            raise ValueError(f"ISOLATION_UNVERIFIED: invalid {field}")
    if provenance.get("isolationFailureReason"):
        raise ValueError("ISOLATION_UNVERIFIED: isolation failure was recorded")
    if provenance.get("collisionEvents"):
        raise ValueError("ISOLATION_UNVERIFIED: collision events were recorded")
