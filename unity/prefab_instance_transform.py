"""Resolve a PrefabInstance root Transform from exact source defaults and overrides."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .prefab_parser import PrefabData, ref_guid


_FIELDS = {"m_LocalPosition": ("x", "y", "z"),
           "m_LocalRotation": ("x", "y", "z", "w"),
           "m_LocalScale": ("x", "y", "z")}
_PROPERTY = {f"{name}.{axis}": (name, axis)
             for name, axes in _FIELDS.items() for axis in axes}


@dataclass(frozen=True)
class EffectiveInstanceTransform:
    source_transform_id: int
    position: dict[str, float]
    rotation: dict[str, float]
    scale: dict[str, float]


def _complete_trs(prefab: PrefabData, transform_id: int):
    documents = [doc for doc in prefab.documents
                 if doc.class_id == 4 and doc.file_id == transform_id]
    if len(documents) != 1:
        return None
    values = {}
    try:
        for name, axes in _FIELDS.items():
            raw = documents[0].data[name]
            if not isinstance(raw, dict) or not all(axis in raw for axis in axes):
                return None
            values[name] = {axis: float(raw[axis]) for axis in axes}
            if not all(math.isfinite(value) for value in values[name].values()):
                return None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return values


def has_complete_transform(prefab: PrefabData, transform_id: int) -> bool:
    """Require readable local TRS for a semantic parent and all its ancestors."""
    current, visited = transform_id, set()
    while current not in (None, 0):
        if current in visited or current not in prefab.transforms or _complete_trs(prefab, current) is None:
            return False
        visited.add(current)
        current = prefab.transforms[current].parent_id
    return True


def resolve_instance_transform(container: PrefabData, instance_id: int,
                               source: PrefabData) -> EffectiveInstanceTransform | None:
    """Return exact root-local TRS, or None when any required identity/value is unknown."""
    instances = [doc for doc in container.documents
                 if doc.class_id == 1001 and doc.file_id == instance_id]
    roots = [transform for transform in source.transforms.values()
             if transform.parent_id in (None, 0)
             and transform.game_object_id in source.game_objects]
    if len(instances) != 1 or len(roots) != 1 or not source.asset_guid:
        return None
    instance, root = instances[0], roots[0]
    if ref_guid(instance.data.get("m_SourcePrefab")) != source.asset_guid:
        return None
    values = _complete_trs(source, root.file_id)
    if values is None:
        return None
    try:
        parsed = [item for item in container.modifications()
                  if item.prefab_instance_file_id == instance_id
                  and item.property_path.startswith(("m_LocalPosition.",
                                                      "m_LocalRotation.", "m_LocalScale."))]
        raw_paths = re.findall(
            r"(?m)^\s*propertyPath:\s*(m_Local(?:Position|Rotation|Scale)\.[A-Za-z]+)\s*$",
            instance.raw)
        if len(parsed) != len(raw_paths):
            return None
        seen = set()
        for item in parsed:
            field = _PROPERTY.get(item.property_path)
            if field is None:
                return None
            if item.target_file_id == root.file_id and item.target_guid != source.asset_guid:
                return None
            if item.target_guid != source.asset_guid or item.target_file_id != root.file_id:
                continue  # Descendant Transform modification is a different layer.
            if item.property_path in seen or item.object_reference not in (None, {"fileID": 0}):
                return None
            seen.add(item.property_path)
            number = float(item.value)
            if not math.isfinite(number):
                return None
            values[field[0]][field[1]] = number
        quaternion = values["m_LocalRotation"]
        norm = sum(value * value for value in quaternion.values())
        if abs(norm - 1.0) > 1e-4:
            return None  # Do not invent a normalization rule for an unproven override.
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None
    return EffectiveInstanceTransform(root.file_id, values["m_LocalPosition"],
                                      values["m_LocalRotation"], values["m_LocalScale"])
