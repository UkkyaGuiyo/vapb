"""Assemble only the approved synthetic U/D packages and fixed E H input."""
import argparse, hashlib, io, json, tarfile
from pathlib import Path

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--cases',type=Path,required=True);a=ap.parse_args()
    ev=a.repo/'tests/evidence/holmes-material-correspondence-20261011'
    manifest=json.loads((a.cases/'generation.json').read_text())
    package=a.repo/'tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage'
    if sha(package)!=manifest['package_sha256']:raise ValueError('original package changed')
    e=ev/'cases/E.fbx'
    if sha(e)!=json.loads((ev/'cases/generation-E.json').read_text())['cases']['E']['fbx_sha256']:raise ValueError('E changed')
    with tarfile.open(package) as arc:
        entries=[(info,arc.extractfile(info).read() if info.isfile() else None) for info in arc]
    prefabs=[(info.name,data) for info,data in entries if info.name.endswith('/pathname') and data.strip()==b'Assets/PublicMaterialSource/Direct.prefab']
    if len(prefabs)!=1:raise ValueError('unique receiver required')
    prefix=prefabs[0][0].rsplit('/',1)[0]+'/'
    original=next(data for info,data in entries if info.name==prefix+'asset')
    before=b'guid: 64f92a1bd9b35a040bf9e2c6d200b34c'
    after=b'guid: eb805efb35118044db5e74adc652673a'
    if original.count(before)!=1:raise ValueError('unique receiver reference required')
    modified=original.replace(before,after)
    for filename,data in [('original.prefab',original),('D.prefab',modified),('D.fbx',e.read_bytes()),('H.fbx',e.read_bytes())]:
        with (a.cases/filename).open('xb') as f:f.write(data)
    for name in ['D','H']:
        manifest['cases'][name]=dict(fbx_sha256=sha(a.cases/(name+'.fbx')),meta_sha256=manifest['meta_sha256'],fixed_E_input=True)
    checks={}
    for name in ['U','D']:
        target=a.cases/(name+'.unitypackage')
        payload=(a.cases/(name+'.fbx')).read_bytes()
        changed={}
        with target.open('xb') as stream,tarfile.open(fileobj=stream,mode='w:gz') as out:
            for info,data in entries:
                new=payload if info.name=='abcdefabcdefabcdefabcdefabcdefab/asset' else modified if name=='D' and info.name==prefix+'asset' else data
                clone=tarfile.TarInfo(info.name);clone.mode=info.mode;clone.type=info.type;clone.mtime=info.mtime
                if new is not None:
                    clone.size=len(new);out.addfile(clone,io.BytesIO(new))
                    if new!=data:changed[info.name]=hashlib.sha256(new).hexdigest()
                else:out.addfile(clone)
        expected={'abcdefabcdefabcdefabcdefabcdefab/asset'}|({prefix+'asset'} if name=='D' else set())
        if set(changed)!=expected:raise ValueError('package mutation differs')
        with tarfile.open(target) as arc:
            written=[(info.name,arc.extractfile(info).read() if info.isfile() else None) for info in arc]
        if [name for name,_ in written]!=[info.name for info,_ in entries]:raise ValueError('member list differs')
        for (info,data),(path,new) in zip(entries,written):
            intended=payload if path=='abcdefabcdefabcdefabcdefabcdefab/asset' else modified if name=='D' and path==prefix+'asset' else data
            if new!=intended:raise ValueError('written package mismatch')
        checks[name]=dict(package_sha256=sha(target),changed_members=changed)
    manifest['receiver']={'original_sha256':hashlib.sha256(original).hexdigest(),'D_sha256':hashlib.sha256(modified).hexdigest(),'declaration':'Prefab slot2 reference changed to same exact Material as slot0; raw E FBX unchanged'}
    (a.cases/'generation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with (a.cases/'package-copy-check.json').open('x') as f:json.dump(checks,f,indent=2)
    print('Only self-authored boundary copies assembled; independent judgment required')
if __name__=='__main__':main()
