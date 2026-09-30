# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import unittest
from .small_weight_metrics import compare, f32


class SmallWeightNegativeControls(unittest.TestCase):
    def setUp(self):
        self.source=dict(cp_count=3,ladder=[.0005],fbx_sha256='a'*64,mesh_label='WEIGHT-MESH-0',clusters=[
            dict(bone_label=label,weights=[dict(cp=i,weight=f32(w)) for i in range(3)])
            for label,w in [('WEIGHT-BONE-0',.0005),('WEIGHT-BONE-1',.9995)]])
        zero=dict(x=0,y=0,z=0)
        self.capture=dict(hash='a'*64,mesh_label='WEIGHT-MESH-0',bones=['WEIGHT-BONE-1','WEIGHT-BONE-0'],vertices=[
            dict(cp=i,influences=[dict(bone=j,label=label,weight=f32(w)) for j,(label,w) in enumerate([
                ('WEIGHT-BONE-1',.9995),('WEIGHT-BONE-0',.0005)])],baked=zero,raw_cpu=zero) for i in range(3)])

    def test_green_and_weight_changed_red(self):
        self.assertTrue(all(r['exact'] for r in compare(self.source,self.capture)))
        self.capture['vertices'][0]['influences'][1]['weight']=.0004
        self.assertFalse(compare(self.source,self.capture)[0]['exact'])

    def test_source_weight_cluster_and_cp_corruption_reject(self):
        for change in ['weight','cluster','cp']:
            bad=copy.deepcopy(self.source)
            if change=='weight':bad['clusters'][0]['weights'][0]['weight']=.0004
            elif change=='cluster':
                bad['clusters'][0]['bone_label'],bad['clusters'][1]['bone_label']=bad['clusters'][1]['bone_label'],bad['clusters'][0]['bone_label']
            else:bad['clusters'][0]['weights'][0]['cp']=1
            with self.assertRaises(ValueError):compare(bad,self.capture)

    def test_hash_mesh_bone_index_and_cp_corruption_reject(self):
        for change in ['hash','mesh','bone','cp']:
            bad=copy.deepcopy(self.capture)
            if change=='hash':bad['hash']='b'*64
            elif change=='mesh':bad['mesh_label']='OTHER'
            elif change=='bone':bad['vertices'][0]['influences'][0]['bone']=1
            else:bad['vertices'][0]['cp']=1
            with self.assertRaises(ValueError):compare(self.source,bad)
