"""Freeze actual written bytes and input-only predictions before Unity capture."""
import argparse
import hashlib
import json
from pathlib import Path
from read_input import decode, parse
from diagnose import diagnose

ap = argparse.ArgumentParser()
for name in ('repo', 'addon', 'work'):
    ap.add_argument('--'+name, type=Path, required=True)
args = ap.parse_args()
fbx = args.work / 'MixedFour.fbx'
root, version = parse(fbx, args.repo, args.addon)
raw = decode(root)
polygons = raw['polygons']
if len(polygons) != 4 or len(raw['material_connections']) != 2:
    raise ValueError('four polygons and two actual Material connections required')
# Independently recover authored polygon identity from the exact UV fingerprint.
by_authored = {}
for p in polygons:
    label = min(u[0] for u in p['uv']) * 4
    if int(label) != label or label not in (0, 1, 2, 3) or int(label) in by_authored:
        raise ValueError('invalid or duplicate UV polygon fingerprint')
    by_authored[int(label)] = p
if [len(by_authored[i]['uv']) for i in range(4)] != [3, 4, 4, 3]:
    raise ValueError('written FBX did not retain intended triangles/quads')
if by_authored[0]['uid'] != by_authored[2]['uid'] or by_authored[1]['uid'] != by_authored[3]['uid'] or by_authored[0]['uid'] == by_authored[1]['uid']:
    raise ValueError('written Material assignment differs')
corners = [tuple(u) for p in polygons for u in p['uv']]
if len(set(corners)) != 14:
    raise ValueError('UV corners are not globally unique')
strings = []
def scan(node):
    for prop in node.props:
        if isinstance(prop, bytes):
            strings.append(prop)
    for c in node.elems: scan(c)
scan(root)
if any(b'users\\' in s.lower() or b'users/' in s.lower() for s in strings):
    raise ValueError('private path in FBX strings; do not publish')
base = args.repo / 'tests/evidence/holmes-material-correspondence-20261011/cases/original.fbx.meta'
meta = base.read_bytes().replace(b'abcdefabcdefabcdefabcdefabcdefab', b'ce412039a7b14c91af5e832bbcdec041')
with (args.work / 'MixedFour.fbx.meta').open('xb') as stream:
    stream.write(meta)
record = dict(instruction_id='HOLMES-20261011', instruction_commit='94c1f11fb1fac73aadafd6de2d41a3297c0322f1',
              fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(), initial_meta_sha256=hashlib.sha256(meta).hexdigest(),
              fbx_version=version, raw=raw, authored_polygon_to_raw={str(k): v['polygon'] for k, v in by_authored.items()},
              source_only_OFF=diagnose(raw, {'keepQuads': 0}), source_only_ON=diagnose(raw, {'keepQuads': 1}),
              P_UID='two groups by first-used Material UID; no native index or diagonal prediction',
              P_UID_TOPOLOGY='ON may partition a UID into triangle/quad groups; group order UNDETERMINED',
              prediction_frozen_before_native=True)
with (args.work / 'input-and-predictions.json').open('x', encoding='utf8') as stream:
    json.dump(record, stream, indent=2)
print(json.dumps({'fbx_sha256': record['fbx_sha256'], 'raw_order': [(p['polygon'], len(p['uv']), p['uid']) for p in polygons],
                  'P_UID_group_count': len(record['source_only_OFF']['P_UID'])}))
