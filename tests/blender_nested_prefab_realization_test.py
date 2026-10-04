"""Unity-authored public repeated Prefab through the normal package operator."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import bpy


FIXTURES = Path(__file__).with_name("unity_alias_oracle")
TRANSFORM_ORACLE = os.environ.get("VAPB_TRANSFORM_ORACLE") == "1"
EXPECTED = json.loads((FIXTURES / ("transform_expected.json" if TRANSFORM_ORACLE else
                                  "null_pair_expected.json")).read_text(encoding="utf-8"))
PAIR_FILE = "Transform_TwoInstances.prefab" if TRANSFORM_ORACLE else "Null_TwoInstances.prefab"
SOURCE_FILE = "Transform_Source.prefab" if TRANSFORM_ORACLE else "Null_Source.prefab"
MAPPING = json.loads((FIXTURES / "null_fbx_witness_mapping.json").read_text(encoding="utf-8"))
REPORT = json.loads((FIXTURES / "null_fbx_witness_result.json").read_text(encoding="utf-8"))
GEOMETRY = json.loads((FIXTURES / "geometry_expected.json").read_text(encoding="utf-8"))
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
            FIXTURES / "Assets" / "Oracle" / PAIR_FILE)
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


def world_geometry_error(obj, unity_flat, world_override=None):
    """Compare independent Unity/Blender evaluated point sets without vertex indices."""
    from mathutils import Vector

    unity_points = [Vector((-unity_flat[i], -unity_flat[i + 2], unity_flat[i + 1]))
                    for i in range(0, len(unity_flat), 3)]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        world = world_override if world_override is not None else evaluated.matrix_world
        blender_points = [world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

    def distinct(points):
        unique = []
        for point in points:
            if not any((point - prior).length < 1e-7 for prior in unique):
                unique.append(point)
        return unique

    left, right = distinct(unity_points), distinct(blender_points)
    assert len(left) == len(right) == 8, (len(left), len(right))
    return max(max(min((point - other).length for other in right) for point in left),
               max(min((point - other).length for other in left) for point in right))


def check_scene(renamed=False, root_context_id=None, materials_enabled=True):
    from unitypackage_blender_importer.blender.dependency_resolver import load_dependency_registry
    from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome
    from unitypackage_blender_importer.blender.model_witness_bridge import find_witness_consumer
    if TRANSFORM_ORACLE:
        from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
        source_prefab = parse_prefab(FIXTURES / "Assets" / "Oracle" / SOURCE_FILE)
        EXPECTED["sourceRendererFileId"] = str(source_prefab.renderer_documents()[0].file_id)

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
    assert len(material) == len(cleared) == (1 if materials_enabled else 0)
    if materials_enabled:
        assert material[0]["consumer_occurrence_id"] == source_row["occurrence_id"]
        assert cleared[0]["consumer_occurrence_id"] == null_row["occurrence_id"]
        source_obj = find_witness_consumer(material[0], bpy.context.scene.objects)
        null_obj = find_witness_consumer(cleared[0], bpy.context.scene.objects)
    else:
        source_obj = next(obj for obj in bpy.context.scene.objects
                          if obj.get("_vapb_renderer_occurrence_id") == source_row["occurrence_id"])
        null_obj = next(obj for obj in bpy.context.scene.objects
                        if obj.get("_vapb_renderer_occurrence_id") == null_row["occurrence_id"])
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
    pair = parse_prefab(FIXTURES / "Assets" / "Oracle" / PAIR_FILE)
    pair_root, = pair.root_game_objects()
    assert semantic_parent["unity_prefab_file_id"] == str(pair_root.file_id)
    assert source_obj.parent.get("_vapb_model_parent_status") == "EXACT"
    assert null_obj.parent.get("_vapb_model_parent_status") == "EXACT"
    if materials_enabled:
        assert len(source_obj.material_slots) == len(null_obj.material_slots) == 1
    else:
        assert len(source_obj.material_slots) == len(null_obj.material_slots)
    if materials_enabled:
        assert source_obj.material_slots[0].link == null_obj.material_slots[0].link == "OBJECT"
        base_material = source_obj.material_slots[0].material
        assert base_material is not None
        assert base_material.get("unity_material_guid") == source_row["materials"]["0"]["guid"]
        assert null_obj.material_slots[0].material is None
    else:
        base_material = None
        assert all(slot.material is None for obj in (source_obj, null_obj) for slot in obj.material_slots)
    # The public raw FBX has no Material. The source Prefab's A is an Object
    # binding, so the shared DATA table must stay at its original None value.
    assert all(material is None for material in source_obj.data.materials)
    outcome = scene_import_outcome(bpy.context.scene)
    assert outcome["overall"] == ("SUCCESS" if materials_enabled else "PARTIAL"), outcome
    assert "NESTED_PREFAB_RENDERER_NOT_REALIZED" not in {
        item["code"] for item in outcome["items"]}, outcome
    from unitypackage_blender_importer.blender.fbx_receipt import copy_with_receipt, validate_receipt_continuity
    if validate_receipt_continuity(source_obj):
        duplicate = copy_with_receipt(source_obj)
        duplicate.parent = source_obj.parent
        bpy.context.scene.collection.objects.link(duplicate)
        ambiguous = scene_import_outcome(bpy.context.scene)
        assert "NESTED_PREFAB_RENDERER_NOT_REALIZED" in {
            item["code"] for item in ambiguous["items"]}, ambiguous
        bpy.data.objects.remove(duplicate, do_unlink=True)
        assert scene_import_outcome(bpy.context.scene)["overall"] == (
            "SUCCESS" if materials_enabled else "PARTIAL")
    if TRANSFORM_ORACLE:
        source_obj["_vapb_geometry_frame_status"] = "UNVERIFIED"
        uncertain = scene_import_outcome(bpy.context.scene)
        assert uncertain["overall"] == "PARTIAL"
        assert "DIRECT_MESH_GEOMETRY_FRAME_UNVERIFIED" in {
            item["code"] for item in uncertain["items"]}
        source_obj["_vapb_geometry_frame_status"] = "EXACT"
        assert scene_import_outcome(bpy.context.scene)["overall"] == (
            "SUCCESS" if materials_enabled else "PARTIAL")
    from mathutils import Matrix
    from unitypackage_blender_importer.blender.hierarchy_builder import unity_position
    bpy.context.view_layer.update()
    native = source_template[0].matrix_world.copy()
    assert (GEOMETRY["meshGuid"] == EXPECTED["meshGuid"]
            and GEOMETRY["meshFileId"] == EXPECTED["meshFileId"])
    assert GEOMETRY["importerUseFileScale"] and not GEOMETRY["importerBakeAxisConversion"]
    scale = GEOMETRY["importerFileScale"] * GEOMETRY["importerGlobalScale"]
    assert abs(scale - 0.01) < 1e-7
    direct_mesh_frame = Matrix(((scale, 0, 0, 0), (0, 0, -scale, 0),
                                (0, scale, 0, 0), (0, 0, 0, 1)))
    # The native FBX source Object still carries its own Model placement.
    # These source Prefabs reference only its Mesh subasset, so the member
    # local frame is the verified Mesh unit/axis conversion instead.
    assert max(abs(native[i][j] - Matrix.Translation((-1.5, 0, 0))[i][j])
               for i in range(4) for j in range(4)) < 1e-5
    if TRANSFORM_ORACLE:
        from unitypackage_blender_importer.blender.direct_mesh_frame import verified_direct_mesh_frame

        model_path = FIXTURES / "Assets" / "Oracle" / "Model.fbx"
        meta_text = Path(str(model_path) + ".meta").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="vapb_frame_negative_") as temp:
            candidate = Path(temp) / "Model.fbx"
            candidate.write_bytes(model_path.read_bytes())
            meta = Path(str(candidate) + ".meta")
            meta.write_text(meta_text, encoding="utf-8")
            assert verified_direct_mesh_frame(candidate, source_template[0]) is not None
            for old, new in (("    useFileScale: 1", "    useFileScale: 0"),
                             ("    bakeAxisConversion: 0", "    bakeAxisConversion: 1"),
                             ("    globalScale: 1", "    globalScale: 2")):
                assert old in meta_text
                meta.write_text(meta_text.replace(old, new, 1), encoding="utf-8")
                assert verified_direct_mesh_frame(candidate, source_template[0]) is None
    if TRANSFORM_ORACLE:
        basis = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        def converted(values):
            matrix = Matrix(tuple(tuple(values[row * 4 + col] for col in range(4))
                                  for row in range(4)))
            return basis @ matrix @ basis.inverted()
        expected_parent = converted(EXPECTED["parentLocal"])
        assert max(abs(semantic_parent.matrix_world[i][j] - expected_parent[i][j])
                   for i in range(4) for j in range(4)) < 1e-5
        cases = ((source_obj, converted(EXPECTED["aLocal"]), converted(EXPECTED["aWorld"])),
                 (null_obj, converted(EXPECTED["bLocal"]), converted(EXPECTED["bWorld"])))
    else:
        cases = tuple((member, Matrix.Translation(unity_position(position)), None)
                      for member, position in ((source_obj, EXPECTED["materialALocalPosition"]),
                                               (null_obj, EXPECTED["nullLocalPosition"])))
    for member, instance_local, unity_world in cases:
        expected_world = ((unity_world if unity_world is not None else
                           semantic_parent.matrix_world @ instance_local) @ direct_mesh_frame)
        local_error = max(abs(member.parent.matrix_local[i][j] - instance_local[i][j])
                          for i in range(4) for j in range(4))
        member_local_error = max(abs(member.matrix_local[i][j] - direct_mesh_frame[i][j])
                                 for i in range(4) for j in range(4))
        world_error = max(abs(member.matrix_world[i][j] - expected_world[i][j])
                          for i in range(4) for j in range(4))
        print("NESTED_MATRIX_ERROR", local_error, member_local_error, world_error)
        assert local_error < 1e-5 and member_local_error < 1e-5 and world_error < 1e-5
        assert member.get("_vapb_geometry_frame_status") == "EXACT"
    if TRANSFORM_ORACLE:
        assert (GEOMETRY["unityVersion"] == EXPECTED["unityVersion"]
                and GEOMETRY["pairGuid"] == EXPECTED["pairGuid"]
                and GEOMETRY["meshGuid"] == EXPECTED["meshGuid"]
                and GEOMETRY["meshFileId"] == EXPECTED["meshFileId"])
        for member, values in ((source_obj, GEOMETRY["aWorldVertices"]),
                               (null_obj, GEOMETRY["bWorldVertices"])):
            error = world_geometry_error(member, values)
            print("NESTED_WORLD_GEOMETRY_ERROR", error)
            assert error < 1e-5
            # Independent Unity points must reject missing instance placement,
            # doubled native FBX Model placement, and omitted file-unit scale.
            assert world_geometry_error(
                member, values, semantic_parent.matrix_world @ direct_mesh_frame) > 0.1
            assert world_geometry_error(
                member, values, member.parent.matrix_world @ native @ direct_mesh_frame) > 0.1
            assert world_geometry_error(
                member, values, member.parent.matrix_world @
                direct_mesh_frame @ Matrix.Scale(100, 4)) > 0.1
    if renamed and materials_enabled:
        assert source_template[0].name == "Renamed Native Source"
        assert source_obj.name == "Renamed Material Occurrence"
        assert null_obj.name == "Renamed Null Occurrence"
        assert base_material.name == "Renamed Material A"
    print("NESTED_NATIVE_COUNTS source=1 occurrences=2 shared_mesh=1 distinct_realization_ids=2")
    print("NESTED_TRANSFORM_OBSERVED", tuple(source_obj.matrix_world.translation),
          tuple(null_obj.matrix_world.translation),
          source_obj.get("_vapb_model_transform_status"),
          null_obj.get("_vapb_model_transform_status"))
    return source_template[0], source_obj, null_obj, base_material


def main():
    values = sys.argv[sys.argv.index("--") + 1:]
    phase, package_text, blend_text = values[:3]
    zip_path = Path(values[3]).resolve() if len(values) > 3 and values[3] != "-" else None
    materials_enabled = not (len(values) > 4 and values[4] == "off")
    snapshot_path = Path(values[5]).resolve() if len(values) > 5 else None
    baseline_snapshot_path = Path(values[6]).resolve() if len(values) > 6 else None
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
                    keep_extracted=False, use_materials=materials_enabled,
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
            assert "NESTED_PREFAB_RENDERER_NOT_REALIZED" in codes, codes
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
        template, source_obj, null_obj, material = check_scene(materials_enabled=materials_enabled)
        if materials_enabled:
            template.name = "Renamed Native Source"
            source_obj.name = "Renamed Material Occurrence"
            null_obj.name = "Renamed Null Occurrence"
            material.name = "Renamed Material A"
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_scene(renamed=materials_enabled, materials_enabled=materials_enabled)
        if snapshot_path:
            bpy.context.view_layer.update()
            snapshot = {}
            for label, obj in (("material_source", source_obj), ("null_source", null_obj)):
                evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
                mesh = evaluated.to_mesh()
                try:
                    points = sorted(tuple(round(float(value), 8) for value in (evaluated.matrix_world @ vertex.co))
                                    for vertex in mesh.vertices)
                    snapshot[label] = {"points": points,
                                       "polygons": [list(poly.vertices) for poly in mesh.polygons]}
                finally:
                    evaluated.to_mesh_clear()
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            if baseline_snapshot_path:
                baseline = json.loads(baseline_snapshot_path.read_text(encoding="utf-8"))
                assert json.dumps(snapshot, sort_keys=True) == json.dumps(baseline, sort_keys=True), {
                    "reason": "Material ON/OFF evaluated geometry differs",
                    "materials_enabled": materials_enabled,
                    "baseline": baseline,
                    "actual": snapshot,
                }
                print("NESTED_MATERIAL_OPTION_GEOMETRY_PARITY_PASS", flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print("NESTED_PACKAGE_CREATE_PASS")
    else:
        assert phase == "reopen"
        check_scene(renamed=materials_enabled, materials_enabled=materials_enabled)
        resolve_scene_dependencies(bpy.context.scene)
        resolve_scene_dependencies(bpy.context.scene)
        check_scene(renamed=materials_enabled, materials_enabled=materials_enabled)
        print("NESTED_PACKAGE_REOPEN_PASS")
    if zip_path:
        assert bpy.ops.preferences.addon_disable(module=PACKAGE_MODULE) == {"FINISHED"}
    else:
        addon.unregister()


if __name__ == "__main__":
    main()
