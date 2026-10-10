# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 VAPB contributors
"""Normal package output from an existing owned animated Skin scene."""
from pathlib import Path
import sys,json,tarfile,hashlib
import bpy
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from strict_source_import import load_source_package
load_source_package(root)
from unitypackage_blender_importer.operators.export_unitypackage import export_model_skin_packages
source,output=map(Path,sys.argv[sys.argv.index('--')+1:])
original=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
assert len(meshes)==1
mesh=meshes[0];rig=mesh.modifiers[0].object;action=rig.animation_data.action
assert action is not None
manifest=export_model_skin_packages(bpy.context,meshes,output)
def files(package):
    rows={}
    with tarfile.open(package,'r:gz') as t:
        for node in t.getmembers():
            if node.name.endswith('/pathname'):
                p=t.extractfile(node).read().decode().strip();prefix=node.name.rsplit('/',1)[0]
                rows[p]=t.extractfile(prefix+'/asset').read()
    return rows
rows=files(output);data=json.loads(rows['Assets/VAPBExport/manifest.json']);task=data['reference_rebind_tasks'][0]
recipe=task['action_clip'];assert recipe['animated_bone_realization_ids'] and recipe['duration']==9/24
assert 'Assets/VAPBExport/Editor/VapbActionClipFinalizer.cs' in rows
carrier=rows['Assets/VAPBExport/ActionCarrier_'+recipe['carrier_guid']+'.fbx']
assert hashlib.sha256(carrier).hexdigest()==recipe['carrier_sha256']
assert rig.animation_data.action==action and hashlib.sha256(source.read_bytes()).hexdigest()==original
rig.location.x=0;rig.keyframe_insert(data_path='location',index=0,frame=1)
try:
    try: export_model_skin_packages(bpy.context,meshes,output.with_name('Refused.unitypackage'))
    except ValueError as error: assert 'ACTION_CARRIER_CHANNEL_UNSUPPORTED' in str(error)
    else: raise AssertionError('unsupported object Action exported')
    assert not output.with_name('Refused.unitypackage').exists()
finally:
    bag=action.layers[0].strips[0].channelbag(rig.animation_data.action_slot)
    for curve in list(bag.fcurves):
        if curve.data_path=='location':bag.fcurves.remove(curve)
rig.animation_data.action=None
try:
    plain=output.with_name('NonAnimated.unitypackage')
    export_model_skin_packages(bpy.context,meshes,plain)
    assert 'action_clip' not in json.loads(files(plain)['Assets/VAPBExport/manifest.json'])['reference_rebind_tasks'][0]
finally: rig.animation_data.action=action
assert rig.animation_data.action==action
print('VAPB_NORMAL_ACTION_PACKAGE_PASS carrier_helper=1 unsupported_refused=1 nonanimated=1 source_scene_unchanged=1')