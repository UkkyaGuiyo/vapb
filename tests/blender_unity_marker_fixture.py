"""Generate a public synthetic skin FBX for the Unity marker API probe.

Run Blender --factory-startup --background --python-exit-code 1 --python
this_file -- <destination.fbx>. All generated geometry is synthetic.
"""
from pathlib import Path
import sys

import bpy


def main():
    output = Path(sys.argv[sys.argv.index('--') + 1])
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing fixture')
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add()
    mesh = bpy.context.object
    mesh['_vapb_fbx_realization_id'] = 'synthetic-realization-001'
    mesh.shape_key_add(name='Basis')
    mesh.shape_key_add(name='SyntheticSmile').data[0].co.z += 0.25
    armature = bpy.data.objects.new('SyntheticRig', bpy.data.armatures.new('SyntheticRig'))
    bpy.context.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bone = armature.data.edit_bones.new('SyntheticBone')
    bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.vertex_groups.new(name='SyntheticBone').add(list(range(len(mesh.data.vertices))), 1, 'REPLACE')
    mesh.modifiers.new('SyntheticDeform', 'ARMATURE').object = armature
    mesh.parent = armature
    bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, use_custom_props=True,
        add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=False)
    if not output.is_file() or not output.stat().st_size:
        raise RuntimeError('Fixture output missing')
    print('UNITY_MARKER_FIXTURE=PASS')


if __name__ == '__main__':
    main()
