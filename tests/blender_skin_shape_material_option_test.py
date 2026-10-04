"""Compare witnessed Skin/Shape realization across the Material import option.

Run in Blender 5.2: --python-exit-code 1 --python this_file -- PACKAGE WITNESS NEW_DIR
PACKAGE and WITNESS are the existing public unity_shape_probe outputs. NEW_DIR
must be external to the repository and must not already contain result files.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector


def matrix_values(matrix):
    return [[round(float(matrix[row][column]), 7) for column in range(4)]
            for row in range(4)]


def geometry_snapshot(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = [tuple(round(float(value), 7) for value in
                          (evaluated.matrix_world @ vertex.co))
                    for vertex in mesh.vertices]
        return {"vertices": vertices,
                "polygons": [list(poly.vertices) for poly in mesh.polygons]}
    finally:
        evaluated.to_mesh_clear()


def assert_close_tree(expected, actual, label):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and expected.keys() == actual.keys(), label
        for key in expected:
            assert_close_tree(expected[key], actual[key], label + "." + key)
    elif isinstance(expected, (list, tuple)):
        assert isinstance(actual, (list, tuple)) and len(expected) == len(actual), label
        for index, (left, right) in enumerate(zip(expected, actual)):
            assert_close_tree(left, right, label + "[" + str(index) + "]")
    elif isinstance(expected, int) and not isinstance(expected, bool):
        assert isinstance(actual, int) and expected == actual, (label, expected, actual)
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        tolerance = 2e-5 + 1e-6 * max(abs(float(expected)), abs(float(actual)))
        assert math.isclose(float(expected), float(actual), rel_tol=0.0,
                            abs_tol=tolerance), (label, expected, actual, tolerance)
    else:
        assert expected == actual, (label, expected, actual)


def import_case(package, witness, use_materials, source_store):
    options = {"filepath": str(package), "import_mode": "RECONSTRUCT",
               "prefab_choice": "AUTO", "keep_extracted": False,
               "source_storage_directory": str(source_store),
               "use_materials": use_materials}
    if witness is not None:
        options["model_witness_path"] = str(witness)
    assert bpy.ops.import_scene.unitypackage(**options) == {"FINISHED"}


def scene_records():
    roots = [obj for obj in bpy.context.scene.objects
             if obj.get("_vapb_renderer_occurrences")]
    assert len(roots) == 1, ("EXPECTED_ONE_PUBLIC_SHAPE_ROOT", len(roots))
    payload = roots[0]["_vapb_renderer_occurrences"]
    value = json.loads(payload) if isinstance(payload, str) else payload
    records = [record for record in value["records"]
               if record.get("renderer_class_id") == 137]
    assert len(records) == 2, ("EXPECTED_TWO_SKIN_OCCURRENCES", len(records))
    assert {tuple(record["blend_shape_weights"]) for record in records} == {
        (25.0, 60.0, 0.0), (75.0, 0.0, 35.0)}
    return records


def find_occurrence_mesh(record):
    matches = [obj for obj in bpy.context.scene.objects
               if obj.type == "MESH"
               and obj.get("_vapb_renderer_occurrence_id") == record["occurrence_id"]
               and not obj.get("_vapb_technical_skin_template")]
    assert len(matches) == 1, ("SKIN_OCCURRENCE_OBJECT_AMBIGUOUS",
                               record["occurrence_id"], len(matches))
    return matches[0]


def assert_builtin_preview_resolution(use_materials):
    from unitypackage_blender_importer.blender.dependency_resolver import (
        load_dependency_registry, resolve_after_import)

    if not use_materials:
        registry = load_dependency_registry(bpy.context.scene)
        assert not [record for record in registry["dependencies"]
                    if record.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"], (
            "MATERIALS_OFF_MUST_NOT_CAPTURE_RENDERER_MATERIALS")
        assert not [material for material in bpy.data.materials
                    if material.get("_vapb_builtin_preview_provider")], (
            "MATERIALS_OFF_MUST_NOT_CREATE_BUILTIN_PREVIEW")
        return

    registry = load_dependency_registry(bpy.context.scene)
    records = [record for record in registry["dependencies"]
               if record.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"
               and record.get("target_guid", "").lower() ==
               "0000000000000000f000000000000000"
               and str(record.get("target_file_id", "")) == "10303"]
    assert len(records) == 2, ("EXPECTED_TWO_BUILTIN_MATERIAL_OCCURRENCES", len(records))
    assert all(record.get("status") == "RESOLVED_BUILTIN_PREVIEW"
               and record.get("binding_status") == "BOUND"
               and record.get("resolution_provenance") == "UNITY_BUILTIN_PREVIEW_APPROXIMATE"
               for record in records), ("BUILTIN_PREVIEW_NOT_CLASSIFIED", records)
    assert records[0]["consumer_occurrence_id"] != records[1]["consumer_occurrence_id"]
    assigned = []
    for record in records:
        obj = next(obj for obj in bpy.context.scene.objects
                   if obj.get("_vapb_renderer_occurrence_id") ==
                   record["consumer_occurrence_id"])
        slot = int(record["consumer_slot_index"])
        assert slot < len(obj.material_slots)
        material = obj.material_slots[slot].material
        assert material is not None and material.get("_vapb_builtin_preview_provider") == \
            "UNITY_DEFAULT_MATERIAL"
        assert material.get("_vapb_builtin_preview_guid") == \
            "0000000000000000f000000000000000"
        assert str(material.get("_vapb_builtin_preview_file_id")) == "10303"
        assigned.append((obj, slot, material))
    names_before = {material.name for material in bpy.data.materials
                    if material.get("_vapb_builtin_preview_provider")}
    assert len(names_before) == 1, ("EXPECTED_SHARED_APPROXIMATE_PREVIEW", names_before)
    first_counts = resolve_after_import(bpy.context.scene)
    assert first_counts["builtin_preview_bound"] == 2, first_counts
    assert first_counts["unresolved"] == 0, first_counts
    assert {material.name for material in bpy.data.materials
            if material.get("_vapb_builtin_preview_provider")} == names_before
    for obj, slot, material in assigned:
        assert obj.material_slots[slot].material == material
    from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome
    outcome = scene_import_outcome(bpy.context.scene)
    assert outcome["overall"] == "PARTIAL", outcome
    assert "BUILTIN_PREVIEW_APPROXIMATE" in {
        item["code"] for item in outcome["items"]}, outcome

    # A user edit is occurrence-local and must survive another resolve pass.
    edited_obj, edited_slot, _ = assigned[0]
    user_material = bpy.data.materials.new("Synthetic user slot edit")
    edited_obj.material_slots[edited_slot].link = "OBJECT"
    edited_obj.material_slots[edited_slot].material = user_material
    second_counts = resolve_after_import(bpy.context.scene)
    assert second_counts["user_edit_preserved"] == 1, second_counts
    assert second_counts["builtin_preview_bound"] == 1, second_counts
    assert edited_obj.material_slots[edited_slot].material == user_material
    assert assigned[1][0].material_slots[assigned[1][1]].material == assigned[1][2]
    assert len([material for material in bpy.data.materials
                if material.get("_vapb_builtin_preview_provider")]) == 1

    # Near misses and explicit null stay outside the built-in preview allowlist.
    from unitypackage_blender_importer.blender.dependency_resolver import (
        _is_builtin_preview_reference, capture_dependency)
    from unitypackage_blender_importer.unity.prefab_parser import ref_file_id

    def negative_control(suffix, *, kind="PREFAB_RENDERER_MATERIAL",
                         guid="0000000000000000f000000000000000",
                         file_id=10304, raw_file_id=None):
        control = dict(records[0])
        control.update({"dependency_type": kind, "consumer_slot_index": 17,
                        "target_guid": guid, "target_file_id": str(file_id),
                        "target_file_id_raw": raw_file_id,
                        "consumer_occurrence_id": "synthetic-" + suffix})
        control.pop("initial_slot_state", None)
        control.pop("applied_slot_state", None)
        assert not _is_builtin_preview_reference(control), control
        capture_dependency(bpy.context.scene, control)

    negative_control("wrong-file", file_id=10304, raw_file_id=10304)
    negative_control("wrong-guid", guid="1" * 32, file_id=10303, raw_file_id=10303)
    negative_control("wrong-kind", kind="FBX_EXTERNAL_MATERIAL",
                     file_id=10303, raw_file_id=10303)
    # The existing parser truncates this fractional YAML scalar to 10303.
    # Carrying the raw value into the dependency record keeps the allowlist fail-closed.
    fractional_ref = {"fileID": 10303.9, "guid": "0000000000000000f000000000000000"}
    fractional_record_file_id = ref_file_id(fractional_ref)
    assert fractional_record_file_id == 10303
    negative_control("fractional-file", file_id=fractional_record_file_id,
                     raw_file_id=fractional_ref["fileID"])
    negative_control("ordinary-missing", guid="2" * 32,
                     file_id=2100000, raw_file_id=2100000)
    null_ref = dict(records[0])
    null_ref.update({"consumer_slot_index": 18, "target_guid": "", "target_file_id": "0",
                     "target_file_id_raw": 0})
    null_ref["consumer_occurrence_id"] = "synthetic-explicit-null-control"
    capture_dependency(bpy.context.scene, null_ref)
    result = resolve_after_import(bpy.context.scene)
    final = load_dependency_registry(bpy.context.scene)
    null_row = next(row for row in final["dependencies"]
                    if row.get("consumer_occurrence_id") == "synthetic-explicit-null-control")
    negative_rows = [row for row in final["dependencies"]
                     if str(row.get("consumer_occurrence_id", "")).startswith("synthetic-")]
    assert len(negative_rows) == 6, negative_rows
    assert all(row["status"] == "UNRESOLVED" for row in negative_rows), negative_rows
    assert null_row["status"] == "UNRESOLVED", null_row
    assert result["builtin_preview_bound"] == 1, result
    print("BUILTIN_PREVIEW_BOUNDARY_PASS", flush=True)


def assert_builtin_preview_after_reopen(use_materials):
    from unitypackage_blender_importer.blender.dependency_resolver import (
        load_dependency_registry, resolve_after_import)
    registry = load_dependency_registry(bpy.context.scene)
    rows = [row for row in registry["dependencies"]
            if row.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"
            and row.get("target_guid", "").lower() ==
            "0000000000000000f000000000000000"
            and str(row.get("target_file_id", "")) == "10303"
            and type(row.get("target_file_id_raw")) is int
            and row.get("target_file_id_raw") == 10303]
    previews = [material for material in bpy.data.materials
                if material.get("_vapb_builtin_preview_provider") == "UNITY_DEFAULT_MATERIAL"]
    if not use_materials:
        assert not rows and not previews, (rows, previews)
        return
    assert len(rows) == 2 and len(previews) == 1, (len(rows), len(previews))
    assert sorted(row["status"] for row in rows) == [
        "RESOLVED_BUILTIN_PREVIEW", "USER_EDIT_PRESERVED"]
    fractional = next(row for row in registry["dependencies"]
                      if row.get("consumer_occurrence_id") == "synthetic-fractional-file")
    assert fractional["status"] == "UNRESOLVED", fractional
    before = {obj.name: [(slot.link, slot.material.name if slot.material else None)
                         for slot in obj.material_slots]
              for obj in bpy.context.scene.objects
              if obj.get("_vapb_renderer_occurrence_id")}
    counts = resolve_after_import(bpy.context.scene)
    assert counts["builtin_preview_bound"] == 1
    assert counts["user_edit_preserved"] == 1
    assert len([material for material in bpy.data.materials
                if material.get("_vapb_builtin_preview_provider") == "UNITY_DEFAULT_MATERIAL"]) == 1
    after = {obj.name: [(slot.link, slot.material.name if slot.material else None)
                        for slot in obj.material_slots]
             for obj in bpy.context.scene.objects
             if obj.get("_vapb_renderer_occurrence_id")}
    assert before == after, (before, after)
    from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome
    outcome = scene_import_outcome(bpy.context.scene)
    assert outcome["overall"] == "PARTIAL"
    assert "BUILTIN_PREVIEW_APPROXIMATE" in {
        item["code"] for item in outcome["items"]}


def assert_builtin_preview_candidate_safety():
    import json
    from unitypackage_blender_importer.blender.dependency_resolver import (
        BUILTIN_PREVIEW_FILE_ID, BUILTIN_PREVIEW_GUID, BUILTIN_PREVIEW_MARKER,
        SCENE_DEPENDENCY_REGISTRY, _builtin_preview_material, resolve_scene_dependencies)

    def make_candidate(name, *, approximate):
        material = bpy.data.materials.new(name)
        material[BUILTIN_PREVIEW_MARKER] = "UNITY_DEFAULT_MATERIAL"
        material["_vapb_builtin_preview_guid"] = BUILTIN_PREVIEW_GUID
        material["_vapb_builtin_preview_file_id"] = BUILTIN_PREVIEW_FILE_ID
        if approximate:
            material["_vapb_builtin_preview_approximate"] = True
        return material

    def make_scene():
        scene = bpy.data.scenes.new("Synthetic built-in preview candidate check")
        scene[SCENE_DEPENDENCY_REGISTRY] = json.dumps({"schema_version": 1, "dependencies": [{
            "dependency_type": "PREFAB_RENDERER_MATERIAL",
            "target_guid": BUILTIN_PREVIEW_GUID,
            "target_file_id": BUILTIN_PREVIEW_FILE_ID,
            "target_file_id_raw": 10303,
            "consumer_slot_index": 0,
        }]})
        return scene

    candidates = []
    scenes = []
    try:
        candidates.extend((make_candidate("Synthetic duplicate A", approximate=True),
                          make_candidate("Synthetic duplicate B", approximate=True)))
        assert _builtin_preview_material() is None
        ambiguous_scene = make_scene()
        scenes.append(ambiguous_scene)
        counts = resolve_scene_dependencies(ambiguous_scene)
        record = json.loads(ambiguous_scene[SCENE_DEPENDENCY_REGISTRY])["dependencies"][0]
        assert counts["ambiguous"] == 1 and record["status"] == "AMBIGUOUS_PROVIDER", (counts, record)
        for material in candidates:
            bpy.data.materials.remove(material)
        candidates.clear()
        candidates.append(make_candidate("Synthetic incomplete candidate", approximate=False))
        assert _builtin_preview_material() is None
        incomplete_scene = make_scene()
        scenes.append(incomplete_scene)
        counts = resolve_scene_dependencies(incomplete_scene)
        record = json.loads(incomplete_scene[SCENE_DEPENDENCY_REGISTRY])["dependencies"][0]
        assert counts["unresolved"] == 1 and record["status"] == "UNSUPPORTED", (counts, record)
        print("BUILTIN_PREVIEW_CANDIDATE_SAFETY_PASS", flush=True)
    finally:
        for scene in scenes:
            bpy.data.scenes.remove(scene)
        for material in candidates:
            bpy.data.materials.remove(material)


def snapshot(witness, records):
    from unitypackage_blender_importer.blender.fbx_receipt import validate_shape_receipts

    result = {}
    for record in records:
        mesh = find_occurrence_mesh(record)
        guid = record["mesh"]["mesh_guid"]
        mesh_id = int(record["mesh"]["mesh_file_id"])
        row = witness.mesh(guid, mesh_id)
        assert row is not None and row.shape_channels and row.bone_model_uids
        mapped = validate_shape_receipts(
            mesh.data, witness.source_shas[guid], row.geometry_uid)
        expected = record["blend_shape_weights"]
        channel_values = []
        for index, channel_uid, _shape_uid in row.shape_channels:
            key = mapped[channel_uid]
            value = round(float(key.value), 7)
            assert abs(value - float(expected[index]) / 100.0) <= 1e-6, (
                "SHAPE_WEIGHT_MISMATCH", index, value, expected[index])
            channel_values.append([int(channel_uid), value])
        assert sum(value > 0 for _, value in channel_values) >= 2
        modifiers = [modifier for modifier in mesh.modifiers
                     if modifier.type == "ARMATURE" and modifier.object]
        assert len(modifiers) == 1, ("SKIN_ARMATURE_MISSING", mesh.name)
        rig = modifiers[0].object
        bone_matrices = []
        for model_uid in row.bone_model_uids:
            matches = [bone for bone in rig.pose.bones
                       if str(bone.bone.get("_vapb_fbx_model_uid", "")) == str(model_uid)]
            assert len(matches) == 1, ("SKIN_BONE_RECEIPT_MISSING", model_uid)
            bone_matrices.append([int(model_uid), matrix_values(matches[0].matrix)])
        key = ",".join(str(float(value)) for value in expected)
        result[key] = {"weights": channel_values,
                       "geometry": geometry_snapshot(mesh),
                       "bones": bone_matrices}
    assert len(result) == 2
    return result


def realize_attachment_and_pose(records, witness):
    spine_uid = int(witness.mesh(records[0]["mesh"]["mesh_guid"],
                                 records[0]["mesh"]["mesh_file_id"]).bone_model_uids[-1])
    carriers = [obj for obj in bpy.context.scene.objects
                if str(obj.get("_vapb_skin_bone_model_uid", "")) == str(spine_uid)
                and any(constraint.type == "COPY_TRANSFORMS" for constraint in obj.constraints)]
    assert len(carriers) == 1, ("SPINE_SEMANTIC_CARRIER_MISSING", len(carriers))
    carrier = carriers[0]
    attachments = [obj for obj in bpy.context.scene.objects
                   if obj.get("_vapb_material_option_test_attachment")]
    if not attachments:
        attachment = bpy.data.objects.new("Synthetic Spine Attachment", None)
        bpy.context.scene.collection.objects.link(attachment)
        attachment.parent = carrier
        attachment.location = Vector((0.23, 0.11, 0.17))
        attachment["_vapb_material_option_test_attachment"] = True
    else:
        assert len(attachments) == 1
        attachment = attachments[0]
    rigs = {modifier.object for obj in bpy.context.scene.objects if obj.type == "MESH"
            and obj.get("_vapb_renderer_occurrence_id")
            for modifier in obj.modifiers if modifier.type == "ARMATURE" and modifier.object}
    bones = [(rig, bone) for rig in rigs for bone in rig.pose.bones
             if str(bone.bone.get("_vapb_fbx_model_uid", "")) == str(spine_uid)]
    assert len(bones) == 1, ("SPINE_POSE_BONE_AMBIGUOUS", len(bones))
    rig, bone = bones[0]
    bpy.context.view_layer.update()
    before = attachment.matrix_world.copy()
    bone_world_before = rig.matrix_world @ bone.matrix
    original_mode = bone.rotation_mode
    original_rotation = bone.rotation_quaternion.copy()
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion((0.0, 0.0, 1.0), 0.2) @ original_rotation
    bpy.context.view_layer.update()
    after = attachment.matrix_world.copy()
    bone_world_after = rig.matrix_world @ bone.matrix
    movement = max(abs(after[row][column] - before[row][column])
                   for row in range(4) for column in range(4))
    assert movement > 0.01, ("SPINE_ATTACHMENT_DID_NOT_MOVE", movement)
    expected = (bone_world_after @ bone_world_before.inverted()) @ before
    error = max(abs(after[row][column] - expected[row][column])
                for row in range(4) for column in range(4))
    scale = max(abs(value) for matrix in (after, expected)
                for row in matrix for value in row)
    tolerance = 2e-5 + 1e-6 * scale
    assert error <= tolerance, ("SPINE_ATTACHMENT_DELTA_MISMATCH", error, tolerance)
    return attachment, bone, original_mode, original_rotation


def run_mode(package, witness_path, output_dir, mode):
    use_materials = mode == "on"
    blend = output_dir / ("materials_" + mode + ".blend")
    source_store = output_dir / ("sources_" + mode)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_case(package, witness_path, use_materials, source_store)
    assert_builtin_preview_resolution(use_materials)
    witness = load_witness(package, witness_path, output_dir)
    records = scene_records()
    baseline = snapshot(witness, records)
    attachment, bone, original_mode, original_rotation = realize_attachment_and_pose(records, witness)
    posed = snapshot(witness, records)
    assert all(posed[key]["geometry"] != baseline[key]["geometry"] for key in posed), (
        "POSE_DID_NOT_CHANGE_EVALUATED_GEOMETRY", mode)
    before_save = {"occurrences": posed,
                   "attachment": matrix_values(attachment.matrix_world),
                   "spine_pose": matrix_values(bone.matrix)}
    assert bpy.ops.wm.save_as_mainfile(filepath=str(blend)) == {"FINISHED"}
    assert bpy.ops.wm.open_mainfile(filepath=str(blend)) == {"FINISHED"}
    assert_builtin_preview_after_reopen(use_materials)
    witness = load_witness(package, witness_path, output_dir)
    records = scene_records()
    attachments = [obj for obj in bpy.context.scene.objects
                   if obj.get("_vapb_material_option_test_attachment")]
    assert len(attachments) == 1
    rigs = {modifier.object for record in records for modifier in find_occurrence_mesh(record).modifiers
            if modifier.type == "ARMATURE" and modifier.object}
    bones = [bone for rig in rigs for bone in rig.pose.bones
             if str(bone.bone.get("_vapb_fbx_model_uid", "")) ==
             str(witness.mesh(records[0]["mesh"]["mesh_guid"],
                              records[0]["mesh"]["mesh_file_id"]).bone_model_uids[-1])]
    assert len(bones) == 1
    after_reopen = {"occurrences": snapshot(witness, records),
                    "attachment": matrix_values(attachments[0].matrix_world),
                    "spine_pose": matrix_values(bones[0].matrix)}
    assert_close_tree(before_save, after_reopen, "SKIN_SHAPE_STATE_" + mode)
    print("SKIN_SHAPE_MATERIAL_OPTION_PASS mode=" + mode, flush=True)
    return before_save


def load_witness(package, witness_path, output_dir):
    from unitypackage_blender_importer.unity.model_identity_witness import load_model_witness
    from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
    from unitypackage_blender_importer.unity.asset_database import AssetDatabase
    import hashlib
    import tempfile

    with tempfile.TemporaryDirectory(prefix="witness-cache-", dir=str(output_dir)) as temp:
        root = Path(temp)
        extraction = UnityPackageReader(package).extract(root / "package")
        database = AssetDatabase.from_extraction(extraction.root, extraction.assets)
        return load_model_witness(witness_path,
            hashlib.sha256(package.read_bytes()).hexdigest(), database)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise ValueError("PACKAGE_WITNESS_AND_NEW_EVIDENCE_DIRECTORY_REQUIRED")
    package, witness, output_dir = (Path(value).resolve() for value in args)
    repo = Path(__file__).resolve().parents[1]
    if (not package.is_file() or not witness.is_file() or output_dir.exists()
            or output_dir == repo or repo in output_dir.parents):
        raise ValueError("PUBLIC_EXTERNAL_FIXTURE_AND_NEW_EVIDENCE_DIRECTORY_REQUIRED")
    output_dir.mkdir(parents=True)
    addon_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(addon_path))
    import unitypackage_blender_importer as addon
    addon.register()
    try:
        assert_builtin_preview_candidate_safety()
        on = run_mode(package, witness, output_dir, "on")
        off = run_mode(package, witness, output_dir, "off")
        assert_close_tree(on, off, "MATERIAL_OPTION_PARITY")
        report = {"fixture": "public unity_shape_probe synthetic Skin/Shape package",
                  "package_sha256": __import__("hashlib").sha256(package.read_bytes()).hexdigest(),
                  "witness_sha256": __import__("hashlib").sha256(witness.read_bytes()).hexdigest(),
                  "materials_on_off_parity": True,
                  "saved_reopen_parity": True,
                  "builtin_preview": {
                      "dependency_type": "PREFAB_RENDERER_MATERIAL",
                      "target_guid": "0000000000000000f000000000000000",
                      "target_file_id": 10303,
                      "status": "RESOLVED_BUILTIN_PREVIEW",
                      "resolution_provenance": "UNITY_BUILTIN_PREVIEW_APPROXIMATE",
                      "bound_occurrences": 2,
                      "unique_preview_materials": 1,
                      "repeat_resolution": True,
                      "saved_reopen": True,
                      "user_edit_preserved": True,
                      "materials_off_creates_no_preview": True,
                      "negative_controls": ["wrong_file_id", "wrong_guid", "wrong_dependency_type",
                                            "fractional_raw_file_id", "ordinary_missing_provider",
                                            "explicit_null"],
                      "scene_import_outcome": "PARTIAL",
                      "optional_model_witness_used_for_exact_occurrence_mapping": True,
                  },
                  "occurrence_weight_sets": sorted(on["occurrences"])}
        (output_dir / "SkinShapeMaterialOptionResult.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print("SKIN_SHAPE_MATERIAL_ON_OFF_PARITY_PASS", flush=True)
    finally:
        addon.unregister()


if __name__ == "__main__":
    main()
