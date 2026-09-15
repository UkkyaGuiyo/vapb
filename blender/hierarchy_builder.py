"""Apply prefab object relationships and Unity local transforms."""

from __future__ import annotations

from typing import Iterable

import bpy  # type: ignore
from mathutils import Matrix, Quaternion, Vector  # type: ignore

from ..unity.prefab_parser import PrefabData


_UNITY_TO_BLENDER = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)))


def unity_position(value: dict[str, float]):
    source = Vector((value.get("x", 0.0), value.get("y", 0.0), value.get("z", 0.0)))
    return (_UNITY_TO_BLENDER @ source).to_tuple()


def unity_rotation(value: dict[str, float]) -> Quaternion:
    source = Quaternion((value.get("w", 1.0), value.get("x", 0.0), value.get("y", 0.0), value.get("z", 0.0)))
    return (_UNITY_TO_BLENDER @ source.to_matrix() @ _UNITY_TO_BLENDER.inverted()).to_quaternion()


def apply_transform(obj, transform) -> None:
    obj.location = unity_position(transform.position)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = unity_rotation(transform.rotation)
    obj.scale = (transform.scale["x"], transform.scale["y"], transform.scale["z"])


def build_prefab_hierarchy(
    prefab: PrefabData,
    imported_objects: Iterable[bpy.types.Object],
    source_package_id: str = "",
    source_prefab_unity_path: str = "",
):
    imported = list(imported_objects)
    root = bpy.data.objects.new(prefab.display_name, None)
    bpy.context.scene.collection.objects.link(root)
    root["unity_source_prefab"] = str(prefab.path)
    if source_prefab_unity_path:
        root["unity_asset_path"] = str(source_prefab_unity_path).replace("\\", "/")
    if source_package_id:
        root["unity_source_package_id"] = source_package_id
    by_name: dict[str, list[bpy.types.Object]] = {}
    for obj in imported:
        by_name.setdefault(obj.name.casefold(), []).append(obj)
    used: set[int] = set()
    game_object_map: dict[int, bpy.types.Object] = {}
    for game_object_id, game_object in prefab.game_objects.items():
        candidates = by_name.get(game_object.name.casefold(), [])
        obj = next((candidate for candidate in candidates if candidate.as_pointer() not in used), None)
        if obj is None:
            obj = bpy.data.objects.new(game_object.name, None)
            bpy.context.scene.collection.objects.link(obj)
        used.add(obj.as_pointer())
        # Unity fileIDs are identifiers, not numeric values for Blender.
        # Some Unity assets use values outside Blender 4.2 IDProperty's
        # signed C-int range, so preserve the lossless decimal form as text.
        obj["unity_prefab_file_id"] = str(game_object_id)
        if source_prefab_unity_path:
            obj["unity_asset_path"] = str(source_prefab_unity_path).replace("\\", "/")
        if source_package_id:
            obj["unity_source_package_id"] = source_package_id
        game_object_map[game_object_id] = obj
    transform_to_game_object = {
        transform_id: transform.game_object_id
        for transform_id, transform in prefab.transforms.items()
        if transform.game_object_id is not None
    }
    for transform in prefab.transforms.values():
        obj = game_object_map.get(transform.game_object_id)
        if obj is None:
            continue
        parent_game_object_id = transform_to_game_object.get(transform.parent_id)
        obj.parent = game_object_map.get(parent_game_object_id, root)
        apply_transform(obj, transform)
    for obj in imported:
        if obj.parent is None:
            obj.parent = root
    return root, game_object_map
