import unittest

from tools.shader_semantic_oracle.behavior_ir import classify_material_schema


class BehaviorIrTests(unittest.TestCase):
    def test_roles_are_property_name_driven_and_explicit(self):
        result = classify_material_schema({
            "property_names": {
                "Texture": ["_MainTex", "_BumpMap", "_EmissionMap"],
                "Color": ["_Color"],
                "Float": ["_Cutoff", "_Glossiness"],
                "Vector": [],
                "Int": [],
            },
            "shader_guid": "public-guid",
        })
        self.assertEqual(result["base_surface"]["state"], "DETECTED")
        self.assertEqual(result["normal"]["state"], "DETECTED")
        self.assertEqual(result["emission"]["state"], "DETECTED")
        self.assertEqual(result["alpha"]["state"], "DETECTED")
        self.assertEqual(result["unsupported_features"], [])

    def test_unobserved_features_are_not_claimed(self):
        result = classify_material_schema({"property_names": {"Texture": [], "Color": [], "Float": [], "Vector": [], "Int": []}})
        self.assertEqual(result["normal"]["state"], "NOT_OBSERVED")
        self.assertEqual(result["time_behavior"]["state"], "NOT_TESTED")


if __name__ == "__main__":
    unittest.main()
