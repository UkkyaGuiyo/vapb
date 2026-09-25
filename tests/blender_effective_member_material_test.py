"""Blender 5.2 proof for shared Mesh + OBJECT-linked member materials."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))
import bpy


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("SharedRepresentation")
    mesh.materials.append(bpy.data.materials.new("Initial"))
    a = bpy.data.objects.new("Variant_A", mesh)
    b = bpy.data.objects.new("Variant_B", mesh)
    bpy.context.scene.collection.objects.link(a)
    bpy.context.scene.collection.objects.link(b)
    mat_a = bpy.data.materials.new("Material_A")
    mat_b = bpy.data.materials.new("Material_B")
    a.material_slots[0].link = "OBJECT"
    b.material_slots[0].link = "OBJECT"
    a.material_slots[0].material = mat_a
    b.material_slots[0].material = mat_b
    assert a.data is b.data
    assert a.material_slots[0].link == "OBJECT"
    assert b.material_slots[0].link == "OBJECT"
    assert a.material_slots[0].material != b.material_slots[0].material
    mat_c = bpy.data.materials.new("Material_C")
    b.material_slots[0].material = mat_c
    assert a.material_slots[0].material == mat_a
    assert b.material_slots[0].material == mat_c
    material_guid = "a" * 32
    mat_a["unity_material_guid"] = material_guid
    mat_b["unity_material_guid"] = material_guid
    path = bpy.app.tempdir + "vapb_object_links.blend"
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    loaded_a = bpy.data.objects["Variant_A"]
    loaded_b = bpy.data.objects["Variant_B"]
    assert loaded_a.data is loaded_b.data
    assert loaded_a.material_slots[0].link == "OBJECT"
    assert loaded_b.material_slots[0].link == "OBJECT"
    from unitypackage_blender_importer.blender.material_builder import _append_renderer_provenance
    _append_renderer_provenance(
        loaded_a, "member-a", "b" * 32, 101, 201, 23,
        {"guid": "c" * 32, "fileID": 301},
        [{"slot": 0, "effective_material_guid": material_guid,
          "effective_material_file_id": "401", "realized_material_guid": material_guid}],
    )
    _append_renderer_provenance(
        loaded_b, "member-b", "b" * 32, 101, 202, 23,
        {"guid": "c" * 32, "fileID": 301},
        [{"slot": 0, "effective_material_guid": material_guid,
          "effective_material_file_id": "401", "realized_material_guid": material_guid}],
    )
    loaded_a.name = "Renamed_A"
    loaded_b.name = "Renamed_B"
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    bindings_a = json.loads(bpy.data.objects["Renamed_A"]["_vapb_renderer_bindings"])
    bindings_b = json.loads(bpy.data.objects["Renamed_B"]["_vapb_renderer_bindings"])
    assert bindings_a["renderers"][0]["semantic_id"] != bindings_b["renderers"][0]["semantic_id"]
    assert bindings_a["renderers"][0]["material_slots"][0]["realized_material_guid"] == material_guid
    class FakeObject(dict):
        def __init__(self):
            super().__init__()
            self.name = "Ambiguous"
            self.data = SimpleNamespace(materials=[])

        __hash__ = object.__hash__

    from unitypackage_blender_importer.blender.material_builder import apply_prefab_modification_materials
    class FakePrefab:
        def modification_materials(self):
            return [{"object_name": "Ambiguous", "material_guid": material_guid,
                     "target_file_id": "99", "target_source_guid": "b" * 32,
                     "slot_index": 0}]
    class FakeEntry:
        path = "Material"
    class FakeDB:
        def find_guid(self, guid):
            return FakeEntry()
    fake_a, fake_b = FakeObject(), FakeObject()
    apply_prefab_modification_materials(
        FakePrefab(), {fake_a: fake_a, fake_b: fake_b}, FakeDB(), {"Material": mat_a}
    )
    assert "_vapb_renderer_bindings" not in fake_a
    assert "_vapb_renderer_bindings" not in fake_b
    print("EFFECTIVE_MEMBER_OBJECT_LINKS=PASS")
    print("RENDERER_PROVENANCE_SAVE_RELOAD=PASS")
    print("RENDERER_PROVENANCE_AMBIGUOUS_FAIL_CLOSED=PASS")


if __name__ == "__main__":
    main()
