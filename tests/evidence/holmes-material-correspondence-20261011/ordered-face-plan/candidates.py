"""Experimental input-only candidate. No observations, EXACT claim or product hook."""
from collections import OrderedDict
import copy
import math


def predict_ordered_partitions(raw, meshes_meta):
    keep = meshes_meta.get('keepQuads')
    if type(keep) is not int or keep not in (0,1):
        raise ValueError('missing/invalid declared keepQuads')
    required = ('fbx_sha256','meta_sha256','mesh_guid')
    if any(not meshes_meta.get(k) for k in required):
        raise ValueError('input revision/asset identity missing')
    slots=raw['material_connections']; polygons=raw['polygons']
    if not slots or len(set(slots)) != len(slots) or any(type(uid) is not int for uid in slots):
        raise ValueError('missing/invalid/duplicate Material connection')
    if not polygons or [p['polygon'] for p in polygons] != list(range(len(polygons))):
        raise ValueError('missing/duplicate/out-of-order raw polygon identity')
    if any(type(raw.get(k)) is not int for k in ('model_uid','geometry_uid')):
        raise ValueError('missing Model/Geometry identity')
    groups=OrderedDict(); fingerprints=set()
    for p in polygons:
        size=len(p['cp']); uv=[tuple(x) for x in p['uv']]; pos=p['positions']
        if p['uid'] not in slots or size not in (3,4) or len(uv)!=size or len(pos)!=size:
            raise ValueError('invalid reference or unsupported polygon topology')
        if any(type(c) is not int or not 0<=c<65535 for c in p['cp']) or len(set(p['cp']))!=size:
            raise ValueError('invalid/large/duplicate corner index')
        if any(len(c)!=2 or any(not math.isfinite(v) for v in c) for c in uv) or len(set(uv))!=size or fingerprints.intersection(uv):
            raise ValueError('ambiguous/nonfinite diagnostic corners')
        fingerprints.update(uv)
        if any(len(c)!=3 or any(not math.isfinite(v) for v in c) for c in pos):
            raise ValueError('invalid position stream')
        # Axis-aligned planar fixture, independent of exporter axis conversion.
        constant=[axis for axis in range(3) if len({c[axis] for c in pos})==1]
        if len(constant)!=1:
            raise ValueError('outside planar fixture scope')
        axes=[axis for axis in range(3) if axis!=constant[0]]
        for corners in (uv,[[c[axis] for axis in axes] for c in pos]):
            turns=[]
            for i in range(size):
                a,b,c=corners[i-2],corners[i-1],corners[i]
                turns.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
            if not (all(v>0 for v in turns) or all(v<0 for v in turns)):
                raise ValueError('outside strict convex fixture scope')
        topology='Triangles' if not keep or size==3 else 'Quads'; key=(p['uid'],topology)
        if key not in groups:
            groups[key]=dict(ordinal=len(groups),uid=p['uid'],topology=topology,polygons=[],multiplicity=0)
        groups[key]['polygons'].append(p['polygon']);groups[key]['multiplicity']+=1
    return dict(partition_evidence='CANDIDATE',ready_to_apply=False,model_uid=raw['model_uid'],
        geometry_uid=raw['geometry_uid'],input_revision={k:meshes_meta[k] for k in required},
        declared_keep_quads=keep,effective_policy_evidence='UNPROVEN_DECLARATION',groups=list(groups.values()),
        raw_polygons=copy.deepcopy(polygons))


def reference_key(ref):
    if not isinstance(ref,dict):raise ValueError('reference missing')
    package=ref.get('source_package_id');guid=ref.get('guid');fid=str(ref.get('file_id',''))
    if not package or not isinstance(guid,str) or len(guid)!=32 or any(c not in '0123456789abcdef' for c in guid.lower()) or not fid.lstrip('-').isdigit() or int(fid)==0:
        raise ValueError('invalid package/GUID/signed fileID')
    return str(package),guid.lower(),str(int(fid))


def plan_receiver_materials(partitions, occurrence):
    unresolved=[]; faces=[]
    def issue(reason):
        if reason not in unresolved:unresolved.append(reason)
    values=occurrence.get('materials',{});count=occurrence.get('material_slot_count')
    if occurrence.get('material_status')!='EXACT':issue('SERIALIZED_REFERENCE_UNRESOLVED')
    if type(count) is not int or count != len(partitions['groups']) or len(values)!=count or set(str(k) for k in values)!=set(str(i) for i in range(count or 0)):
        issue('REFERENCE_LENGTH_MISMATCH')
    revision=occurrence.get('input_revision',{})
    if any(revision.get(k)!=partitions['input_revision'][k] for k in ('fbx_sha256','meta_sha256')):
        issue('REVISION_MISMATCH')
    if occurrence.get('mesh',{}).get('mesh_guid')!=partitions['input_revision']['mesh_guid']:
        issue('MESH_IDENTITY_CONFLICT')
    if occurrence.get('root_revision_sha256')!=occurrence.get('source_revision_sha256') or occurrence.get('instance_edge_path'):
        issue('OCCURRENCE_REVISION_OR_SCOPE_UNSUPPORTED')
    for group in partitions['groups']:
        i=group['ordinal'];ref=values.get(i,values.get(str(i)))
        if ref is None:issue('NULL_REFERENCE')
        else:
            try:
                key=reference_key(ref)
                if key[0]!=occurrence.get('root_package_id'):issue('SCOPE_CONFLICT')
                providers=[p for p in occurrence.get('providers',[]) if reference_key(p['reference'])==key and p.get('revision_sha256')]
                if not providers:issue('PROVIDER_MISSING')
                elif len(providers)!=1:issue('PROVIDER_AMBIGUOUS')
            except (ValueError,KeyError):issue('INVALID_REFERENCE')
        for polygon in group['polygons']:
            faces.append(dict(polygon=polygon,model_uid=partitions['model_uid'],geometry_uid=partitions['geometry_uid'],
                raw_uid=group['uid'],group=i,topology=group['topology'],material=copy.deepcopy(ref)))
    return dict(ready_to_apply=False,partition_evidence='CANDIDATE',serialized_reference_evidence=occurrence.get('material_status'),
        source_binding=occurrence.get('source_binding','UNPROVEN'),unresolved=unresolved,faces=sorted(faces,key=lambda r:r['polygon']),
        input_revision=copy.deepcopy(partitions['input_revision']),receiver=copy.deepcopy(occurrence))
