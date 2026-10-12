# SPDX-License-Identifier: GPL-3.0-or-later
"""Unkeyed mapped descendants must retain their evaluated baked channels."""
from pathlib import Path
import importlib.util
import json
import hashlib
import sys
import tempfile
import bpy

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from strict_source_import import load_source_package
load_source_package(root)
spec=importlib.util.spec_from_file_location('connected_fixture',root/'tests/blender_bone_merge_test.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
from unitypackage_blender_importer.export.action_carrier import export_action_carrier
fixture.reset()
rig=fixture.rig('Connected carrier source',(0.2,-0.1,0.3),(0,0,0),extra=True,chain=True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
child=rig.data.edit_bones['Extra'];child.head=rig.data.edit_bones['Root'].tail;child.use_connect=True
bpy.ops.object.mode_set(mode='OBJECT')
mesh,_=fixture.mesh('Connected Skin',rig,chain=True)
rows=[]
for i,name in enumerate(('Root','Extra','Tip')):
 pose=rig.pose.bones[name];pose['_vapb_fbx_bone_realization_id']='connected-'+name.lower()
 rows.append(dict(edited_bone_realization_id=pose['_vapb_fbx_bone_realization_id'],source_model_uid=str(i+1)))
for frame,factor in ((1,0.0),(5,0.5),(10,1.0)):
 parent=rig.pose.bones['Root'];child=rig.pose.bones['Extra'];child.rotation_mode='XYZ'
 child.rotation_euler.z=-0.4*factor;child.keyframe_insert(data_path='rotation_euler',index=2,frame=frame)
 child.scale=(1+0.15*factor,1+0.15*factor,1+0.15*factor);child.keyframe_insert(data_path='scale',frame=frame)
bpy.context.scene.frame_set(1)
action=rig.animation_data.action
curves=lambda:tuple((c.data_path,c.array_index,tuple(tuple(k.co) for k in c.keyframe_points)) for c in action.layers[0].strips[0].channelbag(rig.animation_data.action_slot).fcurves)
original_curves=curves()
rest=lambda:tuple((b.name,b.parent.name if b.parent else '',b.use_connect,b.inherit_scale,b.use_inherit_rotation,b.use_local_location,b.use_relative_parent,tuple(tuple(x) for x in b.matrix_local)) for b in rig.data.bones)
original_rest=rest()
assert rig.data.bones['Extra'].use_connect
samples=(1,5.5,10)
expected={};vertices={}
for f in samples:
 bpy.context.scene.frame_set(int(f),subframe=f%1)
 expected[f]={p.get('_vapb_fbx_bone_realization_id'):rig.matrix_world@p.matrix.copy() for p in rig.pose.bones}
 vertices[f]=fixture.evaluated_world_vertices(mesh)
bpy.context.scene.frame_set(1)
with tempfile.TemporaryDirectory(prefix='vapb_connected_action_') as tmp:
 output=Path(tmp)/'Carrier.fbx'
 result=export_action_carrier(bpy.context,rig,output,rows)
 assert result['animated_bone_realization_ids']==['connected-extra','connected-tip']
 assert result['animation_curve_count']>0 and output.is_file()
 from unitypackage_blender_importer.export.action_carrier import _inspect_curve_targets
 artifact_hash=hashlib.sha256(output.read_bytes()).hexdigest()
 declared_labels={'VAPB-BONE-connected-extra'}
 try:_inspect_curve_targets(output,declared_labels,{'connected-extra':'VAPB-BONE-connected-extra'})
 except ValueError as error:assert str(error)=='ACTION_CARRIER_UNEXPECTED_BAKED_MOTION'
 else:raise AssertionError('Undeclared moving target accepted')
 try:_inspect_curve_targets(output,declared_labels,{'connected-extra':'VAPB-BONE-connected-extra','foreign-receipt':'VAPB-BONE-connected-tip'})
 except ValueError as error:assert str(error)=='ACTION_CARRIER_BONE_IDENTITY_INVALID'
 else:raise AssertionError('Foreign receipt accepted for derived binding')
 assert hashlib.sha256(output.read_bytes()).hexdigest()==artifact_hash
 assert rest()==original_rest and curves()==original_curves and rig.animation_data.action==action
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=str(output),use_custom_props=True,use_anim=True,anim_offset=0,automatic_bone_orientation=False)
 carrier,=[o for o in bpy.data.objects if o not in before and o.type=='ARMATURE']
 marked={p.get('_vapb_fbx_bone_realization_id'):p for p in carrier.pose.bones}
 assert set(marked)=={'connected-root','connected-extra','connected-tip'}
 assert marked['connected-extra'].parent==marked['connected-root']
 assert marked['connected-root'].parent is None
 assert marked['connected-tip'].parent==marked['connected-extra']
 returned=mesh.copy();returned.data=mesh.data.copy();bpy.context.collection.objects.link(returned)
 returned.modifiers['Skin'].object=carrier
 for name in ('Root','Extra','Tip'):returned.vertex_groups[name].name=marked['connected-'+name.lower()].name
 matrix_error=vertex_error=0.0
 for f in samples:
  bpy.context.scene.frame_set(int(f),subframe=f%1)
  for uid,p in marked.items():
   actual=carrier.matrix_world@p.matrix
   error=max(abs(expected[f][uid][i][j]-actual[i][j]) for i in range(4) for j in range(4))
   matrix_error=max(matrix_error,error)
   assert fixture.close_matrix(expected[f][uid],actual),(f,uid,error)
  err=max((x-y).length for x,y in zip(vertices[f],fixture.evaluated_world_vertices(returned)))
  vertex_error=max(vertex_error,err);assert err<1e-4,(f,err)
 assert rest()==original_rest and curves()==original_curves
 observation=dict(status='PASS',authored_bones=1,required_carrier_bindings=result['animated_bone_realization_ids'],original_connections_rest_curves_preserved=True,uid_parent_graph_exact=True,unknown_moving_target_refused=True,derived_marker_mismatch_refused=True,artifact_unchanged=True,samples=3,matrix_max_error=matrix_error,skin_vertex_max_error=vertex_error,threshold=1e-4,unity='NOT_RUN')
 if '--' in sys.argv:Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(observation,indent=2),encoding='utf-8')
 print('CONNECTED_DESCENDANT_CARRIER_PASS',json.dumps(observation))
