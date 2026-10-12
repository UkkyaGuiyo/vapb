"""First owned Basis-relative Shape on shape-free input; real import/save/reopen/export, no receipt repair."""
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
                    matrix=[list(row) for row in b.matrix_local]) for b in rig.data.bones],
        materials=[dict(guid=str(s.material.get('unity_material_guid', '')),
                        file_id=str(s.material.get('unity_material_file_id', ''))) for s in obj.material_slots],
        channels=[] if keys is None else [dict(name=k.name, value=k.value, relative=keys.key_blocks.find(k.relative_key.name),
                       points=[list(p.co) for p in k.data]) for k in keys.key_blocks],
        shape_receipt=None if keys is None else keys.get('_vapb_fbx_shape_receipts'),
        shape_receipt_sha256=None if keys is None else keys.get('_vapb_fbx_shape_receipt_sha256'),
        model_uid=str(obj.get('_vapb_fbx_model_uid', '')),
        geometry_uid=str(obj.get('_vapb_fbx_geometry_uid', '')),
        realization_id=str(obj.get('_vapb_fbx_realization_id', '')))


addon.register()
try:
    package = work / 'Source.unitypackage'
    original_hash = sha(package)
    saved = work / 'Authored.blend'
    if phase == 'edit':
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        assert bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode='RECONSTRUCT',
            keep_extracted=True, source_storage_directory=str(work / 'Sources')) == {'FINISHED'}
    else:
        assert bpy.ops.wm.open_mainfile(filepath=str(saved)) == {'FINISHED'}
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    before = state(obj)
    assert len(before['channels']) == (0 if phase == 'edit' else 2) and len(before['bones']) == 2
    if phase == 'edit':
        assert obj.data.shape_keys is None and before['channels'] == []
        basis = obj.shape_key_add(name='Basis', from_mix=False)
        key = obj.shape_key_add(name='Authored_First', from_mix=False)
        key.relative_key = basis
        key.value = 0.0
        cp = 0
        old = list(key.data[cp].co)
        key.data[cp].co.z += .04
        after = state(obj)
        assert {k:v for k,v in before.items() if k != 'channels'} == {k:v for k,v in after.items() if k != 'channels'}
        assert len(after['channels']) == 2 and after['channels'][1]['relative'] == 0 and after['channels'][1]['value'] == 0.0
        assert after['channels'][0]['points'] == before['vertices']
        assert all(after['channels'][1]['points'][i] == before['vertices'][i] for i in range(len(key.data)) if i != cp)
        assert bpy.ops.wm.save_as_mainfile(filepath=str(saved)) == {'FINISHED'}
        write('state.json', after)
        write('result.json', dict(status='PASS', new_key_index=1, selected_cp=cp,
            original_shape_state_absent=True, original_receipt_unmodified=True,
            before_point=old, after_point=list(key.data[cp].co), before=before, after=after,
            source_package_sha256=original_hash, blend_sha256=sha(saved)))
    else:
        assert before == json.loads((work / 'edit/state.json').read_text(encoding='utf-8'))
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        output = work / ('FirstShapeGreenOutput.unitypackage' if phase == 'green-export' else 'FirstShapeOutput.unitypackage')
        assert not output.exists()
        try:
            outcome = bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))
        except RuntimeError as exc:
            write('result.json', dict(status='REJECTED', stage='normal_export', error=str(exc),
                source_preserved=sha(package) == original_hash, partial_output=output.exists(),
                reopen_state_exact=True))
        else:
            assert outcome == {'FINISHED'} and state(obj) == before
            assets = RawAssetRepository(output).read_all()
            by = {a.guid:a for a in assets}
            assert all(by[a.guid].asset_bytes == a.asset_bytes and by[a.guid].meta_bytes == a.meta_bytes
                       for a in RawAssetRepository(package).read_all())
            manifest = json.loads(next(a.asset_bytes for a in assets if a.pathname == 'Assets/VAPBExport/manifest.json'))
            task, = manifest['reference_rebind_tasks']
            assert task['kind'] == 'RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1'
            (run / 'Export.fbx').write_bytes(by[task['model_guid']].asset_bytes)
            write('manifest.json', manifest)
            write('result.json', dict(status='PASS', stage='normal_export', reopen_state_exact=True,
                source_preserved=True, source_package_sha256=original_hash,
                output_sha256=sha(output), export_fbx_sha256=sha(run / 'Export.fbx'), task=task, state=before))
    assert sha(package) == original_hash
finally:
    addon.unregister()
