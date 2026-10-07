"""Promote a passing exact-revision Unity probe to v1 and authored Skin-slot v2.
Blender --python-exit-code 1 --python FILE -- ISOLATED_PROJECT.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from unitypackage_blender_importer.blender.fbx_receipt import RawFbxSemanticIndex
from unitypackage_blender_importer.unity.model_identity_witness import ModelAssetRevision, build_model_witness_from_probe, validate_model_witness


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    dry_run = '--dry-run' in args
    args = [arg for arg in args if arg != '--dry-run']
    if len(args) != 1:
        raise ValueError('EXACTLY_ONE_SOURCE_PROJECT_REQUIRED')
    project = Path(args[0]).resolve()
    identity = json.loads((project / 'ExactSourceIdentity.json').read_text(encoding='utf-8-sig'))
    probe = json.loads((project / 'VapbBoneWitnessMapping.json').read_text(encoding='utf-8-sig'))
    report = json.loads((project / 'VapbBoneWitnessResult.json').read_text(encoding='utf-8-sig'))
    source = project / 'Source.fbx'
    package = project / 'ExactPackage.unitypackage'
    assert hashlib.sha256(package.read_bytes()).hexdigest() == identity['package_sha256'], 'PACKAGE_REVISION_MISMATCH'
    for file, expected in ((source, identity['source_fbx_sha256']),
            (project / 'Source.fbx.meta', identity['source_meta_sha256']),
            (project / 'Assets/VapbBoneWitness/Model.fbx', identity['source_fbx_sha256']),
            (project / 'Assets/VapbBoneWitness/Model.fbx.meta', identity['source_meta_sha256'])):
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected
    revision = ModelAssetRevision(identity['source_fbx_sha256'], identity['source_meta_sha256'], RawFbxSemanticIndex.from_file(source))
    witness = build_model_witness_from_probe(probe, report, identity['package_sha256'], {identity['model_guid']: revision})
    output = project / 'witness_v1.json'
    from unitypackage_blender_importer.blender.fbx_witness import source_skin_bone_uids
    observation = json.loads((project / 'VapbHierarchyBoneObservation.json').read_text(encoding='utf-8-sig'))
    assert observation['schema_version'] == 'vapb-hierarchy-bone-public-api-observation-1'
    assert observation['model_guid'] == identity['model_guid']
    assert observation['source_fbx_sha256'] == identity['source_fbx_sha256']
    assert observation['source_meta_sha256'] == identity['source_meta_sha256']
    assert observation['unity_version'] == witness['unity_version']
    assert all(report.get(k) is True for k in ('pass', 'noopEquivalent', 'witnessEquivalent',
        'restoredEquivalent', 'metaStable', 'callbackExactlyOnce', 'markerIdentityUnique',
        'allSkinBonesMarked', 'sourceMetaRestored', 'sourceRawRestored', 'originalRevisionEquivalent'))
    observed = {}
    for row in observation['skinned_renderers']:
        key = (int(row['renderer_model_uid']), int(row['renderer_local_id']), int(row['mesh_local_id']))
        assert key not in observed
        observed[key] = row
    extended = json.loads(json.dumps(witness))
    extended['schema_version'] = 'vapb-model-identity-witness-v2'
    membership = {}
    consumed = set()
    for model in extended['assets'][0]['models']:
        for renderer in model['renderers']:
            if renderer['class_id'] != 137:
                continue
            key = (int(model['model_uid']), int(renderer['renderer_local_id']), int(renderer['mesh_local_id']))
            assert key in observed and key not in consumed
            consumed.add(key)
            row = observed[key]
            ordered = [str(int(bone['model_uid'])) for bone in row['ordered_bones']]
            assert len(set(ordered)) == len(ordered) == row['bindpose_count']
            native_members = source_skin_bone_uids(source, model['model_uid'], model['geometry_uid'])
            assert frozenset(ordered) == native_members
            root_uid = str(int(row['root_bone']['model_uid']))
            assert root_uid in ordered
            membership[int(model['model_uid'])] = native_members
            renderer['skin'] = {'ordered_bone_model_uids': ordered, 'root_bone_model_uid': root_uid}
            frames = [bone.get('world_matrix', bone.get('local_to_world_matrix')) for bone in row['ordered_bones']]
            if any(frame is not None for frame in frames):
                assert all(isinstance(frame, list) and len(frame) == 16 for frame in frames)
                renderer['skin']['source_bone_world_matrices'] = frames
    assert consumed == set(observed)
    validated_revision = ModelAssetRevision(identity['source_fbx_sha256'], identity['source_meta_sha256'],
        revision.fbx_index, membership)
    validate_model_witness(extended, identity['package_sha256'], {identity['model_guid']: validated_revision})
    destination = project / 'witness_v2.json'
    for path, value in ((output, witness), (destination, extended)):
        if path.exists():
            assert json.loads(path.read_text(encoding='utf-8')) == value, 'EXISTING_WITNESS_MISMATCH'
    if dry_run:
        print('EXACT_WITNESS_DRY_RUN_VALIDATED source_revision=1 existing_outputs_preserved=1')
        return
    for path, value in ((output, witness), (destination, extended)):
        if not path.exists():
            try:
                with path.open('x', encoding='utf-8') as stream:
                    json.dump(value, stream, indent=2)
            except FileExistsError:
                assert json.loads(path.read_text(encoding='utf-8')) == value, 'EXISTING_WITNESS_MISMATCH'
    print('EXACT_WITNESS_V1_VALIDATED restored_fbx_meta_hashes=1')
    print('EXACT_WITNESS_V2_VALIDATED ordered_bones=UNITY_SKIN_SLOTS')


if __name__ == '__main__':
    main()
