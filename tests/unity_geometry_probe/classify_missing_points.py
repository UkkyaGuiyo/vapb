# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender CLI: CONTROL_PROJECT OUTPUT_JSON. Raw-base diagnostic, never acceptance."""
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    from io_scene_fbx import parse_fbx
    project, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    manifest = read(project / 'ControlPointManifest.json')
    report = read(project / 'UnityControlPointBridge.json')
    for file, field in [('Source.fbx', 'source_fbx_sha256'), ('Source.fbx.meta', 'source_meta_sha256'),
                        ('Noop.fbx', 'noop_fbx_sha256'), ('Stamped.fbx', 'stamped_fbx_sha256')]:
        assert hashlib.sha256((project / file).read_bytes()).hexdigest() == manifest[field] == report[field]
    assert all(report[field] for field in ('noop_equivalent', 'stamped_equivalent', 'restored_equivalent',
                                          'source_fbx_restored', 'source_meta_restored'))
    markers = {(row['mesh_guid'], row['mesh_local_id']): row for row in manifest['meshes']}
    assert len(markers) == len(manifest['meshes'])
    root, _ = parse_fbx.parse(str(project / 'Source.fbx'), use_namedtuple=True)
    objects = {node.props[0]: node for node in next(node for node in root.elems if node.id == b'Objects').elems}
    assert len(objects) == len(next(node for node in root.elems if node.id == b'Objects').elems)
    incoming = {}
    for node in next(node for node in root.elems if node.id == b'Connections').elems:
        if node.id == b'C' and node.props[0] == b'OO':
            incoming.setdefault(node.props[2], []).append(node.props[1])
    def array(node, name):
        values, = [element.props[0] for element in node.elems if element.id == name]
        return list(values)
    def norm_cross(a, b):
        return math.sqrt((a[1]*b[2]-a[2]*b[1])**2 + (a[2]*b[0]-a[0]*b[2])**2 + (a[0]*b[1]-a[1]*b[0])**2)
    def subtract(a, b):
        return tuple(x-y for x,y in zip(a,b))
    def dot(a,b):
        return sum(x*y for x,y in zip(a,b))
    def area(points):
        # Sum of unsigned fan triangle areas is only a raw-base non-collinearity
        # measurement. It does not select or claim Unity's tessellation algorithm.
        if len(points) < 3:
            return 0.0
        return sum(norm_cross(subtract(points[i],points[0]), subtract(points[i+1],points[0]))*.5
                   for i in range(1,len(points)-1))
    rows = []
    threshold = 1e-12
    for observed in report['stamped']:
        marker = markers[(observed['mesh_guid'], observed['mesh_local_id'])]
        assert observed['geometry_uid'] == marker['geometry_uid']
        geometry = objects[int(marker['geometry_uid'])]
        assert geometry.id == b'Geometry' and geometry.props[2] == b'Mesh'
        flat = array(geometry, b'Vertices'); vertices = list(zip(flat[0::3],flat[1::3],flat[2::3]))
        assert len(vertices) == marker['control_point_count']
        polygons = []; current = []
        for value in array(geometry, b'PolygonVertexIndex'):
            cp = -value-1 if value < 0 else value
            assert 0 <= cp < len(vertices)
            current.append(cp)
            if value < 0:
                polygons.append(current); current = []
        assert not current
        areas = [area([vertices[index] for index in polygon]) for polygon in polygons]
        membership = {}
        for polygon_index, polygon in enumerate(polygons):
            for cp in set(polygon):
                membership.setdefault(cp, []).append(polygon_index)
        shape_points = set(); shape_count = 0
        for blend_uid in incoming.get(int(marker['geometry_uid']), []):
            blend = objects[blend_uid]
            if blend.id != b'Deformer' or blend.props[2] != b'BlendShape':
                continue
            for channel_uid in incoming.get(blend_uid, []):
                channel = objects[channel_uid]
                if channel.id != b'Deformer' or channel.props[2] != b'BlendShapeChannel':
                    continue
                shape_count += 1
                for shape_uid in incoming.get(channel_uid, []):
                    shape = objects[shape_uid]
                    if shape.id == b'Geometry' and shape.props[2] == b'Shape':
                        shape_points.update(array(shape,b'Indexes'))
        for cp in observed['missing_control_point_indices']:
            assert 0 <= cp < len(vertices)
            owners = membership.get(cp, [])
            category = ('UNREFERENCED_RAW_CONTROL_POINT' if not owners else
                        'REFERENCED_ONLY_ZERO_AREA_OR_DEGENERATE_RAW_BASE_POLYGONS'
                        if all(areas[index] <= threshold for index in owners) else
                        'REFERENCED_BY_POSITIVE_AREA_RAW_BASE_POLYGON')
            corners = []
            for polygon_index in owners:
                polygon = polygons[polygon_index]
                for slot, value in enumerate(polygon):
                    if value != cp:
                        continue
                    previous, following = polygon[(slot-1)%len(polygon)], polygon[(slot+1)%len(polygon)]
                    before, point, after = vertices[previous], vertices[cp], vertices[following]
                    a, b = subtract(point,before), subtract(point,after)
                    cross = norm_cross(a,b)
                    corners.append(dict(polygon_index=polygon_index, polygon_corner_index=slot,
                        polygon_positive_fan_area=areas[polygon_index]>threshold,
                        equal_previous_exact=point==before, equal_next_exact=point==after,
                        previous_distance_raw_units=math.sqrt(dot(a,a)), next_distance_raw_units=math.sqrt(dot(b,b)),
                        corner_cross_norm_raw_units_squared=cross,
                        collinear_under_cross_threshold=cross<=2*threshold,
                        between_neighbors_under_dot_threshold=dot(a,b)<=1e-24,
                        neighbor_dot_raw_units_squared=dot(a,b)))
            rows.append(dict(mesh_guid=observed['mesh_guid'], mesh_local_id=observed['mesh_local_id'],
                geometry_uid=marker['geometry_uid'], control_point_index=cp, category=category,
                polygon_indices=owners, polygon_fan_areas=[areas[index] for index in owners],
                shape_channel_count=shape_count, appears_in_shape_frame_indices=cp in shape_points,
                immediate_neighbor_corroboration=corners))
    counts = {category:sum(row['category']==category for row in rows) for category in
        ('UNREFERENCED_RAW_CONTROL_POINT','REFERENCED_ONLY_ZERO_AREA_OR_DEGENERATE_RAW_BASE_POLYGONS',
         'REFERENCED_BY_POSITIVE_AREA_RAW_BASE_POLYGON')}
    result = dict(status='RAW_BASE_DIAGNOSTIC_NO_CONTRACT_CHANGE', source_fbx_sha256=manifest['source_fbx_sha256'],
        source_meta_sha256=manifest['source_meta_sha256'], area_threshold_raw_units_squared=threshold,
        area_measure='UNSIGNED_FAN_TRIANGLE_SUM_NOT_A_TESSELLATION_IDENTITY',
        corner_cross_threshold_raw_units_squared=2*threshold, between_dot_threshold_raw_units_squared=1e-24,
        limitation='RAW_BASE_POSITIONS_ONLY_NOT_ALL_SHAPE_OR_SKIN_DEFORMATIONS', counts=counts, rows=rows)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('MISSING_CONTROL_POINT_CLASSES '+json.dumps(counts))


if __name__ == '__main__':
    main()
