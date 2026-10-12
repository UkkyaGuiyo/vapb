"""One owned imported Shape rename with zero-default source; real import/save/reopen/export, no receipt repair."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
repo = Path(args[args.index('--repo') + 1])
work = Path(args[args.index('--work') + 1])
phase = args[args.index('--phase') + 1]
run = work / phase


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (run / name).write_text(json.dumps(value, indent=2), encoding='utf-8')


strict = load(repo / 'tests/strict_source_import.py', '_strict')
addon = strict.load_source_package(repo)
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter
from unitypackage_blender_importer.blender.fbx_receipt import validate_shape_receipts
from unitypackage_blender_importer.blender.fbx_witness import source_shape_channel_uids


def state(obj):
    rig = next(m.object for m in obj.modifiers if m.type == 'ARMATURE')
    keys = obj.data.shape_keys
    return dict(
        vertices=[list(v.co) for v in obj.data.vertices],
        faces=[list(p.vertices) for p in obj.data.polygons],
        face_materials=[p.material_index for p in obj.data.polygons],
        uv=[list(x.uv) for x in obj.data.uv_layers.active.data],
        weights=[[[g.group, g.weight] for g in v.groups] for v in obj.data.vertices],
        groups=[g.name for g in obj.vertex_groups],
        matrix=[list(row) for row in obj.matrix_world],
        rig_matrix=[list(row) for row in rig.matrix_world],
        bones=[dict(uid=str(b.get('_vapb_fbx_model_uid', '')),
                    realization=str(b.get('_vapb_fbx_bone_realization_id', '')),
                    parent_uid=str(b.parent.get('_vapb_fbx_model_uid', '')) if b.parent else '',
                    matrix=[list(row) for row in b.matrix_local], head=list(b.head_local), tail=list(b.tail_local), connected=b.use_connect) for b in rig.data.bones],
        materials=[dict(guid=str(s.material.get('unity_material_guid', '')),
                        file_id=str(s.material.get('unity_material_file_id', ''))) for s in obj.material_slots],
        channels=[dict(name=k.name, value=k.value, relative=keys.key_blocks.find(k.relative_key.name),
                       points=[list(p.co) for p in k.data]) for k in keys.key_blocks],
        shape_receipt=keys['_vapb_fbx_shape_receipts'],
        shape_receipt_sha256=keys['_vapb_fbx_shape_receipt_sha256'],
        model_uid=str(obj.get('_vapb_fbx_model_uid', '')),
        geometry_uid=str(obj.get('_vapb_fbx_geometry_uid', '')),
        realization_id=str(obj.get('_vapb_fbx_realization_id', '')))


addon.register()
try:
    package = work / 'Source.unitypackage'
    original_hash = sha(package)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    assert bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode='RECONSTRUCT',
        keep_extracted=True, source_storage_directory=str(work/'Sources')) == {'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    rig = next(m.object for m in obj.modifiers if m.type == 'ARMATURE')
    before = state(obj)
    child, = [b for b in rig.data.bones if b.parent]
    selected_uid = str(child.get('_vapb_fbx_model_uid'))
    selected_name = child.name
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bone = rig.data.edit_bones[selected_name]
    from mathutils import Vector
    delta = Vector((0.025, 0.0, 0.0))
    edit_bone.head += delta
    edit_bone.tail += delta
    bpy.ops.object.mode_set(mode='OBJECT')
    after = state(obj)
    expected = json.loads(json.dumps(before))
    index, = [i for i,b in enumerate(before['bones']) if b['uid']==selected_uid]
    assert before['bones'][index]['matrix'] != after['bones'][index]['matrix']
    # Standard connected child edit propagates its head move to the parent tail.
    assert before['bones'][index]['connected']
    parent_index, = [i for i,b in enumerate(before['bones']) if b['uid']==before['bones'][index]['parent_uid']]
    for i in [index,parent_index]:
        for field in ['matrix','head','tail']:
            expected['bones'][i][field]=after['bones'][i][field]
    assert after==expected
    for i,field in [(index,'head'),(index,'tail'),(parent_index,'tail')]:
        assert max(abs(after['bones'][i][field][j]-before['bones'][i][field][j]-delta[j]) for j in range(3))<1e-7
    assert after['bones'][parent_index]['head']==before['bones'][parent_index]['head']
    saved = work/'Authored.blend'
    assert bpy.ops.wm.save_as_mainfile(filepath=str(saved)) == {'FINISHED'}
    saved_hash = sha(saved)
    assert bpy.ops.wm.open_mainfile(filepath=str(saved)) == {'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert state(obj) == after
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    output = work/'BoneRestOutput.unitypackage'
    assert not output.exists()
    result = dict(selected_bone_uid=selected_uid, selected_index=index,
        changed_field='child Bone rest matrix by EditMode head/tail translation',
        delta_blender_m=[0.025,0,0], before=before, after=after,
        reopen_state_exact=True, blend_sha256=saved_hash,
        source_package_sha256=original_hash, source_fbx_sha256=sha(work/'Source.fbx'))
    try:
        outcome = bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))
    except RuntimeError as exc:
        result.update(status='REJECTED',stage='normal_export',error=str(exc),partial_output=output.exists())
    else:
        assert outcome == {'FINISHED'} and state(obj) == after
        assets = RawAssetRepository(output).read_all()
        by = {a.guid:a for a in assets}
        assert all(by[a.guid].asset_bytes==a.asset_bytes and by[a.guid].meta_bytes==a.meta_bytes
            for a in RawAssetRepository(package).read_all())
        manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'))
        task, = manifest['reference_rebind_tasks']
        assert task['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1'
        (run/'Export.fbx').write_bytes(by[task['model_guid']].asset_bytes)
        write('manifest.json',manifest)
        result.update(status='PASS',stage='normal_export',output_sha256=sha(output),
            export_fbx_sha256=sha(run/'Export.fbx'),task=task)
    assert sha(package)==original_hash and sha(saved)==saved_hash and state(obj)==after
    result.update(source_preserved=True,edited_state_preserved=True)
    write('result.json',result)
finally:
    addon.unregister()
