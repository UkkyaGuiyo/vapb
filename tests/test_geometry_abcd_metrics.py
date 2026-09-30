# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unitypackage_blender_importer.tests.geometry_abcd_metrics import position_metric, triangle_multiset,oriented_triangles
from unitypackage_blender_importer.tests.blender_geometry_abcd_compare import d_identity_metrics


class AbcdMetricsTests(unittest.TestCase):
    def test_explicit_labels_survive_vertex_reorder(self):
        self.assertEqual(position_metric([0,1],[[0,0,0],[1,0,0]],
                                        [1,0],[[1,0,0],[0,0,0]])['status'],'EXACT')

    def test_equal_count_and_coordinates_do_not_repair_wrong_labels(self):
        self.assertEqual(position_metric([0,1],[[0,0,0],[1,0,0]],
                                        [1,0],[[0,0,0],[1,0,0]])['status'],'POSITION_MISMATCH')

    def test_split_vertex_disagreement_is_not_hidden(self):
        self.assertEqual(position_metric([0],[[0,0,0]],[0,0],[[0,0,0],[0,0,.01]])['status'],
                         'POSITION_MISMATCH')

    def test_diagonal_difference_is_retained(self):
        self.assertNotEqual(triangle_multiset([[0,1,2],[0,2,3]]),triangle_multiset([[0,1,3],[1,2,3]]))

    def test_missing_label_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'IDENTITY_UNPROVEN'):
            position_metric([None],[[0,0,0]],[0],[[0,0,0]])

    def test_reflected_basis_requires_one_winding_reversal(self):
        self.assertEqual(oriented_triangles([[0,1,2]]),oriented_triangles([[0,2,1]],True))
        self.assertNotEqual(oriented_triangles([[0,1,2]]),oriented_triangles([[0,2,1]]))

    def export_controls(self):
        before=dict(vertex_control_point_indices=[0],shapes=[dict(export_label='VAPB-EXP-SHAPE-1',deltas=[[1,2,3]])],
                    skin_weights=[[dict(group='VAPB-EXP-BONE-1',weight=1.)]])
        actual=dict(vertex_control_point_indices=[0],renderer_local_to_world=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
                    shape_frames=[dict(name='VAPB-EXP-SHAPE-1',frame=0,weight=100,
                                       delta_positions=[dict(x=-1,y=3,z=-2)])],
                    bones=[dict(index=0,export_label='VAPB-EXP-BONE-1')],
                    bone_weights=[dict(vertex=0,bone=0,weight=1.)])
        return before,actual

    def test_explicit_transport_label_and_delta_control(self):
        before,actual=self.export_controls()
        result=d_identity_metrics(before,actual)
        self.assertEqual(result['shape_geometry']['status'],'EXACT')
        self.assertEqual(result['skin_bone_weight_binding'],'EXACT')

    def test_shape_label_same_count_does_not_repair_identity(self):
        before,actual=self.export_controls();actual['shape_frames'][0]['name']='Decoy'
        self.assertEqual(d_identity_metrics(before,actual)['shape_geometry']['status'],'SHAPE_EXPORT_LABEL_MISMATCH')

    def test_wrong_bone_binding_with_equal_weight_is_rejected(self):
        before,actual=self.export_controls();actual['bones'][0]['export_label']='VAPB-EXP-BONE-2'
        self.assertEqual(d_identity_metrics(before,actual)['skin_bone_weight_binding'],'SKIN_BINDING_MISMATCH')

    def test_wrong_delta_keeps_red(self):
        before,actual=self.export_controls();actual['shape_frames'][0]['delta_positions'][0]['x']=0
        self.assertEqual(d_identity_metrics(before,actual)['shape_geometry']['status'],'SHAPE_DELTA_MISMATCH')
