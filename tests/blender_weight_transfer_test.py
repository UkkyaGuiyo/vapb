"""Run with Blender --background --factory-startup --python this_file."""

from pathlib import Path
import math
import os
import sys
import traceback

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from unitypackage_blender_importer.operators.weight_transfer import (
    WEIGHT_TRANSFER_CLASSES, calculate_transfer, apply_transfer_plan,
    register_weight_transfer_properties, unregister_weight_transfer_properties,
)


def weight(group, index):
    try:
        return group.weight(index)
    except RuntimeError:
        return 0.0


def make_mesh(name, vertices, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def assert_rollback():
    class FakeGroup:
        def __init__(self, fail_once=False):
            self.values = {}
            self.fail_once = fail_once

        def weight(self, index):
            if index not in self.values:
                raise RuntimeError('absent')
            return self.values[index]

        def add(self, indices, value, _mode):
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError('injected write failure')
            for index in indices:
                self.values[index] = value

        def remove(self, indices):
            for index in indices:
                self.values.pop(index, None)

    class FakeGroups(dict):
        def new(self, name):
            group = FakeGroup()
            self[name] = group
            return group

        def remove(self, group):
            for name, candidate in tuple(self.items()):
                if candidate is group:
                    del self[name]

    class FakeTarget:
        vertex_groups = FakeGroups()

    target = FakeTarget()
    target.vertex_groups['Existing'] = FakeGroup(fail_once=True)
    target.vertex_groups['Existing'].values[1] = 0.4
    try:
        apply_transfer_plan(target, [('New', 0, 0.2), ('Existing', 1, 0.3)])
    except RuntimeError as exc:
        assert 'injected' in str(exc)
    else:
        raise AssertionError('Injected write did not fail')
    assert 'New' not in target.vertex_groups
    assert target.vertex_groups['Existing'].values == {1: 0.4}


def main():
    for cls in WEIGHT_TRANSFER_CLASSES:
        bpy.utils.register_class(cls)
    register_weight_transfer_properties()
    try:
        rig_data = bpy.data.armatures.new('A Rig')
        rig = bpy.data.objects.new('A Rig', rig_data)
        bpy.context.collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name in ('Bone1', 'Bone2'):
            bone = rig_data.edit_bones.new(name)
            bone.head = (0, 0, 0)
            bone.tail = (0, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')
        rig.select_set(False)

        a = make_mesh('A', [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
        a.location.x = 2
        modifier = a.modifiers.new('Rig', 'ARMATURE')
        modifier.object = rig
        ag1 = a.vertex_groups.new(name='Bone1')
        ag1.add([1, 2], 1, 'REPLACE')
        ag2 = a.vertex_groups.new(name='Bone2')
        ag2.add([0, 1, 2, 3], 1, 'REPLACE')
        b = make_mesh('B', [(0.25, 0.25, 0), (0.75, 0.25, 0), (0.5, 0.75, 0)], [(0, 1, 2)])
        b.location.x = 2
        bg1 = b.vertex_groups.new(name='Bone1')
        bg1.add([0], 0.8, 'REPLACE')
        bg2 = b.vertex_groups.new(name='Bone2')
        bg2.add([0, 1, 2], 0.4, 'REPLACE')
        bg2.lock_weight = True
        only = b.vertex_groups.new(name='BOnly')
        only.add([0, 1, 2], 0.7, 'REPLACE')
        state = bpy.context.scene.vapb_weight_transfer
        state.source, state.armature, state.target = a, rig, b
        state.max_distance = 0.1
        assert bpy.ops.vapb.weight_mappings() == {'FINISHED'}
        assert len(state.mappings) == 2
        assert not any(m.confirmed for m in state.mappings)
        for mapping in state.mappings:
            mapping.confirmed = True
        mapping = state.mappings[0]
        original_name = mapping.target_name
        mapping.target_name = 'DifferentName'
        assert not mapping.confirmed
        mapping.target_name = original_name
        assert not mapping.confirmed
        mapping.confirmed = True
        mapping.source_name = 'WrongSource'
        assert not mapping.confirmed
        mapping.source_name = original_name
        mapping.confirmed = True
        source_before = [(g.name, tuple(round(weight(g, i), 6) for i in range(4))) for g in a.vertex_groups]
        b_before = [(g.name, tuple(round(weight(g, i), 6) for i in range(3))) for g in b.vertex_groups]
        coords_before = [tuple(v.co) for v in b.data.vertices]
        plan, stats = calculate_transfer(state)
        assert stats['matched'] == 3 and stats['unresolved'] == 0 and stats['locked'] == 3
        assert plan
        assert bpy.ops.vapb.weight_preview() == {'FINISHED'}
        assert b_before == [(g.name, tuple(round(weight(g, i), 6) for i in range(3))) for g in b.vertex_groups]
        assert coords_before == [tuple(v.co) for v in b.data.vertices]
        b.data.vertices[2].co.z = 0.2
        _distant_plan, distant = calculate_transfer(state)
        assert distant['matched'] == 2 and distant['unresolved'] == 1
        assert distant['unresolved_indices'] == (2,)
        a.select_set(True)
        assert bpy.ops.vapb.weight_select_unresolved() == {'FINISHED'}
        assert bpy.context.mode == 'EDIT_MESH'
        assert list(bpy.context.objects_in_mode) == [b]
        bpy.ops.object.mode_set(mode='OBJECT')
        assert [v.index for v in b.data.vertices if v.select] == [2]
        b.data.vertices[2].co.z = 0.0

        for vertex in b.data.vertices:
            vertex.select = vertex.index == 0
        state.scope = 'SELECTED'
        selected_plan, selected_stats = calculate_transfer(state)
        assert selected_stats['scope_vertices'] == 1 and selected_stats['matched'] == 1
        assert all(index == 0 for _name, index, _weight in selected_plan)
        state.mode = 'REPLACE'
        assert bpy.ops.vapb.weight_apply() == {'FINISHED'}
        assert abs(weight(bg1, 0) - 0.25) < 1e-5 and weight(bg1, 1) == 0
        state.scope = 'ALL'

        for mode, expected0 in [('REPLACE', 0.25), ('MERGE', 0.8), ('FILL_MISSING', 0.8)]:
            bg1.add([0], 0.8, 'REPLACE')
            state.mode = mode
            assert bpy.ops.vapb.weight_apply() == {'FINISHED'}
            assert abs(weight(bg1, 0) - expected0) < 1e-5, (mode, weight(bg1, 0))
            assert abs(weight(bg1, 1) - 0.75) < 1e-5
            assert all(abs(weight(bg2, i) - 0.4) < 1e-5 for i in range(3))
            assert all(abs(weight(only, i) - 0.7) < 1e-5 for i in range(3))
        assert source_before == [(g.name, tuple(round(weight(g, i), 6) for i in range(4))) for g in a.vertex_groups]
        assert coords_before == [tuple(v.co) for v in b.data.vertices]

        b_modifier = b.modifiers.new('Deform B', 'ARMATURE')
        b_modifier.object = rig
        depsgraph = bpy.context.evaluated_depsgraph_get()
        def evaluated_vertex():
            evaluated = b.evaluated_get(depsgraph)
            evaluated_mesh = evaluated.to_mesh()
            try:
                return tuple(evaluated_mesh.vertices[0].co)
            finally:
                evaluated.to_mesh_clear()
        rest_vertex = evaluated_vertex()
        rig.pose.bones['Bone1'].rotation_mode = 'XYZ'
        rig.pose.bones['Bone1'].rotation_euler.z = 0.5
        bpy.context.view_layer.update()
        posed_vertex = evaluated_vertex()
        assert sum(abs(x - y) for x, y in zip(rest_vertex, posed_vertex)) > 1e-4
        rig.pose.bones['Bone1'].rotation_euler.z = 0
        bpy.context.view_layer.update()
        assert_rollback()

        shared = bpy.data.objects.new('Shared B', b.data)
        bpy.context.collection.objects.link(shared)
        try:
            calculate_transfer(state)
        except ValueError as exc:
            assert '共有' in str(exc)
        else:
            raise AssertionError('Shared target was accepted')
        bpy.data.objects.remove(shared, do_unlink=True)
        other_scene = bpy.data.scenes.new('Other synthetic scene')
        other_scene.collection.objects.link(b)
        try:
            calculate_transfer(state)
        except ValueError:
            pass
        else:
            raise AssertionError('Object shared with another scene was accepted')
        other_scene.collection.objects.unlink(b)
        bpy.data.scenes.remove(other_scene)

        # All world X coordinates are positive. A rotated reference rig makes
        # its local X axis align with world Y, so only rig-local sign detects
        # the two actual crossings of the user-declared plane.
        rig.rotation_euler.z = math.pi / 2
        bpy.context.view_layer.update()
        a_lr = make_mesh('A plane test',
            [(0.1, 0.02, 0), (0.3, 0.02, 0), (0.3, 0.04, 0), (0.1, 0.04, 0)],
            [(0, 1, 2, 3)])
        a_lr.modifiers.new('Reference', 'ARMATURE').object = rig
        a_lr.vertex_groups.new(name='Bone1').add([0, 1, 2, 3], 1, 'REPLACE')
        b_lr = make_mesh('B plane test',
            [(0.15, -0.01, 0), (0.25, -0.01, 0), (0.2, 0.03, 0)],
            [(0, 1, 2)])
        state.source, state.target = a_lr, b_lr
        state.max_distance = 0.05
        assert bpy.ops.vapb.weight_mappings() == {'FINISHED'}
        assert len(state.mappings) == 1
        state.mappings[0].confirmed = True
        assert all((a_lr.matrix_world @ vertex.co).x > 0 for vertex in a_lr.data.vertices)
        assert all((b_lr.matrix_world @ vertex.co).x > 0 for vertex in b_lr.data.vertices)
        state.guard_declared_plane = False
        unguarded_plan, unguarded = calculate_transfer(state)
        assert unguarded['matched'] == 3 and unguarded['cross_plane'] == 0
        assert len(unguarded_plan) == 3
        state.guard_declared_plane = True
        lr_coords = [tuple(v.co) for v in b_lr.data.vertices]
        guarded_plan, guarded = calculate_transfer(state)
        assert guarded['matched'] == 1 and guarded['cross_plane'] == 2
        assert guarded['cross_plane_indices'] == (0, 1)
        assert len(guarded_plan) == 1 and guarded_plan[0][1] == 2
        assert bpy.ops.vapb.weight_preview() == {'FINISHED'}
        assert len(b_lr.vertex_groups) == 0
        assert [tuple(v.co) for v in b_lr.data.vertices] == lr_coords
        assert bpy.ops.vapb.weight_select_unresolved() == {'FINISHED'}
        bpy.ops.object.mode_set(mode='OBJECT')
        assert [v.index for v in b_lr.data.vertices if v.select] == [0, 1]
        assert bpy.ops.vapb.weight_apply() == {'FINISHED'}
        lr_group = b_lr.vertex_groups['Bone1']
        assert weight(lr_group, 0) == 0 and weight(lr_group, 1) == 0
        assert abs(weight(lr_group, 2) - 1) < 1e-5
        state.guard_declared_plane = False
        assert bpy.ops.vapb.weight_apply() == {'FINISHED'}
        assert all(abs(weight(lr_group, i) - 1) < 1e-5 for i in range(3))
        rig.rotation_euler.z = 0
        bpy.context.view_layer.update()
        state.source, state.target = a, b
        state.max_distance = 0.1
        assert bpy.ops.vapb.weight_mappings() == {'FINISHED'}
        for mapping in state.mappings:
            mapping.confirmed = True
        # Explicit pushes reproduce Blender's UI undo boundaries in a script.
        # Confirm restoration through the real undo system, then reacquire RNA
        # references, which are invalidated when the scene snapshot is restored.
        b['_weight_test_target'] = True
        bg1.add([0, 1, 2], 0.17, 'REPLACE')
        state.mode = 'REPLACE'
        bpy.ops.ed.undo_push(message='Before synthetic transfer')
        assert bpy.ops.vapb.weight_apply() == {'FINISHED'}
        bpy.ops.ed.undo_push(message='After synthetic transfer')
        assert bpy.ops.ed.undo() == {'FINISHED'}
        b = next(obj for obj in bpy.data.objects if obj.get('_weight_test_target'))
        assert all(abs(weight(b.vertex_groups['Bone1'], i) - 0.17) < 1e-5 for i in range(3))
        state = bpy.context.scene.vapb_weight_transfer
        state.target = None
        assert len(state.mappings) == 0
        print('WEIGHT_TRANSFER_RUNTIME_PASS modes=3 selected_scope=1 unresolved_selection=1 declared_plane_crossings=2 guarded=1 unguarded=1 posed_deformation=1 rollback=1 undo=1 stale_mapping_cleared=1 source_unchanged=1 shared_rejected=1')
    finally:
        unregister_weight_transfer_properties()
        for cls in reversed(WEIGHT_TRANSFER_CLASSES):
            bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
