"""Actual Object/Bone/KeyBlock rename + save/reopen, using immutable baseline locators.

BLEND BASELINE_SNAPSHOT PACKAGE WITNESS SOURCE PACKAGE_OBS CONTROL OUTPUT_DIR.
Both observers run after reopening. No Unity-derived native state is injected.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_hierarchy_snapshot import snapshot
from unitypackage_blender_importer.tests.blender_shape_snapshot import observe
from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin


def main():
    blend, baseline_file, package, witness, source, public, controls, output = map(Path, sys.argv[sys.argv.index('--')+1:])
    baseline = json.loads(baseline_file.read_text(encoding='utf-8-sig'))
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    assert baseline['package_sha256'] == sha and baseline['import_result'] == ['FINISHED']
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    seen_rigs, seen_keys = set(), set()
    for index, obj in enumerate(bpy.context.scene.objects):
        obj.name = 'RenamedObject_%d' % index
        if obj.type == 'ARMATURE' and obj.data.as_pointer() not in seen_rigs:
            seen_rigs.add(obj.data.as_pointer())
            for i, bone in enumerate(obj.data.bones): bone.name = 'RenamedBone_%d_%d' % (index, i)
        if obj.type == 'MESH' and obj.data.shape_keys and obj.data.shape_keys.as_pointer() not in seen_keys:
            seen_keys.add(obj.data.shape_keys.as_pointer())
            for i, key in enumerate(obj.data.shape_keys.key_blocks): key.name = 'RenamedKey_%d_%d' % (index, i)
    saved = output / 'renamed.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(saved))
    bpy.ops.wm.open_mainfile(filepath=str(saved))
    shape = dict(package_sha256=sha, objects=observe())
    full = snapshot(sha, baseline['assets'], {'FINISHED'})
    full['native_skin'] = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=True)
    (output/'shape_snapshot.json').write_text(json.dumps(shape, indent=2), encoding='utf-8')
    (output/'blender_snapshot.json').write_text(json.dumps(full, indent=2), encoding='utf-8')
    print('SHAPE_REOPEN_OBSERVED source_revision_checked=1')


if __name__ == '__main__':
    main()
