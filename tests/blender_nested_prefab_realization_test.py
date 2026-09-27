"""Unity-authored public repeated Prefab through the normal package operator."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import bpy


FIXTURES = Path(__file__).with_name("unity_alias_oracle")
EXPECTED = json.loads((FIXTURES / "null_pair_expected.json").read_text(encoding="utf-8"))
MAPPING = json.loads((FIXTURES / "null_fbx_witness_mapping.json").read_text(encoding="utf-8"))
REPORT = json.loads((FIXTURES / "null_fbx_witness_result.json").read_text(encoding="utf-8"))
PACKAGE_MODULE = "unitypackage_blender_importer"


def enable_addon(phase, zip_path):
    if zip_path:
        if phase == "create":
            assert bpy.ops.preferences.addon_install(filepath=str(zip_path), overwrite=False) == {"FINISHED"}
        assert bpy.ops.preferences.addon_enable(module=PACKAGE_MODULE) == {"FINISHED"}
        addon = sys.modules[PACKAGE_MODULE]
        assert Path(addon.__file__).resolve().is_relative_to(
            Path(os.environ["BLENDER_USER_SCRIPTS"]).resolve())
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        import unitypackage_blender_importer as addon
        addon.register()
    return addon


def create_witness(package, output):
    from unitypackage_blender_importer.blender.fbx_receipt import RawFbxSemanticIndex, source_sha256
    from unitypackage_blender_importer.unity.asset_database import AssetDatabase
    from unitypackage_blender_importer.unity.model_identity_witness import (
        ModelAssetRevision, build_model_witness_from_probe)
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader

    with tempfile.TemporaryDirectory(prefix="vapb_nested_oracle_") as temp:
        extraction = UnityPackageReader(package).extract(Path(temp))
        assert not extraction.errors, extraction.errors
        db = AssetDatabase.from_extraction(extraction.root, extraction.assets)
        model = db.find_guid(MAPPING["model_guid"])
        pair = db.find_guid(EXPECTED["pairGuid"])
        assert model is not None and pair is not None
        assert model.path.suffix.lower() == ".fbx" and pair.path.suffix.lower() == ".prefab"
        assert source_sha256(pair.path) == source_sha256(
            FIXTURES / "Assets" / "Oracle" / "Null_TwoInstances.prefab")
        fbx_sha = source_sha256(model.path)
        meta_sha = source_sha256(Path(str(model.path) + ".meta"))
        assert (fbx_sha, meta_sha) == (
            MAPPING["source_fbx_sha256"], MAPPING["source_meta_sha256"])
        package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
        revisions = {MAPPING["model_guid"]: ModelAssetRevision(
            fbx_sha, meta_sha, RawFbxSemanticIndex.from_file(model.path))}
        document = build_model_witness_from_probe(MAPPING, REPORT, package_sha, revisions)
        output.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        return f"PREFAB_{db.prefabs().index(pair.path)}"


def check_scene(renamed=False, root_context_id=None):
    from unitypackage_blender_importer.blender.dependency_resolver import load_dependency_registry
    from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome
    from unitypackage_blender_importer.blender.model_witness_bridge import find_witness_consumer

    roots = []
    for obj in bpy.context.scene.objects:
        raw = obj.get("_vapb_renderer_occurrences")
        if not raw:
            continue
        projection = json.loads(raw)
        if (len(projection.get("records", [])) == 2 and
                (root_context_id is None or obj.get("_vapb_root_context_id") == root_context_id) and
                all(row.get("root_asset_guid") == EXPECTED["pairGuid"]
                    for row in projection["records"])):
            roots.append((obj, projection))
    assert len(roots) == 1, len(roots)
    root, projection = roots[0]
    assert not projection["issues"], projection["issues"]
    records = projection["records"]
    assert len({row["occurrence_id"] for row in records}) == 2
    assert len({row["instance_edge_path"][0]["prefab_instance_file_id"] for row in records}) == 2
    assert all(row["source_key"]["source_asset_guid"] == EXPECTED["sourceGuid"]
               and row["source_key"]["renderer_file_id"] == int(EXPECTED["sourceRendererFileId"])
               and row["mesh"]["mesh_guid"] == EXPECTED["meshGuid"]
               and row["mesh"]["mesh_file_id"] == int(EXPECTED["meshFileId"])
               for row in records)
    source_row, null_row = sorted(records, key=lambda row: row["materials"]["0"] is None)
    assert source_row["materials"]["0"] is not None and null_row["materials"]["0"] is None
    assert all(row["material_slot_count"] == 1 and row["material_status"] == "EXACT"
               for row in records)
    dependencies = load_dependency_registry(bpy.context.scene)["dependencies"]
    scoped = [item for item in dependencies if item.get("consumer_root_context_id") == root["_vapb_root_context_id"]]
    material = [item for item in scoped if item.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"]
    cleared = [item for item in scoped if item.get("dependency_type") == "CLEAR_MATERIAL_SLOT"]
    assert len(material) == len(cleared) == 1
    assert material[0]["consumer_occurrence_id"] == source_row["occurrence_id"]
    assert cleared[0]["consumer_occurrence_id"] == null_row["occurrence_id"]
    source_obj = find_witness_consumer(material[0], bpy.context.scene.objects)
    null_obj = find_witness_consumer(cleared[0], bpy.context.scene.objects)
    assert source_obj is not None and null_obj is not None and source_obj is not null_obj
    assert source_obj.data is null_obj.data
    assert source_obj["_vapb_fbx_realization_id"] != null_obj["_vapb_fbx_realization_id"]
    assert source_obj["_vapb_fbx_source_realization_id"] == null_obj["_vapb_fbx_source_realization_id"]
    assert source_obj["_vapb_fbx_mesh_receipt_id"] == null_obj["_vapb_fbx_mesh_receipt_id"]
    source_template = [obj for obj in bpy.data.objects if
                       obj.get("_vapb_fbx_realization_id") ==
                       source_obj["_vapb_fbx_source_realization_id"]]
    assert len(source_template) == 1 and source_template[0].data is source_obj.data
    assert source_obj.parent is not None and null_obj.parent is not None
    assert source_obj.parent is not null_obj.parent
    semantic_parent = source_obj.parent.parent
    assert semantic_parent is not None and semantic_parent is null_obj.parent.parent
    assert semantic_parent.parent is root
    from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
    pair = parse_prefab(FIXTURES / "Assets" / "Oracle" / "Null_TwoInstances.prefab")
    pair_root, = pair.root_game_objects()
    assert semantic_parent["unity_prefab_file_id"] == str(pair_root.file_id)
    assert source_obj.parent.get("_vapb_model_parent_status") == "EXACT"
    assert null_obj.parent.get("_vapb_model_parent_status") == "EXACT"
    assert len(source_obj.material_slots) == len(null_obj.material_slots) == 1
    assert source_obj.material_slots[0].link == null_obj.material_slots[0].link == "OBJECT"
    base_material = source_obj.material_slots[0].material
    assert base_material is not None
    assert base_material.get("unity_material_guid") == source_row["materials"]["0"]["guid"]
    assert null_obj.material_slots[0].material is None
    # The public raw FBX has no Material. The source Prefab's A is an Object
    # binding, so the shared DATA table must stay at its original None value.
    assert source_obj.data.materials[0] is None
    assert scene_import_outcome(bpy.context.scene)["overall"] == "SUCCESS"
    if renamed:
        assert source_template[0].name == "Renamed Native Source"
        assert source_obj.name == "Renamed Material Occurrence"
        assert null_obj.name == "Renamed Null Occurrence"
        assert base_material.name == "Renamed Material A"
    print("NESTED_NATIVE_COUNTS source=1 occurrences=2 shared_mesh=1 distinct_realization_ids=1")
    print("NESTED_TRANSFORM_OBSERVED", tuple(source_obj.matrix_world.translation),
          tuple(null_obj.matrix_world.translation),
          source_obj.get("_vapb_model_transform_status"),
          null_obj.get("_vapb_model_transform_status"))
    return source_template[0], source_obj, null_obj, base_material


def main():
    values = sys.argv[sys.argv.index("--") + 1:]
    phase, package_text, blend_text = values[:3]
    zip_path = Path(values[3]).resolve() if len(values) > 3 else None
    package, blend = Path(package_text).resolve(), Path(blend_text).resolve()
    assert package.is_file()
    if phase in {"create", "dual-root", "no-witness"}:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    addon = enable_addon(phase, zip_path)
    from unitypackage_blender_importer.blender.dependency_resolver import resolve_scene_dependencies
    if phase in {"create", "dual-root", "no-witness"}:
        with tempfile.TemporaryDirectory(prefix="vapb_nested_witness_") as temp:
            sidecar = Path(temp) / "witness.json"
            choice = create_witness(package, sidecar)
            for _ in range(2 if phase == "dual-root" else 1):
                assert bpy.ops.import_scene.unitypackage(
                    filepath=str(package), import_mode="RECONSTRUCT", prefab_choice=choice,
                    model_witness_path="" if phase == "no-witness" else str(sidecar),
                    keep_extracted=False,
                    source_storage_directory=str(blend.parent / "nested_oracle_sources")) == {"FINISHED"}
        if phase == "no-witness":
            from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome
            roots = [obj for obj in bpy.context.scene.objects if obj.get("_vapb_renderer_occurrences")]
            assert len(roots) == 1
            context_id = roots[0]["_vapb_root_context_id"]
            assert not [obj for obj in bpy.context.scene.objects if obj.type == "MESH"
                        and obj.get("_vapb_root_context_id") == context_id]
            codes = {item["code"] for item in scene_import_outcome(bpy.context.scene)["items"]}
            assert "NULL_MATERIAL_REALIZATION_UNVERIFIED" in codes, codes
            print("NESTED_NO_WITNESS_FAIL_CLOSED_PASS")
            if zip_path:
                assert bpy.ops.preferences.addon_disable(module=PACKAGE_MODULE) == {"FINISHED"}
            else:
                addon.unregister()
            return
        if phase == "dual-root":
            contexts = {obj.get("_vapb_root_context_id") for obj in bpy.context.scene.objects
                        if obj.get("_vapb_renderer_occurrences")}
            assert len(contexts) == 2, contexts
            instances = [check_scene(root_context_id=context) for context in contexts]
            members = [obj for _, source_obj, null_obj, _ in instances
                       for obj in (source_obj, null_obj)]
            assert len({obj["_vapb_fbx_realization_id"] for obj in members}) == 4
            assert len({id(obj) for obj in members}) == 4
            assert len({obj["_vapb_root_context_id"] for obj in members}) == 2
            print("NESTED_TWO_ROOTS_PASS")
            if zip_path:
                assert bpy.ops.preferences.addon_disable(module=PACKAGE_MODULE) == {"FINISHED"}
            else:
                addon.unregister()
            return
        template, source_obj, null_obj, material = check_scene()
        template.name = "Renamed Native Source"
        source_obj.name = "Renamed Material Occurrence"
        null_obj.name = "Renamed Null Occurrence"
        material.name = "Renamed Material A"
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_scene(renamed=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print("NESTED_PACKAGE_CREATE_PASS")
    else:
        assert phase == "reopen"
        check_scene(renamed=True)
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_scene(renamed=True)
        print("NESTED_PACKAGE_REOPEN_PASS")
    if zip_path:
        assert bpy.ops.preferences.addon_disable(module=PACKAGE_MODULE) == {"FINISHED"}
    else:
        addon.unregister()


if __name__ == "__main__":
    main()
