"""Bounded U/D/H checks reusing the independent exact-UV judge, without predictions."""
import argparse, hashlib, importlib.util, json, tarfile
from collections import Counter
from pathlib import Path

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def diff(a,b,path=()):
    if isinstance(a,dict) and isinstance(b,dict):
        return [r for key in sorted(set(a)|set(b)) for r in diff(a.get(key),b.get(key),path+(key,))]
    return [] if a==b else [(path,a,b)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--addon',type=Path,required=True);ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--native',type=Path);ap.add_argument('--blender',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('occupied output')
    ev=a.repo/'tests/evidence/holmes-material-correspondence-20261011'
    spec=importlib.util.spec_from_file_location('boundary_exact_judge',ev/'judge_faces.py');j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
    spec=importlib.util.spec_from_file_location('boundary_parser_loader',a.repo/'tests/evidence/inbound-material-face-membership-20261007/verify_inbound_frame.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    parser=helper.load_parser(a.addon)
    if sha(a.cases/'original.fbx')!=helper.PIN_FBX or sha(a.cases/'original.fbx.meta')!=helper.PIN_META:raise ValueError('original changed')
    original,version=parser.parse(str(a.cases/'original.fbx'),use_namedtuple=True);base,slots,edges=j.decode(original)
    epath=ev/'cases/E.fbx';egen=read(ev/'cases/generation-E.json')
    if sha(epath)!=egen['cases']['E']['fbx_sha256']:raise ValueError('E changed')
    etree,ever=parser.parse(str(epath),use_namedtuple=True);erows,eslots,eedges=j.decode(etree)
    manifest=read(a.cases/'generation.json');baseline=read(ev/'observations/E-context.json');ecoordinate=read(ev/'observations/E-coordinate.json')
    package=a.repo/'tests/unity_model_material_probe/fixtures/ThreeSlotSource.unitypackage'
    if sha(package)!=helper.PIN_PACKAGE:raise ValueError('original package changed')
    with tarfile.open(package) as arc:original_prefab=arc.extractfile('7cbdcbe81fde386408bcfb379e62b6bb/asset').read()
    if hashlib.sha256(original_prefab).hexdigest()!=baseline['prefab_sha']:raise ValueError('receiver baseline differs')
    before=('guid: '+baseline['materials'][2]['guid']).encode();after=('guid: '+baseline['materials'][0]['guid']).encode()
    if original_prefab.count(before)!=1:raise ValueError('unique receiver reference required')
    derived_prefab=original_prefab.replace(before,after);derived_sha=hashlib.sha256(derived_prefab).hexdigest()
    if (a.cases/'D.prefab').read_bytes()!=derived_prefab or (a.cases/'original.prefab').read_bytes()!=original_prefab:raise ValueError('declared receiver mutation differs')
    report={'scope':'Three finite synthetic boundaries; no product policy or guarantee','cases':{}}
    for name in ['U','D','H']:
        path=a.cases/(name+'.fbx');tree,v=parser.parse(str(path),use_namedtuple=True);raw,rawslots,rawedges=j.decode(tree)
        if v!=version or rawedges!=edges or rawslots!=slots:raise ValueError('undeclared edges/slots/version change')
        if sha(path)!=manifest['cases'][name]['fbx_sha256']:raise ValueError('manifest revision mismatch')
        if name=='U':
            omit=[(b'',b'Objects',b'Geometry',b'LayerElementMaterial',b'Materials')]
            if j.canonical(tree,omit)!=j.canonical(original,omit):raise ValueError('U undeclared tree change')
            if [r['slot'] for r in raw]!=[2]*6+[1]*4+[2]*2:raise ValueError('U assignments differ')
            for x,y,_,_ in j.join(base,raw):
                if any(x[k]!=y[k] for k in ['cps','corners','uv','normals']):raise ValueError('U face meaning changed')
        else:
            if sha(path)!=sha(epath) or j.canonical(tree)!=j.canonical(etree):raise ValueError('D/H E input differs')
        item={'fbx_sha256':sha(path),'raw_material_connections':rawslots,'raw_faces':raw,'written_semantics_checked':True}
        if a.native:
            context=read(a.native/(name+'-context.json'));snap=read(a.native/(name+'-coordinate.json'))
            if not snap['pass'] or context.get('error') or not context['same_model_mesh'] or not context['get_triangles_matches_mesh_data']:raise ValueError('capture failed')
            if snap['unity_version']!=context['unity_version']:raise ValueError('snapshot/context version differs')
            if context['fbx_sha']!=sha(path) or context['fbx_sha_after']!=sha(path) or context['original_meta_sha']!=helper.PIN_META:raise ValueError('capture revision differs')
            if context['mesh']!=baseline['mesh'] or snap['source_asset_guid']!=j.GUID or snap['mesh_file_id']!=j.FILE_ID:raise ValueError('identity differs')
            for field in ['unity_version','weld_vertices','optimize_vertices','compression','index_format','import_normals','import_tangents','external_remaps','renderer_guid','renderer_file_id','prefab_meta_sha']:
                if context[field]!=baseline[field]:raise ValueError('fixed control differs: '+field)
            if context['optimize_polygons']!=(False if name=='H' else baseline['optimize_polygons']):raise ValueError('optimization differs')
            for field in ['importer_file_scale','importer_global_scale','importer_use_file_scale','importer_bake_axis_conversion']:
                if snap[field]!=ecoordinate[field]:raise ValueError('scale/axis differs')
            for field in ['fbx_sha256_before','fbx_sha256_after','source_sha256']:
                if snap[field]!=sha(path):raise ValueError('snapshot revision differs')
            for field in ['meta_sha256_before','meta_sha256_after']:
                if snap[field]!=context['meta_sha']:raise ValueError('snapshot meta differs')
            if context['meta_sha_after']!=context['meta_sha']:raise ValueError('meta changed during capture')
            expected_refs=baseline['materials'] if name!='D' else [baseline['materials'][0],baseline['materials'][1],baseline['materials'][0]]
            if context['materials']!=expected_refs:raise ValueError('receiver references differ')
            expected_sha=derived_sha if name=='D' else baseline['prefab_sha']
            if context['prefab_sha']!=expected_sha:raise ValueError('receiver revision differs')
            changes=diff(json.loads(context['policy_before']),json.loads(context['serialized_model_importer']))
            if name in ['D','H'] and json.loads(context['policy_before'])!=json.loads(baseline['serialized_model_importer']):raise ValueError('D/H starting effective policy differs from E')
            if name=='H':
                if len(changes)!=1 or changes[0][0]!=('meshes','meshOptimizationFlags'):raise ValueError('H undeclared effective policy change: '+repr(changes))
            elif changes or context['meta_sha']!=helper.PIN_META:raise ValueError('fixed effective policy/meta changed')
            native=j.native_rows(snap);pairs=j.join(raw,native)
            groups={str(i):dict(Counter(str(x['uid']) for x,y,_,_ in pairs if y['slot']==i)) for i in range(len(snap['source_submeshes']))}
            item.update(native_context=context,raw_to_unity=j.observations(raw,native),all_native_groups=groups,effective_policy_changes=changes)
            # True permutation across every actual submesh, including empty groups.
            n=len(snap['source_submeshes']);permuted=[dict(row,slot=(row['slot']+1)%n) for row in native]
            if n>1 and j.observations(raw,permuted)['groups']==j.observations(raw,native)['groups']:raise ValueError('slot control ineffective')
            item['slot_permutation_control_count']=n
            if name in ['D','H']:
                item['E_same_face_to_native_submesh']=all(x['slot']==y['slot'] for x,y,_,_ in j.join(j.native_rows(ecoordinate),native))
            if a.blender and name in ['U','D']:
                b=read(a.blender/(name+'-blender.json'))
                if b['fbx_sha256']!=sha(path) or b['meta_sha256']!=helper.PIN_META or b['operator_result']!=['CANCELLED'] or b['before']!=b['after']:raise ValueError('Blender capture/guard differs')
                if b['package_sha256']!=read(a.cases/'package-copy-check.json')[name]['package_sha256']:raise ValueError('Blender package revision differs')
                item['raw_to_blender']=j.observations(raw,b['faces']);item['blender_receipt']=b['receipt']
                bpairs=j.join(raw,b['faces'])
                item['all_blender_groups']={str(i):dict(Counter(str(x['uid']) for x,y,_,_ in bpairs if y['slot']==i)) for i in range(len(b['before']['mesh']['object_slots']))}
                item['blender_guard']='CANCELLED_UNCHANGED'
        report['cases'][name]=item
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    print('Boundary declared semantics and available native exact-UV controls checked')
if __name__=='__main__':main()
