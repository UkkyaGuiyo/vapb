"""Independent native-judge controls, using existing exact-cover primitives."""
import copy
import unittest
from test_candidates import fixture
from judge_holdout import judge,verify_metadata


def holdout_fixture():
    raw,meta,occ=fixture();groups=[dict(topology=t,index_count=0,base_vertex=0,indices=[]) for t in ['Triangles','Quads','Quads','Triangles']]
    uv=[];labels=[0,1,2,3,0,1]
    for p,g in zip(raw['polygons'],labels):
        start=len(uv);uv.extend(dict(x=u[0],y=u[1]) for u in p['uv']);groups[g]['indices'].extend(range(start,len(uv)))
    for g in groups:g['index_count']=len(g['indices'])
    refs=[occ['materials'][i] for i in range(4)]
    refs_native=[dict(guid=r['guid'],file_id=r['file_id']) for r in refs]
    expected=[dict(polygon=i,group=g,topology=groups[g]['topology'],material=refs[g]) for i,g in enumerate(labels)]
    record=dict(raw=raw,asset_sha256={'OrderedSix.fbx':'fbx-sha','OrderedSix.fbx.meta':'meta-sha','Receiver.prefab':'prefab-sha'},
        package_id='pkg',creation=dict(mesh=dict(guid='a'*32,file_id='-43'),model_renderer=dict(guid='a'*32,file_id='-23'),
            receiver_renderer=dict(guid='f'*32,file_id='-23'),prefab=dict(guid='f'*32,file_id='100'),materials=refs_native),
        predictions={'PAIR_FIRST':dict(groups=groups,faces=expected)})
    snapshot=dict(unity_version='2022.3.22f1',keep_quads=True,policy='{"meshes":{"keepQuads":true}}',apply_base_vertex=True,
        fbx_sha256='fbx-sha',fbx_sha256_after='fbx-sha',meta_sha256='meta-sha',meta_sha256_after='meta-sha',prefab_sha256='prefab-sha',
        mesh=record['creation']['mesh'],renderer=record['creation']['model_renderer'],receiver_renderer=record['creation']['receiver_renderer'],
        prefab=record['creation']['prefab'],materials=refs_native,groups=groups,uv=uv)
    return record,snapshot


class JudgeControls(unittest.TestCase):
    def test_supplement_revision_and_receiver_mesh(self):
        record,snapshot=holdout_fixture()
        supplement=dict(phase='METADATA_ONLY',utc='supplemental-time',policy=snapshot['policy'],
            receiver_mesh=snapshot['mesh'],materials=snapshot['materials'],
            asset_hashes=[dict(name=k,sha256=v) for k,v in record['asset_sha256'].items()])
        self.assertTrue(verify_metadata(record,snapshot,supplement))
        s=copy.deepcopy(supplement);s['receiver_mesh']=dict(guid='wrong',file_id='-43')
        with self.assertRaises(ValueError):verify_metadata(record,snapshot,s)
        s=copy.deepcopy(supplement);s['asset_hashes'][0]['sha256']='changed'
        with self.assertRaises(ValueError):verify_metadata(record,snapshot,s)
    def test_complete_and_swapped_same_count(self):
        record,snapshot=holdout_fixture()
        self.assertEqual(judge(record,snapshot)['hypotheses']['PAIR_FIRST'],'SUPPORTED_IN_THIS_FIXTURE')
        s=copy.deepcopy(snapshot);s['groups'][0],s['groups'][3]=s['groups'][3],s['groups'][0]
        self.assertEqual(judge(record,s)['hypotheses']['PAIR_FIRST'],'FALSIFIED')
        r=copy.deepcopy(record);r['predictions']['PAIR_FIRST']['faces'][0]['material']=r['predictions']['PAIR_FIRST']['faces'][2]['material']
        self.assertEqual(judge(r,snapshot)['hypotheses']['PAIR_FIRST'],'FALSIFIED')

    def test_missing_duplicate_unknown_revision(self):
        record,snapshot=holdout_fixture()
        def missing(s):s['groups'][0]['indices']=s['groups'][0]['indices'][:-3];s['groups'][0]['index_count']-=3
        def duplicate(s):s['groups'][0]['indices']+=s['groups'][0]['indices'][:3];s['groups'][0]['index_count']+=3
        for change in [missing,duplicate,lambda s:s['groups'][0].update(topology='Lines'),lambda s:s.update(meta_sha256='changed')]:
            s=copy.deepcopy(snapshot);change(s)
            with self.assertRaises(ValueError):judge(record,s)

if __name__=='__main__':unittest.main()
