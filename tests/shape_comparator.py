"""Independent channel identity/weight verdicts; geometry is not self-scored."""
import json
import hashlib
import math
from collections import Counter
from pathlib import Path
import sys

from unitypackage_blender_importer.blender.renderer_binding import semantic_owner_id


def compare_shapes(oracle, snapshot, witness):
    if (oracle['package_sha256'] != snapshot['package_sha256']
            or witness['source_unitypackage_sha256'] != oracle['package_sha256']):
        raise ValueError('SOURCE_REVISION_MISMATCH')
    witnessed = {}
    oracle_meshes = {(row['mesh']['guid'], str(row['mesh']['local_id'])): row for row in oracle['meshes']}
    if len(oracle_meshes) != len(oracle['meshes']):
        raise ValueError('DUPLICATE_MESH_IDENTITY')
    for asset in witness['assets']:
        if (asset['source_fbx_sha256'] != oracle['source_fbx_sha256']
                or asset['source_meta_sha256'] != oracle['source_meta_sha256']):
            raise ValueError('SOURCE_REVISION_MISMATCH')
        for model in asset['models']:
            for renderer in model['renderers']:
                mesh_key = (asset['asset_guid'], renderer['mesh_local_id'])
                if mesh_key in witnessed:
                    raise ValueError('DUPLICATE_MESH_IDENTITY')
                witnessed[mesh_key] = (model['geometry_uid'], renderer.get('shape_channels'))
    verdicts = []
    for renderer in oracle['prefab_renderers']:
        mesh = renderer['mesh']
        mesh_key = (mesh['guid'], str(mesh['local_id']))
        independent = oracle_meshes.get(mesh_key)
        if independent is None:
            verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
            continue
        if not independent['channels']:
            continue  # Independently observed zero-channel Mesh only.
        geometry_uid, channels = witnessed.get(mesh_key, (None, None))
        expected_indices = sorted(c['channel_index'] for c in independent['channels'])
        if not channels or sorted(c['unity_channel_index'] for c in channels) != expected_indices:
            verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
            continue
        identity = renderer['renderer']
        native = []
        for row in snapshot['objects']:
            record = row.get('renderer_record')
            if record and (record['source_key']['source_asset_guid'], str(record['source_key']['renderer_file_id'])) == (identity['guid'], str(identity['local_id'])):
                native.append(row)
        if len(native) != 1:
            verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
            continue
        row = native[0]
        record = row['renderer_record']
        if (row['renderer_occurrence'] != row['weight_occurrence'] or row['actual_owner'] != semantic_owner_id(record)
                or row['fbx_sha256'] != oracle['source_fbx_sha256']):
            verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
            continue
        expected_receipt = 'vapb-fbx-mesh:' + hashlib.sha256(f"{oracle['source_fbx_sha256']}:{geometry_uid}".encode()).hexdigest()
        if (row['geometry_uid'] != geometry_uid or row['mesh_receipt'] != expected_receipt
                or (record['mesh']['mesh_guid'], str(record['mesh']['mesh_file_id'])) != mesh_key):
            verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
            continue
        try:
            payload = row['key_properties']['_vapb_fbx_shape_receipts']
            if hashlib.sha256(payload.encode()).hexdigest() != row['key_properties']['_vapb_fbx_shape_receipt_sha256']:
                raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
            receipts = json.loads(payload)
            if receipts['geometry_uid'] != int(geometry_uid) or receipts['fbx_sha256'] != oracle['source_fbx_sha256']:
                raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
            if len(row['channels']) != len(receipts['channels']) + 1:
                raise ValueError('MISSING_KEYBLOCK')
            mapped = {r['channel_uid']: r for r in receipts['channels']}
            if len(mapped) != len(channels) or len({r['key_index'] for r in mapped.values()}) != len(channels):
                raise ValueError('CHANNEL_IDENTITY_UNPROVEN')
            for channel in channels:
                receipt = mapped[int(channel['channel_uid'])]
                key = row['channels'][receipt['key_index']]
                if (receipt['shape_uid'] != int(channel['shape_uid']) or key['relative_index'] != 0
                        or key['delta_sha256'] != receipt['delta_sha256']):
                    verdicts.append('CHANNEL_IDENTITY_UNPROVEN')
                else:
                    expected = renderer['current_weights'][channel['unity_channel_index']] / 100
                    verdicts.append('EXACT' if math.isfinite(key['value']) and abs(key['value']-expected) < 1e-6 else 'WEIGHT_VALUE_MISMATCH')
        except (KeyError, IndexError, ValueError) as exc:
            verdicts.append('MISSING_KEYBLOCK' if str(exc) == 'MISSING_KEYBLOCK' else 'CHANNEL_IDENTITY_UNPROVEN')
    return dict(status='GREEN' if verdicts and all(v == 'EXACT' for v in verdicts) else 'RED',
                counts=dict(Counter(verdicts)))


if __name__ == '__main__':
    oracle, snapshot, witness, output = map(Path, sys.argv[1:])
    result = compare_shapes(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in (oracle, snapshot, witness)))
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    sys.exit(0 if result['status'] == 'GREEN' else 1)
