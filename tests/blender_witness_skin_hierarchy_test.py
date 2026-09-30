"""Actual Bone motion must drive its witnessed semantic carrier/attachments.

CLI: BLEND WITNESS UNITY_ORACLE. Selection uses receipts and public Transform IDs.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    blend, witness_path, oracle_path = args[:3]
    bpy.ops.wm.open_mainfile(filepath=blend)
    witness = json.loads(Path(witness_path).read_text())
    oracle = json.loads(Path(oracle_path).read_text())
    check(witness, oracle)
    if len(args) == 4:
        for index, obj in enumerate(bpy.data.objects):
            obj.name = 'Renamed object ' + str(index)
        for data_index, data in enumerate(bpy.data.armatures):
            for index, bone in enumerate(data.bones):
                bone.name = 'Renamed bone ' + str(data_index) + '-' + str(index)
        check(witness, oracle)
        bpy.ops.wm.save_as_mainfile(filepath=args[3])
        bpy.ops.wm.open_mainfile(filepath=args[3])
        check(witness, oracle)
        print('WITNESS_SKIN_RENAME_SAVE_REOPEN_PASS')


def check(witness, oracle):
    objects = list(bpy.context.scene.objects)
    root, = [o for o in objects if o.get('_vapb_renderer_occurrences')]
    records = json.loads(root['_vapb_renderer_occurrences'])['records']
    transform_go = {n['transform']['localId']: n['gameObject']['localId'] for n in oracle['nodes']}
    moves = 0
    def belongs(obj):
        while obj is not None:
            if obj == root:
                return True
            obj = obj.parent
        return False
    for record in records:
        if record['renderer_class_id'] != 137:
            continue
        asset, = [a for a in witness['assets'] if a['asset_guid'] == record['mesh']['mesh_guid']]
        model, = [m for m in asset['models'] if any(r['mesh_local_id'] == str(record['mesh']['mesh_file_id']) for r in m['renderers'])]
        renderer, = [r for r in model['renderers'] if r['mesh_local_id'] == str(record['mesh']['mesh_file_id'])]
        mesh, = [o for o in objects if o.type == 'MESH'
            and o.get('_vapb_root_context_id') == record['root_context_id']
            and str(o.get('_vapb_fbx_model_uid')) == model['model_uid']]
        armature, = [m.object for m in mesh.modifiers if m.type == 'ARMATURE']
        for slot, row in enumerate(record['skin']['bones']):
            uid = renderer['skin']['ordered_bone_model_uids'][slot]
            bone, = [b for b in armature.pose.bones if str(b.bone.get('_vapb_fbx_model_uid')) == uid]
            carrier, = [o for o in objects if o.get('unity_prefab_file_id') == transform_go[row['transform_file_id']]
                and belongs(o)]
            bpy.context.view_layer.update()
            before = carrier.matrix_world.copy()
            bone_before = (armature.matrix_world @ bone.matrix).copy()
            children = list(carrier.children)
            child_before = [c.matrix_world.copy() for c in children]
            mode, original = bone.rotation_mode, bone.rotation_quaternion.copy()
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = Quaternion((1, 0, 0), 0.25) @ original
            armature.update_tag()
            bpy.context.view_layer.update()
            delta = armature.matrix_world @ bone.matrix @ bone_before.inverted()
            expected = delta @ before
            actual = carrier.matrix_world
            difference = lambda a, b: max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
            assert difference(expected, before) > 0.01, 'Native control motion did not execute'
            tolerance = lambda a,b: 2e-5 + 1e-6 * max(abs(v) for matrix in (a,b) for line in matrix for v in line)
            assert difference(actual, expected) <= tolerance(actual, expected), 'Witnessed semantic Bone carrier does not follow native Bone'
            for child, position in zip(children, child_before):
                expected_child = delta @ position
                assert difference(child.matrix_world, expected_child) <= tolerance(child.matrix_world, expected_child), 'Bone attachment motion diverged'
            bone.rotation_quaternion, bone.rotation_mode = original, mode
            armature.update_tag()
            bpy.context.view_layer.update()
            moves += 1
    assert moves, 'No witnessed native Skin motion tested'
    print('WITNESS_SKIN_HIERARCHY_PASS moves=' + str(moves))


if __name__ == '__main__':
    main()
