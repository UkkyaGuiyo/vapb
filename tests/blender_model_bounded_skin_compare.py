# SPDX-License-Identifier: GPL-3.0-or-later
"""External model-route capture join. Private subjects stay in external reports.

Run inside Blender: -- REAL_CAPTURE_FOLDER UNITY_PROJECT OUTPUT_JSON.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.bounded_skin_roundtrip import accept, SUBJECTS, CHECKS
from unitypackage_blender_importer.tests.blender_geometry_abcd_compare import compare, unity_row, skin_parity_report
from unitypackage_blender_importer.tests.blender_small_weight_real_check import raw_skin_weights
from unitypackage_blender_importer.unity.yaml_parser import parse_unity_yaml
from unitypackage_blender_importer.export.model_skin import model_skin_material_bindings


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(condition, code):
    if not condition:
        raise ValueError(code)


def exact(condition):
    return 'EXACT' if condition else 'RED'


def material_comparison_labels(material_ids, bindings, target_guids, target_file_ids):
    """Label measured Material references for the existing face-partition oracle.

    These diagnostic labels encode GUID/localID identity; the FBX transport
    carrier labels are independently validated by the existing task builder.
    """
    need(bool(bindings), 'MATERIAL_BINDINGS_MISSING')
    source = sorted(material_ids, key=lambda material: material['slot'])
    need([m['slot'] for m in source] == list(range(len(bindings)))
         and [m['guid'] for m in source] == [b['guid'] for b in bindings], 'CURRENT_MATERIAL_BINDING_MISMATCH')
    need(model_skin_material_bindings(bindings) == bindings, 'MATERIAL_TRANSPORT_LABEL_MISMATCH')
    refs = {(b['guid'], str(b['file_id'])) for b in bindings}
    need(len(target_guids) == len(target_file_ids) and all((guid, str(local_id)) in refs
         for guid, local_id in zip(target_guids, target_file_ids)), 'TARGET_MATERIAL_REFERENCE_MISMATCH')
    label = lambda guid, local_id: 'VAPB-EXP-MAT-' + guid + ':' + str(local_id)
    return ([label(b['guid'], b['file_id']) for b in bindings],
            [label(guid, local_id) for guid, local_id in zip(target_guids, target_file_ids)])


def negative_controls(entity, evidence):
    controls = {}
    for name, field in [('wrong_target', 'renderer_file_id'), ('stale_fbx', 'fbx_sha256'),
                        ('swapped_bones', 'bone_ids'), ('wrong_root', 'root_bone_id'),
                        ('wrong_occurrence', 'occurrence_id')]:
        altered = deepcopy(evidence)
        domain = 'geometry' if field == 'fbx_sha256' else 'hierarchy'
        # Deliberately corrupt one recorded subject; the acceptance function must
        # reject cross-evidence disagreement without any relaxed check statuses.
        original = altered[domain]['subject'][field]
        if field == 'bone_ids':
            replacement = list(reversed(original))
            if replacement == original:
                replacement = list(original) + ['CONTROL_INVALID_BONE']
        else:
            replacement = 'CONTROL_INVALID_SUBJECT'
        altered[domain]['subject'][field] = replacement
        controls[name] = accept(entity, altered)
    return dict(controls=controls, total=len(controls), rejected=sum(
        row['supported_bounded_skin_roundtrip'] == 'RED' for row in controls.values()))


def build(folder, project):
    blender = read(folder / 'BoundedBlender.json')
    recipe = read(folder / 'BoundedRecipe.json')
    task = recipe['task']
    lock = read(folder / 'InputLock.json')
    source_lock = read(folder / 'SourceLockPrivate.json')
    proof = read(folder / 'PriorSkinProofPrivate.json')
    unity = read(project / 'ModelBoundedUnity.json')
    preserved = read(folder / 'BoundedPreservation.json')
    binding = blender['renderer_binding']
    occurrence = binding['occurrence']
    need(blender['prior_skin'] == proof, 'PRIOR_CAPTURE_REVISION_MISMATCH')
    need(task['kind'] == 'RESTORE_DIRECT_SKIN_VARIANT_V1', 'UNSUPPORTED_TASK_KIND')
    need(read(project / 'Assets/VAPBExport/manifest.json')['reference_rebind_tasks'] == [task], 'TASK_REVISION_MISMATCH')
    need(read(project / 'InputLock.json') == lock, 'INPUT_LOCK_MISMATCH')
    archive_path = Path(source_lock['source_archive_path'])
    need(sha(archive_path) == source_lock['source_package_sha256'] == blender['package_sha256']
         == lock['source_package_sha256'] == unity['package_sha256'], 'PACKAGE_REVISION_MISMATCH')
    need(sha(folder / 'BoundedBlender.json') == lock['blender_capture_sha256']
         == unity['blender_capture_sha256'] == sha(project / 'BoundedBlender.json'), 'STALE_BLENDER_CAPTURE')
    need(sha(folder / 'Output.unitypackage') == recipe['output_sha256'] == lock['output_sha256']
         == unity['output_sha256'] == sha(project / 'Output.unitypackage'), 'OUTPUT_REVISION_MISMATCH')
    need(occurrence['root_package_id'] == occurrence['source_package_id'] == 'sha256:' + blender['package_sha256']
         and not occurrence['instance_edge_path'] and not task['instance_edges'], 'UNSUPPORTED_SOURCE_OCCURRENCE')
    need(binding['occurrence_id'] == occurrence['occurrence_id'] == lock['occurrence_id']
         == unity['occurrence_id'] == proof['occurrence_id'], 'OCCURRENCE_MISMATCH')
    need(occurrence['source_key']['source_asset_guid'] == occurrence['root_asset_guid'] == task['prefab_guid'],
         'SOURCE_PREFAB_MISMATCH')
    renderer_id = str(occurrence['source_key']['renderer_file_id'])
    owner_id = str(occurrence['owner']['owner_game_object_id'])
    need(renderer_id == lock['expected_renderer_file_id'] and owner_id == lock['expected_owner_file_id'], 'TARGET_LOCK_MISMATCH')
    candidate, = [c for c in task['renderer_candidates'] if c['renderer_file_id'] == renderer_id]
    with tarfile.open(archive_path) as archive:
        prefab_bytes = archive.extractfile(task['prefab_guid'] + '/asset').read()
        model_bytes = archive.extractfile(task['source_model_guid'] + '/asset').read()
    need(hashlib.sha256(prefab_bytes).hexdigest() == task['prefab_source_sha256']
         == occurrence['source_revision_sha256'] == unity['prefab_source_sha256'], 'PREFAB_REVISION_MISMATCH')
    receipt = binding['mesh_receipt']
    need(hashlib.sha256(model_bytes).hexdigest() == task['source_model_sha256'] == receipt['source_sha256']
         and receipt['mesh_guid'] == task['source_model_guid']
         and str(receipt['mesh_file_id']) == str(candidate['source_mesh_file_id']), 'SOURCE_MESH_RECEIPT_MISMATCH')
    need(sha(folder / 'Generated/D1.fbx') == task['model_sha256'] == unity['fbx_sha256'], 'STALE_FBX')
    need(task['realization_id'] == binding['native_realization_id'] == unity['realization_id'], 'NATIVE_REALIZATION_MISMATCH')
    docs = parse_unity_yaml(prefab_bytes.decode('utf-8-sig'))
    by_id = {str(d.file_id): d for d in docs}
    source_renderer = by_id[renderer_id]
    need(str(source_renderer.data['m_GameObject']['fileID']) == owner_id, 'SOURCE_OWNER_MISMATCH')
    source_ids = [str(v['fileID']) for v in source_renderer.data['m_Bones']]
    root_id = str(source_renderer.data['m_RootBone']['fileID'])
    need(source_ids == candidate['bone_transform_file_ids'] and root_id == candidate['root_bone_transform_file_id'],
         'CANDIDATE_IDENTITY_MISMATCH')
    transforms = {str(d.file_id): d for d in docs if d.class_id == 4}
    objects = blender['hierarchy']['objects']
    observed = {str(o['metadata']['_vapb_source_local_file_id']): o for o in objects if o['classification'] == 'SEMANTIC'}
    unity_parent = {n['game_object_id']: n['parent_game_object_id'] or None for n in unity['hierarchy']}
    unity_transforms = {n['transform_id']: n for n in unity['hierarchy']}
    bridge_path = project / 'ModelHierarchyBridge.json'
    source_fields = ('source_guid', 'source_game_object_id', 'source_transform_id', 'instance_guid', 'prefab_instance_file_id')
    bridge_nodes = unity['hierarchy'] if all(all(f in n for f in source_fields) for n in unity['hierarchy']) else []
    if bridge_path.exists():
        bridge = read(bridge_path)
        need(bridge['output_sha256'] == lock['output_sha256'] and bridge['prefab_source_sha256'] == task['prefab_source_sha256'],
             'HIERARCHY_BRIDGE_REVISION_MISMATCH')
        base_fields = ('game_object_id', 'parent_game_object_id', 'transform_id', 'parent_transform_id')
        measured = {n['transform_id']: {f: n[f] for f in base_fields} for n in unity['hierarchy']}
        bridge_measured = {n['transform_id']: {f: n[f] for f in base_fields} for n in bridge['nodes']}
        need(measured == bridge_measured and len(bridge['nodes']) == len(measured), 'HIERARCHY_BRIDGE_SOURCE_GRAPH_MISMATCH')
        bridge_nodes = bridge['nodes']
    semantic_ids = {}
    nested_bridge_proven = True
    for source_id, obj in observed.items():
        metadata = obj['metadata']
        edge_raw = metadata.get('_vapb_model_instance_edge_path')
        if not edge_raw:
            semantic_ids[obj['handle']] = source_id
            continue
        edges = json.loads(edge_raw) if isinstance(edge_raw, str) else edge_raw
        if len(edges) != 1:
            nested_bridge_proven = False
            continue
        edge = edges[0]
        source_guid = metadata['unity_source_prefab_guid']
        source_transform = metadata['_vapb_source_transform_file_id']
        need(edge['container_asset_guid'] == task['prefab_guid'] and edge['source_prefab_guid'] == source_guid
             and edge['container_package_id'] == edge['source_package_id'] == 'sha256:' + blender['package_sha256'],
             'NESTED_SOURCE_OCCURRENCE_MISMATCH')
        instance_id = str(edge['prefab_instance_file_id'])
        need(by_id[instance_id].class_id == 1001 and by_id[instance_id].data['m_SourcePrefab']['guid'] == source_guid,
             'NESTED_INSTANCE_SOURCE_MISMATCH')
        with tarfile.open(archive_path) as archive:
            child_docs = parse_unity_yaml(archive.extractfile(source_guid + '/asset').read().decode('utf-8-sig'))
        child_by_id = {str(d.file_id): d for d in child_docs}
        need(child_by_id[source_id].class_id == 1 and child_by_id[source_transform].class_id == 4
             and str(child_by_id[source_transform].data['m_GameObject']['fileID']) == source_id,
             'NESTED_SOURCE_NODE_MISMATCH')
        joined = [n for n in bridge_nodes if n.get('source_guid') == source_guid
            and n.get('source_game_object_id') == source_id and n.get('source_transform_id') == source_transform
            and n.get('prefab_instance_file_id') == instance_id and n.get('instance_guid') == task['prefab_guid']]
        if len(joined) != 1:
            nested_bridge_proven = False
            continue
        semantic_ids[obj['handle']] = joined[0]['game_object_id']
    blender_parent = {semantic_ids[o['handle']]: semantic_ids.get(o['actual_parent']) for o in observed.values()
                      if o['handle'] in semantic_ids}
    # Stripped model-instance Transform YAML omits native hierarchy fields.
    # The immutable-source public API hierarchy is the authoritative full graph.
    semantic_ok = (nested_bridge_proven and len(semantic_ids) == len(observed)
        and len(set(semantic_ids.values())) == len(observed) and blender_parent == unity_parent)
    before = blender['before']
    first = deepcopy(unity['first'])
    need(first == unity['repeated'] and unity['repeated_capture_equal'], 'REPEATED_CAPTURE_MISMATCH')
    need(first['renderer_file_id'] == renderer_id and first['owner_file_id'] == owner_id, 'TARGET_OWNER_MISMATCH')
    mapping = {m['source_model_uid']: m['edited_bone_realization_id'] for m in task['bone_mappings']}
    prior = sorted(proof['bones'], key=lambda b: b['slot'])
    need([b['slot'] for b in prior] == list(range(len(source_ids)))
         and [str(b['prefab_transform']['local_id']) for b in prior] == source_ids
         and all(b['prefab_transform']['guid'] == task['prefab_guid'] for b in prior), 'PRIOR_ORDERED_BONE_IDENTITY_UNPROVEN')
    source_uids = [b['model_uid'] for b in prior]
    target_by_uid = dict(zip(source_uids, source_ids))
    observed_uids = [b['source_model_uid'] for b in first['bones']]
    labels = [b['export_label'] for b in first['bones']]
    bone_ok = (len(observed_uids) == len(set(observed_uids)) and set(observed_uids) == set(source_uids)
        and [b['index'] for b in first['bones']] == list(range(len(observed_uids)))
        and all(b['target_file_id'] == target_by_uid.get(b['source_model_uid'])
                and b['export_label'] == mapping.get(b['source_model_uid']) for b in first['bones'])
        and first['ordered_bone_uids'] == observed_uids
        and first['ordered_target_ids'] == [b['target_file_id'] for b in first['bones']]
        and all(b['carrier_constraint_valid'] and b['bone_parent_valid'] for b in prior))
    for bone in first['bones']:
        node = unity_transforms.get(bone['target_file_id'])
        bone_ok = bone_ok and node is not None and (bone['parent_target_file_id'] or '0') == (node['parent_transform_id'] or '0')
    root_label = first.get('root_bone_export_label')
    root_uid = first.get('root_bone_source_model_uid')
    root_ok = (first['root_bone_id'] == root_id == str(proof['root_transform_identity']['local_id'])
        and proof['root_transform_identity']['guid'] == task['prefab_guid'] and proof['root_frame_binding_valid'])
    # Receipt roots and measured semantic frame roots are separate supported
    # representations. A frame root has no invented Model UID.
    root_proven = bool(root_label and root_uid and mapping.get(root_uid) == root_label)
    native, = [o for o in objects if o['metadata'].get('_vapb_fbx_realization_id') == task['realization_id']]
    expected_receipt = 'vapb-fbx-mesh:' + hashlib.sha256((receipt['source_sha256'] + ':' + receipt['fbx_geometry_uid']).encode()).hexdigest()
    mesh_ok = (receipt['fbx_mesh_receipt_id'] == expected_receipt
        == native['metadata'].get('_vapb_fbx_mesh_receipt_id') == native['mesh_metadata'].get('_vapb_fbx_mesh_receipt_id')
        and native['metadata'].get('_vapb_root_context_id') == binding['root_context_id'])
    armature, = [o for o in objects if o['metadata'].get('_vapb_native_object_id') == binding['armature_native_object_id']]
    armature_ok = (native['armature_modifiers'] == [dict(target=armature['handle'])]
        and proof['armature_handle'] == armature['handle'] and proof['mesh_handle'] == native['handle']
        and armature['actual_parent'] == proof['actual_armature_parent_handle']
        and native['actual_parent'] == proof['actual_mesh_parent_handle'])
    native_bones = {b['metadata'].get('_vapb_fbx_bone_realization_id'): b for b in armature['bones']}
    bone_ok = bone_ok and all(label in native_bones for label in labels)
    for p in prior:
        bone = native_bones.get(mapping[p['model_uid']])
        if bone is None:
            continue
        parent = bone['parent_index']
        parent_label = armature['bones'][parent]['metadata'].get('_vapb_fbx_bone_realization_id') if parent is not None else None
        bone_ok = bone_ok and parent_label == mapping.get(p['actual_parent_uid'])
        bone_ok = bone_ok and bone['metadata'].get('_vapb_fbx_model_uid') == p['model_uid']
    object_handles = {o['handle']: o for o in objects}
    root_carrier = object_handles.get(proof['root_bone_semantic_carrier_handle'])
    root_node = unity_transforms.get(root_id)
    root_go = root_node['game_object_id'] if root_node else None
    frame_root_proven = (proof['root_representation'] == 'ROOT_FRAME_OBJECT'
        and proof['root_bone_carrier_handle'] == proof['root_bone_semantic_carrier_handle']
        and root_carrier is not None and root_carrier['classification'] == 'SEMANTIC'
        and bool(root_go) and str(root_carrier['metadata'].get('_vapb_source_local_file_id')) == root_go
        and root_carrier['metadata'].get('_vapb_root_context_id') == binding['root_context_id']
        and root_uid in (None, '') and root_label in (None, '') and armature_ok and bone_ok)
    root_proven = root_proven or frame_root_proven
    need(first['shape_count'] == 0 and not before['shapes'], 'SHAPE_SCOPE_UNSUPPORTED')
    first.update(shape_frames=[], vertex_count=len(first['vertex_control_point_indices']), renderer_type='SkinnedMeshRenderer')
    bindings = task.get('material_bindings')
    if bindings:
        before = deepcopy(before)
        before['material_export_labels'], first['material_export_labels'] = material_comparison_labels(
            blender['material_ids'], bindings, first['material_guids'], first['material_file_ids'])
    geometry = compare(before, unity_row(first), before['marker_channel'])
    raw = raw_skin_weights(folder / 'Generated', bone_label_property='_vapb_fbx_bone_realization_id')
    policy = read(project / ('Assets/VAPBExport/SkinWeightPolicy_' + task['model_guid'] + '.json'))
    skin = skin_parity_report(before, first, dict(unity_version=unity['version'], fbx_sha256=task['model_sha256'],
        expected_fbx_sha256=task['model_sha256'], observed_fbx_sha256=unity['fbx_sha256'], mesh_guid=first['guid'],
        mesh_local_id=first['local_id'], raw_weights=raw, preprocess_policy=policy))
    from io_scene_fbx import parse_fbx
    tree, _ = parse_fbx.parse(str(folder / 'Generated/D1.fbx'), use_namedtuple=True)
    fbx_geom, = [n for n in next(n for n in tree.elems if n.id == b'Objects').elems if n.id == b'Geometry' and n.props[2] == b'Mesh']
    sizes, size = [], 0
    for index in next(n.props[0] for n in fbx_geom.elems if n.id == b'PolygonVertexIndex'):
        size += 1
        if index < 0:
            sizes.append(size)
            size = 0
    entity = dict(package_sha256=blender['package_sha256'], prefab_sha256=task['prefab_source_sha256'],
        root_context_id=binding['root_context_id'], occurrence_id=binding['occurrence_id'], prefab_guid=task['prefab_guid'],
        renderer_file_id=renderer_id, owner_file_id=owner_id, realization_id=task['realization_id'],
        model_guid=task['model_guid'], fbx_sha256=task['model_sha256'], mesh_local_id=first['local_id'],
        bone_ids=labels, root_bone_id=root_label or root_id)
    evidence = {domain: dict(subject={field: entity[field] for field in fields}, checks={}) for domain, fields in SUBJECTS.items()}
    evidence['hierarchy']['checks'] = dict(semantic_parent=exact(semantic_ok),
        renderer_owner=exact(proof['renderer_owner_valid'] and observed[owner_id]['metadata'].get('_vapb_semantic_owner_id') == binding['semantic_owner_id']),
        mesh_bridge=exact(mesh_ok), armature_relation=exact(armature_ok), ordered_bones=exact(bone_ok),
        root_bone=exact(root_ok) if root_proven else 'UNPROVEN')
    evidence['geometry']['checks'] = dict(explicit_triangles=exact(bool(sizes) and not size and set(sizes) == {3}),
        topology=geometry['topology'], sampled_surface=exact(geometry['surface']['status'] == 'SAMPLED_EXACT'),
        cp_correspondence=geometry['vertex_correspondence']['status'])
    evidence['skin']['report'] = skin
    material_guids = [m['guid'] for m in sorted(blender['material_ids'], key=lambda m: m['slot'])]
    source_materials = [m.get('guid', '') for m in source_renderer.data['m_Materials']]
    material_ok = (geometry['material_identity_partitions'] == 'EXACT') if bindings else (
        material_guids == source_materials == first['material_guids'] and geometry['topology_by_material_slot'] == 'EXACT')
    evidence['material']['checks'] = dict(effective_association=exact(material_ok))
    evidence['shape']['checks'] = dict(shape='NOT_APPLICABLE')
    evidence['finalizer']['checks'] = dict(package_import=exact(unity['output_sha256'] == lock['output_sha256']),
        target_resolution=exact(first['renderer_file_id'] == renderer_id and first['owner_file_id'] == owner_id and first['guid'] == task['model_guid']),
        apply=exact(unity['first_apply']), repeated_apply=exact(unity['second_apply'] and unity['second_apply_unchanged']
            and unity['component_node_counts_unchanged'] and unity['siblings_preserved'] and unity['originals_unchanged']))
    need(preserved['realization_id'] == task['realization_id'] and preserved['fbx_sha256'] == task['model_sha256'], 'PRESERVATION_REVISION_MISMATCH')
    evidence['preservation']['checks'] = {field: exact(preserved[field]) for field in CHECKS['preservation']}
    evidence['known_boundaries'] = dict(deformation='UNMEASURED', normals=geometry['normals_per_cp_values'],
        uv=geometry['uv_per_cp_values'], submesh_numbering=geometry['topology_by_material_slot'], tangents='UNKNOWN',
        import_preview='NOT_MEASURED_BY_THIS_CONTROL', shape='NOT_APPLICABLE_NO_SHAPES')
    return dict(entity=entity, evidence=evidence, result=accept(entity, evidence), geometry=geometry,
        negative_controls=negative_controls(entity, evidence))


def main():
    folder, project, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
    try:
        result = build(folder, project)
    except FileNotFoundError:
        result = dict(result=dict(supported_bounded_skin_roundtrip='UNSUPPORTED', reason='REQUIRED_CAPTURE_FILE_MISSING'))
    except ValueError as error:
        # Only adapter-owned fixed codes are exposed; arbitrary parser errors can
        # contain private source values and remain inside the external reports.
        reason = str(error)
        if not reason.isupper() or not reason.replace('_', '').isalnum():
            reason = 'CAPTURE_VALUE_INVALID'
        result = dict(result=dict(supported_bounded_skin_roundtrip='UNSUPPORTED', reason=reason))
    except (KeyError, IndexError, TypeError, AssertionError, StopIteration):
        result = dict(result=dict(supported_bounded_skin_roundtrip='UNSUPPORTED', reason='CAPTURE_CONTEXT_INCOMPLETE'))
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('MODEL_BOUNDED_SKIN', result['result']['supported_bounded_skin_roundtrip'], result['result']['reason'])
    if result['result']['supported_bounded_skin_roundtrip'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
