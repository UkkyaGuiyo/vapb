"""Input-only applicability candidates; no native observation or EXACT claim."""
import argparse
import json
from pathlib import Path
from read_input import decode, parse


def diagnose(raw, mesh_meta):
    try:
        keep = mesh_meta.get('keepQuads')
        if type(keep) is not int or keep not in (0, 1):
            raise ValueError('keepQuads missing or invalid; effective environment unknown')
        polygons = raw['polygons']
        if not polygons or any(len(p['uv']) not in (3, 4) for p in polygons):
            raise ValueError('outside triangle/quad polygon scope')
        uids = list(dict.fromkeys(p['uid'] for p in polygons))
        kinds = {len(p['uv']) for p in polygons}
        status = ('TRIANGLE_ONLY_CANDIDATE' if kinds == {3} else
                  'TRIANGULATION_BOUNDARY_UNVERIFIED' if not keep else
                  'MIXED_TOPOLOGY_REQUIRES_PARTITION_RULE' if kinds == {3, 4} else 'UNKNOWN_SCOPE')
        reason = 'quad-only ON is outside this mixed-topology experiment' if status == 'UNKNOWN_SCOPE' else ''
        return dict(status=status, reason=reason, declared_keep_quads=bool(keep),
                    effective_policy_proven=False,
                    P_UID=[dict(uid=uid, polygons=[p['polygon'] for p in polygons if p['uid'] == uid]) for uid in uids],
                    P_UID_TOPOLOGY_unordered=[dict(uid=uid, topology='Triangles' if count == 3 else 'Quads',
                                                   polygons=[p['polygon'] for p in polygons if p['uid'] == uid and len(p['uv']) == count])
                                             for uid in uids for count in sorted(kinds)
                                             if any(p['uid'] == uid and len(p['uv']) == count for p in polygons)],
                    group_order='UNDETERMINED', exact=False)
    except (KeyError, TypeError, ValueError) as error:
        return dict(status='UNKNOWN_SCOPE', reason=str(error), effective_policy_proven=False, exact=False)


def from_nodes(root, mesh_meta):
    try:
        return diagnose(decode(root), mesh_meta)
    except (ValueError, IndexError, KeyError, TypeError, AttributeError) as error:
        return dict(status='UNKNOWN_SCOPE', reason=str(error), effective_policy_proven=False, exact=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--fbx', type=Path, required=True)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--addon', type=Path, required=True)
    ap.add_argument('--mesh-meta-json', type=Path, required=True, help='parsed meshes metadata only')
    args = ap.parse_args()
    root, _ = parse(args.fbx, args.repo, args.addon)
    print(json.dumps(from_nodes(root, json.loads(args.mesh_meta_json.read_text())), indent=2))
