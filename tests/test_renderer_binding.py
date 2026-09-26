import copy
import json
import unittest
from types import SimpleNamespace

from unitypackage_blender_importer.blender.renderer_binding import (
    BindingError, semantic_owner_id, validate_binding, validate_existing_binding,
)
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity
from unitypackage_blender_importer.blender.fbx_receipt import RECEIPT_VERSION


class FakeObject(dict):
    def __init__(self, kind, name, data=None, **values):
        super().__init__(values)
        self.type = kind
        self.name = name
        self.data = data
        self.modifiers = []


def fixture():
    guid = "a" * 32
    mesh_guid = "b" * 32
    sha = "c" * 64
    record = {
        "root_context_id": "root-1", "root_package_id": "root-pkg",
        "root_member_id": "member", "root_asset_guid": guid,
        "instance_edge_path": [], "source_package_id": "root-pkg",
        "source_key": {"source_asset_guid": guid, "renderer_file_id": -23},
        "renderer_class_id": 23,
        "owner": {"source_asset_guid": guid, "owner_game_object_id": -15},
        "mesh": {"mesh_guid": mesh_guid, "mesh_file_id": 4300000,
                 "source_package_id": "mesh-pkg", "source_sha256": sha},
        "materials": {}, "material_slot_count": 0, "material_status": "EXACT",
    }
    record["occurrence_id"] = occurrence_identity(record)
    root = FakeObject("EMPTY", "Root", _vapb_root_context_id="root-1",
                      _vapb_renderer_occurrences=json.dumps({"records": [record], "issues": []}))
    owner = FakeObject("EMPTY", "Owner", _vapb_root_context_id="root-1",
                       unity_source_package_id="root-pkg",
                       _vapb_semantic_owner_id=semantic_owner_id(record))
    data = FakeObject("DATA", "Mesh data", _vapb_fbx_source_asset_sha256=sha,
                      _vapb_fbx_receipt_version=RECEIPT_VERSION,
                      _vapb_fbx_geometry_uid="42", _vapb_fbx_mesh_receipt_id="mesh-receipt")
    mesh = FakeObject("MESH", "Body", data, _vapb_root_context_id="root-1",
                      unity_source_package_id="mesh-pkg", _vapb_fbx_realization_id="realization-1",
                      _vapb_fbx_receipt_version=RECEIPT_VERSION,
                      _vapb_fbx_source_asset_guid=mesh_guid,
                      _vapb_fbx_source_asset_sha256=sha, _vapb_fbx_geometry_uid="42",
                      _vapb_fbx_mesh_receipt_id="mesh-receipt",
                      _vapb_fbx_model_uid="43", _vapb_fbx_object_receipt_id="object-receipt")
    return record, root, owner, mesh


class RendererBindingTests(unittest.TestCase):
    def test_renames_do_not_affect_identity_or_reload(self):
        record, root, owner, mesh = fixture()
        link = validate_binding(record, root, mesh, [root, owner, mesh])
        mesh["_vapb_renderer_binding"] = json.dumps(link)
        root.name, owner.name, mesh.name = "New root", "New owner", "New mesh"
        self.assertEqual(link, validate_existing_binding(link, root, mesh, [root, owner, mesh]))

    def test_duplicate_realization_rejected(self):
        record, root, owner, mesh = fixture()
        duplicate = copy.deepcopy(mesh)
        with self.assertRaisesRegex(BindingError, "Non-unique"):
            validate_binding(record, root, mesh, [root, owner, mesh, duplicate])

    def test_wrong_root_rejected(self):
        record, root, owner, mesh = fixture()
        mesh["_vapb_root_context_id"] = "different"
        with self.assertRaisesRegex(BindingError, "root context"):
            validate_binding(record, root, mesh, [root, owner, mesh])

    def test_unlisted_or_modified_occurrence_rejected(self):
        record, root, owner, mesh = fixture()
        changed = copy.deepcopy(record)
        changed["root_revision_sha256"] = "unlisted revision"
        with self.assertRaisesRegex(BindingError, "differs from root projection"):
            validate_binding(changed, root, mesh, [root, owner, mesh])

    def test_duplicate_root_context_rejected(self):
        record, root, owner, mesh = fixture()
        other_root = copy.deepcopy(root)
        with self.assertRaisesRegex(BindingError, "Root context is not unique"):
            validate_binding(record, root, mesh, [root, other_root, owner, mesh])

    def test_missing_owner_rejected(self):
        record, root, owner, mesh = fixture()
        with self.assertRaisesRegex(BindingError, "owner missing"):
            validate_binding(record, root, mesh, [root, mesh])

    def test_duplicate_owner_rejected(self):
        record, root, owner, mesh = fixture()
        duplicate = copy.deepcopy(owner)
        with self.assertRaisesRegex(BindingError, "duplicated"):
            validate_binding(record, root, mesh, [root, owner, duplicate, mesh])

    def test_altered_mesh_receipt_rejected(self):
        record, root, owner, mesh = fixture()
        mesh.data["_vapb_fbx_mesh_receipt_id"] = "changed"
        with self.assertRaisesRegex(BindingError, "receipt"):
            validate_binding(record, root, mesh, [root, owner, mesh])

    def test_wrong_mesh_package_rejected(self):
        record, root, owner, mesh = fixture()
        mesh["unity_source_package_id"] = "wrong"
        with self.assertRaisesRegex(BindingError, "package"):
            validate_binding(record, root, mesh, [root, owner, mesh])

    def test_skinned_binding_keeps_armature_identity_separate(self):
        record, root, owner, mesh = fixture()
        record["renderer_class_id"] = 137
        record["occurrence_id"] = occurrence_identity(record)
        root["_vapb_renderer_occurrences"] = json.dumps({"records": [record], "issues": []})
        armature = FakeObject("ARMATURE", "Armature", _vapb_root_context_id="root-1",
                              unity_source_package_id="mesh-pkg", _vapb_native_object_id="arm-1")
        mesh.modifiers = [SimpleNamespace(type="ARMATURE", object=armature)]
        link = validate_binding(record, root, mesh, [root, owner, mesh, armature])
        self.assertEqual("arm-1", link["armature_native_object_id"])
        self.assertNotEqual(link["armature_native_object_id"], link["native_realization_id"])

    def test_distinct_occurrence_needs_distinct_object(self):
        record, root, owner, mesh = fixture()
        link = validate_binding(record, root, mesh, [root, owner, mesh])
        mesh["_vapb_renderer_binding"] = json.dumps(link)
        other = copy.deepcopy(record)
        other["source_key"]["renderer_file_id"] = -24
        other["occurrence_id"] = occurrence_identity(other)
        root["_vapb_renderer_occurrences"] = json.dumps({"records": [record, other], "issues": []})
        with self.assertRaisesRegex(BindingError, "already has"):
            validate_binding(other, root, mesh, [root, owner, mesh])


if __name__ == "__main__":
    unittest.main()
