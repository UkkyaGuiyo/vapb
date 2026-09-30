# SPDX-License-Identifier: GPL-3.0-or-later
"""External single-source experiment: UNITY_PROJECT BLENDER_REPORT OUTPUT_JSON.

CP transport proves correspondence. Surface samples measure distance only.
No channel/Bone semantic identity is inferred from labels or array order.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_geometry_abcd import observe
from unitypackage_blender_importer.tests.geometry_abcd_metrics import (
    POSITION_TOLERANCE, triangle_multiset, position_metric, corner_values_by_point, weight_value_sets,attribute_set_distance,oriented_triangles,material_label_partitions)


def unity_vector(v):
    return [-v['x'],-v['z'],v['y']]


def unity_row(row):
    assert row['marker_invalid_count'] == 0
    labels = row['vertex_control_point_indices']
    indices = row['triangles']
    assert len(indices)%3 == 0
    triangles = [[labels[v] for v in indices[i:i+3]] for i in range(0,len(indices),3)]
    influences = [[] for _ in labels]
    for weight in row['bone_weights']:
        influences[weight['vertex']].append(weight['weight'])
    return dict(positions=[unity_vector(v) for v in row['world_positions']],
        vertex_control_point_indices=labels, triangles=[indices[i:i+3] for i in range(0,len(indices),3)],
        triangle_control_points=triangles,
        unity_handedness=True,
        material_export_labels=row.get('material_export_labels',[]),
        triangle_material_slots=[index for index,submesh in enumerate(row['submeshes'])
                                 for _ in range(len(submesh['indices'])//3)],
        corner_normals=[unity_vector(row['world_normals'][i]) for i in indices] if row['world_normals'] else [],
        uv_channels=[dict(channel=layer['channel'],corners=[[layer['values'][i]['x'],layer['values'][i]['y']]
                     for i in indices]) for layer in row['uv_channels'] if layer['values']],
        skin_weight_values=influences, shape_frame_count=len(row['shape_frames']),
        baked_positions=[unity_vector(v) for v in row.get('baked_true_world_positions',row.get('baked_world_positions',[]))],
        bake_method='PUBLIC_BAKEMESH_TRUE_EXISTING_ORACLE_CONTRACT' if 'baked_true_world_positions' in row else 'STATIC_OR_LEGACY_FALSE_DIAGNOSTIC',
        cpu_positions=[unity_vector(v) for v in row.get('cpu_weighted_world_positions',[])],
        unity_vertex_count=row['vertex_count'], renderer_type=row['renderer_type'])


def surface_metric(a,b):
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    def triangles(row):
        points=[Vector(v) for v in row['positions']]
        return [tuple(points[i] for i in t) for t in row['triangles']
                if (points[t[1]]-points[t[0]]).cross(points[t[2]]-points[t[0]]).length > 2e-12]
    aa,bb=triangles(a),triangles(b)
    assert aa and bb,'SURFACE_UNAVAILABLE'
    def measure(source,target):
        corners=[p for t in target for p in t]
        tree=BVHTree.FromPolygons(corners,[tuple(range(i,i+3)) for i in range(0,len(corners),3)],all_triangles=True)
        distances=[]
        for p,q,r in source:
            for x in ((p+q+r)/3,(p+q)/2,(p+r)/2,(q+r)/2,p,q,r):
                hit=tree.find_nearest(x)
                assert hit is not None
                distances.append(hit[3])
        return dict(maximum_distance=max(distances),samples=len(distances),
                    samples_above_tolerance=sum(v>POSITION_TOLERANCE for v in distances))
    forward,backward=measure(aa,bb),measure(bb,aa)
    return dict(status='SAMPLED_EXACT' if max(forward['maximum_distance'],backward['maximum_distance'])<=POSITION_TOLERANCE
                else 'SURFACE_DIFFERENCE',a_to_b=forward,b_to_a=backward,tolerance=POSITION_TOLERANCE,
                limitation='FINITE_SAMPLES_NOT_CONTINUOUS_SURFACE_PROOF')


def compare(a,b,marker):
    topology='EXACT' if triangle_multiset(a['triangle_control_points'])==triangle_multiset(b['triangle_control_points']) else 'TOPOLOGY_MISMATCH'
    result=dict(vertex_correspondence=position_metric(a['vertex_control_point_indices'],a['positions'],
                    b['vertex_control_point_indices'],b['positions']),topology=topology,
                a_triangles=len(a['triangles']),b_triangles=len(b['triangles']),surface=surface_metric(a,b))
    result['oriented_topology']='EXACT' if oriented_triangles(a['triangle_control_points'],a.get('unity_handedness',False))==oriented_triangles(b['triangle_control_points'],b.get('unity_handedness',False)) else 'ORIENTED_TOPOLOGY_MISMATCH'
    if 'triangle_material_slots' in a and 'triangle_material_slots' in b:
        partition=lambda row:Counter((slot,tuple(sorted(triangle))) for slot,triangle in
                            zip(row['triangle_material_slots'],row['triangle_control_points']))
        result['topology_by_material_slot']='EXACT' if partition(a)==partition(b) else 'SUBMESH_TOPOLOGY_MISMATCH'
    result['material_identity_partitions']='UNPROVEN'
    if a.get('material_export_labels') and b.get('material_export_labels'):
        try:
            aa=material_label_partitions(a['triangle_control_points'],a['triangle_material_slots'],a['material_export_labels'])
            bb=material_label_partitions(b['triangle_control_points'],b['triangle_material_slots'],b['material_export_labels'])
            result['material_identity_partitions']='EXACT' if aa==bb else 'MATERIAL_BINDING_MISMATCH'
        except ValueError:
            pass
    result['world_bounds']={label:dict(minimum=[min(p[i] for p in row['positions']) for i in range(3)],
                                    maximum=[max(p[i] for p in row['positions']) for i in range(3)])
                           for label,row in [('a',a),('b',b)]}
    auv={r['channel']:r['corners'] for r in a['uv_channels'] if r['channel']!=marker}
    buv={r['channel']:r['corners'] for r in b['uv_channels'] if r['channel']!=marker}
    result['uv_per_cp_values']='EXACT' if set(auv)==set(buv) and all(
        corner_values_by_point(a['triangle_control_points'],auv[i])==corner_values_by_point(b['triangle_control_points'],buv[i])
        for i in auv) else 'UV_MISMATCH'
    result['uv_set_distances']={str(i):attribute_set_distance(a['triangle_control_points'],auv[i],
                               b['triangle_control_points'],buv[i]) for i in auv if i in buv}
    result['normals_per_cp_values']='UNMEASURED'
    if a['corner_normals'] and b['corner_normals']:
        result['normals_per_cp_values']='EXACT' if corner_values_by_point(a['triangle_control_points'],a['corner_normals'],5)==corner_values_by_point(b['triangle_control_points'],b['corner_normals'],5) else 'NORMALS_DIFFERENCE'
        result['normal_set_distance']=attribute_set_distance(a['triangle_control_points'],a['corner_normals'],
                                                             b['triangle_control_points'],b['corner_normals'])
    av=a.get('skin_weight_values',[[v['weight'] for v in row] for row in a.get('skin_weights',[])])
    bv=b.get('skin_weight_values',[[v['weight'] for v in row] for row in b.get('skin_weights',[])])
    result['skin_numeric_weight_sets']='EXACT' if weight_value_sets(a['vertex_control_point_indices'],av)==weight_value_sets(b['vertex_control_point_indices'],bv) else 'WEIGHT_VALUES_DIFFERENCE'
    result['bone_identity']='UNPROVEN_BY_THIS_CP_TRANSPORT'
    result['shape_frame_counts']=[a.get('shape_frame_count',len(a.get('shapes',[]))),b.get('shape_frame_count',len(b.get('shapes',[])))]
    result['shape_semantic_identity']='UNPROVEN_BY_THIS_CP_TRANSPORT'
    if a.get('baked_positions') and b.get('baked_positions'):
        aa=dict(a,positions=a['baked_positions']);bb=dict(b,positions=b['baked_positions'])
        result['baked_vertex_correspondence']=position_metric(a['vertex_control_point_indices'],a['baked_positions'],
                                                             b['vertex_control_point_indices'],b['baked_positions'])
        result['baked_surface']=surface_metric(aa,bb)
        result['unity_bake_method']=b.get('bake_method',a.get('bake_method','BLENDER_DEPSGRAPH'))
        for label,row in [('a',a),('b',b)]:
            if row.get('cpu_positions'):
                result[label+'_bake_vs_cpu']=position_metric(row['vertex_control_point_indices'],row['baked_positions'],
                                                           row['vertex_control_point_indices'],row['cpu_positions'])
    return result


def skin_parity_report(before, observed, context):
    """Independent facts for the measured export scope; no transport-policy verdict."""
    import math
    from unitypackage_blender_importer.tests.weight_numeric_models import representation_compare
    result=dict(identity='UNPROVEN',influence_retention='UNPROVEN',raw_numeric='UNMEASURED',
        unity_representation='UNSUPPORTED_REPRESENTATION',deformation=dict(status='UNMEASURED'),
        overall_supported_transport='NOT_ASSESSED_PRODUCT_POLICY',
        identity_scope='EXPORTED_MESH_CP_BONE_INFLUENCE_ASSOCIATIONS',
        source_renderer_owner='UNMEASURED',total_influences=0,missing_influences=0,
        raw_changed_influences=0,representation_exact_influences=0,unexplained_influences=0,
        max_expected_actual_ULP=None)
    def require(condition,code):
        if not condition:raise ValueError(code)
    def cp_rows(ids,rows):
        require(len(ids)==len(rows),'CP_IDENTITY_UNPROVEN')
        output={}
        for cp,row in zip(ids,rows):
            require(type(cp) is int and cp>=0,'CP_IDENTITY_UNPROVEN')
            values={}
            for w in row:
                key=w['group'];value=w['weight']
                require(isinstance(key,str) and bool(key) and key not in values,'DUPLICATE_OR_UNRESOLVED_BONE')
                require(math.isfinite(value) and value>=0,'UNSUPPORTED_REPRESENTATION')
                if value>0:values[key]=value
            require(cp not in output or output[cp]==values,'CP_SPLIT_INFLUENCE_CONFLICT')
            output[cp]=values
        return output
    try:
        require(bool(context),'NUMERIC_CONTEXT_MISSING')
        measurement=context.get('deformation')
        if measurement:
            metrics=measurement['metrics']
            require(bool(measurement['provenance']) and bool(metrics) and all(
                math.isfinite(v) and v>=0 for v in metrics.values()),'DEFORMATION_MEASUREMENT_INVALID')
            result['deformation']=dict(measurement,status='MEASURED_NONZERO' if any(metrics.values()) else 'MEASURED_ZERO')
        revision=context['fbx_sha256']
        require(len(revision)==64 and all(c in '0123456789abcdef' for c in revision)
            and revision==context['expected_fbx_sha256']==context['observed_fbx_sha256'],'SOURCE_REVISION_MISMATCH')
        require(context['unity_version']=='2022.3.22f1','UNSUPPORTED_REPRESENTATION')
        policy=context['preprocess_policy']
        require(policy.get('version')==1 and policy.get('model_sha256')==revision
            and policy.get('model_guid')==observed['guid']==context['mesh_guid']
            and str(observed['local_id'])==str(context['mesh_local_id']),'IMPORT_POLICY_OR_MESH_IDENTITY_UNPROVEN')
        require(observed.get('marker_invalid_count')==0,'CP_IDENTITY_UNPROVEN')
        bones={}
        for bone in observed['bones']:
            index,label=bone['index'],bone.get('export_label')
            require(type(index) is int and index>=0 and index not in bones and label
                and label not in bones.values(),'DUPLICATE_OR_UNRESOLVED_BONE')
            bones[index]=label
        labels=observed['vertex_control_point_indices'];native=[[] for _ in labels]
        for w in observed['bone_weights']:
            require(w['bone'] in bones,'UNEXPECTED_BONE')
            require(type(w['vertex']) is int and 0<=w['vertex']<len(labels),'CP_IDENTITY_UNPROVEN')
            native[w['vertex']].append(dict(group=bones[w['bone']],weight=w['weight']))
        authored=cp_rows(before['vertex_control_point_indices'],before['skin_weights'])
        staged=cp_rows(before['vertex_control_point_indices'],context.get('staged_weights',before['skin_weights']))
        actual=cp_rows(labels,native);raw={cp:{} for cp in authored}
        for (cp,bone),value in context['raw_weights'].items():
            require(cp in raw and bone in bones.values(),'CP_OR_BONE_IDENTITY_UNPROVEN')
            require(math.isfinite(value) and value>=0,'UNSUPPORTED_REPRESENTATION')
            if value>0:raw[cp][bone]=value
        require(set(authored)==set(actual),'CP_IDENTITY_UNPROVEN')
        require(all(set(authored[cp])==set(raw[cp]) for cp in raw),'CANONICAL_INPUT_INCOMPLETE')
        result['total_influences']=sum(len(row) for row in raw.values())
        result['missing_influences']=sum(len(set(raw[cp])-set(actual[cp])) for cp in raw)
        unexpected=sum(len(set(actual[cp])-set(raw[cp])) for cp in raw)
        result['influence_retention']='MISSING_POSITIVE_INFLUENCES' if result['missing_influences'] else 'EXACT'
        result['raw_changed_influences']=sum(actual[cp].get(k)!=v for cp,row in raw.items() for k,v in row.items())
        result['raw_numeric']='RAW_NUMERIC_DIFFERENCE' if result['raw_changed_influences'] else 'EXACT'
        require(not result['missing_influences'] and not unexpected,'INFLUENCE_ASSOCIATION_MISMATCH')
        result['identity']='EXACT'
        rows=[]
        for cp in raw:
            require(authored[cp]==staged[cp]==raw[cp],'AUTHORED_CANONICAL_OR_STAGING_CHANGED')
            comparison=representation_compare(authored[cp],staged[cp],raw[cp],actual[cp],unity_version=context['unity_version'])
            rows.extend(dict(row,cp=cp) for row in comparison['rows'])
        result['staging']='EXACT' if 'staged_weights' in context else 'UNMEASURED'
        if result['staging']=='UNMEASURED':
            for row in rows:row['STAGED']=None
        result['representation_exact_influences']=sum(row['expected_actual_ULP']==0 for row in rows)
        result['unexplained_influences']=len(rows)-result['representation_exact_influences']
        result['max_expected_actual_ULP']=max((row['expected_actual_ULP'] for row in rows),default=0)
        result['unity_representation']='EXACT' if not result['unexplained_influences'] else 'NUMERIC_MISMATCH'
        result['numeric_stages']=rows  # Private reports remain external; publish only aggregates.
        result['reason']='NONE'
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        result['reason']=str(exc) if isinstance(exc,ValueError) else 'NUMERIC_CONTEXT_INCOMPLETE'
        result['unexplained_influences']=result['total_influences']
    return result


def d_identity_metrics(before, observed, *, skin_context=None):
    report=skin_parity_report(before,observed,skin_context)
    try:result=_legacy_d_identity_metrics(before,observed)
    except (KeyError,IndexError,TypeError):
        result=dict(shape_geometry=dict(status='UNPROVEN'),skin_bone_weight_binding='SKIN_BINDING_MISMATCH')
    result['skin_report']=report
    return result


def skin_export_context(folder, export, capture, policy_root=None, deformation=None):
    """Bind actual FBX bytes, public API Mesh identity and the existing import policy."""
    from unitypackage_blender_importer.tests.blender_small_weight_real_check import raw_skin_weights
    observed,=capture['meshes']
    path=Path(folder)/(export['mode']+'.fbx')
    policy_path=Path(policy_root or Path(folder)/'Assets/VAPBExport')/('SkinWeightPolicy_'+observed['guid']+'.json')
    # Missing policy is an unsupported context, never a guessed min=0 setting.
    policy=json.loads(policy_path.read_text()) if policy_path.exists() else {}
    try:raw=raw_skin_weights(Path(folder),path.name)
    except (ValueError,KeyError,IndexError):return {}
    context=dict(unity_version=capture['editor_version'],
        fbx_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),expected_fbx_sha256=export['fbx_sha256'],
        observed_fbx_sha256=capture['input_sha256'],mesh_guid=observed['guid'],
        mesh_local_id=observed['local_id'],preprocess_policy=policy,
        raw_weights=raw)
    if deformation:context['deformation']=deformation
    return context


def skin_deformation_measurement(before, observed):
    native=unity_row(observed);metrics={}
    if before.get('baked_positions') and native.get('baked_positions'):
        measurement=position_metric(before['vertex_control_point_indices'],before['baked_positions'],
            native['vertex_control_point_indices'],native['baked_positions'])
        if 'maximum_distance' in measurement:metrics['Blender_Unity_evaluated_capture_position_max_m']=measurement['maximum_distance']
    if native.get('cpu_positions') and native.get('baked_positions'):
        measurement=position_metric(native['vertex_control_point_indices'],native['cpu_positions'],
            native['vertex_control_point_indices'],native['baked_positions'])
        if 'maximum_distance' in measurement:metrics['CPU_Unity_BakeMesh_capture_position_max_m']=measurement['maximum_distance']
    return dict(provenance='EXACT_REVISION_CAPTURE_BAKEMESH_TRUE_TRANSFORMPOINT_EXISTING_POSE',metrics=metrics) if metrics else None


def _legacy_d_identity_metrics(before, observed):
    """Verify explicitly assigned export labels against the exact output revision."""
    labels=observed['vertex_control_point_indices']
    mesh_matrix=observed['renderer_local_to_world']
    def direction(v):
        xyz=[sum(mesh_matrix[col*4+row]*v[axis] for col,axis in enumerate(('x','y','z'))) for row in range(3)]
        return [-xyz[0],-xyz[2],xyz[1]]
    expected={s['export_label']:s for s in before['shapes']}
    frames=observed['shape_frames']
    actual={f['name']:f for f in frames}
    assert len(actual)==len(frames),'DUPLICATE_SHAPE_EXPORT_LABEL'
    shape=dict(status='NOT_APPLICABLE' if not expected and not actual else 'SHAPE_EXPORT_LABEL_MISMATCH')
    if expected and set(expected)==set(actual):
        rows=[]
        for label,source in expected.items():
            target=actual[label]
            assert label.startswith('VAPB-EXP-SHAPE-') and target['frame']==0 and target['weight']==100
            rows.append(position_metric(before['vertex_control_point_indices'],source['deltas'],labels,
                                        [direction(v) for v in target['delta_positions']]))
        shape=dict(status='EXACT' if all(r['status']=='EXACT' for r in rows) else 'SHAPE_DELTA_MISMATCH',
                   frames=len(rows),maximum_distance=max(r.get('maximum_distance',float('inf')) for r in rows))
    bones={b['index']:b.get('export_label') for b in observed['bones']}
    expected_weights=before['skin_weights']
    observed_weights=[[] for _ in labels]
    for value in observed['bone_weights']:
        observed_weights[value['vertex']].append(dict(group=bones[value['bone']],weight=value['weight']))
    def keyed(point_ids,weights):
        from collections import defaultdict
        result=defaultdict(set)
        for cp,row in zip(point_ids,weights):
            result[cp].add(tuple(sorted((v['group'],round(v['weight'],6)) for v in row if v['weight']>0)))
        return dict(result)
    groups={w['group'] for row in expected_weights for w in row if w['weight']>0}
    if not groups and not observed['bone_weights']:
        skin='NOT_APPLICABLE'
    elif any(not label or not label.startswith('VAPB-EXP-BONE-') for label in groups) or len(set(bones.values()))!=len(bones):
        skin='BONE_EXPORT_LABEL_UNPROVEN'
    else:
        skin='EXACT' if keyed(before['vertex_control_point_indices'],expected_weights)==keyed(labels,observed_weights) else 'SKIN_BINDING_MISMATCH'
    return dict(shape_geometry=shape,skin_bone_weight_binding=skin,
                authority='EXPLICIT_TEMPORARY_EXPORT_LABELS_AND_EXACT_FBX_SHA256')


def main():
    import bpy
    from io_scene_fbx import import_fbx
    project,blender_report,output=map(Path,sys.argv[sys.argv.index('--')+1:])
    assert not output.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    manifest=read(project/'ControlPointManifest.json')
    spec,=manifest['meshes']
    report=read(blender_report)
    assert report['manifest']==manifest and report['marker_noninterference']
    a_capture=read(project/'A_stamped.json')
    assert a_capture['input_sha256']==manifest['stamped_fbx_sha256']
    assert a_capture['input_meta_sha256']==manifest['source_meta_sha256']
    # Bounded one-source scene: cover every observed Mesh, with no candidate selection.
    ar,=a_capture['meshes']; br,=report['B']; a=unity_row(ar)
    result=dict(source_fbx_sha256=manifest['source_fbx_sha256'],
                A_vs_B=compare(a,br,spec['uv_channel']),D=[])
    original_geom=import_fbx.blen_read_geom
    c_rows=[]
    for label,stamped in [('C_unmarked',False),('C_stamped',True)]:
        path=project/(label+'.fbx'); expected=read(project/'UnityACStatus.json')[label.lower()+'_sha256']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        bpy.ops.wm.read_factory_settings(use_empty=True)
        meshes={}
        def capture(*args):
            mesh=original_geom(*args);meshes[int(args[1].props[0])]=mesh;return mesh
        try:
            import_fbx.blen_read_geom=capture
            assert bpy.ops.import_scene.fbx(filepath=str(path))=={'FINISHED'}
        finally:
            import_fbx.blen_read_geom=original_geom
        rows=[]
        for uid,mesh in meshes.items():
            obj,=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data is mesh]
            if mesh.shape_keys:
                for key in mesh.shape_keys.key_blocks:key.value=0
            bpy.context.view_layer.update()
            rows.append(observe(obj,uid,spec['uv_channel'] if stamped else None,spec['control_point_count']))
        row,=rows;c_rows.append(row)
    for field in ('positions','triangles','polygons','corner_normals','skin_weights'):
        assert c_rows[0][field]==c_rows[1][field],'C_STAMP_INTERFERENCE_'+field
    result['C_marker_noninterference']=True
    result['A_vs_C']=compare(a,c_rows[1],spec['uv_channel'])
    result['C_blender']=c_rows[1]
    for export in report['exports']:
        label=export['mode']; capture=read(project/(label+'.json'))
        assert capture['input_sha256']==export['fbx_sha256']
        before,=export['pre_export']; observed,=capture['meshes']
        result['D'].append(dict(mode=label,fbx_sha256=export['fbx_sha256'],
             comparison=compare(before,unity_row(observed),spec['uv_channel']),
             identity=d_identity_metrics(before,observed,skin_context=skin_export_context(project,export,capture,
                deformation=skin_deformation_measurement(before,observed))),
             source_unchanged=export['source_objects_unchanged'],raw_polygon_sizes=export['raw_polygon_sizes']))
    result['unity_ac_status']=read(project/'UnityACStatus.json')
    result['unity_d_status']=read(project/'UnityDStatus.json')
    output.write_text(json.dumps(result,indent=2))
    print('ABCD_MEASURED A_B=%s A_C=%s D=%s' % (result['A_vs_B']['topology'],result['A_vs_C']['topology'],
           ','.join(r['mode']+':'+r['comparison']['topology'] for r in result['D'])))


if __name__=='__main__':main()
