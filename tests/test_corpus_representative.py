# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import unittest
from types import SimpleNamespace
from . import blender_corpus_representative as adapter


class RepresentativeSelectionTests(unittest.TestCase):
    def test_model_unassigned_slot_is_a_product_scope_refusal_not_rollback_failure(self):
        mesh = SimpleNamespace(material_slots=[SimpleNamespace(material=object()), SimpleNamespace(material=None)])
        with self.assertRaisesRegex(ValueError, 'MODEL_UNASSIGNED_MATERIAL_SCOPE_UNSUPPORTED') as caught:
            adapter.check_model_material_scope(mesh)
        report = adapter.capture_failure(caught.exception)
        self.assertEqual((report['verdict'], report['reason']), ('UNSUPPORTED', 'UNSUPPORTED_STRUCTURE'))
        self.assertIsNone(mesh.material_slots[1].material)

    def test_bound_material_slots_pass_and_other_failure_classes_stay_separate(self):
        mesh = SimpleNamespace(material_slots=[SimpleNamespace(material=object())])
        adapter.check_model_material_scope(mesh)
        self.assertEqual(adapter.capture_failure(ValueError('SHAPE_CAPTURE_SCOPE_UNSUPPORTED'))['reason'], 'HARNESS_UNSUPPORTED')
        report = adapter.capture_failure(ValueError('FAILURE_ROLLBACK_UNPROVEN'))
        self.assertEqual((report['verdict'], report['reason']), ('UNPROVEN', 'HARNESS_ERROR'))
        self.assertEqual(adapter.capture_failure(RuntimeError('private path or value'))['detail_code'], 'CAPTURE_EXCEPTION')

    def setUp(self):
        self.selection = dict(root_guid='a'*32, renderer_guid='a'*32,
                              renderer_file_id='11', mesh_guid='b'*32, mesh_file_id='22')
        self.record = dict(renderer_class_id=137, root_asset_guid='a'*32,
            source_key=dict(source_kind='PREFAB_LOCAL', source_asset_guid='a'*32, renderer_file_id='11'),
            mesh=dict(mesh_guid='b'*32, mesh_file_id='22'), instance_edge_path=[], occurrence_id='exact-occurrence')

    def test_selection_uses_all_exact_subject_fields(self):
        unrelated = copy.deepcopy(self.record)
        unrelated['source_key']['renderer_file_id'] = '99'
        self.assertEqual(adapter.select_record([unrelated, self.record], self.selection), self.record)
        for key in self.selection:
            changed = dict(self.selection, **{key: 'wrong'})
            with self.assertRaisesRegex(ValueError, 'SELECTED_OCCURRENCE_NOT_UNIQUE'):
                adapter.select_record([self.record], changed)

    def test_ambiguous_and_nested_subjects_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SELECTED_OCCURRENCE_NOT_UNIQUE'):
            adapter.select_record([self.record, self.record], self.selection)
        self.record['instance_edge_path'] = [{'exact': 'nested'}]
        with self.assertRaisesRegex(ValueError, 'NESTED_CAPTURE_SCOPE_UNSUPPORTED'):
            adapter.select_record([self.record], self.selection)

    def test_prior_skin_is_selected_by_occurrence_not_array_order(self):
        prior = dict(occurrence_id='exact-occurrence', renderer_owner_valid=True, root_frame_binding_valid=True,
                     bones=[dict(carrier_constraint_valid=True, bone_parent_valid=True)])
        observed = dict(status='OBSERVED_NOT_COMPARED', source_validated=True, source_control_report_pass=True,
                        skins=[dict(prior, occurrence_id='other'), prior])
        self.assertEqual(adapter.select_proof(observed, 'exact-occurrence'), prior)
        prior['bones'][0]['carrier_constraint_valid'] = False
        with self.assertRaisesRegex(ValueError, 'PRIOR_SKIN_RELATION_UNPROVEN'):
            adapter.select_proof(observed, 'exact-occurrence')

    def test_transport_markers_join_to_editing_world_geometry_by_exact_clone_data(self):
        source = dict(positions=[[1., 2., 3.]], triangles=[[0,0,0]], polygons=[[0,0,0]],
                      skin_weights=[[dict(group='native', weight=1.)]], uv_channels=[], corner_normals=[[0,0,1]])
        staged = copy.deepcopy(source)
        staged.update(positions=[[1.00000001, 2., 3.]], marker_channel=0,
            vertex_control_point_indices=[0], triangle_control_points=[[0,0,0]],
            uv_channels=[dict(channel=0, corners=[[1.,.375]]*3)])
        local = dict(vertices=[[0.,0.,0.]], loops=[0,0,0])
        before = copy.deepcopy(source)
        joined = adapter.checkpoint_with_transport(source, staged, local, local)
        self.assertEqual(joined['positions'], source['positions'])
        self.assertNotEqual(joined['positions'], staged['positions'])
        self.assertEqual(joined['uv_channels'], staged['uv_channels'])
        self.assertEqual(source, before)
        with self.assertRaisesRegex(ValueError, 'EXPORT_LOCAL_DATA_CHANGED'):
            adapter.checkpoint_with_transport(source, staged, local, dict(vertices=[[.1,0,0]],loops=[0,0,0]))
        staged['vertex_control_point_indices'] = [None]
        with self.assertRaisesRegex(ValueError, 'CP_UNREFERENCED_VERTEX'):
            adapter.checkpoint_with_transport(source, staged, local, local)

    def test_e1_copy_preserves_other_user_of_working_mesh_data(self):
        class Data(dict):
            users = 2
            session_uid = 7
            vertices = [SimpleNamespace(co=SimpleNamespace(x=1.))]

            def copy(self):
                result = copy.deepcopy(self)
                result.vertices = copy.deepcopy(self.vertices)
                result.session_uid = 8
                return result

            def update(self):
                pass

        shared = Data(source_receipt='preserved')
        selected, other = SimpleNamespace(data=shared), SimpleNamespace(data=shared)
        facts = adapter.edit_native_mesh(selected)
        self.assertIsNot(selected.data, other.data)
        self.assertEqual(other.data.vertices[0].co.x, 1.)
        self.assertEqual(selected.data.vertices[0].co.x, 1.002)
        self.assertEqual(selected.data['source_receipt'], 'preserved')
        self.assertTrue(facts['working_mesh_made_single_user'])


if __name__ == '__main__':
    unittest.main()
