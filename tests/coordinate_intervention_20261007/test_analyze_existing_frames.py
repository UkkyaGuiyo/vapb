import unittest

from analyze_existing_frames import (
    CWORLD,
    _matrix_max,
    frame_residuals,
    local_conversion,
    multiply,
    transform_point,
)


def _affine(rows, translation):
    return (
        (rows[0][0], rows[0][1], rows[0][2], translation[0]),
        (rows[1][0], rows[1][1], rows[1][2], translation[1]),
        (rows[2][0], rows[2][1], rows[2][2], translation[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


class ExistingFrameAnalysisTests(unittest.TestCase):
    def test_affine_parent_child_composition_preserves_noncommuting_translation(self):
        parent = _affine(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), (5.0, -2.0, 3.0))
        child = _affine(((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.5)), (1.0, 4.0, -1.0))
        point = (0.25, -2.0, 3.0)
        composed = transform_point(multiply(parent, child), point)
        sequential = transform_point(parent, transform_point(child, point))
        reversed_order = transform_point(multiply(child, parent), point)
        for actual, expected in zip(composed, sequential):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertGreater(max(abs(a - b) for a, b in zip(composed, reversed_order)), 1.0)

    def test_unit_scale_is_applied_in_local_vertices_when_blender_world_has_point_one_scale(self):
        blender_world = _affine(((0.01, 0.0, 0.0), (0.0, 0.01, 0.0), (0.0, 0.0, 0.01)), (0, 0, 0))
        unity_world = _affine(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)), (0, 0, 0))
        blender_vertex = (1.0, 2.0, 3.0)
        unity_vertex = transform_point(local_conversion(0.01), blender_vertex)
        residual = frame_residuals(blender_vertex, unity_vertex, blender_world, unity_world, 0.01)
        self.assertAlmostEqual(max(abs(v) for v in unity_vertex), 0.03, places=12)
        self.assertLess(residual["matrix_max_abs_wu_dc_minus_cwb"], 1e-12)
        for equation in ("local_vu_minus_dc_vb", "world_wu_dc_vb_minus_cwb_vb", "world_pu_minus_cpb"):
            self.assertLess(max(abs(v) for v in residual[equation]), 1e-12)

    def test_constant_local_scale_control_fails_unit_case(self):
        blender_world = _affine(((0.01, 0.0, 0.0), (0.0, 0.01, 0.0), (0.0, 0.0, 0.01)), (0, 0, 0))
        blender_vertex = (1.0, 2.0, 3.0)
        unity_vertex = transform_point(local_conversion(0.01), blender_vertex)
        wrong = frame_residuals(blender_vertex, unity_vertex, blender_world, CWORLD, 1.0)
        self.assertGreater(max(abs(v) for v in wrong["local_vu_minus_dc_vb"]), 0.9)
        self.assertGreater(wrong["matrix_max_abs_wu_dc_minus_cwb"], 0.9)

    def test_same_frame_left_multiplication_control_fails_with_translation(self):
        d = local_conversion(0.01)
        blender_world = _affine(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), (2.0, -3.0, 4.0))
        target = multiply(CWORLD, blender_world)
        diagonal = (-0.01, 0.01, 0.01, 1.0)
        unity_world = tuple(tuple(target[row][column] / diagonal[column] for column in range(4))
                            for row in range(4))
        self.assertLess(_matrix_max(multiply(unity_world, d), target), 1e-12)
        self.assertGreater(_matrix_max(multiply(d, unity_world), target), 1.0)

    def test_missing_corner_payload_fails_closed(self):
        from analyze_existing_frames import _corner_map

        blender_case = {
            "case_id": "synthetic",
            "hierarchy": [{"type": "MESH", "matrix_world": CWORLD}],
            "triangles": [{"uvs": [[0.0, 0.0], [1.0, 0.0]],
                           "vertices_local": [[0, 0, 0], [1, 0, 0], [0, 1, 0]]}],
        }
        with self.assertRaisesRegex(ValueError, "BLENDER_CORNER_INPUT_INVALID"):
            _corner_map(blender_case, "blender")

        unity_case = {"case_id": "synthetic", "renderers": [{"transform_path": "mesh", "vertices_local": []}],
                      "hierarchy": [{"path": "mesh", "world_matrix": CWORLD}], "renderers": [
                          {"transform_path": "mesh", "vertices_local": [], "submeshes": []}]}
        with self.assertRaisesRegex(ValueError, "UNITY_CORNER_INPUT_MISSING"):
            _corner_map(unity_case, "unity")


if __name__ == "__main__":
    unittest.main()
