"""Public synthetic occurrence-to-native joins; names never identify objects."""

import copy
import hashlib
import json
from io import BytesIO
from pathlib import Path
import re
import tarfile
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


def raw_three_slot_mesh_reference():
    """Read the Mesh subasset identity from the fixed public input package."""
    package_path = (Path(__file__).resolve().parent
                    / "unity_model_material_probe" / "fixtures"
                    / "ThreeSlotSource.unitypackage")
    package_bytes = package_path.read_bytes()
    package_sha = hashlib.sha256(package_bytes).hexdigest()
    if package_sha != "d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c":
        raise AssertionError("fixed public fixture package SHA-256 changed")

    with tarfile.open(fileobj=BytesIO(package_bytes), mode="r:*") as archive:
        prefabs = []
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith("/pathname"):
                continue
            pathname = archive.extractfile(member)
            if pathname is None or not pathname.read().decode("utf-8").endswith(".prefab"):
                continue
            payload = archive.extractfile(member.name.removesuffix("/pathname") + "/asset")
            if payload is None:
                raise AssertionError("fixed Prefab asset payload is missing")
            prefabs.append(payload.read())
        fbx_member = "abcdefabcdefabcdefabcdefabcdefab/asset"
        fbx_stream = archive.extractfile(fbx_member)
        if fbx_stream is None:
            raise AssertionError("fixed source FBX payload is missing")
        fbx_sha = hashlib.sha256(fbx_stream.read()).hexdigest()
        meta_stream = archive.extractfile("abcdefabcdefabcdefabcdefabcdefab/asset.meta")
        if meta_stream is None:
            raise AssertionError("fixed source FBX importer metadata is missing")
        fbx_meta = meta_stream.read()

    if len(prefabs) != 1:
        raise AssertionError("fixed fixture must contain exactly one Prefab")
    docs = re.findall(rb"(?ms)^--- !u!137 &(\d+)\r?\n(.*?)(?=^--- !u!|\Z)", prefabs[0])
    mesh_refs = []
    for renderer_file_id, body in docs:
        match = re.search(
            rb"(?m)^\s*m_Mesh:\s*\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]{32}),\s*type:\s*\d+\s*\}",
            body)
        if match:
            owner = re.search(rb"(?m)^\s*m_GameObject:\s*\{fileID:\s*(-?\d+)\s*\}", body)
            if owner is None:
                raise AssertionError("fixed Renderer owner reference is missing")
            mesh_refs.append({
                "renderer_file_id": renderer_file_id.decode("ascii"),
                "owner_game_object_id": owner.group(1).decode("ascii"),
                "mesh_file_id": match.group(1).decode("ascii"),
                "mesh_guid": match.group(2).decode("ascii").lower(),
            })
    if len(mesh_refs) != 1:
        raise AssertionError("fixed fixture must contain exactly one Renderer Mesh reference")
    if fbx_sha != "fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5":
        raise AssertionError("fixed source FBX SHA-256 changed")
    if b"internalIDToNameTable: []" not in fbx_meta or b"externalObjects: {}" not in fbx_meta:
        raise AssertionError("fixed source FBX metadata now has an importer identity mapping")
    return package_sha, fbx_sha, mesh_refs[0]


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

    def test_guid_sha_singleton_cannot_prove_mesh_file_id_without_witness(self):
        package_sha, fbx_sha, raw_ref = raw_three_slot_mesh_reference()
        self.assertEqual("fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5",
                         fbx_sha)
        self.assertEqual({
            "renderer_file_id": "3728717051629469441",
            "owner_game_object_id": "6665729011320497926",
            "mesh_file_id": "3538053534738119282",
            "mesh_guid": "abcdefabcdefabcdefabcdefabcdefab",
        }, raw_ref)

        package_id = "sha256:" + package_sha
        root_context = "fixed-three-slot-root-context"
        source_record = record()
        source_record.update({
            "root_context_id": root_context,
            "root_package_id": package_id,
            "root_member_id": "7cbdcbe81fde386408bcfb379e62b6bb",
            "root_asset_guid": "7cbdcbe81fde386408bcfb379e62b6bb",
            "source_package_id": package_id,
            "source_key": {
                "source_kind": "PREFAB_LOCAL",
                "source_asset_guid": "7cbdcbe81fde386408bcfb379e62b6bb",
                "renderer_file_id": int(raw_ref["renderer_file_id"]),
            },
            "owner": {
                "source_kind": "PREFAB_LOCAL",
                "source_asset_guid": "7cbdcbe81fde386408bcfb379e62b6bb",
                "owner_game_object_id": int(raw_ref["owner_game_object_id"]),
            },
            "mesh": {
                "mesh_guid": raw_ref["mesh_guid"],
                "mesh_file_id": int(raw_ref["mesh_file_id"]),
                "source_package_id": package_id,
                "source_sha256": fbx_sha,
            },
        })
        source_record["occurrence_id"] = occurrence_identity(source_record)

        changed_file_id_record = copy.deepcopy(source_record)
        changed_file_id_record["mesh"]["mesh_file_id"] += 1
        self.assertEqual(source_record["occurrence_id"],
                         changed_file_id_record["occurrence_id"])
        restored_file_id_record = copy.deepcopy(changed_file_id_record)
        restored_file_id_record["mesh"]["mesh_file_id"] = int(raw_ref["mesh_file_id"])
        self.assertEqual(source_record, restored_file_id_record)

        # This test double represents the one scoped GUID/SHA candidate; the
        # prior T0 run separately established its real persistent receipt.
        native_candidate = Object(
            _vapb_root_context_id=root_context,
            unity_source_package_id=package_id,
            _vapb_fbx_source_asset_guid=raw_ref["mesh_guid"],
            _vapb_fbx_source_asset_sha256=fbx_sha,
        )
        records = [source_record, changed_file_id_record]

        def guid_sha_candidates(value):
            mesh_ref = value["mesh"]
            return [obj for obj in [native_candidate]
                    if obj.type == "MESH"
                    and obj.get("_vapb_root_context_id") == value["root_context_id"]
                    and obj.get("unity_source_package_id") == mesh_ref["source_package_id"]
                    and obj.get("_vapb_fbx_source_asset_guid", "").lower() == mesh_ref["mesh_guid"]
                    and obj.get("_vapb_fbx_source_asset_sha256", "").lower() == mesh_ref["source_sha256"]]

        # A fallback that sees only package, GUID, and FBX revision selects the
        # same sole native object for both the raw fileID and a different fileID.
        candidate_sets = [guid_sha_candidates(value) for value in records]
        self.assertEqual([[native_candidate], [native_candidate]], candidate_sets)

        # The production bridge requires the missing subasset-to-FBX identity
        # mapping and therefore must not turn either candidate set into a bind.
        for value in records:
            bindings, issues = plan_witness_realizations([value], [native_candidate], None)
            self.assertEqual([], bindings)
            self.assertEqual([{"occurrence_id": value["occurrence_id"],
                               "code": "WITNESS_MISSING"}], issues)

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
