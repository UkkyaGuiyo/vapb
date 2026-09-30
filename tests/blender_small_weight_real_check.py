# SPDX-License-Identifier: GPL-3.0-or-later
"""Read existing bounded D1 artifacts; emit only aggregate raw/native weight proof."""
import hashlib
import json
from pathlib import Path
import sys


def raw_skin_weights(folder, filename='D1.fbx'):
    from io_scene_fbx import parse_fbx
    path=folder/filename;root,_=parse_fbx.parse(str(path),use_namedtuple=True)
    nodes={n.props[0]:n for n in next(n for n in root.elems if n.id==b'Objects').elems}
    edges={}
    for row in next(n for n in root.elems if n.id==b'Connections').elems:
        if row.props[0]==b'OO':edges.setdefault(row.props[2],[]).append(row.props[1])
    geom,=[n for n in nodes.values() if n.id==b'Geometry' and n.props[2]==b'Mesh']
    marker=json.loads((folder/'ControlPointManifest.json').read_text())['meshes'][0]['uv_channel']
    uv,=[n for n in geom.elems if n.id==b'LayerElementUV' and n.props[0]==marker]
    values=next(n.props[0] for n in uv.elems if n.id==b'UV')
    method=next(n.props[0] for n in uv.elems if n.id==b'MappingInformationType')
    reference=next(n.props[0] for n in uv.elems if n.id==b'ReferenceInformationType')
    uv_indices=next((n.props[0] for n in uv.elems if n.id==b'UVIndex'),None)
    cp_map={}
    indices=next(n.props[0] for n in geom.elems if n.id==b'PolygonVertexIndex')
    for loop,index in enumerate(indices):
        cp=index if index>=0 else -index-1
        slot=cp if method==b'ByVertice' else loop
        if method not in (b'ByVertice',b'ByPolygonVertex'):raise ValueError('UV_MAPPING_UNPROVEN')
        if reference==b'IndexToDirect':slot=uv_indices[slot]
        elif reference!=b'Direct':raise ValueError('UV_REFERENCE_UNPROVEN')
        label=int(round(values[slot*2]))-1
        if abs(values[slot*2]-(label+1))>1e-5 or abs(values[slot*2+1]-.375)>1e-5:raise ValueError('CP_MARKER_INVALID')
        if cp in cp_map and cp_map[cp]!=label:raise ValueError('CP_MARKER_CONFLICT')
        cp_map[cp]=label
    skin,=[nodes[u] for u in edges[geom.props[0]] if nodes[u].id==b'Deformer' and nodes[u].props[2]==b'Skin']
    raw={}
    for uid in edges[skin.props[0]]:
        cluster=nodes[uid]
        if cluster.props[2]!=b'Cluster':continue
        model,=[nodes[u] for u in edges[uid] if nodes[u].id==b'Model']
        # These are explicit temporary labels assigned to actual Bone handles by
        # the existing diagnostic, never original Bone names as identity.
        label=model.props[1].split(b'\x00')[0].decode()
        if not label.startswith('VAPB-EXP-BONE-'):raise ValueError('EXPLICIT_BONE_LABEL_MISSING')
        ids=next((n.props[0] for n in cluster.elems if n.id==b'Indexes'),[])
        weights=next((n.props[0] for n in cluster.elems if n.id==b'Weights'),[])
        if len(ids)!=len(weights):raise ValueError('CLUSTER_ARRAY_MISMATCH')
        for cp,w in zip(ids,weights):
            if cp not in cp_map:raise ValueError('RAW_CP_UNPROVEN')
            if (cp_map[cp],label) in raw:raise ValueError('DUPLICATE_RAW_BONE_CLAIM')
            raw[(cp_map[cp],label)]=float(w)
    return raw


def main():
    folder, output = map(Path,sys.argv[sys.argv.index('--')+1:])
    path=folder/'D1.fbx';raw=raw_skin_weights(folder)
    result=[]
    for name in ['BeforePolicy','D1','RepeatedPolicy']:
        capture=json.loads((folder/(name+'.json')).read_text())
        assert capture['input_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        observed,=capture['meshes']; bones={b['index']:b['export_label'] for b in observed['bones']}
        actual={(v['vertex'],bones[v['bone']]):v['weight'] for v in observed['bone_weights']}
        missing=0;max_error=0;checked=0
        for vertex,cp in enumerate(observed['vertex_control_point_indices']):
            for label in bones.values():
                expected=raw.get((cp,label),0);weight=actual.get((vertex,label),0)
                missing+=int(expected>0 and weight==0);max_error=max(max_error,abs(expected-weight));checked+=1
        result.append(dict(label=name,checked=checked,missing_positive=missing,max_raw_native_error=max_error,
                           below_threshold_native=sum(0<w<.001 for w in actual.values())))
    output.write_text(json.dumps(dict(rows=result),indent=2));print(json.dumps(result))


if __name__=='__main__':main()
