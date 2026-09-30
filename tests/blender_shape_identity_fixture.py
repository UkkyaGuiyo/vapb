"""First-party asymmetric three-channel Skin input; no expected-output mapper."""
import os
from pathlib import Path

import bpy


def main():
    output = Path(os.environ['VAPB_SHAPE_FIXTURE_FBX'])
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    rig = bpy.data.objects.new('Rig', bpy.data.armatures.new('RigData'))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    hips = rig.data.edit_bones.new('Hips')
    hips.head, hips.tail = (0, 0, 0), (0, 0, .9)
    spine = rig.data.edit_bones.new('Spine')
    spine.head, spine.tail, spine.parent = hips.tail, (0, 0, 1.8), hips
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, .9))
    body = bpy.context.object
    body.name, body.parent = 'Body', rig
    body.scale = (.4, .3, 1.8)
    for channel in ('Hips', 'Spine'):
        group = body.vertex_groups.new(name=channel)
        group.add([v.index for v in body.data.vertices if (v.co.z < 0) == (channel == 'Hips')], 1, 'REPLACE')
    body.modifiers.new('Skin', 'ARMATURE').object = rig
    body.shape_key_add(name='Basis')
    for label, changes in (
        ('Diagnostic_A', {0: (.31, -.12, .07), 1: (.08, .03, -.11)}),
        ('Diagnostic_B', {4: (-.16, .23, .09), 6: (.05, -.07, .19)}),
        ('Diagnostic_C', {2: (.13, .04, -.17), 5: (-.09, -.21, .06), 7: (.03, .18, .11)}),
    ):
        key = body.shape_key_add(name=label)
        for index, delta in changes.items():
            key.data[index].co += __import__('mathutils').Vector(delta)
    rig.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True, bake_anim=False, add_leaf_bones=False)
    print('PUBLIC_SHAPE_INPUT_CREATED channels=3')


if __name__ == '__main__':
    main()
