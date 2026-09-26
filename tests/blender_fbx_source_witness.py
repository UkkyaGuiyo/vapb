"""Encode a bounded external source-FBX witness without changing its source.

Blender --background --python-exit-code 1 --python <this> -- <external-folder>
The folder must contain Source.fbx. Private input/output stays outside Git.
This is an experiment, not a production identity mapper.
"""
import hashlib
from pathlib import Path
import sys

from io_scene_fbx import encode_bin, parse_fbx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_fbx_witness_fixture import PROPERTY, canonical, encode_node


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder == repo or repo in folder.parents:
        raise ValueError('EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    source = folder / 'Source.fbx'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    destinations = [folder / 'Noop.fbx', folder / 'Witness.fbx']
    if any(path.exists() for path in destinations):
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    decoded, version = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(child for child in decoded.elems if child.id == b'Objects')
    models = [node for node in objects.elems if node.id == b'Model']
    assert models and len({node.props[0] for node in models}) == len(models)
    for destination, witness in zip(destinations, (False, True)):
        encode_bin.write(str(destination), encode_node(decoded, witness), version)
        after, after_version = parse_fbx.parse(str(destination), use_namedtuple=True)
        assert version == after_version and canonical(decoded) == canonical(after), 'SOURCE_SEMANTICS_CHANGED'
        if witness:
            after_objects = next(child for child in after.elems if child.id == b'Objects')
            for model in (node for node in after_objects.elems if node.id == b'Model'):
                properties = next(child for child in model.elems if child.id == b'Properties70')
                markers = [p for p in properties.elems if p.props and p.props[0] == PROPERTY]
                assert len(markers) == 1 and markers[0].props[-1] == str(model.props[0]).encode()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    print(f'FBX_SOURCE_WITNESS_PASS models={len(models)} original_unchanged=1')


if __name__ == '__main__':
    main()
