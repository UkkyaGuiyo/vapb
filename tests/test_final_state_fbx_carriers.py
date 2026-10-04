"""Isolated Blender tests for temporary final-state FBX Material carriers."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import bpy
except ImportError:
    bpy = None

from unitypackage_blender_importer.export import final_state_package


@unittest.skipIf(bpy is None, "requires Blender's Python runtime")
class FinalStateFbxCarrierTests(unittest.TestCase):
    def setUp(self):
        self.scene = bpy.context.scene
        self.selected_before = tuple(bpy.context.selected_objects)
        self.active_before = bpy.context.view_layer.objects.active
        self.materials_before = set(bpy.data.materials)
        self.meshes_before = set(bpy.data.meshes)
        self.objects_before = set(bpy.data.objects)

        self.material_a = bpy.data.materials.new("Stage2 Source A")
        self.material_a["source_note"] = "preserve A"
        self.material_a["_vapb_export_material_id"] = "VAPB-MAT-" + "a" * 32
        self.material_b = bpy.data.materials.new("Stage2 Source B")
        self.material_b["source_note"] = "preserve B"
        self.material_b["_vapb_export_material_id"] = "VAPB-MAT-" + "b" * 32
        self.mesh_data = bpy.data.meshes.new("Stage2 Source Mesh")
        self.mesh_data.from_pydata(
            [(0, 0, 0), (1, 0, 0), (0, 1, 0),
             (2, 0, 0), (3, 0, 0), (2, 1, 0),
             (4, 0, 0), (5, 0, 0), (4, 1, 0)], [],
            [(0, 1, 2), (3, 4, 5), (6, 7, 8)])
        self.mesh_data.materials.append(self.material_a)
        self.mesh_data.materials.append(self.material_b)
        self.mesh_data.materials.append(self.material_a)
        self.mesh_data.polygons[0].material_index = 0
        self.mesh_data.polygons[1].material_index = 1
        self.mesh_data.polygons[2].material_index = 2
        self.mesh_object = bpy.data.objects.new("Stage2 Source Object", self.mesh_data)
        self.scene.collection.objects.link(self.mesh_object)
        self.mesh_object["source_note"] = "preserve object"
        self.mesh_object["_vapb_export_object_id"] = "VAPB-OBJ-" + "c" * 32
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        self.mesh_object.select_set(True)
        bpy.context.view_layer.objects.active = self.mesh_object

        self.export_id = "VAPB-OBJ-" + "1" * 32
        self.label_a = "VAPB-MAT-" + "a" * 32
        self.label_b = "VAPB-MAT-" + "b" * 32
        self.material_ids = {
            self.material_a.as_pointer(): self.label_a,
            self.material_b.as_pointer(): self.label_b,
        }

    def tearDown(self):
        for obj in tuple(bpy.data.objects):
            if obj not in self.objects_before:
                bpy.data.objects.remove(obj, do_unlink=True)
        for datablock in tuple(bpy.data.meshes):
            if datablock not in self.meshes_before and datablock.users == 0:
                bpy.data.meshes.remove(datablock)
        for datablock in tuple(bpy.data.materials):
            if datablock not in self.materials_before and datablock.users == 0:
                bpy.data.materials.remove(datablock)
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in self.selected_before:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = (
            self.active_before if self.active_before and self.active_before.name in bpy.data.objects else None)

    def snapshot(self):
        return {
            "materials": [(material.as_pointer(), material.name, dict(material))
                          for material in (self.material_a, self.material_b)],
            "mesh": (self.mesh_object.name, self.mesh_object.data.name,
                     tuple(material.as_pointer() for material in self.mesh_data.materials),
                     tuple(poly.material_index for poly in self.mesh_data.polygons),
                     tuple((slot.link, slot.material.as_pointer() if slot.material else None)
                           for slot in self.mesh_object.material_slots),
                     tuple(tuple(row) for row in self.mesh_object.matrix_world),
                     tuple(tuple(vertex.co) for vertex in self.mesh_data.vertices),
                     tuple((poly.material_index, tuple(poly.vertices))
                           for poly in self.mesh_data.polygons),
                     dict(self.mesh_object)),
            "selection": tuple(obj.as_pointer() for obj in bpy.context.selected_objects),
            "active": (bpy.context.view_layer.objects.active.as_pointer()
                       if bpy.context.view_layer.objects.active else None),
            "counts": (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials)),
        }

    def assert_stage_cleanup_and_source_unchanged(self, before):
        self.assertEqual(before, self.snapshot())

    def _imported_mesh(self, output):
        existing = set(bpy.data.objects)
        self.assertEqual({"FINISHED"}, bpy.ops.import_scene.fbx(filepath=str(output)))
        imported = [obj for obj in bpy.data.objects
                    if obj not in existing and obj.type == "MESH"]
        self.assertEqual(1, len(imported))
        return imported[0]

    def _stage_with_slot_capture(self, output):
        captured = []

        def capture_and_export(options):
            staged = [obj for obj in bpy.context.selected_objects
                      if obj is not self.mesh_object]
            self.assertEqual(1, len(staged))
            captured.append([slot.material.name for slot in staged[0].material_slots])
            return bpy.ops.export_scene.fbx(**options)

        with patch.object(final_state_package, "_export_fbx", side_effect=capture_and_export):
            final_state_package._stage_fbx(
                bpy.context, self.mesh_object, self.export_id, output,
                material_ids_by_pointer=self.material_ids)

        self.assertEqual([[self.label_a, self.label_b, self.label_a]], captured)

    def _assert_imported_material_identity(self, imported):
        slot_names = [slot.material.name for slot in imported.material_slots]
        # Blender's FBX roundtrip coalesces the repeated A carrier into two
        # material slots. Face identity survives; native Unity multiplicity
        # remains unverified and must be checked by the Finalizer in Stage 3.
        self.assertEqual([self.label_a, self.label_b], slot_names)
        face_names = [imported.material_slots[poly.material_index].material.name
                      for poly in imported.data.polygons]
        self.assertEqual([self.label_a, self.label_b, self.label_a], face_names)

    def test_staging_keeps_a_b_a_slots_and_blender_roundtrip_records_coalescing(self):
        before = self.snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "Generated.fbx"
            self._stage_with_slot_capture(output)

            self.assertTrue(output.is_file())
            payload = output.read_bytes()
            self.assertIn(self.label_a.encode("ascii"), payload)
            self.assertIn(self.label_b.encode("ascii"), payload)
            self.assert_stage_cleanup_and_source_unchanged(before)
            self._assert_imported_material_identity(self._imported_mesh(output))

    def test_object_linked_slot_exports_carrier_names_without_source_mutation(self):
        self.mesh_object.material_slots[0].link = "OBJECT"
        self.mesh_object.material_slots[0].material = self.material_a
        before = self.snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "Generated.fbx"
            self._stage_with_slot_capture(output)
            self.assert_stage_cleanup_and_source_unchanged(before)
            self._assert_imported_material_identity(self._imported_mesh(output))

    def test_renamed_carrier_suffix_is_rejected_and_cleaned_up(self):
        before = self.snapshot()
        blocker = bpy.data.materials.new(self.label_a)
        before = self.snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "Generated.fbx"
            with self.assertRaisesRegex(ValueError, "material.*label.*exact"):
                final_state_package._stage_fbx(
                    bpy.context, self.mesh_object, self.export_id, output,
                    material_ids_by_pointer=self.material_ids)

            self.assertFalse(output.exists())

        self.assertEqual(self.label_a, blocker.name)
        self.assert_stage_cleanup_and_source_unchanged(before)

    def test_export_exception_cleans_staging_and_preserves_sources(self):
        before = self.snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "missing-parent" / "Generated.fbx"
            with self.assertRaisesRegex(RuntimeError, "No such file or directory"):
                final_state_package._stage_fbx(
                    bpy.context, self.mesh_object, self.export_id, output,
                    material_ids_by_pointer=self.material_ids)
            self.assertFalse(output.exists())

        self.assert_stage_cleanup_and_source_unchanged(before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
