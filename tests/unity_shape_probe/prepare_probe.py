"""Prepare a new isolated Shape probe: create FBX PROJECT, oracle PACKAGE PROJECT, controls WITNESS_DIR PROJECT."""
import hashlib
from pathlib import Path
import shutil
import sys
import tarfile


def main():
    mode, input_path, destination = sys.argv[1:]
    source, project = Path(input_path).resolve(), Path(destination).resolve()
    repo = Path(__file__).resolve().parents[2]
    if mode not in ('create', 'oracle', 'controls') or project.exists() or project == repo or repo in project.parents:
        raise ValueError('UNUSED_EXTERNAL_PROJECT_REQUIRED')
    editor = project / 'Assets/Editor'
    editor.mkdir(parents=True)
    (project / 'Packages').mkdir()
    (project / 'Packages/manifest.json').write_text('{"dependencies":{}}')
    (project / 'ProjectSettings').mkdir()
    (project / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.22f1\n')
    for probe in (Path(__file__).parent / 'Editor').glob('*.cs'):
        shutil.copy2(probe, editor)
    if mode == 'create':
        asset = project / 'Assets/VapbShape/Model.fbx'
        asset.parent.mkdir()
        shutil.copy2(source, asset)
        if Path(str(source) + '.meta').exists():
            shutil.copy2(Path(str(source) + '.meta'), Path(str(asset) + '.meta'))
    elif mode == 'oracle':
        for name in ('VapbHierarchyPackageSkinObservation.cs', 'VapbHierarchyOracle.cs'):
            shutil.copy2(repo / 'tests/unity_hierarchy_probe/Editor' / name, editor)
        shutil.copy2(source, project / 'ExactPackage.unitypackage')
        with tarfile.open(source, 'r:*') as archive:
            models = [m.name.split('/')[0] for m in archive.getmembers()
                if m.isfile() and m.name.endswith('/pathname') and
                archive.extractfile(m).read().decode('utf-8').strip().lower().endswith('.fbx')]
            if len(models) != 1:
                raise ValueError('EXACT_FBX_AMBIGUOUS')
            (project / 'SelectedModelPath.txt').write_text(archive.extractfile(models[0] + '/pathname').read().decode('utf-8').strip())
            for target, member in [('Source.fbx', '/asset'), ('Source.fbx.meta', '/asset.meta')]:
                (project / target).write_bytes(archive.extractfile(models[0] + member).read())
    else:
        asset = project / 'Assets/VapbShape/Model.fbx'
        asset.parent.mkdir()
        for name in ('Source.fbx', 'Source.fbx.meta', 'ShapeNoop.fbx', 'ShapeMarked.fbx'):
            shutil.copy2(source / name, project / name)
        shutil.copy2(source / 'Source.fbx', asset)
        shutil.copy2(source / 'Source.fbx.meta', Path(str(asset) + '.meta'))
    print('SHAPE_PROJECT_PREPARED mode=' + mode)


if __name__ == '__main__':
    main()
