# SPDX-License-Identifier: GPL-3.0-or-later
"""First-party loose/coincident/degenerate CP controls with Shape deformation.

Uses VAPB_SHAPE_FIXTURE_FBX, a new external output. No identity expectations.
"""
import os
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_shape_identity_fixture import main as create_skin


def main():
    output = Path(os.environ['VAPB_SHAPE_FIXTURE_FBX'])
    assert not output.exists()
    create_skin()
    body, = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    data = bpy.data.meshes.new('AuthoredOmissionControl')
    data.from_pydata([(0,0,0), (1,0,0), (1,1,.2), (0,1,0), (1,0,0),
                     (3,3,3), (4,0,0), (4,1,0), (4,2,0)], [],
                    [(0,1,4,2,3), (6,7,8)])
    body.data = data
    body.vertex_groups.clear()
    body.vertex_groups.new(name='Hips').add([0,1,4,6], 1, 'REPLACE')
    body.vertex_groups.new(name='Spine').add([2,3,5,7,8], 1, 'REPLACE')
    body.shape_key_add(name='Basis')
    for label, index, delta in (('DuplicateCornerMoved',4,(.15,.04,.09)),
                               ('LoosePointMoved',5,(.27,-.1,.03)),
                               ('DegenerateFaceOpened',7,(.3,0,.12))):
        key = body.shape_key_add(name=label)
        key.data[index].co += __import__('mathutils').Vector(delta)
    bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True, bake_anim=False, add_leaf_bones=False)
    print('PUBLIC_CP_OMISSION_INPUT_CREATED points=9 shapes=3')


if __name__ == '__main__':
    main()
