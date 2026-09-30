import unittest
from unitypackage_blender_importer.tests.blender_geometry_point_controls import decode_marker


class ControlPointMarkersTests(unittest.TestCase):
    def test_exact_marker_accepts_only_declared_indices(self):
        self.assertEqual(decode_marker(1.0, .375, 3), 0)
        self.assertEqual(decode_marker(3.0, .375, 3), 2)

    def test_marker_corruption_rejects(self):
        for x, y in ((0, .375), (4, .375), (1.25, .375), (1, 0),
                     (float('nan'), .375), (1, float('inf'))):
            with self.subTest(x=x, y=y), self.assertRaisesRegex(ValueError, 'CONTROL_POINT_MARKER_INVALID'):
                decode_marker(x, y, 3)
