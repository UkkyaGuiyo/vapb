"""Encode a bounded external source-FBX witness without changing its source.

Blender --background --python-exit-code 1 --python <this> -- <external-folder>
The folder must contain Source.fbx. Private input/output stays outside Git.
This is an experiment, not a production identity mapper.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_witness import prepare_witness


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder == repo or repo in folder.parents:
        raise ValueError('EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    source = folder / 'Source.fbx'
    uids = prepare_witness(source, folder / 'Noop.fbx', folder / 'Witness.fbx')
    print(f'FBX_SOURCE_WITNESS_PASS models={len(uids)} original_unchanged=1')


if __name__ == '__main__':
    main()
