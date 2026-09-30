"""Apply prefab object relationships and Unity local transforms."""

from __future__ import annotations

import re
import json
from typing import Iterable

import bpy  # type: ignore
from mathutils import Matrix, Quaternion, Vector  # type: ignore

from ..unity.prefab_parser import PrefabData, ref_file_id, ref_guid
from ..unity.prefab_instance_transform import resolve_instance_transform, has_complete_transform


def _realize_renderer_free_instances(prefab, mapping, package_id, context_id,
                                     source_loader, collection, issues):
    """Expand directly serialized transform-only source trees per exact instance.

    Renderer/model instances keep their existing realization route. Ambiguous,
    removed/added, deeper nested or modified descendant trees remain unresolved.
    """
    transforms = {t.file_id: t for t in prefab.transforms.values()}
    for instance in prefab.documents:
        if instance.class_id != 1001:
            continue
        guid = ref_guid(instance.data.get('m_SourcePrefab'))
        source = source_loader(package_id, guid) if guid else None
        candidates = list(source) if isinstance(source, (list, tuple)) else ([] if source is None else [source])
        if len(candidates) != 1 or candidates[0].prefab is None:
            continue  # Existing projection reports source ambiguity/unavailability.
        source = candidates[0]
        child = source.prefab
        if child.renderer_documents():
            continue
        modification = instance.data.get('m_Modification') or {}
        parent_id = ref_file_id(modification.get('m_TransformParent'))
        parent = mapping.get(transforms[parent_id].game_object_id) if parent_id in transforms else None
        effective = resolve_instance_transform(prefab, instance.file_id, child)
        allowed = all((m.property_path == 'm_Name' and m.target_guid == child.asset_guid
                       and m.target_file_id in child.game_objects) or
                      (m.target_file_id == (effective.source_transform_id if effective else None)
                       and m.target_guid == child.asset_guid
                       and m.property_path.startswith(('m_LocalPosition.', 'm_LocalRotation.', 'm_LocalScale.',
                                                       'm_LocalEulerAnglesHint.')))
                      for m in prefab.modifications() if m.prefab_instance_file_id == instance.file_id)
        transform_ids = {t.file_id for t in child.transforms.values()}
        complete = (len(child.transforms) == len(child.game_objects)
                    and {t.game_object_id for t in child.transforms.values()} == set(child.game_objects)
                    and all(t.game_object_id in child.game_objects
                            and t.parent_id in transform_ids | {0, None}
                            and has_complete_transform(child, t.file_id)
                            for t in child.transforms.values())
                    and all(set(go.component_ids) <= transform_ids for go in child.game_objects.values()))
        structural_change = any(modification.get(k) for k in ('m_RemovedComponents', 'm_RemovedGameObjects',
                                                               'm_AddedComponents', 'm_AddedGameObjects'))
        if (not context_id or child.asset_guid != guid or source.package_id != package_id
                or parent is None or not has_complete_transform(prefab, parent_id)
                or effective is None or not allowed or not complete
                or structural_change or any(d.class_id == 1001 for d in child.documents)):
            issues.append({'code': 'RENDERER_FREE_HIERARCHY_UNRESOLVED',
                           'root_context_id': context_id, 'prefab_instance_file_id': instance.file_id})
            continue
        edge = [{'container_package_id': package_id, 'container_asset_guid': prefab.asset_guid,
                 'prefab_instance_file_id': instance.file_id, 'source_package_id': source.package_id,
                 'source_prefab_guid': guid}]
        edge_json = json.dumps(edge, sort_keys=True)
        nodes = {}
        for transform in child.transforms.values():
            go = child.game_objects[transform.game_object_id]
            labels = [m.value for m in prefab.modifications()
                      if m.prefab_instance_file_id == instance.file_id
                      and m.target_guid == guid and m.target_file_id == go.file_id
                      and m.property_path == 'm_Name']
            obj = bpy.data.objects.new(str(labels[0]) if len(labels) == 1 else go.name, None)
            collection.objects.link(obj)
            obj['unity_source_package_id'] = source.package_id
            obj['unity_source_prefab_guid'] = guid
            obj['unity_prefab_file_id'] = str(go.file_id)
            obj['_vapb_source_local_file_id'] = str(go.file_id)
            obj['_vapb_source_transform_file_id'] = str(transform.file_id)
            obj['_vapb_root_context_id'] = context_id
            obj['_vapb_model_instance_edge_path'] = edge_json
            obj['_vapb_semantic_id'] = f'v1:{source.package_id}:{guid}:{go.file_id}:{context_id}:{edge_json}'
            nodes[transform.file_id] = obj
        for transform in child.transforms.values():
            obj = nodes[transform.file_id]
            obj.parent = nodes.get(transform.parent_id, parent)
            apply_transform(obj, effective if transform.file_id == effective.source_transform_id else transform)


# Match native FBX import: Unity is left-handed Y-up, Blender is right-handed
# Z-up. The asymmetric cross-runtime fixture verifies (-x, -z, y).
_UNITY_TO_BLENDER = Matrix(((-1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
_BLENDER_DUPLICATE_SUFFIX = re.compile(r"\.\d{3}$")


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
    obj.scale = (transform.scale["x"], transform.scale["z"], transform.scale["y"])


def build_prefab_hierarchy(
    prefab: PrefabData,
    imported_objects: Iterable[bpy.types.Object],
    source_package_id: str = "",
    source_prefab_unity_path: str = "",
    target_collection=None,
    source_loader=None,
    root_context_id='',
    semantic_issues=None,
):
    imported = list(imported_objects)
    bpy.context.view_layer.update()
    native_world = {obj: obj.matrix_world.copy() for obj in imported}
    native_parent = {obj: obj.parent for obj in imported}
    collection = target_collection or bpy.context.scene.collection
    root = bpy.data.objects.new(prefab.display_name, None)
    collection.objects.link(root)
    root.empty_display_size = 0.03
    root["unity_source_prefab"] = str(prefab.path)
    if source_prefab_unity_path:
        root["unity_asset_path"] = str(source_prefab_unity_path).replace("\\", "/")
    if source_package_id:
        root["unity_source_package_id"] = source_package_id
    used: set[int] = set()
    game_object_map: dict[int, bpy.types.Object] = {}
    for game_object_id, game_object in prefab.game_objects.items():
        semantic_candidates = [
            candidate for candidate in imported
            if str(candidate.get("unity_prefab_file_id", "")) == str(game_object_id)
        ]
        candidates = [candidate for candidate in semantic_candidates if candidate.as_pointer() not in used]
        mapping_confidence = "SEMANTIC_ID" if len(candidates) == 1 else "UNKNOWN"
        obj = candidates[0] if len(candidates) == 1 else None
        if obj is not None:
            used.add(obj.as_pointer())
            obj["_vapb_mapping_confidence"] = mapping_confidence
            game_object_map[game_object_id] = obj
    transform_by_go = {t.game_object_id: t for t in prefab.transforms.values()}
    transform_to_game_object = {t.file_id: t.game_object_id for t in prefab.transforms.values()}

    def parent_go(game_object_id):
        transform = transform_by_go.get(game_object_id)
        return transform_to_game_object.get(transform.parent_id) if transform else None

    def source_hierarchy_path(game_object_id):
        names = []
        current = game_object_id
        visited = set()
        while current is not None and current not in visited:
            visited.add(current)
            game_object = prefab.game_objects.get(current)
            if game_object is not None:
                names.append(game_object.name)
            current = parent_go(current)
        names.reverse()
        return "/".join(names)

    # Bones already exist inside the native armature. Collapse only a unique,
    # structurally matching bone hierarchy in that specific model instance.
    bone_candidates = {}
    for go_id, go in prefab.game_objects.items():
        if go_id in game_object_map:
            continue
        ancestor = parent_go(go_id)
        visited = {go_id}
        while ancestor is not None and ancestor not in visited:
            visited.add(ancestor)
            armature = game_object_map.get(ancestor)
            if armature is not None and armature.type == "ARMATURE":
                bone = armature.data.bones.get(go.name)
                if bone is not None:
                    bone_candidates[go_id] = (ancestor, armature, bone)
                break
            ancestor = parent_go(ancestor)
    counts = {}
    for _, armature, bone in bone_candidates.values():
        key = (armature.as_pointer(), bone.name)
        counts[key] = counts.get(key, 0) + 1
    bone_map = {}

    def matching_bone(go_id, visiting):
        if go_id in bone_map:
            return True
        if go_id in visiting or go_id not in bone_candidates:
            return False
        armature_id, armature, bone = bone_candidates[go_id]
        if counts[(armature.as_pointer(), bone.name)] != 1:
            return False
        parent_id = parent_go(go_id)
        if bone.parent is None:
            valid = parent_id == armature_id
        else:
            valid = (parent_id in bone_candidates
                     and bone_candidates[parent_id][1] == armature
                     and bone_candidates[parent_id][2] == bone.parent
                     and matching_bone(parent_id, visiting | {go_id}))
        if valid:
            bone_map[go_id] = (armature, bone)
        return valid

    for go_id in bone_candidates:
        matching_bone(go_id, set())
    # Do not collapse a bone that is needed as an Object parent for a scene
    # attachment: preserve that attachment's original representation instead.
    retained = {parent_go(go_id) for go_id in prefab.game_objects
                if go_id not in bone_map}
    while retained:
        go_id = retained.pop()
        if go_id in bone_map:
            del bone_map[go_id]
            retained.add(parent_go(go_id))
    bone_identities = {}
    for game_object_id, game_object in prefab.game_objects.items():
        if game_object_id in bone_map:
            armature, bone = bone_map[game_object_id]
            transform = transform_by_go.get(game_object_id)
            bone_identities[str(game_object_id)] = {
                "armature_file_id": str(bone_candidates[game_object_id][0]),
                "bone_name": bone.name, "transform_file_id": str(transform.file_id),
                "parent_transform_id": str(transform.parent_id),
                "position": transform.position, "rotation": transform.rotation,
                "scale": transform.scale,
            }
            obj = bone
        else:
            obj = game_object_map.get(game_object_id)
            if obj is None:
                obj = bpy.data.objects.new(game_object.name, None)
                collection.objects.link(obj)
                obj.empty_display_size = 0.02
                game_object_map[game_object_id] = obj
        # Unity fileIDs are identifiers, not numeric values for Blender.
        # Some Unity assets use values outside Blender 4.2 IDProperty's
        # signed C-int range, so preserve the lossless decimal form as text.
        obj["unity_prefab_file_id"] = str(game_object_id)
        if source_prefab_unity_path:
            obj["unity_asset_path"] = str(source_prefab_unity_path).replace("\\", "/")
        if source_package_id:
            obj["unity_source_package_id"] = source_package_id
        semantic_source = source_package_id or "UNSCOPED"
        semantic_path = str(source_prefab_unity_path).replace("\\", "/")
        obj["_vapb_semantic_id"] = f"v1:{semantic_source}:{semantic_path}:{game_object_id}"
        obj["_vapb_source_local_file_id"] = str(game_object_id)
        obj["_vapb_source_hierarchy_path"] = source_hierarchy_path(game_object_id)
    root["unity_prefab_bone_identities"] = json.dumps(bone_identities, sort_keys=True)
    # Mapped FBX TRS may include genuine instance overrides, but without a
    # source/default comparison they cannot be separated from model-import
    # conversion. Preserve them as evidence; do NOT apply them a second time.
    for transform in prefab.transforms.values():
        obj = game_object_map.get(transform.game_object_id)
        if obj is None:
            continue
        if obj in native_world:
            obj["unity_prefab_model_transform"] = json.dumps({
                "position": transform.position, "rotation": transform.rotation,
                "scale": transform.scale, "parent_transform_id": str(transform.parent_id),
            }, sort_keys=True)
            continue
        parent_game_object_id = transform_to_game_object.get(transform.parent_id)
        obj.parent = game_object_map.get(parent_game_object_id, root)
        apply_transform(obj, transform)
    native_go = {obj: go_id for go_id, obj in game_object_map.items() if obj in native_world}

    def scene_placement(go_id):
        ancestor = parent_go(go_id)
        visited = {go_id}
        placement = root
        while ancestor is not None and ancestor not in visited:
            visited.add(ancestor)
            candidate = game_object_map.get(ancestor)
            if candidate is not None and candidate not in native_world:
                placement = candidate
                break
            ancestor = parent_go(ancestor)
        return placement

    for obj in imported:
        if native_parent[obj] in native_world:
            continue
        placement = scene_placement(native_go.get(obj))
        if obj not in native_go:
            placements = set()
            for member, go_id in native_go.items():
                ancestor = member
                visited = set()
                while ancestor in native_parent and ancestor not in visited:
                    if ancestor == obj:
                        placements.add(scene_placement(go_id))
                        break
                    visited.add(ancestor)
                    ancestor = native_parent[ancestor]
            if len(placements) == 1:
                placement = placements.pop()
        obj.parent = placement
        obj.matrix_parent_inverse = Matrix.Identity(4)
        # Native root world is now local to the scene-only placement. The
        # placement therefore acts exactly once on the entire native model.
        obj.matrix_basis = native_world[obj]
    if source_loader is not None:
        _realize_renderer_free_instances(prefab, game_object_map, source_package_id,
                                        root_context_id, source_loader, collection,
                                        semantic_issues if semantic_issues is not None else [])
    return root, game_object_map
