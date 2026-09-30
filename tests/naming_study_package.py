"""Historical research-only relocation probe; never called by production.

PRODUCT-NO-GO: its internal-name patch documents a technical counterexample,
not an allowed export policy or reusable production naming implementation.

stage BASE_OUTPUT SOURCE_PROJECT; relocate SOURCE_PROJECT FRESH_PROJECT
Run Unity Prepare between commands, then Unity Validate in the fresh project.
Only generated first-party synthetic inputs are permitted.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree
from unitypackage_blender_importer.export.package_writer import UnityPackageWriter


def relocate(root, destination, bind_index=0):
    evidence = json.loads((root / 'SourceEvidence.json').read_text())
    assets = {a.guid: StagedUnityAsset(a.guid, a.pathname, a.asset_bytes, a.meta_bytes, a.preview_bytes)
              for a in RawAssetRepository(root / 'Source.unitypackage').read_all()}
    records = evidence['materials']
    packages = {name: {a.guid: a for a in RawAssetRepository(root / (name + '.unitypackage')).read_all()}
                for name in ('Majun', 'SyntheticOther', 'Materials', 'Shared')}
    assert records[2]['guid'] not in packages['Majun']
    assert records[2]['guid'] in packages['Materials']
    assert records[3]['guid'] not in packages['Majun'] and records[3]['guid'] not in packages['SyntheticOther']
    assert records[3]['guid'] in packages['Shared']
    assert len(records[5]['candidate_labels']) == 2 and not records[5]['owners']
    # Labels are fixture inputs; ownership was independently observed from
    # exact public-API Renderer references, not guessed from these strings.
    owners = [('Majun', 'MOVE'), ('SyntheticOther', 'MODIFY'), ('Majun', 'MODIFY'),
              ('Shared', 'MOVE'), ('Majun', 'MOVE'), ('Unassigned', 'MOVE')]
    paths = {}
    for i, (record, (owner, mode)) in enumerate(zip(records, owners)):
        count = len(record['owners'])
        assert count == (2 if i == 3 else 0 if i == 5 else 1)
        suffix = '__' + hashlib.sha256(record['guid'].encode()).hexdigest()[:8] if i in (0, 2, 4) else ''
        stem = (owner + '_' if owner not in ('Shared', 'Unassigned') else '') + record['original_name'] + suffix
        # Compare filename-only, internal-name-only and both changes.
        filename = 'Body' if i == 1 else stem
        record.update(output_path=f'Assets/VAPBExport/{owner}/Materials/{filename}.mat',
                      output_name=stem if i in (1, 2) else record['original_name'], mode=mode)
        source = assets[record['guid']]
        assert hashlib.sha256(source.asset_bytes).hexdigest() == record['sha256']
        payload = source.asset_bytes
        if i in (1, 2):
            payload, changed = re.subn(rb'(?m)^  m_Name:.*$',
                                      ('  m_Name: ' + stem).encode(), payload)
            assert changed == 1
        record['sha256'] = hashlib.sha256(payload).hexdigest()
        assets[record['guid']] = replace(source, pathname=record['output_path'], asset_bytes=payload,
            operation=mode, strategy='PRESERVE_AND_PATCH_SERIALIZED' if mode == 'MODIFY' else 'PRESERVE_VERBATIM',
            source_identity={'source_guid': source.guid, 'source_path': source.pathname})
        paths[record['guid']] = record['output_path']
    manifest_asset = next(a for a in assets.values() if a.pathname == 'Assets/VAPBExport/manifest.json')
    manifest = json.loads(manifest_asset.asset_bytes)
    selected_material = records[bind_index]
    for collection in (manifest['material_mappings'], manifest['reference_rebind_tasks'][0]['materials']):
        for record in collection:
            record['guid'] = selected_material['guid']
            record['file_id'] = selected_material['file_id']
            record['asset_sha256'] = hashlib.sha256(assets[record['guid']].asset_bytes).hexdigest()
    for record in manifest['export_assets']:
        guid = record['export_identity']['export_guid']
        if guid in paths:
            record['desired_export_path'] = paths[guid]
    assets[manifest_asset.guid] = replace(manifest_asset, asset_bytes=json.dumps(manifest).encode())
    tree = StagingTree(assets.values())
    assert len(tree) == len(assets)  # Shared logical asset appears only once.
    sample = assets[records[0]['guid']]
    for invalid in [replace(sample, guid='9'*32,
                            meta_bytes=re.sub(rb'guid: [0-9a-f]{32}', b'guid: '+b'9'*32, sample.meta_bytes)),
                    replace(sample, pathname='Assets/OtherCopy.mat')]:
        try:
            StagingTree([sample, invalid])
        except ValueError:
            pass
        else:
            raise AssertionError('COLLISION_NOT_REJECTED')
    destination.mkdir(parents=True, exist_ok=True)
    UnityPackageWriter().write(tree, destination / 'Output.unitypackage')
    evidence['finalizer_material_guid'] = selected_material['guid']
    evidence['finalizer_material_id'] = selected_material['file_id']
    (destination / 'Expected.json').write_text(json.dumps(evidence), encoding='utf-8')
    print('VAPB_NAMING_STAGING_PASS cases=5 collisions=2')


if __name__ == '__main__':
    mode, source, destination = sys.argv[1:4]
    if mode == 'stage':
        for asset in RawAssetRepository(Path(source)).read_all():
            path = Path(destination) / asset.pathname
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(asset.asset_bytes)
            Path(str(path)+'.meta').write_bytes(asset.meta_bytes)
    else:
        assert mode == 'relocate'
        relocate(Path(source), Path(destination), int(sys.argv[4]) if len(sys.argv)>4 else 0)
