"""HOLMES06: standard import, native replacement Cube, persistence/final-state export."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
import bpy

sys.dont_write_bytecode = True
GUIDS = ['afd253dd071f7e5469e24392cdbf181c', '70c1cb3bd3a723141a677eca237e252c',
         '242d369718abeb942873ec054737cf94', '4d7af3be41387054c9f86b68e180d9e7']
ORDER = [2, 0, 3, 1]
WANTED = {'+X': 0, '-X': 1, '+Y': 2, '-Y': 2, '+Z': 3, '-Z': 3}


def main():
    ap = argparse.ArgumentParser()
    for name in ('repo', 'work'): ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--phase', choices=['replace', 'export'], required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    repo, work = args.repo, args.work
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(instruction_id='HOLMES-20261011-06', phase=args.phase,
                  blender_version=bpy.app.version_string, status='NOT_RUN')
    stage = 'BLENDER_PROVENANCE'
    try:
        spec = importlib.util.spec_from_file_location('unitypackage_blender_importer', repo / '__init__.py', submodule_search_locations=[str(repo)])
        addon = importlib.util.module_from_spec(spec); sys.modules[spec.name] = addon
        spec.loader.exec_module(addon); addon.register()
        from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
        fixture = repo / 'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan'
        frozen = json.loads((fixture / 'input-and-predictions.json').read_text(encoding='utf-8-sig'))
        assert all(sha(fixture / name) == digest for name, digest in frozen['asset_sha256'].items())
        original = fixture / 'OrderedSix.unitypackage'
        assert sha(original) == frozen['package_sha256']
        source = {a.guid: a for a in RawAssetRepository(original).read_all()}
        package_id = 'sha256:' + sha(original)
        if args.phase == 'replace':
            bpy.ops.wm.read_factory_settings(use_empty=True)
            assert bpy.ops.import_scene.unitypackage(filepath=str(original), import_mode='RECONSTRUCT', prefab_choice='AUTO', source_storage_directory=str(work / 'archive')) == {'FINISHED'}
            imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            assert imported, 'Standard Import produced no Mesh'
            report['imported_mesh_count'] = len(imported)
            report['old_slot_guids'] = [[str(s.material.get('unity_material_guid', '')) for s in old.material_slots if s.material] for old in imported]
            report['available_unity_materials'] = [dict(guid=str(m.get('unity_material_guid', '')), file_id=str(m.get('unity_material_file_id', '')), package_id=str(m.get('unity_source_package_id', ''))) for m in bpy.data.materials if m.get('unity_material_guid')]
            mats = {}
            for guid in GUIDS:
                matches = [m for m in bpy.data.materials if str(m.get('unity_material_guid', '')) == guid and str(m.get('unity_material_file_id', '')) == '2100000' and m.get('unity_source_package_id') == package_id]
                assert len(matches) == 1, 'Missing or ambiguous retained Unity Material ' + guid
                mats[guid] = matches[0]
            assert set(mats) == set(GUIDS)
            providers = []
            for guid in GUIDS:
                mat, asset = mats[guid], source[guid]
                assert mat['unity_source_package_id'] == package_id
                assert str(mat['unity_material_file_id']) == '2100000'
                assert re.search(rb'(?m)^---\s+!u!21\s+&2100000\b', asset.asset_bytes)
                assert ('guid: ' + guid).encode() in asset.meta_bytes
                providers.append(dict(guid=guid, file_id='2100000', source_package_id=package_id,
                                      asset_sha256=hashlib.sha256(asset.asset_bytes).hexdigest(), meta_sha256=hashlib.sha256(asset.meta_bytes).hexdigest()))
            old_data = {old.data.as_pointer(): old.data for old in imported}
            report['old_receipt_present_before_delete'] = [bool(old.get('_vapb_fbx_material_receipt')) for old in imported]
            for old in imported: bpy.data.objects.remove(old, do_unlink=True)
            for data in old_data.values():
                assert data.users == 0
                bpy.data.meshes.remove(data)
            bpy.ops.mesh.primitive_cube_add(size=2, calc_uvs=True, location=(0, 0, 0))
            obj = bpy.context.active_object
            assert not list(obj.keys()) and not list(obj.data.keys()) and obj.parent is None
            for index in ORDER: obj.data.materials.append(mats[GUIDS[index]])
            for face in obj.data.polygons:
                axis = max(range(3), key=lambda i: abs(face.normal[i]))
                label = ('+' if face.normal[axis] > 0 else '-') + 'XYZ'[axis]
                face.material_index = ORDER.index(WANTED[label])
            report.update(standard_import='PASS', providers=providers, imported_mesh_object_and_data_deleted=True)
        else:
            assert bpy.ops.wm.open_mainfile(filepath=str(work / 'Replacement.blend')) == {'FINISHED'}
            meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            assert len(meshes) == 1
            obj = meshes[0]
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
        assert not obj.modifiers and not obj.data.shape_keys and obj.data.uv_layers.active
        assert not list(obj.keys()) and not list(obj.data.keys()), 'Old Mesh identity/receipt on new Cube'
        faces = []
        for face in obj.data.polygons:
            axis = max(range(3), key=lambda i: abs(face.normal[i]))
            assert abs(face.normal[axis]) == 1 and len(face.vertices) == 4
            label = ('+' if face.normal[axis] > 0 else '-') + 'XYZ'[axis]
            mat = obj.material_slots[face.material_index].material
            ref = dict(guid=str(mat['unity_material_guid']), file_id=str(mat['unity_material_file_id']), source_package_id=str(mat['unity_source_package_id']))
            assert ref == dict(guid=GUIDS[WANTED[label]], file_id='2100000', source_package_id=package_id)
            faces.append(dict(plane=label, normal=list(face.normal), corners=[list(obj.data.vertices[v].co) for v in face.vertices],
                              uv=[list(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices], material=ref))
        faces.sort(key=lambda r: r['plane'])
        assert len(faces) == 6 and set(r['plane'] for r in faces) == set(WANTED)
        state = dict(faces=faces, slots=[dict(guid=str(s.material['unity_material_guid']), file_id=str(s.material['unity_material_file_id'])) for s in obj.material_slots],
                     object_keys=list(obj.keys()), mesh_keys=list(obj.data.keys()), matrix_world=[list(row) for row in obj.matrix_world])
        if args.phase == 'replace':
            (work / 'final-state.json').write_text(json.dumps(state, indent=2))
            assert bpy.ops.wm.save_as_mainfile(filepath=str(work / 'Replacement.blend'), check_existing=False) == {'FINISHED'}
            report.update(status='PASS', state=state, blend_sha256=sha(work / 'Replacement.blend'))
        else:
            assert state == json.loads((work / 'final-state.json').read_text()), 'Reopen changed Cube/materials'
            stage = 'EXPORT'
            output = work / 'ReplacementOutput.unitypackage'
            assert not output.exists()
            assert bpy.ops.export_scene.vapb_final_state_unitypackage(filepath=str(output)) == {'FINISHED'}
            assets = RawAssetRepository(output).read_all()
            manifest = next(a for a in assets if a.pathname == 'Assets/VAPBExport/manifest.json')
            (work / 'manifest.json').write_bytes(manifest.asset_bytes)
            models = [a for a in assets if a.pathname.endswith('.fbx')]
            assert len(models) == 1
            (work / 'Exported.fbx').write_bytes(models[0].asset_bytes)
            (work / 'Exported.fbx.meta').write_bytes(models[0].meta_bytes)
            by_guid = {a.guid: a for a in assets}
            assert all(by_guid[g].asset_bytes == source[g].asset_bytes and by_guid[g].meta_bytes == source[g].meta_bytes for g in GUIDS)
            assert not list(obj.keys()) and not list(obj.data.keys()), 'Export modified editing identity'
            report.update(status='PASS', reopen='PASS', standard_final_state_export='PASS', state=state,
                          package_sha256=sha(output), fbx_sha256=sha(work / 'Exported.fbx'), manifest_sha256=sha(work / 'manifest.json'),
                          task=json.loads(manifest.asset_bytes)['reference_rebind_tasks'][0],
                          assets=[dict(guid=a.guid, path=a.pathname, asset_sha256=hashlib.sha256(a.asset_bytes).hexdigest(), meta_sha256=hashlib.sha256(a.meta_bytes).hexdigest()) for a in assets])
        assert all(sha(fixture / name) == digest for name, digest in frozen['asset_sha256'].items())
        report['original_preservation'] = 'PASS'
    except Exception as error:
        import traceback
        traceback.print_exc()  # private process log only
        report.update(status='FAIL', first_failure=stage, error=type(error).__name__ + ': ' + str(error))
    (work / (args.phase + '.json')).write_text(json.dumps(report, indent=2))
    print('HOLMES06', args.phase, report['status'], report.get('error', ''))


if __name__ == '__main__': main()
