"""Independent exact-cover judge. Never imports the candidate/prediction function."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'topology-boundary'))
from judge import membership


def normalized(ref,package):
    if ref is None:return None
    return dict(source_package_id=ref.get('source_package_id',package),guid=ref['guid'].lower(),file_id=str(int(ref['file_id'])))


def verify_metadata(record,snapshot,supplement):
    if supplement['phase']!='METADATA_ONLY' or not supplement['utc']:raise ValueError('supplement phase missing')
    rows=supplement['asset_hashes'];hashes={r['name']:r['sha256'] for r in rows}
    if len(hashes)!=len(rows) or hashes!=record['asset_sha256']:raise ValueError('supplement frozen asset/meta revision differs')
    if supplement['receiver_mesh']!=snapshot['mesh'] or supplement['receiver_mesh']!=record['creation']['mesh']:
        raise ValueError('actual receiver Mesh identity differs')
    if supplement['materials']!=snapshot['materials'] or json.loads(supplement['policy'])!=json.loads(snapshot['policy']):
        raise ValueError('supplement fixed references/effective policy differs')
    return True


def judge(record,snapshot):
    hashes=record['asset_sha256'];creation=record['creation']
    if snapshot['unity_version']!='2022.3.22f1' or snapshot['keep_quads'] is not True:
        raise ValueError('Unity version/effective Keep Quads differs')
    if json.loads(snapshot['policy'])['meshes']['keepQuads'] not in (True,1):raise ValueError('effective serialized policy differs')
    for field,name in [('fbx_sha256','OrderedSix.fbx'),('fbx_sha256_after','OrderedSix.fbx'),
            ('meta_sha256','OrderedSix.fbx.meta'),('meta_sha256_after','OrderedSix.fbx.meta'),('prefab_sha256','Receiver.prefab')]:
        if snapshot[field]!=hashes[name]:raise ValueError('frozen revision differs: '+field)
    for field,created in [('mesh','mesh'),('renderer','model_renderer'),('receiver_renderer','receiver_renderer'),('prefab','prefab')]:
        if snapshot[field]!=creation[created]:raise ValueError('native asset identity differs: '+field)
    if snapshot['materials']!=creation['materials']:raise ValueError('fixed receiver references changed')
    rows=membership(record['raw'],snapshot)
    actual=[]
    for row in rows:
        group=row['group'];reference=snapshot['materials'][group] if group<len(snapshot['materials']) else None
        actual.append(dict(polygon=row['polygon'],group=group,topology=snapshot['groups'][group]['topology'],
            raw_uid=row['raw_uid'],material=normalized(reference,record['package_id']),winding=row['winding']))
    statuses={};comparisons={}
    for name,prediction in record['predictions'].items():
        expected=prediction['faces'];checks=[]
        if [r['polygon'] for r in expected]!=[r['polygon'] for r in actual]:raise ValueError('prediction polygon identities incomplete')
        for want,got in zip(expected,actual):
            match=want['group']==got['group'] and want['topology']==got['topology'] and normalized(want['material'],record['package_id'])==got['material']
            checks.append(dict(polygon=got['polygon'],predicted_group=want['group'],actual_group=got['group'],
                predicted_material=normalized(want['material'],record['package_id']),actual_material=got['material'],match=match))
        matched=len(prediction['groups'])==len(snapshot['groups']) and all(c['match'] for c in checks)
        statuses[name]='SUPPORTED_IN_THIS_FIXTURE' if matched else 'FALSIFIED';comparisons[name]=checks
    return dict(instruction_id='HOLMES-20261011-02',hypotheses=statuses,comparisons=comparisons,actual_faces=actual,
        native_membership='PASS',native_group_count=len(snapshot['groups']),receiver_reference_count=len(snapshot['materials']),
        winding=[r['winding'] for r in actual],position_comparison='NOT_RUN',render='NOT_RUN',
        product_guard_changed=False,product_automatic_restore='NOT_IMPLEMENTED')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for name in ('input','native','output'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--supplement',type=Path,required=True)
    args=ap.parse_args();record=json.loads(args.input.read_text(encoding='utf-8-sig'));snapshot=json.loads(args.native.read_text(encoding='utf-8-sig'))
    result=judge(record,snapshot)
    supplement=json.loads(args.supplement.read_text(encoding='utf-8-sig'))
    result['supplemental_revision_binding']='PASS' if verify_metadata(record,snapshot,supplement) else 'FAIL'
    result['supplement_utc']=supplement['utc']
    result['supplement_scope']='Material/meta/receiver Mesh revisions verified later; not claimed contemporaneous with first face capture'
    result['input_prediction_sha256']=hashlib.sha256(args.input.read_bytes()).hexdigest()
    result['native_sha256']=hashlib.sha256(args.native.read_bytes()).hexdigest()
    with args.output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result['hypotheses']))
