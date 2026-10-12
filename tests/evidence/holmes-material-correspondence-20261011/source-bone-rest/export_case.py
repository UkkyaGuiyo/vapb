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
    saved = Path(args[args.index('--blend')+1])
    original_blend_hash=sha(saved)
    expected=json.loads(Path(args[args.index('--expected')+1]).read_text(encoding='utf-8'))
    assert bpy.ops.wm.open_mainfile(filepath=str(saved))=={'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type=='MESH']
    before=state(obj)
    assert before==expected['after']
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    output=work/'BoneRestGreenOutput.unitypackage';assert not output.exists()
    assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))=={'FINISHED'}
    assert state(obj)==before and sha(saved)==original_blend_hash
    assets=RawAssetRepository(output).read_all();by={a.guid:a for a in assets}
    source=Path(args[args.index('--source')+1]);assert sha(source)==expected['source_package_sha256']
    assert all(by[a.guid].asset_bytes==a.asset_bytes and by[a.guid].meta_bytes==a.meta_bytes for a in RawAssetRepository(source).read_all())
    manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'))
    task, = manifest['reference_rebind_tasks'];assert task['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1' and not task.get('action_clip')
    (run/'Export.fbx').write_bytes(by[task['model_guid']].asset_bytes)
    write('manifest.json',manifest)
    deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
    try:
        assert len(mesh.vertices)==len(obj.data.vertices)
        points=[list(evaluated.matrix_world@v.co) for v in mesh.vertices]
    finally:evaluated.to_mesh_clear()
    write('blender-evaluated.json',dict(points=points,blend_sha256=original_blend_hash,output_sha256=sha(output),state=before))
    write('result.json',dict(status='PASS',existing13_state_exact=True,original_blend_hash=original_blend_hash,source_preserved=True,source_package_sha256=sha(source),output_sha256=sha(output),export_fbx_sha256=sha(run/'Export.fbx'),task=task))
finally:
    addon.unregister()
