"""Semantic Contract v0 data model and a synthetic projection oracle.

This module defines identity-bearing values only.  The synthetic adapter is
intentionally not connected to package import or Blender realization; it is a
contract-test reference for the occurrence projection boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from .provenance_model import (
    MeshKey,
    OccurrenceKey,
    OccurrenceStep,
    OwnerKey,
    SourceComponentKey,
)


CONTRACT_VERSION = "v0"


@dataclass(frozen=True)
class OccurrenceProjectionContext:
    """Selected-root and instance-edge scope for one occurrence projection."""

    root_context_id: str
    instance_edge_path: tuple[OccurrenceStep, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.root_context_id).strip():
            raise ValueError("root_context_id must be non-empty")
        object.__setattr__(self, "root_context_id", str(self.root_context_id))
        object.__setattr__(self, "instance_edge_path", tuple(self.instance_edge_path))


@dataclass(frozen=True)
class ProjectionSource:
    """One explicit source Renderer relation used by the contract adapter."""

    source_key: SourceComponentKey
    expected_owner: OwnerKey
    expected_mesh: MeshKey


@dataclass(frozen=True)
class ContractMaterialOverride:
    """Material value scoped to an existing occurrence and slot."""

    slot_index: int
    material_guid: str

    def __post_init__(self) -> None:
        if int(self.slot_index) < 0:
            raise ValueError("slot_index must be non-negative")
        if not str(self.material_guid).strip():
            raise ValueError("material_guid must be non-empty")
        object.__setattr__(self, "slot_index", int(self.slot_index))
        object.__setattr__(self, "material_guid", str(self.material_guid).lower())


@dataclass(frozen=True)
class RendererOccurrenceContract:
    """Stable occurrence identity plus explicit source/realization expectations."""

    occurrence_key: OccurrenceKey
    expected_owner: OwnerKey
    expected_mesh: MeshKey
    material_overrides: tuple[ContractMaterialOverride, ...] = ()
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"unsupported contract version: {self.contract_version}")
        overrides = tuple(self.material_overrides)
        slots = [item.slot_index for item in overrides]
        if len(slots) != len(set(slots)):
            raise ValueError("material override slots must be unique")
        object.__setattr__(self, "material_overrides", tuple(sorted(overrides, key=lambda item: item.slot_index)))

    @property
    def source_key(self) -> SourceComponentKey:
        return self.occurrence_key.source_key

    def with_material_overrides(
        self, overrides: Iterable[ContractMaterialOverride]
    ) -> "RendererOccurrenceContract":
        """Return a changed value while preserving occurrence identity."""
        return replace(self, material_overrides=tuple(overrides))

    def to_dict(self) -> dict:
        """Return a deterministic, name-free diagnostic representation."""
        return {
            "contract_version": self.contract_version,
            "occurrence": {
                "root_context_id": self.occurrence_key.root_context_id,
                "instance_edge_path": [
                    {
                        "container_asset_guid": step.container_asset_guid,
                        "prefab_instance_file_id": step.prefab_instance_file_id,
                        "source_prefab_guid": step.source_prefab_guid,
                    }
                    for step in self.occurrence_key.instance_edge_path
                ],
            },
            "source": {
                "source_kind": self.source_key.source_kind,
                "source_asset_guid": self.source_key.source_asset_guid,
                "renderer_file_id": self.source_key.renderer_file_id,
            },
            "owner": {
                "source_kind": self.expected_owner.source_kind,
                "source_asset_guid": self.expected_owner.source_asset_guid,
                "owner_game_object_id": self.expected_owner.owner_game_object_id,
            },
            "mesh": {
                "mesh_guid": self.expected_mesh.mesh_guid,
                "mesh_file_id": self.expected_mesh.mesh_file_id,
            },
            "material_overrides": [
                {"slot_index": item.slot_index, "material_guid": item.material_guid}
                for item in self.material_overrides
            ],
        }


@dataclass(frozen=True)
class ProjectionResult:
    occurrences: tuple[RendererOccurrenceContract, ...]
    ambiguous_source_keys: tuple[SourceComponentKey, ...] = ()


class SyntheticOccurrenceProjectionAdapter:
    """Small deterministic adapter used only by the Stage 1B contract tests."""

    def project(
        self,
        sources: Iterable[ProjectionSource],
        contexts: Iterable[OccurrenceProjectionContext],
    ) -> ProjectionResult:
        normalized: dict[SourceComponentKey, ProjectionSource] = {}
        ambiguous: set[SourceComponentKey] = set()
        for item in sources:
            previous = normalized.get(item.source_key)
            if previous is None:
                normalized[item.source_key] = item
            elif previous != item:
                ambiguous.add(item.source_key)

        context_values = tuple(contexts)
        result: list[RendererOccurrenceContract] = []
        for context in context_values:
            for source_key in sorted(normalized, key=lambda key: (key.source_kind, key.source_asset_guid, key.renderer_file_id)):
                if source_key in ambiguous:
                    continue
                item = normalized[source_key]
                result.append(RendererOccurrenceContract(
                    OccurrenceKey(context.root_context_id, context.instance_edge_path, source_key),
                    item.expected_owner,
                    item.expected_mesh,
                ))
        return ProjectionResult(tuple(result), tuple(sorted(ambiguous, key=lambda key: (
            key.source_kind, key.source_asset_guid, key.renderer_file_id
        ))))
