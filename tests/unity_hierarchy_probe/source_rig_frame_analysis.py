"""Compare full source/Prefab Unity frames through exact Mesh Skin binding slots.
Run in Blender: --python-exit-code 1 --python FILE -- SOURCE_OBSERVATION
PACKAGE_SKIN_OBSERVATION FULL_ORACLE CONTROL_REPORT OUTPUT.
Raw matrices and identities are written only to external OUTPUT; stdout is aggregate.
"""
import json
from pathlib import Path
import sys


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def unique(rows, key):
    values = {}
    for row in rows:
        identity = key(row)
        require(identity not in values, 'DUPLICATE_AUTHORITATIVE_IDENTITY')
        values[identity] = row
    return values


def analyze(source, public, oracle, controls):
    from mathutils import Matrix
    require(controls.get('pass') is True and controls.get('error') == 'NONE'
        and all(controls.get(k) is True for k in ('noopEquivalent','witnessEquivalent','restoredEquivalent',
            'metaStable','callbackExactlyOnce','markerIdentityUnique','allSkinBonesMarked',
            'sourceMetaRestored','sourceRawRestored','originalRevisionEquivalent')), 'SOURCE_CONTROLS_NOT_PASS')
    require(source['unity_version'] == public['unity_version'] == oracle['unityVersion'], 'UNITY_VERSION_MISMATCH')
    source_rows = unique(source['skinned_renderers'], lambda r: int(r['mesh_local_id']))
    frames = unique(source['model_frames'], lambda r: str(r['model_uid']))
    nodes = unique(oracle['nodes'], lambda n: n['transform']['globalId'])
    basis = Matrix(((-1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))

    def matrix(values):
        require(len(values) == 16, 'FULL_MATRIX_UNAVAILABLE')
        return Matrix(tuple(tuple(values[i+4*j] for j in range(4)) for i in range(4)))

    def converted(values):
        return basis @ matrix(values) @ basis.inverted()

    pairs = {}
    uid_targets = {}
    renderer_rows = []
    binding_count = 0
    for skin in public['skinned_renderers']:
        require(skin['mesh']['guid'] == source['model_guid'], 'MODEL_GUID_MISMATCH')
        original = source_rows.get(int(skin['mesh']['local_id']))
        require(original is not None, 'SOURCE_MESH_IDENTITY_MISSING')
        require(len(original['ordered_bones']) == len(skin['ordered_bones'])
            == original['bindpose_count'] == skin['bindpose_count'], 'AUTHORED_SLOT_COUNT_MISMATCH')
        renderer_pairs = []
        for authored, witnessed in zip(skin['ordered_bones'], original['ordered_bones']):
            uid = str(witnessed['model_uid'])
            target_id = authored['transform']['global_id']
            node = nodes.get(target_id)
            require(node is not None and node['transform']['guid'] == authored['transform']['guid']
                and node['transform']['localId'] == authored['transform']['local_id'], 'PREFAB_BONE_IDENTITY_MISMATCH')
            frame = frames.get(uid)
            require(frame is not None and frame['transform_local_id'] == witnessed['transform_local_id'],
                'SOURCE_MODEL_UID_FRAME_MISMATCH')
            delta = converted(node['worldMatrix']) @ converted(frame['local_to_world_matrix']).inverted()
            key = (uid, target_id)
            row = dict(model_uid=uid, prefab_transform=node['transform'], source_frame=frame,
                prefab_world_matrix=node['worldMatrix'], placement_delta_blender=[list(r) for r in delta])
            if key in pairs:
                require(pairs[key]['placement_delta_blender'] == row['placement_delta_blender'], 'REPEATED_BINDING_FRAME_DRIFT')
            else:
                pairs[key] = row
            uid_targets.setdefault(uid, set()).add(target_id)
            renderer_pairs.append(key)
            binding_count += 1
        renderer_rows.append(renderer_pairs)
    require(pairs, 'NO_AUTHORITATIVE_BONE_PAIRS')
    anchor = Matrix(next(iter(pairs.values()))['placement_delta_blender'])
    residuals = []
    for row in pairs.values():
        delta = Matrix(row['placement_delta_blender'])
        error = max(abs(delta[i][j]-anchor[i][j]) for i in range(4) for j in range(4))
        tolerance = 2e-5 + 1e-6*max(abs(v) for m in (delta,anchor) for r in m for v in r)
        row['delta_max_error_from_anchor'] = error
        row['delta_agrees'] = error <= tolerance
        residuals.append(error)
    members = set(uid_targets)
    outside = []
    for row in pairs.values():
        parent_uid = row['source_frame']['parent_model_uid']
        if parent_uid in members:
            continue
        node = nodes[row['prefab_transform']['globalId']]
        parent_id = node.get('parentTransform')
        parent_node = nodes.get(parent_id['globalId']) if parent_id else None
        parent_frame = frames.get(parent_uid)
        parent_delta = (converted(parent_node['worldMatrix']) @ converted(parent_frame['local_to_world_matrix']).inverted()) if parent_node and parent_frame else None
        error = max(abs(parent_delta[i][j]-anchor[i][j]) for i in range(4) for j in range(4)) if parent_delta is not None else None
        outside.append(dict(source_parent_model_uid=parent_uid, source_parent_frame_available=parent_frame is not None,
            prefab_parent_transform=parent_id, prefab_parent_frame_available=parent_node is not None,
            parent_delta_agrees=error is not None and error <= 2e-5,
            parent_delta_max_error=error))
    return dict(status='AUTHORITATIVE_SLOT_FRAME_COMPARISON', renderer_count=len(renderer_rows),
        binding_count=binding_count, unique_pair_count=len(pairs), source_bone_uid_count=len(members),
        source_uid_multiple_prefab_targets_count=sum(len(v)>1 for v in uid_targets.values()),
        all_bone_placement_deltas_agree=all(r['delta_agrees'] for r in pairs.values()),
        maximum_delta_residual=max(residuals), common_placement_delta_blender=[list(r) for r in anchor],
        source_parents_outside_weighted_slots=outside, pairs=list(pairs.values()))


def main():
    source, public, oracle, controls, output = sys.argv[sys.argv.index('--')+1:]
    output = Path(output)
    require(not output.exists(), 'OUTPUT_ALREADY_EXISTS')
    report = analyze(read(source), read(public), read(oracle), read(controls))
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('AUTHORITATIVE_FRAME_COMPARISON renderers='+str(report['renderer_count'])
        +' binding_slots='+str(report['binding_count'])+' unique_bones='+str(report['source_bone_uid_count'])
        +' all_deltas_agree='+str(report['all_bone_placement_deltas_agree'])
        +' source_parent_outside_slot_count='+str(len(report['source_parents_outside_weighted_slots'])))


if __name__ == '__main__':
    main()
