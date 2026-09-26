"""Exercise the real model-Skin export operator with synthetic or external input.

-- <external-directory>, containing Source.unitypackage or case.json with an
input_blend. Private paths and output packages must remain outside the repo.
"""
import json
import hashlib
from pathlib import Path
import sys
import tarfile
import tempfile
import zipfile

import bpy

installation = None
if '--addon-zip' in sys.argv:
    installation = tempfile.TemporaryDirectory(prefix='vapb_model_skin_install_')
    archive_path = Path(sys.argv[sys.argv.index('--addon-zip') + 1]).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(installation.name)
    sys.path.insert(0, installation.name)
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
if installation:
    assert Path(addon.__file__).resolve().is_relative_to(Path(installation.name).resolve())


def package_asset(path, guid):
    with tarfile.open(path, 'r:*') as archive:
        return archive.extractfile(f'{guid}/asset').read()


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder == repo or repo in folder.parents:
        raise ValueError('EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    output = folder / 'Output.unitypackage'
    saved = folder / 'Edited.blend'
    if output.exists() or saved.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    addon.register()
    try:
        config_file = folder / 'case.json'
        config = json.loads(config_file.read_text(encoding='utf-8-sig')) if config_file.exists() else {}
        texture_mode = config.get('texture_edit_mode', 'file') if config.get('texture_edit') else ''
        assert texture_mode in ('', 'file', 'packed')
        if config.get('input_blend'):
            assert bpy.ops.wm.open_mainfile(filepath=config['input_blend']) == {'FINISHED'}
        else:
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            assert bpy.ops.import_scene.unitypackage(filepath=str(folder / 'Source.unitypackage'),
                import_mode='RECONSTRUCT', prefab_choice='AUTO',
                keep_extracted=texture_mode == 'file',
                source_storage_directory=str(folder / 'Sources')) == {'FINISHED'}
        candidates = [o for o in bpy.context.scene.objects if o.type == 'MESH'
                      and (config.get('direct_skin') or o.get('_vapb_model_instance_edge_path'))
                      and o.get('_vapb_fbx_realization_id')
                      and o.get('_vapb_root_context_id')
                      and any(m.type == 'ARMATURE' for m in o.modifiers)]
        if config.get('realization_id'):
            candidates = [o for o in candidates if o.get('_vapb_fbx_realization_id') == config['realization_id']]
            assert len(candidates) == 1
        assert candidates
        # Test selection only. The exporter proves source identity independently.
        if config.get('direct_skin'):
            assert len(candidates) == 1
            mesh = candidates[0]
        else:
            mesh = max(candidates, key=lambda o: len(json.loads(o['_vapb_model_instance_edge_path'])))
        realization = mesh['_vapb_fbx_realization_id']
        mesh.data = mesh.data.copy()
        texture = None
        if config.get('texture_edit'):
            from unitypackage_blender_importer.operators.texture_editing import (
                STATUS_OK, save_image_to_unity_source)
            source_package = folder / 'Source.unitypackage'
            source_archive_sha = hashlib.sha256(source_package.read_bytes()).hexdigest()
            source_info = json.loads((folder / 'SourceInfo.json').read_text(encoding='utf-8-sig'))
            texture_guid = source_info['texture_guid']
            assert texture_guid and source_info['texture_sha256']
            original_png = package_asset(source_package, texture_guid)
            assert hashlib.sha256(original_png).hexdigest() == source_info['texture_sha256']
            roots = [obj for obj in bpy.context.scene.objects
                     if obj.get('_vapb_renderer_occurrences') and
                     obj.get('_vapb_root_context_id') == mesh.get('_vapb_root_context_id')]
            assert len(roots) == 1
            records = json.loads(roots[0]['_vapb_renderer_occurrences'])['records']
            selected = [record for record in records
                        if str(record.get('source_key', {}).get('renderer_file_id')) ==
                        str(source_info['renderer_file_id'])]
            assert len(selected) == 1
            bpy.context.scene.vapb_renderer_root = roots[0]
            bpy.context.scene.vapb_renderer_mesh = mesh
            assert bpy.ops.vapb.confirm_renderer_binding(
                occurrence_id=selected[0]['occurrence_id']) == {'FINISHED'}
            images = [image for image in bpy.data.images
                      if image.get('unity_guid') == texture_guid
                      and image.get('unity_source_package_id') == mesh.get('unity_source_package_id')]
            assert len(images) == 1
            image = images[0]
            materials = [material for material in bpy.data.materials
                         if material.get('unity_material_guid') == source_info['material_guid']
                         and material.get('unity_source_package_id') == mesh.get('unity_source_package_id')]
            assert len(materials) == 1
            assert len(mesh.material_slots) == 1 and mesh.material_slots[0].material == materials[0]
            assert any(node.type == 'TEX_IMAGE' and node.image == image
                       for node in materials[0].node_tree.nodes)
            identity = tuple(image.get(key) for key in
                             ('unity_guid', 'unity_asset_path', 'unity_source_path',
                              'unity_source_package_id'))
            image.pixels[0] = 0.25
            image.update()
            if texture_mode == 'file':
                assert save_image_to_unity_source(image) == STATUS_OK
                working_path = Path(image['unity_source_path'])
            else:
                assert image.packed_file is not None
                working_path = folder / 'WorkingPacked.png'
                assert not working_path.exists()
                image.save(filepath=str(working_path), save_copy=True)
            working_png = working_path.read_bytes()
            assert working_png != original_png
            if texture_mode == 'packed':
                image.pack(data=working_png, data_len=len(working_png))
                assert image.packed_file is not None
                assert bytes(image.packed_file.data) == working_png
            assert tuple(image.get(key) for key in
                         ('unity_guid', 'unity_asset_path', 'unity_source_path',
                          'unity_source_package_id')) == identity
            texture = (texture_guid, source_archive_sha, original_png, working_path, working_png,
                       identity, texture_mode)
        if not config.get('already_edited'):
            if config.get('uv_shape_split'):
                assert len(mesh.data.vertices) == 4 and len(mesh.data.polygons) == 2
                keys = mesh.data.shape_keys.key_blocks
                assert len(keys) == 3 and mesh.data.uv_layers.active is not None
                rings = [tuple(mesh.data.loops[index].vertex_index for index in polygon.loop_indices)
                         for polygon in mesh.data.polygons]
                mesh.data.vertices[0].co.x += 0.002
                for key in keys:
                    key.data[0].co.x += 0.002
                keys[1].data[0].co.z += 0.003
                split_loop = next(index for index in mesh.data.polygons[1].loop_indices
                                  if mesh.data.loops[index].vertex_index == 0)
                mesh.data.uv_layers.active.data[split_loop].uv.x += 0.25
                assert rings == [tuple(mesh.data.loops[index].vertex_index for index in polygon.loop_indices)
                                 for polygon in mesh.data.polygons]
            elif mesh.data.shape_keys:
                mesh.data.vertices[0].co.x += 0.002
                for key in mesh.data.shape_keys.key_blocks:
                    key.data[0].co.x += 0.002
            else:
                mesh.data.vertices[0].co.x += 0.002
            mesh.data.update()
            mesh.name = 'Edited Native Skin'
        assert bpy.ops.wm.save_as_mainfile(filepath=str(saved)) == {'FINISHED'}
        assert bpy.ops.wm.open_mainfile(filepath=str(saved)) == {'FINISHED'}
        matches = [o for o in bpy.context.scene.objects if o.get('_vapb_fbx_realization_id') == realization]
        assert len(matches) == 1
        mesh = matches[0]
        if texture:
            texture_guid, source_archive_sha, original_png, working_path, working_png, identity, texture_mode = texture
            reopened = [image for image in bpy.data.images
                        if image.get('unity_guid') == texture_guid
                        and image.get('unity_source_package_id') == mesh.get('unity_source_package_id')]
            assert len(reopened) == 1
            assert tuple(reopened[0].get(key) for key in
                         ('unity_guid', 'unity_asset_path', 'unity_source_path',
                          'unity_source_package_id')) == identity
            assert working_path.read_bytes() == working_png
            if texture_mode == 'packed':
                assert reopened[0].packed_file is not None
                assert bytes(reopened[0].packed_file.data) == working_png
                assert abs(reopened[0].pixels[0] - 0.25) < 0.005
        bpy.ops.object.select_all(action='DESELECT')
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        def reject():
            try:
                result = bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))
            except RuntimeError:
                result = {'CANCELLED'}
            assert result == {'CANCELLED'} and not output.exists()
        geometry_uid = mesh.data['_vapb_fbx_geometry_uid']
        mesh.data['_vapb_fbx_geometry_uid'] = '0'
        reject()
        mesh.data['_vapb_fbx_geometry_uid'] = geometry_uid
        roots = [o for o in bpy.context.scene.objects if o.get('_vapb_renderer_occurrences')
                 and o.get('_vapb_root_context_id') == mesh['_vapb_root_context_id']]
        assert len(roots) == 1
        member = roots[0]['unity_composition_member_id']
        roots[0]['unity_composition_member_id'] = '0' * 32
        reject()
        roots[0]['unity_composition_member_id'] = member
        rig = next(mod.object for mod in mesh.modifiers if mod.type == 'ARMATURE')
        bone_state = [(bone.get('_vapb_fbx_bone_realization_id'), bone.use_deform)
                      for bone in rig.data.bones]
        if config.get('source_subset_fbx'):
            from unitypackage_blender_importer.blender.fbx_witness import source_skin_bone_uids
            source_uids = source_skin_bone_uids(config['source_subset_fbx'],
                mesh['_vapb_fbx_model_uid'], mesh.data['_vapb_fbx_geometry_uid'])
            excluded = [bone for bone in rig.data.bones
                        if str(bone.get('_vapb_fbx_model_uid')) not in source_uids]
            assert len(rig.data.bones) == 3 and len(source_uids) == 2 and len(excluded) == 1
            selected_bone = next(bone for bone in rig.data.bones
                                 if str(bone.get('_vapb_fbx_model_uid')) in source_uids)
            original_deform = selected_bone.use_deform
            try:
                selected_bone.use_deform = False
                reject()
            finally:
                selected_bone.use_deform = original_deform
            # Native Blender group/bone names define this intentionally added
            # influence; the source subset above is selected by FBX identities.
            assert mesh.vertex_groups.get(excluded[0].name) is None
            group = mesh.vertex_groups.new(name=excluded[0].name)
            try:
                group.add([0], 0.25, 'REPLACE')
                reject()
            finally:
                mesh.vertex_groups.remove(group)
        assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output)) == {'FINISHED'}
        assert bone_state == [(bone.get('_vapb_fbx_bone_realization_id'), bone.use_deform)
                              for bone in rig.data.bones]
        assert output.is_file() and output.stat().st_size > 0
        if texture:
            exported_png = package_asset(output, texture_guid)
            with tarfile.open(folder / 'Source.unitypackage', 'r:*') as archive:
                original_meta = archive.extractfile(f'{texture_guid}/asset.meta').read()
            with tarfile.open(output, 'r:*') as archive:
                output_meta = archive.extractfile(f'{texture_guid}/asset.meta').read()
            (folder / 'OriginalTexture.png').write_bytes(original_png)
            (folder / 'TextureExpected.json').write_text(json.dumps({
                'original_sha256': hashlib.sha256(original_png).hexdigest(),
                'edited_sha256': hashlib.sha256(working_png).hexdigest(),
                'meta_sha256': hashlib.sha256(original_meta).hexdigest(),
                'output_meta_same': original_meta == output_meta,
            }, indent=2), encoding='utf-8')
            source_unchanged = hashlib.sha256((folder / 'Source.unitypackage').read_bytes()).hexdigest() == source_archive_sha
            evidence = {
                'mode': texture_mode,
                'source_archive_unchanged': source_unchanged,
                'working_png_changed': working_png != original_png,
                'save_reopen_identity_preserved': True,
                'packed_pixel_persisted': texture_mode != 'packed' or (
                    reopened[0].packed_file is not None and
                    abs(reopened[0].pixels[0] - 0.25) < 0.005),
                'output_equals_original': exported_png == original_png,
                'output_equals_working': exported_png == working_png,
            }
            (folder / 'TextureRedResult.json').write_text(json.dumps(evidence, indent=2),
                                                           encoding='utf-8')
            assert source_unchanged and exported_png == working_png, 'WORKING_TEXTURE_EDIT_DROPPED'
        print('MODEL_SKIN_PACKAGE_PASS')
    finally:
        addon.unregister()


if __name__ == '__main__':
    try:
        main()
    finally:
        if installation:
            installation.cleanup()
