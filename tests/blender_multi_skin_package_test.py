"""Public two-direct-skin selected export; evidence stays in an external directory."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import bpy

installation = None
if '--addon-zip' in sys.argv:
    installation = tempfile.TemporaryDirectory(prefix='vapb_multi_skin_install_')
    with zipfile.ZipFile(sys.argv[sys.argv.index('--addon-zip') + 1]) as archive:
        archive.extractall(installation.name)
    sys.path.insert(0, installation.name)
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
if installation:
    assert Path(addon.__file__).resolve().is_relative_to(Path(installation.name).resolve())


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder == repo or repo in folder.parents:
        raise ValueError('EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    source_path = folder / 'Source.unitypackage'
    output = folder / 'Output.unitypackage'
    saved = folder / 'Edited.blend'
    if output.exists() or saved.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    info = json.loads((folder / 'MultiSkinSourceInfo.json').read_text(encoding='utf-8-sig'))
    assert len(info['skins']) == 2
    assert len({row['renderer_file_id'] for row in info['skins']}) == 2
    assert len({row['source_mesh_file_id'] for row in info['skins']}) == 2
    addon.register()
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        assert bpy.ops.import_scene.unitypackage(filepath=str(source_path),
            import_mode='RECONSTRUCT', keep_extracted=False,
            source_storage_directory=str(folder / 'BlenderSources')) == {'FINISHED'}
        roots = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_renderer_occurrences')]
        assert len(roots) == 1
        records = json.loads(roots[0]['_vapb_renderer_occurrences'])['records']
        skins = [record for record in records if record['renderer_class_id'] == 137]
        assert len(skins) == 2
        assert {str(row['source_key']['renderer_file_id']) for row in skins} == {
            row['renderer_file_id'] for row in info['skins']}
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
                  and obj.get('_vapb_root_context_id') == roots[0].get('_vapb_root_context_id')
                  and obj.get('_vapb_fbx_realization_id')
                  and any(mod.type == 'ARMATURE' for mod in obj.modifiers)]
        assert len(meshes) == 2
        assert len({obj['_vapb_fbx_realization_id'] for obj in meshes}) == 2
        assert len({str(obj['_vapb_fbx_model_uid']) for obj in meshes}) == 2
        assert len({str(obj.data['_vapb_fbx_geometry_uid']) for obj in meshes}) == 2
        assert len({id(next(mod.object for mod in obj.modifiers if mod.type == 'ARMATURE'))
                    for obj in meshes}) == 1
        realization_ids = sorted(obj['_vapb_fbx_realization_id'] for obj in meshes)
        for obj in meshes:
            obj.data = obj.data.copy()
            delta = 0.002 if obj['_vapb_fbx_realization_id'] == realization_ids[0] else 0.004
            obj.data.vertices[0].co.x += delta
            if obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    key.data[0].co.x += delta
            obj.data.update()
            obj.name = 'Edited public skin'
        assert bpy.ops.wm.save_as_mainfile(filepath=str(saved)) == {'FINISHED'}
        assert bpy.ops.wm.open_mainfile(filepath=str(saved)) == {'FINISHED'}
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
                  and obj.get('_vapb_fbx_realization_id') in realization_ids]
        assert len(meshes) == 2 and {obj['_vapb_fbx_realization_id'] for obj in meshes} == set(realization_ids)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        parameters = dict(filepath=str(output))
        if 'export_scope' in bpy.ops.export_scene.vapb_unitypackage.get_rna_type().properties:
            parameters['export_scope'] = 'SELECTED'
        def reject():
            try:
                result = bpy.ops.export_scene.vapb_unitypackage(**parameters)
            except RuntimeError:
                result = {'CANCELLED'}
            assert result == {'CANCELLED'} and not output.exists()
        state = {obj['_vapb_fbx_realization_id']: (
            obj.data['_vapb_fbx_geometry_uid'],
            tuple(tuple(vertex.co) for vertex in obj.data.vertices),
            tuple((bone.get('_vapb_fbx_bone_realization_id'), bone.use_deform)
                  for bone in next(mod.object for mod in obj.modifiers
                                   if mod.type == 'ARMATURE').data.bones)) for obj in meshes}
        damaged = meshes[1]
        original_uid = damaged.data['_vapb_fbx_geometry_uid']
        try:
            damaged.data['_vapb_fbx_geometry_uid'] = '0'
            reject()
        finally:
            damaged.data['_vapb_fbx_geometry_uid'] = original_uid
        original_context = damaged['_vapb_root_context_id']
        try:
            damaged['_vapb_root_context_id'] = 'other-root-context'
            reject()
        finally:
            damaged['_vapb_root_context_id'] = original_context
        assert bpy.ops.export_scene.vapb_unitypackage(**parameters) == {'FINISHED'}
        assert state == {obj['_vapb_fbx_realization_id']: (
            obj.data['_vapb_fbx_geometry_uid'],
            tuple(tuple(vertex.co) for vertex in obj.data.vertices),
            tuple((bone.get('_vapb_fbx_bone_realization_id'), bone.use_deform)
                  for bone in next(mod.object for mod in obj.modifiers
                                   if mod.type == 'ARMATURE').data.bones)) for obj in meshes}
        import tarfile
        with tarfile.open(output, 'r:*') as archive:
            manifest_paths = [member.name.rsplit('/', 1)[0] for member in archive.getmembers()
                if member.name.endswith('/pathname') and
                archive.extractfile(member).read().decode('utf-8').strip() == 'Assets/VAPBExport/manifest.json']
            assert len(manifest_paths) == 1
            manifest = json.loads(archive.extractfile(manifest_paths[0] + '/asset').read())
        tasks = manifest['reference_rebind_tasks']
        assert len(tasks) == 2
        assert {task['kind'] for task in tasks} == {'RESTORE_DIRECT_SKIN_VARIANT_V1'}
        assert len({task['variant_path'] for task in tasks}) == 1
        assert len({task['realization_id'] for task in tasks}) == 2
        assert {task['prefab_guid'] for task in tasks} == {info['prefab_guid']}
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
        (folder / 'MultiSkinBlenderResult.json').write_text(json.dumps({
            'pass': True, 'selected_skins': 2, 'tasks': 2,
            'one_variant': True, 'source_archive_unchanged': True
        }, indent=2), encoding='utf-8')
        print('MULTI_SKIN_BLENDER_PASS')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
