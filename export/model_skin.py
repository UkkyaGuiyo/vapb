"""Build a deferred model-skin task from confirmed source and instance evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re

from ..unity.yaml_parser import parse_unity_yaml


_GUID = re.compile(r"[0-9a-fA-F]{32}\Z")
_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")
_SIGNED_ID = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


def _guid(value):
    if not isinstance(value, str) or not _GUID.fullmatch(value):
        raise ValueError("Asset GUID is incomplete")
    return value.lower()


def _sha(value):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError("Source revision is incomplete")
    return value.lower()


def _id(value):
    if not isinstance(value, str) or not _SIGNED_ID.fullmatch(value):
        raise ValueError("Signed local ID is incomplete")
    number = int(value)
    if number == 0 or number < -(1 << 63) or number >= (1 << 63):
        raise ValueError("Signed local ID is out of range")
    return value


def _asset(by_guid, guid, extension, sha):
    source = by_guid.get(guid)
    if source is None or PurePosixPath(source.pathname).suffix.lower() != extension:
        raise ValueError("Source asset is missing or has the wrong type")
    if hashlib.sha256(source.asset_bytes).hexdigest() != sha:
        raise ValueError("Source asset revision changed")
    return source


def model_skin_task(metadata, bone_mappings, assets):
    """Verify the ordered class1001 path; leave FBX and Unity ID mapping to witnesses."""
    try:
        prefab_guid = _guid(metadata['prefab_guid'])
        prefab_sha = _sha(metadata['prefab_source_sha256'])
        model_guid = _guid(metadata['source_model_guid'])
        model_sha = _sha(metadata['source_model_sha256'])
        model_uid = _id(metadata['source_model_uid'])
        geometry_uid = _id(metadata['source_geometry_uid'])
        realization_id = metadata['realization_id']
        raw_edges = metadata['instance_edges']
    except (KeyError, TypeError) as exc:
        raise ValueError("Model skin metadata is incomplete") from exc
    if not isinstance(realization_id, str) or not realization_id or not isinstance(raw_edges, list) or not raw_edges:
        raise ValueError("Model occurrence is incomplete")

    by_guid = {}
    for source in assets:
        guid = _guid(source.guid)
        if guid in by_guid:
            raise ValueError("Source asset GUID is duplicated")
        by_guid[guid] = source
    _asset(by_guid, prefab_guid, '.prefab', prefab_sha)
    _asset(by_guid, model_guid, '.fbx', model_sha)

    edges = []
    expected_container = prefab_guid
    for raw in raw_edges:
        try:
            container = _guid(raw['container_guid'])
            revision = _sha(raw['container_sha256'])
            instance_id = _id(raw['instance_file_id'])
            source_guid = _guid(raw['source_guid'])
        except (KeyError, TypeError) as exc:
            raise ValueError("Prefab instance edge is incomplete") from exc
        if container != expected_container:
            raise ValueError("Prefab instance edge chain is broken")
        source = _asset(by_guid, container, '.prefab', revision)
        docs = parse_unity_yaml(source.asset_bytes.decode('utf-8-sig'))
        if len({doc.file_id for doc in docs}) != len(docs):
            raise ValueError("Prefab document local ID is duplicated")
        match = next((doc for doc in docs if doc.file_id == int(instance_id)), None)
        reference = match.data.get('m_SourcePrefab') if match is not None and match.class_id == 1001 else None
        if not isinstance(reference, dict) or _guid(reference.get('guid')) != source_guid:
            raise ValueError("Prefab instance source does not match serialized edge")
        edges.append({'container_guid': container, 'container_sha256': revision,
                      'instance_file_id': instance_id, 'source_guid': source_guid})
        expected_container = source_guid
    if expected_container != model_guid:
        raise ValueError("Prefab instance path does not end at the source FBX")

    if not isinstance(bone_mappings, list) or not bone_mappings:
        raise ValueError("Bone mappings are incomplete")
    bones = []
    seen_edits, seen_sources = set(), set()
    for row in bone_mappings:
        try:
            edited = row['edited_bone_realization_id']
            source_uid = _id(row['source_model_uid'])
        except (KeyError, TypeError) as exc:
            raise ValueError("Bone mapping is incomplete") from exc
        if not isinstance(edited, str) or not edited or edited in seen_edits or source_uid in seen_sources:
            raise ValueError("Bone mapping identity is missing or duplicated")
        seen_edits.add(edited)
        seen_sources.add(source_uid)
        bones.append({'edited_bone_realization_id': edited, 'source_model_uid': source_uid})
    bones.sort(key=lambda row: int(row['source_model_uid']))

    identity = {'prefab_guid': prefab_guid, 'instance_edges': edges, 'realization_id': realization_id}
    suffix = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {
        'kind': 'RESTORE_MODEL_SKIN_VARIANT_V1',
        'prefab_guid': prefab_guid, 'prefab_source_sha256': prefab_sha,
        'source_model_guid': model_guid, 'source_model_sha256': model_sha,
        'source_model_uid': model_uid, 'source_geometry_uid': geometry_uid,
        'realization_id': realization_id, 'instance_edges': edges, 'bone_mappings': bones,
        'variant_path': f'Assets/VAPBExport/EditedVariant_{suffix}.prefab',
    }
