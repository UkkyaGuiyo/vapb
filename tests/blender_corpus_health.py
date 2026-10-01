"""Observe one ordinary VAPB import; private evidence never becomes a fixture.

Blender --factory-startup --background --python-exit-code 1 --python SCRIPT
    -- CONTEXT_JSON RESULT_JSON
Context: input, expected_sha256, optional case_dir, prefab_choice (AUTO),
model_witness_path and import_options. All outputs must be inside case_dir,
outside the repository. Run each importer composition/root token as a separate
job. This adapter does not invent selections or Renderer-to-Mesh bindings.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


class HealthError(RuntimeError):
    pass


def _require(condition, reason):
    if not condition:
        raise HealthError(reason)


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@contextmanager
def private_console(path):
    """Confine Python and native importer output to private evidence."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(fd) for fd in (1, 2)]
    with path.open('w', encoding='utf-8') as output:
        try:
            for fd in (1, 2):
                os.dup2(output.fileno(), fd)
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for fd, original in zip((1, 2), saved):
                os.dup2(original, fd)
                os.close(original)


def _metadata(block):
    if block is None:
        return {}
    return {key: str(block[key]) for key in sorted(block.keys())
            if key.startswith(('_vapb_', 'unity_')) and not key.endswith('_session_uid')}


def observe(bpy):
    from unitypackage_blender_importer.blender.fbx_receipt import RECEIPT_VERSION
    from unitypackage_blender_importer.blender.renderer_binding import (
        semantic_owner_id, validate_existing_binding)
    from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity
    from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome

    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    rigs = [obj for obj in objects if obj.type == 'ARMATURE']
    roots = [obj for obj in objects if obj.get('_vapb_renderer_occurrences') is not None]
    occurrences, projection_issues = [], []
    for root in roots:
        try:
            projection = json.loads(root['_vapb_renderer_occurrences'])
            records = projection['records']
            _require(isinstance(records, list), 'PROJECTION_MALFORMED')
            projection_issues.extend(projection.get('issues', []))
        except (ValueError, KeyError, TypeError):
            projection_issues.append({'code': 'PROJECTION_MALFORMED'})
            continue
        for record in records:
            row = {'occurrence_id': record.get('occurrence_id', ''),
                   'renderer_class_id': record.get('renderer_class_id'),
                   'identity': 'UNKNOWN', 'semantic_owner_count': 0,
                   'receipt_scope_candidates': 0, 'binding': 'UNKNOWN',
                   'binding_reason': 'INDEPENDENT_BINDING_NOT_PROVIDED',
                   'skin_projection': record.get('skin', {}).get('status', 'UNKNOWN')}
            try:
                row['identity'] = ('PASS' if record['occurrence_id'] == occurrence_identity(record)
                                   and record['root_context_id'] == root.get('_vapb_root_context_id')
                                   else 'FAIL')
                owner_id = semantic_owner_id(record)
                row['semantic_owner_count'] = sum(obj.get('_vapb_semantic_owner_id') == owner_id
                                                  for obj in objects)
            except (KeyError, TypeError, ValueError):
                row['identity'] = 'INCOMPLETE'
            mesh = record.get('mesh', {})
            row['mesh_metadata_complete'] = all(mesh.get(key) for key in
                ('source_package_id', 'mesh_guid', 'mesh_file_id', 'source_sha256'))
            # Scope candidates are diagnostics only, even when their count is 1.
            if all(mesh.get(key) for key in ('source_package_id', 'mesh_guid', 'source_sha256')):
                row['receipt_scope_candidates'] = sum(
                    obj.get('_vapb_root_context_id') == record.get('root_context_id')
                    and obj.get('unity_source_package_id') == mesh['source_package_id']
                    and str(obj.get('_vapb_fbx_source_asset_guid', '')).lower() == mesh['mesh_guid'].lower()
                    and str(obj.get('_vapb_fbx_source_asset_sha256', '')).lower() == mesh['source_sha256'].lower()
                    and bool(obj.get('_vapb_fbx_realization_id')) for obj in meshes)
            linked = []
            for obj in meshes:
                raw = obj.get('_vapb_renderer_binding')
                if not raw:
                    continue
                try:
                    binding = json.loads(raw)
                    if binding.get('occurrence_id') == row['occurrence_id']:
                        linked.append((obj, binding))
                except (TypeError, ValueError):
                    pass
            if linked:
                row['binding'] = 'FAIL'
                row['binding_reason'] = 'EXISTING_BINDING_INVALID'
                if len(linked) == 1:
                    try:
                        validate_existing_binding(linked[0][1], root, linked[0][0], objects)
                        row['binding'] = 'PASS'
                        row['binding_reason'] = 'EXISTING_BINDING_VALIDATED'
                    except ValueError:
                        pass
            occurrences.append(row)

    receipt_rows = []
    for obj in meshes:
        keys = ('_vapb_fbx_source_asset_guid', '_vapb_fbx_source_asset_sha256',
                '_vapb_fbx_model_uid', '_vapb_fbx_geometry_uid',
                '_vapb_fbx_object_receipt_id', '_vapb_fbx_mesh_receipt_id',
                '_vapb_fbx_realization_id', '_vapb_fbx_receipt_evidence')
        missing = [key for key in keys if not obj.get(key)]
        paired = all(obj.get(key) == obj.data.get(key) and bool(obj.get(key))
                     for key in ('_vapb_fbx_source_asset_sha256', '_vapb_fbx_geometry_uid',
                                 '_vapb_fbx_mesh_receipt_id'))
        complete = (not missing and paired and
                    obj.get('_vapb_fbx_receipt_version') == RECEIPT_VERSION and
                    obj.data.get('_vapb_fbx_receipt_version') == RECEIPT_VERSION)
        receipt_rows.append({'realization_id': obj.get('_vapb_fbx_realization_id', ''),
                             'metadata_complete': complete, 'missing_keys': missing,
                             'datablock_agrees': paired})
    counts = dict(objects=len(objects), meshes=len(meshes), armatures=len(rigs),
                  mesh_datablocks=len({obj.data.as_pointer() for obj in meshes}),
                  vertices=sum(len(obj.data.vertices) for obj in meshes),
                  bones=sum(len(obj.data.bones) for obj in rigs),
                  observed_skin_meshes=sum(any(mod.type == 'ARMATURE' and mod.object is not None
                                               for mod in obj.modifiers) for obj in meshes),
                  material_slots=sum(len(obj.material_slots) for obj in meshes),
                  empty_material_slots=sum(slot.material is None for obj in meshes for slot in obj.material_slots),
                  shape_key_meshes=sum(bool(obj.data.shape_keys) for obj in meshes),
                  shape_channels=sum(max(0, len(obj.data.shape_keys.key_blocks) - 1)
                                     if obj.data.shape_keys else 0 for obj in meshes),
                  roots=len(roots), renderer_occurrences=len(occurrences),
                  receipt_metadata_complete=sum(row['metadata_complete'] for row in receipt_rows))
    # Names here compare unedited serialization only; they never select source identity.
    state = {'scene': _metadata(bpy.context.scene), 'objects': []}
    for obj in sorted(objects, key=lambda item: item.name):
        state['objects'].append(dict(name=obj.name, type=obj.type,
            parent=obj.parent.name if obj.parent else None,
            metadata=_metadata(obj), data_metadata=_metadata(obj.data),
            matrix=[list(row) for row in obj.matrix_local],
            materials=[(slot.material.name, _metadata(slot.material)) if slot.material else None
                       for slot in obj.material_slots] if obj.type == 'MESH' else [],
            shapes=_metadata(obj.data.shape_keys) if obj.type == 'MESH' and obj.data.shape_keys else {},
            bones=[(bone.name, bone.parent.name if bone.parent else None, _metadata(bone))
                   for bone in obj.data.bones] if obj.type == 'ARMATURE' else []))
    return state, dict(counts=counts, occurrences=occurrences, receipts=receipt_rows,
                       projection_issues=projection_issues,
                       import_outcome=scene_import_outcome(bpy.context.scene))


def main():
    context_path, result_arg = sys.argv[sys.argv.index('--') + 1:]
    config = json.loads(Path(context_path).read_text(encoding='utf-8-sig'))
    case = Path(config.get('case_dir', Path(context_path).parent)).resolve()
    result_path = Path(result_arg).resolve()
    repo = Path(__file__).resolve().parents[1]
    _require(not case.is_relative_to(repo), 'EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED')
    _require(result_path.is_relative_to(case), 'RESULT_OUTSIDE_CASE')
    case.mkdir(parents=True, exist_ok=True)
    _require(not result_path.exists(), 'OUTPUT_ALREADY_EXISTS')
    report = dict(schema='vapb-corpus-health-1', verdict='FAIL', reason='NOT_RUN',
                  import_status='NOT_RUN', save_reopen='NOT_RUN', source_unchanged=None,
                  source_skin_count='UNKNOWN', source_skin_reason='INDEPENDENT_ORACLE_NOT_RUN')
    registered, error = False, None
    with private_console(case / 'health-console.log'):
        try:
            import bpy
            sys.path.insert(0, str(repo.parent))
            import unitypackage_blender_importer as addon
            report['blender_version'] = bpy.app.version_string
            _require('--factory-startup' in sys.argv, 'FACTORY_STARTUP_REQUIRED')
            source = Path(config['input']).resolve()
            before_hash = _sha(source)
            _require(before_hash == config['expected_sha256'], 'SOURCE_HASH_MISMATCH')
            options = config.get('import_options', {})
            permitted = {'use_armatures', 'use_bone_weights', 'use_shape_keys',
                         'use_materials', 'use_textures', 'apply_prefab_transforms'}
            _require(isinstance(options, dict) and set(options) <= permitted
                     and all(type(value) is bool for value in options.values()), 'IMPORT_OPTIONS_INVALID')
            temp = case / 'Temp'
            temp.mkdir(exist_ok=True)
            tempfile.tempdir = str(temp)
            saved = case / 'Health.blend'
            _require(not saved.exists(), 'OUTPUT_ALREADY_EXISTS')
            addon.register()
            registered = True
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            report['reason'] = 'IMPORT_FAILED'
            imported = bpy.ops.import_scene.unitypackage(filepath=str(source),
                import_mode='RECONSTRUCT', prefab_choice=config.get('prefab_choice', 'AUTO'),
                model_witness_path=config.get('model_witness_path', ''), keep_extracted=True,
                source_storage_directory=str(case / 'Sources'), **options)
            report['import_status'] = 'PASS' if imported == {'FINISHED'} else 'CANCELLED'
            _require(imported == {'FINISHED'}, 'IMPORT_CANCELLED')
            report['reason'] = 'OBSERVATION_FAILED'
            before_state, observations = observe(bpy)
            report.update(observations)
            report['reason'] = 'SAVE_REOPEN_FAILED'
            report['save_reopen'] = 'FAIL'
            _require(bpy.ops.wm.save_as_mainfile(filepath=str(saved)) == {'FINISHED'} and saved.is_file(), 'SAVE_FAILED')
            _require(bpy.ops.wm.open_mainfile(filepath=str(saved)) == {'FINISHED'}, 'REOPEN_FAILED')
            after_state, after = observe(bpy)
            _require(before_state == after_state and observations == after, 'SAVE_REOPEN_SEMANTICS_CHANGED')
            report['save_reopen'] = 'PASS'
            report['semantic_state_sha256'] = hashlib.sha256(json.dumps(before_state, sort_keys=True).encode()).hexdigest()
            report['source_unchanged'] = _sha(source) == before_hash
            _require(report['source_unchanged'], 'SOURCE_CHANGED')
            report['verdict'] = 'PASS'
            report['reason'] = 'HEALTH_OBSERVATION_COMPLETE'
        except Exception as exc:
            error = exc
            report['error_type'] = type(exc).__name__
            if isinstance(exc, HealthError):
                report['reason'] = str(exc)
            if report['import_status'] == 'NOT_RUN':
                report['import_status'] = 'FAIL'
        finally:
            if 'before_hash' in locals():
                try:
                    report['source_unchanged'] = _sha(source) == before_hash
                except OSError:
                    report['source_unchanged'] = None
                if report['source_unchanged'] is not True:
                    error = HealthError('SOURCE_INTEGRITY_UNVERIFIED')
                    report.update(verdict='FAIL', reason='SOURCE_INTEGRITY_UNVERIFIED')
            if registered:
                try:
                    addon.unregister()
                except Exception:
                    if error is None:
                        error = HealthError('UNREGISTER_FAILED')
                        report.update(verdict='FAIL', reason='UNREGISTER_FAILED')
            report['scope'] = 'HEALTH_OBSERVATION_ONLY_NOT_ROUNDTRIP'
            report['detail_code'] = report['reason']
            if error is None:
                report['reason'] = 'NONE'
            else:
                report['verdict'] = 'BLOCKED' if report['import_status'] != 'PASS' else 'UNPROVEN'
                report['reason'] = 'HARNESS_UNSUPPORTED' if report['import_status'] != 'PASS' else 'HARNESS_ERROR'
            result_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding='utf-8')
    counts = report.get('counts', {})
    print('CORPUS_HEALTH verdict={} reason={} meshes={} skins={} roots={} occurrences={}'.format(
        report['verdict'], report['reason'], counts.get('meshes', 'UNKNOWN'),
        counts.get('observed_skin_meshes', 'UNKNOWN'), counts.get('roots', 'UNKNOWN'),
        counts.get('renderer_occurrences', 'UNKNOWN')), flush=True)
    if error is not None:
        raise HealthError(report['detail_code']) from None


if __name__ == '__main__':
    main()
