# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare bounded private D reports; write only external evidence and safe counts.

Blender CLI: PRIVATE_EXPORT_FOLDER PRIVATE_UNITY_FOLDER NEW_OUTPUT_JSON.
"""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_geometry_abcd_compare import compare,unity_row,d_identity_metrics,skin_export_context,skin_deformation_measurement


def main():
    source,unity,output=map(Path,sys.argv[sys.argv.index('--')+1:])
    assert not output.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    selection=read(source/'PrivateSelection.json')
    rows=[]
    for chosen in selection:
        name='sample_%02d'%chosen['sample']
        folder=source/name; project=unity/(name+'_unity')
        if not project.exists():project=unity/name
        marker,=read(folder/'ControlPointManifest.json')['meshes']
        report=read(folder/'BlenderD.json')
        status=read(project/'UnityDStatus.json')
        assert status['status']=='CAPTURED' and status['editor_version']=='2022.3.22f1'
        for export in report['exports']:
            mode=export['mode'];capture=read(project/(mode+'.json'))
            revision=hashlib.sha256((folder/(mode+'.fbx')).read_bytes()).hexdigest()
            assert revision==capture['input_sha256']==export['fbx_sha256']
            assert capture['editor_version']=='2022.3.22f1'
            before,=export['pre_export'];actual,=capture['meshes']
            rows.append(dict(sample=chosen['sample'],source_category=chosen['source_category'],
                source_ngon_count=chosen['source_ngon_count'],mode=mode,input_sha256=revision,
                comparison=compare(before,unity_row(actual),marker['uv_channel']),
                identity=d_identity_metrics(before,actual,skin_context=skin_export_context(folder,export,capture,
                    project/'Assets/VAPBExport',skin_deformation_measurement(before,actual))),unity_status=status))
    output.write_text(json.dumps(dict(rows=rows),indent=2))
    for mode in ('D0','D1'):
        subset=[r for r in rows if r['mode']==mode]
        print('REAL_D_AGGREGATE mode=%s cases=%d topology_exact=%d position_exact=%d baked_exact=%d shape_exact_or_na=%d skin_binding_exact=%d' %
            (mode,len(subset),sum(r['comparison']['topology']=='EXACT' for r in subset),
             sum(r['comparison']['vertex_correspondence']['status']=='EXACT' for r in subset),
             sum(r['comparison'].get('baked_vertex_correspondence',{}).get('status')=='EXACT' for r in subset),
             sum(r['identity']['shape_geometry']['status'] in ('EXACT','NOT_APPLICABLE') for r in subset),
             sum(r['identity']['skin_bone_weight_binding']=='EXACT' for r in subset)))


if __name__=='__main__':main()
