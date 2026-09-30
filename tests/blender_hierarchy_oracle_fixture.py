"""Generate a first-party synthetic skin FBX for the independent Unity Oracle.

Run Blender factory-startup/background with --python-exit-code 1 and supply
VAPB_HIERARCHY_MODEL (an output FBX path outside the repository).
This generates input only; it does not assert VAPB hierarchy parity.
"""
import os
from pathlib import Path

import bpy


def main():
    path = Path(os.environ['VAPB_HIERARCHY_MODEL'])
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    rig = bpy.data.objects.new('Rig', bpy.data.armatures.new('RigData'))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    hips = rig.data.edit_bones.new('Hips')
    hips.head = (0, 0, 0)
    hips.tail = (0, 0, 0.9)
    spine = rig.data.edit_bones.new('Spine')
    spine.head = hips.tail
    spine.tail = (0, 0, 1.8)
    spine.parent = hips
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.9))
    body = bpy.context.object
    body.name = 'Body'
    body.scale = (0.4, 0.3, 1.8)
    body.parent = rig
    for bone in ('Hips', 'Spine'):
        group = body.vertex_groups.new(name=bone)
        group.add([v.index for v in body.data.vertices
                   if (v.co.z < 0) == (bone == 'Hips')], 1, 'REPLACE')
    body.modifiers.new('Skin', 'ARMATURE').object = rig
    rig.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
                             bake_anim=False, add_leaf_bones=False)
    print('VAPB_HIERARCHY_FIXTURE_PASS')


if __name__ == '__main__':
    main()
