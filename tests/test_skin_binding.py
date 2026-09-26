import copy
import hashlib
import json
import unittest
from types import SimpleNamespace

from unitypackage_blender_importer.blender.fbx_receipt import RECEIPT_VERSION
from unitypackage_blender_importer.blender.renderer_binding import (
    BindingError, make_skin_binding, validate_binding, validate_skin_binding,
)
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity
from unitypackage_blender_importer.tests.test_renderer_binding import FakeObject, fixture


def skin_fixture():
    record, root, owner, mesh = fixture()
    record["renderer_class_id"] = 137
    record["source_revision_sha256"] = "source-rev"
    record["root_revision_sha256"] = "root-rev"
    record["skin"] = {"status": "EXACT", "bones": [
        {"transform_file_id": "-101", "display_name": "Same", "parent_transform_file_id": "0"},
        {"transform_file_id": "-102", "display_name": "Same", "parent_transform_file_id": "-101"}],
        "root_bone_transform_file_id": "-101"}
    record["occurrence_id"] = occurrence_identity(record)
    root["_vapb_renderer_occurrences"] = json.dumps({"records": [record], "issues": []})
    bones = []
    for index in (1, 2):
        bones.append(FakeObject("BONE", f"Bone{index}",
            _vapb_fbx_receipt_version=RECEIPT_VERSION,
            _vapb_fbx_bone_realization_id=f"bone-local-{index}",
            _vapb_fbx_bone_receipt_id="vapb-fbx-bone:" + hashlib.sha256(
                f"{'d' * 32}:{'e' * 64}:{100 + index}".encode()).hexdigest(),
            _vapb_fbx_model_uid=str(100 + index),
            _vapb_fbx_source_asset_guid="d" * 32,
            _vapb_fbx_source_asset_sha256="e" * 64,
            _vapb_fbx_receipt_evidence="OFFICIAL_IMPORTER_BUILD_SKELETON_RETURN"))
    armature = FakeObject("ARMATURE", "Rig", SimpleNamespace(bones=bones),
                          _vapb_root_context_id="root-1", unity_source_package_id="mesh-pkg",
                          _vapb_native_object_id="arm-1")
    mesh.modifiers = [SimpleNamespace(type="ARMATURE", object=armature)]
    objects = [root, owner, mesh, armature]
    mesh["_vapb_renderer_binding"] = json.dumps(validate_binding(record, root, mesh, objects))
    return record, root, mesh, armature, objects


class SkinBindingTests(unittest.TestCase):
    def test_explicit_mapping_survives_rename_and_json_reload(self):
        _, root, mesh, armature, objects = skin_fixture()
        binding = make_skin_binding(mesh, root, objects, {"-101": "Bone1", "-102": "Bone2"})
        self.assertEqual(["-101", "-102"], [row["target_transform_file_id"] for row in binding["mappings"]])
        self.assertNotEqual(binding["mappings"][0]["target_transform_file_id"],
                            binding["mappings"][0]["source_fbx_model_uid"])
        mesh["_vapb_skin_binding"] = json.dumps(binding)
        armature.data.bones[0].name = "Renamed"
        armature.data.bones[1].name = "Renamed too"
        self.assertEqual(binding, validate_skin_binding(mesh, root, objects))

    def test_duplicate_realization_and_stale_receipt_rejected(self):
        _, root, mesh, armature, objects = skin_fixture()
        armature.data.bones[1]["_vapb_fbx_bone_realization_id"] = "bone-local-1"
        with self.assertRaises(BindingError):
            make_skin_binding(mesh, root, objects, {"-101": "Bone1", "-102": "Bone2"})
        armature.data.bones[1]["_vapb_fbx_bone_realization_id"] = "bone-local-2"
        binding = make_skin_binding(mesh, root, objects, {"-101": "Bone1", "-102": "Bone2"})
        mesh["_vapb_skin_binding"] = json.dumps(binding)
        armature.data.bones[0]["_vapb_fbx_bone_receipt_id"] = "changed"
        with self.assertRaisesRegex(BindingError, "receipt"):
            validate_skin_binding(mesh, root, objects)

    def test_projection_or_root_change_rejected(self):
        record, root, mesh, _, objects = skin_fixture()
        mesh["_vapb_skin_binding"] = json.dumps(make_skin_binding(
            mesh, root, objects, {"-101": "Bone1", "-102": "Bone2"}))
        changed = copy.deepcopy(record)
        changed["skin"]["root_bone_transform_file_id"] = "-102"
        root["_vapb_renderer_occurrences"] = json.dumps({"records": [changed], "issues": []})
        with self.assertRaises(BindingError):
            validate_skin_binding(mesh, root, objects)


if __name__ == "__main__":
    unittest.main()
