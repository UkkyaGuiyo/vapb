# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender CLI: SOURCE_WITNESS_FOLDER NEW_EXTERNAL_PROJECT. Diagnostic UV only."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from unitypackage_blender_importer.blender.fbx_witness import canonical, encode_node


def main():
    from io_scene_fbx import encode_bin, parse_fbx
    source_folder, project = map(Path, sys.argv[sys.argv.index('--') + 1:])
    repo = Path(__file__).resolve().parents[2]
    assert not project.exists() and repo.resolve() not in project.resolve().parents
    source = source_folder / 'Source.fbx'
    meta = source_folder / 'Source.fbx.meta'
    witness = json.loads((source_folder / 'witness_v2.json').read_text(encoding='utf-8-sig'))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    asset, = witness['assets']
    assert asset['source_fbx_sha256'] == digest(source) and asset['source_meta_sha256'] == digest(meta)
    root, version = parse_fbx.parse(str(source), use_namedtuple=True)
    geometries = {n.props[0]: n for n in next(n for n in root.elems if n.id == b'Objects').elems
        if n.id == b'Geometry' and n.props[2] == b'Mesh'}
    rows = []
    for model in asset['models']:
        if not model.get('geometry_uid'):
            continue
        geometry = geometries[int(model['geometry_uid'])]
        existing = [n for n in geometry.elems if n.id == b'LayerElementUV']
        assert [n.props[0] for n in existing] == list(range(len(existing))), 'UV_LAYOUT_UNSUPPORTED'
        assert len(existing) < 8, 'NO_SPARE_UV_CHANNEL'
        count = len(next(n.props[0] for n in geometry.elems if n.id == b'Vertices')) // 3
        assert 0 < count < 2**24, 'CONTROL_POINT_RANGE_UNSUPPORTED'
        for renderer in model['renderers']:
            rows.append(dict(mesh_guid=asset['asset_guid'], mesh_local_id=str(renderer['mesh_local_id']),
                geometry_uid=str(model['geometry_uid']), control_point_count=count, uv_channel=len(existing)))
    assert rows and len({(r['mesh_guid'], r['mesh_local_id']) for r in rows}) == len(rows)
    assert len({r['geometry_uid'] for r in rows}) == len(rows), 'SHARED_GEOMETRY_UNSUPPORTED_CONTROL'
    project.mkdir(parents=True)
    editor = project / 'Assets/Editor'; editor.mkdir(parents=True)
    shutil.copy2(Path(__file__).parent / 'Editor/VapbControlPointProbe.cs', editor)
    (project / 'Packages').mkdir(); (project / 'Packages/manifest.json').write_text('{"dependencies":{}}')
    (project / 'ProjectSettings').mkdir()
    (project / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.22f1\n')
    target = project / 'Assets/VapbGeometry/Model.fbx'; target.parent.mkdir()
    shutil.copy2(source, project / 'Source.fbx'); shutil.copy2(meta, project / 'Source.fbx.meta')
    shutil.copy2(source, target); shutil.copy2(meta, Path(str(target) + '.meta'))
    def element(parent, name, method=None, value=None):
        node = encode_bin.FBXElem(name); parent.elems.append(node)
        if method:
            getattr(node, method)(value)
        return node
    for name, stamped in [('Noop.fbx', False), ('Stamped.fbx', True)]:
        encoded = encode_node(root, False)
        objects = next(n for n in encoded.elems if n.id == b'Objects')
        if stamped:
            for row in rows:
                # Encoded integer properties are byte strings; retain raw object positions
                # only for encoding their already-proven UID nodes, not Unity object matching.
                raw_objects = next(n for n in root.elems if n.id == b'Objects')
                index, = [i for i,n in enumerate(raw_objects.elems) if n.props[0] == int(row['geometry_uid'])]
                geometry = objects.elems[index]
                uv = element(geometry, b'LayerElementUV', 'add_int32', row['uv_channel'])
                element(uv, b'Version', 'add_int32', 101)
                element(uv, b'Name', 'add_string', b'VAPB_CONTROL_POINT_INDEX')
                element(uv, b'MappingInformationType', 'add_string', b'ByVertice')
                element(uv, b'ReferenceInformationType', 'add_string', b'Direct')
                element(uv, b'UV', 'add_float64_array', [v for i in range(row['control_point_count']) for v in (float(i + 1), 0.375)])
                original_geometry = geometries[int(row['geometry_uid'])]
                existing_layer = [i for i,n in enumerate(original_geometry.elems) if n.id == b'Layer' and n.props[0] == row['uv_channel']]
                assert len(existing_layer) <= 1
                if existing_layer:
                    layer = geometry.elems[existing_layer[0]]
                else:
                    layer = element(geometry, b'Layer', 'add_int32', row['uv_channel'])
                    element(layer, b'Version', 'add_int32', 100)
                ref = element(layer, b'LayerElement')
                element(ref, b'Type', 'add_string', b'LayerElementUV')
                element(ref, b'TypedIndex', 'add_int32', row['uv_channel'])
        output = project / name; encode_bin.write(str(output), encoded, version)
        decoded, _ = parse_fbx.parse(str(output), use_namedtuple=True)
        if stamped:
            for row in rows:
                geometry = next(n for n in next(n for n in decoded.elems if n.id == b'Objects').elems if n.props[0] == int(row['geometry_uid']))
                uv, = [n for n in geometry.elems if n.id == b'LayerElementUV' and n.props[0] == row['uv_channel']]
                values = next(n.props[0] for n in uv.elems if n.id == b'UV')
                assert list(values) == [v for i in range(row['control_point_count']) for v in (float(i + 1), .375)]
                geometry.elems.remove(uv)
                layer, = [n for n in geometry.elems if n.id == b'Layer' and n.props[0] == row['uv_channel']]
                ref, = [n for n in layer.elems if n.id == b'LayerElement' and
                    any(v.id == b'Type' and v.props == [b'LayerElementUV'] for v in n.elems)]
                layer.elems.remove(ref)
                original_geometry = geometries[int(row['geometry_uid'])]
                if not any(n.id == b'Layer' and n.props[0] == row['uv_channel'] for n in original_geometry.elems):
                    geometry.elems.remove(layer)
        assert canonical(decoded) == canonical(root), 'NON_MARKER_SOURCE_CHANGED'
    manifest = dict(source_fbx_sha256=digest(source), source_meta_sha256=digest(meta), meshes=rows,
        noop_fbx_sha256=digest(project/'Noop.fbx'), stamped_fbx_sha256=digest(project/'Stamped.fbx'))
    (project / 'ControlPointManifest.json').write_text(json.dumps(manifest, indent=2))
    print('CONTROL_POINT_PROJECT_PREPARED meshes=' + str(len(rows)) + ' original_data_preserved=1')


if __name__ == '__main__':
    main()
