"""Exact diagnostic CP topology comparison, independent of geometry proximity."""
from collections import Counter
import json
from pathlib import Path
import sys


def triangles(rows, count):
    if any(len(row) != 3 or any(type(v) is not int or not 0 <= v < count for v in row) for row in rows):
        raise ValueError('CONTROL_POINT_TRIANGLE_INVALID')
    return Counter(tuple(sorted(row)) for row in rows)


def compare_points(unity, native, manifest):
    flags = ('noop_equivalent', 'stamped_equivalent', 'restored_equivalent',
             'source_fbx_restored', 'source_meta_restored')
    if unity['error'] != 'NONE' or not all(unity.get(k) is True for k in flags):
        raise ValueError('UNITY_CONTROL_UNPROVEN')
    if native['status'] != 'PASS' or native.get('original_noop_stamped_restored_equal') is not True:
        raise ValueError('NATIVE_CONTROL_UNPROVEN')
    for key in ('source_fbx_sha256', 'source_meta_sha256', 'noop_fbx_sha256', 'stamped_fbx_sha256'):
        if unity.get(key) != manifest[key]:
            raise ValueError('SOURCE_REVISION_MISMATCH')
    for key in ('source_fbx_sha256', 'source_meta_sha256', 'noop_fbx_sha256', 'stamped_fbx_sha256'):
        if native[key] != manifest[key]:
            raise ValueError('SOURCE_REVISION_MISMATCH')
    expected = {(r['mesh_guid'], r['mesh_local_id']): r for r in manifest['meshes']}
    observed = {(r['mesh_guid'], r['mesh_local_id']): r for r in unity['stamped']}
    realized = {r['geometry_uid']: r for r in native['meshes']}
    if (len(expected) != len(manifest['meshes']) or len(observed) != len(unity['stamped'])
            or len(realized) != len(native['meshes']) or set(expected) != set(observed)
            or {r['geometry_uid'] for r in expected.values()} != set(realized)):
        raise ValueError('MESH_COVERAGE_UNPROVEN')
    results = []
    for identity, spec in expected.items():
        oracle = observed[identity]
        if oracle['geometry_uid'] != spec['geometry_uid']:
            raise ValueError('CONTROL_POINT_IDENTITY_UNPROVEN')
        observed_contract = 'observed_vertex_map_valid' in oracle
        mapping_valid = (oracle.get('observed_vertex_map_valid') is True
            and oracle.get('negative_observed_set_removal_rejected') is True
            if observed_contract else oracle.get('marker_valid') is True
            and oracle.get('negative_duplicate_rejected') is True)
        if not mapping_valid or oracle.get('negative_out_of_range_rejected') is not True:
            results.append(dict(mesh_guid=identity[0], mesh_local_id=identity[1],
                geometry_uid=spec['geometry_uid'], category='CONTROL_POINT_IDENTITY_UNPROVEN'))
            continue  # Retain this Mesh as RED; never skip its acceptance check.
        points = oracle['triangle_control_point_indices']
        if len(points) % 3:
            raise ValueError('CONTROL_POINT_TRIANGLE_INVALID')
        unity_triangles = [points[i:i+3] for i in range(0, len(points), 3)]
        member = realized[spec['geometry_uid']]
        actual = triangles(member['triangle_control_points'], spec['control_point_count'])
        wanted = triangles(unity_triangles, spec['control_point_count'])
        differences = (actual - wanted) + (wanted - actual)
        polygons = [set(p) for p in member['polygon_control_points']]
        assigned, unknown = set(), 0
        for tri, multiplicity in differences.items():
            owners = [i for i, p in enumerate(polygons) if set(tri) <= p]
            if len(owners) == 1:
                assigned.add(owners[0])
            else:
                unknown += multiplicity
        results.append(dict(mesh_guid=identity[0], mesh_local_id=identity[1],
            geometry_uid=spec['geometry_uid'], category='EXACT' if actual == wanted else 'TOPOLOGY_MISMATCH',
            raw_source_cp_complete=oracle.get('raw_source_cp_complete', oracle['marker_valid']),
            omitted_raw_control_points=len(oracle.get('missing_control_point_indices', [])),
            unity_triangle_count=sum(wanted.values()), native_triangle_count=sum(actual.values()),
            differing_triangle_occurrences=sum(differences.values()),
            affected_polygon_indices=sorted(assigned), unattributed_triangle_occurrences=unknown))
    return dict(status='GREEN' if all(r['category'] == 'EXACT' for r in results) else 'RED',
                scope='OBSERVED_UNITY_TRIANGLE_CP_CONNECTIVITY_NOT_RAW_CP_BIJECTION_OR_SURFACE_EQUALITY',
                strict_source_cp_control_pass=unity['pass'],
                counts=dict(Counter(r['category'] for r in results)), meshes=results)


if __name__ == '__main__':
    unity, native, manifest, output = map(Path, sys.argv[1:])
    result = compare_points(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in (unity, native, manifest)))
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('status', 'counts')}))
    sys.exit(0 if result['status'] == 'GREEN' else 1)
