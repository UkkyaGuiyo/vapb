"""Public synthetic occurrence-to-native joins; names never identify objects."""

import copy
import json
import unittest
from unittest import mock
from dataclasses import replace
from types import SimpleNamespace

from unitypackage_blender_importer.blender.fbx_receipt import FbxModelLink, RawFbxSemanticIndex
from unitypackage_blender_importer.blender.model_witness_bridge import (
    plan_witness_realizations, plan_witness_material_dependencies,
    find_witness_consumer,
    plan_witness_skin_carriers,
)
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelAssetRevision, validate_model_witness,
)
from unitypackage_blender_importer.unity.import_outcome import summarize_import_outcome
from unitypackage_blender_importer.unity.occurrence_projection import occurrence_identity


GUID = "a" * 32
FBX_SHA = "b" * 64
META_SHA = "c" * 64
PACKAGE_SHA = "d" * 64


class Data(dict):
    def __init__(self):
        super().__init__()
        self.materials = []


class Object(dict):
    def __init__(self, *args, obj_type="MESH", **kwargs):
        super().__init__(*args, **kwargs)
        self.type = obj_type
        self.data = Data()


def witness():
    doc = {"schema_version": "vapb-model-identity-witness-v1",
           "source_unitypackage_sha256": PACKAGE_SHA,
           "unity_version": "2022.3.22f1",
           "source_validation": {"probe_pass": True, "original_revision_equivalent": True},
           "assets": [{"asset_guid": GUID, "source_fbx_sha256": FBX_SHA,
                       "source_meta_sha256": META_SHA,
                       "models": [{"model_uid": "101", "geometry_uid": "202",
                                   "transform_local_id": "-303", "game_object_local_id": "-404",
                                   "renderers": [{"class_id": 137,
                                                  "renderer_local_id": "-505",
                                                  "mesh_local_id": "-606"}]}]}]}
    revisions = {GUID: ModelAssetRevision(
        FBX_SHA, META_SHA, RawFbxSemanticIndex([FbxModelLink(101, 202)], [101]))}
    return validate_model_witness(doc, PACKAGE_SHA, revisions)


def record(edge=(), material="e" * 32):
    value = {"root_context_id": "root-one", "root_package_id": "pkg",
             "root_member_id": "root-member", "root_asset_guid": "f" * 32,
             "instance_edge_path": list(edge), "source_package_id": "pkg",
             "source_key": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": "f" * 32,
                            "renderer_file_id": -22},
             "renderer_class_id": 137,
             "owner": {"source_kind": "PREFAB_LOCAL", "source_asset_guid": "f" * 32,
                       "owner_game_object_id": -11},
             "mesh": {"mesh_guid": GUID, "mesh_file_id": -606,
                      "source_package_id": "pkg", "source_sha256": FBX_SHA},
             "materials": {0: {"guid": material, "file_id": 2100000,
                                "raw_file_id": 2100000, "source_package_id": "pkg"}},
             "material_slot_count": 1, "material_status": "EXACT"}
    value["occurrence_id"] = occurrence_identity(value)
    return value


def model_record(edge=(), material="e" * 32):
    value = record(edge, material)
    value["source_key"] = {"source_kind": "MODEL_SOURCE",
                           "source_asset_guid": GUID, "renderer_file_id": -505}
    value["owner"] = {"source_kind": "MODEL_SOURCE",
                      "source_asset_guid": GUID, "owner_game_object_id": -404}
    value["occurrence_id"] = occurrence_identity(value)
    return value


def native(edge=(), realization="native-one"):
    value = Object(_vapb_root_context_id="root-one", unity_source_package_id="pkg",
                   _vapb_fbx_source_asset_guid=GUID,
                   _vapb_fbx_source_asset_sha256=FBX_SHA,
                   _vapb_fbx_model_uid="101", _vapb_fbx_geometry_uid="202",
                   _vapb_fbx_realization_id=realization)
    if edge:
        value["_vapb_model_instance_edge_path"] = json.dumps(list(edge), sort_keys=True)
    value["_vapb_fbx_receipt_version"] = "vapb_fbx_realization_receipt_v1"
    value["_vapb_fbx_mesh_receipt_id"] = "mesh-receipt"
    value["_vapb_fbx_object_receipt_id"] = "object-receipt"
    value.data.update(_vapb_fbx_receipt_version="vapb_fbx_realization_receipt_v1",
                      _vapb_fbx_source_asset_sha256=FBX_SHA,
                      _vapb_fbx_geometry_uid="202", _vapb_fbx_mesh_receipt_id="mesh-receipt")
    return value


def root(current):
    return Object(_vapb_root_context_id="root-one",
                  _vapb_witness_package_sha256=PACKAGE_SHA,
                  _vapb_renderer_occurrences=json.dumps({"records": [current], "issues": []}),
                  obj_type="EMPTY")


class ModelWitnessBridgeTests(unittest.TestCase):
    def test_materials_disabled_still_restores_witnessed_shape_and_skin_state(self):
        import unitypackage_blender_importer.blender.model_witness_bridge as bridge
        restore = getattr(bridge, "restore_witnessed_prefab_state", None)
        self.assertTrue(callable(restore), "witness restoration must be independent of material import")

        edge = ({"container_package_id": "pkg", "container_asset_guid": "f" * 32,
                 "prefab_instance_file_id": 1, "source_package_id": "pkg",
                 "source_prefab_guid": GUID},)
        current, obj, model_witness = record(edge), native(edge), witness()
        collection = SimpleNamespace(objects=SimpleNamespace(link=lambda value: None))
        view_layer = SimpleNamespace(update=lambda: None)
        prefab = SimpleNamespace(transforms={})
        semantic_objects = {}
        bindings = [(current, obj)]
        skin_issues = [{"code": "SKIN_SYNTHETIC", "occurrence_id": current["occurrence_id"]}]
        shape_issues = [{"code": "SHAPE_SYNTHETIC", "occurrence_id": current["occurrence_id"]}]
        with mock.patch.object(bridge, "realize_repeated_shape_occurrences", return_value=[obj]) as shapes, \
             mock.patch.object(bridge, "plan_witness_realizations", return_value=(bindings, [])), \
             mock.patch.object(bridge, "plan_witness_skin_carriers", return_value=([], skin_issues)) as skin_plan, \
             mock.patch.object(bridge, "realize_witness_skin_carriers", return_value=True) as skin_realize, \
             mock.patch.object(bridge, "apply_witness_shape_weights", return_value=shape_issues) as weights, \
             mock.patch.object(bridge, "plan_witness_material_dependencies") as materials:
            member_objects, actual_bindings, issues, dependencies = restore(
                [current], [obj], model_witness, collection, view_layer, prefab, semantic_objects,
                PACKAGE_SHA, restore_materials=False)

        self.assertEqual([obj], member_objects)
        self.assertEqual(bindings, actual_bindings)
        self.assertEqual([
            {"code": "SKIN_SYNTHETIC", "occurrence_id": current["occurrence_id"], "root_context_id": "root-one"},
            {"code": "SHAPE_SYNTHETIC", "occurrence_id": current["occurrence_id"], "root_context_id": "root-one"},
        ], issues)
        self.assertEqual([], dependencies)
        self.assertEqual(current["occurrence_id"], obj["_vapb_renderer_occurrence_id"])
        nested_clear = summarize_import_outcome(
            [{"records": [current], "issues": []}], [],
            realized_renderer_occurrences={obj["_vapb_renderer_occurrence_id"]})
        self.assertEqual("SUCCESS", nested_clear["overall"])
        self.assertNotIn("NESTED_PREFAB_RENDERER_NOT_REALIZED",
                         {item["code"] for item in nested_clear["items"]})
        unresolved_state = summarize_import_outcome(
            [{"records": [current], "issues": issues}], [],
            realized_renderer_occurrences={obj["_vapb_renderer_occurrence_id"]})
        self.assertEqual("PARTIAL", unresolved_state["overall"])
        self.assertNotIn("NESTED_PREFAB_RENDERER_NOT_REALIZED",
                         {item["code"] for item in unresolved_state["items"]})
        shapes.assert_called_once()
        skin_plan.assert_called_once_with(bindings, model_witness, prefab, semantic_objects)
        skin_realize.assert_called_once_with([], collection, bindings, semantic_objects, prefab)
        weights.assert_called_once_with(bindings, model_witness)
        materials.assert_not_called()

    def test_material_dependencies_are_planned_when_materials_are_enabled(self):
        import unitypackage_blender_importer.blender.model_witness_bridge as bridge
        restore = getattr(bridge, "restore_witnessed_prefab_state", None)
        self.assertTrue(callable(restore), "material gate belongs only to material dependency planning")

        current, obj, model_witness = record(), native(), witness()
        bindings = [(current, obj)]
        dependencies = [{"dependency_type": "PREFAB_RENDERER_MATERIAL"}]
        with mock.patch.object(bridge, "realize_repeated_shape_occurrences", return_value=[obj]), \
             mock.patch.object(bridge, "plan_witness_realizations", return_value=(bindings, [])), \
             mock.patch.object(bridge, "plan_witness_skin_carriers", return_value=([], [])), \
             mock.patch.object(bridge, "realize_witness_skin_carriers", return_value=True), \
             mock.patch.object(bridge, "apply_witness_shape_weights", return_value=[]), \
             mock.patch.object(bridge, "plan_witness_material_dependencies", return_value=dependencies) as materials:
            _, _, _, actual_dependencies = restore(
                [current], [obj], model_witness, SimpleNamespace(objects=SimpleNamespace(link=lambda value: None)),
                SimpleNamespace(update=lambda: None), SimpleNamespace(transforms={}), {},
                PACKAGE_SHA, restore_materials=True)

        self.assertEqual(dependencies, actual_dependencies)
        materials.assert_called_once_with(bindings, PACKAGE_SHA)

    def test_repeated_mesh_requires_explicit_renderer_creation_provenance(self):
        first, second = record(), record()
        second['source_key']['renderer_file_id'] = -23
        second['owner']['owner_game_object_id'] = -12
        second['occurrence_id'] = occurrence_identity(second)
        a, b = native(realization='a'), native(realization='b')
        a['_vapb_renderer_occurrence_id'] = first['occurrence_id']
        b['_vapb_renderer_occurrence_id'] = second['occurrence_id']
        bindings, issues = plan_witness_realizations([first, second], [b, a], witness())
        self.assertEqual(issues, [])
        self.assertEqual([(r['occurrence_id'], obj['_vapb_fbx_realization_id']) for r, obj in bindings],
                         [(first['occurrence_id'], 'a'), (second['occurrence_id'], 'b')])
        b['_vapb_renderer_occurrence_id'] = 'wrong'
        self.assertTrue(plan_witness_realizations([first, second], [a, b], witness())[1])

    def test_skin_plan_uses_receipts_and_rejects_wrong_parent_root_scope(self):
        from unitypackage_blender_importer.blender.fbx_receipt import make_bone_receipt, RECEIPT_VERSION
        from unitypackage_blender_importer.unity.model_identity_witness import ModelWitnessIndex
        class Entity(Object):
            __hash__ = object.__hash__
        class Point:
            length = 0
            def __sub__(self, other): return self
        class Frame:
            translation = Point()
            def __matmul__(self, other): return Point()
        current = record()
        current['skin'] = {'status': 'EXACT', 'bones': [
            {'transform_file_id': '1', 'parent_transform_file_id': '0'},
            {'transform_file_id': '2', 'parent_transform_file_id': '1'}],
            'root_bone_transform_file_id': '1'}
        index = ModelWitnessIndex([replace(witness().rows[0], bone_model_uids=(707, 808), root_bone_model_uid=707)], {GUID: FBX_SHA})
        bones = []
        for uid in (707, 808):
            receipt = make_bone_receipt(uid, GUID, FBX_SHA)
            bone = Entity(_vapb_fbx_model_uid=str(uid), _vapb_fbx_bone_receipt_id=receipt.blender_bone_receipt_id,
                _vapb_fbx_receipt_version=RECEIPT_VERSION, _vapb_fbx_receipt_evidence=receipt.evidence,
                _vapb_fbx_bone_realization_id=str(uid))
            bone.parent = bones[0] if bones else None
            bone.head_local = Point()
            bones.append(bone)
        rig = Entity(_vapb_root_context_id='root-one', obj_type='ARMATURE')
        rig.data.bones, rig.matrix_world = bones, Frame()
        mesh = native()
        mesh.modifiers = [SimpleNamespace(type='ARMATURE', object=rig)]
        carriers = {}
        for go in (10, 20):
            carrier = Entity(_vapb_root_context_id='root-one', obj_type='EMPTY')
            carrier.constraints, carrier.matrix_world = [], Frame()
            carriers[go] = carrier
        prefab = SimpleNamespace(transforms={1: SimpleNamespace(game_object_id=10), 2: SimpleNamespace(game_object_id=20)})
        plans, issues = plan_witness_skin_carriers([(current, mesh)], index, prefab, carriers)
        self.assertEqual((2, []), (len(plans), issues))
        # The Prefab, not the model default, owns a legitimate rootBone override.
        current['skin']['root_bone_transform_file_id'] = '2'
        plans, issues = plan_witness_skin_carriers([(current, mesh)], index, prefab, carriers)
        self.assertEqual((2, []), (len(plans), issues))
        current['skin']['root_bone_transform_file_id'] = '1'
        prefab.transforms[3] = SimpleNamespace(game_object_id=30)
        carriers[30] = Entity(_vapb_root_context_id='root-one', obj_type='EMPTY')
        current['skin']['root_bone_transform_file_id'] = '3'
        plans, issues = plan_witness_skin_carriers([(current, mesh)], index, prefab, carriers)
        self.assertEqual((2, []), (len(plans), issues))
        current['skin']['root_bone_transform_file_id'] = '1'
        for change, undo in (
            (lambda: setattr(bones[1], 'parent', None), lambda: setattr(bones[1], 'parent', bones[0])),
            (lambda: current['skin'].update(root_bone_transform_file_id='999'), lambda: current['skin'].update(root_bone_transform_file_id='1')),
            (lambda: rig.update(_vapb_root_context_id='other'), lambda: rig.update(_vapb_root_context_id='root-one')),
            (lambda: bones[0].update(_vapb_fbx_bone_receipt_id='wrong'), lambda: bones[0].update(_vapb_fbx_bone_receipt_id=make_bone_receipt(707, GUID, FBX_SHA).blender_bone_receipt_id)),
        ):
            change()
            rejected, issues = plan_witness_skin_carriers([(current, mesh)], index, prefab, carriers)
            self.assertEqual([], rejected)
            self.assertEqual(1, len(issues))
            undo()

    def test_explicit_null_is_typed_clear_only_with_exact_slot_evidence(self):
        current = record()
        current["materials"] = {0: None}
        obj = native()
        bindings, issues = plan_witness_realizations([current], [obj], witness())
        self.assertEqual([], issues)
        operations = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        self.assertEqual(["CLEAR_MATERIAL_SLOT"], [item["dependency_type"] for item in operations])
        self.assertNotIn("target_guid", operations[0])
        self.assertIs(obj, find_witness_consumer(operations[0], [root(current), obj]))
        for field, wrong in (("consumer_occurrence_id", "other"),
                             ("consumer_native_realization_id", "other"),
                             ("consumer_root_context_id", "other"),
                             ("consumer_package_id", "other"),
                             ("consumer_source_package_sha256", "0" * 64),
                             ("consumer_fbx_object_receipt_id", "other")):
            changed = {**operations[0], field: wrong}
            with self.subTest(field=field):
                self.assertIsNone(find_witness_consumer(changed, [root(current), obj]))
        self.assertIsNone(find_witness_consumer(operations[0], [root(current), obj, native()]))
        for status, count, reference in (("UNKNOWN", 1, None), ("EXACT", None, None),
                                         ("EXACT", 0, None), ("EXACT", 1, {"file_id": 2100000}),
                                         ("EXACT", 1, {"fileID": 0, "guid": "invalid"})):
            changed = copy.deepcopy(current)
            changed["material_status"] = status
            changed["material_slot_count"] = count
            changed["materials"] = {0: reference}
            self.assertEqual([], plan_witness_material_dependencies([(changed, obj)], PACKAGE_SHA))

    def test_projected_renderer_joins_one_native_mesh(self):
        bindings, issues = plan_witness_realizations([record()], [native()], witness())
        self.assertEqual([], issues)
        self.assertEqual(1, len(bindings))
        self.assertEqual("native-one", bindings[0][1]["_vapb_fbx_realization_id"])

    def test_repeated_model_source_keeps_occurrence_materials_separate(self):
        edge_a = ({"container_package_id": "pkg", "container_asset_guid": "f" * 32,
                   "prefab_instance_file_id": 1, "source_package_id": "pkg",
                   "source_prefab_guid": GUID},)
        edge_b = ({**edge_a[0], "prefab_instance_file_id": 2},)
        records = [model_record(edge_a), model_record(edge_b, "9" * 32)]
        objects = [native(edge_a, "native-a"), native(edge_b, "native-b")]
        bindings, issues = plan_witness_realizations(records, objects, witness())
        self.assertEqual([], issues)
        self.assertEqual(["native-a", "native-b"],
                         [obj["_vapb_fbx_realization_id"] for _, obj in bindings])
        self.assertNotEqual(bindings[0][0]["materials"], bindings[1][0]["materials"])
        dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        self.assertEqual(["e" * 32, "9" * 32],
                         [item["target_guid"] for item in dependencies])
        self.assertEqual(["native-a", "native-b"],
                         [item["consumer_native_realization_id"] for item in dependencies])

    def test_missing_witness_wrong_revision_or_duplicate_native_stays_unbound(self):
        current = record()
        self.assertEqual(([], [{"occurrence_id": current["occurrence_id"],
                                "code": "WITNESS_MISSING"}]),
                         plan_witness_realizations([current], [native()], None))
        wrong = native()
        wrong["_vapb_fbx_source_asset_sha256"] = "0" * 64
        bindings, issues = plan_witness_realizations([current], [wrong], witness())
        self.assertEqual([], bindings)
        self.assertEqual("NATIVE_MISSING", issues[0]["code"])
        bindings, issues = plan_witness_realizations([current], [native(), native(realization="other")], witness())
        self.assertEqual([], bindings)
        self.assertEqual("NATIVE_AMBIGUOUS", issues[0]["code"])

    def test_two_renderer_occurrences_cannot_claim_same_native_object(self):
        first = record()
        second = record()
        second["source_key"]["renderer_file_id"] = -23
        second["owner"]["owner_game_object_id"] = -12
        second["occurrence_id"] = occurrence_identity(second)
        bindings, issues = plan_witness_realizations([first, second], [native()], witness())
        self.assertEqual([], bindings)
        self.assertEqual(["NATIVE_AMBIGUOUS", "NATIVE_AMBIGUOUS"],
                         [issue["code"] for issue in issues])

    def test_model_source_renderer_and_owner_ids_must_match_witness(self):
        current = record()
        current["source_key"] = {"source_kind": "MODEL_SOURCE", "source_asset_guid": GUID,
                                 "renderer_file_id": -505}
        current["owner"] = {"source_kind": "MODEL_SOURCE", "source_asset_guid": GUID,
                            "owner_game_object_id": -404}
        current["occurrence_id"] = occurrence_identity(current)
        bindings, issues = plan_witness_realizations([current], [native()], witness())
        self.assertEqual([], issues)
        self.assertEqual(1, len(bindings))
        changed = copy.deepcopy(current)
        changed["owner"]["owner_game_object_id"] = -999
        changed["occurrence_id"] = occurrence_identity(changed)
        bindings, issues = plan_witness_realizations([changed], [native()], witness())
        self.assertEqual([], bindings)
        self.assertEqual("SOURCE_IDENTITY_MISMATCH", issues[0]["code"])

    def test_exact_material_reference_produces_scoped_dependency(self):
        current = record()
        obj = native()
        bindings, issues = plan_witness_realizations([current], [obj], witness())
        self.assertEqual([], issues)
        dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        self.assertEqual(1, len(dependencies))
        dep = dependencies[0]
        self.assertEqual((current["occurrence_id"], "native-one", "e" * 32, "2100000"),
                         (dep["consumer_occurrence_id"], dep["consumer_native_realization_id"],
                          dep["target_guid"], dep["target_file_id"]))
        self.assertEqual(2100000, dep["target_file_id_raw"])
        self.assertIs(obj, find_witness_consumer(dep, [root(current), obj]))
        self.assertIsNone(find_witness_consumer(dep, [root(current), obj, native()]))
        unknown = copy.deepcopy(current)
        unknown["material_status"] = "UNKNOWN"
        self.assertEqual([], plan_witness_material_dependencies([(unknown, obj)], PACKAGE_SHA))

    def test_shared_mesh_slot_capacity_is_reserved_before_dependency_capture(self):
        from unitypackage_blender_importer.blender.model_witness_bridge import reserve_witness_slots
        left = record()
        right = record(material="9" * 32)
        right["root_context_id"] = "root-two"
        right["occurrence_id"] = occurrence_identity(right)
        first = native()
        second = native(realization="native-two")
        second["_vapb_root_context_id"] = "root-two"
        second.data = first.data
        root_two = root(right)
        root_two["_vapb_root_context_id"] = "root-two"
        deps = (plan_witness_material_dependencies([(left, first)], PACKAGE_SHA)
                + plan_witness_material_dependencies([(right, second)], PACKAGE_SHA))
        ready, rejected = reserve_witness_slots(deps, [root(left), root_two, first, second])
        self.assertEqual([], rejected)
        self.assertEqual(2, len(ready))
        self.assertEqual([None], first.data.materials)


if __name__ == "__main__":
    unittest.main()
