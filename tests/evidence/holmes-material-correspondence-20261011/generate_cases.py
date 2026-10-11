"""Bounded R/A/B copies of the pinned self-authored fixture. No application launch."""
import argparse
import array
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child(node, name):
    matches = [n for n in node.elems if n.id == name]
    if len(matches) != 1:
        raise ValueError(('unique node required', name))
    return matches[0]


def replace_array(node, values):
    old = node.props[0]
    if not isinstance(old, array.array):
        raise ValueError('array required')
    node.props[0] = array.array(old.typecode, values)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--addon', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(exist_ok=False)  # fresh owned directory; never overwrite an earlier run
    helper = load('holmes_existing_frame', args.repo / 'tests/evidence/inbound-material-face-membership-20261007/verify_inbound_frame.py')
    witness = load('holmes_existing_properties', args.repo / 'blender/fbx_witness.py')
    parser = helper.load_parser(args.addon)
    encoder = importlib.import_module(parser.__package__ + '.encode_bin')
    package = args.repo / 'tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage'
    if helper.sha256(package) != helper.PIN_PACKAGE:
        raise ValueError('source package revision changed')
    with tarfile.open(package) as archive:
        prefix = 'abcdefabcdefabcdefabcdefabcdefab/'
        if archive.extractfile(prefix + 'pathname').read().decode().strip() != 'Assets/PublicMaterialSource/Input.fbx':
            raise ValueError('source GUID/path mismatch')
        for entry, filename in [('asset', 'original.fbx'), ('asset.meta', 'original.fbx.meta')]:
            with (out / filename).open('xb') as stream:
                stream.write(archive.extractfile(prefix + entry).read())
    if helper.sha256(out / 'original.fbx') != helper.PIN_FBX or helper.sha256(out / 'original.fbx.meta') != helper.PIN_META:
        raise ValueError('source payload revision changed')
    original, version = parser.parse(str(out / 'original.fbx'), use_namedtuple=True)
    def no_marker(node):
        if node.id == b'P' and node.props and node.props[0] == witness.PROPERTY:
            raise ValueError('unexpected witness marker')
        for n in node.elems:
            no_marker(n)
    no_marker(original)
    def encode(node):  # existing property conversion, without bpy-dependent witness insertion
        encoded = encoder.FBXElem(node.id)
        if len(node.props_type) != len(node.props):
            raise ValueError('property types mismatch')
        for kind, value in zip(node.props_type, node.props):
            getattr(encoded, witness.METHODS[kind])(value)
        encoded.elems.extend(encode(n) for n in node.elems)
        return encoded
    manifest = dict(package_sha256=helper.PIN_PACKAGE, original_fbx_sha256=helper.PIN_FBX,
                    meta_sha256=helper.PIN_META, fbx_version=version,
                    encoder_sha256=helper.sha256(args.addon / 'encode_bin.py'),
                    parser_sha256=helper.sha256(args.addon / 'parse_fbx.py'), cases={})
    for case in ['R', 'A', 'B']:
        root = copy.deepcopy(original)
        objects = child(root, b'Objects')
        geometries = [n for n in objects.elems if n.id == b'Geometry' and n.props[0] == 329684292]
        if len(geometries) != 1:
            raise ValueError('geometry UID mismatch')
        g = geometries[0]
        pvi = child(g, b'PolygonVertexIndex')
        if len(pvi.props[0]) != 36 or any(v < 0 for i, v in enumerate(pvi.props[0]) if i % 3 != 2) or any(v >= 0 for v in pvi.props[0][2::3]):
            raise ValueError('only pinned twelve triangles supported')
        materials = child(child(g, b'LayerElementMaterial'), b'Materials')
        if list(materials.props[0]) != [2]*6 + [1]*4 + [0]*2:
            raise ValueError('pinned material records changed')
        if case == 'A':
            # Refuse extra layers: otherwise an unhandled polygon-addressed stream could change meaning.
            if sorted(n.id for n in g.elems if n.id.startswith(b'LayerElement')) != [b'LayerElementMaterial', b'LayerElementNormal', b'LayerElementUV']:
                raise ValueError('unsupported extra geometry layer')
            order = [i for slot in [1, 0, 2] for i, value in enumerate(materials.props[0]) if value == slot]
            loops = [i*3+j for i in order for j in range(3)]
            inverse = {old: new for new, old in enumerate(loops)}
            for layer_name, array_name in [(b'LayerElementUV', b'UVIndex'), (b'LayerElementNormal', b'NormalsIndex')]:
                layer = child(g, layer_name)
                if child(layer, b'MappingInformationType').props[0] != b'ByPolygonVertex' or child(layer, b'ReferenceInformationType').props[0] != b'IndexToDirect':
                    raise ValueError('unsupported layer addressing')
                stream = child(layer, array_name)
                if len(stream.props[0]) != 36:
                    raise ValueError('corner stream length mismatch')
                replace_array(stream, [stream.props[0][i] for i in loops])
            replace_array(pvi, [pvi.props[0][i] for i in loops])
            replace_array(materials, [materials.props[0][i] for i in order])
            edges = child(g, b'Edges')
            replace_array(edges, [inverse[i] for i in edges.props[0]])
        if case == 'B':
            connections = child(root, b'Connections')
            indices = [i for i, n in enumerate(connections.elems) if n.id == b'C' and n.props[0] == b'OO' and n.props[2] == 208084244 and n.props[1] in {943593828, 504963197, 123443898}]
            if len(indices) != 3:
                raise ValueError('material connections mismatch')
            old = [connections.elems[i] for i in indices]
            if [n.props[1] for n in old] != [943593828, 504963197, 123443898]:
                raise ValueError('pinned connections changed')
            reordered = [old[i] for i in [2, 0, 1]]
            for i, n in zip(indices, reordered):
                connections.elems[i] = n
            lookup = {n.props[1]: i for i, n in enumerate(reordered)}
            replace_array(materials, [lookup[old[i].props[1]] for i in materials.props[0]])
        path = out / (case + '.fbx')
        if path.exists():
            raise ValueError('occupied output')
        encoder.write(str(path), encode(root), version)
        actual, actual_version = parser.parse(str(path), use_namedtuple=True)
        no_marker(actual)
        if actual_version != version or witness.canonical(actual) != witness.canonical(root):
            raise ValueError('written FBX has undeclared semantic changes')
        manifest['cases'][case] = dict(fbx_sha256=helper.sha256(path), meta_sha256=helper.PIN_META,
                                     writer_semantic_readback_equal=True)
    if helper.sha256(package) != helper.PIN_PACKAGE or helper.sha256(out / 'original.fbx') != helper.PIN_FBX:
        raise ValueError('original changed')
    with (out / 'generation.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
    print('R/A/B copies generated; independent judgment still required')


if __name__ == '__main__':
    main()
