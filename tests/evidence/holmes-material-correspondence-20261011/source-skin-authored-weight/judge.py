"""Bounded independent CP/Bone oracle; reads frozen expectations and actual native data."""
import sys,json,hashlib,tarfile,re
from pathlib import Path
w=Path(sys.argv[1]);r=Path(__file__).parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=load(r/'pre-observation.json');native=load(w/'native/native.json');old=r.parent/'source-skin-cp-witness'
control=load(old/'B-final-native.json');old_weight=load(old/'B-final-weight.json')
assert native['status']=='OBSERVED' and not native['error'] and native['instruction_id']=='HOLMES-20261012-03'
assert native['apply'] and native['repeat_apply'] and not native['rejection']
assert native['weight_proof'] and native['compatibility_proof'] and not native['weight_error']
assert native['package_sha256']==f['output_package_sha256']==sha(w/'AuthoredWeightOutput.unitypackage')
assert native['finalizer_sha256']==f['consumer_sha256']
rows={p['cp']:dict(zip(p['bone_realization_ids'],p['expected_bits'])) for p in f['expected_points']};assert set(rows)==set(range(4))
def point_map(o):
 result={}
 for i,uv in enumerate(o['cp_marker']):
  assert uv['y']==.375 and uv['x']==int(uv['x']);cp=int(uv['x'])-1;assert cp in rows and cp not in result;result[cp]=i
 assert set(result)==set(rows);return result
prior_map=point_map(old_weight);observations=list((w/'native').glob('weight-observation-*.json'));assert observations
for p in observations:
 o=load(p);assert o['fbx_sha256']==f['task']['weight_transport']['stamped_sha256'];m=point_map(o)
 for cp,i in m.items():
  actual={o['bone_receipts'][v['bone']]:v['bits'] for v in o['skin']['weights'][i]['influences'] if v['weight']>0};assert actual==rows[cp]
  for k in ['vertices','normals','uv']:assert o['skin'][k][i]==old_weight['skin'][k][prior_map[cp]],k
 for k in ['vertices','normals','uv','groups','weights','bindposes']:assert o['skin'][k]==native['post_import'][k],k
 def groups(s,m):
  inv={i:cp for cp,i in m.items()};return [(g['topology'],[inv[i] for i in g['indices']]) for g in s['groups']]
 assert groups(o['skin'],m)==groups(old_weight['skin'],prior_map),'Diagonal/material-face membership changed'
 for cp in range(1,4):
  i=prior_map[cp];before={old_weight['bone_receipts'][v['bone']]:v['bits'] for v in old_weight['skin']['weights'][i]['influences']};assert before==rows[cp]
 i=prior_map[0];before={old_weight['bone_receipts'][v['bone']]:v['bits'] for v in old_weight['skin']['weights'][i]['influences']};assert before!=rows[0]
s=native['source'];e=native['post_import'];v=native['variant']
assert v['mesh']==e['mesh'];assert v['materials']==s['materials']==control['source']['materials']
assert v['source_bones']==s['bones']==control['source']['bones'];assert v['source_root']==s['root'];assert v['source_parents']==s['bone_parents']
for k in ['vertices','normals','uv','groups','weights','bindposes']:assert v[k]==e[k],k
assert v['bindposes']==s['bindposes']==control['source']['bindposes'];assert v['matrix']==s['matrix']
assert all(abs(a-b)<=.001 for a,b in zip(s['matrix'],e['matrix']))
assert native['source_bytes_preserved'];assert native['source_components']==['UnityEngine.Transform','UnityEngine.SkinnedMeshRenderer']
assert set(native['edited_components'])=={'UnityEngine.Transform','VapbRealizationMarker','UnityEngine.SkinnedMeshRenderer'}
negative=load(w/'native/negative.json');assert negative['status']=='PASS' and not negative['accepted']
assert negative['first_rejection']=='VAPB_MODEL_SKIN_VARIANT_REJECTED=EXPORTED_WEIGHT_DATA_INVALID' and negative['variant_unchanged'] and negative['source_manifest_unchanged']
for p,h in load(w/'original-hashes-private.json').items():assert sha(Path(p))==h,p
# Standard unitypackage raw assets: compare original bytes/meta and installed paths by exact GUID.
def assets(p):
 with tarfile.open(p) as t:
  files={m.name:t.extractfile(m).read() for m in t if m.isfile()}
 return {n.split('/')[0]:{'asset':b,'meta':files[n+'.meta'],'path':files[n.rsplit('/',1)[0]+'/pathname'].decode('utf-8').rstrip('\0\r\n')} for n,b in files.items() if n.endswith('/asset')}
source=assets(w/'Source.unitypackage');output=assets(w/'AuthoredWeightOutput.unitypackage');preservation=[]
for g,a in source.items():
 assert output[g]['asset']==a['asset'] and output[g]['meta']==a['meta']
 target=w/'Project'/output[g]['path'];assert target.read_bytes()==a['asset'];assert target.with_name(target.name+'.meta').read_bytes()==a['meta']
 preservation.append({'guid':g,'asset_bytes_exact':True,'meta_bytes_exact':True,'path':output[g]['path']})
result={'instruction_id':'HOLMES-20261012-03','status':'VERIFIED_IN_SCOPE','pre_observation_commit':'5d4850269e8b3dad0eab9c1898e3e902daef2c27','cp0_weights':'0.625/0.375','native_cp_bone_expected_bits':'EXACT_BITWISE','other3CP':'UNCHANGED','geometry_uv_normals_face_diagonal':'UNCHANGED_CP_CANONICAL','bone_root_bindpose_source_ancestry_material_guid_signed_fileid':'EXACT','variant':'EDITED_SHARED_MESH_EXACT','apply_repeat':'PASS','one_bit_refusal':'PASS_ORIGINAL_MANIFEST_VARIANT_UNCHANGED','original_preservation':preservation,'saved_original_inputs':'HASH_IDENTICAL','weight_observations':len(observations),'deformation':'NOT_RUN','rendering':'NOT_RUN','product_source_changes':False}
(w/'judgment.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('HOLMES03_VERIFIED_IN_SCOPE')
