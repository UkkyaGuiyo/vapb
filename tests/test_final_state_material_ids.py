"""Focused final-state material slot identity and preflight tests."""

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest.mock import patch

from unitypackage_blender_importer.export import final_state_package


class FakeMaterial(dict):
    def __init__(self, pointer, name, **properties):
        super().__init__(properties)
        self.pointer = pointer
        self.name = name

    def as_pointer(self):
        return self.pointer


def slot(material):
    return SimpleNamespace(material=material)


def polygon(material_index):
    return SimpleNamespace(material_index=material_index)


class FinalStateMaterialIdTests(unittest.TestCase):
    def test_repeated_slots_share_one_id_and_distinct_materials_get_unique_ids(self):
        first = FakeMaterial(1, "First", unity_source_package_id="package-a")
        second = FakeMaterial(2, "Second", unity_source_package_id="package-a")
        materials = [first, second]

        with patch.object(final_state_package, "uuid4",
                          side_effect=[SimpleNamespace(hex="a" * 32),
                                       SimpleNamespace(hex="b" * 32)]):
            ids_by_pointer, slot_ids = final_state_package._material_slot_export_ids(
                [slot(first), slot(first), slot(second)], materials)

        first_id = "VAPB-MAT-" + "a" * 32
        second_id = "VAPB-MAT-" + "b" * 32
        self.assertEqual([first_id, first_id, second_id], slot_ids)
        self.assertEqual({1: first_id, 2: second_id}, ids_by_pointer)
        self.assertEqual(2, len(set(slot_ids)))

    def test_generated_id_collision_between_distinct_materials_is_rejected(self):
        first = FakeMaterial(1, "First")
        second = FakeMaterial(2, "Second")
        materials = [first, second]
        collision = SimpleNamespace(hex="c" * 32)
        before = [(dict(material), material.name) for material in materials]

        with patch.object(final_state_package, "uuid4", side_effect=[collision, collision]):
            with self.assertRaisesRegex(ValueError, "duplicate.*Export Material ID"):
                final_state_package._material_slot_export_ids(
                    [slot(first), slot(second)], materials)

        self.assertEqual(before, [(dict(material), material.name) for material in materials])

    def test_generated_id_collision_with_later_existing_id_is_rejected_without_mutation(self):
        collision = "VAPB-MAT-" + "c" * 32
        generated = FakeMaterial(1, "Generated", custom="generated-stays-unchanged")
        existing = FakeMaterial(2, "Existing", _vapb_export_material_id=collision,
                                custom="existing-stays-unchanged")
        materials = [generated, existing]
        before = [(dict(material), material.name) for material in materials]

        with patch.object(final_state_package, "uuid4",
                          return_value=SimpleNamespace(hex="c" * 32)):
            with self.assertRaisesRegex(ValueError, "duplicate.*Export Material ID"):
                final_state_package._material_slot_export_ids(
                    [slot(generated), slot(existing)], materials)

        self.assertEqual(before, [(dict(material), material.name) for material in materials])

    def test_generated_id_collision_with_earlier_existing_id_is_rejected_without_mutation(self):
        collision = "VAPB-MAT-" + "c" * 32
        existing = FakeMaterial(1, "Existing", _vapb_export_material_id=collision,
                                custom="existing-stays-unchanged")
        generated = FakeMaterial(2, "Generated", custom="generated-stays-unchanged")
        materials = [existing, generated]
        before = [(dict(material), material.name) for material in materials]

        with patch.object(final_state_package, "uuid4",
                          return_value=SimpleNamespace(hex="c" * 32)):
            with self.assertRaisesRegex(ValueError, "duplicate.*Export Material ID"):
                final_state_package._material_slot_export_ids(
                    [slot(existing), slot(generated)], materials)

        self.assertEqual(before, [(dict(material), material.name) for material in materials])

    def test_existing_export_id_is_reused_for_repeated_slots_without_mutation(self):
        existing_id = "VAPB-MAT-" + "f" * 32
        material = FakeMaterial(1, "Existing", _vapb_export_material_id=existing_id,
                                unity_source_package_id="package-a")
        before = (dict(material), material.name)

        ids_by_pointer, slot_ids = final_state_package._material_slot_export_ids(
            [slot(material), slot(material)], [material])

        self.assertEqual({1: existing_id}, ids_by_pointer)
        self.assertEqual([existing_id, existing_id], slot_ids)
        self.assertEqual(before, (dict(material), material.name))

    def test_existing_duplicate_ids_are_rejected_without_source_mutation(self):
        duplicate = "VAPB-MAT-" + "d" * 32
        first = FakeMaterial(1, "First", _vapb_export_material_id=duplicate,
                             unity_source_package_id="package-a")
        second = FakeMaterial(2, "Second", _vapb_export_material_id=duplicate,
                              unity_source_package_id="package-a")
        materials = [first, second]
        before = [(dict(material), material.name) for material in materials]

        with self.assertRaisesRegex(ValueError, "duplicate VAPB Export ID"):
            final_state_package._material_slot_export_ids(
                [slot(first), slot(second)], materials)

        self.assertEqual(before, [(dict(material), material.name) for material in materials])

    def test_generated_ids_and_repeated_slot_resolution_do_not_mutate_sources(self):
        first = FakeMaterial(1, "First", unity_source_package_id="package-a",
                             custom="preserve-me")
        materials = [first]
        before = (dict(first), first.name)

        with patch.object(final_state_package, "uuid4",
                          return_value=SimpleNamespace(hex="e" * 32)):
            ids_by_pointer, slot_ids = final_state_package._material_slot_export_ids(
                [slot(first), slot(first)], materials)

        self.assertEqual([ids_by_pointer[1], ids_by_pointer[1]], slot_ids)
        self.assertEqual(before, (dict(first), first.name))
        self.assertNotIn("_vapb_export_material_id", first)

    def test_unused_material_slot_is_rejected_without_mutation(self):
        first = FakeMaterial(1, "Used", color=(1, 0, 0))
        unused = FakeMaterial(2, "Unused", color=(0, 1, 0))
        slots = [slot(first), slot(unused)]
        polygons = [polygon(0), polygon(0)]
        before_materials = [(dict(value.material), value.material.name) for value in slots]
        before_indices = [value.material_index for value in polygons]

        with self.assertRaisesRegex(ValueError, "unused material slot.*remove.*re-export"):
            final_state_package._reject_unused_material_slots(slots, polygons)

        self.assertEqual(before_materials,
                         [(dict(value.material), value.material.name) for value in slots])
        self.assertEqual(before_indices, [value.material_index for value in polygons])

    def test_used_material_slots_are_accepted_without_mutation(self):
        first = FakeMaterial(1, "First")
        second = FakeMaterial(2, "Second")
        slots = [slot(first), slot(second)]
        polygons = [polygon(0), polygon(1)]
        before = ([(dict(value.material), value.material.name) for value in slots],
                  [value.material_index for value in polygons])

        final_state_package._reject_unused_material_slots(slots, polygons)

        self.assertEqual(before, ([(dict(value.material), value.material.name) for value in slots],
                                  [value.material_index for value in polygons]))

    def test_export_rejects_unused_slot_before_fbx_staging_without_mutation(self):
        used = FakeMaterial(1, "Used", unity_source_package_id="package-a",
                            custom="keep-used")
        unused = FakeMaterial(2, "Unused", unity_source_package_id="package-a",
                              custom="keep-unused")
        slots = [slot(used), slot(unused)]
        polygons = [polygon(0)]
        mesh = FakeMaterial(3, "Mesh", custom="keep-mesh")
        mesh.type = "MESH"
        mesh.data = SimpleNamespace(shape_keys=None, uv_layers=[object()], polygons=polygons)
        mesh.modifiers = []
        mesh.material_slots = slots
        context = SimpleNamespace(mode="OBJECT", scene={})
        before = ([(dict(value.material), value.material.name) for value in slots],
                  dict(mesh), mesh.name, [value.material_index for value in polygons])
        bpy_module = ModuleType("bpy")
        bpy_module.data = SimpleNamespace(objects=[], materials=[used, unused])

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "should-not-be-created.unitypackage"
            with patch.dict("sys.modules", {"bpy": bpy_module}), \
                    patch.object(final_state_package, "_stage_fbx") as stage_fbx:
                with self.assertRaisesRegex(ValueError, "unused material slot.*remove.*re-export"):
                    final_state_package.export_final_state_package(context, mesh, output)

                stage_fbx.assert_not_called()
                self.assertFalse(output.exists())

        after = ([(dict(value.material), value.material.name) for value in slots],
                 dict(mesh), mesh.name, [value.material_index for value in polygons])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
