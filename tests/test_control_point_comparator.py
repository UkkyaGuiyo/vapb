import copy
import unittest
from unitypackage_blender_importer.tests.control_point_comparator import compare_points


class ControlPointComparatorTests(unittest.TestCase):
    def inputs(self):
        revision = dict(source_fbx_sha256='a'*64, source_meta_sha256='b'*64,
                        noop_fbx_sha256='c'*64, stamped_fbx_sha256='d'*64)
        mesh = dict(mesh_guid='1'*32, mesh_local_id='-4', geometry_uid='19', control_point_count=4)
        manifest = dict(revision, meshes=[mesh])
        unity = dict(revision, error='NONE', **{k: True for k in ('pass', 'noop_equivalent',
            'stamped_equivalent', 'restored_equivalent', 'source_fbx_restored', 'source_meta_restored')})
        unity['stamped'] = [dict(mesh, marker_valid=True, negative_duplicate_rejected=True,
            negative_out_of_range_rejected=True, triangle_control_point_indices=[0,1,2,0,2,3])]
        native = dict(revision, status='PASS', original_noop_stamped_restored_equal=True,
            meshes=[dict(geometry_uid='19', triangle_control_points=[[3,2,0],[2,1,0]], polygon_control_points=[[0,1,2,3]])])
        return unity, native, manifest

    def test_reorder_passes_changed_diagonal_fails(self):
        args = self.inputs()
        self.assertEqual(compare_points(*args)['status'], 'GREEN')
        args[1]['meshes'][0]['triangle_control_points'] = [[0,1,3],[1,2,3]]
        result = compare_points(*args)
        self.assertEqual(result['status'], 'RED')
        self.assertEqual(result['meshes'][0]['affected_polygon_indices'], [0])

    def test_stale_revision_or_missing_mesh_rejects(self):
        for kind in ('revision', 'coverage', 'range'):
            args = copy.deepcopy(self.inputs())
            if kind == 'revision': args[0]['source_fbx_sha256'] = '0'*64
            elif kind == 'coverage': args[1]['meshes'] = []
            else: args[0]['stamped'][0]['triangle_control_point_indices'][0] = 5
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                compare_points(*args)

    def test_invalid_mesh_is_retained_as_red_without_overriding_probe(self):
        unity, native, manifest = self.inputs()
        unity['pass'] = False
        unity['stamped'][0]['marker_valid'] = False
        result = compare_points(unity, native, manifest)
        self.assertEqual(result['status'], 'RED')
        self.assertEqual(result['counts'], {'CONTROL_POINT_IDENTITY_UNPROVEN': 1})
        self.assertFalse(unity['pass'])

    def test_failed_negative_control_cannot_pass(self):
        unity, native, manifest = self.inputs()
        unity['pass'] = False
        unity['stamped'][0]['negative_duplicate_rejected'] = False
        result = compare_points(unity, native, manifest)
        self.assertEqual(result['status'], 'RED')
        self.assertEqual(result['counts'], {'CONTROL_POINT_IDENTITY_UNPROVEN': 1})

    def test_observed_map_does_not_claim_full_raw_point_bijection(self):
        unity, native, manifest = self.inputs()
        unity['pass'] = False
        row = unity['stamped'][0]
        row.update(marker_valid=False, negative_duplicate_rejected=False,
            observed_vertex_map_valid=True, negative_observed_set_removal_rejected=True,
            raw_source_cp_complete=False, missing_control_point_indices=[3])
        # A loose point can be absent without changing the observed triangles.
        row['triangle_control_point_indices'] = [0,1,2]
        native['meshes'][0]['triangle_control_points'] = [[2,1,0]]
        result = compare_points(unity, native, manifest)
        self.assertEqual(result['status'], 'GREEN')
        self.assertFalse(result['strict_source_cp_control_pass'])
        self.assertFalse(result['meshes'][0]['raw_source_cp_complete'])
        self.assertEqual(result['meshes'][0]['omitted_raw_control_points'], 1)
        row['negative_observed_set_removal_rejected'] = False
        self.assertEqual(compare_points(unity, native, manifest)['status'], 'RED')
