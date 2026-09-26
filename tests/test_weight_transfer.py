import unittest

from unitypackage_blender_importer.blender.weight_transfer import closest_triangle_weights, combine_weight, crosses_declared_plane


class WeightTransferPolicyTest(unittest.TestCase):
    def test_declared_plane_signs(self):
        self.assertTrue(crosses_declared_plane(-0.02, 0.03))
        self.assertFalse(crosses_declared_plane(0.02, 0.03))
        self.assertFalse(crosses_declared_plane(0.000001, -0.03))

    def test_barycentric_inside_and_outside(self):
        tri = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
        self.assertEqual(closest_triangle_weights((0.5, 0.5, 1), *tri), (0.5, 0.25, 0.25))
        self.assertEqual(closest_triangle_weights((3, 0, 0), *tri), (0.0, 1.0, 0.0))

    def test_duplicate_triangle_vertices(self):
        weights = closest_triangle_weights((0.5, 0.5, 0), (0, 0, 0), (0, 0, 0), (1, 0, 0))
        self.assertAlmostEqual(sum(weights), 1.0)
        self.assertTrue(all(0 <= value <= 1 for value in weights))

    def test_modes_and_blend(self):
        self.assertAlmostEqual(combine_weight(0.8, 0.2, 'REPLACE', 1), 0.2)
        self.assertEqual(combine_weight(0.8, 0.2, 'MERGE', 1), 0.8)
        self.assertEqual(combine_weight(0.0, 0.2, 'FILL_MISSING', 1), 0.2)
        self.assertEqual(combine_weight(0.8, 0.2, 'FILL_MISSING', 1), 0.8)
        self.assertAlmostEqual(combine_weight(0.8, 0.2, 'REPLACE', 0.5), 0.5)


if __name__ == '__main__':
    unittest.main()
