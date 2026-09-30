"""Independent Blender observation after normal production Import.

Arguments: package, expected SHA-256, selected prefab Unity asset path, output.
Optional exact source witness is passed to normal Import. Independent Oracle
evidence is read only after Import for observation/comparison.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def value(raw):
    if isinstance(raw, (str, int, float, bool)) or raw is None:
        return raw
    if hasattr(raw, 'to_dict'):
        return {k: value(v) for k, v in raw.to_dict().items()}
    return [value(item) for item in raw]


def properties(entity):
    return {k: value(entity[k]) for k in entity.keys()
            if k.startswith(('unity_', '_vapb_'))}


def snapshot(package_sha, assets, import_result):
    bpy.context.view_layer.update()
    objects = list(bpy.context.scene.objects)
    realized = {o for o in objects if o.get('_vapb_renderer_occurrence_id')}
    realized.update(m.object for o in tuple(realized) for m in o.modifiers
                    if m.type == 'ARMATURE' and m.object is not None)
    rows = []
    for index, obj in enumerate(objects):
        metadata = properties(obj)
        classification = ('SEMANTIC' if metadata.get('_vapb_semantic_id') else
                          'TECHNICAL_ONLY' if metadata.get('_vapb_renderer_occurrences') or metadata.get('_vapb_technical_bone_proxy') else
                          'NATIVE_REALIZATION' if obj in realized else
                          'UNMAPPED_REALIZATION' if obj.type in {'MESH', 'ARMATURE'} else
                          'UNCLASSIFIED')
        rows.append(dict(handle=index, diagnostic_name=obj.name,
            classification=classification, representation=obj.type, metadata=metadata,
            actual_parent=objects.index(obj.parent) if obj.parent in objects else None,
            parent_type=obj.parent_type, parent_bone=obj.parent_bone,
            local_matrix=[list(row) for row in obj.matrix_local],
            world_matrix=[list(row) for row in obj.matrix_world],
            constraints=[dict(kind=c.type, target=objects.index(c.target) if c.target in objects else None,
                subtarget=c.subtarget if hasattr(c, 'subtarget') else '', influence=c.influence,
                muted=c.mute) for c in obj.constraints],
            mesh_metadata=properties(obj.data) if obj.type == 'MESH' else None,
            armature_modifiers=[dict(target=objects.index(m.object) if m.object in objects else None)
                for m in obj.modifiers if m.type == 'ARMATURE'],
            bones=[dict(diagnostic_name=b.name, metadata=properties(b),
                parent_index=list(obj.data.bones).index(b.parent) if b.parent else None,
                matrix=[list(row) for row in b.matrix_local])
                for b in obj.data.bones] if obj.type == 'ARMATURE' else []))
    return dict(schema=1, package_sha256=package_sha, assets=assets,
                import_result=sorted(import_result), objects=rows)


def main():
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
    from unitypackage_blender_importer.unity.asset_database import AssetDatabase
    import unitypackage_blender_importer as addon
    package_text, expected_sha, selected_path, output_text = sys.argv[sys.argv.index('--')+1:]
    package, output = Path(package_text), Path(output_text)
    actual_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        raise AssertionError('Package revision mismatch; comparison prohibited')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vapb_hierarchy_input_') as directory:
        extracted = UnityPackageReader(package).extract(Path(directory))
        if extracted.errors:
            raise AssertionError('Package extraction failed')
        db = AssetDatabase.from_extraction(extracted.root, extracted.assets)
        assets = {guid: asset.unity_path for guid, asset in db.by_guid.items()}
        selected = [asset for asset in db.by_guid.values() if asset.unity_path == selected_path]
        if len(selected) != 1:
            raise AssertionError('Selected composition must identify exactly one package asset')
        choice = 'PREFAB_' + str(db.prefabs().index(selected[0].path))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon.register()
    try:
        result = bpy.ops.import_scene.unitypackage(filepath=str(package),
            import_mode='RECONSTRUCT', prefab_choice=choice, keep_extracted=False,
            model_witness_path=os.environ.get('VAPB_HIERARCHY_WITNESS', ''),
            source_storage_directory=str(output / 'sources'))
        if result != {'FINISHED'}:
            raise AssertionError('Normal Import did not finish')
        observed = snapshot(actual_sha, assets, result)
        paths = [os.environ.get(key, '') for key in (
            'VAPB_HIERARCHY_SOURCE_OBSERVATION', 'VAPB_HIERARCHY_PACKAGE_OBSERVATION',
            'VAPB_HIERARCHY_CONTROL_REPORT')]
        if any(paths):
            if not all(paths) or not os.environ.get('VAPB_HIERARCHY_WITNESS'):
                raise ValueError('Incomplete native observation inputs')
            from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin
            observed['native_skin'] = observe_native_skin(bpy.context, package,
                os.environ['VAPB_HIERARCHY_WITNESS'], *paths, pose_controls=True)
        (output / 'blender_snapshot.json').write_text(json.dumps(observed, indent=2), encoding='utf-8')
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'baseline.blend'))
        print('VAPB_HIERARCHY_SNAPSHOT_PASS objects=' + str(len(observed['objects'])))
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
