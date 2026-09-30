"""Read-only Blender native Skin evidence, never a representation-equivalence verdict.

Callable observe_native_skin(context, package, witness, source_observation,
package_observation, control_report) reads exact external public evidence and
persisted normal-import occurrence records. It changes no identity or Scene data.
CLI: blender --background --python-exit-code 1 --python FILE --
BLEND PACKAGE WITNESS SOURCE_OBSERVATION PACKAGE_OBSERVATION CONTROL_REPORT OUTPUT [--check-rejections]
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _unique(rows, key, code):
    result = {}
    for row in rows:
        identity = key(row)
        _require(identity not in result, code)
        result[identity] = row
    return result


def observe_native_skin(context, package, witness, source_observation,
                        package_observation, control_report, *, pose_controls=False):
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
    from unitypackage_blender_importer.unity.asset_database import AssetDatabase
    from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
    from unitypackage_blender_importer.unity.model_identity_witness import load_model_witness
    from unitypackage_blender_importer.blender.model_witness_bridge import plan_witness_realizations
    from unitypackage_blender_importer.blender.fbx_receipt import make_bone_receipt, RECEIPT_VERSION
    from unitypackage_blender_importer.blender.fbx_witness import source_skin_bone_uids

    package = Path(package)
    package_sha = _sha(package)
    source = _read(source_observation)
    public = _read(package_observation)
    controls = _read(control_report)
    # ExactPackage is the immutable input to the separate public API observation.
    _require(_sha(Path(package_observation).parent / 'ExactPackage.unitypackage') == package_sha,
             'PACKAGE_OBSERVATION_REVISION_MISMATCH')
    flags = ('pass', 'noopEquivalent', 'witnessEquivalent', 'restoredEquivalent',
             'metaStable', 'callbackExactlyOnce', 'markerIdentityUnique',
             'allSkinBonesMarked', 'sourceMetaRestored', 'sourceRawRestored',
             'originalRevisionEquivalent', 'mappingWritten')
    _require(controls.get('error') == 'NONE' and all(controls.get(k) is True for k in flags),
             'SOURCE_CONTROL_REPORT_NOT_PASS')
    _require(source.get('schema_version') == 'vapb-hierarchy-bone-public-api-observation-1'
             and source.get('unity_version') == public.get('unity_version') == '2022.3.22f1',
             'OBSERVATION_SCHEMA_OR_VERSION_MISMATCH')
    _require(public.get('status') == 'OBSERVED_PUBLIC_API', 'PACKAGE_OBSERVATION_UNKNOWN')
    source_rows = _unique(source['skinned_renderers'],
        lambda r: (source['model_guid'], int(r['mesh_local_id'])), 'SOURCE_SKIN_AMBIGUOUS')
    public_rows = _unique(public['skinned_renderers'],
        lambda r: (r['renderer']['guid'], int(r['renderer']['local_id'])), 'PREFAB_SKIN_AMBIGUOUS')
    objects = tuple(context.scene.objects)
    handles = {obj: index for index, obj in enumerate(objects)}
    roots = [obj for obj in objects if obj.get('_vapb_renderer_occurrences') is not None]
    _require(len(roots) == 1, 'ROOT_OCCURRENCE_SCOPE_AMBIGUOUS')
    root = roots[0]
    _require(root.get('_vapb_witness_package_sha256') == package_sha, 'PERSISTED_WITNESS_REVISION_MISMATCH')
    persisted = root['_vapb_renderer_occurrences']
    projection = json.loads(persisted) if isinstance(persisted, str) else persisted
    _require(not projection.get('issues'), 'PERSISTED_PROJECTION_HAS_ISSUES')
    records = [r for r in projection['records'] if r.get('renderer_class_id') == 137]
    _require(records and all(r['root_package_id'] == 'sha256:' + package_sha for r in records),
             'PERSISTED_PACKAGE_REVISION_MISMATCH')
    frame_oracle = None
    if any(bone.get('local_to_world_matrix', bone.get('world_matrix')) is not None
        for row in source['skinned_renderers'] for bone in row['ordered_bones']):
        oracle_path = Path(package_observation).parent / 'unity_oracle.json'
        _require(oracle_path.is_file(), 'PREFAB_FULL_FRAME_ORACLE_MISSING')
        frame_oracle = _unique(_read(oracle_path)['nodes'], lambda node: node['transform']['globalId'],
            'PREFAB_FRAME_IDENTITY_AMBIGUOUS')
    context.view_layer.update()
    skins = []
    pose_control_cache = {}
    with tempfile.TemporaryDirectory(prefix='vapb_native_skin_read_') as temp:
        extraction = UnityPackageReader(package).extract(Path(temp))
        _require(not extraction.errors, 'PACKAGE_EXTRACTION_FAILED')
        db = AssetDatabase.from_extraction(extraction.root, extraction.assets, 'sha256:' + package_sha)
        validated = load_model_witness(Path(witness), package_sha, db)
        bindings, issues = plan_witness_realizations(records, objects, validated)
        _require(not issues and len(bindings) == len(records), 'NATIVE_WITNESS_JOIN_REJECTED')
        for record, mesh in bindings:
            mesh_key = (record['mesh']['mesh_guid'], int(record['mesh']['mesh_file_id']))
            expected = source_rows.get(mesh_key)
            _require(expected is not None, 'SOURCE_SKIN_MISSING')
            witness_row = validated.mesh(*mesh_key)
            _require(str(witness_row.model_uid) == str(expected['renderer_model_uid'])
                     and witness_row.renderer_local_id == int(expected['renderer_local_id']),
                     'SOURCE_RENDERER_WITNESS_MISMATCH')
            asset = db.find_guid(mesh_key[0])
            _require(_sha(asset.path) == source['source_fbx_sha256'] == record['mesh']['source_sha256']
                     and _sha(Path(str(asset.path) + '.meta')) == source['source_meta_sha256'],
                     'SOURCE_OBSERVATION_REVISION_MISMATCH')
            key = record['source_key']
            _require(key['source_kind'] == 'PREFAB_LOCAL', 'PREFAB_SKIN_ROUTE_UNSUPPORTED')
            authored = public_rows.get((key['source_asset_guid'], int(key['renderer_file_id'])))
            _require(authored is not None and (authored['mesh']['guid'], int(authored['mesh']['local_id'])) == mesh_key,
                     'PREFAB_RENDERER_MESH_IDENTITY_MISMATCH')
            prefab_entry = db.find_guid(key['source_asset_guid'])
            prefab = parse_prefab(prefab_entry.path)

            def carrier_for_transform(transform_id):
                transform = prefab.transforms.get(int(transform_id))
                _require(transform is not None, 'AUTHORED_TRANSFORM_MISSING')
                candidates = [obj for obj in objects if obj.get('_vapb_semantic_id')
                    and obj.get('unity_source_package_id') == 'sha256:' + package_sha
                    and obj.get('unity_asset_path') == prefab_entry.unity_path
                    and str(obj.get('unity_prefab_file_id', '')) == str(transform.game_object_id)]
                _require(len(candidates) == 1, 'SEMANTIC_CARRIER_AMBIGUOUS_OR_MISSING')
                return candidates[0]

            semantic_owner = carrier_for_transform(authored['owner']['local_id'])
            _require(int(prefab.transforms[int(authored['owner']['local_id'])].game_object_id)
                == int(record['owner']['owner_game_object_id']), 'RENDERER_OWNER_IDENTITY_MISMATCH')
            serialized = record.get('skin', {})
            source_bones, slots = expected['ordered_bones'], authored['ordered_bones']
            _require(serialized.get('status') == 'EXACT' and len(source_bones) == len(slots)
                     == len(serialized['bones']) == expected['bindpose_count'] == authored['bindpose_count'],
                     'SKIN_SLOT_COUNT_MISMATCH')
            _require([str(b['transform_file_id']) for b in serialized['bones']]
                     == [b['transform']['local_id'] for b in slots]
                     and str(serialized['root_bone_transform_file_id']) == authored['root_bone']['transform']['local_id'],
                     'AUTHORED_SKIN_BINDING_MISMATCH')
            ordered_uids = [str(b['model_uid']) for b in source_bones]
            _require(len(set(ordered_uids)) == len(ordered_uids), 'SOURCE_BONE_UID_DUPLICATE')
            members = source_skin_bone_uids(asset.path, witness_row.model_uid, witness_row.geometry_uid)
            _require(set(ordered_uids) == members, 'SOURCE_SKIN_MEMBERSHIP_MISMATCH')
            modifiers = [m for m in mesh.modifiers if m.type == 'ARMATURE']
            _require(len(modifiers) == 1 and modifiers[0].object is not None
                     and modifiers[0].object.type == 'ARMATURE', 'ACTUAL_ARMATURE_TARGET_AMBIGUOUS')
            rig = modifiers[0].object
            _require(rig.get('_vapb_root_context_id') == record['root_context_id']
                and rig.get('_vapb_native_object_id') and sum(1 for obj in objects
                    if obj.get('_vapb_native_object_id') == rig['_vapb_native_object_id']) == 1,
                'ACTUAL_ARMATURE_OCCURRENCE_MISMATCH')
            bone_rows = _unique(rig.data.bones,
                lambda b: str(b.get('_vapb_fbx_model_uid', '')), 'ACTUAL_BONE_UID_DUPLICATE')
            observed_bones = []
            control_targets = []
            for slot, uid in enumerate(ordered_uids):
                bone = bone_rows.get(uid)
                _require(bone is not None, 'ACTUAL_BONE_RECEIPT_MISSING')
                receipt = make_bone_receipt(int(uid), mesh_key[0], source['source_fbx_sha256'])
                _require(bone.get('_vapb_fbx_receipt_version') == RECEIPT_VERSION
                         and bone.get('_vapb_fbx_source_asset_guid') == receipt.source_asset_guid
                         and bone.get('_vapb_fbx_source_asset_sha256') == receipt.source_asset_sha256
                         and bone.get('_vapb_fbx_bone_receipt_id') == receipt.blender_bone_receipt_id
                         and bone.get('_vapb_fbx_receipt_evidence') == receipt.evidence
                         and bone.get('_vapb_fbx_bone_realization_id'), 'ACTUAL_BONE_RECEIPT_INVALID')
                pose = rig.pose.bones.get(bone.name)  # Native data-to-pose API handle, not cross-runtime identity.
                _require(pose is not None, 'ACTUAL_POSE_BONE_MISSING')
                carrier = carrier_for_transform(slots[slot]['transform']['local_id'])
                carrier_constraints, actual_carrier_uid = _carrier_constraints(carrier, rig, handles)
                control_targets.append((uid, pose, carrier))
                parent_uid = str(bone.parent.get('_vapb_fbx_model_uid', 'UNKNOWN')) if bone.parent else None
                observed_bones.append(dict(slot=slot, model_uid=uid,
                    prefab_transform=slots[slot]['transform'], source_transform_local_id=source_bones[slot]['transform_local_id'],
                    semantic_carrier_handle=handles[carrier], carrier_constraints=carrier_constraints,
                    actual_carrier_uid=actual_carrier_uid, carrier_constraint_valid=actual_carrier_uid == uid,
                    bone_parent_valid=parent_uid == source_bones[slot]['parent_model_uid'] if source_bones[slot]['parent_model_uid'] in members else parent_uid is None,
                    actual_parent_uid=parent_uid, expected_source_parent_uid=source_bones[slot]['parent_model_uid'],
                    rest_head_world=list(rig.matrix_world @ bone.head_local),
                    evaluated_head_world=list(rig.matrix_world @ pose.head),
                    source_unity_world_origin=source_bones[slot]['world_origin'],
                    prefab_unity_world_origin=slots[slot]['world_origin'],
                    bone_realization_id=bone['_vapb_fbx_bone_realization_id']))
                source_matrix = source_bones[slot].get('local_to_world_matrix', source_bones[slot].get('world_matrix'))
                if source_matrix is not None:
                    from mathutils import Matrix
                    node = frame_oracle.get(slots[slot]['transform']['global_id'])
                    _require(node is not None, 'PREFAB_FULL_FRAME_IDENTITY_MISSING')
                    basis = Matrix(((-1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
                    def converted(values):
                        _require(len(values) == 16, 'FULL_FRAME_MATRIX_INVALID')
                        matrix = Matrix(tuple(tuple(values[i+4*j] for j in range(4)) for i in range(4)))
                        return basis @ matrix @ basis.inverted()
                    native_rest = rig.matrix_world @ bone.matrix_local
                    expected_native = converted(node['worldMatrix']) @ converted(source_matrix).inverted() @ native_rest
                    evaluated_native = rig.matrix_world @ pose.matrix
                    observed_bones[-1].update(dict(native_rest_world_matrix=[list(row) for row in native_rest],
                        evaluated_native_world_matrix=[list(row) for row in evaluated_native],
                        expected_native_world_matrix=[list(row) for row in expected_native],
                        native_pose_frame_max_matrix_error=_matrix_error(evaluated_native, expected_native)))
            root_slots = [index for index, slot in enumerate(slots)
                          if slot['transform'] == authored['root_bone']['transform']]
            _require(len(root_slots) <= 1, 'ROOT_BONE_AUTHORED_BINDING_AMBIGUOUS')
            root_carrier = carrier_for_transform(authored['root_bone']['transform']['local_id'])
            root_uid = ordered_uids[root_slots[0]] if root_slots else None
            root_representation = 'BONE_CARRIER' if root_slots else 'ROOT_FRAME_OBJECT'
            if not root_slots:
                _require(str(mesh.get('_vapb_skin_root_transform_file_id', ''))
                    == authored['root_bone']['transform']['local_id']
                    and mesh.get('_vapb_skin_root_frame_semantic_id') == root_carrier['_vapb_semantic_id'],
                    'ACTUAL_ROOT_FRAME_BINDING_MISMATCH')
            source_default_root_uid = str(expected['root_bone']['model_uid'])
            controls = _pose_controls(context, rig, control_targets, objects, handles, pose_control_cache) if pose_controls else []
            controls_by_uid = {control['model_uid']: control for control in controls}
            for bone_row in observed_bones:
                control = controls_by_uid.get(bone_row['model_uid'])
                bone_row['pose_delta_pass'] = bool(control and control['carrier_delta_matches'] and control['restored'])
            evaluated = mesh.evaluated_get(context.evaluated_depsgraph_get())
            geometry = evaluated.to_mesh()
            try:
                vertices = [list(evaluated.matrix_world @ vertex.co) for vertex in geometry.vertices]
                geometry.calc_loop_triangles()
                triangle_corners = [vertices[index] for triangle in geometry.loop_triangles for index in triangle.vertices]
            finally:
                evaluated.to_mesh_clear()
            skins.append(dict(occurrence_id=record['occurrence_id'], mesh_handle=handles[mesh],
                armature_handle=handles.get(rig), mesh_guid=mesh_key[0], mesh_local_id=str(mesh_key[1]),
                renderer_model_uid=str(witness_row.model_uid), root_bone_model_uid=root_uid,
                source_default_root_bone_model_uid=source_default_root_uid,
                renderer=authored['renderer'], owner_transform=authored['owner'],
                renderer_identity=authored['renderer'], owner_transform_identity=authored['owner'],
                semantic_owner_handle=handles[semantic_owner], renderer_owner_valid=mesh.parent == semantic_owner,
                actual_mesh_parent_handle=handles.get(mesh.parent),
                actual_armature_parent_handle=handles.get(rig.parent),
                root_bone_semantic_carrier_handle=handles[root_carrier],
                root_bone_carrier_handle=handles[root_carrier], root_representation=root_representation,
                root_transform_identity=authored['root_bone']['transform'], root_frame_binding_valid=True,
                root_bone_actual_carrier_uid=observed_bones[root_slots[0]]['actual_carrier_uid'] if root_slots else None,
                pose_controls=controls,
                bones=observed_bones, evaluated_world_vertices=vertices,
                evaluated_world_triangle_corners=triangle_corners,
                prefab_unity_world_triangle_corners=authored.get('baked_world_triangle_corners'),
                source_unity_baked_world_vertices=expected['baked_world_vertices'],
                prefab_unity_baked_world_vertices=authored['baked_world_vertices']))
    carriers = []
    for obj in objects:
        if not obj.get('_vapb_semantic_id'):
            continue
        parent_bone_uid = None
        if obj.parent is not None and obj.parent_type == 'BONE':
            bone = obj.parent.data.bones.get(obj.parent_bone)
            parent_bone_uid = str(bone.get('_vapb_fbx_model_uid', 'UNKNOWN')) if bone is not None else 'UNKNOWN'
        carriers.append(dict(handle=handles[obj], semantic_id=obj['_vapb_semantic_id'],
            actual_parent_handle=handles.get(obj.parent), actual_parent_semantic_id=obj.parent.get('_vapb_semantic_id') if obj.parent else None,
            parent_type=obj.parent_type, parent_bone_model_uid=parent_bone_uid,
            world_matrix=[list(row) for row in obj.matrix_world], local_matrix=[list(row) for row in obj.matrix_local],
            constraints=_constraint_rows(obj, handles)))
    return dict(schema_version='vapb-native-skin-observation-1', status='OBSERVED_NOT_COMPARED',
                package_sha256=package_sha, source_validated=True, source_control_report_pass=True,
                unique_native_pose_control_count=len(pose_control_cache),
                skins=skins, semantic_carriers=carriers)



def _constraint_rows(obj, handles):
    return [dict(type=c.type, target_handle=handles.get(getattr(c, 'target', None)),
        subtarget=getattr(c, 'subtarget', ''), influence=c.influence, mute=c.mute,
        owner_space=getattr(c, 'owner_space', None), target_space=getattr(c, 'target_space', None),
        inverse_matrix=[list(row) for row in c.inverse_matrix] if c.type == 'CHILD_OF' else None)
        for c in obj.constraints]


def _carrier_constraints(carrier, rig, handles):
    rows = _constraint_rows(carrier, handles)
    resolved = []
    for constraint in carrier.constraints:
        proxy = getattr(constraint, 'target', None)
        if constraint.type != 'COPY_TRANSFORMS' or proxy is None or constraint.mute or constraint.influence != 1:
            continue
        for target in proxy.constraints:
            if target.type != 'CHILD_OF' or target.target != rig or target.mute or target.influence != 1:
                continue
            bone = rig.data.bones.get(target.subtarget)
            if bone is not None and bone.get('_vapb_fbx_model_uid'):
                resolved.append(str(bone['_vapb_fbx_model_uid']))
                rows.append(dict(proxy_handle=handles.get(proxy), proxy_constraints=_constraint_rows(proxy, handles),
                    actual_armature_handle=handles.get(rig), target_bone_uid=str(bone['_vapb_fbx_model_uid'])))
    return rows, resolved[0] if len(resolved) == 1 else 'UNKNOWN'


def _matrix_error(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))


def _pose_controls(context, rig, targets, objects, handles, cache=None):
    from mathutils import Matrix
    controls = []
    cache = {} if cache is None else cache
    for uid, pose, carrier in targets:
        cache_key = (str(rig['_vapb_native_object_id']), str(pose.bone['_vapb_fbx_bone_realization_id']), handles[carrier])
        if cache_key in cache:
            controls.append(cache[cache_key])
            continue
        context.view_layer.update()
        saved_basis = pose.matrix_basis.copy()
        saved_world = {obj: obj.matrix_world.copy() for obj in objects}
        before_bone_world = rig.matrix_world @ pose.matrix
        descendants = []
        for obj in objects:
            if not obj.get('_vapb_semantic_id'):
                continue
            parent = obj
            seen = set()
            while parent is not None and parent not in seen:
                if parent == carrier:
                    descendants.append(obj)
                    break
                seen.add(parent)
                parent = parent.parent
        try:
            pose.matrix_basis = saved_basis @ Matrix.Rotation(0.21, 4, 'Y')
            context.view_layer.update()
            delta = (rig.matrix_world @ pose.matrix) @ before_bone_world.inverted()
            errors = [dict(handle=handles[obj], max_world_matrix_error=_matrix_error(obj.matrix_world, delta @ saved_world[obj]),
                actual_world_displacement=list(obj.matrix_world.translation - saved_world[obj].translation))
                for obj in descendants]
            control = dict(model_uid=uid, carrier_handle=handles[carrier], axis='NATIVE_LOCAL_Y', angle_radians=0.21,
                carrier_and_descendant_count=len(descendants), world_delta=[list(row) for row in delta],
                carrier_and_descendant_errors=errors,
                native_motion_executed=_matrix_error(delta, Matrix.Identity(4)) > 0.01,
                carrier_delta_matches=_matrix_error(delta, Matrix.Identity(4)) > 0.01 and bool(errors)
                    and all(row['max_world_matrix_error'] <= 2e-5 for row in errors))
        finally:
            pose.matrix_basis = saved_basis
            context.view_layer.update()
            restore_error = max([_matrix_error(obj.matrix_world, saved_world[obj]) for obj in objects] +
                [_matrix_error(pose.matrix_basis, saved_basis)])
        control['restored'] = restore_error <= 2e-5
        control['max_restore_matrix_error'] = restore_error
        cache[cache_key] = control
        controls.append(control)
    return controls


def main():
    import bpy
    args = sys.argv[sys.argv.index('--') + 1:]
    checks = '--check-rejections' in args
    pose_controls = '--pose-controls' in args
    args = [arg for arg in args if arg not in ('--check-rejections', '--pose-controls')]
    blend, package, witness, source, public, controls, output = args
    output = Path(output)
    _require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
    observation = observe_native_skin(bpy.context, package, witness, source, public, controls, pose_controls=pose_controls)
    output.write_text(json.dumps(observation, indent=2), encoding='utf-8')
    print('NATIVE_SKIN_OBSERVATION_WRITTEN skins=' + str(len(observation['skins'])))
    if checks:
        with tempfile.TemporaryDirectory(prefix='vapb_native_skin_rejection_') as folder:
            original = _read(source)
            cases = []
            duplicate = json.loads(json.dumps(original))
            duplicate['skinned_renderers'].append(duplicate['skinned_renderers'][0])
            cases.append((duplicate, 'SOURCE_SKIN_AMBIGUOUS'))
            wrong_revision = json.loads(json.dumps(original))
            wrong_revision['source_fbx_sha256'] = '0' * 64
            cases.append((wrong_revision, 'SOURCE_OBSERVATION_REVISION_MISMATCH'))
            for index, (document, expected) in enumerate(cases):
                changed = Path(folder) / ('source_' + str(index) + '.json')
                changed.write_text(json.dumps(document), encoding='utf-8')
                try:
                    observe_native_skin(bpy.context, package, witness, changed, public, controls)
                except ValueError as error:
                    _require(str(error) == expected, 'UNEXPECTED_REJECTION_REASON')
                else:
                    raise ValueError('INVALID_OBSERVATION_ACCEPTED')
        print('NATIVE_SKIN_REJECTION_CHECKS_PASS count=2')


if __name__ == '__main__':
    main()
