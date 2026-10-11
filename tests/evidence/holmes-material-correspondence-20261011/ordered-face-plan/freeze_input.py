"""Freeze actual package/assets and three source-only predictions before face holdout."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types
from candidates import predict_ordered_partitions,plan_receiver_materials

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run(repo,addon,work):
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'topology-boundary'))
    from read_input import decode,parse
    # Namespace only: existing offline readers without running Blender addon registration.
    namespace=types.ModuleType('unitypackage_blender_importer');namespace.__path__=[str(repo)]
    sys.modules['unitypackage_blender_importer']=namespace
    parser=importlib.import_module('unitypackage_blender_importer.unity.prefab_parser')
    projection=importlib.import_module('unitypackage_blender_importer.unity.occurrence_projection')
    identity=importlib.import_module('unitypackage_blender_importer.unity.package_identity')
    yaml=importlib.import_module('unitypackage_blender_importer.unity.yaml_parser')
    frozen=work/'frozen';fbx=frozen/'OrderedSix.fbx';meta=frozen/'OrderedSix.fbx.meta'
    root,version=parse(fbx,repo,addon);raw=decode(root)
    if len(raw['polygons'])!=6 or len(raw['material_connections'])!=2:raise ValueError('six faces/two unique connections required')
    authored=[min(u[0] for u in p['uv'])*8 for p in raw['polygons']]
    if authored!=list(range(6)) or [len(p['cp']) for p in raw['polygons']]!=[3,4,4,3,3,4]:
        raise ValueError('actual bytes lost discriminating authored face order')
    uids=[p['uid'] for p in raw['polygons']]
    if not (uids[0]==uids[2]==uids[4] and uids[1]==uids[3]==uids[5] and uids[0]!=uids[1]):raise ValueError('actual assignment differs')
    creation=json.loads((work/'creation.json').read_text(encoding='utf-8-sig'))
    # Only asset identities from creation; face data has not been captured.
    parsed_meta=yaml._parse_document_body(meta.read_text(encoding='utf-8-sig'))
    settings=parsed_meta['ModelImporter']['meshes']
    meshes_meta=dict(keepQuads=settings.get('keepQuads'),fbx_sha256=sha(fbx),meta_sha256=sha(meta),mesh_guid=creation['mesh']['guid'])
    package=identity.PackageIdentity.from_path(work/'OrderedSix.unitypackage');package_id=package.source_package_id
    prefab=parser.parse_prefab(frozen/'Receiver.prefab')
    source=projection.PrefabSource.from_prefab(prefab,package_id,prefab.asset_guid)
    result=projection.project_occurrences(source,'diagnostic-ordered-six',lambda package,guid:None)
    if result.issues or len(result.records)!=1:raise ValueError(('direct occurrence not uniquely projected',result.issues))
    occurrence=result.records[0]
    if occurrence['mesh']!={'mesh_guid':creation['mesh']['guid'],'mesh_file_id':int(creation['mesh']['file_id'])}:raise ValueError('serialized Mesh/creation identities differ')
    if str(occurrence['source_key']['renderer_file_id'])!=creation['receiver_renderer']['file_id']:raise ValueError('serialized Renderer identity differs')
    providers=[]
    for i in range(4):
        asset=frozen/('R'+str(i)+'.mat');docs=yaml.parse_unity_yaml(asset.read_text(encoding='utf-8-sig'))
        mats=[d for d in docs if d.class_id==21]
        if len(mats)!=1:raise ValueError('unique serialized Material provider required')
        ref=dict(source_package_id=package_id,guid=creation['materials'][i]['guid'],file_id=str(mats[0].file_id))
        if ref['file_id']!=creation['materials'][i]['file_id']:raise ValueError('provider fileID differs')
        guid=yaml._parse_document_body((frozen/(asset.name+'.meta')).read_text(encoding='utf-8-sig'))['guid']
        if str(guid)!=ref['guid']:raise ValueError('provider GUID differs')
        providers.append(dict(reference=ref,revision_sha256=sha(asset),meta_sha256=sha(frozen/(asset.name+'.meta'))))
    occurrence.update(providers=providers,source_binding='UNPROVEN',input_revision={k:meshes_meta[k] for k in ('fbx_sha256','meta_sha256')})
    partitions=predict_ordered_partitions(raw,meshes_meta);plan=plan_receiver_materials(partitions,occurrence)
    if plan['unresolved']:raise ValueError(plan['unresolved'])
    # Competing hypotheses from input only; no observations or predictor oracle in judge.
    pair_order=partitions['groups'];runs=[];uid_first=[]
    for p in raw['polygons']:
        topology='Triangles' if len(p['cp'])==3 else 'Quads'
        if not runs or (runs[-1]['uid'],runs[-1]['topology'])!=(p['uid'],topology):
            runs.append(dict(ordinal=len(runs),uid=p['uid'],topology=topology,polygons=[]))
        runs[-1]['polygons'].append(p['polygon'])
    for uid in dict.fromkeys(p['uid'] for p in raw['polygons']):
        for group in pair_order:
            if group['uid']==uid:uid_first.append({**group,'ordinal':len(uid_first)})
    predictions={}
    for name,groups in [('PAIR_FIRST',pair_order),('PAIR_RUN',runs),('UID_FIRST',uid_first)]:
        rows=[]
        for group in groups:
            index=group['ordinal'];ref=occurrence['materials'].get(index)
            for p in group['polygons']:rows.append(dict(polygon=p,group=index,topology=group['topology'],material=ref))
        predictions[name]=dict(groups=groups,faces=sorted(rows,key=lambda r:r['polygon']))
    record=dict(instruction_id='HOLMES-20261011-02',instruction_commit='02c51d6cda52bb912a0afc2c2f804e9ca09a8ac5',
        frozen_utc=datetime.now(timezone.utc).isoformat(),fbx_version=version,raw=raw,partitions=partitions,plan=plan,
        predictions=predictions,creation=creation,package_id=package_id,package_sha256=package.sha256,
        asset_sha256={p.name:sha(p) for p in sorted(frozen.iterdir()) if p.is_file()},
        code_sha256={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
        face_observation_exists=(work/'native.json').exists())
    if record['face_observation_exists']:raise ValueError('holdout already observed')
    with (work/'input-and-predictions.json').open('x',encoding='utf8') as f:json.dump(record,f,indent=2)
    print(json.dumps(dict(result='INPUT_ONLY_FROZEN',group_predictions={k:len(v['groups']) for k,v in predictions.items()},fbx_sha256=sha(fbx))))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for name in ('repo','addon','work'):ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args();run(args.repo,args.addon,args.work)
