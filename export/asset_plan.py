"""Deterministic semantic asset planning; no filesystem materialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .semantic_graph import NodeType, SemanticGraph


class AssetOperation(str, Enum):
    PRESERVE = "PRESERVE"
    MODIFY = "MODIFY"
    CREATE = "CREATE"
    DELETE = "DELETE"
    DUPLICATE = "DUPLICATE"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    RENAME = "RENAME"
    MOVE = "MOVE"
    PRESERVE_EXTERNAL = "PRESERVE_EXTERNAL"
    UNSUPPORTED_PRESERVED = "UNSUPPORTED_PRESERVED"
    AMBIGUOUS = "AMBIGUOUS"


class ExportStrategy(str, Enum):
    PRESERVE_VERBATIM = "PRESERVE_VERBATIM"
    PRESERVE_META_REPLACE_BYTES = "PRESERVE_META_REPLACE_BYTES"
    PRESERVE_AND_PATCH_SERIALIZED = "PRESERVE_AND_PATCH_SERIALIZED"
    REGENERATE_FROM_BLENDER = "REGENERATE_FROM_BLENDER"
    REGENERATE_WITH_NEW_GUID = "REGENERATE_WITH_NEW_GUID"
    UNITY_FINALIZER_REBUILD = "UNITY_FINALIZER_REBUILD"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    UNSUPPORTED_BUT_PRESERVED = "UNSUPPORTED_BUT_PRESERVED"
    EXCLUDE_UNREACHABLE = "EXCLUDE_UNREACHABLE"
    AMBIGUOUS_EXPORT = "AMBIGUOUS_EXPORT"


class GuidDecision(str, Enum):
    PRESERVE_SOURCE_GUID = "PRESERVE_SOURCE_GUID"
    ALLOCATE_NEW_GUID = "ALLOCATE_NEW_GUID"
    REMAP_DUE_TO_COLLISION = "REMAP_DUE_TO_COLLISION"
    DEFER = "DEFER"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    AMBIGUOUS = "AMBIGUOUS"


class PathStatus(str, Enum):
    PRESERVE = "PRESERVE"
    MOVE = "MOVE"
    NEW_PATH = "NEW_PATH"
    COLLISION = "COLLISION"
    DEFER = "DEFER"
    AMBIGUOUS = "AMBIGUOUS"


class ReferenceStability(str, Enum):
    STABLE_OFFLINE = "STABLE_OFFLINE"
    EXPECTED_STABLE = "EXPECTED_STABLE"
    POSTIMPORT_REBIND_REQUIRED = "POSTIMPORT_REBIND_REQUIRED"
    SOURCE_TARGET_REMOVED = "SOURCE_TARGET_REMOVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class FinalizerTaskType(str, Enum):
    REBIND_MODEL_SUBASSET = "REBIND_MODEL_SUBASSET"
    REBIND_RENDERER_MESH = "REBIND_RENDERER_MESH"
    REBIND_RENDERER_MATERIAL = "REBIND_RENDERER_MATERIAL"
    REBIND_SKIN_BONES = "REBIND_SKIN_BONES"
    REBIND_ROOT_BONE = "REBIND_ROOT_BONE"
    REBUILD_PREFAB = "REBUILD_PREFAB"
    PATCH_PREFAB_REFERENCE = "PATCH_PREFAB_REFERENCE"
    PATCH_VRC_REFERENCE = "PATCH_VRC_REFERENCE"
    PATCH_ANIMATOR_REFERENCE = "PATCH_ANIMATOR_REFERENCE"
    VERIFY_ONLY = "VERIFY_ONLY"
    DELETE_ASSET = "DELETE_ASSET"


@dataclass(frozen=True)
class Collision:
    code: str
    left_node_id: str
    right_node_id: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedAsset:
    node_id: str
    node_type: str
    source_identity: dict[str, Any]
    operation: AssetOperation
    strategy: ExportStrategy
    guid_decision: GuidDecision
    path_status: PathStatus
    reference_stability: ReferenceStability
    proof_path: tuple[str, ...]
    postimport_tasks: tuple[str, ...] = ()
    external_dependency: bool = False
    ambiguity: tuple[str, ...] = ()
    target_logical_identity: dict[str, Any] = field(default_factory=dict)
    export_identity: dict[str, Any] = field(default_factory=dict)
    postimport_identity: dict[str, Any] = field(default_factory=dict)
    expected_importer_type: str = ""
    desired_export_path: str = ""


@dataclass(frozen=True)
class AssetPlan:
    export_roots: tuple[str, ...]
    assets: tuple[PlannedAsset, ...]
    collisions: tuple[Collision, ...]
    unsupported_preserved_state: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    proof_relations: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    semantic_records: tuple[dict[str, Any], ...] = ()


def _operation(node: Any) -> AssetOperation:
    if node.node_type == NodeType.EXTERNAL_DEPENDENCY and "operation" not in node.attributes:
        return AssetOperation.PRESERVE_EXTERNAL
    if node.node_type == NodeType.PRESERVED_UNKNOWN_ASSET and "operation" not in node.attributes:
        return AssetOperation.UNSUPPORTED_PRESERVED
    raw = str(node.attributes.get("operation", "CREATE"))
    try:
        return AssetOperation(raw)
    except ValueError:
        return AssetOperation.AMBIGUOUS


def _strategy(node: Any, operation: AssetOperation) -> ExportStrategy:
    raw = node.attributes.get("strategy")
    if raw:
        try:
            return ExportStrategy(str(raw))
        except ValueError:
            return ExportStrategy.AMBIGUOUS_EXPORT
    if operation in {AssetOperation.PRESERVE, AssetOperation.PRESERVE_EXTERNAL}:
        return ExportStrategy.EXTERNAL_DEPENDENCY if operation == AssetOperation.PRESERVE_EXTERNAL else ExportStrategy.PRESERVE_VERBATIM
    if operation == AssetOperation.UNSUPPORTED_PRESERVED:
        return ExportStrategy.UNSUPPORTED_BUT_PRESERVED
    if operation == AssetOperation.MODIFY:
        return ExportStrategy.AMBIGUOUS_EXPORT
    if operation == AssetOperation.DELETE:
        return ExportStrategy.AMBIGUOUS_EXPORT
    if operation in {AssetOperation.DUPLICATE, AssetOperation.CREATE, AssetOperation.SPLIT, AssetOperation.MERGE}:
        return ExportStrategy.REGENERATE_WITH_NEW_GUID
    if operation in {AssetOperation.RENAME, AssetOperation.MOVE}:
        return ExportStrategy.PRESERVE_VERBATIM
    return ExportStrategy.AMBIGUOUS_EXPORT


def _source_identity(node: Any) -> dict[str, Any]:
    provenance = node.provenance
    return {
        "source_package_id": provenance.source_package_id,
        "source_guid": provenance.source_guid,
        "source_file_id": provenance.source_file_id,
        "source_path": provenance.source_path,
        "occurrence_id": provenance.occurrence_id,
    }


def _postimport_tasks(node: Any, operation: AssetOperation) -> tuple[str, ...]:
    if operation not in {AssetOperation.CREATE, AssetOperation.DUPLICATE, AssetOperation.SPLIT, AssetOperation.MERGE}:
        if operation == AssetOperation.DELETE:
            return (FinalizerTaskType.DELETE_ASSET.value,)
        return ()
    if node.node_type == NodeType.MESH_ASSET:
        return (FinalizerTaskType.REBIND_MODEL_SUBASSET.value,)
    if node.node_type == NodeType.RENDERER_OCCURRENCE:
        return (FinalizerTaskType.REBIND_RENDERER_MESH.value, FinalizerTaskType.REBIND_RENDERER_MATERIAL.value)
    if node.node_type == NodeType.PREFAB_ASSET:
        return (FinalizerTaskType.REBUILD_PREFAB.value,)
    return (FinalizerTaskType.VERIFY_ONLY.value,)


_ASSET_NODE_TYPES = {
    NodeType.MESH_ASSET, NodeType.ARMATURE_ASSET, NodeType.MATERIAL_ASSET, NodeType.TEXTURE_ASSET,
    NodeType.ANIMATION_ASSET, NodeType.PREFAB_ASSET, NodeType.ANIMATOR_CONTROLLER_ASSET,
    NodeType.SCRIPTABLE_OBJECT_ASSET, NodeType.SHADER_ASSET, NodeType.MONOSCRIPT_ASSET,
    NodeType.EXTERNAL_DEPENDENCY, NodeType.PRESERVED_UNKNOWN_ASSET,
}


def _expected_importer_type(node: Any) -> str:
    return str(node.attributes.get("expected_importer_type", node.node_type.value))


def _collisions(graph: SemanticGraph, included: tuple[str, ...]) -> tuple[Collision, ...]:
    records = []
    for node_id in included:
        node = graph.nodes[node_id]
        guid = str(node.provenance.source_guid or node.attributes.get("source_guid", "")).lower()
        package = str(node.provenance.source_package_id or node.attributes.get("source_package_id", ""))
        path = str(node.provenance.source_path or node.attributes.get("source_path", "")).replace("\\", "/")
        source_file_id_value = node.provenance.source_file_id if node.provenance.source_file_id is not None else node.attributes.get("source_file_id", "")
        source_file_id = str(source_file_id_value)
        bytes_hash = str(node.attributes.get("bytes_sha256", "")).lower()
        desired_path = str(node.attributes.get("desired_export_path", "")).replace("\\", "/")
        if guid or path or bytes_hash or desired_path:
            records.append((node_id, package, guid, path, source_file_id, bytes_hash, desired_path))
    result: list[Collision] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left[2] and left[2] == right[2]:
                if left[1] != right[1]:
                    result.append(Collision("CROSS_PACKAGE_GUID_COLLISION", left[0], right[0], {"guid": left[2]}))
                elif left[4] == right[4] and left[3] == right[3]:
                    if left[5] and right[5] and left[5] != right[5]:
                        result.append(Collision("DIFFERENT_BYTES_SAME_GUID", left[0], right[0], {"guid": left[2]}))
                    else:
                        result.append(Collision("SAME_GUID_SAME_SOURCE_IDENTITY", left[0], right[0], {"guid": left[2]}))
                elif left[4] == right[4] and (left[3] or right[3]):
                    result.append(Collision("GUID_DIFFERENT_SOURCE_IDENTITY", left[0], right[0], {"guid": left[2]}))
                elif left[4] == right[4] and left[5] and right[5] and left[5] != right[5]:
                    result.append(Collision("DIFFERENT_BYTES_SAME_GUID", left[0], right[0], {"guid": left[2]}))
            if left[3] and left[3] == right[3]:
                if left[1] != right[1]:
                    result.append(Collision("CROSS_PACKAGE_PATH_COLLISION", left[0], right[0], {"path": left[3]}))
                elif left[2] != right[2]:
                    result.append(Collision("SAME_PATH_DIFFERENT_ASSET", left[0], right[0], {"path": left[3]}))
            if left[5] and left[5] == right[5] and left[2] != right[2]:
                result.append(Collision("SAME_BYTES_DIFFERENT_GUID", left[0], right[0], {"bytes_sha256": left[5]}))
            if left[2] and left[2] == right[2] and left[5] and right[5] and left[5] != right[5]:
                result.append(Collision("DIFFERENT_BYTES_SAME_GUID", left[0], right[0], {"guid": left[2]}))
            if left[6] and left[6] == right[6] and left[0] != right[0]:
                same_logical = left[1] == right[1] and left[2] == right[2] and left[3] == right[3] and left[4] == right[4]
                result.append(Collision("SAME_TARGET_PATH_SAME_ASSET" if same_logical else "TARGET_PATH_COLLISION", left[0], right[0], {"path": left[6]}))
    return tuple(result)


def plan_assets(graph: SemanticGraph, roots: list[str] | tuple[str, ...]) -> AssetPlan:
    reachability = graph.reachable_from(roots)
    collisions = _collisions(graph, reachability.included)
    collision_nodes = {node_id for collision in collisions for node_id in (collision.left_node_id, collision.right_node_id)}
    assets: list[PlannedAsset] = []
    errors: list[str] = []
    ambiguous_targets = {target for _source, _edge_type, targets in reachability.ambiguous_edges for target in targets}
    for node_id in reachability.included:
        node = graph.nodes[node_id]
        if node.node_type not in _ASSET_NODE_TYPES:
            continue
        operation = _operation(node)
        if node_id in ambiguous_targets:
            operation = AssetOperation.AMBIGUOUS
        strategy = _strategy(node, operation)
        source_identity = _source_identity(node)
        has_source = bool(source_identity["source_package_id"] and (source_identity["source_guid"] or source_identity["source_path"]))
        continuity = bool(node.attributes.get("continuation", operation in {AssetOperation.PRESERVE, AssetOperation.MODIFY, AssetOperation.RENAME, AssetOperation.MOVE, AssetOperation.PRESERVE_EXTERNAL}) or node.attributes.get("continuation_winner"))
        guid_decision = GuidDecision.PRESERVE_SOURCE_GUID if operation in {AssetOperation.PRESERVE, AssetOperation.MODIFY, AssetOperation.RENAME, AssetOperation.MOVE, AssetOperation.PRESERVE_EXTERNAL} and bool(source_identity["source_guid"]) else GuidDecision.PRESERVE_SOURCE_GUID if operation in {AssetOperation.SPLIT, AssetOperation.MERGE} and continuity and bool(source_identity["source_guid"]) else GuidDecision.ALLOCATE_NEW_GUID if operation in {AssetOperation.CREATE, AssetOperation.DUPLICATE, AssetOperation.SPLIT, AssetOperation.MERGE} else GuidDecision.DEFER
        ambiguity_parts: list[str] = []
        if node_id in collision_nodes:
            ambiguity_parts.append("IDENTITY_COLLISION")
        if node_id in ambiguous_targets:
            ambiguity_parts.append("AMBIGUOUS_PROVIDER")
        if not has_source and operation in {AssetOperation.PRESERVE, AssetOperation.MODIFY, AssetOperation.PRESERVE_EXTERNAL}:
            ambiguity_parts.append("MISSING_SOURCE_PROVENANCE")
        if operation == AssetOperation.MODIFY:
            ambiguity_parts.append("UNVALIDATED_TYPED_PATCH")
        if operation == AssetOperation.MERGE and not node.attributes.get("continuation_winner"):
            ambiguity_parts.append("MERGE_CONTINUATION_UNSET")
        ambiguity = tuple(sorted(set(ambiguity_parts)))
        if ambiguity:
            guid_decision = GuidDecision.AMBIGUOUS
            strategy = ExportStrategy.AMBIGUOUS_EXPORT
            errors.append(f"{node_id}: {','.join(ambiguity)}")
        reference_stability = ReferenceStability.SOURCE_TARGET_REMOVED if operation == AssetOperation.DELETE else ReferenceStability.POSTIMPORT_REBIND_REQUIRED if operation in {AssetOperation.CREATE, AssetOperation.DUPLICATE, AssetOperation.SPLIT, AssetOperation.MERGE} and guid_decision != GuidDecision.PRESERVE_SOURCE_GUID else ReferenceStability.UNKNOWN
        if operation in {AssetOperation.PRESERVE, AssetOperation.PRESERVE_EXTERNAL}:
            reference_stability = ReferenceStability.EXPECTED_STABLE
        source_path = str(source_identity["source_path"] or "")
        desired_path = str(node.attributes.get("desired_export_path", ""))
        path_status = PathStatus.DEFER
        if desired_path and source_path:
            path_status = PathStatus.PRESERVE if desired_path == source_path else PathStatus.MOVE
        elif desired_path:
            path_status = PathStatus.NEW_PATH
        if any(c.left_node_id == node_id or c.right_node_id == node_id for c in collisions if "PATH" in c.code):
            path_status = PathStatus.COLLISION
        target_identity = {"continuation": continuity, "operation": operation.value}
        export_identity = {"export_namespace_id": str(node.attributes.get("export_namespace_id", "")), "export_guid": source_identity["source_guid"] if guid_decision == GuidDecision.PRESERVE_SOURCE_GUID else ""}
        assets.append(PlannedAsset(node_id, node.node_type.value, source_identity, operation, strategy, guid_decision, path_status, reference_stability, tuple(reachability.proof_paths[node_id]), _postimport_tasks(node, operation), operation == AssetOperation.PRESERVE_EXTERNAL, ambiguity, target_identity, export_identity, {}, _expected_importer_type(node), desired_path))
    for collision in collisions:
        errors.append(f"{collision.code}: {collision.left_node_id} vs {collision.right_node_id}")
    semantic_records = tuple(
        {
            "node_id": node_id,
            "node_type": graph.nodes[node_id].node_type.value,
            "provenance": graph.nodes[node_id].provenance.to_dict(),
            "attributes": dict(graph.nodes[node_id].attributes),
            "proof_relations": list(reachability.proof_relations.get(node_id, ())),
        }
        for node_id in reachability.included
        if graph.nodes[node_id].node_type not in _ASSET_NODE_TYPES
    )
    errors.extend(f"AMBIGUOUS_EDGE: {source} -> {','.join(targets)} ({edge_type.value})" for source, edge_type, targets in reachability.ambiguous_edges)
    return AssetPlan(tuple(sorted(set(roots))), tuple(assets), collisions, reachability.unsupported_preserved, (), tuple(sorted(errors)), reachability.proof_relations, semantic_records)
