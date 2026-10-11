"""Owned one-CP weight edit; normal production exporter, no Unity observation mutation."""
import sys,json,hashlib,struct,importlib.util
from pathlib import Path
import bpy
from io_scene_fbx import parse_fbx
args=sys.argv[sys.argv.index('--')+1:];repo=Path(args[args.index('--repo')+1]);work=Path(args[args.index('--work')+1]);phase=args[args.index('--phase')+1];run=work/phase
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):(run/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def state(obj):
    rig = obj.modifiers[0].object
    return dict(vertices=[list(v.co) for v in obj.data.vertices], faces=[list(p.vertices) for p in obj.data.polygons], face_materials=[p.material_index for p in obj.data.polygons], uv=[list(x.uv) for x in obj.data.uv_layers.active.data], corner_vertices=[l.vertex_index for l in obj.data.loops], weights=[[[g.group, g.weight] for g in v.groups] for v in obj.data.vertices], groups=[g.name for g in obj.vertex_groups], matrix=[list(row) for row in obj.matrix_world], bones=[dict(uid=str(b.get('_vapb_fbx_model_uid', '')), realization=str(b.get('_vapb_fbx_bone_realization_id', '')), parent_uid=str(b.parent.get('_vapb_fbx_model_uid', '')) if b.parent else '', matrix=[list(row) for row in b.matrix_local]) for b in rig.data.bones], materials=[dict(guid=str(s.material.get('unity_material_guid', '')), file_id=str(s.material.get('unity_material_file_id', ''))) for s in obj.material_slots], shape_count=len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0, model_uid=str(obj.get('_vapb_fbx_model_uid', '')), geometry_uid=str(obj.get('_vapb_fbx_geometry_uid', '')), receipt={k: str(obj[k]) for k in obj.keys() if 'receipt' in k or 'realization' in k})

spec=importlib.util.spec_from_file_location('_strict',repo/'tests/strict_source_import.py');strict=importlib.util.module_from_spec(spec);spec.loader.exec_module(strict);addon=strict.load_source_package(repo);addon.register()
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
old=work.parent/'holmes-source-skin-cp-20261012-02'
try:
 saved=work/'B-authored.blend';input_blend=work/'B-base.blend' if phase=='edit' else saved
 assert bpy.ops.wm.open_mainfile(filepath=str(input_blend))=={'FINISHED'}
 obj,=[o for o in bpy.context.scene.objects if o.type=='MESH'];rig=obj.modifiers[0].object
 before=state(obj);before['rig_matrix']=[list(r) for r in rig.matrix_world]
 baseline=json.loads((old/'B-final-export/result.json').read_text(encoding='utf-8'))
 if phase=='edit':
  assert {k:before[k] for k in baseline['state']}==baseline['state']
  task=baseline['task'];receipt=task['realization_id'];assert before['receipt']['_vapb_fbx_realization_id']==receipt
  raw,_=parse_fbx.parse(str(old/'B-final-export/Export.fbx'),use_namedtuple=True);objects=next(n for n in raw.elems if n.id==b'Objects');nodes={n.props[0]:n for n in objects.elems};conn=next(n for n in raw.elems if n.id==b'Connections')
  def marker(n,k):
   v=[p.props[-1] for c in n.elems if c.id==b'Properties70' for p in c.elems if p.id==b'P' and p.props and p.props[0]==k]
   assert len(v)<=1;return v[0].decode() if v else None
  model,=[n for n in objects.elems if n.id==b'Model' and n.props[2]==b'Mesh' and marker(n,b'_vapb_fbx_realization_id')==receipt]
  gids=[r.props[1] for r in conn.elems if r.id==b'C' and r.props[0]==b'OO' and r.props[2]==model.props[0] and nodes[r.props[1]].id==b'Geometry'];assert len(gids)==1;geom=nodes[gids[0]]
  vs=list(next(n.props[0] for n in geom.elems if n.id==b'Vertices'));poly=list(next(n.props[0] for n in geom.elems if n.id==b'PolygonVertexIndex'))
  assert vs==[v for p in before['vertices'] for v in p]
  assert [(-i-1 if i<0 else i) for i in poly]==before['corner_vertices']
  uv,=[n for n in geom.elems if n.id==b'LayerElementUV' and n.props[0]==0];uvs=list(next(n.props[0] for n in uv.elems if n.id==b'UV'));uvi=list(next(n.props[0] for n in uv.elems if n.id==b'UVIndex'))
  assert [[uvs[i*2],uvs[i*2+1]] for i in uvi]==before['uv']
  assert len({tuple(v) for v in before['vertices']})==4
  target_cp=0;old_row=next(p for p in task['weight_transport']['points'] if p['cp']==target_cp)
  mapped={b['realization']:b['uid'] for b in before['bones']};assert all(mapped[x['edited_bone_realization_id']]==x['source_model_uid'] for x in task['bone_mappings'])
  old_receipts=dict(zip(old_row['bone_realization_ids'],old_row['raw_bits']));new_values={r:(.625 if v==bits(.75) else .375) for r,v in old_receipts.items()};assert sorted(old_receipts.values())==sorted([bits(.75),bits(.25)])
  group_receipts={obj.vertex_groups[bpy_b.name].index:str(bpy_b['_vapb_fbx_bone_realization_id']) for bpy_b in rig.data.bones}
  actual={group_receipts[g.group]:bits(g.weight) for g in obj.data.vertices[target_cp].groups};assert actual==old_receipts
  for g in list(obj.data.vertices[target_cp].groups):obj.vertex_groups[g.group].add([target_cp],new_values[group_receipts[g.group]],'REPLACE')
  after=state(obj);after['rig_matrix']=[list(r) for r in rig.matrix_world]
  assert {k:v for k,v in before.items() if k!='weights'}=={k:v for k,v in after.items() if k!='weights'}
  assert before['weights'][1:]==after['weights'][1:]
  assert bpy.ops.wm.save_as_mainfile(filepath=str(saved))=={'FINISHED'}
  proof={'status':'PASS','selected_cp':target_cp,'source_geometry_uid':before['geometry_uid'],'realization_id':receipt,'prior_export_sha256':sha(old/'B-final-export/Export.fbx'),'full_point_stream_and_polygon_corner_uv_exact':True,'bone_receipt_uid_join_exact':True,'prior_native_cp_marker_control':'B-final-weight.json CP0 -> Unity vertex3','before':before,'after':after,'new_by_bone_receipt':new_values,'blend_sha256':sha(saved)}
  write('result.json',proof);write('state.json',after)
 else:
  expected=json.loads((work/'edit/state.json').read_text(encoding='utf-8'));assert before==expected,'Reopen state changed'
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  output=work/'AuthoredWeightOutput.unitypackage';assert not output.exists()
  assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output))=={'FINISHED'}
  after=state(obj);after['rig_matrix']=[list(r) for r in rig.matrix_world];assert after==before
  assets=RawAssetRepository(output).read_all();original=RawAssetRepository(work/'Source.unitypackage').read_all();by={a.guid:a for a in assets};assert all(by[a.guid].asset_bytes==a.asset_bytes and by[a.guid].meta_bytes==a.meta_bytes for a in original)
  manifest=json.loads(next(a.asset_bytes for a in assets if a.pathname=='Assets/VAPBExport/manifest.json'));t,=manifest['reference_rebind_tasks'];assert t['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1';assert 'weight_transport' in t
  old_t=baseline['task'];new_rows={r['cp']:r for r in t['weight_transport']['points']};old_rows={r['cp']:r for r in old_t['weight_transport']['points']};assert set(new_rows)==set(old_rows)==set(range(4))
  for cp in range(4):
   old_bits=dict(zip(old_rows[cp]['bone_realization_ids'],old_rows[cp]['raw_bits']));new_bits=dict(zip(new_rows[cp]['bone_realization_ids'],new_rows[cp]['raw_bits']))
   want={r:bits(.625 if v==bits(.75) else .375) for r,v in old_bits.items()} if cp==0 else old_bits
   assert new_bits==want;assert dict(zip(new_rows[cp]['bone_realization_ids'],new_rows[cp]['expected_bits']))==want
  fbx=by[t['model_guid']];(run/'Export.fbx').write_bytes(fbx.asset_bytes);write('manifest.json',manifest)
  write('result.json',{'status':'PASS','reopen_state_exact':True,'state':after,'task':t,'input_sha256':sha(work/'Source.unitypackage'),'output_sha256':sha(output),'fbx_sha256':sha(run/'Export.fbx'),'source_assets_preserved':True,'expected_frozen_before_unity':True})
finally:addon.unregister()
