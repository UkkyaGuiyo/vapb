# SPDX-License-Identifier: GPL-3.0-or-later
"""Observe diagnostic CP labels, never inject Unity topology into production.

Blender CLI: EXTERNAL_CONTROL_PROJECT NEW_OUTPUT_JSON.
Original/no-op/stamped/restored native arrays must remain identical.
"""
import hashlib
import inspect
import json
import math
from pathlib import Path
import struct
import sys


def decode_marker(x, y, count):
    if (not math.isfinite(x) or not math.isfinite(y) or x != int(x)
            or not 1 <= x <= count or y != .375):
        raise ValueError('CONTROL_POINT_MARKER_INVALID')
    return int(x) - 1


def signature(values):
    return hashlib.sha256(b''.join(struct.pack('<f', v) for v in values)).hexdigest()


def main():
    import bpy
    from io_scene_fbx import import_fbx
    folder, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
    assert not output.exists()
    manifest = json.loads((folder / 'ControlPointManifest.json').read_text())
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(folder / 'Source.fbx') == manifest['source_fbx_sha256']
    assert digest(folder / 'Source.fbx.meta') == manifest['source_meta_sha256']
    assert digest(folder / 'Noop.fbx') == manifest['noop_fbx_sha256']
    assert digest(folder / 'Stamped.fbx') == manifest['stamped_fbx_sha256']
    expected = {int(row['geometry_uid']): row for row in manifest['meshes']}
    assert len(expected) == len(manifest['meshes'])
    original_hook = import_fbx.blen_read_geom
    assert tuple(inspect.signature(original_hook).parameters) == ('fbx_tmpl', 'fbx_obj', 'settings')

    def observe(filename, stamped=False):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        captured = {}

        def capture(*args):
            mesh = original_hook(*args)
            uid = args[1].props[0]
            assert uid not in captured
            captured[uid] = mesh
            return mesh

        try:
            import_fbx.blen_read_geom = capture
            assert bpy.ops.import_scene.fbx(filepath=str(folder / filename)) == {'FINISHED'}
        finally:
            import_fbx.blen_read_geom = original_hook
        rows = {}
        for uid, spec in expected.items():
            mesh = captured[uid]
            if not stamped:
                assert spec['uv_channel'] >= len(mesh.uv_layers), 'NATIVE_SPARE_UV_OCCUPIED'
            mesh.calc_loop_triangles()
            triangles = [list(t.vertices) for t in mesh.loop_triangles]
            polygons = [list(p.vertices) for p in mesh.polygons]
            keys = list(mesh.shape_keys.key_blocks) if mesh.shape_keys else []
            row = dict(geometry_uid=str(uid), vertex_count=len(mesh.vertices),
                position_sha256=signature(c for v in mesh.vertices for c in v.co),
                triangles=triangles, polygons=polygons,
                existing_uv_signatures=[signature(c for loop in layer.data for c in loop.uv)
                    for index, layer in enumerate(mesh.uv_layers) if index != spec['uv_channel']],
                shapes=[dict(value=k.value, coordinates_sha256=signature(c for v in k.data for c in v.co)) for k in keys])
            if stamped:
                layer = mesh.uv_layers[spec['uv_channel']]
                point_by_vertex = {}
                for loop in mesh.loops:
                    uv = layer.data[loop.index].uv
                    point = decode_marker(uv.x, uv.y, spec['control_point_count'])
                    old = point_by_vertex.setdefault(loop.vertex_index, point)
                    assert old == point, 'CONTROL_POINT_VERTEX_CONFLICT'
                row['triangle_control_points'] = [[point_by_vertex[v] for v in tri] for tri in triangles]
                row['polygon_control_points'] = [[point_by_vertex[v] for v in poly] for poly in polygons]
            rows[str(uid)] = row
        return rows

    original = observe('Source.fbx')
    noop = observe('Noop.fbx')
    stamped = observe('Stamped.fbx', True)
    restored = observe('Source.fbx')
    reduced = {uid: {key: value for key, value in row.items()
                    if key not in ('triangle_control_points', 'polygon_control_points')}
               for uid, row in stamped.items()}
    assert original == noop == reduced == restored, 'NATIVE_CONTROL_INTERFERENCE'
    assert digest(folder / 'Source.fbx') == manifest['source_fbx_sha256']
    output.write_text(json.dumps(dict(status='PASS', source_fbx_sha256=manifest['source_fbx_sha256'],
        source_meta_sha256=manifest['source_meta_sha256'], noop_fbx_sha256=manifest['noop_fbx_sha256'],
        stamped_fbx_sha256=manifest['stamped_fbx_sha256'], original_noop_stamped_restored_equal=True,
        meshes=list(stamped.values())), indent=2))
    print('NATIVE_CONTROL_POINT_PASS meshes=%d' % len(stamped))


if __name__ == '__main__':
    main()
