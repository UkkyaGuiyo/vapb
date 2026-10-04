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
    assert bpy.ops.import_scene.unitypackage(
        filepath=str(package), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        model_witness_path=str(witness), keep_extracted=False,
        source_storage_directory=str(source_store),
        use_materials=use_materials) == {"FINISHED"}


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
        on = run_mode(package, witness, output_dir, "on")
        off = run_mode(package, witness, output_dir, "off")
        assert_close_tree(on, off, "MATERIAL_OPTION_PARITY")
        report = {"fixture": "public unity_shape_probe synthetic Skin/Shape package",
                  "package_sha256": __import__("hashlib").sha256(package.read_bytes()).hexdigest(),
                  "witness_sha256": __import__("hashlib").sha256(witness.read_bytes()).hexdigest(),
                  "materials_on_off_parity": True,
                  "saved_reopen_parity": True,
                  "occurrence_weight_sets": sorted(on["occurrences"])}
        (output_dir / "SkinShapeMaterialOptionResult.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print("SKIN_SHAPE_MATERIAL_ON_OFF_PARITY_PASS", flush=True)
    finally:
        addon.unregister()


if __name__ == "__main__":
    main()
