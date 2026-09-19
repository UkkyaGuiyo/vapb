"""Synthetic-only corpus grouping and deterministic holdout helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def holdout_groups(records: list[dict[str, Any]], holdout_count: int = 1) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        groups[str(record["group"])].append(str(record["case"]))
    ordered = sorted(groups)
    holdout_count = max(0, min(holdout_count, len(ordered)))
    holdout = ordered[-holdout_count:] if holdout_count else []
    train = ordered[:-holdout_count] if holdout_count else ordered
    return {
        "trainGroups": train,
        "holdoutGroups": holdout,
        "trainCases": sorted(case for group in train for case in groups[group]),
        "holdoutCases": sorted(case for group in holdout for case in groups[group]),
    }
