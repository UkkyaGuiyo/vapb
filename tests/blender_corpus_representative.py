# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture one exact direct occurrence through production E0/E1 export.

Blender --factory-startup --background --python-exit-code 1 --python FILE --
CONTEXT_JSON RESULT_JSON. This writes export evidence, never a round-trip PASS.
Context supplies input, expected_sha256, selection, mode, output_dir, witness,
source_observation, package_observation, control_report, optional input_blend.
All outputs and diagnostic console are private; existing output is refused.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def need(condition, code):
    if not condition:
        raise ValueError(code)


def check_model_material_scope(mesh):
    # This capture uses the model Skin route, which currently requires a real
    # Material carrier in every slot. Reject before edits or rollback injection.
    need(all(slot.material is not None for slot in mesh.material_slots),
         'MODEL_UNASSIGNED_MATERIAL_SCOPE_UNSUPPORTED')


def capture_failure(error):
    code = str(error)
    code = code if code.isupper() and code.replace('_', '').isalnum() else 'CAPTURE_EXCEPTION'
    unsupported = 'SCOPE_UNSUPPORTED' in code or code == 'CP_UNREFERENCED_VERTEX'
    reason = 'HARNESS_UNSUPPORTED' if unsupported else 'HARNESS_ERROR'
    if code == 'MODEL_UNASSIGNED_MATERIAL_SCOPE_UNSUPPORTED':
        reason = 'UNSUPPORTED_STRUCTURE'
    return dict(verdict='UNSUPPORTED' if unsupported else 'UNPROVEN',
                reason=reason, detail_code=code, error_type=type(error).__name__,
                scope='PRODUCTION_EXPORT_CAPTURE_ONLY')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, document):
    Path(path).write_text(json.dumps(document, indent=2), encoding='utf-8')


def select_record(records, selection):
    matches = [row for row in records if row.get('renderer_class_id') == 137
        and row.get('root_asset_guid') == selection['root_guid']
        and row.get('source_key', {}).get('source_asset_guid') == selection['renderer_guid']
        and str(row.get('source_key', {}).get('renderer_file_id')) == selection['renderer_file_id']
        and row.get('mesh', {}).get('mesh_guid') == selection['mesh_guid']
        and str(row.get('mesh', {}).get('mesh_file_id')) == selection['mesh_file_id']]
    need(len(matches) == 1, 'SELECTED_OCCURRENCE_NOT_UNIQUE')
    record = matches[0]
    need(not record['instance_edge_path'] and record['source_key']['source_kind'] == 'PREFAB_LOCAL',
         'NESTED_CAPTURE_SCOPE_UNSUPPORTED')
    return record


def select_proof(observation, occurrence):
    need(observation.get('status') == 'OBSERVED_NOT_COMPARED'
         and observation.get('source_validated') is True
         and observation.get('source_control_report_pass') is True, 'PRIOR_SOURCE_CONTROL_UNPROVEN')
    rows = [row for row in observation['skins'] if row['occurrence_id'] == occurrence]
    need(len(rows) == 1, 'PRIOR_SKIN_NOT_UNIQUE')
    prior = rows[0]
    need(prior['renderer_owner_valid'] and prior['root_frame_binding_valid']
         and prior['bones'] and all(b['carrier_constraint_valid'] and b['bone_parent_valid']
                                    for b in prior['bones']), 'PRIOR_SKIN_RELATION_UNPROVEN')
    return prior


def checkpoint_with_transport(source, staged, source_local, staged_local):
    """Join observed CP transport to exact clone indices; source world geometry is the baseline."""
    need(source_local == staged_local, 'EXPORT_LOCAL_DATA_CHANGED')
    need(source['triangles'] == staged['triangles'] and source['polygons'] == staged['polygons']
         and source['skin_weights'] == staged['skin_weights'], 'EXPORT_CHECKPOINT_CHANGED')
    channel = staged['marker_channel']
    need(all(value is not None for value in staged['vertex_control_point_indices']),
         'CP_UNREFERENCED_VERTEX')
    need(staged['vertex_control_point_indices'] == list(range(len(source['positions'])))
         and staged['triangle_control_points'] == source['triangles'], 'CLONE_CP_IDENTITY_UNPROVEN')
    diagnostic = [uv for uv in staged['uv_channels'] if uv['channel'] == channel]
    need(len(diagnostic) == 1 and [uv for uv in staged['uv_channels'] if uv['channel'] != channel]
         == source['uv_channels'], 'EXPORT_UV_CHECKPOINT_CHANGED')
    result = deepcopy(source)
    result['uv_channels'].extend(deepcopy(diagnostic))
    for field in ('marker_channel', 'vertex_control_point_indices', 'triangle_control_points'):
        result[field] = deepcopy(staged[field])
    return result


def edit_native_mesh(mesh):
    """An E1 edit on the disposable import; preserve the other users of shared data."""
    shared = mesh.data.users > 1
    if shared:
        original = mesh.data
        mesh.data = original.copy()
        need(mesh.data is not original, 'WORKING_MESH_COPY_FAILED')
        mesh.data['_vapb_fbx_mesh_session_uid'] = str(mesh.data.session_uid)
        mesh.data['_vapb_fbx_mesh_copy_evidence'] = 'OBSERVED_MEMBER_DEFORM_COPY'
    before_x = mesh.data.vertices[0].co.x
    mesh.data.vertices[0].co.x += 0.002
    mesh.data.update()
    return dict(working_mesh_made_single_user=shared, vertex_index=0, coordinate='LOCAL_X',
                before=before_x, after=mesh.data.vertices[0].co.x, delta_requested=0.002)


def capture(config, output):
    import bpy
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer.blender.identity_registry import load_scene_registry
    from unitypackage_blender_importer.blender.renderer_binding import validate_binding, validate_existing_binding
    from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
    from unitypackage_blender_importer.tests.blender_hierarchy_snapshot import snapshot
    from unitypackage_blender_importer.tests.blender_geometry_abcd import observe
    from unitypackage_blender_importer.tests.unity_hierarchy_probe.native_skin_observation import observe_native_skin
    from unitypackage_blender_importer.operators import export_unitypackage as exporter

    package = Path(config['input']).resolve()
    need(sha(package) == config['expected_sha256'], 'INPUT_HASH_MISMATCH')
    input_hashes = dict(config.get('input_hashes', {}), **{str(package): config['expected_sha256']})
    need(all(sha(path) == digest for path, digest in input_hashes.items()), 'INPUT_HASH_MISMATCH')
    need(config['mode'] in ('E0', 'E1'), 'EDIT_MODE_INVALID')
    addon.register()
    try:
        if config.get('input_blend'):
            need(bpy.ops.wm.open_mainfile(filepath=config['input_blend']) == {'FINISHED'}, 'OPEN_FAILED')
        else:
            from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
            from unitypackage_blender_importer.unity.asset_database import AssetDatabase
            with tempfile.TemporaryDirectory(dir=output) as temporary:
                extraction = UnityPackageReader(package).extract(Path(temporary))
                need(not extraction.errors, 'PACKAGE_EXTRACTION_FAILED')
                db = AssetDatabase.from_extraction(extraction.root, extraction.assets,
                                                  'sha256:' + config['expected_sha256'])
                root_asset = db.find_guid(config['selection']['root_guid'])
                need(root_asset is not None and root_asset.path in db.prefabs(), 'SELECTED_ROOT_MISSING')
                choice = 'PREFAB_' + str(db.prefabs().index(root_asset.path))
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            imported = bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode='RECONSTRUCT',
                prefab_choice=choice, model_witness_path=config['witness'], keep_extracted=True,
                source_storage_directory=str(output / 'Sources'), **config.get('import_options', {}))
            need(imported == {'FINISHED'}, 'IMPORT_CANCELLED')
        roots = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_renderer_occurrences')]
        records = [row for root in roots for row in read_projection(root)['records']]
        selected = select_record(records, config['selection'])
        occurrence = selected['occurrence_id']

        def subject():
            matches = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
                       and obj.get('_vapb_renderer_occurrence_id') == occurrence]
            need(len(matches) == 1, 'NATIVE_OCCURRENCE_NOT_UNIQUE')
            return matches[0]

        mesh = subject()
        need(not mesh.data.shape_keys, 'SHAPE_CAPTURE_SCOPE_UNSUPPORTED')
        check_model_material_scope(mesh)
        need(mesh.data.vertices and len(mesh.data.uv_layers) < 8, 'CP_MARKER_SCOPE_UNSUPPORTED')
        mesh.name = 'Campaign renamed exact occurrence'
        def other_geometry():
            return {obj: hashlib.sha256(json.dumps(observe(obj, obj.get('_vapb_fbx_geometry_uid', 'UNKNOWN')),
                sort_keys=True).encode()).hexdigest() for obj in bpy.context.scene.objects
                if obj.type == 'MESH' and obj is not mesh}

        mode_facts = dict(mode=config['mode'], working_mesh_made_single_user=False,
                          native_identity_revalidated_after_edit_save_reopen=False)
        other_before_edit = other_geometry()
        if config['mode'] == 'E1':
            mode_facts.update(edit_native_mesh(mesh))
        need(other_geometry() == other_before_edit, 'EDIT_CHANGED_OTHER_MESH_GEOMETRY')
        mode_facts.update(other_meshes_unchanged_after_edit=True, other_mesh_count=len(other_before_edit))
        write(output / 'ModeFactsPrivate.json', mode_facts)
        checkpoint = output / 'Checkpoint.blend'
        before_save = snapshot('', {}, {'FINISHED'})
        need(bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint)) == {'FINISHED'}, 'SAVE_FAILED')
        need(bpy.ops.wm.open_mainfile(filepath=str(checkpoint)) == {'FINISHED'}, 'REOPEN_FAILED')
        need(snapshot('', {}, {'FINISHED'}) == before_save, 'SAVE_REOPEN_GRAPH_CHANGED')
        mesh = subject()
        observation = observe_native_skin(bpy.context, package, config['witness'],
            config['source_observation'], config['package_observation'], config['control_report'],
            occurrence_id=occurrence)
        prior = select_proof(observation, occurrence)
        mode_facts['native_identity_revalidated_after_edit_save_reopen'] = True
        write(output / 'ModeFactsPrivate.json', mode_facts)
        write(output / 'NativeSkinObservationPrivate.json', observation)
        write(output / 'PriorSkinProofPrivate.json', prior)
        root, = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_renderer_occurrences')
                 and obj.get('_vapb_root_context_id') == mesh['_vapb_root_context_id']]
        record = select_record(read_projection(root)['records'], config['selection'])
        rigs = [modifier.object for modifier in mesh.modifiers if modifier.type == 'ARMATURE']
        need(len(rigs) == 1 and rigs[0] is not None, 'ARMATURE_NOT_UNIQUE')
        rig = rigs[0]
        existing = mesh.get('_vapb_renderer_binding')
        if existing:
            binding = validate_existing_binding(json.loads(existing), root, mesh, bpy.data.objects)
            binding_mode = 'EXPLICIT_CONFIRMED'
        else:
            binding = validate_binding(record, root, mesh, bpy.data.objects, rig)
            # This is an independently witnessed read-only capture link, not a confirmation mutation.
            binding['evidence'] = 'WITNESS_VALIDATED'
            binding_mode = 'AUTO_PROVEN'
        registry_package = load_scene_registry(bpy.context.scene).packages[mesh['unity_source_package_id']]
        source = Path(registry_package['source_archive_path'])
        need(sha(source) == config['expected_sha256'], 'STORED_SOURCE_HASH_MISMATCH')
        for obj in bpy.context.scene.objects:
            obj.select_set(False)
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        before = snapshot('', {}, {'FINISHED'})
        source_observed = observe(mesh, mesh['_vapb_fbx_geometry_uid'])
        other_before_export = other_geometry()
        source_local = dict(vertices=[list(vertex.co) for vertex in mesh.data.vertices],
                            loops=[loop.vertex_index for loop in mesh.data.loops])
        checkpoint_sha = sha(checkpoint)
        freeze = exporter.frozen_export_meshes
        failure_calls = []

        @contextmanager
        def fail_freeze(meshes):
            with freeze(meshes):
                failure_calls.append(1)
                raise RuntimeError('INJECTED_CAMPAIGN_EXPORT_FAILURE')
                yield

        failure = output / 'IntentionalFailure.unitypackage'
        with patch.object(exporter, 'frozen_export_meshes', fail_freeze):
            try:
                rejected = bpy.ops.export_scene.vapb_unitypackage(filepath=str(failure), export_scope='ACTIVE')
            except RuntimeError:
                rejected = {'CANCELLED'}
        need(rejected == {'CANCELLED'} and failure_calls == [1] and not failure.exists()
             and snapshot('', {}, {'FINISHED'}) == before
             and observe(mesh, mesh['_vapb_fbx_geometry_uid']) == source_observed,
             'FAILURE_ROLLBACK_UNPROVEN')
        need(other_geometry() == other_before_export, 'FAILURE_CHANGED_OTHER_MESH_GEOMETRY')
        captures = []
        capture_guard_failures = []

        @contextmanager
        def capture_freeze(meshes):
            staged, = meshes
            need(staged is not mesh and staged.data is not mesh.data, 'EXPORT_COPY_NOT_ISOLATED')
            channel = len(staged.data.uv_layers)
            marker = staged.data.uv_layers.new(name='VAPB_Diagnostic_CP')
            for loop in staged.data.loops:
                marker.data[loop.index].uv = (loop.vertex_index + 1, .375)
            measured = observe(staged, mesh['_vapb_fbx_geometry_uid'], channel, len(staged.data.vertices))
            staged_local = dict(vertices=[list(vertex.co) for vertex in staged.data.vertices],
                                loops=[loop.vertex_index for loop in staged.data.loops])
            write(output / 'ExportCheckpointComparison.json', dict(
                source=source_observed, staged=measured,
                source_local=source_local, staged_local=staged_local,
                local_data_equal=source_local == staged_local,
                positions_equal=measured['positions'] == source_observed['positions'],
                skin_weights_equal=measured['skin_weights'] == source_observed['skin_weights'],
                source_matrix_world=[list(row) for row in mesh.matrix_world],
                staged_matrix_world=[list(row) for row in staged.matrix_world],
                source_vertex_count=len(source_observed['positions']),
                staged_vertex_count=len(measured['positions'])))
            # Raw staged world/matrix differences remain separate evidence above.
            # The unchanged comparator receives the actual editing checkpoint positions/normals.
            try:
                checkpoint = checkpoint_with_transport(source_observed, measured, source_local, staged_local)
            except ValueError as error:
                capture_guard_failures.append(str(error))
                raise
            ids = {bone.name: str(bone['_vapb_fbx_bone_realization_id']) for bone in rig.data.bones
                   if bone.get('_vapb_fbx_bone_realization_id')}
            for weights in checkpoint['skin_weights']:
                for weight in weights:
                    weight['group'] = ids[weight['group']]
            captures.append(checkpoint)
            with freeze(meshes):
                yield

        exported = output / 'Output.unitypackage'
        with patch.object(exporter, 'frozen_export_meshes', capture_freeze):
            try:
                exported_result = bpy.ops.export_scene.vapb_unitypackage(filepath=str(exported), export_scope='ACTIVE')
            except RuntimeError:
                exported_result = {'CANCELLED'}
            need(exported_result == {'FINISHED'},
                 capture_guard_failures[-1] if capture_guard_failures else 'EXPORT_CANCELLED')
        need(len(captures) == 1 and snapshot('', {}, {'FINISHED'}) == before
             and observe(mesh, mesh['_vapb_fbx_geometry_uid']) == source_observed
             and other_geometry() == other_before_export
             and sha(checkpoint) == checkpoint_sha
             and all(sha(path) == digest for path, digest in input_hashes.items()), 'EXPORT_PRESERVATION_FAILED')
        assets = RawAssetRepository(exported).read_all()
        manifest = json.loads(next(asset.asset_bytes for asset in assets
                                  if asset.pathname == 'Assets/VAPBExport/manifest.json'))
        task, = manifest['reference_rebind_tasks']
        need(task['kind'] == 'RESTORE_DIRECT_SKIN_VARIANT_V1', 'TASK_CAPTURE_SCOPE_UNSUPPORTED')
        fbx = next(asset.asset_bytes for asset in assets if asset.guid == task['model_guid'])
        need(hashlib.sha256(fbx).hexdigest() == task['model_sha256'], 'GENERATED_FBX_HASH_MISMATCH')
        generated = output / 'Generated'
        generated.mkdir()
        (generated / 'D1.fbx').write_bytes(fbx)
        write(generated / 'ControlPointManifest.json', {'meshes': [{'uv_channel': captures[0]['marker_channel']}]})
        write(output / 'BoundedBlender.json', dict(package_sha256=config['expected_sha256'],
            renderer_binding=binding, binding_mode=binding_mode, prior_skin=prior, before=captures[0],
            hierarchy=before, material_ids=[dict(guid=str(slot.material.get('unity_material_guid', ''))
                if slot.material else None, slot=i) for i, slot in enumerate(mesh.material_slots)]))
        write(output / 'BoundedRecipe.json', dict(task=task, manifest=manifest, output_sha256=sha(exported)))
        write(output / 'InputLock.json', dict(expected_renderer_file_id=str(record['source_key']['renderer_file_id']),
            expected_owner_file_id=str(record['owner']['owner_game_object_id']), source_package_sha256=config['expected_sha256'],
            occurrence_id=occurrence, blender_capture_sha256=sha(output / 'BoundedBlender.json'),
            cp_channel=captures[0]['marker_channel'], output_sha256=sha(exported)))
        write(output / 'SourceLockPrivate.json', dict(blend_sha256=checkpoint_sha,
            source_archive_path=str(source), source_package_sha256=config['expected_sha256']))
        write(output / 'BoundedPreservation.json', dict(source_unchanged=True, rollback=True,
            rename_save_reopen=True, realization_id=task['realization_id'], fbx_sha256=task['model_sha256']))
        mode_facts['other_meshes_unchanged_after_export'] = True
        write(output / 'ModeFactsPrivate.json', mode_facts)
        return dict(verdict='UNPROVEN', reason='NONE', detail_code='EXPORT_CAPTURED_PENDING_UNITY',
                    scope='SELECTED_OCCURRENCE_EXPORT_CAPTURE_ONLY', binding_mode=binding_mode, mode=config['mode'])
    finally:
        addon.unregister()


def read_projection(root):
    return json.loads(root['_vapb_renderer_occurrences'])


def main():
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo.parent))
    from unitypackage_blender_importer.tests.blender_corpus_health import private_console
    context, result_path = map(Path, sys.argv[sys.argv.index('--') + 1:])
    config = read(context)
    output = Path(config['output_dir']).resolve()
    need(not output.exists() and not output.is_relative_to(repo), 'FRESH_EXTERNAL_OUTPUT_REQUIRED')
    need(result_path.resolve().is_relative_to(output), 'RESULT_OUTSIDE_PRIVATE_OUTPUT')
    output.mkdir(parents=True)
    with private_console(output / 'representative-console.log'):
        try:
            need('--factory-startup' in sys.argv, 'FACTORY_STARTUP_REQUIRED')
            report = capture(config, output)
        except Exception as error:
            import traceback
            traceback.print_exc()  # Private console only; do not emit source values in public summaries.
            report = capture_failure(error)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        write(result_path, report)
    print('CORPUS_REPRESENTATIVE verdict={} reason={}'.format(report['verdict'], report['reason']))
    if report['detail_code'] != 'EXPORT_CAPTURED_PENDING_UNITY':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
