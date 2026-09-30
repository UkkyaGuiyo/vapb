"""Focused normal-import RED/GREEN: two renderer-free source occurrences."""
import json
import copy
import tempfile
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_hierarchy_snapshot import main, snapshot
from hierarchy_comparator import compare


def persistence_controls(data, output):
    oracle = json.loads((Path(__file__).parent / 'unity_hierarchy_probe' / 'unity_oracle.json').read_text())
    before = compare(oracle, data, data['package_sha256'])
    identities = {o['metadata']['_vapb_semantic_id'] for o in data['objects']
                  if o['classification'] == 'SEMANTIC'}
    for i, obj in enumerate(bpy.context.scene.objects):
        obj.name = 'Renamed semantic test ' + str(i)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'renamed.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(output / 'renamed.blend'))
    after_data = snapshot(data['package_sha256'], data['assets'], {'FINISHED'})
    after = compare(oracle, after_data, data['package_sha256'])
    assert before['checks'] == after['checks']
    assert identities == {o['metadata']['_vapb_semantic_id'] for o in after_data['objects']
                          if o['classification'] == 'SEMANTIC'}
    assert after['dimensions']['node'] == {'EXACT': 12}
    (output / 'comparison.json').write_text(json.dumps(after, indent=2))
    print('SEMANTIC_12_RENAME_SAVE_REOPEN_PASS; NATIVE_SKIN_STILL_UNPROVEN')


def negative_controls(package):
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
    from unitypackage_blender_importer.unity.asset_database import AssetDatabase
    from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
    from unitypackage_blender_importer.unity.occurrence_projection import PrefabSource
    from unitypackage_blender_importer.blender.hierarchy_builder import build_prefab_hierarchy
    with tempfile.TemporaryDirectory() as directory:
        extraction = UnityPackageReader(package).extract(Path(directory))
        db = AssetDatabase.from_extraction(extraction.root, extraction.assets)
        container = parse_prefab(db.by_unity_path['Assets/VapbHierarchy/Majun.prefab'].path)
        source = parse_prefab(db.by_unity_path['Assets/VapbHierarchy/Accessory.prefab'].path)
        for mode in ('ambiguous', 'extra_component', 'missing_trs', 'removed_go'):
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            child, root = copy.deepcopy(source), copy.deepcopy(container)
            if mode == 'extra_component':
                next(iter(child.game_objects.values())).component_ids.append(99)
            if mode == 'missing_trs':
                next(d for d in child.documents if d.class_id == 4).data['m_LocalScale'].pop('x')
            if mode == 'removed_go':
                for doc in root.documents:
                    if doc.class_id == 1001:
                        doc.data['m_Modification']['m_RemovedGameObjects'] = [{'fileID': 99}]
            provider = PrefabSource.from_prefab(child, 'fixture-package', child.asset_guid)
            issues = []
            build_prefab_hierarchy(root, [], 'fixture-package', 'Assets/VapbHierarchy/Majun.prefab',
                source_loader=lambda package_id, guid: [provider, provider] if mode == 'ambiguous' else provider,
                root_context_id='fixture-context', semantic_issues=issues)
            assert not [o for o in bpy.context.scene.objects if o.get('_vapb_model_instance_edge_path')], mode
            if mode != 'ambiguous':
                assert len(issues) == 2, (mode, issues)
    print('RENDERER_FREE_NEGATIVE_CONTROLS_PASS=4')


if __name__ == '__main__':
    main()
    output = Path(sys.argv[-1])
    data = json.loads((output / 'blender_snapshot.json').read_text())
    nested = [obj for obj in data['objects']
              if obj['metadata'].get('_vapb_semantic_id')
              and obj['metadata'].get('_vapb_model_instance_edge_path')]
    assert len(nested) == 2, f'Expected two renderer-free occurrences; observed {len(nested)}'
    assert len({obj['metadata']['_vapb_semantic_id'] for obj in nested}) == 2
    assert len({obj['metadata']['_vapb_root_context_id'] for obj in nested}) == 1
    assert len({obj['metadata']['unity_prefab_file_id'] for obj in nested}) == 1
    assert nested[0]['actual_parent'] == nested[1]['actual_parent']
    assert nested[0]['actual_parent'] is not None
    print('RENDERER_FREE_HIERARCHY_PASS')
    persistence_controls(data, output)
    negative_controls(Path(sys.argv[sys.argv.index('--')+1]))
