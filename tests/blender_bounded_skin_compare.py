# SPDX-License-Identifier: GPL-3.0-or-later
"""CLI: exact public Skin capture folder, fresh Unity project, output report.

This adapter supports direct, explicitly confirmed source Renderer/Bone bindings.
It does not upgrade unrelated aggregate reports or infer nested occurrences.
"""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.bounded_skin_roundtrip import accept, SUBJECTS, CHECKS
from unitypackage_blender_importer.tests.blender_geometry_abcd_compare import compare, unity_row, skin_parity_report
from unitypackage_blender_importer.tests.blender_small_weight_real_check import raw_skin_weights
from unitypackage_blender_importer.unity.yaml_parser import parse_unity_yaml


def source_bytes(package,guid):
    with tarfile.open(package) as archive: return archive.extractfile(guid+'/asset').read()


def build(folder,project):
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    b=read(folder/'BoundedBlender.json'); recipe=read(folder/'BoundedRecipe.json');task=recipe['task']
    u=read(project/'BoundedUnity.json'); applied=read(project/'VapbSkinRoundtripResult.json')
    preserved=read(folder/'BoundedPreservation.json');binding=b['renderer_binding'];occ=binding['occurrence']
    def need(condition,reason):
        if not condition:raise ValueError(reason)
    need(u['blender_capture_sha256']==hashlib.sha256((folder/'BoundedBlender.json').read_bytes()).hexdigest(),
         'STALE_BLENDER_CAPTURE')
    need(u['package_sha256']==b['package_sha256']==hashlib.sha256((folder/'Source.unitypackage').read_bytes()).hexdigest(),
         'PACKAGE_REVISION_MISMATCH')
    need(occ['root_package_id']==occ['source_package_id']=='sha256:'+b['package_sha256']
         and not occ['instance_edge_path'],'UNSUPPORTED_SOURCE_OCCURRENCE')
    need(occ['source_key']['source_asset_guid']==task['prefab_guid']==occ['root_asset_guid'],
         'SOURCE_RENDERER_MISMATCH')
    need(str(occ['source_key']['renderer_file_id'])==task['renderer_file_id'], 'SOURCE_RENDERER_MISMATCH')
    need(binding['native_realization_id']==task['realization_id']==u['realization_id'], 'EXPORT_MESH_MISMATCH')
    need(task['model_sha256']==u['fbx_sha256']==hashlib.sha256((folder/'Generated/D1.fbx').read_bytes()).hexdigest(),
         'STALE_FBX')
    prefab=source_bytes(folder/'Source.unitypackage',task['prefab_guid'])
    need(hashlib.sha256(prefab).hexdigest()==task['prefab_source_sha256']==occ['source_revision_sha256'],
         'PREFAB_REVISION_MISMATCH')
    docs=parse_unity_yaml(prefab.decode('utf-8-sig'));by_id={str(d.file_id):d for d in docs}
    renderer=by_id[task['renderer_file_id']];owner=str(renderer.data['m_GameObject']['fileID'])
    source_mesh=renderer.data['m_Mesh'];receipt=binding['mesh_receipt']
    need(source_mesh['guid']==receipt['mesh_guid']==task['source_model_guid']
         and str(source_mesh['fileID'])==str(receipt['mesh_file_id'])==task['source_mesh_file_id']
         and hashlib.sha256(source_bytes(folder/'Source.unitypackage',receipt['mesh_guid'])).hexdigest()
         ==receipt['source_sha256']==task['source_model_sha256'],'SOURCE_MESH_RECEIPT_MISMATCH')
    need(owner==str(occ['owner']['owner_game_object_id']), 'RENDERER_OWNER_MISMATCH')
    transforms={str(d.file_id):d for d in docs if d.class_id==4}
    source_parent={str(d.data['m_GameObject']['fileID']):
        str(transforms[str(d.data['m_Father']['fileID'])].data['m_GameObject']['fileID'])
        if str(d.data['m_Father']['fileID'])!='0' else None for d in transforms.values()}
    observed={str(o['metadata']['_vapb_source_local_file_id']):o for o in b['hierarchy']['objects']
              if o['classification']=='SEMANTIC'}
    need(set(observed)==set(source_parent),'SEMANTIC_NODE_SET_MISMATCH')
    handles={o['handle']:o for o in observed.values()}
    blender_parent={k: str(handles[o['actual_parent']]['metadata']['_vapb_source_local_file_id'])
        if o['actual_parent'] in handles else None for k,o in observed.items()}
    # JsonUtility serializes a null string as ""; both mean the measured root.
    unity_parent={n['game_object_id']:n['parent_game_object_id'] or None for n in u['hierarchy']}
    need(blender_parent==source_parent==unity_parent,'SEMANTIC_PARENT_MISMATCH')
    need(observed[owner]['metadata'].get('_vapb_semantic_owner_id')==binding['semantic_owner_id'],
         'SEMANTIC_OWNER_BRIDGE_MISMATCH')
    mapping={m['target_transform_file_id']:m['edited_bone_realization_id'] for m in b['skin_binding']['mappings']}
    source_bones=[str(r['fileID']) for r in renderer.data['m_Bones']]
    source_root=str(renderer.data['m_RootBone']['fileID'])
    bone_ids=[mapping[v] for v in source_bones]; root_id=mapping[source_root]
    first=u['first'];repeat=u['repeated']
    need(first==repeat,'REPEATED_CAPTURE_MISMATCH')
    need(first['renderer_file_id']==task['renderer_file_id'] and first['owner_file_id']==owner,'TARGET_OWNER_MISMATCH')
    need([x['target_file_id'] for x in first['bones']]==source_bones
         and [x['export_label'] for x in first['bones']]==bone_ids and first['root_bone_id']==source_root,
         'ORDERED_BONE_OR_ROOT_MISMATCH')
    need(first['shape_count']==0 and not b['before']['shapes'],'SHAPE_SCOPE_UNSUPPORTED')
    before=b['before'];first.update(shape_frames=[],vertex_count=len(first['vertex_control_point_indices']),renderer_type='SkinnedMeshRenderer')
    geo=compare(before,unity_row(first),before['marker_channel'])
    raw=raw_skin_weights(folder/'Generated',bone_label_property='_vapb_fbx_bone_realization_id')
    policy,=[read(p) for p in (project/'Assets/VAPBExport').glob('SkinWeightPolicy_'+task['model_guid']+'.json')]
    context=dict(unity_version=u['version'],fbx_sha256=task['model_sha256'],expected_fbx_sha256=task['model_sha256'],
        observed_fbx_sha256=u['fbx_sha256'],mesh_guid=first['guid'],mesh_local_id=first['local_id'],
        raw_weights=raw,preprocess_policy=policy,
        deformation=dict(provenance='PUBLIC_FINALIZER_CONTROL_CPU_EXPECTED_VS_UNITY_BAKEMESH',
                         metrics=dict(CPU_Unity_Bake_max_error_m=applied['deformationMaxError'])))
    skin=skin_parity_report(before,first,context)
    key=dict(package_sha256=b['package_sha256'],prefab_sha256=task['prefab_source_sha256'],
        root_context_id=binding['root_context_id'],occurrence_id=binding['occurrence_id'],
        prefab_guid=task['prefab_guid'],renderer_file_id=task['renderer_file_id'],owner_file_id=owner,
        realization_id=task['realization_id'],model_guid=task['model_guid'],fbx_sha256=task['model_sha256'],
        mesh_local_id=first['local_id'],bone_ids=bone_ids,root_bone_id=root_id)
    e={name:dict(subject={f:key[f] for f in fields},checks={}) for name,fields in SUBJECTS.items()}
    e['hierarchy']['checks']={f:'EXACT' for f in CHECKS['hierarchy']}
    # Native modifier target is a persisted native Object ID, independent of names.
    native,=[o for o in b['hierarchy']['objects'] if o['metadata'].get('_vapb_fbx_realization_id')==binding['native_realization_id']]
    # Exact existing fbx_receipt.make_receipt format; GUID is checked above.
    expected_receipt='vapb-fbx-mesh:'+hashlib.sha256((receipt['source_sha256']+':'+receipt['fbx_geometry_uid']).encode()).hexdigest()
    need(expected_receipt==receipt['fbx_mesh_receipt_id']==native['metadata'].get('_vapb_fbx_mesh_receipt_id')
         ==native['mesh_metadata'].get('_vapb_fbx_mesh_receipt_id')
         and native['metadata'].get('_vapb_root_context_id')==binding['root_context_id'], 'NATIVE_MESH_RECEIPT_MISMATCH')
    armature,=[o for o in b['hierarchy']['objects'] if o['metadata'].get('_vapb_native_object_id')==binding['armature_native_object_id']]
    need(native['armature_modifiers']==[dict(target=armature['handle'])],'ARMATURE_TARGET_MISMATCH')
    native_bones={r['metadata'].get('_vapb_fbx_bone_realization_id'):r for r in armature['bones']}
    need(set(bone_ids)<=set(native_bones),'NATIVE_BONE_RECEIPT_MISSING')
    for target,bone_id in zip(source_bones,bone_ids):
        parent=str(transforms[target].data['m_Father']['fileID'])
        actual_parent=native_bones[bone_id]['parent_index']
        actual_id=armature['bones'][actual_parent]['metadata'].get('_vapb_fbx_bone_realization_id') if actual_parent is not None else None
        need(actual_id==mapping.get(parent),'NATIVE_BONE_PARENT_MISMATCH')
    from io_scene_fbx import parse_fbx
    tree,_=parse_fbx.parse(str(folder/'Generated/D1.fbx'),use_namedtuple=True)
    geometry,=[n for n in next(n for n in tree.elems if n.id==b'Objects').elems if n.id==b'Geometry' and n.props[2]==b'Mesh']
    sizes=[];size=0
    for value in next(n.props[0] for n in geometry.elems if n.id==b'PolygonVertexIndex'):
        size+=1
        if value<0:sizes.append(size);size=0
    e['geometry']['checks']=dict(explicit_triangles='EXACT' if sizes and not size and set(sizes)=={3} else 'RED',
        topology=geo['topology'],sampled_surface='EXACT' if geo['surface']['status']=='SAMPLED_EXACT' else 'RED',
        cp_correspondence=geo['vertex_correspondence']['status'])
    e['skin']['report']=skin
    materials=[r['guid'] for r in b['material_ids']]
    material_ok=materials==[m['guid'] for m in task['materials']]==first['material_guids']
    material_ok=material_ok and geo['topology_by_material_slot']=='EXACT'
    e['material']['checks']=dict(effective_association='EXACT' if material_ok else 'RED')
    e['shape']['checks']=dict(shape='NOT_APPLICABLE')
    e['finalizer']['checks']={k:'EXACT' if applied[v] else 'RED' for k,v in dict(
        package_import='packageImported',target_resolution='editedMesh',apply='firstApply',repeated_apply='secondApplyUnchanged').items()}
    e['preservation']['checks']={k:'EXACT' if preserved[k] else 'RED' for k in CHECKS['preservation']}
    need(preserved['realization_id']==key['realization_id'] and preserved['fbx_sha256']==key['fbx_sha256'],'PRESERVATION_REVISION_MISMATCH')
    e['known_boundaries']=dict(normals='UNMEASURED',tangents='UNKNOWN',import_preview='NOT_MEASURED_BY_THIS_CONTROL',
                             shape='NOT_APPLICABLE_NO_SHAPES_IN_THIS_FIXTURE')
    return dict(entity=key,evidence=e,result=accept(key,e),geometry=geo)


def main():
    folder,project,output=map(Path,sys.argv[sys.argv.index('--')+1:])
    try: result=build(folder,project)
    except (KeyError,ValueError,IndexError,TypeError) as error:
        result=dict(result=dict(supported_bounded_skin_roundtrip='UNSUPPORTED',reason=str(error)))
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('BOUNDED_SKIN',result['result']['supported_bounded_skin_roundtrip'],result['result']['reason'])
    if result['result']['supported_bounded_skin_roundtrip']!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
