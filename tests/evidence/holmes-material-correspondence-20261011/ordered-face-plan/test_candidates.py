"""Input-only controls: no native files or Blender runtime required."""
import copy
import tempfile
import unittest
from pathlib import Path
from candidates import predict_ordered_partitions, plan_receiver_materials


def fixture():
    raw = dict(model_uid=10, geometry_uid=20, material_connections=[30, 40], polygons=[])
    for i, (uid, size) in enumerate([(30,3),(40,4),(30,4),(40,3),(30,3),(40,4)]):
        uv = [[i/8+x/32,y/32] for x,y in ([(0,0),(1,0),(0,1)] if size == 3 else [(0,0),(1,0),(1,1),(0,1)])]
        raw['polygons'].append(dict(polygon=i,uid=uid,cp=list(range(i*4,i*4+size)),uv=uv,
            positions=[[i*3+x,y,0] for x,y in ([(0,0),(1,0),(0,1)] if size == 3 else [(0,0),(1,0),(1,1),(0,1)])]))
    refs = [dict(source_package_id='pkg',guid=str(i+1)*32,file_id=str(-100-i)) for i in range(4)]
    occurrence = dict(materials=dict(enumerate(refs)),material_slot_count=4,material_status='EXACT',
        root_package_id='pkg',root_asset_guid='f'*32,root_revision_sha256='prefab-sha',
        source_revision_sha256='prefab-sha',occurrence_id='occ',instance_edge_path=[],
        source_key=dict(source_asset_guid='f'*32,renderer_file_id=-23),
        mesh=dict(mesh_guid='a'*32,mesh_file_id=-43),source_binding='UNPROVEN',
        input_revision=dict(fbx_sha256='fbx-sha',meta_sha256='meta-sha'),
        providers=[dict(reference=r,revision_sha256='mat-'+str(i)) for i,r in enumerate(refs)])
    meta=dict(keepQuads=1,fbx_sha256='fbx-sha',meta_sha256='meta-sha',mesh_guid='a'*32)
    return raw,meta,occurrence


class Candidates(unittest.TestCase):
    def test_order_and_repeated_pairs_without_observations(self):
        raw,meta,occ=fixture()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            self.assertEqual(list(Path(directory).iterdir()),[])
            p=predict_ordered_partitions(raw,meta)
            self.assertEqual([g['polygons'] for g in p['groups']],[[0,4],[1,5],[2],[3]])
            self.assertEqual([g['topology'] for g in p['groups']],['Triangles','Quads','Quads','Triangles'])
            result=plan_receiver_materials(p,occ)
            self.assertEqual([r['group'] for r in result['faces']],[0,1,2,3,0,1])
            self.assertFalse(result['ready_to_apply'])
            self.assertEqual(result['partition_evidence'],'CANDIDATE')
            self.assertEqual(result['source_binding'],'UNPROVEN')
            self.assertEqual(result['unresolved'],[])
            self.assertEqual(result['faces'][3]['material']['file_id'],'-103')
        meta['keepQuads']=0
        self.assertEqual([g['polygons'] for g in predict_ordered_partitions(raw,meta)['groups']],[[0,2,4],[1,3,5]])

    def test_reject_unsupported_input(self):
        raw,meta,_=fixture()
        changes=[lambda r:r['polygons'].pop(),lambda r:r['polygons'].append(copy.deepcopy(r['polygons'][0])),
            lambda r:r['polygons'][0].update(uid=999),lambda r:r['polygons'][0]['cp'].append(99),
            lambda r:r['polygons'][0]['cp'].__setitem__(0,70000)]
        # Missing polygon alone can be a legitimate different input; an inconsistent ID sequence is not.
        changes[0]=lambda r:r['polygons'].pop(1)
        for change in changes:
            r=copy.deepcopy(raw);change(r)
            with self.assertRaises(ValueError):predict_ordered_partitions(r,meta)
        for setting in [None,2,'1',True]:
            m=dict(meta,keepQuads=setting)
            with self.assertRaises(ValueError):predict_ordered_partitions(raw,m)

    def test_receiver_unresolved_reasons(self):
        raw,meta,occ=fixture(); p=predict_ordered_partitions(raw,meta)
        variants=[('REFERENCE_LENGTH_MISMATCH',lambda o:o.update(material_slot_count=3)),
            ('NULL_REFERENCE',lambda o:o['materials'].__setitem__(1,None)),
            ('PROVIDER_MISSING',lambda o:o.update(providers=[])),
            ('SCOPE_CONFLICT',lambda o:o['materials'][0].update(source_package_id='other')),
            ('REVISION_MISMATCH',lambda o:o['input_revision'].update(meta_sha256='changed')),
            ('PROVIDER_AMBIGUOUS',lambda o:o['providers'].append(copy.deepcopy(o['providers'][0])))]
        for reason,change in variants:
            o=copy.deepcopy(occ);change(o)
            self.assertIn(reason,plan_receiver_materials(p,o)['unresolved'])
        o=copy.deepcopy(occ);o['materials'][0],o['materials'][2]=o['materials'][2],o['materials'][0]
        self.assertNotEqual(plan_receiver_materials(p,o)['faces'],plan_receiver_materials(p,occ)['faces'])


if __name__=='__main__':unittest.main()
