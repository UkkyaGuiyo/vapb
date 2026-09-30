"""Pure output labels after Material identity/provider resolution; no payload edits."""
import hashlib
import re
import unicodedata

from .staging import normalize_guid, portable_path_key


def _label(value):
    value = unicodedata.normalize('NFC', str(value))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')
    if not value:
        value = 'Unnamed'
    if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])', value.split('.')[0], re.I):
        value = '_' + value
    # Leave room for owner prefix, suffix and extension under staging budgets.
    while len(value.encode('utf-8')) > 40:
        value = value[:-1]
    return value


def allocate_material_paths(rows):
    """GUID-keyed paths; owner keys must come from already-proved usage."""
    candidates = {}
    for row in rows:
        guid = normalize_guid(row['guid'])
        owners = row['owners']
        if len(owners) == 1:
            owner = _label(next(iter(owners.values())))
            # These words are reserved neutral folders, not ownership claims.
            if owner.casefold() in {'shared', 'unassigned'}:
                owner = '_' + owner
            prefix = owner + '_'
        else:
            owner = 'Shared' if len(owners) > 1 else 'Unassigned'
            prefix = ''
        stem = prefix + _label(row['name'])
        path = f'Assets/VAPBExport/{owner}/Materials/{stem}.mat'
        if guid in candidates and candidates[guid] != path:
            raise ValueError('conflicting canonical Material naming inputs')
        candidates[guid] = path
    groups = {}
    for guid, path in candidates.items():
        groups.setdefault(portable_path_key(path), []).append(guid)
    result = dict(candidates)
    for group in groups.values():
        if len(group) > 1:
            for guid in group:
                suffix = hashlib.sha256(guid.encode()).hexdigest()[:12]
                result[guid] = candidates[guid][:-4] + '__' + suffix + '.mat'
    if len({portable_path_key(path) for path in result.values()}) != len(result):
        raise ValueError('deterministic Material suffix collision')
    return result
