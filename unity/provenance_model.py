"""Public-safe semantic provenance model for renderer realizations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SourceComponentKey:
    source_kind: str
    source_asset_guid: str
    renderer_file_id: int


@dataclass(frozen=True)
class OwnerKey:
    source_kind: str
    source_asset_guid: str
    owner_game_object_id: int


@dataclass(frozen=True)
class MeshKey:
    mesh_guid: str
    mesh_file_id: int | None


@dataclass(frozen=True)
class OccurrenceStep:
    container_asset_guid: str
    prefab_instance_file_id: int
    source_prefab_guid: str


@dataclass(frozen=True)
class OccurrenceKey:
    root_context_id: str
    instance_edge_path: tuple[OccurrenceStep, ...]
    source_key: SourceComponentKey


@dataclass(frozen=True)
class BridgeKey:
    import_package_id: str
    source_primitive_id: str


@dataclass(frozen=True)
class OccurrenceRecord:
    occurrence_key: OccurrenceKey
    expected_owner: OwnerKey
    expected_mesh: MeshKey
    bridge_key: BridgeKey | None = None


@dataclass(frozen=True)
class ProvenanceLookup:
    status: str
    occurrence: OccurrenceRecord | None = None


class SemanticProvenanceIndex:
    """Join only explicit records; conflicts and omissions fail closed."""

    def __init__(self, records: Iterable[OccurrenceRecord] = ()):
        self._by_occurrence: dict[OccurrenceKey, list[OccurrenceRecord]] = {}
        self._by_bridge: dict[BridgeKey, list[OccurrenceRecord]] = {}
        for record in records:
            self.add(record)

    def add(self, record: OccurrenceRecord) -> None:
        self._by_occurrence.setdefault(record.occurrence_key, []).append(record)
        if record.bridge_key is not None:
            self._by_bridge.setdefault(record.bridge_key, []).append(record)

    def lookup_occurrence(self, key: OccurrenceKey) -> ProvenanceLookup:
        records = self._by_occurrence.get(key, [])
        if not records:
            return ProvenanceLookup("UNKNOWN")
        if len(records) != 1:
            return ProvenanceLookup("AMBIGUOUS")
        return ProvenanceLookup("EXACT", records[0])

    def lookup_bridge(self, key: BridgeKey) -> ProvenanceLookup:
        records = self._by_bridge.get(key, [])
        if not records:
            return ProvenanceLookup("UNKNOWN")
        if len(records) != 1:
            return ProvenanceLookup("AMBIGUOUS")
        return ProvenanceLookup("EXACT", records[0])
