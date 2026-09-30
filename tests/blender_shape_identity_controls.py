"""Actual corruptions and rename/reopen, independent shape/hierarchy verdicts.

Arguments: BLEND PACKAGE WITNESS SOURCE PACKAGE_OBS CONTROL SHAPE_ORACLE
HIERARCHY_ORACLE OUTPUT_DIR. Public fixture only; source cache is checked too.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_shape_snapshot import observe
from unitypackage_blender_importer.tests.shape_comparator import compare_shapes
from unitypackage_blender_importer.tests.blender_hierarchy_snapshot import snapshot
from unitypackage_blender_importer.tests.hierarchy_comparator import compare
from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin


def main():
    blend, package, witness, source, public, controls, shape_oracle, hierarchy_oracle, output = map(Path, sys.argv[sys.argv.index('--')+1:])
    output.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    oracle = json.loads(shape_oracle.read_text(encoding='utf-8-sig'))
    hierarchy = json.loads(hierarchy_oracle.read_text(encoding='utf-8-sig'))
    proof = json.loads(witness.read_text(encoding='utf-8-sig'))

    def shapes():
        return dict(package_sha256=sha, objects=observe())

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    assert compare_shapes(oracle, shapes(), proof)['status'] == 'GREEN'
    source_values = [[k.value for k in obj.data.shape_keys.key_blocks]
        for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.data.shape_keys
        and not obj.get('_vapb_fbx_source_realization_id')]
    assert source_values and all(values[1:] == [1, 1, 1] for values in source_values)
    members = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_shape_weight_occurrence_id')]
    assert len(members) == 2 and members[0].data.shape_keys != members[1].data.shape_keys
    results = []
    for control in ('wrong_receipt', 'duplicate_claim', 'missing_key', 'same_name_decoy',
                    'swapped_identity', 'wrong_renderer', 'weight_value', 'shared_occurrences', 'stale_revision'):
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        members = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_shape_weight_occurrence_id')]
        target = members[0]
        keys = target.data.shape_keys
        receipt = json.loads(keys['_vapb_fbx_shape_receipts'])
        altered_proof = json.loads(json.dumps(proof))
        if control == 'wrong_receipt': receipt['channels'][0]['channel_uid'] += 1
        elif control == 'duplicate_claim': receipt['channels'][1]['channel_uid'] = receipt['channels'][0]['channel_uid']
        elif control == 'swapped_identity':
            receipt['channels'][0]['key_index'], receipt['channels'][1]['key_index'] = receipt['channels'][1]['key_index'], receipt['channels'][0]['key_index']
        elif control == 'missing_key': target.shape_key_remove(keys.key_blocks[-1])
        elif control == 'same_name_decoy': target.shape_key_add(name=keys.key_blocks[1].name)
        elif control == 'wrong_renderer': target['_vapb_shape_weight_occurrence_id'] = members[1]['_vapb_shape_weight_occurrence_id']
        elif control == 'weight_value': keys.key_blocks[1].value += .1
        elif control == 'shared_occurrences': members[1].data = target.data
        else: altered_proof['assets'][0]['source_meta_sha256'] = '0'*64
        if control in ('wrong_receipt', 'duplicate_claim', 'swapped_identity'):
            keys['_vapb_fbx_shape_receipts'] = json.dumps(receipt)
        try:
            verdict = compare_shapes(oracle, shapes(), altered_proof)
            assert verdict['status'] == 'RED', control + ' false PASS'
            results.append(dict(control=control, result=verdict))
        except ValueError:
            results.append(dict(control=control, result='REJECTED'))
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    for index, obj in enumerate(bpy.context.scene.objects):
        obj.name = 'RenamedObject_%d' % index
        if obj.type == 'ARMATURE':
            for i, bone in enumerate(obj.data.bones): bone.name = 'RenamedBone_%d' % i
        if obj.type == 'MESH' and obj.data.shape_keys:
            for i, key in enumerate(obj.data.shape_keys.key_blocks): key.name = 'RenamedKey_%d' % i
    saved = output / 'renamed.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(saved))
    bpy.ops.wm.open_mainfile(filepath=str(saved))
    observed = shapes()
    shape_result = compare_shapes(oracle, observed, proof)
    assert shape_result['status'] == 'GREEN'
    baseline = json.loads((blend.parent / 'blender_snapshot.json').read_text(encoding='utf-8-sig'))
    assert baseline['package_sha256'] == sha
    assets = baseline['assets']
    native = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=True)
    full = snapshot(sha, assets, {'FINISHED'})
    full['native_skin'] = native
    full_result = compare(hierarchy, full, sha)
    (output/'reopened_full_comparison.json').write_text(json.dumps(full_result, indent=2), encoding='utf-8')
    assert full_result['hierarchy_status'] == 'GREEN'
    (output/'reopened_shape_snapshot.json').write_text(json.dumps(observed, indent=2), encoding='utf-8')
    (output/'reopened_hierarchy_snapshot.json').write_text(json.dumps(full, indent=2), encoding='utf-8')
    (output/'result.json').write_text(json.dumps(dict(status='PASS', negative_controls=results,
        shape_result=shape_result, hierarchy_result={k:full_result[k] for k in ('hierarchy_status','geometry_status','hierarchy_counts','geometry_counts')},
        source_cache_unchanged=True), indent=2), encoding='utf-8')
    print('SHAPE_ACTUAL_CONTROLS_PASS count=%d rename_reopen=PASS' % len(results))


if __name__ == '__main__':
    main()
