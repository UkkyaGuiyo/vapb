import math
import unittest

from contract import CASES, CORNER_UVS, TOLERANCE, VERTICES, validate_contract
from oracle import (CWORLD, authored_trs, expected_unity_world, local_matrix, maxima_for_case,
                    multiply, point, residuals, validate_u_tags, verdict)


def affine(translation=(0., 0., 0.)):
    return ((1., 0., 0., translation[0]), (0., 1., 0., translation[1]),
            (0., 0., 1., translation[2]), (0., 0., 0., 1.))


class HoldoutOracleTests(unittest.TestCase):
    def test_contract_has_four_frozen_cases_and_eighteen_distinct_tags(self):
        self.assertEqual(validate_contract(), [])
        self.assertEqual(tuple(c["id"] for c in CASES), ("H0", "H1", "H2", "H3"))
        self.assertEqual(len(set(CORNER_UVS)), 18)

    def test_candidate_passes_compound_noncommuting_world_and_local_equations(self):
        wb = multiply(affine((1.375, -2.125, .625)), ((0., -1., 0., 0.), (1., 0., 0., 0.), (0., 0., 1., 0.), (0., 0., 0., 1.)))
        d = local_matrix(.1)
        # The candidate prescribes Wu * D = C * Wb. This independently authored
        # synthetic frame exercises order and translation; it is not prior data.
        target = multiply(CWORLD, wb)
        wu = tuple(tuple(target[r][c] / (-.1, .1, .1, 1.)[c] for c in range(4)) for r in range(4))
        blender = {uv[0]: VERTICES[i] for i, uv in enumerate(CORNER_UVS)}
        unity = {uv[0]: point(d, VERTICES[i]) for i, uv in enumerate(CORNER_UVS)}
        maxima = maxima_for_case(blender, unity, wb, wu, .1)
        self.assertEqual(verdict(maxima), "PASS")
        self.assertLessEqual(max(maxima.values()), TOLERANCE)
        self.assertGreater(max(abs(multiply(wb, wu)[r][c] - multiply(wu, wb)[r][c])
                               for r in range(4) for c in range(4)), .1)

    def test_wrong_reflection_sign_fails_local_and_world(self):
        vb, wb, wu = VERTICES[0], affine(), CWORLD
        vu = (abs(vb[0]), vb[1], vb[2])
        result = residuals(vb, vu, wb, wu, 1.)
        maxima = {"local": max(map(abs, result["local"])),
                  "world_matrix": max(abs(x) for row in result["world_matrix"] for x in row),
                  "world_matrix_chain_point": max(map(abs, result["world_matrix_chain_point"])),
                  "world_point": max(map(abs, result["world_point"]))}
        self.assertEqual(verdict(maxima), "FAIL")

    def test_wrong_unit_ratio_fails(self):
        vb = VERTICES[0]; vu = point(local_matrix(.1), vb)
        result = residuals(vb, vu, affine(), CWORLD, 1.)
        self.assertGreater(max(map(abs, result["local"])), TOLERANCE)

    def test_chain_point_residual_is_diagnostic_and_not_a_fourth_acceptance_gate(self):
        maxima = {"local": 0.0, "world_matrix": 0.0, "world_matrix_chain_point": 1.0,
                  "world_point": 0.0}
        self.assertEqual(verdict(maxima), "PASS")
        maxima["world_matrix_chain_point"] = float("inf")
        with self.assertRaisesRegex(ValueError, "RESIDUAL_SET_OR_FINITE_INVALID"):
            verdict(maxima)

    def test_wrong_matrix_order_fails(self):
        wb = affine((2., -3., 4.)); d = local_matrix(.1)
        wu = multiply(CWORLD, wb)
        correct = multiply(wu, d); wrong = multiply(d, wu)
        self.assertGreater(max(abs(correct[r][c] - wrong[r][c]) for r in range(4) for c in range(4)), 1.)

    def test_authored_trs_and_candidate_world_are_built_without_blender(self):
        case = CASES[3]
        wb = authored_trs(case["location"], case["rotation_degrees"], case["scale"])
        wu = expected_unity_world(wb, .1)
        vb = VERTICES[4]
        vu = point(local_matrix(.1), vb)
        result = residuals(vb, vu, wb, wu, .1)
        self.assertLess(max(abs(x) for row in result["world_matrix"] for x in row), 1.e-12)
        self.assertLess(max(map(abs, result["world_point"])), 1.e-12)

    def test_known_xyz_trs_point_uses_scale_then_x_y_z_rotation_then_translation(self):
        matrix = authored_trs((1., 2., 3.), (0., 0., 90.), (2., 3., 4.))
        for actual, expected in zip(point(matrix, (1., 0., 0.)), (1., 4., 3.)):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_duplicate_missing_nonfinite_tags_and_matrices_reject(self):
        points = {uv[0]: VERTICES[i] for i, uv in enumerate(CORNER_UVS)}
        with self.assertRaisesRegex(ValueError, "CORNER_TAG_DUPLICATE"):
            validate_u_tags(list(points) + [CORNER_UVS[0][0]])
        del points[CORNER_UVS[-1][0]]
        with self.assertRaisesRegex(ValueError, "CORNER_TAG_SET_MISMATCH"):
            maxima_for_case(points, points, affine(), CWORLD, 1.)
        with self.assertRaisesRegex(ValueError, "MATRIX_NONFINITE"):
            local_bad = ((math.nan, 0, 0, 0), (0,1,0,0), (0,0,1,0), (0,0,0,1))
            residuals(VERTICES[0], VERTICES[0], local_bad, CWORLD, 1.)
        with self.assertRaisesRegex(ValueError, "UNIT_RATIO_INVALID"):
            local_matrix(math.nan)
        with self.assertRaisesRegex(ValueError, "CORNER_TAG_NONFINITE"):
            validate_u_tags(list(points) + [math.nan])
        with self.assertRaisesRegex(ValueError, "RESIDUAL_NEGATIVE"):
            verdict({"local": -1., "world_matrix": 0., "world_matrix_chain_point": 0., "world_point": 0.})


if __name__ == "__main__": unittest.main()
