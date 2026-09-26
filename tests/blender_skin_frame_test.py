"""Reproduce source/control/edited FBX mesh frames through actual VAPB staging.

Run after the source fixture is prepared with --source-units-in-fbx.
All generated files belong in the external synthetic Unity project.
"""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.operators.export_unitypackage import _export_staged_skin


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder == repo or repo in folder.parents:
        raise ValueError('EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    control, edited = folder / 'NoEdit.fbx', folder / 'Edited.fbx'
    if control.exists() or edited.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    addon.register()
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        assert bpy.ops.import_scene.unitypackage(filepath=str(folder / 'Source.unitypackage'),
            import_mode='RECONSTRUCT', keep_extracted=False,
            source_storage_directory=str(folder / 'BlenderSources')) == {'FINISHED'}
        roots = [o for o in bpy.context.scene.objects if o.get('_vapb_renderer_occurrences')]
        assert len(roots) == 1
        candidates = [o for o in bpy.context.scene.objects if o.type == 'MESH'
                      and o.get('_vapb_root_context_id') == roots[0]['_vapb_root_context_id']
                      and o.get('_vapb_fbx_realization_id')]
        assert len(candidates) == 1
        mesh = candidates[0]
        assert len(mesh.modifiers) == 1 and mesh.modifiers[0].type == 'ARMATURE'
        rig = mesh.modifiers[0].object
        mappings = []
        for bone in rig.data.bones:
            receipt = bone.get('_vapb_fbx_bone_realization_id')
            assert receipt and rig.pose.bones[bone.name].get('_vapb_fbx_bone_realization_id') == receipt
            mappings.append({'edited_bone_realization_id': receipt})
        before = (len(bpy.data.objects), len(bpy.data.scenes))
        _export_staged_skin(bpy.context, mesh, rig, control, {'mappings': mappings})
        mesh.data = mesh.data.copy()
        assert mesh.data.shape_keys is None
        mesh.data.vertices[0].co.x += 0.002
        mesh.data.update()
        _export_staged_skin(bpy.context, mesh, rig, edited, {'mappings': mappings})
        assert before == (len(bpy.data.objects), len(bpy.data.scenes))
        assert control.is_file() and edited.is_file()
        print('SKIN_FRAME_STAGING_PASS')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
