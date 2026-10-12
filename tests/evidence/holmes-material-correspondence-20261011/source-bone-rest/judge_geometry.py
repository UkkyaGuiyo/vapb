import argparse,hashlib,importlib.util,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=read(a.work/'native/native.json');n=read(a.work/'native/deformation.json');x=read(a.work/'green-export/blender-evaluated.json');ex=read(a.work/'green-export/result.json')
assert f['apply'] and f['repeat_apply'] and f['repeat_variant_bytes_unchanged'] and f['repeat_variant_meta_unchanged'] and f['repeat_variant_semantics_unchanged']
assert f['source']==f['source_after']
assert n['status']=='OBSERVED' and not n['error'] and n['assets_bytes_preserved']
assert f['package_sha256']==n['package_sha256']==ex['output_sha256']==sha(a.work/'BoneRestGreenOutput.unitypackage')
assert n['mesh_asset_sha256']==ex['export_fbx_sha256']
assert f['finalizer_sha256']==n['finalizer_sha256']==sha(a.repo/'unity_editor/Editor/VapbModelSkinFinalizer.cs')
assert n['mesh_guid']==f['variant']['mesh']['guid'] and n['mesh_file_id']==f['variant']['mesh']['file_id']
obs=[read(p) for p in (a.work/'native').glob('weight-observation-*.json')]
matching=[o for o in obs if o['skin']['vertices']==n['positions'] and o['skin']['weights']==f['variant']['weights'] and o['skin']['shape_data']==f['variant']['shape_data']]
assert matching
first=matching[0];cp=[int(v['x'])-1 for v in first['cp_marker']]
assert set(cp)==set(range(8)) and all(v['x']==c+1 and v['y']==.375 for v,c in zip(first['cp_marker'],cp))
assert all(o['cp_marker']==first['cp_marker'] and o['bone_receipts']==first['bone_receipts'] for o in matching)
metricfile=a.repo/'tests/geometry_abcd_metrics.py';spec=importlib.util.spec_from_file_location('_metric',metricfile);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.POSITION_TOLERANCE==3e-5
convert=lambda p:[-p['x'],-p['z'],p['y']]
bake=list(map(convert,n['baked_true_world_positions']));cpu=list(map(convert,n['cpu_weighted_world_positions']))
bn=m.position_metric(list(range(8)),x['points'],cp,bake);cn=m.position_metric(cp,cpu,cp,bake)
assert bn['maximum_distance']<=m.POSITION_TOLERANCE and cn['maximum_distance']<=m.POSITION_TOLERANCE
prior=read(a.work/'prior-protected-before.json');assert all(sha(Path(p))==h for p,h in prior.items())
assert f['variant']['source_bones']==f['source']['bones'] and f['variant']['source_root']==f['source']['root']
assert f['variant']['weights']==f['post_import']['weights'] and f['variant']['shape_weights']==f['post_import']['shape_weights']==[0.,0.,0.]
assert f['variant']['bone_local']!=f['source']['bone_local']
result=dict(status='PASS',blender_to_BakeMesh_true=bn,CPU_to_BakeMesh_true=cn,position_tolerance_m=m.POSITION_TOLERANCE,original_source_state_exact=True,prior_file_count=len(prior),prior_hashes_exact=True,linked_original_bone_root_identity=True,rest_locals_changed=True,weights_Shapes_defaults_preserved=True,duplicate_cp_capture_count=len(matching),cp_count=8,native_vertices=len(cp),package_sha256=f['package_sha256'],consumer_sha256=f['finalizer_sha256'],metric_sha256=sha(metricfile),axis_contract=['-x','-z','y'],restart_NOT_RUN=True)
(a.work/'geometry-judgment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(a.work/'selected-cp-observation.json').write_text(json.dumps(first,indent=2),encoding='utf-8')
print('SOURCE_REST_GREEN_GEOMETRY',bn['maximum_distance'],cn['maximum_distance'],'prior preserved',len(prior))
