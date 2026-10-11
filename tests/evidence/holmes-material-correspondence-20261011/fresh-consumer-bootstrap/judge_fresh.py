"""HOLMES05: reuse existing independent corner coverage; no Blender rerun."""
import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--previous', type=Path, required=True)
    args = ap.parse_args()
    repo, work, previous = args.repo, args.work, args.previous
    out = repo / 'tests/evidence/holmes-material-correspondence-20261011/fresh-consumer-bootstrap'
    load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    save = lambda name, data: (out / name).write_text(json.dumps(data, indent=2) + '\n')
    sys.path.insert(0, str(repo / 'tests/evidence/holmes-material-correspondence-20261011/topology-boundary'))
    from judge import cover, native_faces
    export = load(previous / 'export.json')
    initial = load(work / 'initial/initial.json')
    assert not any(initial[k] for k in ('finalizer_available', 'model_finalizer_available', 'assistant_available', 'vapb_named_assemblies'))
    assert all('VAPBExport' not in p and not p.lower().endswith(('.fbx', '.mat', '.prefab')) for p in initial['asset_paths'])
    package = previous / 'EditedMaterialOutput.unitypackage'
    assert sha(package) == export['package_sha256']
    frozen_root = repo / 'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan'
    frozen = load(frozen_root / 'input-and-predictions.json')
    assert all(sha(frozen_root / name) == digest for name, digest in frozen['asset_sha256'].items())
    prior_blends = {'BeforeConfirm.blend': 'a93fc0d6d45210f61e047a5e3c4845cd250839bd6ccc8e667a3541912d73febb',
                    'EditedFinal.blend': 'b034e336787eb9f1b29c51631733c2e0722439e6fa728d42814cc66ffe7b0411'}
    assert all(sha(previous / name) == digest for name, digest in prior_blends.items())
    assert sha(previous / 'Exported.fbx') == export['exported_fbx_sha256']
    assert sha(previous / 'manifest.json') == export['manifest_sha256']
    packaged = []
    with tarfile.open(package, 'r:gz') as tf:
        for member in tf.getmembers():
            if not member.name.endswith('/pathname'):
                continue
            folder = member.name.rsplit('/', 1)[0]
            path = tf.extractfile(member).read().decode().strip()
            for item in ('asset', 'asset.meta'):
                source = tf.extractfile(folder + '/' + item).read()
                target = work / 'Project' / (path + ('.meta' if item == 'asset.meta' else ''))
                # Apply intentionally changes this owned Prefab copy; its imported
                # source hash is checked in Capture.cs before the first Apply.
                if item == 'asset' and path.endswith('.prefab'):
                    continue
                assert target.read_bytes() == source, 'Packaged asset bytes changed: ' + path
            packaged.append(path)
    native = {phase: load(work / phase / 'native.json') for phase in ('initial', 'reopen')}
    faces = {}
    for phase, capture in native.items():
        assert capture['status'] == 'PASS' and capture['explicit_apply'] and capture['apply_returned_true']
        assert capture['import_completed'] == (phase == 'initial')
        assert capture['repeat_apply_returned_true'] and capture['repeat_materials_unchanged'] and capture['repeat_mesh_unchanged']
        assert capture['prefab_repeat_before'] == capture['prefab_repeat_after']
        assert capture['package_sha256'] == export['package_sha256']
        assert capture['manifest_sha256'] == export['manifest_sha256']
        observed = native_faces(capture)
        joined = {row['source_polygon']: [] for row in export['faces']}
        for face in observed:
            match = [row for row in export['faces'] if set(map(tuple, face['uv'])) <= set(map(tuple, row['uv']))]
            assert len(match) == 1, 'Ambiguous final face'
            joined[match[0]['source_polygon']].append(face)
        rows = []
        for final in export['faces']:
            matches = joined[final['source_polygon']]
            winding = cover(final['uv'], [f['uv'] for f in matches])
            material = {k: final['material'][k] for k in ('guid', 'file_id')}
            assert all(capture['materials'][f['group']] == material for f in matches)
            rows.append(dict(final_polygon=final['source_polygon'], expected_material=material,
                             groups=sorted({f['group'] for f in matches}), triangle_count=len(matches),
                             native_winding=winding, cover='PASS'))
        assert len(rows) == 6 and rows[0]['expected_material'] != rows[4]['expected_material']
        faces[phase] = rows
        public = dict(capture)
        public['policy'] = json.loads(public['policy'])['meshes']
        save('native-' + phase + '.json', public)
    assert native['initial']['prefab_sha256_after'] == native['reopen']['prefab_sha256_before']
    for key in ('mesh', 'renderer', 'materials', 'groups', 'uv', 'vertices', 'policy', 'prefab', 'manifest', 'finalizer_script', 'finalizer_source_sha256', 'fbx_sha256', 'meta_sha256'):
        assert native['initial'][key] == native['reopen'][key], 'Reopen state differs: ' + key
    events = []
    for line in (work / 'initial/events.tsv').read_text().splitlines():
        timestamp, stage, detail = line.split('\t', 2)
        events.append(dict(utc=timestamp, stage=stage, detail=detail))
    after_start = events[next(i for i, e in enumerate(events) if e['stage'] == 'A_import_start'):]
    stages = [e['stage'] for e in after_start]
    for stage in ('B_import_completed', 'C_compile_started', 'C_compile_finished', 'D_before_reload', 'D_after_reload', 'E_finalizer_available'):
        assert stage in stages
    assert stages.index('C_compile_finished') < stages.index('D_after_reload') < stages.index('E_finalizer_available')
    assert all('errors=0' in e['detail'] for e in after_start if e['stage'] == 'C_assembly_finished')
    runs = {}
    for phase in ('initial', 'reopen'):
        process, exited, release = (load(work / phase / name) for name in ('process.json', 'exit.json', 'release.json'))
        assert exited['exitCode'] == 0 and release['releaseVerified']
        runs[phase] = dict(pid=process['pid'], startUtc=process['startUtc'], exitUtc=exited['exitUtc'], exitCode=0,
                           ownedChildrenAbsent=release['ownedChildrenAbsent'], lockAbsent=release['lockAbsent'],
                           executed_source_sha256=sha(work / phase / 'executed-existing-runner-private.ps1'))
    resource = load(work / 'resource-return.json')
    assert resource['mutexAvailableAndProbeReleased'] and resource['poolAllFree'] and not resource['processCensusConflict'] and resource['newProjectLockAbsent']
    save('initial.json', initial)
    save('events.json', events)
    save('run-summary.json', dict(runs=runs, resource_return=resource, lease='No fixed-root pool lease; explicitly owned new off-pool Project',
                                  launch_gates='Existing reviewed mutex/census/stability/pool/4GiB-RAM/journal/lock checks passed before each Start',
                                  launch_ram_value='Not separately captured; threshold enforced by executed existing source',
                                  frozen_original_hashes_unchanged=len(frozen['asset_sha256']),
                                  prior_blends_package_fbx_manifest_unchanged=True, product_code_changes=False))
    save('judgment.json', dict(instruction_id='HOLMES-20261011-05', verdict='VERIFIED_IN_SCOPE', faces=faces,
                               repeat_apply='PASS', normal_reopen_retention='PASS', initial_install='PASS',
                               unchanged_packaged_asset_and_meta_paths=packaged, package_sha256=sha(package),
                               GUI='NOT_RUN', render='NOT_RUN', reimport='NOT_RUN', distinct_variant='NOT_ESTABLISHED'))
    print('HOLMES05_FIRST_INSTALL_REPEAT_REOPEN_AND_SIX_FACE_COVER_PASS')


if __name__ == '__main__':
    main()
