"""Independent single-composition hierarchy comparison, names never used as keys.

This first checkpoint compares persistent prefab occurrence GO identities,
semantic Object parent relations and local/world TRS. Native renderer/bone
equivalence without an authoritative occurrence bridge is reported unsupported,
never inferred from native names or counts.
"""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys


def identity(ref):
    return None if ref is None else (ref['guid'], str(ref['localId']))


def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def unity_trs(node):
    p, q, s = node['localPosition'], node['localRotation'], node['localScale']
    x, y, z, w = (q[k] for k in ('x', 'y', 'z', 'w'))
    matrix = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), p['x']],
              [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), p['y']],
              [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), p['z']], [0, 0, 0, 1]]
    for i in range(3):
        for j, axis in enumerate(('x', 'y', 'z')):
            matrix[i][j] *= s[axis]
    return matrix


def convert(matrix):
    # Declared Unity-world -> Blender basis, independent of production helpers.
    basis = [[-1,0,0,0], [0,0,-1,0], [0,1,0,0], [0,0,0,1]]
    inverse = [list(row) for row in zip(*basis)]
    return multiply(multiply(basis, matrix), inverse)


def matrix_equal(a, b, tolerance=2e-5):
    # Float32 TRS decomposition error grows with scale (fixture reaches 180).
    tolerance += 1e-6 * max(abs(v) for matrix in (a,b) for row in matrix for v in row)
    return all(math.isfinite(v) for matrix in (a,b) for row in matrix for v in row) and max(
        abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4)) <= tolerance


def compare(oracle, snapshot, expected_sha):
    if snapshot['package_sha256'] != expected_sha:
        raise ValueError('Input revision mismatch')
    if snapshot['import_result'] != ['FINISHED']:
        raise ValueError('Incomplete normal Import')
    if len({node['gameObject']['globalId'] for node in oracle['nodes']}) != len(oracle['nodes']):
        raise ValueError('Duplicate Unity occurrence identity')
    assets = {path: guid for guid, path in snapshot['assets'].items()}
    # Unity-generated selected-prefab GO IDs need not be serialized in source.
    # Bridge only through exact source GO + ordered public instance handles.
    aliases = defaultdict(list)
    for node in oracle['nodes']:
        chain, handles = node.get('sourceChain', []), node.get('instanceHandles', [])
        if len(chain) == 1 and handles:
            alias = (*identity(chain[0]), tuple(identity(h) for h in reversed(handles)))
            aliases[alias].append(identity(node['gameObject']))
    contexts = {o['metadata']['_vapb_root_context_id'] for o in snapshot['objects']
                if o['metadata'].get('_vapb_root_context_id')}
    if len(contexts) > 1:
        raise ValueError('Multiple root contexts require explicit selected-root scope')
    candidates = defaultdict(list)
    handles = {obj['handle']: obj for obj in snapshot['objects']}
    by_handle = {}
    for obj in snapshot['objects']:
        if obj['classification'] != 'SEMANTIC':
            continue
        meta = obj['metadata']
        if meta.get('unity_source_package_id') != 'sha256:' + expected_sha:
            raise ValueError('Semantic source revision mismatch')
        key = (assets.get(meta.get('unity_asset_path')), str(meta.get('unity_prefab_file_id')))
        if meta.get('unity_source_prefab_guid') and meta.get('_vapb_model_instance_edge_path'):
            if not meta.get('_vapb_root_context_id'):
                raise ValueError('Missing nested occurrence root context')
            edges = json.loads(meta['_vapb_model_instance_edge_path'])
            if not edges or edges[-1]['source_prefab_guid'] != meta['unity_source_prefab_guid']:
                raise ValueError('Invalid nested source edge')
            if any(e['container_package_id'] != 'sha256:'+expected_sha or
                   e['source_package_id'] != 'sha256:'+expected_sha for e in edges):
                raise ValueError('Nested source revision scope mismatch')
            alias = (meta['unity_source_prefab_guid'], str(meta['unity_prefab_file_id']),
                     tuple((e['container_asset_guid'], str(e['prefab_instance_file_id'])) for e in edges))
            targets = aliases.get(alias, [])
            if len(targets) != 1:
                raise ValueError('Ambiguous/unproven source-to-occurrence bridge')
            key = targets[0]
        candidates[key].append(obj)
        by_handle[obj['handle']] = key
    transform_to_go = {identity(n['transform']): identity(n['gameObject']) for n in oracle['nodes']}
    checks = []
    def record(category, dimension, key):
        checks.append(dict(category=category, dimension=dimension, identity=list(key)))
    expected = {identity(n['gameObject']) for n in oracle['nodes']}
    oracle_counts = Counter(identity(n['gameObject']) for n in oracle['nodes'])
    for node in oracle['nodes']:
        key = identity(node['gameObject'])
        if oracle_counts[key] > 1:
            record('AMBIGUOUS', 'occurrence_bridge', key)
            continue
        matches = candidates.get(key, [])
        if not matches:
            record('MISSING', 'node', key)
            continue
        if len(matches) != 1:
            record('DUPLICATE_OCCURRENCE', 'node', key)
            continue
        obj = matches[0]
        record('EXACT', 'node', key)
        parent = transform_to_go.get(identity(node['parentTransform']))
        actual_parent = by_handle.get(obj['actual_parent'])
        # A root wrapper may be ignored only when it has no semantic identity.
        unknown_parent = obj['actual_parent'] is not None and obj['actual_parent'] not in by_handle
        valid_root = parent is None and (obj['actual_parent'] is None or
                     handles[obj['actual_parent']]['classification'] == 'TECHNICAL_ONLY')
        record('EXACT' if valid_root or (not unknown_parent and parent == actual_parent)
               else 'WRONG_PARENT', 'parent', key)
        for dimension, observed, wanted in (
            ('local', obj['local_matrix'], convert(unity_trs(node))),
            ('world', obj['world_matrix'], convert([[node['worldMatrix'][j*4+i]
                for j in range(4)] for i in range(4)]))):
            record('EXACT' if matrix_equal(observed, wanted) else 'TRANSFORM_MISMATCH', dimension, key)
        # Projection metadata describes source intent, not actual native binding.
        # Do not turn it into a proof of Renderer/Bone realization.
        for renderer in node['renderers']:
            for dimension in ('renderer_owner', 'mesh', 'bones_order', 'root_bone', 'bone_representation'):
                record('UNSUPPORTED_REPRESENTATION', dimension, key)
    for key, objects in candidates.items():
        if key not in expected:
            for obj in objects:
                record('EXTRA_SEMANTIC', 'node', key)
    repeated = defaultdict(list)
    for node in oracle['nodes']:
        if node['sourceChain']:
            repeated[identity(node['sourceChain'][0])].append(identity(node['gameObject']))
    for group in repeated.values():
        if len(group) > 1 and any(not candidates.get(key) for key in group):
            record('MISSING_OCCURRENCE', 'multiplicity', group[0])
    counts = dict(Counter(c['category'] for c in checks))
    return dict(status='GREEN' if all(c['category'] == 'EXACT' for c in checks) else 'RED',
        scope='SINGLE_COMPOSITION_OBJECT_RELATIONS; native skin equivalence unimplemented',
        counts=counts, dimensions={d: dict(Counter(c['category'] for c in checks if c['dimension']==d))
            for d in sorted({c['dimension'] for c in checks})}, checks=checks,
        blender=dict(semantic_nodes=len(by_handle),
            semantic_edges=sum(obj['actual_parent'] in by_handle for obj in snapshot['objects'] if obj['handle'] in by_handle),
            technical_helpers=sum(o['classification']=='TECHNICAL_ONLY' for o in snapshot['objects']),
            unmapped_realizations=sum(o['classification']=='UNMAPPED_REALIZATION' for o in snapshot['objects'])))


if __name__ == '__main__':
    oracle_path, snapshot_path, sha, output_path = sys.argv[1:]
    result = compare(json.loads(Path(oracle_path).read_text()), json.loads(Path(snapshot_path).read_text()), sha)
    Path(output_path).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('status', 'counts', 'dimensions', 'blender')}))
    sys.exit(0 if result['status'] == 'GREEN' else 1)
