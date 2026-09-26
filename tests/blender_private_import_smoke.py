"""Run a bounded real-package import smoke; all private evidence stays outside Git.

Blender --factory-startup --background --python-exit-code 1 --python <this>
    -- <external-case-directory>
The directory contains case.json: input, expected_sha256, optional prefab_choice.
Logs, .blend and detailed identity state are private local evidence, not fixtures.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def snapshot():
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    rigs = [obj for obj in objects if obj.type == 'ARMATURE']
    def metadata(block):
        return tuple(sorted((key, str(block[key])) for key in block.keys()
                            if key.startswith('_vapb_') and not key.endswith('_session_uid')))
    # Names are only a serialization comparison key for an unedited save/reopen;
    # they are not used to infer Unity source or occurrence identity.
    state = sorted((obj.name, obj.type, obj.parent.name if obj.parent else '',
                    metadata(obj))
                   for obj in objects)
    bone_state = sorted((rig.name, bone.name, bone.parent.name if bone.parent else '', metadata(bone))
                        for rig in rigs for bone in rig.data.bones)
    records = []
    for obj in objects:
        value = obj.get('_vapb_renderer_occurrences')
        if value:
            records.extend(json.loads(value).get('records', []))
    return (state, bone_state), {
        'objects': len(objects), 'meshes': len(meshes), 'armatures': len(rigs),
        'mesh_datablocks': len({obj.data.as_pointer() for obj in meshes}),
        'bones': sum(len(obj.data.bones) for obj in rigs),
        'vertices': sum(len(obj.data.vertices) for obj in meshes),
        'shape_key_meshes': sum(bool(obj.data.shape_keys) for obj in meshes),
        'shape_keys': sum(len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0 for obj in meshes),
        'material_slots': sum(len(obj.material_slots) for obj in meshes),
        'empty_material_slots': sum(slot.material is None for obj in meshes for slot in obj.material_slots),
        'images': len(bpy.data.images),
        'images_loaded': sum(image.has_data for image in bpy.data.images),
        'renderer_occurrences': len(records),
        'native_mesh_receipts': sum(bool(obj.get('_vapb_fbx_realization_id')) for obj in meshes),
        'skin_modifiers': sum(mod.type == 'ARMATURE' and mod.object is not None
                              for obj in meshes for mod in obj.modifiers),
    }


def main():
    import unitypackage_blender_importer as addon
    case_dir = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if case_dir == repo or repo in case_dir.parents:
        raise ValueError('Private evidence directory must be outside the repository')
    config = json.loads((case_dir / 'case.json').read_text(encoding='utf-8-sig'))
    source = Path(config['input'])
    report = {'import': 'NOT_RUN', 'save_reopen': 'NOT_RUN', 'source_unchanged': None,
              'error_type': '', 'core_roundtrip': 'NOT_RUN'}
    registered = False
    try:
        with source.open('rb') as stream:
            before_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        if before_hash != config['expected_sha256']:
            raise ValueError('Source archive does not match catalog')
        addon.register()
        registered = True
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        result = bpy.ops.import_scene.unitypackage(
            filepath=str(source), import_mode='RECONSTRUCT', keep_extracted=False,
            prefab_choice=config.get('prefab_choice', 'AUTO'),
            source_storage_directory=str(case_dir / 'Sources'))
        if result != {'FINISHED'}:
            report['import'] = 'CANCELLED'
            raise RuntimeError('Import did not finish')
        before_state, counts = snapshot()
        report.update(counts)
        if not counts['meshes']:
            raise RuntimeError('Import produced no Mesh Objects')
        report['import'] = 'PASS'
        blend = case_dir / 'Imported.blend'
        if blend.exists():
            raise FileExistsError('Use a new case directory for another attempt')
        report['save_reopen'] = 'FAIL'
        if bpy.ops.wm.save_as_mainfile(filepath=str(blend)) != {'FINISHED'} or not blend.is_file():
            raise RuntimeError('Save did not finish')
        if bpy.ops.wm.open_mainfile(filepath=str(blend)) != {'FINISHED'}:
            raise RuntimeError('Reopen did not finish')
        after_state, after_counts = snapshot()
        if before_state != after_state or counts != after_counts:
            raise AssertionError('Saved structure or metadata changed on reopen')
        report['save_reopen'] = 'PASS'
        with source.open('rb') as stream:
            report['source_unchanged'] = hashlib.file_digest(stream, 'sha256').hexdigest() == before_hash
        if not report['source_unchanged']:
            raise AssertionError('Source archive changed')
    except Exception as error:
        report['error_type'] = type(error).__name__
        if report['import'] == 'NOT_RUN':
            report['import'] = 'FAIL'
        raise
    finally:
        (case_dir / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        if registered:
            addon.unregister()


if __name__ == '__main__':
    main()
