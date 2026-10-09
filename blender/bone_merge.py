"""Explicit semantic bone remap and conservative Blender armature merge."""

from __future__ import annotations

import json
import uuid


REMAP_PROPERTY = "_vapb_bone_merge_remap_v1"
LOCAL_ID_PROPERTY = "_vapb_bone_merge_local_id"
_IDENTITY_KEYS = ("_vapb_fbx_source_asset_guid", "_vapb_fbx_source_asset_sha256",
                  "_vapb_fbx_model_uid")


def _identity(bone):
    values = tuple(bone.get(key) for key in _IDENTITY_KEYS)
    return values if all(values) else None


def candidate_mappings(a_bones, b_bones):
    """Return suggestions, never confirmations. Names and transforms are ignored."""
    by_identity = {}
    for bone in a_bones:
        identity = _identity(bone)
        if identity:
            by_identity.setdefault(identity, []).append(bone.name)
    result = []
    for bone in b_bones:
        matches = by_identity.get(_identity(bone), ()) if _identity(bone) else ()
        result.append((bone.name, matches[0], "EQUIVALENT") if len(matches) == 1
                      else (bone.name, "", "AMBIGUOUS"))
    return result


def confirmed_remap(a_names, b_names, choices):
    a_names, b_names = set(a_names), set(b_names)
    if len(choices) != len(b_names) or {row.source_name for row in choices} != b_names:
        raise ValueError("B の Bone 一覧が変わりました。候補を読み直してください")
    remap = {}
    equivalent_targets = set()
    for row in choices:
        if not row.confirmed or row.classification not in {"EQUIVALENT", "B_ONLY"}:
            raise ValueError("全 Bone の分類と対応を個別に確認してください。AMBIGUOUS は保護します")
        if row.classification == "EQUIVALENT":
            if row.target_name not in a_names or row.target_name in equivalent_targets:
                raise ValueError("対応先 A Bone が無効または複数 Bone から重複指定されています")
            equivalent_targets.add(row.target_name)
            remap[row.source_name] = row.target_name
        else:
            if row.source_name in a_names:
                raise ValueError("B 固有 Bone 名が A と衝突しています。先に明示的に改名してください")
            remap[row.source_name] = row.source_name
    return remap


def _close_matrix(left, right, epsilon=1e-5):
    return all(abs(left[i][j] - right[i][j]) <= epsilon
               for i in range(4) for j in range(4))


def _rigid_world(matrix):
    columns = [matrix.col[i].xyz for i in range(3)]
    return (all(abs(v.length - 1.0) <= 1e-5 for v in columns)
            and all(abs(columns[i].dot(columns[j])) <= 1e-5
                    for i in range(3) for j in range(i + 1, 3)))


def _unsupported_reference(owner, *, allowed_constraints=(), allowed_animation=False):
    if getattr(owner, "animation_data", None) and not allowed_animation:
        return True
    if any(c not in allowed_constraints for c in getattr(owner, "constraints", ())):
        return True
    try:
        keys = owner.keys()
    except (AttributeError, TypeError):
        keys = ()
    for key in keys:
        lowered = key.lower()
        if (lowered.startswith('_vapb_') and not lowered.startswith(('_vapb_fbx_', '_vapb_bone_merge_'))
                or lowered.startswith('unity_') and lowered not in {
                    'unity_source_fbx', 'unity_source_package_id'}
                or any(token in lowered for token in ('physbone', 'contact', 'vrc', 'rootbone'))):
            return True
    return False


def _attached_objects(a, b):
    import bpy  # type: ignore

    return [obj for obj in bpy.data.objects if obj is not a and obj is not b and
            (obj.parent is b or any(mod.type == 'ARMATURE' and mod.object is b
                                    for mod in obj.modifiers))]


def _bone_location_action(a, b, remap):
    data = b.animation_data
    if data is None:
        return None
    action = data.action
    if (a.animation_data is not None or action is None or action.library or action.override_library or
            data.drivers or data.nla_tracks or data.use_tweak_mode or
            data.action_blend_type != 'REPLACE' or data.action_influence != 1 or
            not action.is_action_layered or len(action.slots) != 1 or len(action.layers) != 1 or
            len(action.layers[0].strips) != 1 or data.action_slot is None):
        raise ValueError("Bone Action は A が未アニメーションで、単一 location Clip/slot のみ対応しています")
    paths = {}
    for source in b.data.bones:
        target = a.data.bones.get(remap[source.name])
        if target is None or any(
                bone.bbone_segments != 1 or bone.inherit_scale != 'FULL' or
                not bone.use_inherit_rotation or not bone.use_local_location or
                bone.use_relative_parent or bone.use_connect for bone in (source, target)):
            raise ValueError("Bone Action は標準継承設定の同等 Bone のみ対応しています")
        source_pose, target_pose = b.pose.bones[source.name], a.pose.bones[target.name]
        if source_pose.rotation_mode != target_pose.rotation_mode:
            raise ValueError("Bone Action の回転モードが一致しません")
        paths[source_pose.path_from_id()+'.location'] = target_pose.path_from_id()+'.location'
    strip = action.layers[0].strips[0]
    bag = strip.channelbag(data.action_slot) if strip.type == 'KEYFRAME' else None
    if bag is None or not bag.fcurves:
        raise ValueError("Bone Action の channel がありません")
    destinations = set()
    for curve in bag.fcurves:
        if curve.data_path not in paths or curve.array_index not in (0,1,2):
            raise ValueError("Bone Action の location 以外の binding は未対応です")
        address = (paths[curve.data_path], curve.array_index)
        if address in destinations:
            raise ValueError("Bone Action の付け替え先 binding が重複しています")
        destinations.add(address)
    return {'source': action, 'slot': data.action_slot.identifier, 'paths': paths,
            'extrapolation': data.action_extrapolation}


def prepare_merge(a, b, choices, scene):
    """Read-only full preflight. Return the exact objects and mappings to edit."""
    if a is None or b is None or a is b or a.type != 'ARMATURE' or b.type != 'ARMATURE':
        raise ValueError("異なる基準 A と統合対象 B のアーマチュアを選択してください")
    if a.name not in scene.objects or b.name not in scene.objects:
        raise ValueError("A/B は現在の Scene に必要です")
    if (a.library or b.library or a.data.library or b.data.library or
            a.data.users != 1 or b.data.users != 1 or
            len(a.users_scene) != 1 or len(b.users_scene) != 1):
        raise ValueError("共有またはリンクされた Armature は処理できません")
    if not _rigid_world(a.matrix_world) or not _rigid_world(b.matrix_world):
        raise ValueError("Armature の非一様 Scale/Shear はこの統合では未対応です")
    remap = confirmed_remap(a.data.bones.keys(), b.data.bones.keys(), choices)
    classifications = {row.source_name: row.classification for row in choices}
    if REMAP_PROPERTY in a:
        try:
            existing_remap = json.loads(a[REMAP_PROPERTY])
        except (TypeError, ValueError):
            raise ValueError("既存 Bone remap が読めません") from None
        if existing_remap.get('version') != 1 or not isinstance(existing_remap.get('merges'), list):
            raise ValueError("既存 Bone remap の形式が未対応です")
        if b.get(LOCAL_ID_PROPERTY) and any(
                entry.get('source_armature_local_id') == b[LOCAL_ID_PROPERTY]
                for entry in existing_remap['merges']):
            raise ValueError("この B は既に統合されています")
    existing_ids = [owner.get(LOCAL_ID_PROPERTY) for owner in
                    (a, b, *a.data.bones, *b.data.bones) if owner.get(LOCAL_ID_PROPERTY)]
    if len(existing_ids) != len(set(existing_ids)):
        raise ValueError("Armature/Bone のローカル ID が重複しています")
    try:
        for value in existing_ids:
            uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise ValueError("Armature/Bone のローカル ID が無効です") from None
    action_plan = _bone_location_action(a, b, remap)
    for owner in (a, b, a.data, b.data, *a.pose.bones, *b.pose.bones):
        if _unsupported_reference(owner, allowed_animation=owner is b and action_plan is not None):
            raise ValueError("Animation / Constraint / VRC 参照があり、付替えを証明できません")
    if _unsupported_reference(scene):
        raise ValueError("Scene に未対応の Unity/VRC 参照があります")
    for bone in b.data.bones:
        if _unsupported_reference(bone):
            raise ValueError("B Bone に未対応の参照があります")
        if classifications[bone.name] == 'EQUIVALENT':
            target = a.data.bones[remap[bone.name]]
            expected_parent = remap[bone.parent.name] if bone.parent else None
            actual_parent = target.parent.name if target.parent else None
            if actual_parent != expected_parent:
                raise ValueError("同等 Bone の親対応が一致しません。A/B の親階層と確定 mapping を確認してください")
            if target.use_deform != bone.use_deform:
                raise ValueError("同等 Bone の Deform 設定が一致しません。A/B の変形設定を確認してください")
            if not _close_matrix(a.matrix_world @ target.matrix_local,
                                 b.matrix_world @ bone.matrix_local):
                raise ValueError("等価 Bone の World Rest が一致しません")
            if not _close_matrix(a.matrix_world @ a.pose.bones[target.name].matrix,
                                 b.matrix_world @ b.pose.bones[bone.name].matrix):
                raise ValueError("等価 Bone の現在 Pose が一致しません")
        else:
            if (bone.bbone_segments != 1 or bone.inherit_scale != 'FULL' or
                    not bone.use_inherit_rotation or not bone.use_local_location or
                    bone.use_relative_parent or bone.use_connect):
                raise ValueError("B 固有 Bone の特殊な変形/継承設定は未対応です")
    attached = _attached_objects(a, b)
    import bpy  # type: ignore
    constraint_refs = []
    for obj in bpy.data.objects:
        references = [c for c in obj.constraints if getattr(c, 'target', None) is b]
        for constraint in references:
            if (obj.type != 'EMPTY' or obj.parent is not None or obj.library or obj.override_library or
                    len(obj.users_scene) != 1 or obj.name not in scene.objects or
                    a in obj.children_recursive or b in obj.children_recursive or len(obj.constraints) != 1 or
                    constraint.type != 'COPY_LOCATION' or constraint.target_space != 'WORLD' or
                    constraint.owner_space != 'WORLD' or constraint.head_tail != 0 or
                    constraint.use_bbone_shape or constraint.subtarget not in remap):
                raise ValueError("B の Constraint 参照は親なし Empty の World/head Copy Location のみ対応しています")
            constraint_refs.append((obj, constraint, constraint.subtarget, remap[constraint.subtarget]))
        if obj.type == 'ARMATURE' and any(
                getattr(constraint, 'target', None) is b
                for pose in obj.pose.bones for constraint in pose.constraints):
            raise ValueError("B を参照する Bone Constraint があり、付替えを証明できません")
        if obj.name in scene.objects and obj not in (a, b) and _unsupported_reference(obj, allowed_constraints=references) and obj not in attached:
            raise ValueError("Scene に未対応の Unity/VRC 参照があります")
    for obj in attached:
        if (obj.name not in scene.objects or obj.type != 'MESH' or obj.library or
                obj.data.library or obj.data.users != 1 or
                len(obj.users_scene) != 1 or _unsupported_reference(obj) or
                _unsupported_reference(obj.data) or
                any(_unsupported_reference(mod) for mod in obj.modifiers)):
            raise ValueError("B 参照 Mesh に共有/未対応参照があります")
        if obj.parent is b and obj.parent_type not in {'OBJECT', 'BONE'}:
            raise ValueError("未対応の B 親子参照があります")
        if obj.parent is b and obj.parent_type == 'BONE' and obj.parent_bone not in remap:
            raise ValueError("Bone 親参照が未解決です")
        for old, new in remap.items():
            if old != new and obj.vertex_groups.get(old) and obj.vertex_groups.get(new):
                raise ValueError("Vertex Group 名が衝突しています。先に明示的に整理してください")
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object is b and (
                    mod.use_bone_envelopes or not mod.use_vertex_groups):
                raise ValueError("Bone Envelope 変形は未対応です")
    b_only = [bone for bone in b.data.bones if classifications[bone.name] == 'B_ONLY']
    def depth(bone):
        value = 0
        while bone.parent is not None:
            value += 1
            bone = bone.parent
        return value
    b_only.sort(key=depth)
    return {"a": a, "b": b, "remap": remap, "classes": classifications,
            "attached": attached, "b_only": [bone.name for bone in b_only], "constraints": constraint_refs, "action": action_plan}


def _activate_object(obj):
    import bpy  # type: ignore

    for selected in bpy.context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _add_b_only_bones(plan):
    import bpy  # type: ignore

    a, b, remap = plan['a'], plan['b'], plan['remap']
    source = {name: (b.data.bones[name].matrix_local.copy(),
                     b.data.bones[name].head_local.copy(),
                     b.data.bones[name].tail_local.copy(),
                     b.data.bones[name].parent.name if b.data.bones[name].parent else None,
                     b.data.bones[name].use_deform,
                     {key: b.data.bones[name][key] for key in b.data.bones[name].keys()})
              for name in plan['b_only']}
    _activate_object(a)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        for name in plan['b_only']:
            _matrix, _head, _tail, _parent, deform, properties = source[name]
            bone = a.data.edit_bones.new(name)
            bone.use_deform = deform
            source_bone = b.data.bones[name]
            for option in ('envelope_distance', 'envelope_weight', 'head_radius',
                           'tail_radius', 'bbone_x', 'bbone_z'):
                setattr(bone, option, getattr(source_bone, option))
            for key, value in properties.items():
                if key != LOCAL_ID_PROPERTY:
                    bone[key] = value
            if "_vapb_fbx_bone_receipt_id" in properties:
                bone["_vapb_fbx_source_realization_id"] = properties.get(
                    "_vapb_fbx_bone_realization_id", "")
                bone["_vapb_fbx_bone_realization_id"] = str(uuid.uuid4())
                bone["_vapb_fbx_receipt_evidence"] = "OBSERVED_BONE_TRANSPLANT"
        for name in plan['b_only']:
            parent = source[name][3]
            if parent:
                child = a.data.edit_bones[name]
                child.parent = a.data.edit_bones[remap[parent]]
        for name in plan['b_only']:
            matrix, head, tail, _parent, _deform, _properties = source[name]
            bone = a.data.edit_bones[name]
            transform = a.matrix_world.inverted() @ b.matrix_world
            bone.head = transform @ head
            bone.tail = transform @ tail
            bone.align_roll((transform @ matrix).col[2].xyz)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    for name in plan['b_only']:
        expected = b.matrix_world @ source[name][0]
        actual = a.matrix_world @ a.data.bones[name].matrix_local
        if not _close_matrix(actual, expected):
            raise RuntimeError("移植 Bone の World Rest 検証に失敗しました")
    for name in plan['b_only']:
        target = a.pose.bones[name]
        for key in b.pose.bones[name].keys():
            target[key] = b.pose.bones[name][key]
        for key in a.data.bones[name].keys():
            if key.startswith("_vapb_fbx_"):
                target[key] = a.data.bones[name][key]
        a.pose.bones[name].matrix = a.matrix_world.inverted() @ b.matrix_world @ b.pose.bones[name].matrix
        bpy.context.view_layer.update()
        if not _close_matrix(a.matrix_world @ a.pose.bones[name].matrix,
                             b.matrix_world @ b.pose.bones[name].matrix):
            raise RuntimeError("移植 Bone の Pose 検証に失敗しました")


def _remove_b_only_bones(a, names):
    import bpy  # type: ignore

    if not names:
        return
    _activate_object(a)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        for name in reversed(names):
            bone = a.data.edit_bones.get(name)
            if bone:
                a.data.edit_bones.remove(bone)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def _evaluated_vertices(obj):
    import bpy  # type: ignore

    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return tuple((obj.matrix_world @ vertex.co).copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def apply_merge(plan):
    """Apply a preflighted plan; keep B and undo local writes if an API fails."""
    import bpy  # type: ignore

    a, b, remap = plan['a'], plan['b'], plan['remap']
    if bpy.context.mode != 'OBJECT':
        raise ValueError("オブジェクトモードで実行してください")
    before = {}
    bpy.context.view_layer.update()
    for obj in plan['attached']:
        before[obj] = {
            "evaluated": _evaluated_vertices(obj),
            "modifiers": [(mod, mod.object) for mod in obj.modifiers if mod.type == 'ARMATURE'],
            "parent": obj.parent, "parent_type": obj.parent_type,
            "parent_bone": obj.parent_bone, "world": obj.matrix_world.copy(),
        }
    constraint_world = [(obj, obj.matrix_world.copy()) for obj, _, _, _ in plan['constraints']]
    old_remap = a.get(REMAP_PROPERTY)
    prior = json.loads(old_remap) if old_remap is not None else {'version': 1, 'merges': []}
    id_before = {(side, name): owner.get(LOCAL_ID_PROPERTY)
                 for side, armature in (('A', a), ('B', b))
                 for name, owner in [('__armature__', armature),
                                     *((bone.name, bone) for bone in armature.data.bones)]}
    renamed_groups = []
    retargeted_constraints = []
    copied_action = None
    action_data_created = False
    try:
        _add_b_only_bones(plan)
        target_bones = [a.data.bones[name] for name in set(remap.values())]
        for owner in (a, b, *target_bones, *b.data.bones):
            if not owner.get(LOCAL_ID_PROPERTY):
                owner[LOCAL_ID_PROPERTY] = str(uuid.uuid4())
        for obj in plan['attached']:
            for old, new in remap.items():
                group = obj.vertex_groups.get(old)
                if group and old != new:
                    group.name = new
                    renamed_groups.append((group, old))
            for mod, target in before[obj]['modifiers']:
                if target is b:
                    mod.object = a
            if obj.parent is b:
                world = obj.matrix_world.copy()
                parent_type = obj.parent_type
                old_parent_bone = obj.parent_bone
                obj.parent = a
                obj.parent_type = parent_type
                if parent_type == 'BONE':
                    obj.parent_bone = remap[old_parent_bone]
                obj.matrix_world = world
        if plan['action'] is not None:
            capture = plan['action']
            copied_action = capture['source'].copy()
            slot = copied_action.slots[capture['slot']]
            for curve in copied_action.layers[0].strips[0].channelbag(slot).fcurves:
                curve.data_path = capture['paths'][curve.data_path]
            a.animation_data_create()
            action_data_created = True
            a.animation_data.action = copied_action
            a.animation_data.action_slot = slot
            a.animation_data.action_extrapolation = capture['extrapolation']
        for obj, constraint, old, new in plan['constraints']:
            retargeted_constraints.append((constraint, constraint.target, constraint.subtarget))
            constraint.target = a
            constraint.subtarget = new
        records = []
        for old, new in remap.items():
            source = b.data.bones[old]
            target = a.data.bones[new]
            records.append({
                'source_local_id': source[LOCAL_ID_PROPERTY],
                'target_local_id': target[LOCAL_ID_PROPERTY],
                'source_fbx': {key: source.get(key) for key in _IDENTITY_KEYS},
                'source_receipt_id': source.get('_vapb_fbx_bone_receipt_id'),
                'target_receipt_id': target.get('_vapb_fbx_bone_receipt_id'),
                'old_name': old, 'new_name': new,
                'classification': plan['classes'][old],
            })
        prior['merges'].append({
            'source_armature_local_id': b[LOCAL_ID_PROPERTY],
            'target_armature_local_id': a[LOCAL_ID_PROPERTY],
            'bones': records,
        })
        a[REMAP_PROPERTY] = json.dumps(prior, sort_keys=True)
        bpy.context.view_layer.update()
        for obj, world in constraint_world:
            if not _close_matrix(obj.matrix_world, world):
                raise RuntimeError("Constraint 付け替え後の World 配置が一致しません")
        for obj, snapshot in before.items():
            after = _evaluated_vertices(obj)
            baseline = snapshot['evaluated']
            if len(after) != len(baseline) or any(
                    (left - right).length > 1e-4 for left, right in zip(after, baseline)):
                raise RuntimeError("付替え後の World 変形が一致しません")
    except Exception:
        if copied_action is not None:
            if action_data_created:
                a.animation_data_clear()
            bpy.data.actions.remove(copied_action)
        for constraint, target, subtarget in reversed(retargeted_constraints):
            constraint.target = target
            constraint.subtarget = subtarget
        for group, old_name in reversed(renamed_groups):
            group.name = old_name
        for obj, snapshot in before.items():
            for mod, target in snapshot['modifiers']:
                mod.object = target
            obj.parent = snapshot['parent']
            obj.parent_type = snapshot['parent_type']
            obj.parent_bone = snapshot['parent_bone']
            obj.matrix_world = snapshot['world']
        if old_remap is None:
            if REMAP_PROPERTY in a:
                del a[REMAP_PROPERTY]
        else:
            a[REMAP_PROPERTY] = old_remap
        _remove_b_only_bones(a, plan['b_only'])
        for side, armature in (('A', a), ('B', b)):
            for name, owner in [('__armature__', armature),
                                *((bone.name, bone) for bone in armature.data.bones)]:
                previous = id_before.get((side, name))
                if previous is None:
                    if LOCAL_ID_PROPERTY in owner:
                        del owner[LOCAL_ID_PROPERTY]
                else:
                    owner[LOCAL_ID_PROPERTY] = previous
        raise
    return len(plan['b_only']), len(plan['attached'])
