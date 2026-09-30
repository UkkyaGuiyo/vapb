"""External display-marker experiment for FBX channel UIDs; never production import.

Blender background --python-exit-code 1 --python FILE -- EXTERNAL_SOURCE_FOLDER.
The two outputs differ only in display labels, never UIDs/connections/deltas.
Unity must independently verify equivalence before using marker observations.
"""
import hashlib
from pathlib import Path
import sys
import struct

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_witness import encode_node


def main():
    from io_scene_fbx import encode_bin, parse_fbx
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    assert folder != repo and repo not in folder.parents
    source = folder / 'Source.fbx'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    raw, version = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(n for n in raw.elems if n.id == b'Objects')
    nodes = {n.props[0]: n for n in objects.elems}
    connections = next(n for n in raw.elems if n.id == b'Connections')
    shapes = {}
    for c in connections.elems:
        if c.id == b'C' and len(c.props) == 3 and c.props[0] == b'OO':
            shape, channel = (nodes.get(uid) for uid in c.props[1:])
            if (shape and channel and shape.id == b'Geometry' and shape.props[2] == b'Shape'
                    and channel.id == b'Deformer' and channel.props[2] == b'BlendShapeChannel'):
                assert shape.props[0] not in shapes
                shapes[shape.props[0]] = channel.props[0]
    assert shapes
    for name, marked in (('ShapeNoop.fbx', False), ('ShapeMarked.fbx', True)):
        output = folder / name
        assert not output.exists()
        tree = encode_node(raw, False)
        target = next(n for n in tree.elems if n.id == b'Objects')
        for n, original in zip(target.elems, objects.elems):
            uid = original.props[0]
            channel_uid = shapes.get(uid, uid if uid in shapes.values() else None)
            if marked and channel_uid is not None:
                assert n.props_type[1] == ord('S')
                tail = original.props[1].split(b'\x00\x01', 1)[1]
                label = ('VAPB_SHAPE_UID_' + str(channel_uid)).encode() + b'\x00\x01' + tail
                n.props[1] = struct.pack('<I', len(label)) + label
        encode_bin.write(str(output), tree, version)
        decoded, _ = parse_fbx.parse(str(output), use_namedtuple=True)
        for n, original in zip(next(n for n in decoded.elems if n.id == b'Objects').elems, objects.elems):
            if marked and (n.props[0] in shapes or n.props[0] in shapes.values()):
                expected_uid = shapes.get(n.props[0], n.props[0])
                assert n.props[1].split(b'\x00\x01')[0] == ('VAPB_SHAPE_UID_' + str(expected_uid)).encode()
                n.props[1] = original.props[1]
        # Encoder metadata is checked by the same source-witness canonical form.
        from unitypackage_blender_importer.blender.fbx_witness import canonical
        assert canonical(decoded) == canonical(raw)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    print('SHAPE_CHANNEL_MARKER_CREATED channels=%d source_unchanged=1' % len(set(shapes.values())))


if __name__ == '__main__':
    main()
