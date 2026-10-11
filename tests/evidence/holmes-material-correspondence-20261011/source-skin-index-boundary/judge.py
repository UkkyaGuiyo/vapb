"""Captured-data checks; geometric equality never substitutes for Skin CP identity."""
import json,math,copy
from collections import Counter
from pathlib import Path
import sys
work=Path(sys.argv[1]);load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
a=load(work/'A-unity/native.json');b=load(work/'B-unity/native.json');save=load(work/'B-save/result.json');raw=load(work/'fbx-stages.json')
def xyz(v):return tuple(v[x] for x in ('x','y','z'))
def edge_counts(s):
 c=Counter()
 for g in s['groups']:
  assert g['topology']=='Triangles' and len(g['indices'])%3==0
  for j in range(0,len(g['indices']),3):
   tri=[xyz(s['vertices'][i]) for i in g['indices'][j:j+3]]
   assert len(set(tri))==3
   for k in range(3):c[tuple(sorted((tri[k],tri[(k+1)%3])))]+=1
 return c
def coverage(s):
 c=edge_counts(s)
 return dict(boundary=sorted(e for e,n in c.items() if n==1),internal=sorted(e for e,n in c.items() if n==2),multiplicities=sorted(c.values()),triangles=sum(len(g['indices'])//3 for g in s['groups']))
def uv_by_vertex(s):
 out={}
 for cp,uv in zip(s['corner_vertices'],s['uv']):out.setdefault(cp,set()).add(tuple(uv))
 return out
def old_influences(s,e):
 if len(s['weights'])!=len(e['weights']):return False
 for sr,er in zip(s['weights'],e['weights']):
  ss={x['bone']:x['weight'] for x in sr['influences']};ee={x['bone']:x['weight'] for x in er['influences']}
  if len(sr['influences'])!=len(er['influences']) or ss.keys()!=ee.keys() or any(abs(ss[k]-ee[k])>1e-6 for k in ss):return False
 return True
assert a['status']=='OBSERVED' and a['apply'] and a['repeat_apply'] and a['source_bytes_preserved']
assert b['status']=='OBSERVED' and not b['apply'] and b['rejection']==['VAPB_MODEL_SKIN_VARIANT_REJECTED=SOURCE_MODEL_INDEX_LAYOUT_CHANGED'] and b['source_bytes_preserved']
assert old_influences(a['source'],a['post_apply'])
assert not old_influences(b['source'],b['post_apply'])
assert uv_by_vertex(save['before'])==uv_by_vertex(save['after'])
for k in ['vertices','weights','groups','matrix','bones','materials','shape_count','model_uid','geometry_uid','receipt']:assert save['before'][k]==save['after'][k]
original=coverage(b['source']);edited=coverage(b['post_apply']);assert original['boundary']==edited['boundary'] and original['triangles']==edited['triangles']==2 and len(original['internal'])==len(edited['internal'])==1 and original['internal']!=edited['internal']
assert set(map(xyz,b['source']['vertices']))==set(map(xyz,b['post_apply']['vertices']))
assert original['multiplicities']==edited['multiplicities']==[1,1,1,1,2]
assert b['source']['bindposes']==b['post_apply']['bindposes']
assert all(s['shapes']==0 and not s['cloth'] for s in [a['source'],a['variant'],b['source'],b['post_apply']])
for case in ['A','B']:
 for phase in ['save','export']:assert load(work/(case+'-'+phase)/'result.json')['status']=='PASS'
 task=load(work/(case+'-export/result.json'))['task'];assert 'weight_transport' not in task and 'parent_transform_mapping' not in task
 assert len(raw[case]['vertices'])//3==4 and len(raw[case]['polygon_vertex_index'])==6
 # Raw CP streams can be compared, but native vertex-to-CP identity remains absent.
 assert raw['source']['vertices']==raw[case]['vertices']
 mapping={x['edited_bone_realization_id']:x['source_model_uid'] for x in task['bone_mappings']}
 source_weights={c['bone_model_uid']:dict(zip(c['cp'],c['weights'])) for c in raw['source']['clusters']}
 edited_weights={mapping[c['bone_receipts']['_vapb_fbx_bone_realization_id']]:dict(zip(c['cp'],c['weights'])) for c in raw[case]['clusters']}
 assert source_weights==edited_weights
for s in [a['source'],a['variant'],b['post_apply']]:
 assert len(s['weights'])==4 and all(len(row['influences'])==2 and all(math.isfinite(x['weight']) and x['weight']>0 for x in row['influences']) and sum(x['weight'] for x in row['influences'])==1 for row in s['weights'])
# Captured-data negatives prove nearest observer checks without new native fixtures.
missing=copy.deepcopy(b['post_apply']);missing['groups'][0]['indices']=missing['groups'][0]['indices'][:3]
assert coverage(missing)['triangles']!=2
uvbad=copy.deepcopy(save['after']);uvbad['uv'][0][0]+=0.125
assert uv_by_vertex(save['before'])!=uv_by_vertex(uvbad)
weightbad=copy.deepcopy(a['post_apply']);weightbad['weights'][0]['influences'][0]['weight']=0.5
assert not old_influences(a['source'],weightbad)
result=dict(instruction_id='HOLMES-20261012-01',verdict='UNDETERMINED',A='PASS_BOUNDED_RETURN',B_first_failure='SOURCE_MODEL_INDEX_LAYOUT_CHANGED',B_blender_edit='PASS_DIAGONAL_ONLY',B_raw_fbx_cp_weights='EXACT_IN_RAW_CP_DOMAIN',B_native_geometry='PASS_EXACT_QUAD_COVERAGE_ONLY',B_native_uv_and_skin_cp_identity='UNDETERMINED',B_bindpose_array='EXACT_ARRAY_NOT_BONE_JOIN',B_old_index_influence_comparator=False,reason='No exported CP weight witness in this source-root context; native renumbering not joined to exported CP identity. Old index guard is first refusal, but later SameSkinInfluences would also fail. Therefore index-only causal isolation and full B Skin proof are not established.',source_coverage=original,edited_coverage=edited,negatives=dict(missing_triangle='REJECTED_CAPTURED_DATA',changed_corner_uv='REJECTED_CAPTURED_DATA',changed_influence='REJECTED_CAPTURED_DATA',product_safety_negatives='NOT_RUN_NO_PRODUCT_CHANGE'),product_change='NONE',next_minimum='Reuse prepare_export_weight_witness for the existing source-model context without parent_transform_mapping, and let ValidateExportedWeightTransport validate its existing exact CP/realization/revision evidence; then retry only this preserved A/B and required safety controls before changing the index guard.')
(work/'judgment.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('A_PASS_B_FIRST_INDEX_REJECTION; HYPOTHESES_UNDETERMINED; PRODUCT_UNCHANGED')
