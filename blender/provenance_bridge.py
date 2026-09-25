"""Fail-closed semantic joins between effective Renderers and Blender objects."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable


@dataclass(frozen=True)
class RealizationKey:
    source_guid: str
    renderer_file_id: str
    owner_game_object_id: str
    mesh_guid: str
    mesh_file_id: str
    occurrence_id: str = ""


@dataclass(frozen=True)
class RealizationLookup:
    obj: object | None
    evidence: str


class BlenderRealizationIndex:
    """Index explicit persisted provenance, never display labels."""

    def __init__(self, objects: Iterable[object] = ()):
        self._records: dict[RealizationKey, list[object]] = {}
        for obj in objects:
            self.add(obj)

    @staticmethod
    def _bindings(obj: object) -> list[dict]:
        try:
            payload = json.loads(str(obj.get("_vapb_renderer_bindings", "{}")))
        except (TypeError, ValueError, AttributeError):
            return []
        records = payload.get("renderers", [])
        return [record for record in records if isinstance(record, dict)]

    @staticmethod
    def _key(record: dict) -> RealizationKey | None:
        required = (
            record.get("source_asset_guid"),
            record.get("renderer_file_id"),
            record.get("game_object_file_id"),
            record.get("mesh_guid"),
            record.get("mesh_file_id"),
            record.get("occurrence_id") or record.get("member_id"),
        )
        if any(value in (None, "") for value in required):
            return None
        return RealizationKey(
            str(required[0]).lower(), str(required[1]), str(required[2]),
            str(required[3]).lower(), str(required[4]),
            str(required[5]),
        )

    def add(self, obj: object) -> None:
        for record in self._bindings(obj):
            key = self._key(record)
            if key is not None:
                self._records.setdefault(key, []).append(obj)

    def lookup(self, key: RealizationKey) -> RealizationLookup:
        candidates = self._records.get(key, [])
        if not candidates:
            return RealizationLookup(None, "UNKNOWN")
        if len(candidates) != 1:
            return RealizationLookup(None, "AMBIGUOUS")
        return RealizationLookup(candidates[0], "EXACT")
