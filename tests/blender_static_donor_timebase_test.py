"""Native FBX import regression using self-authored Skin/Action and donors.

Blender --background --factory-startup --python this_file -- output_dir repo_root
"""
from pathlib import Path
import json
import sys
import types

import bpy
from io_scene_fbx import parse_fbx


def channels(rig):
    action = rig.animation_data.action
    slot = rig.animation_data.action_slot
    return [(f.data_path, f.array_index,
             [(tuple(k.co), k.interpolation, tuple(k.handle_left), tuple(k.handle_right),
               k.handle_left_type, k.handle_right_type) for k in f.keyframe_points])
            for layer in action.layers for strip in layer.strips
            for f in strip.channelbag(slot).fcurves]


def existing_skin():
    arm = bpy.data.armatures.new('OwnedRig')
    rig = bpy.data.objects.new('OwnedRig', arm)
    bpy.context.collection.objects.link(rig)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = arm.edit_bones.new('OwnedBone')
    bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    pose = rig.pose.bones[0]
    pose.location = (0, 0, 0)
    pose.keyframe_insert('location', frame=1)
    pose.location = (0.25, 0, 0)
    pose.keyframe_insert('location', frame=13)
    mesh_data = bpy.data.meshes.new('OwnedSkin')
    mesh_data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    mesh = bpy.data.objects.new('OwnedSkin', mesh_data)
    bpy.context.collection.objects.link(mesh)
    mesh.vertex_groups.new(name=arm.bones[0].name).add([0, 1, 2], 1.0, 'REPLACE')
    mesh.modifiers.new('OwnedSkin', 'ARMATURE').object = rig
    uv = mesh_data.uv_layers.new()
    for item, value in zip(uv.data, ((0, 0), (1, 0), (0, 1))):
        item.uv = value
    bpy.context.scene.frame_set(1)

    def state():
        return (mesh.as_pointer(), mesh_data.as_pointer(), rig.as_pointer(), arm.as_pointer(),
                rig.animation_data.action.as_pointer(), channels(rig),
                [tuple(v.co) for v in mesh_data.vertices],
                [tuple(p.vertices) for p in mesh_data.polygons],
                [tuple(x.uv) for x in uv.data],
                [[(g.group, g.weight) for g in v.groups] for v in mesh_data.vertices],
                [tuple(x) for x in mesh.matrix_world], [tuple(x) for x in rig.matrix_world],
                [(b.parent.as_pointer() if b.parent else None, b.use_connect,
                  [tuple(x) for x in b.matrix_local]) for b in arm.bones])
    return rig, state


def main():
    work, repo = map(Path, sys.argv[sys.argv.index('--') + 1:][:2])
    work.mkdir(exist_ok=False)
    package = types.ModuleType('unitypackage_blender_importer')
    package.__path__ = [str(repo)]
    sys.modules[package.__name__] = package
    from unitypackage_blender_importer.blender.fbx_importer import import_fbx

    donors = {}
    for animated in (False, True):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps, scene.render.fps_base = 30, 1.0
        scene.frame_start, scene.frame_end = 1, 13
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        if animated:
            obj.keyframe_insert('location', frame=1)
            obj.location.x = 1.0
            obj.keyframe_insert('location', frame=13)
        path = work / ('Animated.fbx' if animated else 'Static.fbx')
        assert bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
            object_types={'MESH'}, bake_anim=animated,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False) == {'FINISHED'}
        tree, _ = parse_fbx.parse(str(path), use_namedtuple=True)
        objects, = [n for n in tree.elems if n.id == b'Objects']
        counts = {kind: sum(n.id == kind.encode() for n in objects.elems)
                  for kind in ('AnimationStack', 'AnimationLayer', 'AnimationCurveNode', 'AnimationCurve')}
        assert bool(counts['AnimationCurve']) == animated
        donors[animated] = path, counts

    rows = []
    for label, animated, prior_action in (
        ('STATIC_DONOR_EXISTING_ACTION', False, True),
        ('INITIAL_STATIC_IMPORT', False, False),
        ('ANIMATED_DONOR_EXISTING_ACTION', True, True),
    ):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps, scene.render.fps_base = 25, 1.0
        rig, state = existing_skin() if prior_action else (None, None)
        baseline = state() if state else None
        old_actions = {a.as_pointer() for a in bpy.data.actions}
        imported = import_fbx(donors[animated][0])
        expected = (25, 1.0) if prior_action and not animated else (30, 1.0)
        actual = scene.render.fps, scene.render.fps_base
        unchanged = state() == baseline if state else True
        new_actions = len({a.as_pointer() for a in bpy.data.actions} - old_actions)
        row = dict(case=label, expected_timebase=list(expected), actual_timebase=list(actual),
                   prior_skin_bone_action_state_exact=unchanged,
                   prior_key_span_seconds=12/(actual[0]/actual[1]) if prior_action else None,
                   incoming_animated=animated, incoming_animation_objects=donors[animated][1],
                   imported_objects=len(imported), new_actions=new_actions)
        row['pass'] = actual == expected and unchanged and bool(imported) and bool(new_actions) == animated
        rows.append(row)
    with (work / 'result.json').open('x', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)
    print('STATIC_DONOR_TIMEBASE', [(r['case'], r['actual_timebase'], r['pass']) for r in rows])
    assert all(r['pass'] for r in rows), 'STATIC_DONOR_RETIMES_UNTOUCHED_ACTION'


if __name__ == '__main__':
    main()
