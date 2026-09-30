# SPDX-License-Identifier: GPL-3.0-or-later
"""Read known immutable diagnostic artifacts; report a partial join, never PASS.

CLI: hierarchy baseline folder, D1 spot-check folder, numeric folder, output.
No assets are imported and no private identifiers are emitted in the summary.
"""
import hashlib
import json
from pathlib import Path
import sys


def inspect(baseline, geometry, numeric):
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    snapshot=read(baseline/'blender_snapshot.json')
    selection=read(geometry/'PrivateSelection.json')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    partial=0; bone_links=0
    for index in (0,3):
        row,=[r for r in selection if r['sample']==index]
        before=read(geometry/('sample_%02d'%index)/'BlenderD.json')
        native=read(numeric/('sample_%02d'%index)/'D1.json')
        export,=[r for r in before['exports'] if r['mode']=='D1']
        skins=[s for s in snapshot['native_skin']['skins'] if s['occurrence_id']==row['source_occurrence']
               and s['mesh_guid']==row['mesh_guid'] and str(s['mesh_local_id'])==str(row['mesh_local_id'])]
        if (len(skins)!=1 or before['source_package_sha256']!=snapshot['package_sha256']
            or before['baseline_blend_sha256']!=digest(baseline/'baseline.blend')
            or export['fbx_sha256']!=native['input_sha256']
            or export['fbx_sha256']!=digest(numeric/('sample_%02d'%index)/'D1.fbx')): continue
        skin,=skins
        if not skin['renderer_owner_valid'] or not skin['root_frame_binding_valid']: continue
        partial+=1
        # Explicit labels were authored onto copied Bone handles, with raw UIDs
        # retained in the immutable export artifact; original names are irrelevant.
        labels=export['bone_export_labels']
        wanted=[b['model_uid'] for b in skin['bones']]
        actual=[labels[b['export_label']] for b in native['meshes'][0]['bones']]
        if wanted==actual:bone_links+=len(wanted)
    return dict(cases=2,source_occurrence_to_numeric_export_joins=partial,
                ordered_bone_links=bone_links,full_roundtrip_joins=0,verdict='UNSUPPORTED',
                reason='FINALIZER_TARGET_AND_APPLY_NOT_CAPTURED_FOR_DIAGNOSTIC_EXPORT',
                limitation='PARTIAL_SOURCE_EXPORT_JOIN_IS_NOT_FULL_ROUNDTRIP_ACCEPTANCE')


if __name__=='__main__':
    baseline,geometry,numeric,output=map(Path,sys.argv[1:])
    result=inspect(baseline,geometry,numeric)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
