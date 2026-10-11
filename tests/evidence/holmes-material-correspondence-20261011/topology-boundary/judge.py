"""Independent exact corner/edge cover, using explicit native topology. No predictions."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from read_input import decode, parse


def sign_area(uv):
    area = sum(a[0]*b[1] - a[1]*b[0] for a, b in zip(uv, uv[1:] + uv[:1]))
    if area == 0:
        raise ValueError('degenerate UV face')
    return 1 if area > 0 else -1


def cover(raw_uv, observed):
    raw = [tuple(x) for x in raw_uv]
    if len(raw) not in (3, 4) or len(set(raw)) != len(raw):
        raise ValueError('unsupported or ambiguous polygon corners')
    # This experiment's polygons are strictly convex in exact fingerprint UV space.
    turn = []
    for i in range(len(raw)):
        a, b, c = raw[i-2], raw[i-1], raw[i]
        cross = (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
        if cross == 0: raise ValueError('non-strict convex fingerprint')
        turn.append(1 if cross > 0 else -1)
    if len(set(turn)) != 1:
        raise ValueError('nonconvex fingerprint')
    faces = [[tuple(x) for x in f] for f in observed]
    if (len(raw) == 3 and [len(f) for f in faces] != [3]) or (len(raw) == 4 and sorted(len(f) for f in faces) not in ([4], [3, 3])):
        raise ValueError('missing/duplicate face or incompatible topology')
    edges, directed = Counter(), Counter()
    orientations = []
    for f in faces:
        if len(set(f)) != len(f) or not set(f) <= set(raw):
            raise ValueError('ambiguous/unknown native corner')
        orientations.append(sign_area(f)*sign_area(raw))
        for a, b in zip(f, f[1:] + f[:1]):
            edges[tuple(sorted((a, b)))] += 1
            directed[(a, b)] += 1
    if len(set(orientations)) != 1:
        raise ValueError('inconsistent winding')
    boundary = Counter(tuple(sorted((a, b))) for a, b in zip(raw, raw[1:]+raw[:1]))
    if any(edges[e] != 1 for e in boundary):
        raise ValueError('polygon boundary multiplicity mismatch')
    internal = {e: n for e, n in edges.items() if e not in boundary}
    expected_internal = 1 if len(faces) == 2 else 0
    if len(internal) != expected_internal or any(n != 2 or directed[(e[0], e[1])] != 1 or directed[(e[1], e[0])] != 1 for e, n in internal.items()):
        raise ValueError('internal diagonal does not cancel exactly')
    return orientations[0]


def native_faces(snapshot):
    if snapshot['apply_base_vertex'] is not True:
        raise ValueError('indices must already include baseVertex')
    uv = [(p['x'], p['y']) for p in snapshot['uv']]
    faces = []
    for ordinal, group in enumerate(snapshot['groups']):
        topology = group['topology']
        if topology not in ('Triangles', 'Quads'):
            raise ValueError('unsupported native topology: ' + topology)
        width = 3 if topology == 'Triangles' else 4
        indices = group['indices']
        if group['index_count'] != len(indices) or len(indices) % width:
            raise ValueError('topology/index stream mismatch')
        for i in range(0, len(indices), width):
            ids = indices[i:i+width]
            if any(type(k) is not int or not 0 <= k < len(uv) for k in ids):
                raise ValueError('native index out of range')
            faces.append(dict(group=ordinal, topology=topology, indices=ids, uv=[uv[k] for k in ids]))
    return faces


def membership(raw, snapshot):
    polygons = raw['polygons']
    matched = {p['polygon']: [] for p in polygons}
    for face in native_faces(snapshot):
        candidates = [p for p in polygons if set(face['uv']) <= {tuple(x) for x in p['uv']}]
        if len(candidates) != 1:
            raise ValueError('native face requires unique original polygon and exact corners')
        matched[candidates[0]['polygon']].append(face)
    rows = []
    for p in polygons:
        observed = matched[p['polygon']]
        orientation = cover(p['uv'], [f['uv'] for f in observed])
        groups = {f['group'] for f in observed}
        if len(groups) != 1:
            raise ValueError('one original polygon spans different native groups; UNDETERMINED')
        rows.append(dict(polygon=p['polygon'], group=next(iter(groups)), raw_uid=p['uid'],
                         winding=orientation, native_faces=observed))
    return rows


def validate_labels(recomputed, reported):
    if reported != recomputed:
        raise ValueError('reported face/group/Material labels differ from independent recomputation')


def changed_paths(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        return [row for k in sorted(set(a) | set(b)) for row in changed_paths(a.get(k), b.get(k), path+(k,))]
    return [] if a == b else [(list(path), a, b)]


def judge(raw, off, on):
    if off['unity_version'] != '2022.3.22f1' or on['unity_version'] != off['unity_version']:
        raise ValueError('Unity version differs')
    if off['fbx_sha256'] != on['fbx_sha256'] or off['fbx_sha256'] != off['fbx_sha256_after'] or on['fbx_sha256'] != on['fbx_sha256_after']:
        raise ValueError('FBX bytes differ')
    for item, keep in [(off, False), (on, True)]:
        if item['keep_quads'] is not keep or item['meta_sha256'] != item['meta_sha256_after']:
            raise ValueError('keepQuads or stable metadata mismatch')
    delta = changed_paths(json.loads(off['policy']), json.loads(on['policy']))
    if delta != [(['meshes', 'keepQuads'], False, True)] and delta != [(['meshes', 'keepQuads'], 0, 1)]:
        raise ValueError(('unexpected effective importer changes', delta))
    if off['mesh'] != on['mesh'] or off['renderer'] != on['renderer']:
        raise ValueError('native Mesh/Renderer identities differ')
    result = dict(effective_policy_changes=delta, conditions={})
    for name, item in [('OFF', off), ('ON', on)]:
        rows = membership(raw, item)
        groups = []
        for index, group in enumerate(item['groups']):
            selected = [r for r in rows if r['group'] == index]
            groups.append(dict(ordinal=index, topology=group['topology'], index_count=group['index_count'],
                               base_vertex=group['base_vertex'], polygons=[r['polygon'] for r in selected],
                               raw_uid_polygon_counts=dict(Counter(str(r['raw_uid']) for r in selected)),
                               native_material=item['materials'][index] if index < len(item['materials']) else {'missing_array_entry': True}))
        result['conditions'][name] = dict(groups=groups, memberships=rows, materials=item['materials'],
                                         mesh=item['mesh'], renderer=item['renderer'],
                                         material_array_count=len(item['materials']), submesh_count=len(item['groups']))
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for arg in ['repo', 'addon', 'fbx', 'observations', 'output']:
        ap.add_argument('--'+arg, type=Path, required=True)
    args = ap.parse_args()
    root, version = parse(args.fbx, args.repo, args.addon)
    raw = decode(root)
    snapshots = [json.loads((args.observations / (name+'.json')).read_text(encoding='utf-8-sig')) for name in ['OFF', 'ON']]
    sha = hashlib.sha256(args.fbx.read_bytes()).hexdigest()
    if any(s['fbx_sha256'] != sha for s in snapshots):
        raise ValueError('native capture not bound to raw FBX')
    result = judge(raw, *snapshots)
    result.update(raw=raw, fbx_sha256=sha, fbx_version=version,
                  position_comparison='NOT_RUN', render='NOT_RUN', product_guard_changed=False)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2)
    print('INDEPENDENT_TOPOLOGY_JUDGE_PASS')
