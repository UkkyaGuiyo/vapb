"""One owned source Skin and diagonal-only Edit Mode control; outputs stay external."""
import sys,json,hashlib,importlib.util
from pathlib import Path
import bpy,bmesh
args=sys.argv[sys.argv.index('--')+1:]
repo=Path(args[args.index('--repo')+1]);work=Path(args[args.index('--work')+1]);phase=args[args.index('--phase')+1]
run=work/phase
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value): (run/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
def state(obj):
 rig=obj.modifiers[0].object
 return dict(vertices=[list(v.co) for v in obj.data.vertices],faces=[list(p.vertices) for p in obj.data.polygons],face_materials=[p.material_index for p in obj.data.polygons],uv=[list(x.uv) for x in obj.data.uv_layers.active.data],corner_vertices=[l.vertex_index for l in obj.data.loops],weights=[[[g.group,g.weight] for g in v.groups] for v in obj.data.vertices],groups=[g.name for g in obj.vertex_groups],matrix=[list(row) for row in obj.matrix_world],bones=[dict(uid=str(b.get('_vapb_fbx_model_uid','')),realization=str(b.get('_vapb_fbx_bone_realization_id','')),parent_uid=str(b.parent.get('_vapb_fbx_model_uid','')) if b.parent else '',matrix=[list(row) for row in b.matrix_local]) for b in rig.data.bones],materials=[dict(guid=str(s.material.get('unity_material_guid','')),file_id=str(s.material.get('unity_material_file_id',''))) for s in obj.material_slots],shape_count=len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0,model_uid=str(obj.get('_vapb_fbx_model_uid','')),geometry_uid=str(obj.get('_vapb_fbx_geometry_uid','')),receipt={k:str(obj[k]) for k in obj.keys() if 'receipt' in k or 'realization' in k})
if phase=='source':
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 mesh=bpy.data.meshes.new('Quad');mesh.from_pydata([(-1,0,0),(1,0,0),(1,2,0),(-1,2,0)],[],[(0,1,2),(0,2,3)]);mesh.update();obj=bpy.data.objects.new('Quad',mesh);bpy.context.collection.objects.link(obj)
 uv=mesh.uv_layers.new(name='UVMap')
 for l in mesh.loops: uv.data[l.index].uv=((mesh.vertices[l.vertex_index].co.x+1)/2,mesh.vertices[l.vertex_index].co.y/2)
 mat=bpy.data.materials.new('SourceMaterial');mesh.materials.append(mat)
 bpy.ops.object.armature_add();rig=bpy.context.object;bpy.ops.object.mode_set(mode='EDIT');b0=rig.data.edit_bones[0];b0.name='Lower';b0.head=(0,0,0);b0.tail=(0,1,0);b1=rig.data.edit_bones.new('Upper');b1.head=(0,1,0);b1.tail=(0,2,0);b1.parent=b0;b1.use_connect=True;bpy.ops.object.mode_set(mode='OBJECT')
 for name in ['Lower','Upper']:obj.vertex_groups.new(name=name)
 for i in range(4):
  obj.vertex_groups[0].add([i],0.75 if i<2 else 0.25,'REPLACE');obj.vertex_groups[1].add([i],0.25 if i<2 else 0.75,'REPLACE')
 obj.parent=rig;mod=obj.modifiers.new('Skin','ARMATURE');mod.object=rig
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.fbx(filepath=str(work/'Source.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=False,axis_forward='-Z',axis_up='Y')
 write('result.json',dict(status='PASS',fbx_sha256=sha(work/'Source.fbx'),vertices=4,triangles=2,bones=2));sys.exit(0)
spec=importlib.util.spec_from_file_location('_strict',repo/'tests/strict_source_import.py');strict=importlib.util.module_from_spec(spec);spec.loader.exec_module(strict);addon=strict.load_source_package(repo);addon.register()
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
try:
 case=phase[0];package=work/'Source.unitypackage';saved=work/(case+'.blend')
 if phase.endswith('save'):
  bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
  assert bpy.ops.import_scene.unitypackage(filepath=str(package),import_mode='RECONSTRUCT',keep_extracted=True,source_storage_directory=str(work/(case+'-sources')))=={'FINISHED'}
 else: assert bpy.ops.wm.open_mainfile(filepath=str(saved))=={'FINISHED'}
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1;obj=meshes[0];assert len(obj.data.vertices)==4 and len(obj.data.polygons)==2
 before=state(obj)
 if phase=='B-save':
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data)
  for e in bm.edges:e.select_set(False)
  interior=[e for e in bm.edges if len(e.link_faces)==2];assert len(interior)==1;interior[0].select_set(True)
  assert bpy.ops.mesh.edge_rotate(use_ccw=False)=={'FINISHED'};bpy.ops.object.mode_set(mode='OBJECT')
 after=state(obj)
 for k in ['vertices','weights','groups','matrix','bones','materials','shape_count','model_uid','geometry_uid','receipt']:assert before[k]==after[k],k
 if phase.endswith('save'):
  assert bpy.ops.wm.save_as_mainfile(filepath=str(saved))=={'FINISHED'};write('state.json',after);write('result.json',dict(status='PASS',before=before,after=after,blend_sha256=sha(saved)));sys.exit(0)
 expected=json.loads((work/(case+'-save/state.json')).read_text(encoding='utf-8'));assert expected==after,'Reopen state changed'
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 output=work/(case+'Output.unitypackage');assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))=={'FINISHED'};assert state(obj)==after
 assets=RawAssetRepository(output).read_all();source=RawAssetRepository(package).read_all();by={a.guid:a for a in assets};assert all(by[a.guid].asset_bytes==a.asset_bytes and by[a.guid].meta_bytes==a.meta_bytes for a in source)
 manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'));assert len(manifest['reference_rebind_tasks'])==1 and manifest['reference_rebind_tasks'][0]['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1'
 (run/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 task=manifest['reference_rebind_tasks'][0];fbx=next(a for a in assets if a.guid==task['model_guid']);(run/'Export.fbx').write_bytes(fbx.asset_bytes)
 write('result.json',dict(status='PASS',state=after,input_sha256=sha(package),output_sha256=sha(output),fbx_sha256=sha(run/'Export.fbx'),source_assets_preserved=True,task=task))
finally:addon.unregister()
