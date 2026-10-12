"""Existing marker position metric and world-axis contract; frozen before capture."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
b=a.work.parent/'holmes-source-skin-deleted-shape-20261012-11'
metric_file=a.repo/'tests/geometry_abcd_metrics.py'
spec=importlib.util.spec_from_file_location('_existing_metric',metric_file);metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
assert metrics.POSITION_TOLERANCE==3e-5
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
x=read(a.work/'blender-observed/result.json');n=read(a.work/'native/native.json');f=read(b/'native-green/native.json');ex=read(b/'green-export/result.json');ed=read(b/'edit/result.json');obs=read(next((b/'native-green').glob('weight-observation-*.json')))
assert n['status']=='OBSERVED' and not n['error'] and x['status']=='OBSERVED'
assert x['blend_sha256']==ed['blend_sha256']==sha(b/'Authored.blend') and x['blend_bytes_preserved']
assert n['package_sha256']==ex['output_sha256']==sha(b/'DeletedShapeGreenOutput.unitypackage')
assert n['finalizer_sha256']==f['finalizer_sha256']
assert n['mesh_guid']==f['variant']['mesh']['guid'] and n['mesh_file_id']==f['variant']['mesh']['file_id']
assert n['mesh_asset_sha256']==ex['export_fbx_sha256']
assert n['positions']==obs['skin']['vertices']==f['variant']['vertices']
assert n['shape_weights']==f['variant']['shape_weights']==[100.,0.] and x['active_values']==[1.,0.]
cp=[int(v['x'])-1 for v in obs['cp_marker']]
assert all(v['x']==i+1 and v['y']==.375 for v,i in zip(obs['cp_marker'],cp)) and set(cp)==set(range(8))
# Exactly the existing Unity world -> Blender world contract.
convert=lambda v:[-v['x'],-v['z'],v['y']]
true_points=list(map(convert,n['baked_true_world_positions']));cpu_points=list(map(convert,n['cpu_weighted_world_positions']));false_points=list(map(convert,n['baked_false_world_positions']))
blender_native=metrics.position_metric(x['vertex_control_point_indices'],x['baked_positions'],cp,true_points)
cpu_native=metrics.position_metric(cp,cpu_points,cp,true_points)
false_diagnostic=metrics.position_metric(cp,cpu_points,cp,false_points)
assert blender_native['maximum_distance']<=metrics.POSITION_TOLERANCE
assert cpu_native['maximum_distance']<=metrics.POSITION_TOLERANCE
before=read(a.work/'protected-before.json');project=b/'Project'
assert n['assets_bytes_preserved'] and all(q['before']==q['after'] for q in n['protected_files'])
assert {q['path']:q['sha256'] for q in before}=={q['path']:q['after'] for q in n['protected_files']}
assert all(sha(project/q['path'])==q['sha256'] for q in before)
assert sha(b/'Source.unitypackage')==ed['source_package_sha256']
result=dict(status='PASS',blender_to_actual_BakeMesh_true=blender_native,CPU_effective_skin_to_BakeMesh_true=cpu_native,BakeMesh_false_existing_diagnostic_only=false_diagnostic,position_tolerance_m=metrics.POSITION_TOLERANCE,metric_sha256=sha(metric_file),blend_sha256=x['blend_sha256'],package_sha256=n['package_sha256'],mesh_asset_sha256=n['mesh_asset_sha256'],source_package_sha256=ed['source_package_sha256'],protected_files_exact=True,active_values=x['active_values'],native_defaults=n['shape_weights'],cp_count=8,native_vertex_count=len(cp),pose_basis_max_identity_error=x['pose_basis_max_identity_error'],unity_to_blender_world_axes=['-x','-z','y'],identity_from_frozen_exact_CP_marker=True,product_code_changed=False,GUI_VRC_rendered_visual_not_run=True)
(a.work/'deformation-judgment.json').write_bytes(json.dumps(result,indent=2).encode())
print('ACTIVE_SHAPE_EVALUATED_GEOMETRY_PASS',blender_native['maximum_distance'],cpu_native['maximum_distance'])
