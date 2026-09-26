"""Exercise the real model-Skin export operator with synthetic or external input.

-- <external-directory>, containing Source.unitypackage or case.json with an
input_blend. Private paths and output packages must remain outside the repo.
"""
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon


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
                      and o.get('_vapb_model_instance_edge_path')
                      and any(m.type == 'ARMATURE' for m in o.modifiers)]
        if config.get('realization_id'):
            candidates = [o for o in candidates if o.get('_vapb_fbx_realization_id') == config['realization_id']]
            assert len(candidates) == 1
        assert candidates
        # Test selection only. The exporter proves source identity independently.
        mesh = max(candidates, key=lambda o: len(json.loads(o['_vapb_model_instance_edge_path'])))
        realization = mesh['_vapb_fbx_realization_id']
        mesh.data = mesh.data.copy()
        if not config.get('already_edited'):
            if mesh.data.shape_keys:
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
        assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output)) == {'FINISHED'}
        assert output.is_file() and output.stat().st_size > 0
        print('MODEL_SKIN_PACKAGE_PASS')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
