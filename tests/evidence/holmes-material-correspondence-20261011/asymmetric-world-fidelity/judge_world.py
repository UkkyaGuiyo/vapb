"""HOLMES07 fixed pre-consumer oracle; world geometry/Material/normal/front winding."""
import argparse,copy,datetime,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def vec(p): return [p[k] for k in ('x','y','z')]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(p):
 n=math.sqrt(dot(p,p));assert n>0;return [v/n for v in p]
def matpoint(m,p): return [sum(m[j*4+i]*p[j] for j in range(3))+m[12+i] for i in range(3)]
def normal(m,p):
 a=[[m[j*4+i] for j in range(3)] for i in range(3)]
 # Cyclic minors already incorporate row/column permutation signs.
 cof=[[cross(a[(i+1)%3],a[(i+2)%3])[j] for j in range(3)] for i in range(3)]
 det=dot(a[0],cof[0]);assert det>0
 return unit([dot(row,p)/det for row in cof])
def clean(value):
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in ('unity_source_package_path','unity_source_archive_path','unity_asset_path','unity_source_fbx_path','unity_archive_directory')}
 if isinstance(value,list):return [clean(v) for v in value]
 if isinstance(value,str) and ('C:\\Users\\' in value or 'C:/Users/' in value):return '(private provider path omitted)'
 return value

def judge(oracle,faces,cover):
 result={k:dict(status='PASS') for k in ('A_material','B_world','C_normal','D_winding')}
 rows={r['plane']:[] for r in oracle['faces']};errors=[];normal_errors=[];dots=[]
 for face in faces:
  candidates=[]
  for expected in oracle['faces']:
   ids=[]
   for p in face['positions']:
    possible=[i for i,w in enumerate(expected['world_corners']) if max(abs(x-y) for x,y in zip(p,w))<=oracle['world_component_tolerance']]
    if len(possible)!=1:break
    ids.append(possible[0])
   if len(ids)==len(face['positions']) and len(set(ids))==len(ids):candidates.append((expected,ids))
  if len(candidates)!=1:
   result['B_world']=dict(status='FAIL',reason='Unknown or ambiguous world face/corners')
   for k in ('A_material','C_normal','D_winding'):result[k]=dict(status='UNDETERMINED',reason='No independent geometric correspondence')
   continue
  expected,ids=candidates[0];rows[expected['plane']].append(ids)
  wanted={k:expected['material'][k] for k in ('guid','file_id')}
  if face['material']!=wanted:result['A_material']=dict(status='FAIL',reason='Actual face Material GUID/signedfileID differs')
  errors.extend(max(abs(x-y) for x,y in zip(p,expected['world_corners'][i])) for p,i in zip(face['positions'],ids))
  e=[max(abs(x-y) for x,y in zip(unit(n),expected['world_normal'])) for n in face['normals']]
  normal_errors.extend(e)
  if max(e)>oracle['normal_component_tolerance']:result['C_normal']=dict(status='FAIL',reason='Inverse-transpose world normal differs')
  geometric=unit(cross(sub(face['positions'][1],face['positions'][0]),sub(face['positions'][2],face['positions'][0])))
  d=dot(geometric,unit(expected['world_normal']));dots.append(d)
  if d<oracle['winding_dot_minimum']:result['D_winding']=dict(status='FAIL',reason='Native front winding points inward')
 coverage=[]
 for expected in oracle['faces']:
  ids=rows[expected['plane']];axis=next(i for i in range(3) if len({p[i] for p in expected['local_corners']})==1)
  axes=[i for i in range(3) if i!=axis];project=lambda p:[p[i] for i in axes]
  corners=[project(p) for p in expected['local_corners']]
  # Geometry coverage ignores triangle orientation; D tests actual orientation separately.
  area=lambda p:sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1]))
  oriented=[]
  for t in ids:
   points=[corners[i] for i in t]
   if area(points)*area(corners)<0:points=list(reversed(points))
   oriented.append(points)
  try:cover(corners,oriented);coverage.append(dict(plane=expected['plane'],triangles=len(ids),boundary_and_internal_diagonal='PASS'))
  except ValueError as e:result['B_world']=dict(status='FAIL',reason=str(e));coverage.append(dict(plane=expected['plane'],coverage='FAIL',reason=str(e)))
 result['B_world'].update(max_component_error=max(errors,default=None),coverage=coverage,tolerance=oracle['world_component_tolerance'])
 result['C_normal'].update(max_component_error=max(normal_errors,default=None),tolerance=oracle['normal_component_tolerance'])
 result['D_winding'].update(minimum_outward_dot=min(dots,default=None),dot_minimum=oracle['winding_dot_minimum'],basis_determinant=-1,unity_front='clockwise relative to camera',render_culling='NOT_RUN')
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);args=ap.parse_args();repo,work=args.repo,args.work
 out=repo/'tests/evidence/holmes-material-correspondence-20261011/asymmetric-world-fidelity';save=lambda name,data:(out/name).write_text(json.dumps(clean(data),indent=2)+'\n',encoding='utf-8')
 oracle=load(work/'oracle-frozen.json');freeze=load(work/'pre-consumer-freeze.json');native=load(work/'unity-run/native.json');exported=load(work/'export.json');replaced=load(work/'replace.json')
 assert sha(work/'oracle-frozen.json')==freeze['oracle_sha256']==sha(out/'oracle-frozen.json')
 assert native['status']==exported['status']==replaced['status']=='PASS'
 assert replaced['state']==exported['state']
 assert native['package_sha256']==freeze['package_sha256']==exported['package_sha256']==sha(work/'ReplacementOutput.unitypackage')
 assert native['fbx_sha256']==native['fbx_sha256_after']==exported['fbx_sha256']==sha(work/'Exported.fbx')
 assert native['manifest_sha256']==exported['manifest_sha256']==sha(work/'manifest.json')
 assert native['explicit_apply'] and native['apply_returned_true'] and native['finalizer_result']=='COMPLETE'
 assert native['repeat_apply_returned_true'] and native['repeat_materials_unchanged'] and native['repeat_mesh_unchanged'] and native['prefab_repeat_before']==native['prefab_repeat_after']
 assert native['material_bytes_preserved'] and native['subMeshCount']==len(native['groups'])==4
 assert native['prefab_sha256_before']=='ABSENT' and native['matching_realization_markers']==1
 assert all(sha(repo/n)==digest for n,digest in freeze['product_source_sha256'].items())
 assert native['finalizer_source_sha256']==freeze['product_source_sha256']['unity_editor/Editor/VapbFinalStateFinalizer.cs']
 sys.path.insert(0,str(repo/'tests/evidence/holmes-material-correspondence-20261011/topology-boundary'))
 from judge import cover,native_faces
 from read_input import parse,decode,child
 root,version=parse(work/'Exported.fbx',repo,Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/scripts/addons_core/io_scene_fbx'));raw=decode(root);task=exported['task']
 assert task['kind']=='BUILD_EXPORTED_STATIC_V2'
 by_id={m['export_material_id']:{k:m[k] for k in ('guid','file_id')} for m in task['materials']};objects=child(root,b'Objects').elems
 transported={}
 for n in objects:
  if n.id==b'Material':transported[n.props[0]]=by_id[n.props[1].split(b'\x00')[0].decode()]
 model=next(n for n in objects if n.id==b'Model' and n.props[0]==raw['model_uid'])
 custom={n.props[0].decode():n.props[-1].decode() for n in child(model,b'Properties70').elems if n.id==b'P' and n.props[0].startswith(b'_vapb')}
 assert custom=={'_vapb_export_object_id':task['export_object_id']}
 for face in raw['polygons']:
  match=[e for e in oracle['faces'] if set(map(tuple,face['positions']))<=set(map(tuple,e['local_corners']))];assert len(match)==1
  assert transported[face['uid']]=={k:match[0]['material'][k] for k in ('guid','file_id')}
 assert len(raw['polygons'])==12
 assert len(native['vertices'])==len(native['normals'])==len(native['uv'])==len(native['world_vertices'])==len(native['world_normals'])
 world=[vec(p) for p in native['world_vertices']];normals=[vec(p) for p in native['world_normals']]
 recalculated=max(max(abs(x-y) for x,y in zip(matpoint(native['renderer_matrix'],vec(v)),w)) for v,w in zip(native['vertices'],world))
 recalculated_n=max(max(abs(x-y) for x,y in zip(normal(native['renderer_matrix'],vec(n)),w)) for n,w in zip(native['normals'],normals))
 assert recalculated<=oracle['world_component_tolerance'] and recalculated_n<=oracle['normal_component_tolerance']
 faces=[dict(indices=f['indices'],material=native['materials'][f['group']],positions=[world[i] for i in f['indices']],normals=[normals[i] for i in f['indices']]) for f in native_faces(native)]
 assert len(faces)==12 and all(len(f['indices'])==3 for f in faces)
 positive=judge(oracle,faces,cover)
 negatives={}
 for name,key in [('one_face_material_swap','A_material'),('world_axis_swap','B_world'),('translation_loss','B_world'),('triangle_winding_reverse','D_winding')]:
  changed=copy.deepcopy(faces)
  if name=='one_face_material_swap':
   physical=next(e for e in oracle['faces'] if all(any(max(abs(x-y) for x,y in zip(p,w))<=oracle['world_component_tolerance'] for w in e['world_corners']) for p in changed[0]['positions']))
   swapped=next(m for m in native['materials'] if m!=changed[0]['material'])
   for f in changed:
    if all(any(max(abs(x-y) for x,y in zip(p,w))<=oracle['world_component_tolerance'] for w in physical['world_corners']) for p in f['positions']):f['material']=swapped
  if name=='world_axis_swap':
   for f in changed:f['positions']=[[p[1],p[0],p[2]] for p in f['positions']]
  if name=='translation_loss':
   for f in changed:f['positions']=[sub(p,oracle['translation_expected']) for p in f['positions']]
  if name=='triangle_winding_reverse':
   changed[0]['positions'].reverse();changed[0]['normals'].reverse();changed[0]['indices'].reverse()
  judged=judge(oracle,changed,cover);assert judged[key]['status']=='FAIL',(name,judged)
  negatives[name]=dict(expected_rejection=key,result=judged)
 initial=load(work/'unity-run/initial.json');assert not initial['finalizer_available'] and not initial['assistant_available'] and not initial['model_finalizer_available']
 events=[dict(zip(('utc','stage','detail'),line.split('\t',2))) for line in (work/'unity-run/events.tsv').read_text().splitlines()]
 start=next(i for i,e in enumerate(events) if e['stage']=='A_import_start');relevant=events[start:];stages=[e['stage'] for e in relevant]
 assert all(s in stages for s in ('B_import_completed','C_compile_finished','D_after_reload','E_finalizer_available'))
 assert stages.index('C_compile_finished')<stages.index('D_after_reload')<stages.index('E_finalizer_available')
 assert all('errors=0' in e['detail'] for e in relevant if e['stage']=='C_assembly_finished')
 process=load(work/'unity-run/process.json');exited=load(work/'unity-run/exit.json');release=load(work/'unity-run/release.json');resource=load(work/'resource-return.json')
 assert exited['exitCode']==0 and release['releaseVerified']
 assert datetime.datetime.fromisoformat(freeze['captured_before_consumer_utc'])<datetime.datetime.fromisoformat(process['startUtc'])
 assert resource['mutexAvailableAndProbeReleased'] and resource['poolAllFree'] and resource['newProjectLockAbsent'] and not resource['processCensusConflict']
 fixture=repo/'tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan';original=load(fixture/'input-and-predictions.json')
 assert all(sha(fixture/n)==digest for n,digest in original['asset_sha256'].items())
 runs={}
 for phase in ('replace','export'):
  pr=load(work/(phase+'-run')/'blender-process.json');ex=load(work/(phase+'-run')/'blender-exit.json');assert ex['exit_code']==0 and ex['owned_children_absent'];runs[phase]=dict(process=pr,exited=ex)
 assert runs['replace']['process']['pid']!=runs['export']['process']['pid']
 verdict='VERIFIED_IN_SCOPE' if all(r['status']=='PASS' for r in positive.values()) else 'FALSIFIED_IN_SCOPE'
 failure=next((k for k,v in positive.items() if v['status']=='FAIL'),None)
 save('judgment.json',dict(instruction_id='HOLMES-20261011-07',verdict=verdict,H_A='SUPPORTED_IN_SCOPE' if verdict=='VERIFIED_IN_SCOPE' else 'FALSIFIED_IN_SCOPE',H_B='NOT_OBSERVED_IN_SCOPE' if verdict=='VERIFIED_IN_SCOPE' else 'SUPPORTED_IN_SCOPE' if positive['A_material']['status']=='PASS' else 'UNDETERMINED',first_failed_stage=failure,positive=positive,negative_controls=negatives,world_capture_recalculation_error=recalculated,normal_capture_recalculation_error=recalculated_n,uv_used_for_correspondence=False,old_receipt_used=False,render_culling='NOT_RUN'))
 for name,value in [('replace.json',replaced),('export.json',exported),('native.json',native),('initial.json',initial),('events.json',events)]:save(name,value)
 save('transport.json',dict(fbx_version=version,raw=raw,serialized_export_properties=custom,material_export_ids=by_id,model_guid=task['model_guid']))
 save('run-summary.json',dict(blender=runs,unity=dict(pid=process['pid'],startUtc=process['startUtc'],exitUtc=exited['exitUtc'],exitCode=exited['exitCode'],actual_free_gib=process['actual_free_gib'],release=release),resource_return=resource,product_source_sha256=freeze['product_source_sha256'],executed_observer_sha256=freeze['executed_observer_sha256'],original_frozen_hashes_unchanged=len(original['asset_sha256']),product_code_changes=False,oracle_frozen_sha256=freeze['oracle_sha256'],pre_consumer_freeze_utc=freeze['captured_before_consumer_utc']))
 print('HOLMES07',verdict,json.dumps({k:v['status'] for k,v in positive.items()}));print('WORLD_ERROR',positive['B_world']['max_component_error'],'NORMAL_ERROR',positive['C_normal']['max_component_error'],'MIN_WINDING_DOT',positive['D_winding']['minimum_outward_dot'])
if __name__=='__main__':main()
