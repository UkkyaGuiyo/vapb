"""Conservative, explicit cleanup of selected Blender objects.

This module never infers a Unity identity from a Blender name. Names below
address native vertex groups and edit bones; source identities are retained
only as deletion delta when already present on the native data.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
from typing import Any, Iterable


def bone_retention(parents: dict[str, str | None], references: dict[str, set[str]],
                   unknown: set[str] | None = None) -> dict[str, tuple[str, ...]]:
    """Return reasons to keep each bone; malformed parent graphs fail closed."""
    result = {name: set(unknown or ()) | set(references.get(name, ())) for name in parents}
    if set(references) - set(parents):
        raise ValueError('unknown referenced bone')
    state: dict[str, int] = {}

    def visit(name: str) -> None:
        if state.get(name) == 1:
            raise ValueError('cyclic bone parent graph')
        if state.get(name) == 2:
            return
        state[name] = 1
        parent = parents[name]
        if parent is not None:
            if parent not in parents:
                raise ValueError('missing bone parent')
            visit(parent)
        state[name] = 2

    for name in parents:
        visit(name)
    for name in parents:
        if not result[name]:
            continue
        parent = parents[name]
        while parent is not None:
            result[parent].add('USED_DESCENDANT')
            parent = parents[parent]
    return {name: tuple(sorted(reasons)) for name, reasons in result.items()}


def slot_retention(count: int, polygon_slots: set[int], references: dict[int, set[str]],
                   unknown: set[str] | None = None) -> dict[int, tuple[str, ...]]:
    """Return reasons to keep slots, based on geometry and explicit references."""
    if count < 0 or any(index < 0 or index >= count for index in polygon_slots | set(references)):
        raise ValueError('invalid material slot index')
    return {
        index: tuple(sorted(set(unknown or ()) | set(references.get(index, ())) |
                            ({'POLYGON'} if index in polygon_slots else set())))
        for index in range(count)
    }


@dataclass(frozen=True)
class Decision:
    kind: str
    owner: Any
    key: str
    reasons: tuple[str, ...]
    source_identity: str = ''

    @property
    def candidate(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class CleanupPlan:
    scope: tuple[Any, ...]
    decisions: tuple[Decision, ...]
    materials: bool = True
    bones: bool = True

    @property
    def candidates(self) -> tuple[Decision, ...]:
        return tuple(item for item in self.decisions if item.candidate)

    def fingerprint(self) -> str:
        rows = [(item.kind, item.owner.as_pointer(), item.key, item.reasons,
                 item.source_identity) for item in self.decisions]
        return hashlib.sha256(repr(rows).encode('utf-8')).hexdigest()


def _custom_state(block: Any) -> bool:
    try:
        return any(str(key) not in {'_RNA_UI', '_vapb_semantic_cleanup_delta'}
                   for key in block.keys())
    except (AttributeError, TypeError):
        return False


def _external_object(obj: Any) -> bool:
    data = getattr(obj, 'data', None)
    return bool(obj.library or obj.override_library or (data and data.library) or
                (data and data.override_library) or len(obj.users_scene) != 1 or
                (data is not None and data.users != 1))


def _animation(block: Any) -> bool:
    return getattr(block, 'animation_data', None) is not None


def _ancestor_custom_state(obj: Any) -> bool:
    parent = obj.parent
    while parent is not None:
        if _custom_state(parent) or _custom_state(getattr(parent, 'data', None)):
            return True
        parent = parent.parent
    return False


def _mesh_decisions(obj: Any, opaque_source_state: bool) -> list[Decision]:
    slots = obj.material_slots
    count = len(slots)
    if count == 0:
        return []
    unknown: set[str] = set()
    if _external_object(obj):
        unknown.add('SHARED_OR_LINKED_DATA')
    if _custom_state(obj) or _custom_state(obj.data) or _ancestor_custom_state(obj):
        unknown.add('UNITY_VRC_STATE_UNRESOLVED')
    if opaque_source_state:
        unknown.add('EXTERNAL_SOURCE_REFERENCE_UNRESOLVED')
    if _animation(obj) or _animation(obj.data) or _animation(getattr(obj.data, 'shape_keys', None)):
        unknown.add('ANIMATION_UNRESOLVED')
    if any(modifier.type not in {'ARMATURE'} for modifier in obj.modifiers):
        unknown.add('MODIFIER_UNRESOLVED')
    if any(slot.link != 'DATA' for slot in slots):
        unknown.add('OBJECT_MATERIAL_LINK')
    used = {polygon.material_index for polygon in obj.data.polygons}
    references: dict[int, set[str]] = {}
    for index, slot in enumerate(slots):
        if slot.material is not None and (_animation(slot.material) or _custom_state(slot.material)):
            references.setdefault(index, set()).add('MATERIAL_STATE')
    try:
        keep = slot_retention(count, used, references, unknown)
    except ValueError:
        keep = slot_retention(count, set(), {}, {'POLYGON_INDEX_INVALID'})
    return [Decision('MATERIAL_SLOT', obj, str(index), keep[index],
                     str(slot.material.get('unity_material_guid', '')) if slot.material else '')
            for index, slot in enumerate(slots)]


def _associated_with_rig(obj: Any, rig: Any) -> bool:
    if obj.parent == rig:
        return True
    return any(modifier.type == 'ARMATURE' and modifier.object == rig for modifier in obj.modifiers)


def _rig_decisions(rig: Any, selected: set[Any], all_objects: Iterable[Any],
                   opaque_source_state: bool) -> list[Decision]:
    bones = rig.data.bones
    parents = {bone.name: bone.parent.name if bone.parent else None for bone in bones}
    children = {parent for parent in parents.values() if parent is not None}
    references: dict[str, set[str]] = {name: set() for name in parents}
    unknown: set[str] = set()
    if _external_object(rig):
        unknown.add('SHARED_OR_LINKED_DATA')
    if _custom_state(rig) or _custom_state(rig.data) or _ancestor_custom_state(rig):
        unknown.add('UNITY_VRC_STATE_UNRESOLVED')
    if opaque_source_state:
        unknown.add('EXTERNAL_SOURCE_REFERENCE_UNRESOLVED')
    if _animation(rig) or _animation(rig.data):
        unknown.add('ANIMATION_UNRESOLVED')
    if rig.modifiers:
        unknown.add('MODIFIER_UNRESOLVED')
    for bone in bones:
        if _custom_state(bone):
            references[bone.name].add('BONE_SOURCE_STATE')
    for pose_bone in rig.pose.bones:
        if _custom_state(pose_bone):
            references[pose_bone.name].add('BONE_SOURCE_STATE')
        if pose_bone.constraints:
            references[pose_bone.name].add('CONSTRAINT_OWNER')
        for constraint in pose_bone.constraints:
            target = getattr(constraint, 'target', None)
            subtarget = getattr(constraint, 'subtarget', '')
            if target == rig and subtarget in references:
                references[subtarget].add('CONSTRAINT_TARGET')
            elif target is not None or subtarget:
                unknown.add('CONSTRAINT_UNRESOLVED')
    for obj in all_objects:
        if obj == rig:
            continue
        if obj.type == 'ARMATURE':
            for external_pose_bone in obj.pose.bones:
                for constraint in external_pose_bone.constraints:
                    if getattr(constraint, 'target', None) != rig:
                        continue
                    subtarget = getattr(constraint, 'subtarget', '')
                    if subtarget in references:
                        references[subtarget].add('EXTERNAL_CONSTRAINT_TARGET')
                    else:
                        unknown.add('CONSTRAINT_UNRESOLVED')
        animation_data = getattr(obj, 'animation_data', None)
        if animation_data is not None:
            for driver in animation_data.drivers:
                for variable in driver.driver.variables:
                    if any(target.id == rig for target in variable.targets):
                        unknown.add('EXTERNAL_DRIVER_UNRESOLVED')
        if obj.parent == rig and obj.parent_type == 'BONE':
            if obj.parent_bone in references:
                references[obj.parent_bone].add('BONE_PARENT')
            else:
                unknown.add('BONE_PARENT_UNRESOLVED')
        for constraint in obj.constraints:
            target = getattr(constraint, 'target', None)
            subtarget = getattr(constraint, 'subtarget', '')
            if target == rig and subtarget in references:
                references[subtarget].add('CONSTRAINT_TARGET')
            elif target == rig:
                unknown.add('CONSTRAINT_UNRESOLVED')
        if not _associated_with_rig(obj, rig):
            continue
        if obj not in selected or obj.type != 'MESH' or _external_object(obj):
            unknown.add('EXTERNAL_OR_SHARED_RIG_USER')
            continue
        if _custom_state(obj) or _custom_state(obj.data):
            unknown.add('UNITY_VRC_STATE_UNRESOLVED')
        if _animation(obj) or _animation(obj.data) or _animation(getattr(obj.data, 'shape_keys', None)):
            unknown.add('ANIMATION_UNRESOLVED')
        if any(modifier.type not in {'ARMATURE'} for modifier in obj.modifiers):
            unknown.add('MODIFIER_UNRESOLVED')
        if any(modifier.type == 'ARMATURE' and modifier.object == rig and modifier.use_bone_envelopes
               for modifier in obj.modifiers):
            unknown.add('ENVELOPE_DEFORMATION_UNRESOLVED')
        for group in obj.vertex_groups:
            if group.name not in references:
                continue
            if any(group.index == assignment.group and assignment.weight > 0
                   for vertex in obj.data.vertices for assignment in vertex.groups):
                references[group.name].add('WEIGHT')
    keep = bone_retention(parents, references, unknown)
    return [Decision('BONE', rig, bone.name,
                     keep[bone.name] or (('CHILD_BONE_PRESENT',) if bone.name in children else ()),
                     str(bone.get('_vapb_fbx_model_uid', '')))
            for bone in bones]


def analyze_cleanup(objects: Iterable[Any], *, materials: bool = True, bones: bool = True,
                    all_objects: Iterable[Any] | None = None) -> CleanupPlan:
    """Read-only plan for an explicit selection, including other-object guards."""
    scope = tuple(dict.fromkeys(objects))
    if not scope:
        raise ValueError('select cleanup objects')
    if any(obj.type not in {'MESH', 'ARMATURE'} for obj in scope):
        raise ValueError('only Mesh and Armature selections are supported')
    import bpy  # type: ignore
    all_objects = tuple(all_objects) if all_objects is not None else tuple(bpy.data.objects)
    selected = set(scope)
    opaque_source_state = any(_custom_state(obj) or _custom_state(getattr(obj, 'data', None))
                              for obj in all_objects if obj not in selected)
    decisions: list[Decision] = []
    if materials:
        for obj in scope:
            if obj.type == 'MESH':
                decisions.extend(_mesh_decisions(obj, opaque_source_state))
    if bones:
        for obj in scope:
            if obj.type == 'ARMATURE':
                decisions.extend(_rig_decisions(obj, selected, all_objects, opaque_source_state))
    return CleanupPlan(scope, tuple(decisions), materials, bones)


def _delta_entries(plan: CleanupPlan) -> dict[Any, list[dict[str, str]]]:
    result: dict[Any, list[dict[str, str]]] = {}
    for decision in plan.candidates:
        result.setdefault(decision.owner, []).append({
            'kind': decision.kind,
            'local_key': decision.key,
            'source_identity': decision.source_identity,
        })
    return result


def apply_cleanup(context: Any, plan: CleanupPlan, *, _staged: bool = False) -> int:
    """Clone affected datablocks, then commit; restore pointers on any failure."""
    if context.mode != 'OBJECT':
        raise ValueError('Object mode is required')
    import bpy  # type: ignore
    if not _staged:
        current = analyze_cleanup(plan.scope, materials=plan.materials, bones=plan.bones,
                                  all_objects=tuple(bpy.data.objects))
        if current.fingerprint() != plan.fingerprint():
            raise ValueError('cleanup preview is stale')
    candidates = plan.candidates
    if not candidates:
        return 0
    owners = tuple(dict.fromkeys(item.owner for item in candidates))
    original_data = {owner: owner.data for owner in owners}
    original_deltas = {owner: owner.get('_vapb_semantic_cleanup_delta') for owner in owners}
    original_material_slots = {owner: tuple(owner.data.materials)
                               for owner in owners if owner.type == 'MESH'}
    original_polygon_slots = {owner: tuple(polygon.material_index for polygon in owner.data.polygons)
                              for owner in owners if owner.type == 'MESH'}
    clones: dict[Any, Any] = {}
    active = context.view_layer.objects.active
    try:
        if not _staged:
            for owner in owners:
                clones[owner] = owner.data.copy()
            for owner in owners:
                owner.data = clones[owner]
        for owner in owners:
            items = [item for item in candidates if item.owner == owner]
            if owner.type == 'MESH':
                removed = sorted(int(item.key) for item in items)
                for index in reversed(removed):
                    owner.data.materials.pop(index=index)
                for polygon, old_index in zip(owner.data.polygons, original_polygon_slots[owner]):
                    polygon.material_index = old_index - sum(index < old_index for index in removed)
                for polygon, old_index in zip(owner.data.polygons, original_polygon_slots[owner]):
                    expected = original_material_slots[owner][old_index]
                    actual = owner.data.materials[polygon.material_index]
                    if actual != expected:
                        raise RuntimeError('material assignment changed during cleanup')
            elif owner.type == 'ARMATURE':
                context.view_layer.objects.active = owner
                with context.temp_override(object=owner, active_object=owner,
                                           selected_objects=[owner], selected_editable_objects=[owner]):
                    bpy.ops.object.mode_set(mode='EDIT')
                    try:
                        for item in items:
                            edit_bone = owner.data.edit_bones.get(item.key)
                            if edit_bone is None:
                                raise RuntimeError('bone disappeared during cleanup')
                            owner.data.edit_bones.remove(edit_bone)
                    finally:
                        bpy.ops.object.mode_set(mode='OBJECT')
        for owner, entries in _delta_entries(plan).items():
            prior = original_deltas[owner]
            old = json.loads(prior) if prior else []
            if not isinstance(old, list):
                raise ValueError('existing cleanup delta is invalid')
            owner['_vapb_semantic_cleanup_delta'] = json.dumps(old + entries, sort_keys=True,
                                                               separators=(',', ':'))
        return len(candidates)
    except Exception:
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for owner, data in original_data.items():
            owner.data = data
            prior = original_deltas[owner]
            if prior is None:
                if '_vapb_semantic_cleanup_delta' in owner:
                    del owner['_vapb_semantic_cleanup_delta']
            else:
                owner['_vapb_semantic_cleanup_delta'] = prior
        raise
    finally:
        context.view_layer.objects.active = active
        for clone in clones.values():
            if clone.users == 0:
                if isinstance(clone, bpy.types.Mesh):
                    bpy.data.meshes.remove(clone)
                elif isinstance(clone, bpy.types.Armature):
                    bpy.data.armatures.remove(clone)


@dataclass(frozen=True)
class StagedCleanup:
    scene: Any
    objects: tuple[Any, ...]
    source_to_copy: dict[Any, Any]
    source_plan: CleanupPlan
    removed_count: int


@contextmanager
def cleanup_export_objects(context: Any, objects: Iterable[Any], *, materials: bool = True,
                           bones: bool = True):
    """Yield export-only copies after applying a plan made from live sources.

    The source objects are analyzed before copying, including references from
    other scene objects. Copies are private and live in a disposable scene.
    Neither this helper nor its caller may use the edited scene as staging.
    """
    import bpy  # type: ignore
    sources = tuple(dict.fromkeys(objects))
    if not sources or any(obj.type not in {'MESH', 'ARMATURE', 'EMPTY'} for obj in sources):
        raise ValueError('staging requires selected Mesh, Armature or Empty objects')
    cleanable = tuple(obj for obj in sources if obj.type in {'MESH', 'ARMATURE'})
    source_plan = analyze_cleanup(cleanable, materials=materials, bones=bones,
                                  all_objects=tuple(bpy.data.objects))
    scene = bpy.data.scenes.new('VAPB Cleanup Export')
    scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
    mapping: dict[Any, Any] = {}
    copied_data: list[Any] = []
    try:
        for source in sources:
            copy = source.copy()
            if source.type in {'MESH', 'ARMATURE'}:
                copy.data = source.data.copy()
                copied_data.append(copy.data)
            scene.collection.objects.link(copy)
            mapping[source] = copy
        for source, copy in mapping.items():
            if source.parent is not None:
                if source.parent not in mapping:
                    raise ValueError('staged parent is outside export scope')
                copy.parent = mapping[source.parent]
                copy.matrix_parent_inverse = source.matrix_parent_inverse.copy()
            for modifier in copy.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object is not None:
                    if modifier.object not in mapping:
                        raise ValueError('staged armature target is outside export scope')
                    modifier.object = mapping[modifier.object]
            for constraint in copy.constraints:
                if getattr(constraint, 'target', None) is not None:
                    if constraint.target not in mapping:
                        raise ValueError('staged constraint target is outside export scope')
                    constraint.target = mapping[constraint.target]
        mapped = CleanupPlan(tuple(mapping[obj] for obj in source_plan.scope),
                             tuple(Decision(item.kind, mapping[item.owner], item.key, item.reasons,
                                            item.source_identity) for item in source_plan.decisions),
                             materials, bones)
        with context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
            stage_context = bpy.context
            for copy in mapping.values():
                copy.select_set(True)
            stage_context.view_layer.objects.active = next(iter(mapping.values()))
            removed = apply_cleanup(stage_context, mapped, _staged=True)
            yield StagedCleanup(scene, tuple(mapping[obj] for obj in sources), mapping,
                                source_plan, removed)
    finally:
        for copy in tuple(mapping.values()):
            bpy.data.objects.remove(copy, do_unlink=True)
        for data in copied_data:
            if data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Armature):
                    bpy.data.armatures.remove(data)
        bpy.data.scenes.remove(scene)
