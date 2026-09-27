"""Read existing Blender scene import evidence without modifying it."""

from __future__ import annotations

import json

from .dependency_resolver import load_dependency_registry
from ..unity.import_outcome import summarize_import_outcome


def scene_import_outcome(scene):
    projections = []
    for root in scene.objects:
        raw = root.get("_vapb_renderer_occurrences")
        if not raw:
            continue
        try:
            projection = json.loads(str(raw))
            if not isinstance(projection, dict) or not isinstance(projection.get("issues"), list):
                raise ValueError("invalid projection")
            projections.append(projection)
        except (TypeError, ValueError, json.JSONDecodeError):
            projections.append({"records": [], "issues": [{"code": "INVALID_SAVED_PROJECTION"}]})
    dependencies = load_dependency_registry(scene).get("dependencies", [])
    outcome = summarize_import_outcome(projections, dependencies)
    return outcome
