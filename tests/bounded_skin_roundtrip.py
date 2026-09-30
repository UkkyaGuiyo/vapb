# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded evidence composition. No independent PASS is a same-entity proof."""
SUBJECTS = {
    'hierarchy': ('package_sha256','prefab_sha256','root_context_id','occurrence_id',
                  'prefab_guid','renderer_file_id','owner_file_id','realization_id','bone_ids','root_bone_id'),
    'geometry': ('realization_id','model_guid','fbx_sha256','mesh_local_id'),
    'skin': ('realization_id','model_guid','fbx_sha256','mesh_local_id','bone_ids','root_bone_id'),
    'material': ('prefab_guid','renderer_file_id','occurrence_id','realization_id','fbx_sha256','mesh_local_id'),
    'shape': ('realization_id','model_guid','fbx_sha256','mesh_local_id'),
    'finalizer': ('package_sha256','prefab_sha256','root_context_id','occurrence_id','prefab_guid',
                  'renderer_file_id','owner_file_id','realization_id','model_guid','fbx_sha256',
                  'mesh_local_id','bone_ids','root_bone_id'),
    'preservation': ('package_sha256','root_context_id','occurrence_id','realization_id','fbx_sha256'),
}
CHECKS = {
    'hierarchy': ('semantic_parent','renderer_owner','mesh_bridge','armature_relation','ordered_bones','root_bone'),
    'geometry': ('explicit_triangles','topology','sampled_surface','cp_correspondence'),
    'skin': (), 'material': ('effective_association',), 'shape': ('shape',),
    'finalizer': ('package_import','target_resolution','apply','repeated_apply'),
    'preservation': ('source_unchanged','rollback','rename_save_reopen'),
}


def accept(entity, evidence):
    from copy import deepcopy
    from .blender_geometry_abcd_compare import supported_skin_transport_verdict
    result = dict(supported_bounded_skin_roundtrip='UNSUPPORTED',
                  reason='CROSS_EVIDENCE_IDENTITY_UNPROVEN', renderer_owner='UNPROVEN')
    if not isinstance(entity, dict) or not isinstance(evidence, dict): return result
    for domain, fields in SUBJECTS.items():
        row = evidence.get(domain, {})
        subject = row.get('subject', {})
        for field in fields:
            if field not in entity or field not in subject or not entity[field]: return result
            if subject[field] != entity[field]:
                return dict(result, supported_bounded_skin_roundtrip='RED',
                            reason='CROSS_EVIDENCE_IDENTITY_MISMATCH', domain=domain, field=field)
        for check in CHECKS[domain]:
            value = row.get('checks', {}).get(check)
            if value is None or value in ('UNMEASURED','UNSUPPORTED','UNPROVEN'): return result
            if value != 'EXACT' and not (domain == 'shape' and value == 'NOT_APPLICABLE'):
                return dict(result, supported_bounded_skin_roundtrip='RED',
                            reason='MANDATORY_EVIDENCE_RED', domain=domain, field=check)
    skin = evidence['skin'].get('report', {})
    verdict = supported_skin_transport_verdict(skin)
    if skin.get('overall_supported_transport') != verdict or verdict != 'PASS':
        return dict(result, supported_bounded_skin_roundtrip='UNSUPPORTED' if
                    skin.get('overall_supported_transport') == 'UNSUPPORTED' or verdict == 'UNSUPPORTED'
                    else 'RED', reason='SKIN_TRANSPORT_NOT_PASS')
    return dict(result, supported_bounded_skin_roundtrip='PASS', reason='NONE',
                renderer_owner='EXACT', skin=deepcopy(skin),
                dimensions={domain:deepcopy(row['checks']) for domain,row in evidence.items()
                            if domain in CHECKS},
                known_boundaries=deepcopy(evidence.get('known_boundaries', {})))


def aggregate(joined, intersection, numeric):
    """Publish measured counts/dimensions only; private subjects never leave captures."""
    from copy import deepcopy
    skin=deepcopy(joined['result']['skin']);skin.pop('numeric_stages',None)
    real_rows=[row['skin'] for row in numeric['real_aggregate_only']]
    return dict(schema=1,scope='PUBLIC_DIRECT_EXPLICITLY_CONFIRMED_SKIN_SOURCE',
        source_start_commit='f9ad8a078133a2bffdc739a4e1189fb5d6d3ad20',
        public=dict(verdict=joined['result']['supported_bounded_skin_roundtrip'],
            renderer_owner=joined['result']['renderer_owner'],dimensions=joined['result']['dimensions'],
            skin=skin,known_boundaries=joined['result']['known_boundaries']),
        real=dict(cases=intersection['cases'],authoritative_joins=intersection['full_roundtrip_joins'],
            source_occurrence_to_numeric_export_joins=intersection['source_occurrence_to_numeric_export_joins'],
            ordered_bone_links=intersection['ordered_bone_links'],verdict=intersection['verdict'],reason=intersection['reason'],
            numeric_influences=sum(r['total_influences'] for r in real_rows),
            numeric_transport=[r['overall_supported_transport'] for r in real_rows],
            raw_changed=sum(r['raw_changed_influences'] for r in real_rows),
            deformation=[r['deformation'] for r in real_rows],
            missing_evidence=['ORDERED_BONE_TO_FINALIZER_TARGET_BRIDGE','FRESH_FINALIZER_ON_EXACT_FBX_REVISION']))


if __name__=='__main__':
    import json
    import sys
    from pathlib import Path
    joined,intersection,numeric,controls,output=map(Path,sys.argv[1:])
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    result=aggregate(read(joined),read(intersection),read(numeric));negative=read(controls)
    result['public'].update(negative_controls_rejected=negative['rejected'],negative_controls_total=negative['controls'])
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
