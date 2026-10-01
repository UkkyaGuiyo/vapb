# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact external MonoScript references from the selected Skin Prefab chain."""
import hashlib
from pathlib import PurePosixPath
import re

from ..unity.yaml_parser import parse_unity_yaml


_KINDS = {'RESTORE_MODEL_SKIN_VARIANT_V1', 'RESTORE_DIRECT_SKIN_VARIANT_V1',
          'REBIND_SKINNED_RENDERER_V1'}


def _guid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{32}', value):
        raise ValueError('Script dependency GUID is invalid')
    return value.lower()


def _signed(value):
    text = str(value)
    if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)', text):
        raise ValueError('Script dependency signed fileID is invalid')
    number = int(text)
    if not number or not -(1 << 63) <= number < (1 << 63):
        raise ValueError('Script dependency signed fileID is out of range')
    return str(number)


def script_dependencies_for_tasks(tasks, assets):
    """Preserve references, without guessing a provider or traversing unused Prefabs."""
    by_guid = {}
    for asset in assets:
        guid = _guid(asset.guid)
        if guid in by_guid:
            raise ValueError('Script dependency closure has duplicated asset GUIDs')
        by_guid[guid] = asset
    records, visited, active = {}, set(), set()

    def visit(guid):
        if guid in active:
            raise ValueError('Script dependency Prefab source cycle')
        if guid in visited:
            return
        asset = by_guid.get(guid)
        if asset is None or PurePosixPath(asset.pathname).suffix.lower() != '.prefab':
            raise ValueError('Script dependency Prefab source is unavailable')
        active.add(guid)
        revision = hashlib.sha256(asset.asset_bytes).hexdigest()
        docs = parse_unity_yaml(asset.asset_bytes.decode('utf-8-sig'))
        if len({doc.file_id for doc in docs}) != len(docs):
            raise ValueError('Script dependency Prefab component identity is duplicated')
        for doc in docs:
            if doc.class_id == 114:
                reference = doc.data.get('m_Script')
                if isinstance(reference, dict) and reference == {'fileID': 0}:
                    continue  # Unassigned script remains an unexplained missing script.
                if not isinstance(reference, dict):
                    raise ValueError('Script dependency reference is malformed')
                provider = _guid(reference.get('guid'))
                file_id = _signed(reference.get('fileID'))
                component = _signed(doc.file_id)
                if provider in by_guid:
                    continue
                key = (provider, file_id)
                record = records.setdefault(key, dict(
                    classification='UNRESOLVED_BUT_PRESERVED', kind='UNITY_SCRIPT',
                    reference_id='VAPB-REF-' + hashlib.sha256(
                        f'UNITY_SCRIPT:{provider}:{file_id}'.encode('ascii')).hexdigest()[:32],
                    guid=provider, file_id=file_id, status='EXTERNAL_DEPENDENCY_REQUIRED',
                    required_by=[]))
                record['required_by'].append(dict(asset_guid=guid, asset_sha256=revision,
                                                  component_file_id=component))
            elif doc.class_id == 1001:
                reference = doc.data.get('m_SourcePrefab')
                if not isinstance(reference, dict):
                    raise ValueError('Script dependency Prefab source reference is malformed')
                source_guid = _guid(reference.get('guid'))
                source = by_guid.get(source_guid)
                if source is None:
                    raise ValueError('Script dependency Prefab source is outside the closure')
                if PurePosixPath(source.pathname).suffix.lower() == '.prefab':
                    visit(source_guid)
        active.remove(guid)
        visited.add(guid)

    for task in tasks:
        if task.get('kind') not in _KINDS:
            continue
        guid = _guid(task.get('prefab_guid'))
        source = by_guid.get(guid)
        if source is None or hashlib.sha256(source.asset_bytes).hexdigest() != task.get('prefab_source_sha256'):
            raise ValueError('Script dependency selected Prefab revision is stale')
        visit(guid)
    for record in records.values():
        record['required_by'].sort(key=lambda row: (row['asset_guid'], int(row['component_file_id'])))
    return tuple(records[key] for key in sorted(records))
