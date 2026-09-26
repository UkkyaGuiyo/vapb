import unittest

from unitypackage_blender_importer.blender.bone_merge import (
    candidate_mappings, confirmed_remap,
)


class Bone(dict):
    def __init__(self, name, identity=None):
        super().__init__()
        self.name = name
        if identity:
            self.update(zip(("_vapb_fbx_source_asset_guid", "_vapb_fbx_source_asset_sha256",
                             "_vapb_fbx_model_uid"), identity))


class Choice:
    def __init__(self, source_name, classification, target_name="", confirmed=False):
        self.source_name = source_name
        self.classification = classification
        self.target_name = target_name
        self.confirmed = confirmed


class BoneMergePolicyTests(unittest.TestCase):
    def test_provenance_is_candidate_only(self):
        identity = ("a" * 32, "b" * 64, "-10")
        rows = candidate_mappings([Bone("A", identity)], [Bone("B", identity)])
        self.assertEqual(rows, [("B", "A", "EQUIVALENT")])
        with self.assertRaisesRegex(ValueError, "確認"):
            confirmed_remap(["A"], ["B"], [Choice("B", "EQUIVALENT", "A")])

    def test_name_alone_never_suggests_equivalence(self):
        self.assertEqual(candidate_mappings([Bone("Same")], [Bone("Same")]),
                         [("Same", "", "AMBIGUOUS")])

    def test_ambiguous_collision_and_many_to_one_stop(self):
        with self.assertRaises(ValueError):
            confirmed_remap(["A"], ["B"], [Choice("B", "AMBIGUOUS", confirmed=True)])
        with self.assertRaises(ValueError):
            confirmed_remap(["Twin"], ["Twin"], [Choice("Twin", "B_ONLY", confirmed=True)])
        with self.assertRaises(ValueError):
            confirmed_remap(["A"], ["X", "Y"], [Choice("X", "EQUIVALENT", "A", True),
                                                  Choice("Y", "EQUIVALENT", "A", True)])

    def test_confirmed_equivalent_and_unique_b_only(self):
        self.assertEqual(confirmed_remap(["A"], ["B", "Extra"],
                         [Choice("B", "EQUIVALENT", "A", True),
                          Choice("Extra", "B_ONLY", confirmed=True)]),
                         {"B": "A", "Extra": "Extra"})


if __name__ == "__main__":
    unittest.main()
