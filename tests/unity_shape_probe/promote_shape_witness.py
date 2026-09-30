"""Promote exact-revision UID-marker controls to optional source channel v3.

Blender --python-exit-code 1 --python FILE -- V2 CONTROLS FBX META ORACLE OUTPUT.
No Prefab weights or geometry are copied from the Oracle into production input.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from unitypackage_blender_importer.blender.fbx_witness import source_shape_channel_uids


def main():
    witness_path, controls_path, fbx_path, meta_path, oracle_path, output = map(Path, sys.argv[sys.argv.index('--')+1:])
    witness = json.loads(witness_path.read_text(encoding='utf-8-sig'))
    controls = json.loads(controls_path.read_text(encoding='utf-8-sig'))
    oracle = json.loads(oracle_path.read_text(encoding='utf-8-sig'))
    flags = ('pass', 'noop_equivalent', 'marked_equivalent', 'restored_equivalent',
             'marker_unique', 'source_fbx_restored', 'source_meta_restored')
    assert controls['error'] == 'NONE' and all(controls.get(key) is True for key in flags)
    sha = hashlib.sha256(fbx_path.read_bytes()).hexdigest()
    meta_sha = hashlib.sha256(meta_path.read_bytes()).hexdigest()
    assert sha == controls['source_fbx_sha256'] and meta_sha == controls['source_meta_sha256']
    assert oracle['package_sha256'] == witness['source_unitypackage_sha256']
    assert oracle['source_fbx_sha256'] == sha and oracle['source_meta_sha256'] == meta_sha
    assert oracle['unity_version'] == witness['unity_version'] == '2022.3.22f1'
    original = controls['original']
    marked = controls['marked']
    original_rows = original.get('meshes', [original])
    marked_rows = marked.get('meshes', [marked])
    oracle_meshes = {(row['mesh']['guid'], str(row['mesh']['local_id'])): row for row in oracle['meshes']}
    observed = {(row['mesh_guid'], row['mesh_local_id']): row for row in marked_rows}
    assert len(observed) == len(marked_rows) == len(original_rows)
    for row in original_rows:
        changed = observed[(row['mesh_guid'], row['mesh_local_id'])]
        assert row['geometry_signature'] == changed['geometry_signature']
        assert [c['frame_signature'] for c in row['channels']] == [c['frame_signature'] for c in changed['channels']]
    promoted = 0
    for asset in witness['assets']:
        assert asset['source_fbx_sha256'] == sha and asset['source_meta_sha256'] == meta_sha
        for model in asset['models']:
            graph = source_shape_channel_uids(fbx_path, model['geometry_uid'])
            for renderer in model['renderers']:
                row = observed.get((asset['asset_guid'], renderer['mesh_local_id']))
                if row is None:
                    assert not graph
                    continue
                channels = row['channels']
                assert {int(c['channel_uid']) for c in channels} == set(graph)
                independent = oracle_meshes[(asset['asset_guid'], renderer['mesh_local_id'])]['channels']
                frames = {c['channel_index']: c['frames'] for c in independent}
                assert set(frames) == {c['channel_index'] for c in channels}
                assert all(len(value) == 1 and value[0]['frame_weight'] == 100.0 for value in frames.values())
                renderer['shape_channels'] = [dict(unity_channel_index=c['channel_index'],
                    channel_uid=c['channel_uid'], shape_uid=str(graph[int(c['channel_uid'])]), frame_weight=100.0)
                    for c in channels]
                promoted += len(channels)
    witness['schema_version'] = 'vapb-model-identity-witness-v3'
    witness['source_validation']['shape_channel_probe_pass'] = True
    assert not output.exists()
    output.write_text(json.dumps(witness, indent=2), encoding='utf-8')
    print('SHAPE_WITNESS_PROMOTED channels=%d' % promoted)


if __name__ == '__main__':
    main()
