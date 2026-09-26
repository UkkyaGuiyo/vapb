"""Blender 5.2.1 proof of FBX bone creation receipts across rename and reload."""

from pathlib import Path
import sys
import tempfile

import bpy
from io_scene_fbx.parse_fbx import parse
from io_scene_fbx import import_fbx as native_importer

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.fbx_receipt import import_with_receipts, source_sha256


def make_armature(name):
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bone = data.edit_bones.new("Twin")
    bone.head = (0, 0, 0)
    bone.tail = (0, 0, 1)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def bone_receipts():
    return [bone for armature in bpy.data.armatures for bone in armature.bones
            if "_vapb_fbx_bone_receipt_id" in bone]


def pose_receipts():
    return [bone for obj in bpy.data.objects if obj.type == "ARMATURE"
            for bone in obj.pose.bones if "_vapb_fbx_bone_receipt_id" in bone]


def exported_model_receipts(path):
    root, _ = parse(str(path), use_namedtuple=True)
    objects = next(elem for elem in root.elems if elem.id == b"Objects")
    result = {}
    for model in objects.elems:
        if model.id != b"Model" or model.props[2] != b"LimbNode":
            continue
        props = next((elem for elem in model.elems if elem.id == b"Properties70"), None)
        if props is not None:
            values = {prop.props[0].decode(): prop.props[4].decode()
                      for prop in props.elems if prop.id == b"P" and
                      prop.props[0] in {b"_vapb_fbx_model_uid", b"_vapb_fbx_bone_receipt_id",
                                        b"_vapb_fbx_source_asset_guid", b"_vapb_fbx_source_asset_sha256"}}
            if "_vapb_fbx_model_uid" in values:
                result[values["_vapb_fbx_model_uid"]] = values
    return result


def main():
    with tempfile.TemporaryDirectory(prefix="vapb_bone_receipt_") as directory:
        root = Path(directory)
        fbx = root / "bones.fbx"
        blend = root / "bones.blend"
        bpy.ops.object.select_all(action="DESELECT")
        make_armature("ArmatureA")
        make_armature("ArmatureB")
        bpy.ops.mesh.primitive_cube_add()
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
                                 object_types={"ARMATURE", "MESH"},
                                 add_leaf_bones=False, bake_anim=False)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

        guid = "a" * 32
        helper = native_importer.FbxImportHelperNode
        original_methods = (helper.build_node_obj, helper.build_skeleton,
                            helper.set_pose_matrix_and_custom_props)
        receipts = import_with_receipts(
            fbx,
            lambda: bpy.ops.import_scene.fbx(filepath=str(fbx), use_custom_props=True,
                                             ignore_leaf_bones=False),
            guid,
            bpy,
        )
        assert receipts, "Mesh receipt API regressed"
        assert (helper.build_node_obj, helper.build_skeleton,
                helper.set_pose_matrix_and_custom_props) == original_methods
        def unsupported_bone(self, arm, parent_matrix, settings, parent_bone_size=1,
                             *, addon_parameter=None):
            return original_methods[1](self, arm, parent_matrix, settings, parent_bone_size)

        helper.build_skeleton = unsupported_bone
        try:
            before = set(bpy.data.objects)
            mesh_only = import_with_receipts(
                fbx,
                lambda: bpy.ops.import_scene.fbx(filepath=str(fbx), use_custom_props=True,
                                                 ignore_leaf_bones=False),
                guid,
                bpy,
            )
            assert mesh_only, "unsupported bone signature disabled supported Mesh hook"
            assert helper.build_skeleton is unsupported_bone
            added = [obj for obj in bpy.data.objects if obj not in before]
            assert any(obj.type == "ARMATURE" for obj in added)
            assert all("_vapb_fbx_bone_receipt_id" not in bone
                       for obj in added if obj.type == "ARMATURE" for bone in obj.data.bones)
        finally:
            helper.build_skeleton = original_methods[1]
        bones = bone_receipts()
        assert len(bones) == 2, f"expected two source bone receipts, got {len(bones)}"
        assert len({bone.name for bone in bones}) == 1, "fixture did not retain duplicate bone names"
        assert len({bone["_vapb_fbx_model_uid"] for bone in bones}) == 2
        assert len({bone["_vapb_fbx_bone_receipt_id"] for bone in bones}) == 2
        assert len({bone["_vapb_fbx_bone_realization_id"] for bone in bones}) == 2
        for bone in bones:
            assert bone["_vapb_fbx_source_asset_guid"] == guid
            assert bone["_vapb_fbx_source_asset_sha256"] == source_sha256(fbx)
            assert bone["_vapb_fbx_receipt_evidence"] == "OFFICIAL_IMPORTER_BUILD_SKELETON_RETURN"
        pose_bones = pose_receipts()
        assert len(pose_bones) == 2
        assert {bone["_vapb_fbx_model_uid"]: bone["_vapb_fbx_bone_realization_id"]
                for bone in pose_bones} == {
                    bone["_vapb_fbx_model_uid"]: bone["_vapb_fbx_bone_realization_id"]
                    for bone in bones}
        expected = {bone["_vapb_fbx_model_uid"]: (
            bone["_vapb_fbx_bone_receipt_id"], bone["_vapb_fbx_bone_realization_id"])
            for bone in bones}
        for index, bone in enumerate(bones):
            bone.name = f"Renamed_{index}"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        reopened = bone_receipts()
        assert len(reopened) == 2
        assert {bone["_vapb_fbx_model_uid"]: (
            bone["_vapb_fbx_bone_receipt_id"], bone["_vapb_fbx_bone_realization_id"])
            for bone in reopened} == expected
        assert {bone.name for bone in reopened} == {"Renamed_0", "Renamed_1"}
        assert len(pose_receipts()) == 2
        exported = root / "reexport.fbx"
        bpy.ops.export_scene.fbx(filepath=str(exported), object_types={"ARMATURE", "MESH"},
                                 use_custom_props=True, add_leaf_bones=False, bake_anim=False)
        model_receipts = exported_model_receipts(exported)
        assert set(model_receipts) == set(expected), "Model custom props did not export"
        for uid, values in model_receipts.items():
            assert values["_vapb_fbx_bone_receipt_id"] == expected[uid][0]
            assert values["_vapb_fbx_source_asset_guid"] == guid
            assert values["_vapb_fbx_source_asset_sha256"] == source_sha256(fbx)

        def fail_import():
            raise RuntimeError("intentional import failure")

        try:
            import_with_receipts(fbx, fail_import, guid, bpy)
        except RuntimeError:
            pass
        else:
            raise AssertionError("failure path did not raise")
        assert (helper.build_node_obj, helper.build_skeleton,
                helper.set_pose_matrix_and_custom_props) == original_methods
        print("BONE_RECEIPT_PASS=2 source UID distinct, duplicate names, rename, save/reload, Model export")


if __name__ == "__main__":
    main()
