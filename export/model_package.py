"""Source-preserving model replacement materialization for UnityPackage export."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any

from .asset_plan import (
    AssetOperation, ExportStrategy, FinalizerTaskType, PathStatus,
    ReferenceStability, plan_assets,
)
from .manifest import ExportManifest
from .raw_assets import RawAsset, RawAssetRepository
from .semantic_graph import EdgeType, GraphNode, NodeType, Provenance, SemanticGraph
from .staging import StagedUnityAsset, StagingTree, normalize_guid, stage_asset_plan


@dataclass(frozen=True)
class SourcePackage:
    path: Path
    expected_sha256: str


@dataclass(frozen=True)
class ModelReplacement:
    source_package_id: str
    source_guid: str
    expected_asset_sha256: str
    fbx_bytes: bytes
    rebind_payload: dict[str, Any]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _expected_hash(value: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise ValueError("expected SHA256 must contain 64 hexadecimal characters")
    return value.lower()


def _validate_rebind(payload: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(payload, dict):
        raise ValueError("renderer rebind metadata is required")
    records = payload.get("renderer_mappings")
    if not isinstance(records, (list, tuple)) or not records or any(not isinstance(record, dict) or not record for record in records):
        raise ValueError("authoritative renderer mappings are required")
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("renderer rebind metadata must be JSON serializable") from exc
    return tuple(records)


def materialize_model_package(
    sources: tuple[SourcePackage, ...] | list[SourcePackage],
    replacements: tuple[ModelReplacement, ...] | list[ModelReplacement],
    *,
    generator_version: str,
    blender_version: str,
) -> tuple[StagingTree, ExportManifest]:
    """Build a validated whole-source closure and manifest; caller writes it atomically.

    A replacement continues the source FBX asset with its original GUID, path,
    importer meta and settings. Unity must resolve changed model subassets after
    import using the caller's authoritative renderer mapping.
    """
    if not sources or not replacements:
        raise ValueError("source packages and model replacements are required")
    source_assets: dict[tuple[str, str], RawAsset] = {}
    seen_packages: set[str] = set()
    seen_guids: set[str] = set()
    seen_paths: set[str] = set()
    for source in sources:
        expected = _expected_hash(source.expected_sha256)
        archive_bytes = Path(source.path).read_bytes()
        actual = _sha256(archive_bytes)
        if actual != expected:
            raise ValueError("source package SHA256 is stale")
        package_id = "sha256:" + expected
        if package_id in seen_packages:
            raise ValueError("same source package supplied twice")
        seen_packages.add(package_id)
        for asset in RawAssetRepository(source.path).read_all(archive_bytes):
            if asset.guid in seen_guids or asset.pathname in seen_paths:
                raise ValueError("GUID or path collision across source packages")
            seen_guids.add(asset.guid)
            seen_paths.add(asset.pathname)
            source_assets[(package_id, asset.guid)] = asset

    by_identity: dict[tuple[str, str], ModelReplacement] = {}
    renderer_mappings: list[dict[str, Any]] = []
    for replacement in replacements:
        guid = normalize_guid(replacement.source_guid)
        key = (replacement.source_package_id, guid)
        if key in by_identity:
            raise ValueError("ambiguous model replacement provider")
        if replacement.source_package_id not in seen_packages or key not in source_assets:
            raise ValueError("replacement source identity is unavailable")
        source_asset = source_assets[key]
        if not source_asset.pathname.lower().endswith(".fbx") or not source_asset.asset_bytes:
            raise ValueError("replacement target must be a nonempty source FBX")
        if not isinstance(replacement.fbx_bytes, bytes) or not replacement.fbx_bytes:
            raise ValueError("replacement FBX bytes are empty or invalid")
        if _sha256(source_asset.asset_bytes) != _expected_hash(replacement.expected_asset_sha256):
            raise ValueError("source FBX SHA256 is stale")
        if replacement.fbx_bytes == source_asset.asset_bytes:
            raise ValueError("replacement FBX does not change source bytes")
        mappings = _validate_rebind(replacement.rebind_payload)
        for mapping in mappings:
            if mapping.get("source_package_id", key[0]) != key[0] or mapping.get("source_guid", key[1]) != key[1]:
                raise ValueError("renderer mapping points to another model provider")
            renderer_mappings.append({**mapping, "source_package_id": key[0], "source_guid": key[1]})
        by_identity[key] = replacement

    graph = SemanticGraph()
    graph.add_node(GraphNode("source-closure", NodeType.EXPORT_ROOT, Provenance("SOURCE_CLOSURE")))
    node_keys: dict[str, tuple[str, str]] = {}
    for index, ((package_id, guid), asset) in enumerate(sorted(source_assets.items())):
        node_id = f"source-asset-{index}"
        node_keys[node_id] = (package_id, guid)
        node_type = NodeType.MESH_ASSET if asset.pathname.lower().endswith(".fbx") else NodeType.PRESERVED_UNKNOWN_ASSET
        graph.add_node(GraphNode(node_id, node_type, Provenance("EXACT", package_id, guid, None, asset.pathname), {"operation": "PRESERVE"}))
        graph.add_edge("source-closure", node_id, EdgeType.RAW_SERIALIZED_REFERENCE)
    base_plan = plan_assets(graph, ["source-closure"])
    if base_plan.errors or base_plan.collisions:
        raise ValueError("source asset plan has unresolved collisions or errors")

    planned = []
    for item in base_plan.assets:
        key = node_keys[item.node_id]
        asset = source_assets[key]
        source_identity = {**item.source_identity, "source_sha256": _sha256(asset.asset_bytes)}
        replacement = by_identity.get(key)
        if replacement is None:
            planned.append(replace(item, source_identity=source_identity))
            continue
        planned.append(replace(
            item, source_identity=source_identity,
            operation=AssetOperation.MODIFY,
            strategy=ExportStrategy.PRESERVE_META_REPLACE_BYTES,
            path_status=PathStatus.PRESERVE,
            reference_stability=ReferenceStability.POSTIMPORT_REBIND_REQUIRED,
            postimport_tasks=(
                FinalizerTaskType.REBIND_MODEL_SUBASSET.value,
                FinalizerTaskType.REBIND_RENDERER_MESH.value,
            ),
            postimport_identity={"authoritative_rebind": replacement.rebind_payload},
        ))
    plan = replace(base_plan, assets=tuple(planned), warnings=("CONSERVATIVE_WHOLE_SOURCE_CLOSURE",))

    def payload_for(item: Any) -> StagedUnityAsset:
        key = node_keys[item.node_id]
        asset = source_assets[key]
        replacement = by_identity.get(key)
        return StagedUnityAsset(
            asset.guid, asset.pathname,
            replacement.fbx_bytes if replacement else asset.asset_bytes,
            asset.meta_bytes, asset.preview_bytes,
            asset_type=item.node_type,
            source_identity=item.source_identity,
            export_identity=item.export_identity,
            operation=item.operation.value,
            strategy=item.strategy.value,
            provenance={"source_package_id": key[0], "source_sha256": _sha256(asset.asset_bytes)},
        )

    tree = stage_asset_plan(plan, payload_for)
    manifest = ExportManifest.from_plan(plan, generator_version=generator_version, blender_version=blender_version)
    return tree, replace(manifest, renderer_mappings=tuple(renderer_mappings))
