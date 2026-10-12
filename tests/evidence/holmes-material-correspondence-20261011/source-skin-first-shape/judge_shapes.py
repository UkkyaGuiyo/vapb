"""Fixture oracle: raw Shape graph/CP streams -> independent native CP-marked buffers.

Names do not select channels. The fixed synthetic FBX/native local basis is checked
against the original source control before evaluating the authored delta. This is
not a product policy or a general FBX scale guarantee.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import types
import tarfile
import re

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
p.add_argument('--parser-root', type=Path, required=True)
p.add_argument('--phase', default='native-green')
a = p.parse_args()
package = types.ModuleType('_holmes_installed_fbx_parser')
package.__path__ = [str(a.parser_root)]
sys.modules[package.__name__] = package
parser = importlib.import_module(package.__name__ + '.parse_fbx')
assert Path(parser.__file__).resolve() == (a.parser_root / 'parse_fbx.py').resolve()
f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
xyz = lambda x: (x['x'], x['y'], x['z'])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
tol = 1e-7  # Frozen before GREEN3; reused task04 tolerance, small relative to the added nonzero delta.


def read(path):
    root, _ = parser.parse(str(path), use_namedtuple=True)
    objects = next(n for n in root.elems if n.id == b'Objects')
    nodes = {n.props[0]: n for n in objects.elems}
    assert len(nodes) == len(objects.elems)
    geom, = [n for n in objects.elems if n.id == b'Geometry' and n.props[2] == b'Mesh']
    children = {}
    for row in next(n for n in root.elems if n.id == b'Connections').elems:
        if row.id == b'C' and len(row.props) == 3 and row.props[0] == b'OO':
            children.setdefault(row.props[2], []).append(row.props[1])
    values = lambda n, key: list(next(q.props[0] for q in n.elems if q.id == key))
    points = values(geom, b'Vertices')
    points = [points[i:i+3] for i in range(0, len(points), 3)]
    blends = [i for i in children.get(geom.props[0], []) if nodes[i].id == b'Deformer' and nodes[i].props[2] == b'BlendShape']
    if not blends:
        return dict(sha256=sha(path),geometry_uid=geom.props[0],points=points,channels=[])
    blend, = blends
    rows = []
    for uid in children[blend]:
        channel = nodes[uid]
        assert channel.id == b'Deformer' and channel.props[2] == b'BlendShapeChannel'
        shape_uid, = children[uid]
        shape = nodes[shape_uid]
        assert shape.id == b'Geometry' and shape.props[2] == b'Shape'
        assert values(channel, b'FullWeights') and all(x == 100. for x in values(channel, b'FullWeights'))
        indices, data = values(shape, b'Indexes'), values(shape, b'Vertices')
        assert len(indices) == len(set(indices)) and len(data) == 3*len(indices)
        deltas = [[0.,0.,0.] for _ in points]
        for i, cp in enumerate(indices):
            assert 0 <= cp < len(points)
            deltas[cp] = data[3*i:3*i+3]
        rows.append(dict(channel_uid=uid, shape_uid=shape_uid, deltas=deltas,
                         deform_percent=next(e.props[0] for e in channel.elems if e.id == b'DeformPercent')))
    return dict(sha256=sha(path), geometry_uid=geom.props[0], points=points, channels=rows)


def local(point):
    return (f32(-point[0]*.01), f32(point[1]*.01), f32(point[2]*.01))


def native_rows(skin, cp):
    rows = []
    for channel in skin['shape_data']:
        assert len(channel['frames']) == 1 and channel['frames'][0]['weight'] == 100.
        delta = channel['frames'][0]['delta_vertices']
        mapped = {}
        for i, index in enumerate(cp):
            value = xyz(delta[i])
            if index in mapped:
                assert mapped[index] == value
            mapped[index] = value
        assert set(mapped) == set(range(len(source['points'])))
        rows.append([mapped[i] for i in range(len(source['points']))])
    return rows


def join(raw, native):
    result = []
    used = set()
    for row in raw['channels']:
        expected = [local(d) for d in row['deltas']]
        candidates = [j for j, values in enumerate(native) if all(
            abs(values[i][k]-expected[i][k]) <= tol for i in range(len(source['points'])) for k in range(3))]
        j, = candidates
        assert j not in used
        used.add(j)
        result.append(dict(channel_uid=row['channel_uid'],shape_uid=row['shape_uid'],
                           native_channel=j,max_abs_error=max(abs(native[j][i][k]-expected[i][k])
                           for i in range(len(source['points'])) for k in range(3))))
    return result


work = a.work
source = read(work/'Source.fbx')
final = read(work/'green-export/Export.fbx')
edit = json.loads((work/'edit/result.json').read_text())
native = json.loads((work/a.phase/'native.json').read_text())
assert len(source['points']) == len(final['points']) == 4
assert final['points'] == edit['after']['vertices'] == edit['before']['vertices'] == source['points']
assert len(set(map(tuple,source['points']))) == 4
source_lookup = {local(v): i for i,v in enumerate(source['points'])}
source_cp = [source_lookup[xyz(v)] for v in native['source']['vertices']]
source_join = join(source,native_rows(native['source'],source_cp))
# Final raw channel identity is joined to authored keys by entire delta streams.
basis = edit['after']['channels'][0]['points']
key_rows = [[tuple(f32(k['points'][i][j]-basis[i][j]) for j in range(3))
             for i in range(len(source['points']))] for k in edit['after']['channels'][1:]]
key_joins = []
for row in final['channels']:
    key, = [i for i,k in enumerate(key_rows) if list(map(tuple,row['deltas'])) == k]
    assert row['deform_percent'] == edit['after']['channels'][key+1]['value'] * 100.
    key_joins.append(dict(channel_uid=row['channel_uid'],shape_uid=row['shape_uid'],authored_key_index=key+1,
                          deform_percent=row['deform_percent']))
observations = []
for path in sorted((work/a.phase).glob('weight-observation-*.json')):
    obs = json.loads(path.read_text())
    cp = [int(v['x'])-1 for v in obs['cp_marker']]
    assert all(v['x'] == i+1 and v['y'] == .375 for v,i in zip(obs['cp_marker'],cp))
    assert all(xyz(v) == local(final['points'][i]) for v,i in zip(obs['skin']['vertices'],cp))
    rows = native_rows(obs['skin'],cp)
    joined = join(final,rows)
    observations.append(dict(fbx_sha256=obs['fbx_sha256'],channel_joins=joined))
    assert obs['skin']['vertices'] == native['post_import']['vertices']
    assert obs['skin']['shape_data'] == native['post_import']['shape_data']
assert observations
assert native['apply'] and native['repeat_apply'] and native['source_bytes_preserved']
assert native['variant']['mesh'] == native['post_import']['mesh']
assert native['variant']['shape_data'] == native['post_import']['shape_data']
assert native['variant']['source_bones'] == native['source']['bones']
assert native['variant']['source_root'] == native['source']['root']
assert native['variant']['materials'] == native['source']['materials']
assert native['variant']['matrix'] == native['source']['matrix']
assert native['source']['shape_weights'] == []
assert native['post_import']['shape_weights'] == native['variant']['shape_weights'] == [0.]
assert edit['before']['channels'] == [] and len(edit['after']['channels']) == 2
assert edit['after']['channels'][0]['points'] == edit['before']['vertices']
assert {k:v for k,v in edit['before'].items() if k != 'channels'} == {k:v for k,v in edit['after'].items() if k != 'channels'}
assert len(key_joins) == 1 and {r['authored_key_index'] for r in key_joins} == {1}
assert all(native[k] for k in ['repeat_variant_bytes_unchanged','repeat_variant_meta_unchanged','repeat_variant_semantics_unchanged'])
task = json.loads((work/'green-export/result.json').read_text())['task']
expected = {p['cp']:dict(zip(p['bone_realization_ids'],p['expected_bits']))
            for p in task['weight_transport']['points']}
weight_mismatches = 0
for path in (work/a.phase).glob('weight-observation-*.json'):
    obs = json.loads(path.read_text())
    for marker, point in zip(obs['cp_marker'],obs['skin']['weights']):
        actual = {obs['bone_receipts'][g['bone']]:g['bits'] for g in point['influences']}
        if actual != expected[int(marker['x'])-1]: weight_mismatches += 1
assert weight_mismatches == 0
assert native['variant']['weights'] == native['post_import']['weights']
assert sha(work/'Source.unitypackage') == sha(work.parent/'holmes-source-skin-authored-weight-20261012-03/Source.unitypackage')
assert native['source']['mesh']['guid'] == task['source_model_guid']
assert native['post_import']['mesh']['guid'] == task['model_guid']
original_assets = []
with tarfile.open(work/'Source.unitypackage','r:gz') as archive:
    for member in archive.getmembers():
        if member.name.endswith('/pathname'):
            guid = member.name.split('/')[0]
            asset = archive.extractfile(guid+'/asset').read()
            meta = archive.extractfile(guid+'/asset.meta').read()
            paths = [p for p in (work/'Project/Assets').rglob('*.meta')
                     if re.search(r'^guid: '+guid+r'\s*$',p.read_text(encoding='utf-8'),re.M)]
            stored_meta, = paths
            stored = stored_meta.with_suffix('')
            assert stored.read_bytes() == asset and stored_meta.read_bytes() == meta
            original_assets.append(dict(guid=guid,asset_sha256=sha(stored),meta_sha256=sha(stored_meta)))
result = dict(status='PASS',source=source,final=final,source_channel_native_joins=source_join,
              final_channel_authored_key_joins=key_joins,native_cp_channel_observations=observations,
              native_variant_final_delta_and_uniform_weights_exact=True,
              repeat_variant_bytes_meta_semantics_exact=True,tolerance=tol,
              parser_sha256=sha(a.parser_root/'parse_fbx.py'),labels_used_for_identity=False,
              exact_cp_weight_bit_mismatches=weight_mismatches,installed_originals_exact=original_assets)
(work/'shape-judgment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('SHAPE_CHANNEL_CP_JUDGMENT_PASS',len(observations))
