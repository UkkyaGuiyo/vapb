"""Retain existing occurrence usage on Materials independently of Mesh lifetime."""
import hashlib
import json
import re

KEY = '_vapb_material_owner_usage'


def _records(material):
    try:
        value = json.loads(str(material.get(KEY, '[]')))
        return value if isinstance(value, list) else []
    except (ValueError, TypeError):
        return []


def capture_owner_usage(records, label, materials):
    """Copy only exact projected references with an unambiguous imported provider."""
    materials = tuple(materials)
    for record in records:
        if record.get('material_status') != 'EXACT':
            continue
        scope = ('root_package_id', 'root_member_id', 'root_asset_guid',
                 'root_revision_sha256', 'source_revision_sha256', 'occurrence_id')
        if any(not record.get(key) for key in scope):
            continue
        for reference in record.get('materials', {}).values():
            if not isinstance(reference, dict):
                continue
            guid, file_id = str(reference.get('guid', '')).lower(), str(reference.get('file_id', ''))
            matches = [m for m in materials if m.get('unity_material_guid') == guid
                       and str(m.get('unity_material_file_id', '')) == file_id]
            local = [m for m in matches if m.get('unity_source_package_id') == reference.get('source_package_id')]
            if local:
                matches = local
            if len(matches) != 1:
                continue
            material = matches[0]
            package = str(material.get('unity_source_package_id', ''))
            sha = str(material.get('_vapb_source_material_sha256', ''))
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', package) or not re.fullmatch(r'[0-9a-f]{64}', sha):
                continue
            usage = {key: record[key] for key in scope}
            usage.update(material_guid=guid, material_file_id=file_id,
                         provider_package_id=package, material_sha256=sha, owner_label=str(label))
            existing = _records(material)
            if usage not in existing:
                existing.append(usage)
            material[KEY] = json.dumps(existing, ensure_ascii=False, sort_keys=True)


def proven_owners(material, package_id, guid, file_id, payload):
    """Revision/identity mismatch is not usable label evidence."""
    owners = {}
    for usage in _records(material):
        if not isinstance(usage, dict) or any(usage.get(key) != value for key, value in (
                ('provider_package_id', package_id), ('material_guid', guid),
                ('material_file_id', file_id), ('material_sha256', hashlib.sha256(payload).hexdigest()))):
            continue
        keys = ('root_package_id', 'root_member_id', 'root_asset_guid')
        if any(not usage.get(key) for key in keys + ('occurrence_id', 'root_revision_sha256', 'source_revision_sha256')):
            continue
        owner = json.dumps([usage[key] for key in keys])
        label = str(usage.get('owner_label', ''))
        if not label or owner in owners and owners[owner] != label:
            return {}  # Competing human labels cannot select a winner.
        owners[owner] = label
    return owners


def capture_scene_owner_usage(objects, materials):
    """Revisit saved projections when a late Material provider arrives."""
    for obj in objects:
        label = obj.get('_vapb_material_owner_label')
        if not label:
            continue
        try:
            projection = json.loads(str(obj.get('_vapb_renderer_occurrences', '{}')))
            records = projection.get('records', [])
        except (TypeError, ValueError, AttributeError):
            continue
        capture_owner_usage(records, label, materials)
