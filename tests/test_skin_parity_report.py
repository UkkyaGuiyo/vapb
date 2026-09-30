# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import json
from pathlib import Path
import struct
import unittest
from .blender_geometry_abcd_compare import d_identity_metrics
from .weight_numeric_models import bits


class SkinParityReportTests(unittest.TestCase):
    def fixture(self):
        data=json.loads((Path(__file__).parent/'unity_small_weight_probe/numeric_measurements.json').read_text())
        source=data['source_capture'];capture=data['unity_capture']['first']
        before=dict(vertex_control_point_indices=[r['cp'] for r in source['B0']],shapes=[],
            skin_weights=[[dict(group=w['bone'],weight=w['value']) for w in r['weights']] for r in source['B0']])
        observed=dict(vertex_control_point_indices=[r['cp'] for r in capture['vertices']],
            bones=[dict(index=i,export_label=b) for i,b in enumerate(capture['bones'])],
            bone_weights=[dict(vertex=i,bone=w['bone'],weight=w['value']) for i,r in enumerate(capture['vertices']) for w in r['weights']],
            shape_frames=[],renderer_local_to_world=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
            guid=capture['guid'],local_id=capture['id'],marker_invalid_count=0)
        context=dict(unity_version=data['unity_version'],fbx_sha256=source['fbx_sha256'],
            expected_fbx_sha256=source['fbx_sha256'],observed_fbx_sha256=capture['hash'],
            mesh_guid=capture['guid'],mesh_local_id=capture['id'],
            raw_weights={(w['cp'],c['bone_label']):w['weight'] for c in source['clusters'] for w in c['weights']},
            preprocess_policy=dict(model_guid=capture['guid'],model_sha256=capture['hash'],version=1),
            staged_weights=copy.deepcopy(before['skin_weights']),deformation=dict(
                provenance='PUBLIC_CONTROLLED_POSE_BAKEMESH_TRUE_TRANSFORMPOINT',metrics=data['deformation_max_m']))
        return before,observed,context

    def report(self,b,o,c):return d_identity_metrics(b,o,skin_context=c)['skin_report']

    def test_raw_red_and_bitwise_exact_remain_independent(self):
        b,o,c=self.fixture();r=self.report(b,o,c)
        self.assertEqual(r['unity_representation'],'EXACT')
        self.assertEqual(r['raw_numeric'],'RAW_NUMERIC_DIFFERENCE')
        self.assertGreater(r['raw_changed_influences'],0)
        self.assertEqual(r['representation_exact_influences'],183)
        self.assertEqual(r['missing_influences'],0)
        self.assertEqual(r['deformation']['status'],'MEASURED_NONZERO')
        self.assertEqual(r['overall_supported_transport'],'NOT_ASSESSED_PRODUCT_POLICY')

    def test_one_ulp_is_red(self):
        b,o,c=self.fixture();w=o['bone_weights'][0]
        w['weight']=struct.unpack('<f',struct.pack('<I',bits(w['weight'])+1))[0]
        self.assertEqual(self.report(b,o,c)['unity_representation'],'NUMERIC_MISMATCH')

    def test_swapped_bone_claim_is_red(self):
        b,o,c=self.fixture();o['bones'][0]['export_label'],o['bones'][1]['export_label']=o['bones'][1]['export_label'],o['bones'][0]['export_label']
        self.assertNotEqual(self.report(b,o,c)['unity_representation'],'EXACT')

    def test_missing_positive_influence_is_red(self):
        b,o,c=self.fixture();o['bone_weights'].pop(0);r=self.report(b,o,c)
        self.assertEqual(r['missing_influences'],1)
        self.assertNotEqual(r['unity_representation'],'EXACT')

    def test_unsupported_version_and_count_reject(self):
        b,o,c=self.fixture();c['unity_version']='6000.0'
        self.assertEqual(self.report(b,o,c)['unity_representation'],'UNSUPPORTED_REPRESENTATION')
        b,o,c=self.fixture();cp=9
        b['skin_weights'][cp].append(dict(group='EXTRA',weight=.25));c['raw_weights'][(cp,'EXTRA')]=.25
        o['bones'].append(dict(index=4,export_label='EXTRA'));o['bone_weights'].append(dict(vertex=cp,bone=4,weight=.25))
        c['staged_weights']=copy.deepcopy(b['skin_weights'])
        self.assertEqual(self.report(b,o,c)['unity_representation'],'UNSUPPORTED_REPRESENTATION')

    def test_stale_hash_and_policy_reject(self):
        b,o,c=self.fixture();c['observed_fbx_sha256']='0'*64
        self.assertEqual(self.report(b,o,c)['reason'],'SOURCE_REVISION_MISMATCH')
        b,o,c=self.fixture();c['preprocess_policy']['model_sha256']='0'*64
        self.assertNotEqual(self.report(b,o,c)['unity_representation'],'EXACT')

    def test_duplicate_unexpected_bone_and_cp_reject(self):
        for change in ('bone','influence','cp','unexpected'):
            b,o,c=self.fixture()
            if change=='bone':o['bones'].append(copy.deepcopy(o['bones'][0]))
            elif change=='influence':o['bone_weights'].append(copy.deepcopy(o['bone_weights'][0]))
            elif change=='cp':o['vertex_control_point_indices'][0]=None
            else:o['bones'].append(dict(index=4,export_label='EXTRA'));o['bone_weights'].append(dict(vertex=0,bone=4,weight=.25))
            self.assertNotEqual(self.report(b,o,c)['unity_representation'],'EXACT',change)

    def test_missing_context_and_nonfloat_origin_reject(self):
        b,o,c=self.fixture();self.assertNotEqual(d_identity_metrics(b,o)['skin_report']['unity_representation'],'EXACT')
        c['raw_weights'][(0,'WEIGHT-BONE-0')]=.1
        self.assertEqual(self.report(b,o,c)['unity_representation'],'UNSUPPORTED_REPRESENTATION')

    def test_deformation_not_inferred_and_staging_change_rejects(self):
        b,o,c=self.fixture();c.pop('deformation')
        self.assertEqual(self.report(b,o,c)['deformation']['status'],'UNMEASURED')
        c['staged_weights'][0][0]['weight']=.25
        self.assertNotEqual(self.report(b,o,c)['unity_representation'],'EXACT')
