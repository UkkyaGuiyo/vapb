"""Metadata-only extraction of VRC PhysBone-shaped Unity components.

The parser keeps the original MonoBehaviour payload alongside a small semantic
view.  It deliberately identifies the serialized schema, not a product name or
script GUID, so unknown future SDK fields remain round-trip evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .prefab_parser import PrefabData, ref_file_id


_PHYSBONE_KEYS = {"pull", "spring", "stiffness", "gravity", "colliders", "limitType"}
# SDK serializations use ``shapeType``.  ``shape`` is retained as a fixture
# compatibility alias because older/synthetic YAML may use that spelling.
_COLLIDER_KEYS = {"insideBounds", "position", "rotation"}
_PARAMETER_KEYS = {
    "version", "integrationType", "endpointPosition", "ignoreTransforms",
    "ignoreOtherPhysBones", "multiChildType", "pull", "pullCurve", "spring",
    "springCurve", "stiffness", "stiffnessCurve", "gravity", "gravityCurve",
    "gravityFalloff", "gravityFalloffCurve", "immobileType", "immobile",
    "immobileCurve", "allowCollision", "collisionFilter", "radius", "radiusCurve",
    "limitType", "maxAngleX", "maxAngleXCurve", "maxAngleZ", "maxAngleZCurve",
    "limitRotation", "limitRotationXCurve", "limitRotationYCurve", "limitRotationZCurve",
    "maxStretch", "maxStretchCurve", "colliders", "ignoreTransforms",
}


@dataclass(frozen=True)
class PhysBoneSource:
    component_file_id: str
    owner_game_object_file_id: str
    root_transform_file_id: str
    root_game_object_file_id: str
    root_hierarchy_path: str
    script_guid: str
    script_file_id: str
    parameters: dict[str, Any]
    collider_file_ids: tuple[str, ...]
    raw_payload: str


@dataclass(frozen=True)
class PhysBoneColliderSource:
    component_file_id: str
    owner_game_object_file_id: str
    script_guid: str
    script_file_id: str
    parameters: dict[str, Any]
    raw_payload: str


@dataclass(frozen=True)
class PhysBoneSnapshot:
    physbones: tuple[PhysBoneSource, ...]
    colliders: tuple[PhysBoneColliderSource, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "physbones": [source.__dict__ for source in self.physbones],
            "colliders": [source.__dict__ for source in self.colliders],
        }


def _script_identity(data: dict[str, Any]) -> tuple[str, str]:
    script = data.get("m_Script")
    if not isinstance(script, dict):
        return "", ""
    return str(script.get("guid") or "").lower(), str(script.get("fileID") or "")


def _hierarchy(prefab: PrefabData) -> tuple[dict[int, Any], dict[int, int | None]]:
    transform_by_go = {item.game_object_id: item for item in prefab.transforms.values()}
    transform_to_go = {item.file_id: item.game_object_id for item in prefab.transforms.values()}
    return transform_by_go, transform_to_go


def _root_identity(prefab: PrefabData, owner_id: int, root_transform_id: int | None) -> tuple[str, str, str]:
    transform_by_go, transform_to_go = _hierarchy(prefab)
    root_transform_id = root_transform_id or next(
        (item.file_id for item in prefab.transforms.values() if item.game_object_id == owner_id),
        None,
    )
    root_go = transform_to_go.get(root_transform_id) if root_transform_id is not None else owner_id
    root_go = root_go or owner_id
    names: list[str] = []
    current = root_go
    visited: set[int] = set()
    while current is not None and current not in visited:
        visited.add(current)
        game_object = prefab.game_objects.get(current)
        if game_object is not None:
            names.append(game_object.name)
        transform = transform_by_go.get(current)
        if transform is None:
            break
        current = transform_to_go.get(transform.parent_id)
    names.reverse()
    return str(root_transform_id or 0), str(root_go), "/".join(names)


def _is_physbone(data: dict[str, Any]) -> bool:
    return _PHYSBONE_KEYS.issubset(data.keys()) or {
        "pull", "spring", "stiffness", "gravity"
    }.issubset(data.keys())


def _is_collider(data: dict[str, Any]) -> bool:
    return (
        _COLLIDER_KEYS.issubset(data.keys())
        and ("shapeType" in data or "shape" in data)
        and "radius" in data
    )


def extract_physbone_snapshot(prefab: PrefabData) -> PhysBoneSnapshot:
    physbones: list[PhysBoneSource] = []
    colliders: list[PhysBoneColliderSource] = []
    for document in prefab.documents:
        if document.class_id != 114:
            continue
        data = document.data
        script_guid, script_file_id = _script_identity(data)
        owner = ref_file_id(data.get("m_GameObject")) or 0
        root_transform = ref_file_id(data.get("rootTransform"))
        if _is_physbone(data):
            root_transform_id, root_go_id, root_path = _root_identity(prefab, owner, root_transform)
            colliders_value = data.get("colliders")
            collider_ids = tuple(
                str(ref_file_id(item)).strip()
                for item in (colliders_value if isinstance(colliders_value, list) else [])
                if ref_file_id(item) is not None
            )
            physbones.append(PhysBoneSource(
                component_file_id=str(document.file_id),
                owner_game_object_file_id=str(owner),
                root_transform_file_id=root_transform_id,
                root_game_object_file_id=root_go_id,
                root_hierarchy_path=root_path,
                script_guid=script_guid,
                script_file_id=script_file_id,
                parameters={key: data[key] for key in _PARAMETER_KEYS if key in data},
                collider_file_ids=collider_ids,
                raw_payload=document.raw,
            ))
        elif _is_collider(data):
            colliders.append(PhysBoneColliderSource(
                component_file_id=str(document.file_id),
                owner_game_object_file_id=str(owner),
                script_guid=script_guid,
                script_file_id=script_file_id,
                parameters={key: value for key, value in data.items() if key not in {"m_GameObject", "m_Script"}},
                raw_payload=document.raw,
            ))
    return PhysBoneSnapshot(tuple(physbones), tuple(colliders))


__all__ = ["PhysBoneSource", "PhysBoneColliderSource", "PhysBoneSnapshot", "extract_physbone_snapshot"]
