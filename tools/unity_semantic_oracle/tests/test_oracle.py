import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "Golden" / "SyntheticVariant.json"


class SemanticOracleGoldenTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_public_probe_schema_and_source_identity(self):
        self.assertEqual(self.data["schemaVersion"], "0.1")
        self.assertEqual(len(self.data["prefabs"]), 1)
        prefab = self.data["prefabs"][0]
        renderers = [obj for obj in prefab["objects"] if obj["type"].endswith("MeshRenderer")]
        self.assertEqual(len(renderers), 1)
        renderer = renderers[0]
        self.assertEqual(renderer["originalSourceAssetPath"], "Assets/SyntheticModel.fbx")
        self.assertTrue(renderer["originalSourceGuid"])
        self.assertTrue(renderer["originalSourceLocalFileID"])
        self.assertEqual(renderer["materials"][0]["name"], "SyntheticSurfaceB")
        self.assertTrue(renderer["materials"][0]["guid"])

    def test_property_modifications_are_resolved_by_prefab_api(self):
        modifications = self.data["prefabs"][0]["propertyModifications"]
        self.assertGreaterEqual(len(modifications), 1)
        self.assertTrue(all(item["resolutionStatus"] == "RESOLVED_BY_PREFAB_API" for item in modifications))
        self.assertTrue(any(item["propertyPath"] == "m_Name" for item in modifications))


if __name__ == "__main__":
    unittest.main()
