# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded candidate fixes against independently transported CP triangles.

Blender CLI: CONTROL_PROJECT NEW_OUTPUT_JSON. No production changes.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def main():
    from io_scene_fbx import parse_fbx
    from mathutils import Vector, geometry
    import bmesh
    import bpy
    project, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
    assert not output.exists()
    read = lambda name: json.loads((project / name).read_text(encoding='utf-8-sig'))
    manifest, oracle = read('ControlPointManifest.json'), read('UnityControlPointBridge.json')
    for name, field in (('Source.fbx','source_fbx_sha256'), ('Source.fbx.meta','source_meta_sha256'),
                        ('Noop.fbx','noop_fbx_sha256'), ('Stamped.fbx','stamped_fbx_sha256')):
        assert hashlib.sha256((project/name).read_bytes()).hexdigest() == manifest[field] == oracle[field]
    assert oracle['error'] == 'NONE' and all(oracle[k] for k in ('noop_equivalent',
        'stamped_equivalent','restored_equivalent','source_fbx_restored','source_meta_restored'))
    root, _ = parse_fbx.parse(str(project/'Source.fbx'), use_namedtuple=True)
    nodes = {n.props[0]:n for n in next(n for n in root.elems if n.id == b'Objects').elems}
    observed = {(r['mesh_guid'],r['mesh_local_id']):r for r in oracle['stamped']}
    results = []
    def canonical(tris):
        return Counter(tuple(sorted(t)) for t in tris)
    for spec in manifest['meshes']:
        row = observed[(spec['mesh_guid'],spec['mesh_local_id'])]
        assert row.get('observed_vertex_map_valid', row['marker_valid']) and row.get(
            'negative_observed_set_removal_rejected', row['negative_duplicate_rejected']) and row['negative_out_of_range_rejected']
        node = nodes[int(spec['geometry_uid'])]
        flat = next(n.props[0] for n in node.elems if n.id == b'Vertices')
        points = [Vector(flat[i:i+3]) for i in range(0,len(flat),3)]
        loops, current = [], []
        for value in next(n.props[0] for n in node.elems if n.id == b'PolygonVertexIndex'):
            current.append(-value-1 if value < 0 else value)
            if value < 0:
                loops.append(current); current = []
        assert not current
        # Candidate normalization, tested rather than presumed equivalent:
        # keep the first exactly coincident adjacent corner; preserve triangles,
        # including base-degenerate triangles that Shapes can later open.
        cleaned = []
        for loop in loops:
            ring = []
            for cp in loop:
                if not ring or points[ring[-1]] != points[cp]: ring.append(cp)
            if len(ring)>1 and points[ring[-1]] == points[ring[0]]: ring.pop()
            cleaned.append(ring)
        candidates = {'FIRST_FAN':[], 'BLENDER_FIXED_EAR_CLIP':[], 'CDT_FIRST_NONCOLLINEAR':[]}
        errors = {}
        for ring in cleaned:
            if len(ring)<3: continue
            for name in candidates:
                if name in errors: continue
                try:
                    if len(ring)==3: tris=[ring]
                    elif name=='FIRST_FAN': tris=[[ring[0],ring[i],ring[i+1]] for i in range(1,len(ring)-1)]
                    elif name=='BLENDER_FIXED_EAR_CLIP':
                        mesh=bpy.data.meshes.new('TemporaryCandidate')
                        mesh.from_pydata([points[cp] for cp in ring],[],[list(range(len(ring)))])
                        labels=mesh.attributes.new('source_cp','INT','POINT')
                        labels.data.foreach_set('value',ring)
                        bm=bmesh.new()
                        try:
                            bm.from_mesh(mesh)
                            layer=bm.verts.layers.int['source_cp']
                            bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='EAR_CLIP')
                            tris=[[v[layer] for v in face.verts] for face in bm.faces]
                            assert all(len(t)==3 and all(cp in ring for cp in t) for t in tris), 'CP_PROVENANCE_UNAVAILABLE'
                        finally:
                            bm.free(); bpy.data.meshes.remove(mesh)
                    else:
                        origin=points[ring[0]]; normal=None
                        for i in range(1,len(ring)-1):
                            cross=(points[ring[i]]-origin).cross(points[ring[i+1]]-origin)
                            if cross.length_squared>0: normal=cross.normalized(); break
                        assert normal is not None, 'PROJECTION_UNAVAILABLE'
                        tangent=(points[ring[1]]-origin).normalized(); second=normal.cross(tangent)
                        projected=[Vector(((points[cp]-origin).dot(tangent),(points[cp]-origin).dot(second))) for cp in ring]
                        _,_,faces,origins,_,face_origins=geometry.delaunay_2d_cdt(projected,[],[list(range(len(ring)))],1,1e-10,True)
                        assert all(len(origins[v])==1 for tri in faces for v in tri), 'CP_PROVENANCE_UNAVAILABLE'
                        assert all(len(tri)==3 and origin_ids==[0] for tri,origin_ids in zip(faces,face_origins)), 'FACE_PROVENANCE_UNAVAILABLE'
                        tris=[[ring[origins[v][0]] for v in tri] for tri in faces]
                    candidates[name].extend(tris)
                except (ValueError,AssertionError,KeyError) as exc:
                    errors[name]=str(exc)
        indices=row['triangle_control_point_indices']
        wanted=canonical([indices[i:i+3] for i in range(0,len(indices),3)])
        results.append(dict(geometry_uid=spec['geometry_uid'], candidates={name:
            dict(status='UNPROVEN' if name in errors else 'EXACT' if canonical(tris)==wanted else 'MISMATCH',
                 error=errors.get(name,'NONE'), triangle_count=len(tris)) for name,tris in candidates.items()}))
    aggregate={name:dict(Counter(r['candidates'][name]['status'] for r in results)) for name in candidates}
    output.write_text(json.dumps(dict(status='OBSERVED_CANDIDATES_NOT_PRODUCTION_FIX',
        source_fbx_sha256=manifest['source_fbx_sha256'], candidates=aggregate, meshes=results),indent=2))
    print('TESSELLATION_CANDIDATES '+json.dumps(aggregate))


if __name__=='__main__': main()
