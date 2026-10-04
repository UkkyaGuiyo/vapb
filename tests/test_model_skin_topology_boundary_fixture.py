import unittest

from tests.model_skin_topology_boundary_fixture import (
    make_vertex_split_contract,
    validate_vertex_split_contract,
)


class ModelSkinTopologyBoundaryFixtureTests(unittest.TestCase):
    def test_vertex_split_keeps_two_faces_and_copies_weights(self):
        fixture = make_vertex_split_contract()
        self.assertTrue(validate_vertex_split_contract(fixture))
        self.assertEqual(fixture["source_vertices"], fixture["final_vertices"][:4])
        self.assertEqual(fixture["source_faces"], ((0, 1, 2), (0, 2, 3)))
        self.assertEqual(fixture["final_faces"], ((0, 1, 2), (4, 5, 3)))
        self.assertEqual(len(fixture["source_vertices"]), 4)
        self.assertEqual(len(fixture["final_vertices"]), 6)
        self.assertEqual(sum(map(len, fixture["source_faces"])), 6)
        self.assertEqual(sum(map(len, fixture["final_faces"])), 6)
        self.assertEqual(fixture["final_bone_weights"][4], (("Root", 1.0),))
        self.assertEqual(fixture["final_bone_weights"][5], (("Child", 1.0),))
        self.assertNotEqual(fixture["source_face_uvs"][1], fixture["final_face_uvs"][1])

    def test_rejects_wrong_source_face_or_weight_contract(self):
        with self.assertRaisesRegex(ValueError, "FIXTURE_SHARED_EDGE_UNEXPECTED"):
            make_vertex_split_contract(faces=((0, 1, 2), (1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "FIXTURE_BONE_WEIGHTS_CHANGED"):
            fixture = make_vertex_split_contract()
            fixture["final_bone_weights"] = fixture["final_bone_weights"][:-1] + ((("Root", 1.0),),)
            validate_vertex_split_contract(fixture)


if __name__ == "__main__":
    unittest.main()
