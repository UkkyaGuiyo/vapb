"""Versioned deterministic export manifest serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from .asset_plan import AssetPlan


SCHEMA_VERSION = "vapb-export-manifest-1"


@dataclass(frozen=True)
class GeneratorInfo:
    vapb_version: str
    blender_version: str


@dataclass(frozen=True)
class ExportManifest:
    schema_version: str
    generator: GeneratorInfo
    source_packages: tuple[dict[str, Any], ...]
    source_assets: tuple[dict[str, Any], ...]
    export_assets: tuple[dict[str, Any], ...]
    export_roots: tuple[str, ...]
    renderer_mappings: tuple[dict[str, Any], ...]
    mesh_mappings: tuple[dict[str, Any], ...]
    material_mappings: tuple[dict[str, Any], ...]
    texture_mappings: tuple[dict[str, Any], ...]
    bone_mappings: tuple[dict[str, Any], ...]
    shape_key_mappings: tuple[dict[str, Any], ...]
    prefab_source_chains: tuple[dict[str, Any], ...]
    component_provenance: tuple[dict[str, Any], ...]
    reachability: tuple[dict[str, Any], ...]
    reference_rebind_tasks: tuple[dict[str, Any], ...]
    unity_postimport_identity_map: tuple[dict[str, Any], ...]
    external_dependencies: tuple[dict[str, Any], ...]
    unsupported_preserved_state: tuple[str, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    collisions: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_plan(cls, plan: AssetPlan, *, generator_version: str, blender_version: str) -> "ExportManifest":
        export_assets = tuple(_planned_asset_dict(item) for item in plan.assets)
        proof_paths = {item.node_id: item.proof_path for item in plan.assets}
        reachability = tuple(
            {"node_id": node_id, "proof_path": list(proof_paths.get(node_id, ())), "proof_relations": list(relations)}
            for node_id, relations in sorted(plan.proof_relations.items())
        )
        external = tuple(item for item in export_assets if item["external_dependency"])
        source_packages = tuple({"source_package_id": package_id} for package_id in sorted({item.source_identity["source_package_id"] for item in plan.assets if item.source_identity["source_package_id"]}))
        source_assets = tuple(item.source_identity for item in plan.assets if item.source_identity["source_guid"] or item.source_identity["source_path"])
        renderer = tuple(item for item in plan.semantic_records if item["node_type"] == "RENDERER_OCCURRENCE")
        mesh = tuple(item for item in export_assets if item["node_type"] == "MESH_ASSET")
        material = tuple(item for item in export_assets if item["node_type"] == "MATERIAL_ASSET")
        texture = tuple(item for item in export_assets if item["node_type"] == "TEXTURE_ASSET")
        rebind_tasks = tuple(
            {"node_id": item["node_id"], "tasks": list(item["postimport_tasks"]), "reference_stability": item["reference_stability"]}
            for item in export_assets if item["postimport_tasks"]
        )
        component_provenance = tuple(item for item in plan.semantic_records if item["node_type"] in {"UNITY_COMPONENT_STATE", "VRC_COMPONENT_STATE", "RENDERER_OCCURRENCE"})
        all_relations = tuple(relation for relations in plan.proof_relations.values() for relation in relations)
        prefab_chains = tuple(item for item in all_relations if item.get("edge_type") == "PREFAB_SOURCE_CHAIN")
        bone_mappings = tuple(item for item in plan.semantic_records if item["node_type"] == "BONE_SEMANTIC")
        shape_key_mappings = tuple(item for item in plan.semantic_records if item["node_type"] in {"SHAPE_KEY_DEFINITION", "BLENDSHAPE_OCCURRENCE"})
        return cls(
            SCHEMA_VERSION,
            GeneratorInfo(generator_version, blender_version),
            source_packages,
            source_assets,
            export_assets,
            plan.export_roots,
            renderer, mesh, material, texture, bone_mappings, shape_key_mappings, prefab_chains, component_provenance, reachability, rebind_tasks, (), external,
            plan.unsupported_preserved_state,
            plan.warnings,
            plan.errors,
            tuple(asdict(item) for item in plan.collisions),
        )

    def to_dict(self) -> dict[str, Any]:
        return _normalize(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExportManifest":
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported export manifest schema: {payload.get('schema_version')!r}")
        known_fields = set(cls.__dataclass_fields__)
        data = {key: value for key, value in payload.items() if key in known_fields}
        data["generator"] = GeneratorInfo(**data["generator"])
        tuple_fields = (
            "source_packages", "source_assets", "export_assets", "export_roots", "renderer_mappings", "mesh_mappings",
            "material_mappings", "texture_mappings", "bone_mappings", "shape_key_mappings", "prefab_source_chains",
            "component_provenance", "reachability", "reference_rebind_tasks", "unity_postimport_identity_map",
            "external_dependencies", "unsupported_preserved_state", "warnings", "errors",
            "collisions",
        )
        for field_name in tuple_fields:
            data[field_name] = tuple(data.get(field_name, ()))
        return cls(**data)


def _planned_asset_dict(item: Any) -> dict[str, Any]:
    return {
        "node_id": item.node_id,
        "node_type": item.node_type,
        "source_identity": dict(sorted(item.source_identity.items())),
        "operation": item.operation.value,
        "strategy": item.strategy.value,
        "guid_decision": item.guid_decision.value,
        "path_status": item.path_status.value,
        "desired_export_path": item.desired_export_path,
        "reference_stability": item.reference_stability.value,
        "proof_path": list(item.proof_path),
        "postimport_tasks": list(item.postimport_tasks),
        "external_dependency": item.external_dependency,
        "ambiguity": list(item.ambiguity),
        "target_logical_identity": dict(sorted(item.target_logical_identity.items())),
        "export_identity": dict(sorted(item.export_identity.items())),
        "postimport_identity": dict(sorted(item.postimport_identity.items())),
        "expected_importer_type": item.expected_importer_type,
    }


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value
