"""V2 final-state task serialization contract."""

import unittest
import json

from unitypackage_blender_importer.export.final_state_package import (
    _build_final_state_task, _validate_final_state_material_table,
)
from unitypackage_blender_importer.export.manifest import ExportManifest, GeneratorInfo, SCHEMA_VERSION


class FinalStateV2PayloadTests(unittest.TestCase):
    def test_task_declares_v2_transport_and_preserves_repeated_slot_labels(self):
        materials = [
            {"export_material_id": "VAPB-MAT-" + "a" * 32},
            {"export_material_id": "VAPB-MAT-" + "b" * 32},
        ]
        slots = ["VAPB-MAT-" + value * 32 for value in "aba"]
        task = _build_final_state_task(
            "VAPB-OBJ-" + "c" * 32, "d" * 32, "e" * 64,
            "Assets/VAPBExport/Generated_" + "c" * 32 + ".prefab",
            materials, slots)
        manifest = ExportManifest(
            schema_version=SCHEMA_VERSION, generator=GeneratorInfo("test", "test"),
            source_packages=(), source_assets=(), export_assets=(), export_roots=(),
            renderer_mappings=(), mesh_mappings=(), material_mappings=(), texture_mappings=(),
            bone_mappings=(), shape_key_mappings=(), prefab_source_chains=(),
            component_provenance=(), reachability=(), reference_rebind_tasks=(task,),
            unity_postimport_identity_map=(), external_dependencies=(),
            unsupported_preserved_state=(), warnings=(), errors=())
        task = json.loads(manifest.to_json())["reference_rebind_tasks"][0]

        self.assertEqual("BUILD_EXPORTED_STATIC_V2", task["kind"])
        self.assertEqual(2, task["material_transport_version"])
        self.assertEqual(["VAPB-MAT-" + value * 32 for value in "aba"],
                         [slot["export_material_id"] for slot in task["material_slots"]])
        self.assertEqual(["0", "1", "2"], [slot["slot_index"] for slot in task["material_slots"]])
        self.assertEqual(materials, task["materials"])

    def test_material_table_rejects_duplicate_export_ids(self):
        duplicate = {"export_material_id": "VAPB-MAT-" + "a" * 32}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _validate_final_state_material_table([duplicate, dict(duplicate)], [duplicate["export_material_id"]])

    def test_material_table_rejects_unknown_slot_label(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            _validate_final_state_material_table(
                [{"export_material_id": "VAPB-MAT-" + "a" * 32}],
                ["VAPB-MAT-" + "b" * 32])

    def test_material_table_rejects_unused_declaration(self):
        records = [{"export_material_id": "VAPB-MAT-" + value * 32} for value in "ab"]
        with self.assertRaisesRegex(ValueError, "unused"):
            _validate_final_state_material_table(records, ["VAPB-MAT-" + "a" * 32])

if __name__ == "__main__":
    unittest.main(verbosity=2)
