"""Independent written-FBX semantic checks and exact UV/corner joins. No prediction input."""
import argparse
import array
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode = True
UIDS = [943593828, 504963197, 123443898]
GUID = 'abcdefabcdefabcdefabcdefabcdefab'
FILE_ID = '3538053534738119282'


def child(node, name):
    rows = [n for n in node.elems if n.id == name]
    if len(rows) != 1:
        raise ValueError(('unique child required', name))
    return rows[0]


def value(node, name):
    return child(node, name).props[0]


def canonical(node, omit=(), path=()):
    path += (node.id,)
    if len(path) == 2 and node.id in {b'FileId', b'CreationTime'}:
        return None
    if path in omit:
        return (node.id, bytes(node.props_type), 'DECLARED_CHANGED_VALUES')
    properties = []
    for kind, item in zip(node.props_type, node.props):
        if isinstance(item, array.array):
            item = item.tobytes()
        elif kind in (ord('F'), ord('D')):
            item = struct.pack('<f' if kind == ord('F') else '<d', item)
        properties.append((kind, item))
    return (node.id, tuple(properties), tuple(c for n in node.elems if (c := canonical(n, omit, path)) is not None))


def jsonable(item):
    if isinstance(item, bytes):
        return {'bytes_hex': item.hex()}
    if isinstance(item, array.array):
        return {'array_type': item.typecode, 'values': list(item)}
    if hasattr(item, 'props_type'):
        return dict(id=item.id.decode(), props_type=bytes(item.props_type).decode(),
                    props=[jsonable(x) for x in item.props], elems=[jsonable(x) for x in item.elems])
    return item


def decode(root):
    objects = child(root, b'Objects')
    nodes = {n.props[0]: n for n in objects.elems}
    if len(nodes) != len(objects.elems):
        raise ValueError('duplicate object UID')
    g = nodes[329684292]
    if g.id != b'Geometry' or g.props[2] != b'Mesh' or nodes[208084244].id != b'Model':
        raise ValueError('pinned model/geometry unavailable')
    links = [n for n in child(root, b'Connections').elems if n.id == b'C' and n.props[0] == b'OO' and n.props[2] == 208084244 and n.props[1] in nodes and nodes[n.props[1]].id == b'Material']
    slots = [n.props[1] for n in links]
    if len(slots) != 3 or set(slots) != set(UIDS):
        raise ValueError('three unique pinned material links required')
    if not any(n.props == [b'OO', 329684292, 208084244] for n in child(root, b'Connections').elems):
        raise ValueError('geometry-model link missing')
    pvi = list(value(g, b'PolygonVertexIndex'))
    if len(pvi) != 36 or any((x < 0) != (i % 3 == 2) for i, x in enumerate(pvi)):
        raise ValueError('twelve triangles required')
    cps = [-x-1 if x < 0 else x for x in pvi]
    positions = list(value(g, b'Vertices'))
    uv_layer, normals = child(g, b'LayerElementUV'), child(g, b'LayerElementNormal')
    for layer in [uv_layer, normals]:
        if value(layer, b'MappingInformationType') != b'ByPolygonVertex' or value(layer, b'ReferenceInformationType') != b'IndexToDirect':
            raise ValueError('unsupported corner layer')
    ml = child(g, b'LayerElementMaterial')
    if value(ml, b'MappingInformationType') != b'ByPolygon' or value(ml, b'ReferenceInformationType') != b'IndexToDirect':
        raise ValueError('unsupported material layer')
    uv, uv_index = list(value(uv_layer, b'UV')), list(value(uv_layer, b'UVIndex'))
    ns, ni = list(value(normals, b'Normals')), list(value(normals, b'NormalsIndex'))
    material = list(value(ml, b'Materials'))
    if len(uv_index) != 36 or len(ni) != 36 or len(material) != 12 or len(positions) != 24:
        raise ValueError('pinned stream dimensions changed')
    def lookup(values, index, width):
        if type(index) is not int or index < 0 or (index+1)*width > len(values):
            raise ValueError('invalid stream index')
        return tuple(values[index*width:(index+1)*width])
    rows = []
    for face in range(12):
        indices = list(range(3*face, 3*face+3))
        slot = material[face]
        if not 0 <= slot < 3:
            raise ValueError('material index out of range')
        rows.append(dict(uv=[lookup(uv, uv_index[i], 2) for i in indices],
                         corners=[lookup(positions, cps[i], 3) for i in indices],
                         normals=[lookup(ns, ni[i], 3) for i in indices], cps=[cps[i] for i in indices],
                         slot=slot, uid=slots[slot]))
    # Edges address polygon loops, not CPs. Preserve the same ordered edge endpoints.
    edges = []
    for i in value(g, b'Edges'):
        if not 0 <= i < 36:
            raise ValueError('invalid edge loop address')
        nxt = i//3*3 + (i+1)%3
        edges.append((cps[i], cps[nxt]))
    join(rows, rows)  # reject UV face/corner ambiguity even before native data exists
    return rows, slots, edges


def key(row):
    return tuple(sorted(tuple(x) for x in row['uv']))


def join(source, target):
    sk, tk = [key(x) for x in source], [key(x) for x in target]
    if len(set(sk)) != len(sk) or len(set(tk)) != len(tk):
        raise ValueError('DUPLICATE_FACE_SIGNATURE')
    if Counter(sk) != Counter(tk):
        raise ValueError('FACE_MULTISET_MISMATCH')
    lookup = dict(zip(tk, target))
    pairs = []
    for a in source:
        b = lookup[key(a)]
        auv, buv = [tuple(x) for x in a['uv']], [tuple(x) for x in b['uv']]
        if len(set(auv)) != 3 or len(set(buv)) != 3:
            raise ValueError('AMBIGUOUS_CORNER')
        permutation = [buv.index(x) for x in auv]
        orientation = 1 if permutation in [[0,1,2], [1,2,0], [2,0,1]] else -1
        pairs.append((a, b, permutation, orientation))
    return pairs


def native_rows(snapshot):
    uv = [(x['x'], x['y']) for x in snapshot['source_uv0']]
    pos = [(x['x'], x['y'], x['z']) for x in snapshot['source_local_vertices']]
    ns = [(x['x'], x['y'], x['z']) for x in snapshot['source_local_normals']]
    rows = []
    for slot, group in enumerate(snapshot['source_submeshes']):
        ids = group['indices']
        if len(ids) % 3:
            raise ValueError('native nontriangle group')
        for i in range(0, len(ids), 3):
            tri = ids[i:i+3]
            if any(type(v) is not int or v < 0 or v >= len(pos) for v in tri):
                raise ValueError('invalid native vertex index')
            rows.append(dict(slot=slot, uv=[uv[v] for v in tri], corners=[pos[v] for v in tri], normals=[ns[v] for v in tri]))
    return rows


def observations(source, target):
    pairs = join(source, target)
    slots = sorted({b['slot'] for _, b, _, _ in pairs})
    groups = {str(slot): dict(Counter(str(a['uid']) for a, b, _, _ in pairs if b['slot'] == slot)) for slot in slots}
    return dict(groups=groups, orientations=dict(Counter(o for _, _, _, o in pairs)),
                corners=[dict(uv_key=key(a), target_slot=b['slot'], raw_material_uid=a['uid'], permutation=p, orientation=o) for a,b,p,o in pairs])


def controls(raw, target):
    result = {}
    for name, change in [('duplicate_face', lambda x: x+[copy.deepcopy(x[0])]), ('missing_face', lambda x: x[:-1]),
                         ('duplicate_corner', lambda x: x[0]['uv'].__setitem__(1,x[0]['uv'][0]) or x)]:
        try:
            join(raw, change(copy.deepcopy(target)))
            result[name] = False
        except ValueError:
            result[name] = True
    reversed_rows = copy.deepcopy(target)
    for row in reversed_rows:
        row['uv'].reverse(); row['corners'].reverse(); row['normals'].reverse()
    result['winding_reversal_changes_orientation'] = all(a[3] == -b[3] for a,b in zip(join(raw,target),join(raw,reversed_rows)))
    permuted = copy.deepcopy(target)
    for row in permuted:
        row['slot'] = (row['slot']+1)%3
    result['target_slot_permutation_changes_observed_groups'] = observations(raw,target)['groups'] != observations(raw,permuted)['groups']
    result['target_slot_permutation_preserves_uv_corner_join'] = [x[2:] for x in join(raw,target)] == [x[2:] for x in join(raw,permuted)]
    if not all(result.values()):
        raise ValueError('judge control failed')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--addon', type=Path, required=True)
    ap.add_argument('--cases', type=Path, required=True)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--blender', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('occupied report')
    spec = importlib.util.spec_from_file_location('judge_existing_parser_loader', args.repo/'tests/evidence/inbound-material-face-membership-20261007/verify_inbound_frame.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    parser = helper.load_parser(args.addon)
    if helper.sha256(args.cases/'original.fbx') != helper.PIN_FBX or helper.sha256(args.cases/'original.fbx.meta') != helper.PIN_META:
        raise ValueError('original revision changed')
    baseline, version = parser.parse(str(args.cases/'original.fbx'), use_namedtuple=True)
    original, original_slots, original_edges = decode(baseline)
    if original_slots != UIDS:
        raise ValueError('original material connections changed')
    report = dict(scope='pinned self-authored twelve unique-UV triangles only; no product mapping',
                  original_fbx_sha256=helper.PIN_FBX, meta_sha256=helper.PIN_META, fbx_version=version, cases={})
    geometry_path = (b'',b'Objects',b'Geometry')
    for case in ['R','A','B']:
        root, actual_version = parser.parse(str(args.cases/(case+'.fbx')), use_namedtuple=True)
        raw, slots, edges = decode(root)
        if actual_version != version or edges != original_edges:
            raise ValueError('version or semantic edge changes')
        pairs = join(original, raw)
        if any(a['uid'] != b['uid'] or a['cps'] != b['cps'] or a['corners'] != b['corners'] or a['normals'] != b['normals'] or a['uv'] != b['uv'] for a,b,_,_ in pairs):
            raise ValueError('face semantic meaning changed')
        omit = []
        if case == 'A':
            omit = [geometry_path+(b'PolygonVertexIndex',), geometry_path+(b'Edges',),
                    geometry_path+(b'LayerElementUV',b'UVIndex'), geometry_path+(b'LayerElementNormal',b'NormalsIndex'),
                    geometry_path+(b'LayerElementMaterial',b'Materials')]
            if slots != UIDS or [r['uid'] for r in raw] != [UIDS[1]]*4+[UIDS[0]]*2+[UIDS[2]]*6:
                raise ValueError('A declared order mismatch')
        if case == 'B':
            omit = [geometry_path+(b'LayerElementMaterial',b'Materials'), (b'',b'Connections')]
            if slots != [UIDS[2],UIDS[0],UIDS[1]] or raw != [{**a,'slot': slots.index(a['uid'])} for a in original]:
                raise ValueError('B declared connection order mismatch')
            def unrelated(tree):
                return [canonical(n) for n in child(tree,b'Connections').elems if not (n.id == b'C' and n.props[0] == b'OO' and n.props[2] == 208084244 and n.props[1] in UIDS)]
            if unrelated(root) != unrelated(baseline):
                raise ValueError('unrelated connection changes')
        if canonical(root,omit) != canonical(baseline,omit):
            raise ValueError('undeclared FBX semantic changes')
        item = dict(fbx_sha256=helper.sha256(args.cases/(case+'.fbx')), raw_material_connections=slots,
                    raw_faces=raw, written_semantics_checked=True,
                    geometry=jsonable(next(n for n in child(root,b'Objects').elems if n.props[0] == 329684292)),
                    connections=jsonable(child(root,b'Connections')), global_settings=jsonable(child(root,b'GlobalSettings')))
        if args.native:
            old_context=json.loads((args.repo/'tests/evidence/inbound-material-face-membership-20261007/current-context-20261011/unity-context.json').read_text())
            old=json.loads((args.repo/'tests/evidence/inbound-material-face-membership-20261007/current-context-20261011/unity-coordinate.json').read_text())
            context=json.loads((args.native/(case+'-context.json')).read_text(encoding='utf-8-sig'))
            snapshot=json.loads((args.native/(case+'-coordinate.json')).read_text(encoding='utf-8-sig'))
            if not snapshot['pass'] or context.get('error') or not context['same_model_mesh'] or not context['get_triangles_matches_mesh_data']:
                raise ValueError('native capture failed')
            if context['fbx_sha'] != item['fbx_sha256'] or context['meta_sha'] != helper.PIN_META or context['unity_version'] != '2022.3.22f1':
                raise ValueError('native revision mismatch')
            if snapshot['unity_version'] != context['unity_version']:
                raise ValueError('snapshot/context version differs')
            for field in ['weld_vertices','optimize_vertices','optimize_polygons','compression','index_format','import_normals','import_tangents']:
                if context[field] != old_context[field]:
                    raise ValueError('effective importer policy changed: '+field)
            if context['external_remaps'] != [] or old_context['external_remaps'] != 0:
                raise ValueError('effective remap policy changed')
            for field in ['importer_file_scale','importer_global_scale','importer_use_file_scale','importer_bake_axis_conversion']:
                if snapshot[field] != old[field]:
                    raise ValueError('effective scale/axis policy changed: '+field)
            for field in ['prefab_sha','prefab_meta_sha','renderer_guid','renderer_file_id','materials']:
                if context[field] != old_context[field]:
                    raise ValueError('receiver control changed: '+field)
            if context['mesh'] != dict(guid=GUID,file_id=FILE_ID) or snapshot['source_asset_guid'] != GUID or snapshot['mesh_file_id'] != FILE_ID:
                raise ValueError('native mesh identity mismatch')
            for field in ['fbx_sha256_before','fbx_sha256_after','source_sha256']:
                if snapshot[field] != item['fbx_sha256']:
                    raise ValueError('native FBX binding mismatch')
            for field in ['meta_sha256_before','meta_sha256_after']:
                if snapshot[field] != helper.PIN_META:
                    raise ValueError('native meta binding mismatch')
            native=native_rows(snapshot)
            item.update(native_context=context, raw_to_unity=observations(raw,native), judge_controls=controls(raw,native))
            ru=join(raw,native)
            item['declared_raw_to_unity_C']='0.01 * reflectX; numeric residual diagnostic only'
            item['raw_to_unity_local_position_max_abs_difference']=max(abs(a['corners'][i][axis]*(-.01 if axis==0 else .01)-b['corners'][p[i]][axis]) for a,b,p,o in ru for i in range(3) for axis in range(3))
            if case == 'R':
                if old['source_sha256'] != helper.PIN_FBX or old['meta_sha256_before'] != helper.PIN_META:
                    raise ValueError('baseline native binding missing')
                item['noop_same_face_to_native_submesh']=observations(original,native_rows(old))['groups']==item['raw_to_unity']['groups'] and all(a['slot']==b['slot'] for a,b,_,_ in join(native_rows(old),native))
                if not item['noop_same_face_to_native_submesh']:
                    raise ValueError('NOOP_NATIVE_CHANGED: do not interpret A/B')
            if args.blender:
                capture=json.loads((args.blender/(case+'-blender.json')).read_text(encoding='utf-8-sig'))
                if capture['fbx_sha256'] != item['fbx_sha256'] or capture['meta_sha256'] != helper.PIN_META or not capture['mesh_unchanged'] or capture['operator_result'] != ['CANCELLED']:
                    raise ValueError('Blender binding/nonmutation failure')
                blender=capture['faces']
                item.update(raw_to_blender=observations(raw,blender), blender_to_unity=dict(orientations=dict(Counter(o for _,_,_,o in join(blender,native)))),blender_receipt=capture['receipt'],blender_version=capture['blender_version'])
                item['raw_to_blender_local_position_max_abs_difference']=max(abs(a['corners'][i][axis]-b['corners'][p[i]][axis]) for a,b,p,o in join(raw,blender) for i in range(3) for axis in range(3))
        report['cases'][case]=item
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2)
    print('Independent written semantics checked' + ('; native exact-UV observations captured' if args.native else ''))


if __name__ == '__main__':
    main()
