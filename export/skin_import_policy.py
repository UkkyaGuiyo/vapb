# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt in exact generated Skin revisions to pre-import weight preservation."""
import hashlib
import json
import re
from .staging import StagedUnityAsset


def skin_weight_policy_assets(tasks):
    revisions = {}
    for task in tasks:
        if task.get('kind') not in {'REBIND_SKINNED_RENDERER_V1',
                'RESTORE_MODEL_SKIN_VARIANT_V1', 'RESTORE_DIRECT_SKIN_VARIANT_V1'}:
            continue
        guid, sha = task.get('model_guid', ''), task.get('model_sha256', '')
        if not re.fullmatch('[0-9a-f]{32}', guid) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('Skin import policy requires exact generated model revision')
        if guid in revisions and revisions[guid] != sha:
            raise ValueError('Skin import policy model revisions conflict')
        revisions[guid] = sha
    assets = []
    for guid, sha in sorted(revisions.items()):
        path = f'Assets/VAPBExport/SkinWeightPolicy_{guid}.json'
        identity = hashlib.sha256(('VAPB_SKIN_WEIGHT_POLICY_V1:' + path).encode()).hexdigest()[:32]
        payload = json.dumps(dict(version=1, model_guid=guid, model_sha256=sha), sort_keys=True).encode()
        assets.append(StagedUnityAsset(identity, path, payload,
            f'fileFormatVersion: 2\nguid: {identity}\n'.encode(), operation='CREATE'))
    return tuple(assets)
