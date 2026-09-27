"""Unity-authored null Prefab to witnessed native FBX Object-slot probe."""

import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_dependency, resolve_scene_dependencies,
)
from unitypackage_blender_importer.blender.fbx_receipt import (  # noqa: E402
    RawFbxSemanticIndex, copy_with_receipt, import_with_receipts, source_sha256,
)
from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome  # noqa: E402
from unitypackage_blender_importer.blender.model_witness_bridge import (  # noqa: E402
    plan_witness_material_dependencies, plan_witness_realizations, reserve_witness_slots,
)
from unitypackage_blender_importer.tests.test_unity_null_material_oracle import (  # noqa: E402
    ASSETS, EXPECTED, source,
)
from unitypackage_blender_importer.unity.model_identity_witness import (  # noqa: E402
    ModelAssetRevision, build_model_witness_from_probe, validate_model_witness,
)
from unitypackage_blender_importer.unity.occurrence_projection import project_occurrences  # noqa: E402


ORACLE = EXPECTED.parent
MODEL = ASSETS / "Model.fbx"
META = ASSETS / "Model.fbx.meta"


def check_scene():
    source_obj = bpy.data.objects["Null Source Occurrence"]
    variant_obj = bpy.data.objects["Null Variant Occurrence"]
    material = bpy.data.materials["Null Base Material"]
    assert source_obj.data is variant_obj.data
    assert len(source_obj.material_slots) == len(variant_obj.material_slots) == 1
    assert source_obj.material_slots[0].material is material
    assert variant_obj.material_slots[0].link == "OBJECT"
    assert variant_obj.material_slots[0].material is None
    assert source_obj.data.materials[0] is material
    assert scene_import_outcome(bpy.context.scene)["overall"] == "SUCCESS"


def main():
    phase, blend_path = sys.argv[sys.argv.index("--") + 1:]
    if phase == "reopen":
        check_scene()
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_scene()
        print("UNITY_NULL_NATIVE_REOPEN_PASS")
        return
    assert phase == "create"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    observed = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert observed["unityVersion"] == "2022.3.22f1"
    assert (observed["sourceSlots"], observed["variantSlots"]) == (1, 1)
    assert observed["sourceHasMaterial"] and observed["variantIsNull"] and observed["sharedMeshSame"]
    fbx_sha, meta_sha = source_sha256(MODEL), source_sha256(META)
    mapping = json.loads((ORACLE / "null_fbx_witness_mapping.json").read_text(encoding="utf-8"))
    report = json.loads((ORACLE / "null_fbx_witness_result.json").read_text(encoding="utf-8"))
    guid = observed["meshGuid"].lower()
    assert guid == mapping["model_guid"] and mapping["source_fbx_sha256"] == fbx_sha
    assert mapping["source_meta_sha256"] == meta_sha
    package_sha = hashlib.sha256((fbx_sha + meta_sha + source_sha256(ASSETS / "Null_Override.prefab")
                                  + source_sha256(ASSETS / "Null_Source.prefab")).encode()).hexdigest()
    revisions = {guid: ModelAssetRevision(fbx_sha, meta_sha, RawFbxSemanticIndex.from_file(MODEL))}
    document = build_model_witness_from_probe(mapping, report, package_sha, revisions)
    witness = validate_model_witness(document, package_sha, revisions)
    source_prefab = source("Null_Source.prefab")
    variant_prefab = source("Null_Override.prefab")
    source_projection = project_occurrences(source_prefab, "null-source", lambda _p, _g: None)
    variant_projection = project_occurrences(
        variant_prefab, "null-variant",
        lambda _p, asset_guid: source_prefab if asset_guid == source_prefab.asset_guid else None)
    assert not source_projection.issues and not variant_projection.issues
    source_row, variant_row = source_projection.records[0], variant_projection.records[0]
    assert source_row["mesh"]["mesh_file_id"] == variant_row["mesh"]["mesh_file_id"] == int(observed["meshFileId"])
    assert source_row["materials"][0]["guid"] and variant_row["materials"] == {0: None}
    assert source_row["material_slot_count"] == variant_row["material_slot_count"] == 1
    for row in (source_row, variant_row):
        row["mesh"].update(source_package_id="synthetic", source_sha256=fbx_sha)
    receipts = import_with_receipts(
        MODEL, lambda: bpy.ops.import_scene.fbx(filepath=str(MODEL), use_custom_props=True), guid, bpy)
    assert len(receipts) == 2
    mapped = witness.mesh(guid, int(observed["meshFileId"]))
    assert mapped is not None
    candidates = [obj for obj in bpy.data.objects if obj.type == "MESH"
                  and obj.get("_vapb_fbx_model_uid") == str(mapped.model_uid)
                  and obj.get("_vapb_fbx_geometry_uid") == str(mapped.geometry_uid)
                  and obj.get("_vapb_fbx_source_asset_sha256") == fbx_sha]
    assert len(candidates) == 1
    source_obj = candidates[0]
    variant_obj = copy_with_receipt(source_obj)
    variant_obj["_vapb_model_instance_edge_path"] = json.dumps(
        variant_row["instance_edge_path"], sort_keys=True)
    source_obj.name = "Null Source Occurrence"
    variant_obj.name = "Null Variant Occurrence"
    bpy.context.scene.collection.objects.link(variant_obj)
    material = bpy.data.materials.new("Null Base Material")
    reference = source_row["materials"][0]
    material["unity_material_guid"] = reference["guid"]
    material["unity_material_file_id"] = str(reference["file_id"])
    material["unity_source_package_id"] = "synthetic"
    if source_obj.data.materials:
        source_obj.data.materials[0] = material
    else:
        source_obj.data.materials.append(material)
    for row, obj, projection in ((source_row, source_obj, source_projection),
                                 (variant_row, variant_obj, variant_projection)):
        obj["_vapb_root_context_id"] = row["root_context_id"]
        obj["unity_source_package_id"] = "synthetic"
        root = bpy.data.objects.new("Semantic Root", None)
        bpy.context.scene.collection.objects.link(root)
        root["_vapb_root_context_id"] = row["root_context_id"]
        root["_vapb_witness_package_sha256"] = package_sha
        root["_vapb_renderer_occurrences"] = json.dumps(projection.to_dict(), sort_keys=True)
    bindings, issues = plan_witness_realizations(
        [source_row, variant_row], [source_obj, variant_obj], witness)
    assert not issues and len(bindings) == 2, issues
    operations = plan_witness_material_dependencies(bindings, package_sha)
    assert {item["dependency_type"] for item in operations} == {
        "PREFAB_RENDERER_MATERIAL", "CLEAR_MATERIAL_SLOT"}
    ready, rejected = reserve_witness_slots(operations, bpy.data.objects)
    assert not rejected and len(ready) == 2, rejected
    for operation in ready:
        capture_dependency(bpy.context.scene, operation)
    resolve_scene_dependencies(bpy.context.scene)
    check_scene()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("UNITY_NULL_NATIVE_CREATE_PASS")


if __name__ == "__main__":
    main()
