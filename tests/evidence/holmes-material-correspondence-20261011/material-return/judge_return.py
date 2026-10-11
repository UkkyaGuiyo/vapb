"""Independent final-state corner coverage, actual Unity submeshes and references."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--work',type=Path,required=True)
    args=ap.parse_args();repo,work=args.repo,args.work
    sys.path.insert(0,str(repo/'tests/evidence/holmes-material-correspondence-20261011/topology-boundary'))
    from judge import cover,native_faces
    from read_input import parse,decode,child
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    export=json.loads((work/'export.json').read_text());final=export['faces']
    native=json.loads((work/'unity-run/native.json').read_text(encoding='utf-8-sig'))
    assert native['status']=='PASS' and native['import_completed'] and native['explicit_apply'] and native['apply_returned_true']
    assert native['package_sha256']==export['package_sha256']==sha(work/'EditedMaterialOutput.unitypackage')
    assert native['manifest_sha256']==export['manifest_sha256']==sha(work/'manifest.json')
    assert native['fbx_sha256']==native['fbx_sha256_after']==export['exported_fbx_sha256']==sha(work/'Exported.fbx')
    assert native['meta_sha256']==native['meta_sha256_after'] and native['matching_realization_markers']==1
    root,version=parse(work/'Exported.fbx',repo,Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/scripts/addons_core/io_scene_fbx'))
    raw=decode(root);task=json.loads((work/'manifest.json').read_text())['reference_rebind_tasks'][0]
    model=next(n for n in child(root,b'Objects').elems if n.id==b'Model' and n.props[0]==raw['model_uid'])
    props=child(model,b'Properties70').elems
    transported=[n.props[-1].decode() for n in props if n.id==b'P' and n.props[0]==b'_vapb_fbx_realization_id']
    assert transported==[task['realization_id']]
    assert len(raw['material_connections'])==len(task['materials'])==len(native['materials'])
    observed=native_faces(native);joined={row['source_polygon']:[] for row in final};fbx_join={row['source_polygon']:[] for row in final}
    def match(uv):
        candidates=[row for row in final if set(tuple(p) for p in uv)<=set(tuple(p) for p in row['uv'])]
        assert len(candidates)==1,'final face identity ambiguous';return candidates[0]
    for face in observed:
        target=match(face['uv']);joined[target['source_polygon']].append(face)
    for face in raw['polygons']:
        target=match(face['uv']);fbx_join[target['source_polygon']].append(face)
    rows=[]
    for target in final:
        p=target['source_polygon'];faces=joined[p];fbx=fbx_join[p]
        native_winding=cover(target['uv'],[f['uv'] for f in faces]);fbx_winding=cover(target['uv'],[f['uv'] for f in fbx])
        wanted={k:target['material'][k] for k in ('guid','file_id')}
        for face in faces:assert native['materials'][face['group']]==wanted,'actual Unity face Material differs'
        for face in fbx:assert task['materials'][face['raw_slot']]==wanted,'serialized FBX slot/manifest Material differs'
        rows.append(dict(final_polygon=p,expected_material=wanted,native_materials=[native['materials'][f['group']] for f in faces],
            native_groups=sorted({f['group'] for f in faces}),native_face_count=len(faces),native_topologies=[f['topology'] for f in faces],
            final_corner_count=target['topology'],native_winding=native_winding,fbx_winding=fbx_winding,cover='PASS'))
    assert len(rows)==6 and rows[0]['expected_material']!=rows[4]['expected_material']
    result=dict(instruction_id='HOLMES-20261011-04',status='PASS',export_transport='PASS',final_face_materials='PASS',
        package_sha256=export['package_sha256'],fbx_sha256=export['exported_fbx_sha256'],manifest_sha256=export['manifest_sha256'],
        fbx_version=version,transported_realization_id=transported[0],actual_mesh=native['mesh'],actual_renderer=native['renderer'],
        faces=rows,comparison='Final edited Blender UV corner coverage against actual FBX and Unity index streams; no slot-array-only inference',
        render='NOT_RUN',position_comparison='NOT_RUN')
    (work/'judgment.json').write_text(json.dumps(result,indent=2));print('HOLMES04_FINAL_FACE_RETURN_PASS')

if __name__=='__main__':main()
