"""Independent fixture oracle using imported CP markers, never positional Skin identity."""
import json,sys
from pathlib import Path
from collections import Counter
w=Path(sys.argv[1]);stage=sys.argv[2]
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def xyz(p):return tuple(p[k] for k in ('x','y','z'))
def coverage(s):
    edges=Counter()
    for group in s['groups']:
        assert group['topology']=='Triangles'
        indices=group['indices'];assert len(indices)==6
        for i in range(0,len(indices),3):
            tri=[xyz(s['vertices'][v]) for v in indices[i:i+3]]
            assert len(set(tri))==3
            for j in range(3):edges[tuple(sorted((tri[j],tri[(j+1)%3])))]+=1
    assert sorted(edges.values())==[1,1,1,1,2]
    return sorted(e for e,n in edges.items() if n==1)
results={}
raw=load(w.parent/'holmes-source-skin-20261012-01/fbx-stages.json')
for c in ('A','B'):
    task=load(w/(c+'-'+stage+'-export/result.json'))['task']
    native=load(w/(c+'-'+stage+'-unity/native.json'))
    assert native['status']=='OBSERVED' and not native['error']
    assert native['weight_proof'] and native['compatibility_proof'] and not native['weight_error']
    assert native['source_bytes_preserved']
    assert task['kind']=='RESTORE_SOURCE_MODEL_SKIN_VARIANT_V1' and not task.get('parent_transform_mapping')
    data=task['weight_transport'];rows={p['cp']:p for p in data['points']}
    assert set(rows)==set(range(4)) and data['uv_channel']==1
    mapping={p['edited_bone_realization_id']:p['source_model_uid'] for p in task['bone_mappings']}
    original={p['bone_model_uid']:dict(zip(p['cp'],p['weights'])) for p in raw['source']['clusters']}
    import struct
    expected_source={uid:{cp:struct.unpack('<I',struct.pack('<f',v))[0] for cp,v in row.items()} for uid,row in original.items()}
    for cp,p in rows.items():
        assert all(expected_source[mapping[receipt]][cp]==bits for receipt,bits in zip(p['bone_realization_ids'],p['raw_bits']))
    observations=list((w/(c+'-'+stage+'-unity')).glob('weight-observation-*.json'));assert observations
    for p in observations:
        o=load(p);assert o['fbx_sha256']==data['stamped_sha256']
        s=o['skin'];assert s['groups']==native['post_import']['groups'] and s['vertices']==native['post_import']['vertices']
        assert s['weights']==native['post_import']['weights'] and s['bindposes']==native['post_import']['bindposes']
        seen=set()
        for uv,row in zip(o['cp_marker'],s['weights']):
            assert uv['y']==.375 and uv['x']==int(uv['x'])
            cp=int(uv['x'])-1;assert cp in rows;seen.add(cp)
            actual={o['bone_receipts'][i['bone']]:i['bits'] for i in row['influences']}
            assert actual==dict(zip(rows[cp]['bone_realization_ids'],rows[cp]['expected_bits']))
        assert seen==set(range(4))
    source=native['source'];edited=native['post_import']
    assert source['bindposes']==edited['bindposes']
    # Existing rest/matrix policy is .001; FBX axis rotation round-trip is not bitwise.
    assert all(abs(a-b)<=.001 for a,b in zip(source['matrix'],edited['matrix']))
    assert coverage(source)==coverage(edited)
    assert source['materials']==[{k:p[k] for k in ('guid','file_id')} for p in task['material_bindings']]
    assert native['source_components']==['UnityEngine.Transform','UnityEngine.SkinnedMeshRenderer']
    assert set(native['edited_components'])=={'UnityEngine.Transform','VapbRealizationMarker','UnityEngine.SkinnedMeshRenderer'}
    assert all(s['shapes']==0 and not s['cloth'] for s in [source,edited])
    if stage=='proof' and c=='B':
        assert not native['apply'] and native['rejection']==['VAPB_MODEL_SKIN_VARIANT_REJECTED=SOURCE_MODEL_INDEX_LAYOUT_CHANGED']
    else:
        assert native['apply'] and native['repeat_apply'] and not native['rejection']
        variant=native['variant'];assert variant['mesh']==edited['mesh']
        assert variant['materials']==source['materials']
        if stage!='proof': assert variant['source_bones']==source['bones'] and variant['source_root']==source['root'] and variant['source_parents']==source['bone_parents']
        assert variant['weights']==edited['weights'] and variant['bindposes']==edited['bindposes']
        assert variant['matrix']==source['matrix']
    results[c]=dict(cp_weight='EXACT_BITWISE_NATIVE_CP_JOIN',bone_rest='EXACT_BOUND_SOURCE_UID_ORDER_AND_BINDPOSE',matrix='EXISTING_0.001_POLICY',geometry_material='EXACT_FIXTURE_SCOPE',apply=native['apply'],observations=len(observations))
(w/(stage+'-judgment.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
print(stage.upper()+'_A_B_CP_WEIGHT_BONE_REST_GEOMETRY_MATERIAL_PROVEN')
