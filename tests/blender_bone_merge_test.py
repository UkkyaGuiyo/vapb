"""Blender 5.2 runtime proof of explicit Semantic Bone Merge."""

from pathlib import Path
import json
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.bone_merge import REMAP_PROPERTY, LOCAL_ID_PROPERTY, prepare_merge
import unitypackage_blender_importer.blender.bone_merge as bone_merge_module
from unitypackage_blender_importer.operators.bone_merge import (
    BONE_MERGE_CLASSES, register_bone_merge_properties, unregister_bone_merge_properties,
)


def reset():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for data in (bpy.data.meshes, bpy.data.armatures):
        for item in list(data):
            if item.users == 0:
                data.remove(item)


def rig(name, translation, root_head, extra=False, chain=False):
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = Matrix.Translation(translation)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    root = data.edit_bones.new('Root')
    root.head = root_head
    root.tail = Vector(root_head) + Vector((0, 0, 1))
    if extra:
        child = data.edit_bones.new('Extra')
        child.head = Vector(root_head) + Vector((0.4, 0, 1))
        child.tail = child.head + Vector((0.1, 0.5, 0.8))
        child.roll = 0.37
        child.parent = root
        if chain:
            tip = data.edit_bones.new('Tip')
            tip.head = child.tail + Vector((0.1, 0, 0.1))
            tip.tail = tip.head + Vector((0.2, 0.3, 0.6))
            tip.roll = -0.24
            tip.parent = child
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def mesh(name, b, chain=False, root_name='Root'):
    data = bpy.data.meshes.new(name)
    data.from_pydata([(0, 0, 0.2), (0.5, 0, 1.5), (0.25, 0.3, 1.1)], [], [(0, 1, 2)])
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.vertex_groups.new(name=root_name).add([0] if chain else [0, 2], 1, 'REPLACE')
    obj.vertex_groups.new(name='Extra').add([1], 1, 'REPLACE')
    if chain:
        obj.vertex_groups.new(name='Tip').add([2], 1, 'REPLACE')
    obj.vertex_groups.new(name='Unselected').add([0], 0.23, 'REPLACE')
    mod = obj.modifiers.new('Skin', 'ARMATURE')
    mod.object = b
    return obj, mod


def evaluated_world_vertices(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = evaluated.to_mesh()
    try:
        return [obj.matrix_world @ vert.co.copy() for vert in result.vertices]
    finally:
        evaluated.to_mesh_clear()


def close_matrix(left, right):
    return max(abs(left[i][j] - right[i][j]) for i in range(4) for j in range(4)) < 1e-4


def choices(state, equivalent='Root', chain=False, source_root='Root'):
    state.mappings.clear()
    rows = [(source_root, 'EQUIVALENT', equivalent), ('Extra', 'B_ONLY', '')]
    if chain:
        rows.append(('Tip', 'B_ONLY', ''))
    for source, classification, target in rows:
        row = state.mappings.add()
        row.source_name = source
        row.classification = classification
        row.target_name = target
        row.confirmed = True


def assert_rejected():
    try:
        outcome = bpy.ops.vapb.bone_merge_apply()
    except RuntimeError:
        return
    assert outcome == {'CANCELLED'}


def equivalent_deform_flag_test():
    """Rest/Pose equality must not hide incompatible future skin deformation."""
    from types import SimpleNamespace
    for reference_deform, source_deform in ((False, True), (True, False)):
        reset()
        a = rig('Reference deform', (0, 0, 0), (0, 0, 0))
        b = rig('Source deform', (0, 0, 0), (0, 0, 0))
        obj, modifier = mesh('Weighted deform', b)
        a.data.bones['Root'].use_deform = reference_deform
        b.data.bones['Root'].use_deform = source_deform
        choices = [SimpleNamespace(source_name='Root', classification='EQUIVALENT',
                                   target_name='Root', confirmed=True)]
        names = (tuple(a.data.bones.keys()), tuple(b.data.bones.keys()))
        before = evaluated_world_vertices(obj)
        try:
            prepare_merge(a, b, choices, bpy.context.scene)
        except ValueError as error:
            assert 'Deform' in str(error)
        else:
            raise AssertionError('Equivalent deform mismatch accepted')
        assert modifier.object is b and names == (tuple(a.data.bones.keys()), tuple(b.data.bones.keys()))
        assert a.data.bones['Root'].use_deform == reference_deform
        assert b.data.bones['Root'].use_deform == source_deform
        assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
        assert all((left-right).length < 1e-6 for left,right in zip(before,evaluated_world_vertices(obj)))
    for deform in (True, False):
        reset()
        a = rig('Reference equal', (0, 0, 0), (0, 0, 0))
        b = rig('Source equal', (0, 0, 0), (0, 0, 0))
        obj, modifier = mesh('Weighted equal', b)
        a.data.bones['Root'].use_deform = b.data.bones['Root'].use_deform = deform
        choices = [SimpleNamespace(source_name='Root', classification='EQUIVALENT',
                                   target_name='Root', confirmed=True)]
        assert bone_merge_module.apply_merge(prepare_merge(a,b,choices,bpy.context.scene)) == (0,1)
        a.pose.bones['Root'].location.x = b.pose.bones['Root'].location.x = .5
        returned = evaluated_world_vertices(obj)
        modifier.object = b
        original = evaluated_world_vertices(obj)
        modifier.object = a
        assert all((left-right).length < 1e-6 for left,right in zip(returned,original))
        assert b.name in bpy.data.objects
    print('BONE_MERGE_DEFORM_FLAG_PASS mismatch_refused=2 matching_flags=2 future_pose_preserved=2 no_mutation_on_refusal=1')


def equivalent_parent_mapping_test():
    """Equal Rest/current Pose must not hide a different future parent chain."""
    from types import SimpleNamespace
    for detach_reference in (True, False):
        reset()
        a = rig('Reference parent', (0, 0, 0), (0, 0, 0), extra=True)
        b = rig('Source parent', (0, 0, 0), (0, 0, 0), extra=True)
        obj, modifier = mesh('Parent weighted', b)
        detached = a if detach_reference else b
        bpy.context.view_layer.objects.active = detached
        bpy.ops.object.mode_set(mode='EDIT')
        detached.data.edit_bones['Extra'].parent = None
        bpy.ops.object.mode_set(mode='OBJECT')
        rows = [SimpleNamespace(source_name=n, classification='EQUIVALENT',
                                target_name=n, confirmed=True) for n in ('Root', 'Extra')]
        before = evaluated_world_vertices(obj)
        parents = (a.data.bones['Extra'].parent, b.data.bones['Extra'].parent)
        groups = tuple((g.name, g.lock_weight) for g in obj.vertex_groups)
        weights = tuple(tuple((g.group, g.weight) for g in v.groups) for v in obj.data.vertices)
        try:
            prepare_merge(a, b, rows, bpy.context.scene)
        except ValueError as error:
            assert '親' in str(error)
        else:
            raise AssertionError('Equivalent parent mismatch accepted')
        assert modifier.object is b
        assert groups == tuple((g.name, g.lock_weight) for g in obj.vertex_groups)
        assert weights == tuple(tuple((g.group, g.weight) for g in v.groups) for v in obj.data.vertices)
        assert parents == (a.data.bones['Extra'].parent, b.data.bones['Extra'].parent)
        assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
        assert all((x-y).length < 1e-6 for x,y in zip(before,evaluated_world_vertices(obj)))
    reset()
    a = rig('Reference matched parent', (0, 0, 0), (0, 0, 0), extra=True)
    b = rig('Source matched parent', (0, 0, 0), (0, 0, 0), extra=True)
    a.data.bones['Root'].name = 'ReferenceRoot'
    obj, modifier = mesh('Matched parent weighted', b)
    rows = [SimpleNamespace(source_name='Root', classification='EQUIVALENT',
                            target_name='ReferenceRoot', confirmed=True),
            SimpleNamespace(source_name='Extra', classification='EQUIVALENT',
                            target_name='Extra', confirmed=True)]
    # Observe B before merge renames its Root vertex group to ReferenceRoot.
    b.pose.bones['Root'].location.x = .5
    original = evaluated_world_vertices(obj)
    b.pose.bones['Root'].location.x = 0
    bpy.context.view_layer.update()
    assert bone_merge_module.apply_merge(prepare_merge(a,b,rows,bpy.context.scene)) == (0,1)
    a.pose.bones['ReferenceRoot'].location.x = .5
    returned = evaluated_world_vertices(obj)
    assert all((x-y).length < 1e-6 for x,y in zip(returned,original))
    assert b.name in bpy.data.objects
    print('BONE_MERGE_PARENT_MAPPING_PASS mismatch_refused=2 renamed_mapping_preserved=1 future_pose_preserved=1 no_mutation_on_refusal=1')


def world_copy_location_reference_test():
    """Explicit Bone remap retargets a world/head Empty constraint transactionally."""
    from types import SimpleNamespace
    def fixture(subtarget):
        reset()
        a = rig('Constraint reference', (0, 0, 0), (0, 0, 0))
        a.data.bones['Root'].name = 'ReferenceRoot'
        b = rig('Constraint source', (0, 0, 0), (0, 0, 0), extra=True)
        obj, modifier = mesh('Constraint skin', b)
        owner = bpy.data.objects.new('Constraint owner', None)
        bpy.context.collection.objects.link(owner)
        constraint = owner.constraints.new('COPY_LOCATION')
        constraint.target, constraint.subtarget = b, subtarget
        constraint.target_space = constraint.owner_space = 'WORLD'
        constraint.head_tail = 0
        rows = [SimpleNamespace(source_name='Root', classification='EQUIVALENT',
                                target_name='ReferenceRoot', confirmed=True),
                SimpleNamespace(source_name='Extra', classification='B_ONLY',
                                target_name='', confirmed=True)]
        return a, b, obj, modifier, owner, constraint, rows
    for name in ('Root', 'Extra'):
        a,b,obj,modifier,owner,constraint,rows = fixture(name)
        bpy.context.view_layer.update()
        before = owner.matrix_world.copy()
        plan = prepare_merge(a,b,rows,bpy.context.scene)
        assert constraint.target is b and constraint.subtarget == name
        assert bone_merge_module.apply_merge(plan) == (1,1)
        target = 'ReferenceRoot' if name == 'Root' else name
        assert constraint.target is a and constraint.subtarget == target
        bpy.context.view_layer.update()
        assert close_matrix(owner.matrix_world,before)
        a.pose.bones['ReferenceRoot'].location.x = b.pose.bones['Root'].location.x = .5
        bpy.context.view_layer.update()
        expected = b.matrix_world @ b.pose.bones[name].head
        assert (owner.matrix_world.translation-expected).length < 1e-5
        assert b.name in bpy.data.objects
    for unsupported in ('LOCAL', 'TAIL', 'UNKNOWN', 'COPY_ROTATION'):
        a,b,obj,modifier,owner,constraint,rows = fixture('Root')
        if unsupported == 'LOCAL': constraint.target_space = 'LOCAL'
        elif unsupported == 'TAIL': constraint.head_tail = 1
        elif unsupported == 'UNKNOWN': constraint.subtarget = 'Missing'
        else:
            owner.constraints.remove(constraint)
            constraint = owner.constraints.new('COPY_ROTATION')
            constraint.target, constraint.subtarget = b,'Root'
        try:
            prepare_merge(a,b,rows,bpy.context.scene)
        except ValueError: pass
        else: raise AssertionError('Unsupported constraint accepted: '+unsupported)
        assert constraint.target is b and modifier.object is b and 'Extra' not in a.data.bones
        assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a
    a,b,obj,modifier,owner,constraint,rows = fixture('Root')
    plan = prepare_merge(a,b,rows,bpy.context.scene)
    bpy.context.view_layer.update()
    before = owner.matrix_world.copy()
    original = bone_merge_module._evaluated_vertices
    def fail_after_retarget(mesh_object):
        if constraint.target is a:
            raise RuntimeError('injected after constraint retarget')
        return original(mesh_object)
    bone_merge_module._evaluated_vertices = fail_after_retarget
    try:
        try: bone_merge_module.apply_merge(plan)
        except RuntimeError as error: assert 'injected' in str(error)
        else: raise AssertionError('Constraint rollback injection did not run')
    finally: bone_merge_module._evaluated_vertices = original
    bpy.context.view_layer.update()
    assert constraint.target is b and constraint.subtarget == 'Root' and modifier.object is b
    assert obj.vertex_groups.get('Root') and not obj.vertex_groups.get('ReferenceRoot')
    assert close_matrix(owner.matrix_world,before) and 'Extra' not in a.data.bones
    assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
    print('BONE_MERGE_COPY_LOCATION_PASS equivalent_and_b_only=2 unsupported_refused=4 future_pose_preserved=2 rollback=1')


def bone_transform_action_test():
    """Copy one exact Bone Transform Action; preserve B and rollback new resources."""
    from types import SimpleNamespace
    def fixture():
        reset()
        a = rig('Action reference', (0,0,0), (0,0,0))
        b = rig('Action source', (0,0,0), (0,0,0))
        a.data.bones['Root'].name = 'Target"Root'
        b.data.bones['Root'].name = 'Source"Root'
        obj,modifier = mesh('Action skin', b, root_name='Source"Root')
        bone = b.pose.bones['Source"Root']
        bone.location.x = 0
        bone.keyframe_insert(data_path='location',frame=1)
        bone.location.x = .5
        bone.keyframe_insert(data_path='location',frame=10)
        bpy.context.scene.frame_set(1)
        rows = [SimpleNamespace(source_name='Source"Root',classification='EQUIVALENT',
                                target_name='Target"Root',confirmed=True)]
        return a,b,obj,modifier,rows
    def curves(armature):
        data = armature.animation_data
        return data.action.layers[0].strips[0].channelbag(data.action_slot).fcurves
    def signature(armature):
        return tuple((c.data_path,c.array_index,tuple(tuple(k.co) for k in c.keyframe_points))
                     for c in curves(armature))
    a,b,obj,modifier,rows = fixture()
    source_action, source_signature = b.animation_data.action,signature(b)
    expected = {}
    for frame in (1,5,10):
        bpy.context.scene.frame_set(frame)
        expected[frame] = evaluated_world_vertices(obj)
    bpy.context.scene.frame_set(1)
    assert bone_merge_module.apply_merge(prepare_merge(a,b,rows,bpy.context.scene)) == (0,1)
    assert a.animation_data.action is not source_action and b.animation_data.action is source_action
    assert signature(b) == source_signature
    target_path = a.pose.bones['Target"Root'].path_from_id()+'.location'
    assert all(c.data_path == target_path for c in curves(a))
    for frame in (1,5,10):
        bpy.context.scene.frame_set(frame)
        assert all((x-y).length < 1e-5 for x,y in zip(expected[frame],evaluated_world_vertices(obj)))
    for mode,channel,end in (
            ('XYZ','rotation_euler',(0,0,.5)),
            ('QUATERNION','rotation_quaternion',tuple(Quaternion((0,0,1),.5))),
            ('AXIS_ANGLE','rotation_axis_angle',(.5,0,0,1)),
            ('QUATERNION','scale',(1.25,1.25,1.25))):
        a,b,obj,modifier,rows = fixture()
        source,target = b.pose.bones['Source"Root'],a.pose.bones['Target"Root']
        source.rotation_mode = target.rotation_mode = mode
        source.keyframe_insert(data_path=channel,frame=1)
        setattr(source,channel,end)
        source.keyframe_insert(data_path=channel,frame=10)
        source_action,source_signature = b.animation_data.action,signature(b)
        samples = {}
        for frame in (1,5,10):
            bpy.context.scene.frame_set(frame)
            samples[frame] = evaluated_world_vertices(obj)
        bpy.context.scene.frame_set(1)
        assert bone_merge_module.apply_merge(prepare_merge(a,b,rows,bpy.context.scene)) == (0,1)
        assert b.animation_data.action is source_action and signature(b) == source_signature
        wanted = target.path_from_id()+'.'+channel
        assert any(c.data_path == wanted for c in curves(a))
        for frame in (1,5,10):
            bpy.context.scene.frame_set(frame)
            assert all((x-y).length < 1e-5 for x,y in zip(samples[frame],evaluated_world_vertices(obj)))
    def transplant_fixture():
        reset()
        a = rig('Action transplant reference',(0,0,0),(0,0,0))
        b = rig('Action transplant source',(0,0,0),(0,0,0),extra=True)
        a.data.bones['Root'].name = 'Target"Root'
        b.data.bones['Root'].name = 'Source"Root'
        b.data.bones['Extra'].name = 'Extra"Tip'
        obj,modifier = mesh('Action transplant skin',b,root_name='Source"Root')
        obj.vertex_groups['Extra'].name = 'Extra"Tip'
        extra = b.pose.bones['Extra"Tip']; extra.rotation_mode = 'XYZ'
        for frame,angle,scale in ((1,0,1),(10,.5,1.2)):
            extra.rotation_euler.y = angle; extra.scale.x = scale
            extra.keyframe_insert(data_path='rotation_euler',frame=frame)
            extra.keyframe_insert(data_path='scale',frame=frame)
        bpy.context.scene.frame_set(1)
        rows = [SimpleNamespace(source_name='Source"Root',classification='EQUIVALENT',
                                target_name='Target"Root',confirmed=True),
                SimpleNamespace(source_name='Extra"Tip',classification='B_ONLY',
                                target_name='',confirmed=True)]
        return a,b,obj,modifier,rows
    a,b,obj,modifier,rows = transplant_fixture()
    source_action,source_signature = b.animation_data.action,signature(b)
    samples = {}
    for frame in (1,5,10):
        bpy.context.scene.frame_set(frame); samples[frame] = evaluated_world_vertices(obj)
    bpy.context.scene.frame_set(1)
    assert bone_merge_module.apply_merge(prepare_merge(a,b,rows,bpy.context.scene)) == (1,1)
    assert a.pose.bones['Extra"Tip'].rotation_mode == 'XYZ'
    parent,expected_parent = a.data.bones['Extra"Tip'].parent,a.data.bones['Target"Root']
    print('NATIVE_TRANSPLANTED_PARENT_PROXY',parent.as_pointer()==expected_parent.as_pointer(),parent is expected_parent)
    assert parent.as_pointer() == expected_parent.as_pointer()
    assert b.animation_data.action is source_action and signature(b) == source_signature
    for curve in curves(a): assert a.path_resolve(curve.data_path) is not None
    for frame in (1,5,10):
        bpy.context.scene.frame_set(frame)
        assert all((x-y).length < 1e-5 for x,y in zip(samples[frame],evaluated_world_vertices(obj)))
    a,b,obj,modifier,rows = transplant_fixture()
    actions_before = set(bpy.data.actions)
    plan = prepare_merge(a,b,rows,bpy.context.scene)
    original = bone_merge_module._evaluated_vertices
    def fail_after_transplanted_action(mesh_object):
        if a.animation_data: raise RuntimeError('injected after transplanted Action')
        return original(mesh_object)
    bone_merge_module._evaluated_vertices = fail_after_transplanted_action
    try:
        try: bone_merge_module.apply_merge(plan)
        except RuntimeError as error: assert 'injected' in str(error)
        else: raise AssertionError('Transplanted Action rollback injection did not run')
    finally: bone_merge_module._evaluated_vertices = original
    assert a.animation_data is None and 'Extra"Tip' not in a.data.bones
    assert set(bpy.data.actions) == actions_before and modifier.object is b
    assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
    for unsupported in ('OBJECT_PATH','DESTINATION_ACTION','DRIVER','INACTIVE_ROTATION','BAD_INDEX','MODE_MISMATCH'):
        a,b,obj,modifier,rows = fixture()
        if unsupported == 'OBJECT_PATH': b.keyframe_insert(data_path='location',frame=1)
        elif unsupported == 'DESTINATION_ACTION': a.keyframe_insert(data_path='location',frame=1)
        elif unsupported == 'DRIVER': b.driver_add('location',0)
        elif unsupported == 'INACTIVE_ROTATION': b.pose.bones['Source"Root'].keyframe_insert(data_path='rotation_euler',frame=1)
        elif unsupported == 'BAD_INDEX': curves(b)[0].array_index = 3
        else: a.pose.bones['Target"Root'].rotation_mode = 'XYZ'
        try: prepare_merge(a,b,rows,bpy.context.scene)
        except ValueError: pass
        else: raise AssertionError('Unsupported Action accepted: '+unsupported)
        assert modifier.object is b and REMAP_PROPERTY not in a
    a,b,obj,modifier,rows = fixture()
    plan = prepare_merge(a,b,rows,bpy.context.scene)
    source_action, source_signature = b.animation_data.action,signature(b)
    actions_before = set(bpy.data.actions)
    original = bone_merge_module._evaluated_vertices
    def fail_after_action(mesh_object):
        if a.animation_data and a.animation_data.action:
            raise RuntimeError('injected after Action assignment')
        return original(mesh_object)
    bone_merge_module._evaluated_vertices = fail_after_action
    try:
        try: bone_merge_module.apply_merge(plan)
        except RuntimeError as error: assert 'injected' in str(error)
        else: raise AssertionError('Action rollback injection did not run')
    finally: bone_merge_module._evaluated_vertices = original
    assert a.animation_data is None and set(bpy.data.actions) == actions_before
    assert b.animation_data.action is source_action and signature(b) == source_signature
    assert modifier.object is b and obj.vertex_groups.get('Source"Root')
    assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
    a,b,obj,modifier,rows = fixture()
    a['_test_action_merge_A'] = b['_test_action_merge_B'] = obj['_test_action_merge_mesh'] = True
    source_name,source_signature = b.animation_data.action.name,signature(b)
    state = bpy.context.scene.vapb_bone_merge
    state.reference,state.source = a,b
    state.mappings.clear()
    for choice in rows:
        row = state.mappings.add()
        row.source_name,row.target_name = choice.source_name,choice.target_name
        row.classification,row.confirmed = choice.classification,choice.confirmed
    bpy.ops.ed.undo_push(message='Before owned Bone Action merge')
    assert bpy.ops.vapb.bone_merge_apply() == {'FINISHED'}
    copy_name = a.animation_data.action.name
    bpy.ops.ed.undo_push(message='After owned Bone Action merge')
    assert bpy.ops.ed.undo() == {'FINISHED'}
    a = next(o for o in bpy.data.objects if o.get('_test_action_merge_A'))
    b = next(o for o in bpy.data.objects if o.get('_test_action_merge_B'))
    obj = next(o for o in bpy.data.objects if o.get('_test_action_merge_mesh'))
    assert a.animation_data is None and copy_name not in bpy.data.actions
    assert b.animation_data.action.name == source_name and signature(b) == source_signature
    assert obj.modifiers['Skin'].object is b and obj.vertex_groups.get('Source"Root')
    assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a
    assert bpy.ops.ed.redo() == {'FINISHED'}
    a = next(o for o in bpy.data.objects if o.get('_test_action_merge_A'))
    b = next(o for o in bpy.data.objects if o.get('_test_action_merge_B'))
    obj = next(o for o in bpy.data.objects if o.get('_test_action_merge_mesh'))
    assert a.animation_data.action.name == copy_name and obj.modifiers['Skin'].object is a
    assert b.animation_data.action.name == source_name and signature(b) == source_signature
    bpy.context.scene.frame_set(5)
    assert all((x-y).length < 1e-5 for x,y in zip(expected[5],evaluated_world_vertices(obj)))
    print('BONE_MERGE_LOCATION_ACTION_PASS escaped_rna_path=1 frames_preserved=3 source_action_unchanged=1 unsupported_refused=6 rollback_no_action_leak=1 operator_undo_redo=1 active_rotation_and_scale_channels=4 b_only_action_pose_and_rollback=1')


def main():
    world_copy_location_reference_test()
    equivalent_parent_mapping_test()
    equivalent_deform_flag_test()
    for cls in BONE_MERGE_CLASSES:
        bpy.utils.register_class(cls)
    register_bone_merge_properties()
    try:
        bone_transform_action_test()
        reset()
        a = rig('A collision', (0, 0, 0), (0, 0, 0), extra=True)
        b = rig('B collision', (0, 0, 0), (0, 0, 0), extra=True)
        state = bpy.context.scene.vapb_bone_merge
        state.reference, state.source = a, b
        choices(state)
        before_names = set(a.data.bones.keys())
        assert_rejected()
        assert set(a.data.bones.keys()) == before_names
        state.mappings[1].classification = 'AMBIGUOUS'
        state.mappings[1].confirmed = True
        assert_rejected()
        assert set(a.data.bones.keys()) == before_names
        state.mappings[1].classification = 'EQUIVALENT'
        state.mappings[1].target_name = 'Extra'
        state.mappings[1].confirmed = True
        assert prepare_merge(a, b, state.mappings, bpy.context.scene)['b_only'] == []
        shared = bpy.data.objects.new('Shared armature user', a.data)
        bpy.context.collection.objects.link(shared)
        assert_rejected()
        bpy.data.objects.remove(shared, do_unlink=True)
        b.animation_data_create()
        assert_rejected()
        b.animation_data_clear()
        constraint = b.pose.bones['Root'].constraints.new('COPY_LOCATION')
        assert_rejected()
        b.pose.bones['Root'].constraints.remove(constraint)
        unresolved = bpy.data.objects.new('Unresolved VRC root', None)
        bpy.context.collection.objects.link(unresolved)
        unresolved['_vapb_renderer_occurrences'] = '{}'
        assert_rejected()
        bpy.data.objects.remove(unresolved, do_unlink=True)
        state.reference = None
        state.source = None
        reset()
        a = rig('A', (2, 0, 0), (-2, 0, 0))
        b = rig('B', (-1, 0, 0), (1, 0, 0), extra=True, chain=True)
        identity = ('a' * 32, 'b' * 64, '-10')
        for bone in (a.data.bones['Root'], b.data.bones['Root']):
            for key, value in zip(('_vapb_fbx_source_asset_guid', '_vapb_fbx_source_asset_sha256',
                                   '_vapb_fbx_model_uid'), identity):
                bone[key] = value
        source_tip = b.data.bones['Tip']
        source_tip['_vapb_fbx_source_asset_guid'] = identity[0]
        source_tip['_vapb_fbx_source_asset_sha256'] = identity[1]
        source_tip['_vapb_fbx_model_uid'] = '-11'
        source_tip['_vapb_fbx_bone_receipt_id'] = 'source-bone-tip'
        source_tip['_vapb_fbx_bone_realization_id'] = 'source-realization-tip'
        source_tip['custom_tag'] = 'preserved'
        source_tip.envelope_distance = 0.42
        source_tip.head_radius = 0.13
        b.data.bones['Root'].name = 'OtherRoot'
        obj, modifier = mesh('Cloth', b, chain=True, root_name='OtherRoot')
        accessory_data = bpy.data.meshes.new('Accessory')
        accessory_data.from_pydata([(0, 0, 0)], [], [])
        accessory = bpy.data.objects.new('Accessory', accessory_data)
        bpy.context.collection.objects.link(accessory)
        accessory.parent = b
        accessory.parent_type = 'BONE'
        accessory.parent_bone = 'Extra'
        accessory.matrix_world = Matrix.Translation((0.6, 0.2, 1.4))
        target_only_data = bpy.data.meshes.new('TargetOnly')
        target_only_data.from_pydata([(0, 0, 0)], [], [])
        target_only = bpy.data.objects.new('TargetOnly', target_only_data)
        bpy.context.collection.objects.link(target_only)
        target_only.vertex_groups.new(name='Root').add([0], 0.47, 'REPLACE')
        target_only.parent = b
        target_only.matrix_world = Matrix.Translation((0.2, 0.1, 0.3))
        b.pose.bones['Extra'].rotation_mode = 'QUATERNION'
        b.pose.bones['Extra'].rotation_quaternion = Quaternion((0, 1, 0), 0.35)
        b.pose.bones['Tip'].rotation_mode = 'QUATERNION'
        b.pose.bones['Tip'].rotation_quaternion = Quaternion((1, 0, 0), 0.2)
        state = bpy.context.scene.vapb_bone_merge
        state.reference, state.source = a, b
        assert bpy.ops.vapb.bone_merge_candidates() == {'FINISHED'}
        assert state.mappings[0].classification == 'EQUIVALENT'
        assert not state.mappings[0].confirmed
        assert state.mappings[1].classification == 'AMBIGUOUS'
        assert state.mappings[2].classification == 'AMBIGUOUS'
        try:
            outcome = bpy.ops.vapb.bone_merge_preview()
        except RuntimeError:
            pass
        else:
            assert outcome == {'CANCELLED'}
        choices(state, chain=True, source_root='OtherRoot')
        source_tip.bbone_segments = 2
        assert_rejected()
        source_tip.bbone_segments = 1
        source_tip.inherit_scale = 'NONE'
        assert_rejected()
        source_tip.inherit_scale = 'FULL'
        modifier.use_bone_envelopes = True
        assert_rejected()
        modifier.use_bone_envelopes = False
        obj.data.animation_data_create()
        assert_rejected()
        obj.data.animation_data_clear()
        assert bpy.ops.vapb.bone_merge_preview() == {'FINISHED'}
        before = evaluated_world_vertices(obj)
        accessory_before = accessory.matrix_world.copy()
        old_group_weight = obj.vertex_groups['Unselected'].weight(0)
        b_rest = b.matrix_world @ b.data.bones['Extra'].matrix_local
        b_pose = b.matrix_world @ b.pose.bones['Extra'].matrix
        tip_rest = b.matrix_world @ b.data.bones['Tip'].matrix_local
        tip_pose = b.matrix_world @ b.pose.bones['Tip'].matrix
        original_add = bone_merge_module._add_b_only_bones
        def fail_after_bones(plan):
            original_add(plan)
            raise RuntimeError('injected failure')
        bone_merge_module._add_b_only_bones = fail_after_bones
        try:
            try:
                bone_merge_module.apply_merge(prepare_merge(a, b, state.mappings, bpy.context.scene))
            except RuntimeError as exc:
                assert str(exc) == 'injected failure'
            else:
                raise AssertionError('injected failure was not raised')
        finally:
            bone_merge_module._add_b_only_bones = original_add
        assert 'Extra' not in a.data.bones and 'Tip' not in a.data.bones
        assert modifier.object is b and accessory.parent is b and REMAP_PROPERTY not in a
        assert target_only.vertex_groups.get('Root') is not None
        assert target_only.vertex_groups.get('OtherRoot') is None
        assert abs(target_only.vertex_groups['Root'].weight(0) - 0.47) < 1e-6
        assert LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
        assert max((x - y).length for x, y in zip(before, evaluated_world_vertices(obj))) < 1e-4
        original_evaluate = bone_merge_module._evaluated_vertices
        calls = [0]
        def report_changed_vertex(target):
            calls[0] += 1
            result = original_evaluate(target)
            if calls[0] == 3 and result:
                return (result[0] + Vector((1, 0, 0)), *result[1:])
            return result
        bone_merge_module._evaluated_vertices = report_changed_vertex
        try:
            try:
                bone_merge_module.apply_merge(prepare_merge(a, b, state.mappings, bpy.context.scene))
            except RuntimeError as exc:
                assert 'World 変形' in str(exc)
            else:
                raise AssertionError('changed deformation was accepted')
        finally:
            bone_merge_module._evaluated_vertices = original_evaluate
        assert 'Extra' not in a.data.bones and 'Tip' not in a.data.bones
        assert modifier.object is b and accessory.parent is b
        assert REMAP_PROPERTY not in a and LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
        assert obj.vertex_groups.get('OtherRoot') is not None
        assert obj.vertex_groups.get('Root') is None
        assert target_only.vertex_groups.get('Root') is not None
        assert target_only.vertex_groups.get('OtherRoot') is None
        assert abs(target_only.vertex_groups['Root'].weight(0) - 0.47) < 1e-6
        assert max((x - y).length for x, y in zip(before, evaluated_world_vertices(obj))) < 1e-4
        a['_test_bone_merge_A'] = True
        b['_test_bone_merge_B'] = True
        obj['_test_bone_merge_mesh'] = True
        bpy.ops.ed.undo_push(message='Before synthetic bone merge')
        assert bpy.ops.vapb.bone_merge_apply() == {'FINISHED'}
        after = evaluated_world_vertices(obj)
        assert max((x - y).length for x, y in zip(before, after)) < 1e-4
        assert modifier.object is a and b.name in bpy.data.objects
        assert obj.vertex_groups.get('Root') is not None
        assert obj.vertex_groups.get('OtherRoot') is None
        assert target_only.vertex_groups.get('Root') is not None
        assert target_only.vertex_groups.get('OtherRoot') is None
        assert abs(target_only.vertex_groups['Root'].weight(0) - 0.47) < 1e-6
        assert accessory.parent is a and accessory.parent_type == 'BONE'
        assert accessory.parent_bone == 'Extra'
        assert close_matrix(accessory.matrix_world, accessory_before)
        assert obj.vertex_groups['Unselected'].weight(0) == old_group_weight
        assert obj.vertex_groups.get('Extra') is not None
        assert close_matrix(a.matrix_world @ a.data.bones['Extra'].matrix_local, b_rest)
        assert close_matrix(a.matrix_world @ a.pose.bones['Extra'].matrix, b_pose)
        assert close_matrix(a.matrix_world @ a.data.bones['Tip'].matrix_local, tip_rest)
        assert close_matrix(a.matrix_world @ a.pose.bones['Tip'].matrix, tip_pose)
        assert a.data.bones['Extra'].parent.name == 'Root'
        assert a.data.bones['Tip'].parent.name == 'Extra'
        assert a.data.bones['Tip']['custom_tag'] == 'preserved'
        assert abs(a.data.bones['Tip'].envelope_distance - 0.42) < 1e-5
        assert abs(a.data.bones['Tip'].head_radius - 0.13) < 1e-5
        assert a.data.bones['Tip']['_vapb_fbx_bone_receipt_id'] == 'source-bone-tip'
        assert a.data.bones['Tip']['_vapb_fbx_bone_realization_id'] != 'source-realization-tip'
        assert a.data.bones['Tip']['_vapb_fbx_source_realization_id'] == 'source-realization-tip'
        assert a.pose.bones['Tip']['_vapb_fbx_bone_realization_id'] == a.data.bones['Tip']['_vapb_fbx_bone_realization_id']
        remap = json.loads(a[REMAP_PROPERTY])
        assert remap['version'] == 1 and len(remap['merges']) == 1
        entry = remap['merges'][0]
        assert entry['source_armature_local_id'] == b[LOCAL_ID_PROPERTY]
        assert entry['target_armature_local_id'] == a[LOCAL_ID_PROPERTY]
        assert {record['old_name']: record['new_name'] for record in entry['bones']} == {
            'OtherRoot': 'Root', 'Extra': 'Extra', 'Tip': 'Tip'}
        tip_record = next(record for record in entry['bones'] if record['old_name'] == 'Tip')
        assert tip_record['source_local_id'] == b.data.bones['Tip'][LOCAL_ID_PROPERTY]
        assert tip_record['target_local_id'] == a.data.bones['Tip'][LOCAL_ID_PROPERTY]
        assert tip_record['source_local_id'] != tip_record['target_local_id']
        assert tip_record['source_fbx']['_vapb_fbx_model_uid'] == '-11'
        a.data.bones['Tip'].name = 'RenamedTargetTip'
        b.data.bones['Tip'].name = 'RenamedSourceTip'
        assert a.data.bones['RenamedTargetTip'][LOCAL_ID_PROPERTY] == tip_record['target_local_id']
        assert b.data.bones['RenamedSourceTip'][LOCAL_ID_PROPERTY] == tip_record['source_local_id']
        assert json.loads(a[REMAP_PROPERTY])['merges'][0]['bones'][-1]['target_local_id'] == tip_record['target_local_id']
        bpy.ops.ed.undo_push(message='After synthetic bone merge')
        assert bpy.ops.ed.undo() == {'FINISHED'}
        a = next(obj for obj in bpy.data.objects if obj.get('_test_bone_merge_A'))
        b = next(obj for obj in bpy.data.objects if obj.get('_test_bone_merge_B'))
        obj = next(item for item in bpy.data.objects if item.get('_test_bone_merge_mesh'))
        accessory = bpy.data.objects['Accessory']
        target_only = bpy.data.objects['TargetOnly']
        assert 'Extra' not in a.data.bones and 'Tip' not in a.data.bones
        assert obj.modifiers['Skin'].object is b
        assert obj.vertex_groups.get('OtherRoot') is not None
        assert obj.vertex_groups.get('Root') is None
        assert accessory.parent is b and accessory.parent_bone == 'Extra'
        assert target_only.parent is b and target_only.vertex_groups.get('Root') is not None
        assert target_only.vertex_groups.get('OtherRoot') is None
        assert abs(target_only.vertex_groups['Root'].weight(0) - 0.47) < 1e-6
        assert REMAP_PROPERTY not in a
        assert LOCAL_ID_PROPERTY not in a and LOCAL_ID_PROPERTY not in b
        print('BONE_MERGE_RUNTIME_PASS posed=1 world_matrices=1 b_only_chain=1 bone_parent=1 collision=1 ambiguous=1 shared=1 animation=1 constraint=1 vrc=1 no_weight_transfer=1 target_only_group_preserved=1 B_retained=1 rollback=1 undo=1')
    finally:
        unregister_bone_merge_properties()
        for cls in reversed(BONE_MERGE_CLASSES):
            bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    main()
