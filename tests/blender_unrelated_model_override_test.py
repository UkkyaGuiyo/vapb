"""Exercise three synthetic model Renderers through actual Blender Object slots."""

import json
from pathlib import Path
import sys
import tempfile

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_dependency, load_dependency_registry, resolve_scene_dependencies,
)
from unitypackage_blender_importer.blender.model_witness_bridge import (  # noqa: E402
    plan_witness_material_dependencies, plan_witness_realizations, reserve_witness_slots,
)
from unitypackage_blender_importer.tests.test_unrelated_model_override import (  # noqa: E402
    MATERIAL_A, MATERIAL_B, PACKAGE_SHA, fixture, native,
)


def check_scene():
    rows = json.loads(bpy.data.objects["SyntheticRoot"]["_vapb_renderer_occurrences"])
    assert [row["material_status"] for row in rows["records"]] == ["PARTIAL", "PARTIAL", "PARTIAL"]
    assert len(rows["issues"]) == 1
    registry = load_dependency_registry(bpy.context.scene)["dependencies"]
    assert len(registry) == 2
    assert {item["target_guid"] for item in registry} == {MATERIAL_A, MATERIAL_B}
    for index, guid in enumerate((MATERIAL_A, MATERIAL_B)):
        obj = bpy.data.objects[f"SyntheticMesh_{index}"]
        slot = obj.material_slots[0]
        assert slot.link == "OBJECT"
        assert slot.material is not None
        assert slot.material.get("unity_material_guid") == guid
        assert slot.material.get("unity_material_file_id") == "2100000"
        assert registry[index]["binding_status"] == "BOUND"
    assert bpy.data.objects["SyntheticMesh_2"].material_slots[0].material is None
    assert all(item["consumer_native_realization_id"] != "native-2" for item in registry)


def main():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python script -- import|reopen blend_path")
    phase, blend_path = sys.argv[sys.argv.index("--") + 1:]
    if phase == "reopen":
        check_scene()
        counts = resolve_scene_dependencies(bpy.context.scene)
        assert counts["missing_consumer"] == 0, counts
        check_scene()
        print("UNRELATED_MODEL_OVERRIDE_REOPEN_PASS")
        return
    assert phase == "import"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with tempfile.TemporaryDirectory(prefix="vapb_synthetic_override_") as temp:
        projection, witness = fixture(temp)
    assert [item["code"] for item in projection.issues] == ["UNRESOLVED_OVERRIDE"]
    root = bpy.data.objects.new("SyntheticRoot", None)
    bpy.context.scene.collection.objects.link(root)
    root["_vapb_root_context_id"] = "root-context"
    root["_vapb_witness_package_sha256"] = PACKAGE_SHA
    root["_vapb_renderer_occurrences"] = json.dumps(projection.to_dict(), sort_keys=True)
    objects = []
    for index, record in enumerate(projection.records):
        mesh = bpy.data.meshes.new(f"SyntheticData_{index}")
        mesh.materials.append(None)
        obj = bpy.data.objects.new(f"SyntheticMesh_{index}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        receipt = native(record)
        for key, value in receipt.items():
            obj[key] = value
        for key, value in receipt.data.items():
            mesh[key] = value
        objects.append(obj)
    bindings, issues = plan_witness_realizations(projection.records, objects, witness)
    assert not issues, issues
    dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
    assert len(dependencies) == 2
    ready, rejected = reserve_witness_slots(dependencies, bpy.data.objects)
    assert len(ready) == 2 and not rejected, rejected
    for dependency in ready:
        capture_dependency(bpy.context.scene, dependency)
    for index, guid in enumerate((MATERIAL_A, MATERIAL_B)):
        material = bpy.data.materials.new(f"SyntheticProvider_{index}")
        material["unity_material_guid"] = guid
        material["unity_material_file_id"] = "2100000"
        material["unity_source_package_id"] = "provider-package"
    counts = resolve_scene_dependencies(bpy.context.scene)
    assert counts["late_bindings_applied"] == 2, counts
    check_scene()
    assert bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False) == {"FINISHED"}
    print("UNRELATED_MODEL_OVERRIDE_IMPORT_PASS")


main()
