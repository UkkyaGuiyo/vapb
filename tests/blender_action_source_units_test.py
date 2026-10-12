# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the production carrier callsite against two serialized source unit conventions."""
from pathlib import Path
import ast,importlib.util,json,sys,tempfile
import bpy
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from strict_source_import import load_source_package
load_source_package(root)
from unitypackage_blender_importer.export.action_carrier import export_action_carrier
from unitypackage_blender_importer.blender.fbx_witness import source_export_scale_options
from io_scene_fbx import parse_fbx
spec=importlib.util.spec_from_file_location('unit_fixture',root/'tests/blender_bone_merge_test.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
fixture.reset()
rig=fixture.rig('Source unit fixture',(0.2,-0.1,0.3),(0,0,0),extra=True)
rows=[]
for i,name in enumerate(('Root','Extra')):
 rig.pose.bones[name]['_vapb_fbx_bone_realization_id']='unit-'+name.lower()
 rows.append(dict(edited_bone_realization_id='unit-'+name.lower(),source_model_uid=str(i+1)))
child=rig.pose.bones['Extra'];child.rotation_mode='XYZ'
for frame,z in ((1,0.0),(10,0.2)):
 child.rotation_euler.z=z;child.keyframe_insert(data_path='rotation_euler',index=2,frame=frame)
bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
# Execute the actual production call expression, without copying it or asserting
# its keyword spelling. Acceptance is independently serialized units/local rest.
tree=ast.parse((root/'operators/export_unitypackage.py').read_text(encoding='utf-8'))
call,=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='export_action_carrier']
expression=compile(ast.Expression(body=call),'production_carrier_call','eval')
def inspect(path):
 decoded,_=parse_fbx.parse(str(path),use_namedtuple=True)
 settings=next(n for n in decoded.elems if n.id==b'GlobalSettings')
 props=next(n for n in settings.elems if n.id==b'Properties70')
 units=next(p.props[-1] for p in props.elems if p.id==b'P' and p.props[0]==b'UnitScaleFactor')
 definitions=next(n for n in decoded.elems if n.id==b'Definitions')
 model=next(n for n in definitions.elems if n.id==b'ObjectType' and n.props[0]==b'Model')
 template=next(n for n in model.elems if n.id==b'PropertyTemplate')
 defaults=next(n for n in template.elems if n.id==b'Properties70')
 default_translation=tuple(next(p.props[-3:] for p in defaults.elems if p.id==b'P' and p.props[0]==b'Lcl Translation'))
 objects=next(n for n in decoded.elems if n.id==b'Objects');bones={}
 for node in objects.elems:
  if node.id!=b'Model':continue
  ps=next((n for n in node.elems if n.id==b'Properties70'),None)
  if ps is None:continue
  uid=next((p.props[-1] for p in ps.elems if p.id==b'P' and p.props[0]==b'_vapb_fbx_bone_realization_id'),None)
  if uid is not None:
   assert uid not in bones
   bones[uid]=tuple(next((p.props[-3:] for p in ps.elems if p.id==b'P' and p.props[0]==b'Lcl Translation'),default_translation))
 return units,bones
report=dict(status='RUNNING',conventions=[],unity='NOT_RUN')
try:
 with tempfile.TemporaryDirectory(prefix='vapb_action_units_') as temp:
  folder=Path(temp)
  for mode in ('FBX_SCALE_NONE','FBX_SCALE_ALL'):
   source=folder/(mode+'-source.fbx');carrier=folder/(mode+'-carrier.fbx')
   assert bpy.ops.export_scene.fbx(filepath=str(source),use_selection=True,object_types={'ARMATURE'},use_custom_props=True,add_leaf_bones=False,bake_anim=False,apply_scale_options=mode)=={'FINISHED'}
   scale_options=source_export_scale_options(source,bpy.context.scene.unit_settings.scale_length)
   eval(expression,dict(export_action_carrier=export_action_carrier,context=bpy.context,rig=rig,carrier=carrier,bones=rows,scale_options=scale_options))
   source_units,a=inspect(source);carrier_units,b=inspect(carrier)
   assert set(a)==set(b)=={b'unit-root',b'unit-extra'}
   error=max(abs(x-y) for uid in a for x,y in zip(a[uid],b[uid]))
   report['conventions'].append(dict(policy=mode,source_units=source_units,carrier_units=carrier_units,bone_local_translation_max_error=error))
   assert source_units==carrier_units and error<1e-5,'ACTION_SOURCE_UNIT_OR_LOCAL_REST_MISMATCH'
 report['status']='PASS'
except Exception as error:
 report.update(status='FAIL',reason=str(error));raise
finally:
 if '--' in sys.argv:Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('ACTION_SOURCE_UNITS',json.dumps(report))
