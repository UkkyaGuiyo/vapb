"""Late material providers must bind the actual occurrence Object slot."""

import sys
import tempfile
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import _bind_material, _find_consumer, _unbind_dependency, capture_dependency, load_dependency_registry, resolve_scene_dependencies


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("SharedMesh")
    mesh.materials.append(bpy.data.materials.new("SharedPlaceholder"))
    objects = []
    for file_id in ("101", "102"):
        obj = bpy.data.objects.new(f"Occurrence_{file_id}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj["unity_source_package_id"] = "synthetic-package"
        obj["unity_asset_path"] = "Assets/Synthetic.prefab"
        obj["unity_prefab_file_id"] = file_id
        obj.material_slots[0].link = "OBJECT"
        objects.append(obj)

    materials = [bpy.data.materials.new("Provider_A"), bpy.data.materials.new("Provider_B")]
    for index, material in enumerate(materials):
        material["unity_material_guid"] = chr(ord("a") + index) * 32
        material["unity_source_package_id"] = "synthetic-provider"
    records = []
    for obj, material in zip(objects, materials):
        record = capture_dependency(bpy.context.scene, {
            "dependency_type": "PREFAB_RENDERER_MATERIAL",
            "consumer_package_id": "synthetic-package",
            "consumer_asset_path": "Assets/Synthetic.prefab",
            "consumer_game_object_file_id": obj["unity_prefab_file_id"],
            "consumer_slot_index": 0,
            "target_guid": material["unity_material_guid"],
        })
        assert _bind_material(record, material), record
        records.append(record)
        assert obj.material_slots[0].link == "OBJECT"
        assert obj.material_slots[0].material is material

    assert objects[0].data is objects[1].data
    assert objects[0].material_slots[0].material is materials[0]
    assert objects[1].material_slots[0].material is materials[1]
    copied_provider = materials[0].copy()
    assert not _bind_material(records[0], materials[0])
    assert records[0]["status"] == "UNVERIFIED_SLOT_STATE"
    assert objects[0].material_slots[0].material is materials[0]
    bpy.data.materials.remove(copied_provider)
    user_material = bpy.data.materials.new("UserEdited")
    objects[0].material_slots[0].material = user_material
    retry = records[0]
    assert not _bind_material(retry, materials[0])
    assert retry["status"] == "USER_EDIT_PRESERVED"
    assert objects[0].material_slots[0].material is user_material
    # A deliberate clear and a selection of the shared Mesh default are also
    # edits; retrying a provider must not silently replace either choice.
    objects[1].material_slots[0].material = None
    assert not _bind_material(records[1], materials[1])
    assert objects[1].material_slots[0].material is None
    objects[1].material_slots[0].material = mesh.materials[0]
    assert not _bind_material(records[1], materials[1])
    assert objects[1].material_slots[0].material is mesh.materials[0]
    objects[1].material_slots[0].material = materials[1]
    pending = bpy.data.objects.new("PendingOccurrence", mesh)
    bpy.context.scene.collection.objects.link(pending)
    pending["unity_source_package_id"] = "synthetic-package"
    pending["unity_asset_path"] = "Assets/Synthetic.prefab"
    pending["unity_prefab_file_id"] = "103"
    pending.material_slots[0].link = "OBJECT"
    pending.material_slots[0].material = mesh.materials[0]
    pending_record = capture_dependency(bpy.context.scene, {
        "dependency_type": "PREFAB_RENDERER_MATERIAL",
        "consumer_package_id": "synthetic-package",
        "consumer_asset_path": "Assets/Synthetic.prefab",
        "consumer_game_object_file_id": "103",
        "consumer_slot_index": 0,
        "target_guid": materials[0]["unity_material_guid"],
    })
    pending.material_slots[0].material = None
    assert not _bind_material(pending_record, materials[0])
    assert pending_record["status"] == "USER_EDIT_PRESERVED"
    assert pending.material_slots[0].material is None
    for record, material in zip(records, materials):
        removed = {**record, "dependency_type": "PREFAB_RENDERER_MATERIAL",
                   "resolved_provider_package_id": "synthetic-provider",
                   "resolved_provider_guid": material["unity_material_guid"]}
        _unbind_dependency(removed)
    assert objects[0].material_slots[0].material is user_material
    assert objects[1].material_slots[0].material is None
    assert mesh.materials[0].name == "SharedPlaceholder"
    assert _find_consumer({
        "consumer_package_id": "synthetic-package",
        "consumer_object_path": "Assets/Synthetic.prefab",
        "consumer_game_object_file_id": "999",
        "consumer_object_name": objects[0].name,
    }) is None
    assert _find_consumer({
        "consumer_package_id": "synthetic-package",
        "consumer_object_path": "Assets/Synthetic.prefab",
        "consumer_object_name": objects[0].name,
    }) is None
    objects[0].name = "UserRenamed"
    assert _find_consumer({
        "consumer_package_id": "synthetic-package",
        "consumer_object_path": "Assets/Synthetic.prefab",
        "consumer_game_object_file_id": "101",
        "consumer_object_name": "OldDisplayName",
    }) is objects[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("GrowingSharedMesh")
    mesh.materials.append(None)
    obj = bpy.data.objects.new("TwoPendingSlots", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj["unity_source_package_id"] = "synthetic-package"
    obj["unity_asset_path"] = "Assets/TwoSlots.prefab"
    obj["unity_prefab_file_id"] = "201"
    first = capture_dependency(bpy.context.scene, {
        "dependency_type": "PREFAB_RENDERER_MATERIAL", "consumer_package_id": "synthetic-package",
        "consumer_asset_path": "Assets/TwoSlots.prefab", "consumer_game_object_file_id": "201",
        "consumer_slot_index": 0, "target_guid": "a" * 32,
    })
    second = capture_dependency(bpy.context.scene, {
        "dependency_type": "PREFAB_RENDERER_MATERIAL", "consumer_package_id": "synthetic-package",
        "consumer_asset_path": "Assets/TwoSlots.prefab", "consumer_game_object_file_id": "201",
        "consumer_slot_index": 1, "target_guid": "b" * 32,
    })
    material_a = bpy.data.materials.new("FirstSlotProvider")
    material_b = bpy.data.materials.new("SecondSlotProvider")
    assert _bind_material(second, material_b)
    assert _bind_material(first, material_a)
    assert obj.material_slots[0].material is material_a
    assert obj.material_slots[1].material is material_b
    with tempfile.TemporaryDirectory(prefix="vapb_late_slot_") as temp:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("PersistedMesh")
        mesh.materials.append(None)
        obj = bpy.data.objects.new("PersistedOccurrence", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj["unity_source_package_id"] = "synthetic-package"
        obj["unity_asset_path"] = "Assets/Synthetic.prefab"
        obj["unity_prefab_file_id"] = "104"
        material = bpy.data.materials.new("PersistedProvider")
        material.use_fake_user = True
        material["unity_material_guid"] = "e" * 32
        material["unity_source_package_id"] = "synthetic-provider"
        capture_dependency(bpy.context.scene, {
            "dependency_type": "PREFAB_RENDERER_MATERIAL",
            "consumer_package_id": "synthetic-package",
            "consumer_asset_path": "Assets/Synthetic.prefab",
            "consumer_game_object_file_id": "104",
            "consumer_slot_index": 0,
            "target_guid": "e" * 32,
        })
        blend = str(Path(temp) / "late.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend, check_existing=False)
        bpy.ops.wm.open_mainfile(filepath=blend, load_ui=False)
        assert resolve_scene_dependencies(bpy.context.scene)["late_bindings_applied"] == 1
        obj = _find_consumer({"consumer_package_id": "synthetic-package",
                              "consumer_asset_path": "Assets/Synthetic.prefab",
                              "consumer_game_object_file_id": "104"})
        assert obj.material_slots[0].material.get("unity_material_guid") == "e" * 32
        bpy.ops.wm.save_as_mainfile(filepath=blend, check_existing=False)
        bpy.ops.wm.open_mainfile(filepath=blend, load_ui=False)
        obj = _find_consumer({"consumer_package_id": "synthetic-package",
                              "consumer_asset_path": "Assets/Synthetic.prefab",
                              "consumer_game_object_file_id": "104"})
        obj.material_slots[0].material = None
        assert resolve_scene_dependencies(bpy.context.scene)["user_edit_preserved"] == 1
        assert obj.material_slots[0].material is None
        assert load_dependency_registry(bpy.context.scene)["dependencies"][0]["binding_status"] == "USER_EDIT_PRESERVED"
    print("LATE_MATERIAL_OBJECT_SLOTS=PASS")


if __name__ == "__main__":
    main()
