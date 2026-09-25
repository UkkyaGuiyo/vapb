"""Occurrence-aware semantic graph used before any export materialization."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class NodeType(str, Enum):
    EXPORT_ROOT = "EXPORT_ROOT"
    GAMEOBJECT_OCCURRENCE = "GAMEOBJECT_OCCURRENCE"
    RENDERER_OCCURRENCE = "RENDERER_OCCURRENCE"
    MESH_ASSET = "MESH_ASSET"
    ARMATURE_ASSET = "ARMATURE_ASSET"
    MATERIAL_ASSET = "MATERIAL_ASSET"
    TEXTURE_ASSET = "TEXTURE_ASSET"
    ANIMATION_ASSET = "ANIMATION_ASSET"
    PREFAB_ASSET = "PREFAB_ASSET"
    ANIMATOR_CONTROLLER_ASSET = "ANIMATOR_CONTROLLER_ASSET"
    SCRIPTABLE_OBJECT_ASSET = "SCRIPTABLE_OBJECT_ASSET"
    SHADER_ASSET = "SHADER_ASSET"
    MONOSCRIPT_ASSET = "MONOSCRIPT_ASSET"
    UNITY_COMPONENT_STATE = "UNITY_COMPONENT_STATE"
    VRC_COMPONENT_STATE = "VRC_COMPONENT_STATE"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    PRESERVED_UNKNOWN_ASSET = "PRESERVED_UNKNOWN_ASSET"
    BONE_SEMANTIC = "BONE_SEMANTIC"
    SHAPE_KEY_DEFINITION = "SHAPE_KEY_DEFINITION"
    BLENDSHAPE_OCCURRENCE = "BLENDSHAPE_OCCURRENCE"


class EdgeType(str, Enum):
    ROOT_CONTAINS_OBJECT = "ROOT_CONTAINS_OBJECT"
    OBJECT_USES_RENDERER = "OBJECT_USES_RENDERER"
    RENDERER_USES_MESH = "RENDERER_USES_MESH"
    RENDERER_USES_MATERIAL = "RENDERER_USES_MATERIAL"
    MATERIAL_USES_TEXTURE = "MATERIAL_USES_TEXTURE"
    PREFAB_USES_PREFAB = "PREFAB_USES_PREFAB"
    PREFAB_SOURCE_CHAIN = "PREFAB_SOURCE_CHAIN"
    ANIMATOR_USES_CLIP = "ANIMATOR_USES_CLIP"
    ANIMATOR_USES_MASK = "ANIMATOR_USES_MASK"
    AVATAR_USES_CONTROLLER = "AVATAR_USES_CONTROLLER"
    PHYSBONE_USES_TRANSFORM = "PHYSBONE_USES_TRANSFORM"
    PHYSBONE_USES_COLLIDER = "PHYSBONE_USES_COLLIDER"
    CONTACT_USES_TRANSFORM = "CONTACT_USES_TRANSFORM"
    MONOBEHAVIOUR_REFERENCES_OBJECT = "MONOBEHAVIOUR_REFERENCES_OBJECT"
    SCRIPTABLE_OBJECT_REFERENCES_OBJECT = "SCRIPTABLE_OBJECT_REFERENCES_OBJECT"
    SHADER_DEPENDENCY = "SHADER_DEPENDENCY"
    RAW_SERIALIZED_REFERENCE = "RAW_SERIALIZED_REFERENCE"
    POSTIMPORT_REBIND_REQUIRED = "POSTIMPORT_REBIND_REQUIRED"


_MULTI_VALUED_EDGE_TYPES = {
    EdgeType.ROOT_CONTAINS_OBJECT,
    EdgeType.OBJECT_USES_RENDERER,
    EdgeType.MATERIAL_USES_TEXTURE,
    EdgeType.ANIMATOR_USES_CLIP,
    EdgeType.ANIMATOR_USES_MASK,
    EdgeType.PHYSBONE_USES_TRANSFORM,
    EdgeType.PHYSBONE_USES_COLLIDER,
    EdgeType.CONTACT_USES_TRANSFORM,
    EdgeType.MONOBEHAVIOUR_REFERENCES_OBJECT,
    EdgeType.SCRIPTABLE_OBJECT_REFERENCES_OBJECT,
    EdgeType.RAW_SERIALIZED_REFERENCE,
}

_AMBIGUITY_SENSITIVE_EDGE_TYPES = {
    EdgeType.RENDERER_USES_MESH,
    EdgeType.RENDERER_USES_MATERIAL,
    EdgeType.MATERIAL_USES_TEXTURE,
    EdgeType.AVATAR_USES_CONTROLLER,
}


@dataclass(frozen=True)
class SourceIdentity:
    source_package_id: str
    source_guid: str = ""
    source_file_id: int | None = None
    source_path: str = ""

    def __post_init__(self) -> None:
        if self.source_file_id is not None:
            object.__setattr__(self, "source_file_id", int(self.source_file_id))

    @property
    def key(self) -> tuple[str, ...]:
        if self.source_guid:
            return (self.source_package_id, "guid", self.source_guid.lower(), "file_id", str(self.source_file_id if self.source_file_id is not None else ""))
        if self.source_path:
            return (self.source_package_id, "path", self.source_path.replace("\\", "/"), "file_id", str(self.source_file_id if self.source_file_id is not None else ""))
        return (self.source_package_id, "ambiguous", "file_id", str(self.source_file_id if self.source_file_id is not None else ""))

    @property
    def ambiguous(self) -> bool:
        return not self.source_guid and not self.source_path


@dataclass(frozen=True)
class Provenance:
    relation: str
    source_package_id: str = ""
    source_guid: str = ""
    source_file_id: int | None = None
    source_path: str = ""
    occurrence_id: str = ""
    blender_object_id: str = ""
    blender_datablock_id: str = ""

    def __post_init__(self) -> None:
        if self.source_file_id is not None:
            object.__setattr__(self, "source_file_id", int(self.source_file_id))

    def source_identity(self) -> SourceIdentity | None:
        if not self.source_package_id:
            return None
        return SourceIdentity(self.source_package_id, self.source_guid, self.source_file_id, self.source_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relation": self.relation,
            "source_package_id": self.source_package_id,
            "source_guid": self.source_guid,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "occurrence_id": self.occurrence_id,
            "blender_object_id": self.blender_object_id,
            "blender_datablock_id": self.blender_datablock_id,
        }


@dataclass
class GraphNode:
    node_id: str
    node_type: NodeType
    provenance: Provenance
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    edge_type: EdgeType
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReachabilityResult:
    included: tuple[str, ...]
    proof_paths: dict[str, tuple[str, ...]]
    proof_edges: dict[str, tuple[EdgeType, ...]]
    proof_relations: dict[str, tuple[dict[str, Any], ...]]
    unsupported_preserved: tuple[str, ...]
    ambiguous_edges: tuple[tuple[str, EdgeType, tuple[str, ...]], ...]

    def proof_path(self, node_id: str) -> list[str]:
        return list(self.proof_paths[node_id])

    def edge_types(self, node_id: str) -> list[EdgeType]:
        return list(self.proof_edges[node_id])


class SemanticGraph:
    """A deterministic graph of desired Unity semantics, not package bytes."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []

    def add_node(self, node: GraphNode) -> GraphNode:
        existing = self.nodes.get(node.node_id)
        if existing is not None and existing != node:
            raise ValueError(f"duplicate graph node: {node.node_id}")
        self.nodes[node.node_id] = node
        return node

    def add_edge(self, source: str, target: str, edge_type: EdgeType, attributes: dict[str, Any] | None = None) -> GraphEdge:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("graph edge endpoints must already exist")
        edge = GraphEdge(source, target, edge_type, dict(attributes or {}))
        if edge not in self.edges:
            self.edges.append(edge)
        return edge

    def _outgoing(self, source: str) -> list[GraphEdge]:
        return sorted((edge for edge in self.edges if edge.source == source), key=lambda edge: (edge.edge_type.value, edge.target))

    def reachable_from(self, roots: Iterable[str]) -> ReachabilityResult:
        root_ids = tuple(sorted(set(roots)))
        missing = [root for root in root_ids if root not in self.nodes]
        if missing:
            raise KeyError(f"unknown export root: {missing[0]}")
        queue: deque[str] = deque(root_ids)
        paths: dict[str, tuple[str, ...]] = {root: (root,) for root in root_ids}
        proof_edges: dict[str, tuple[EdgeType, ...]] = {root: () for root in root_ids}
        proof_relations: dict[str, tuple[dict[str, Any], ...]] = {root: () for root in root_ids}
        all_edges: dict[tuple[str, EdgeType, Any], set[str]] = {}
        while queue:
            source = queue.popleft()
            for edge in self._outgoing(source):
                relation_key = edge.attributes.get("relation_key", edge.attributes.get("slot_index"))
                if edge.edge_type not in _MULTI_VALUED_EDGE_TYPES or edge.attributes.get("provider_candidate") or edge.edge_type in _AMBIGUITY_SENSITIVE_EDGE_TYPES and relation_key is not None:
                    all_edges.setdefault((source, edge.edge_type, relation_key), set()).add(edge.target)
                candidate_path = paths[source] + (edge.target,)
                if edge.target not in paths:
                    paths[edge.target] = candidate_path
                    proof_edges[edge.target] = proof_edges[source] + (edge.edge_type,)
                    proof_relations[edge.target] = proof_relations[source] + ({"edge_type": edge.edge_type.value, **dict(edge.attributes)},)
                    queue.append(edge.target)
        ambiguous = tuple(
            (source, edge_type, tuple(sorted(targets)))
            for (source, edge_type, _relation_key), targets in sorted(all_edges.items(), key=lambda item: (item[0][0], item[0][1].value, str(item[0][2])))
            if len(targets) > 1
        )
        unsupported = tuple(sorted(node_id for node_id in paths if self.nodes[node_id].node_type == NodeType.PRESERVED_UNKNOWN_ASSET))
        return ReachabilityResult(tuple(sorted(paths)), paths, proof_edges, proof_relations, unsupported, ambiguous)
