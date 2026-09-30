# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare exact production FBX revisions with fresh public Unity observations."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.tests.blender_geometry_abcd_compare import compare,unity_row,d_identity_metrics

project,report_path,output=map(Path,sys.argv[sys.argv.index('--')+1:])
assert not output.exists()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
report=read(report_path)
status=read(project/'UnityDStatus.json')
assert status['status']=='CAPTURED' and status['editor_version']=='2022.3.22f1'
assert report['manifest']==read(project/'ControlPointManifest.json')
spec,=report['manifest']['meshes']
rows=[]
for export in report['exports']:
    mode=export['mode'];capture=read(project/(mode+'.json'))
    revision=hashlib.sha256((report_path.parent/(mode+'.fbx')).read_bytes()).hexdigest()
    assert revision==export['fbx_sha256']==capture['input_sha256']
    before,=export['pre_export'];actual,=capture['meshes']
    row=dict(mode=mode,fbx_sha256=revision,
        comparison=compare(before,unity_row(actual),spec['uv_channel']),
        identity=d_identity_metrics(before,actual),raw_polygon_sizes=export['raw_polygon_sizes'])
    if mode=='D1':
        assert set(export['raw_polygon_sizes'])=={3}
        assert row['comparison']['topology']=='EXACT'
        assert row['comparison']['surface']['status']=='SAMPLED_EXACT'
    rows.append(row)
output.write_text(json.dumps(dict(rows=rows,unity_status=status),indent=2))
print('PRODUCTION_FRESH_UNITY_GREEN D1_topology=EXACT D1_sampled_surface=EXACT')
