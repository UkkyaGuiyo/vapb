"""Exercise the real model-Skin export operator with synthetic or external input.

-- <external-directory>, containing Source.unitypackage or case.json with an
input_blend. Private paths and output packages must remain outside the repo.
"""
import json
from pathlib import Path
import sys
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
        if config.get('input_blend'):
            assert bpy.ops.wm.open_mainfile(filepath=config['input_blend']) == {'FINISHED'}
        else:
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            assert bpy.ops.import_scene.unitypackage(filepath=str(folder / 'Source.unitypackage'),
                import_mode='RECONSTRUCT', prefab_choice='AUTO', keep_extracted=False,
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
        print('MODEL_SKIN_PACKAGE_PASS')
    finally:
        addon.unregister()


if __name__ == '__main__':
    try:
        main()
    finally:
        if installation:
            installation.cleanup()
