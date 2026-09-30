"""Actual public Scene corruption must be rejected by the full comparator.

CLI: BLEND PACKAGE WITNESS SOURCE PUBLIC CONTROLS ORACLE OUTPUT.
Reload before every control; original source files and saved Scene are immutable.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.tests.blender_hierarchy_snapshot import snapshot
from unitypackage_blender_importer.tests.hierarchy_comparator import compare
from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin


def main():
    blend, package, witness, source, public, controls, oracle_path, output = sys.argv[sys.argv.index('--')+1:]
    sha = hashlib.sha256(Path(package).read_bytes()).hexdigest()
    oracle = json.loads(Path(oracle_path).read_text())
    bpy.ops.wm.open_mainfile(filepath=blend)
    initial = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=True)
    skin, = initial['skins']  # Public control fixture deliberately has one Skin.
    prefab_guid = skin['renderer']['guid']
    assets = {prefab_guid: next(o['unity_asset_path'] for o in bpy.context.scene.objects if o.get('_vapb_semantic_id'))}
    results = []
    for control in ('renderer_owner', 'mesh_receipt', 'armature_target', 'bone_parent', 'root_bone', 'bone_attachment'):
        bpy.ops.wm.open_mainfile(filepath=blend)
        objects = list(bpy.context.scene.objects)
        mesh, rig = objects[skin['mesh_handle']], objects[skin['armature_handle']]
        leaf = skin['bones'][-1]
        carrier = objects[leaf['semantic_carrier_handle']]
        if control == 'renderer_owner':
            mesh.parent = next(o for o in objects if o.get('_vapb_renderer_occurrences'))
        elif control == 'mesh_receipt':
            mesh.data['_vapb_fbx_mesh_receipt_id'] = 'intentional-invalid-receipt'
        elif control == 'armature_target':
            mesh.modifiers[0].object = next(o for o in objects if o.type == 'ARMATURE' and o != rig)
        elif control == 'bone_parent':
            bone, = [b for b in rig.data.bones if str(b.get('_vapb_fbx_model_uid')) == leaf['model_uid']]
            channel = bone.name  # Already selected by native receipt.
            rig.hide_set(False)
            bpy.context.view_layer.objects.active = rig
            rig.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            rig.data.edit_bones[channel].parent = None
            bpy.ops.object.mode_set(mode='OBJECT')
        elif control == 'root_bone':
            mesh['_vapb_skin_root_frame_semantic_id'] = 'intentional-invalid-root'
        else:
            carrier.constraints[0].mute = True
        bpy.context.view_layer.update()
        try:
            observation = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=True)
        except ValueError:
            results.append(dict(control=control, result='REJECTED'))
            continue
        observed = snapshot(sha, assets, {'FINISHED'})
        observed['native_skin'] = observation
        result = compare(oracle, observed, sha)
        assert result['status'] == 'RED', 'Actual corruption falsely passed: ' + control
        results.append(dict(control=control, result='RED', categories=sorted(result['counts'])))
    assert len(results) == 6
    Path(output).write_text(json.dumps(dict(status='PASS', controls=results), indent=2), encoding='utf-8')
    print('HIERARCHY_ACTUAL_NEGATIVE_CONTROLS_PASS count=6')


if __name__ == '__main__':
    main()
