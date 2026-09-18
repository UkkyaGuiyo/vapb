import unittest

from tools.shader_semantic_oracle.behavior_fingerprint import (
    aggregate_prevalence,
    fingerprint_from_metadata,
    schema_signature,
    select_representatives,
)


def material(*textures, colors=(), floats=()):
    return {"material_id": "M-" + str(len(textures)) + str(len(colors)), "property_names": {"Texture": list(textures), "Color": list(colors), "Float": list(floats), "Vector": [], "Int": []}, "texture_references": ["synthetic"] * len(textures)}


class BehaviorFingerprintTests(unittest.TestCase):
    def test_behav_001_schema_signature_is_deterministic(self):
        left = material("_BumpMap", "_MainTex", colors=("_Color",))
        right = material("_MainTex", "_BumpMap", colors=("_Color",))
        self.assertEqual(schema_signature(left), schema_signature(right))

    def test_behav_002_selection_preserves_schema_and_behavior_coverage(self):
        records = [material("_MainTex", colors=("_Color",)), material("_BumpMap"), material("_EmissionMap"), material("_RimColor", colors=("_Color",))]
        selected = select_representatives(records, 3)
        covered = set()
        for item in selected:
            covered.update(key for key, value in fingerprint_from_metadata(item).items() if value["state"] == "DETECTED")
        self.assertGreaterEqual(len(selected), 3)
        self.assertIn("normal", covered)
        self.assertIn("emission", covered)

    def test_behav_003_to_014_generic_fixture_roles(self):
        record = material("_MainTex", "_BumpMap", "_EmissionMap", colors=("_Color",), floats=("_Cutoff", "_RimPower", "_OutlineWidth"))
        fp = fingerprint_from_metadata(record)
        for key in ("base_texture", "base_color", "normal", "emission", "alpha", "rim_fresnel", "outline"):
            self.assertEqual(fp[key]["state"], "DETECTED")
        for key in ("time_animation", "billboard", "vertex_deform"):
            self.assertEqual(fp[key]["state"], "NOT_TESTED")

    def test_behav_015_and_016_state_and_provenance_are_distinct(self):
        fp = fingerprint_from_metadata(material())
        self.assertNotEqual(fp["base_texture"]["state"], fp["time_animation"]["state"])
        self.assertEqual(fp["base_texture"]["evidence"], [])
        self.assertEqual(fp["time_animation"]["evidence"], [])

    def test_behav_017_and_018_do_not_use_shader_name_or_claim_missing_features(self):
        fp = fingerprint_from_metadata({"shader_name": "PretendToon", "property_names": {"Texture": [], "Color": [], "Float": [], "Vector": [], "Int": []}})
        self.assertEqual(fp["toon_lighting"]["state"], "NOT_OBSERVED")
        self.assertEqual(fp["view_dependent"]["state"], "NOT_TESTED")

    def test_prevalence_is_deterministic(self):
        result = aggregate_prevalence([fingerprint_from_metadata(material("_MainTex")), fingerprint_from_metadata(material())])
        self.assertEqual(result["base_texture"]["DETECTED"], 1)


if __name__ == "__main__":
    unittest.main()
