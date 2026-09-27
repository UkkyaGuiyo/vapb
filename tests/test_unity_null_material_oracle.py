"""Unity-authored explicit-null Material override remains a known null slot."""

import hashlib
import json
from pathlib import Path
import unittest

from unitypackage_blender_importer.unity.occurrence_projection import PrefabSource, project_occurrences
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab


ASSETS = Path(__file__).with_name("unity_alias_oracle") / "Assets" / "Oracle"
EXPECTED = ASSETS.parents[1] / "null_expected.json"


def source(filename):
    path = ASSETS / filename
    prefab = parse_prefab(path)
    return PrefabSource(prefab, "synthetic", filename,
                        hashlib.sha256(path.read_bytes()).hexdigest(), prefab.asset_guid)


class UnityNullMaterialOracleTests(unittest.TestCase):
    def test_unity_authored_null_is_known_not_unresolved(self):
        observed = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual("2022.3.22f1", observed["unityVersion"])
        self.assertEqual(1, observed["sourceSlots"])
        self.assertTrue(observed["sourceHasMaterial"])
        self.assertEqual(1, observed["variantSlots"])
        self.assertTrue(observed["variantIsNull"])
        self.assertEqual(1, observed["nullModifications"])
        base = source("Null_Source.prefab")
        variant = source("Null_Override.prefab")
        modifications = [item for item in variant.prefab.modifications()
                         if item.property_path == "m_Materials.Array.data[0]"]
        self.assertEqual(1, len(modifications))
        self.assertEqual({"fileID": 0}, modifications[0].object_reference)
        projection = project_occurrences(
            variant, "synthetic", lambda _package, guid: base if guid == base.asset_guid else None)
        self.assertEqual([], projection.issues)
        self.assertEqual(1, len(projection.records))
        self.assertEqual(1, projection.records[0]["material_slot_count"])
        self.assertEqual({0: None}, projection.records[0]["materials"])
        self.assertEqual("EXACT", projection.records[0]["material_status"])


if __name__ == "__main__":
    unittest.main()
