"""Synthetic exact-witness Material clear across two Object occurrences."""

import copy
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_dependency, load_dependency_registry, resolve_scene_dependencies,
)
from unitypackage_blender_importer.blender.model_witness_bridge import (  # noqa: E402
    plan_witness_realizations, plan_witness_material_dependencies, reserve_witness_slots,
)
from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome  # noqa: E402
from unitypackage_blender_importer.tests.test_model_witness_bridge import (  # noqa: E402
    PACKAGE_SHA, native, record, witness,
)
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity  # noqa: E402


def make_scene(multislot=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("Source Material")
    material["unity_material_guid"] = "e" * 32
    material["unity_material_file_id"] = "2100000"
    material["unity_source_package_id"] = "pkg"
    mesh = bpy.data.meshes.new("Shared Synthetic Mesh")
    mesh.materials.append(material)
    if multislot:
        for label, guid in (("Middle Material", "f" * 32), ("Last Material", "9" * 32)):
            extra = bpy.data.materials.new(label)
            extra["unity_material_guid"] = guid
            extra["unity_material_file_id"] = "2100000"
            extra["unity_source_package_id"] = "pkg"
            mesh.materials.append(extra)
    source = record()
    if multislot:
        source["materials"].update({
            1: {"guid": "f" * 32, "file_id": 2100000},
            2: {"guid": "9" * 32, "file_id": 2100000},
        })
        source["material_slot_count"] = 3
    target = copy.deepcopy(source)
    target["root_context_id"] = "root-two"
    target["occurrence_id"] = occurrence_identity(target)
    target["materials"] = ({0: source["materials"][0], 1: None, 2: source["materials"][2]}
                           if multislot else {0: None})
    for index, row in enumerate((source, target)):
        root = bpy.data.objects.new(f"Root {index}", None)
        bpy.context.scene.collection.objects.link(root)
        root["_vapb_root_context_id"] = row["root_context_id"]
        root["_vapb_witness_package_sha256"] = PACKAGE_SHA
        root["_vapb_renderer_occurrences"] = json.dumps({"records": [row], "issues": []})
        obj = bpy.data.objects.new(f"Occurrence {index}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        source_receipt = native(realization=f"native-{index}")
        source_receipt["_vapb_root_context_id"] = row["root_context_id"]
        for key, value in source_receipt.items():
            obj[key] = value
        for key, value in source_receipt.data.items():
            mesh[key] = value
    return source, target, material


def check_slots(source_material):
    left = bpy.data.objects["Occurrence 0"]
    right = bpy.data.objects["Occurrence 1"]
    assert left.data is right.data
    assert len(left.material_slots) == len(right.material_slots) == 1
    assert left.material_slots[0].material is source_material
    assert right.material_slots[0].link == "OBJECT"
    assert right.material_slots[0].material is None
    assert left.data.materials[0] is source_material


def main():
    phase, blend_path = sys.argv[sys.argv.index("--") + 1:]
    if phase in {"create", "multi", "wrong"}:
        source, target, material = make_scene(multislot=phase == "multi")
        objects = [bpy.data.objects["Occurrence 0"], bpy.data.objects["Occurrence 1"]]
        bindings, issues = plan_witness_realizations([source, target], objects, witness())
        assert not issues and len(bindings) == 2, issues
        dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        ready, rejected = reserve_witness_slots(dependencies, bpy.data.objects)
        assert not rejected, rejected
        for dependency in ready:
            capture_dependency(bpy.context.scene, dependency)
        if phase == "wrong":
            right = bpy.data.objects["Occurrence 1"]
            right["_vapb_fbx_object_receipt_id"] = "incorrect-receipt"
            resolve_scene_dependencies(bpy.context.scene)
            assert right.material_slots[0].material is material
            assert right.material_slots[0].link == "DATA"
            clear = next(item for item in load_dependency_registry(bpy.context.scene)["dependencies"]
                         if item["dependency_type"] == "CLEAR_MATERIAL_SLOT")
            assert clear["binding_status"] == "MISSING_CONSUMER"
            print("NULL_MATERIAL_WRONG_RECEIPT_CLOSED")
            return
        resolve_scene_dependencies(bpy.context.scene)
        if phase == "multi":
            left = bpy.data.objects["Occurrence 0"]
            right = bpy.data.objects["Occurrence 1"]
            assert left.data is right.data and len(left.material_slots) == len(right.material_slots) == 3
            assert [slot.material for slot in left.material_slots] == [
                material, bpy.data.materials["Middle Material"], bpy.data.materials["Last Material"]]
            assert [slot.material for slot in right.material_slots] == [
                material, None, bpy.data.materials["Last Material"]]
            assert right.material_slots[1].link == "OBJECT"
            assert left.data.materials[1] is bpy.data.materials["Middle Material"]
            assert scene_import_outcome(bpy.context.scene)["overall"] == "SUCCESS"
            print("NULL_MATERIAL_MULTISLOT_PASS")
            return
        check_slots(material)
        assert len(ready) == 2, "Known null was omitted from the native realization plan"
        assert scene_import_outcome(bpy.context.scene)["overall"] == "SUCCESS"
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("NULL_MATERIAL_CREATE_PASS")
    elif phase == "reopen":
        material = bpy.data.materials["Source Material"]
        check_slots(material)
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_slots(material)
        assert scene_import_outcome(bpy.context.scene)["overall"] == "SUCCESS"
        print("NULL_MATERIAL_REOPEN_PASS")
    elif phase == "edit":
        edited = bpy.data.materials.new("User Material")
        right = bpy.data.objects["Occurrence 1"]
        right.material_slots[0].material = edited
        resolve_scene_dependencies(bpy.context.scene)
        assert right.material_slots[0].material is edited
        assert "_vapb_dependency_material_token" not in edited
        assert bpy.data.objects["Occurrence 0"].material_slots[0].material.name == "Source Material"
        registry = load_dependency_registry(bpy.context.scene)["dependencies"]
        clear = next(item for item in registry if item["dependency_type"] == "CLEAR_MATERIAL_SLOT")
        assert clear["binding_status"] == "USER_EDIT_PRESERVED"
        outcome = scene_import_outcome(bpy.context.scene)
        assert outcome["overall"] == "PARTIAL"
        assert "USER_EDIT_PRESERVED" in [item["code"] for item in outcome["items"]]
        assert "NULL_MATERIAL_REALIZATION_UNVERIFIED" not in [item["code"] for item in outcome["items"]]
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("NULL_MATERIAL_USER_EDIT_PASS")
    elif phase == "edit-reopen":
        right = bpy.data.objects["Occurrence 1"]
        resolve_scene_dependencies(bpy.context.scene)
        assert right.material_slots[0].material.name == "User Material"
        assert scene_import_outcome(bpy.context.scene)["overall"] == "PARTIAL"
        print("NULL_MATERIAL_USER_EDIT_REOPEN_PASS")
    else:
        raise AssertionError(phase)


if __name__ == "__main__":
    main()
