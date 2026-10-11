"""New Cube geometric face membership, independently of old receipts and UVs."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser()
    for key in ('repo', 'work'): ap.add_argument('--' + key, type=Path, required=True)
    args = ap.parse_args(); repo, work = args.repo, args.work
    out = repo / 'tests/evidence/holmes-material-correspondence-20261011/replacement-multimaterial'
    load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    save = lambda name, data: (out / name).write_text(json.dumps(data, indent=2) + '\n')
    replacement, exported, native = (load(p) for p in (work / 'replace.json', work / 'export.json', work / 'unity-run/native.json'))
    assert replacement['status'] == exported['status'] == native['status'] == 'PASS'
    assert replacement['state'] == exported['state']
    assert replacement['state']['object_keys'] == replacement['state']['mesh_keys'] == []
    assert replacement['imported_mesh_object_and_data_deleted'] and native['prefab_sha256_before'] == 'ABSENT'
    assert native['package_sha256'] == exported['package_sha256'] == sha(work / 'ReplacementOutput.unitypackage')
    assert native['fbx_sha256'] == native['fbx_sha256_after'] == exported['fbx_sha256'] == sha(work / 'Exported.fbx')
    assert native['manifest_sha256'] == exported['manifest_sha256'] == sha(work / 'manifest.json')
    assert native['explicit_apply'] and native['apply_returned_true'] and native['finalizer_result'] == 'COMPLETE'
    assert native['repeat_apply_returned_true'] and native['repeat_materials_unchanged'] and native['repeat_mesh_unchanged']
    assert native['prefab_repeat_before'] == native['prefab_repeat_after']
    task = exported['task']; assert task['kind'] == 'BUILD_EXPORTED_STATIC_V2'
    sys.path.insert(0, str(repo / 'tests/evidence/holmes-material-correspondence-20261011/topology-boundary'))
    from judge import cover, native_faces
    from read_input import parse, decode, child
    root, version = parse(work / 'Exported.fbx', repo, Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/scripts/addons_core/io_scene_fbx'))
    raw = decode(root)
    objects = child(root, b'Objects').elems
    model = next(n for n in objects if n.id == b'Model' and n.props[0] == raw['model_uid'])
    custom = {n.props[0].decode(): n.props[-1] for n in child(model, b'Properties70').elems if n.id == b'P' and n.props[0].startswith(b'_vapb')}
    assert custom == {'_vapb_export_object_id': task['export_object_id'].encode()}
    by_id = {m['export_material_id']: {k: m[k] for k in ('guid', 'file_id')} for m in task['materials']}
    transported = {}
    for n in objects:
        if n.id == b'Material':
            label = n.props[1].split(b'\x00')[0].decode()
            assert label in by_id, 'Unknown serialized Material Export ID'
            transported[n.props[0]] = by_id[label]
    assert len(transported) == len(by_id) == 4
    policy = json.loads(native['policy'])
    assert policy['meshes']['bakeAxisConversion'] is False and policy['meshes']['m_UseFileScale'] is True
    scale = policy['meshes']['m_FileScale']
    assert scale > 0
    # Explicit diagnostic mesh-local frame: raw FBX = Blender Cube coordinates;
    # Unity uses reflected X and the captured file scale. No material-based
    # permutation fitting, old IDs, face ordinals or UV signatures are used.
    native_corners = [(-p['x'] / scale, p['y'] / scale, p['z'] / scale) for p in native['vertices']]
    assert all(all(abs(c) == 1 for c in p) for p in native_corners)
    expected = exported['state']['faces']
    assert len(expected) == 6
    matched = {r['plane']: {'fbx': [], 'unity': []} for r in expected}
    def join(corners, material, kind):
        candidates = [r for r in expected if set(map(tuple, corners)) <= set(map(tuple, r['corners']))]
        assert len(candidates) == 1, 'Ambiguous/unknown geometric Cube face'
        row = candidates[0]
        wanted = {k: row['material'][k] for k in ('guid', 'file_id')}
        assert material == wanted, 'Actual face Material differs from final Blender state'
        matched[row['plane']][kind].append(corners)
    for face in raw['polygons']:
        join(face['positions'], transported[face['uid']], 'fbx')
    for face in native_faces(native):
        join([native_corners[i] for i in face['indices']], native['materials'][face['group']], 'unity')
    rows = []
    for row in expected:
        axis = max(range(3), key=lambda i: abs(row['normal'][i]))
        remaining = [i for i in range(3) if i != axis]
        project = lambda points: [[p[i] for i in remaining] for p in points]
        winding = {kind: cover(project(row['corners']), [project(face) for face in matched[row['plane']][kind]]) for kind in ('fbx', 'unity')}
        rows.append(dict(plane=row['plane'], expected_material=row['material'], fbx_triangles=len(matched[row['plane']]['fbx']),
                         unity_triangles=len(matched[row['plane']]['unity']), cover='PASS', projected_winding=winding))
    assert len(raw['polygons']) == len(native_faces(native)) == 12
    initial = load(work / 'unity-run/initial.json')
    assert not initial['finalizer_available'] and not initial['assistant_available']
    assert not any('VAPBExport' in p for p in initial['asset_paths'])
    events = [dict(zip(('utc', 'stage', 'detail'), line.split('\t', 2))) for line in (work / 'unity-run/events.tsv').read_text().splitlines()]
    a = next(i for i, e in enumerate(events) if e['stage'] == 'A_import_start'); relevant = events[a:]
    stages = [e['stage'] for e in relevant]
    assert all(stage in stages for stage in ('B_import_completed', 'C_compile_finished', 'D_after_reload', 'E_finalizer_available'))
    assert stages.index('C_compile_finished') < stages.index('D_after_reload') < stages.index('E_finalizer_available')
    assert all('errors=0' in e['detail'] for e in relevant if e['stage'] == 'C_assembly_finished')
    frozen_root = repo / 'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan'
    frozen = load(frozen_root / 'input-and-predictions.json')
    assert all(sha(frozen_root / name) == digest for name, digest in frozen['asset_sha256'].items())
    source_hashes = {name: sha(repo / name) for name in ('export/final_state_package.py', 'unity_editor/Editor/VapbFinalStateFinalizer.cs', 'unity_editor/Editor/VapbImportAssistant.cs')}
    observer = work / 'Project/Assets/HolmesReplacementConsumer/Editor/Capture.cs'
    assert observer.read_bytes().replace(b'\r\n', b'\n') == (out / 'Capture.cs').read_bytes().replace(b'\r\n', b'\n')
    assert native['finalizer_source_sha256'] == source_hashes['unity_editor/Editor/VapbFinalStateFinalizer.cs']
    runs = {}
    for folder in ('replace-run', 'diagnose-run', 'replace-corrected-run', 'export-run'):
        process, exited = load(work / folder / 'blender-process.json'), load(work / folder / 'blender-exit.json')
        assert exited['exit_code'] == 0 and exited['owned_children_absent']
        runs[folder] = dict(process=process, exited=exited)
    process, exited, released = (load(work / 'unity-run' / name) for name in ('process.json', 'exit.json', 'release.json'))
    assert exited['exitCode'] == 0 and released['releaseVerified']
    resource = load(work / 'resource-return.json')
    assert not resource['processCensusConflict'] and resource['mutexAvailableAndProbeReleased'] and resource['poolAllFree'] and resource['newProjectLockAbsent']
    for name, data in (('replace.json', replacement), ('export.json', exported), ('initial.json', initial), ('events.json', events)):
        save(name, data)
    public = dict(native); public['policy'] = policy['meshes']; save('native.json', public)
    save('transport.json', dict(fbx_version=version, raw=raw, export_object_id=task['export_object_id'], serialized_custom_properties={k: v.decode() for k, v in custom.items()}, material_export_ids=by_id))
    save('judgment.json', dict(instruction_id='HOLMES-20261011-06', verdict='VERIFIED_IN_SCOPE', H_A='SUPPORTED_IN_SCOPE', H_B='NOT_OBSERVED_IN_SCOPE', faces=rows,
                              frame='Blender = raw FBX local; native common corners = (-x/fileScale,y/fileScale,z/fileScale), captured bakeAxisConversion false',
                              common_corner_exact=True, uv_used_for_correspondence=False, old_mesh_receipt_used=False,
                              positions='NOT_RUN for full transform/world fidelity', winding='Projected local parity recorded; oriented/culling fidelity NOT_RUN', render='NOT_RUN'))
    save('run-summary.json', dict(blender=runs, unity=dict(pid=process['pid'], startUtc=process['startUtc'], exitUtc=exited['exitUtc'], exitCode=0,
                                                        actual_free_gib=process['actual_free_gib'], release=released), resource_return=resource,
                                  product_source_sha256=source_hashes, executed_observer_sha256=sha(observer), public_observer_line_endings_only_normalized=True,
                                  product_code_changes=False, original_frozen_hashes_unchanged=len(frozen['asset_sha256']),
                                  first_failure='BLENDER_PROVENANCE observer assertion: RECONSTRUCT imports two Mesh objects, not one; no product defect',
                                  observer_correction='Delete all imported Mesh objects/data in own working copy; select retained Materials by exact package/GUID/fileID, not old slot membership'))
    print('HOLMES06_NEW_CUBE_SIX_GEOMETRIC_FACE_MATERIAL_RETURN_PASS')


if __name__ == '__main__': main()
