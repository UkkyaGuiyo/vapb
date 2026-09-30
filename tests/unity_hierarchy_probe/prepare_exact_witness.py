"""Prepare an exact public package revision for the existing Unity witness probe.
Run: python prepare_exact_witness.py PACKAGE EXPECTED_SHA256 NEW_PROJECT.
Then run blender_fbx_source_witness.py and Unity VapbBoneWitnessProbe.Run.
Only generated isolated copies are instrumented; v1 witness output is unchanged.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    package, expected, project = sys.argv[1:]
    package, project = Path(package).resolve(), Path(project).resolve()
    repo = Path(__file__).resolve().parents[2]
    if project.exists() or project == repo or repo in project.parents:
        raise ValueError('UNUSED_EXTERNAL_PROJECT_REQUIRED')
    raw = package.read_bytes()
    if sha(raw) != expected:
        raise ValueError('PACKAGE_REVISION_MISMATCH')
    with tarfile.open(package, 'r:*') as archive:
        paths = {}
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith('/pathname'):
                pathname = archive.extractfile(member).read().decode('utf-8').strip()
                if pathname.lower().endswith('.fbx'):
                    paths[member.name.split('/')[0]] = pathname
        if len(paths) != 1:
            raise ValueError('EXACT_FBX_AMBIGUOUS')
        guid, pathname = next(iter(paths.items()))
        fbx = archive.extractfile(guid + '/asset').read()
        meta = archive.extractfile(guid + '/asset.meta').read()
    project.mkdir(parents=True)
    (project / 'Source.fbx').write_bytes(fbx)
    (project / 'ExactPackage.unitypackage').write_bytes(raw)
    (project / 'Source.fbx.meta').write_bytes(meta)
    editor = project / 'Assets/Editor'
    editor.mkdir(parents=True)
    (project / 'Packages').mkdir()
    (project / 'Packages/manifest.json').write_text('{"dependencies": {}}', encoding='utf-8')
    (project / 'ProjectSettings').mkdir()
    (project / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.22f1\n', encoding='utf-8')
    probe_path = repo / 'tests/unity_bone_witness_probe/Editor/VapbBoneWitnessProbe.cs'
    probe = probe_path.read_text(encoding='utf-8')
    needle = 'mapping = InspectMarkers(witnessed, report, original, originalMeta);'
    if probe.count(needle) != 1:
        raise ValueError('PROBE_INSTRUMENTATION_POINT_AMBIGUOUS')
    instrumented = probe.replace(needle, needle + '\n            VapbHierarchyBoneObservation.Capture(original, originalMeta);')
    (editor / probe_path.name).write_text(instrumented, encoding='utf-8')
    shutil.copy2(repo / 'tests/unity_bone_witness_probe/VapbSourceBoneMarker.cs', project / 'Assets/VapbSourceBoneMarker.cs')
    shutil.copy2(Path(__file__).parent / 'Editor/VapbHierarchyBoneObservation.cs', editor)
    shutil.copy2(Path(__file__).parent / 'Editor/VapbHierarchyPackageSkinObservation.cs', editor)
    shutil.copy2(Path(__file__).parent / 'Editor/VapbHierarchyOracle.cs', editor)
    identity = {'package_sha256': sha(raw), 'source_fbx_sha256': sha(fbx),
        'source_meta_sha256': sha(meta), 'model_guid': guid, 'source_pathname': pathname,
        'unity_probe_original_sha256': sha(probe.encode()),
        'unity_probe_instrumented_sha256': sha(instrumented.encode()),
        'probe_patch': 'one diagnostic Capture call after InspectMarkers; v1 schema unchanged'}
    (project / 'ExactSourceIdentity.json').write_text(json.dumps(identity, indent=2), encoding='utf-8')
    print('EXACT_WITNESS_PREPARED fbx_count=1 source_unchanged=1')


if __name__ == '__main__':
    main()
