"""Synthetic model-source overrides stay scoped to their Renderer identity."""

import json
import copy
from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.blender.fbx_receipt import FbxModelLink, RawFbxSemanticIndex
from unitypackage_blender_importer.blender.model_witness_bridge import (
    find_witness_consumer, plan_witness_material_dependencies, plan_witness_realizations,
)
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelAssetRevision, validate_model_witness,
)
from unitypackage_blender_importer.unity.occurrence_projection import PrefabSource, project_occurrences
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab


ROOT = "a" * 32
MODEL = "b" * 32
FBX_SHA = "c" * 64
META_SHA = "d" * 64
PACKAGE_SHA = "e" * 64
MATERIAL_A = "1" * 32
MATERIAL_B = "2" * 32
MATERIAL_U = "3" * 32
OTHER_SOURCE = "4" * 32
NATIVE_IDS = {
    -20: (101, 201, "native-0", "object-0", "mesh-0"),
    -21: (102, 202, "native-1", "object-1", "mesh-1"),
    -22: (103, 203, "native-2", "object-2", "mesh-2"),
}


class Native(dict):
    type = "MESH"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {"_vapb_fbx_receipt_version": "vapb_fbx_realization_receipt_v1",
                     "_vapb_fbx_source_asset_sha256": FBX_SHA,
                     "_vapb_fbx_geometry_uid": str(kwargs["_vapb_fbx_geometry_uid"]),
                     "_vapb_fbx_mesh_receipt_id": str(kwargs["_vapb_fbx_mesh_receipt_id"])}


def fixture(directory, model_revision=FBX_SHA, operations=None):
    models = []
    links = []
    for index in range(3):
        models.append({"model_uid": str(101 + index), "geometry_uid": str(201 + index),
                       "transform_local_id": str(-50 - index),
                       "game_object_local_id": str(-40 - index),
                       "renderers": [{"class_id": 137,
                                      "renderer_local_id": str(-20 - index),
                                      "mesh_local_id": str(-30 - index)}]})
        links.append(FbxModelLink(101 + index, 201 + index))
    witness = validate_model_witness({
        "schema_version": "vapb-model-identity-witness-v1",
        "source_unitypackage_sha256": PACKAGE_SHA,
        "unity_version": "2022.3.22f1",
        "source_validation": {"probe_pass": True, "original_revision_equivalent": True},
        "assets": [{"asset_guid": MODEL, "source_fbx_sha256": FBX_SHA,
                    "source_meta_sha256": META_SHA, "models": models}],
    }, PACKAGE_SHA, {MODEL: ModelAssetRevision(
        FBX_SHA, META_SHA, RawFbxSemanticIndex(links, [101, 102, 103]))})
    if operations is None:
        operations = [(-20, MATERIAL_A, MODEL, 10), (-21, MATERIAL_B, MODEL, 10),
                      (-22, None, MODEL, 10), (-999, MATERIAL_U, MODEL, 10)]
    instances = sorted({10, *(instance for _, _, _, instance in operations)})
    documents = []
    for instance in instances:
        modifications = []
        for renderer_id, material, source_guid, target_instance in operations:
            if target_instance != instance:
                continue
            reference = ("{fileID: 0}" if material is None else
                         f"{{fileID: 2100000, guid: {material}, type: 2}}")
            modifications.append(f"""    - target: {{fileID: {renderer_id}, guid: {source_guid}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {reference}
""")
        documents.append(f"""--- !u!1001 &{instance}
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {MODEL}, type: 3}}
  m_Modification:
    m_Modifications:
{''.join(modifications)}""")
    path = Path(directory) / "root.prefab"
    path.write_text("%YAML 1.1\n" + "".join(documents), encoding="utf-8")
    path.with_name(path.name + ".meta").write_text(f"guid: {ROOT}\n", encoding="utf-8")
    root = PrefabSource(parse_prefab(path), "pkg", "root-member", "root-revision")
    model = PrefabSource(None, "pkg", "model-member", model_revision, MODEL)
    projection = project_occurrences(root, "root-context", lambda _pkg, _guid: model,
                                     model_witness=witness)
    for record in projection.records:
        record["mesh"].update(source_package_id="pkg", source_sha256=FBX_SHA)
    return projection, witness


def native(record):
    renderer_id = int(record["source_key"]["renderer_file_id"])
    model_uid, geometry_uid, realization_id, object_id, mesh_id = NATIVE_IDS[renderer_id]
    instance_id = record["instance_edge_path"][-1]["prefab_instance_file_id"]
    suffix = "" if instance_id == 10 else f"-instance-{instance_id}"
    return Native(_vapb_root_context_id="root-context", unity_source_package_id="pkg",
                  _vapb_fbx_source_asset_guid=MODEL, _vapb_fbx_source_asset_sha256=FBX_SHA,
                  _vapb_fbx_model_uid=str(model_uid),
                  _vapb_fbx_geometry_uid=str(geometry_uid),
                  _vapb_model_instance_edge_path=json.dumps(record["instance_edge_path"], sort_keys=True),
                  _vapb_fbx_realization_id=realization_id + suffix,
                  _vapb_fbx_receipt_version="vapb_fbx_realization_receipt_v1",
                  _vapb_fbx_object_receipt_id=object_id + suffix,
                  _vapb_fbx_mesh_receipt_id=mesh_id + suffix)


class UnrelatedModelOverrideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projection, self.witness = fixture(self.temp.name)
        self.records = sorted(self.projection.records,
                              key=lambda row: row["source_key"]["renderer_file_id"], reverse=True)
        self.objects = [native(record) for record in self.records]

    def test_unrelated_null_and_orphan_cannot_poison_two_proven_renderer_slots(self):
        self.assertEqual([-20, -21, -22],
                         [record["source_key"]["renderer_file_id"] for record in self.records])
        self.assertEqual(["PARTIAL", "PARTIAL", "PARTIAL"],
                         [record["material_status"] for record in self.records])
        self.assertEqual(["UNRESOLVED_OVERRIDE"],
                         [issue["code"] for issue in self.projection.issues])
        self.assertEqual(-999, self.projection.issues[0]["target_renderer_file_id"])
        bindings, issues = plan_witness_realizations(self.records, self.objects, self.witness)
        self.assertEqual([], issues)
        dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        self.assertEqual([MATERIAL_A, MATERIAL_B],
                         [dependency["target_guid"] for dependency in dependencies])
        self.assertEqual(["native-0", "native-1"],
                         [dependency["consumer_native_realization_id"] for dependency in dependencies])
        self.assertEqual({0: None}, self.records[2]["materials"])
        root = {"_vapb_root_context_id": "root-context",
                "_vapb_witness_package_sha256": PACKAGE_SHA,
                "_vapb_renderer_occurrences": json.dumps(self.projection.to_dict())}
        self.assertIs(self.objects[0], find_witness_consumer(dependencies[0], [root, *self.objects]))
        wrong_material = copy.deepcopy(dependencies[0])
        wrong_material["target_file_id"] = "9999999"
        self.assertIsNone(find_witness_consumer(wrong_material, [root, *self.objects]))

    def test_wrong_package_revision_and_ambiguous_native_stay_unbound(self):
        wrong_package = [native(record) for record in self.records]
        wrong_package[0]["unity_source_package_id"] = "other-package"
        bindings, issues = plan_witness_realizations(self.records, wrong_package, self.witness)
        self.assertEqual("NATIVE_MISSING", issues[0]["code"])
        self.assertEqual([MATERIAL_B], [dependency["target_guid"] for dependency in
                         plan_witness_material_dependencies(bindings, PACKAGE_SHA)])
        duplicate = native(self.records[0])
        duplicate["_vapb_fbx_realization_id"] = "duplicate"
        bindings, issues = plan_witness_realizations(self.records, self.objects + [duplicate], self.witness)
        self.assertEqual("NATIVE_AMBIGUOUS", issues[0]["code"])
        self.assertEqual([MATERIAL_B], [dependency["target_guid"] for dependency in
                         plan_witness_material_dependencies(bindings, PACKAGE_SHA)])
        wrong_revision, _ = fixture(self.temp.name, model_revision="0" * 64)
        self.assertEqual([], wrong_revision.records)
        self.assertEqual("UNRESOLVED_SOURCE", wrong_revision.issues[0]["code"])

    def test_counterfactual_unmatched_override_removal_reinsertion_and_order(self):
        # E0-E4: valid Renderer identities and references are fixed. Only U
        # is removed, restored, or moved among independent target operations.
        valid = [(-20, MATERIAL_A, MODEL, 10), (-21, MATERIAL_B, MODEL, 10)]
        unknown = (-999, MATERIAL_U, MODEL, 10)
        experiments = [valid, valid + [unknown], valid, valid + [unknown],
                       [unknown] + valid]
        for label, operations in zip(("E0", "E1", "E2", "E3", "E4"), experiments):
            with self.subTest(label=label):
                projection, witness = fixture(self.temp.name, operations=operations)
                rows = {row["source_key"]["renderer_file_id"]: row
                        for row in projection.records}
                self.assertEqual({-20, -21, -22}, set(rows))
                self.assertEqual(["PARTIAL", "PARTIAL", "PARTIAL"],
                                 [rows[key]["material_status"] for key in (-20, -21, -22)])
                self.assertEqual([MATERIAL_A, MATERIAL_B],
                                 [rows[key]["materials"][0]["guid"] for key in (-20, -21)])
                self.assertEqual({}, rows[-22]["materials"])
                self.assertEqual(int(unknown in operations),
                                 sum(issue["code"] == "UNRESOLVED_OVERRIDE"
                                     for issue in projection.issues))
                bindings, issues = plan_witness_realizations(
                    list(reversed(projection.records)),
                    [native(row) for row in projection.records], witness)
                self.assertEqual([], issues)
                dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
                self.assertEqual({("native-0", MATERIAL_A), ("native-1", MATERIAL_B)},
                                 {(dep["consumer_native_realization_id"], dep["target_guid"])
                                  for dep in dependencies})
        swapped, witness = fixture(self.temp.name, operations=[
            (-20, MATERIAL_B, MODEL, 10), (-21, MATERIAL_A, MODEL, 10), unknown])
        bindings, issues = plan_witness_realizations(
            list(reversed(swapped.records)), [native(row) for row in swapped.records], witness)
        self.assertEqual([], issues)
        self.assertEqual({("native-0", MATERIAL_B), ("native-1", MATERIAL_A)},
                         {(dep["consumer_native_realization_id"], dep["target_guid"])
                          for dep in plan_witness_material_dependencies(bindings, PACKAGE_SHA)})

    def test_unmatched_override_sentinel_does_not_guess_a_renderer(self):
        # A conspicuously different Material on U still supplies no Renderer
        # identity. A change on a proven direct target must remain observable.
        valid = [(-20, MATERIAL_A, MODEL, 10), (-21, MATERIAL_B, MODEL, 10)]
        snapshots = []
        for operations in (valid,
                           valid + [(-999, MATERIAL_U, MODEL, 10)],
                           valid + [(-999, MATERIAL_B, MODEL, 10)],
                           [(-20, MATERIAL_U, MODEL, 10), valid[1]]):
            projection, witness = fixture(self.temp.name, operations=operations)
            bindings, issues = plan_witness_realizations(
                projection.records, [native(row) for row in projection.records], witness)
            self.assertEqual([], issues)
            dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
            snapshots.append((
                {(dep["consumer_native_realization_id"], dep["target_guid"])
                 for dep in dependencies},
                sum(issue["code"] == "UNRESOLVED_OVERRIDE" for issue in projection.issues),
            ))
        self.assertEqual(snapshots[0][0], snapshots[1][0])
        self.assertEqual(snapshots[0][0], snapshots[2][0])
        self.assertEqual([0, 1, 1, 0], [snapshot[1] for snapshot in snapshots])
        self.assertNotEqual(snapshots[0][0], snapshots[3][0])
        self.assertIn(("native-0", MATERIAL_U), snapshots[3][0])

    def test_counterfactual_instance_source_and_direct_invalid_target(self):
        # E5: U is on the same instance, a second occurrence of the same
        # source, or a different source GUID. Instance edges remain explicit.
        valid = [(-20, MATERIAL_A, MODEL, 10), (-21, MATERIAL_B, MODEL, 10),
                 (-20, MATERIAL_A, MODEL, 11), (-21, MATERIAL_B, MODEL, 11)]
        for label, extra in (("same", (-999, MATERIAL_U, MODEL, 10)),
                             ("other_instance", (-999, MATERIAL_U, MODEL, 11)),
                             ("other_source", (-999, MATERIAL_U, OTHER_SOURCE, 10))):
            with self.subTest(label=label):
                projection, _ = fixture(self.temp.name, operations=valid + [extra])
                self.assertEqual(6, len(projection.records))
                self.assertEqual(1, sum(issue["code"] == "UNRESOLVED_OVERRIDE"
                                        for issue in projection.issues))
                for row in projection.records:
                    renderer_id = row["source_key"]["renderer_file_id"]
                    self.assertEqual("PARTIAL", row["material_status"])
                    self.assertEqual({-20: MATERIAL_A, -21: MATERIAL_B}.get(renderer_id),
                                     row["materials"].get(0, {}).get("guid"))
        # E6: a matching explicit null is known, but native slot realization
        # remains partial for a model source with no serialized slot count.
        projection, witness = fixture(
            self.temp.name, operations=valid[:2] + [(-20, None, MODEL, 10)])
        rows = {row["source_key"]["renderer_file_id"]: row for row in projection.records}
        self.assertEqual("PARTIAL", rows[-20]["material_status"])
        self.assertEqual({0: None}, rows[-20]["materials"])
        self.assertEqual("PARTIAL", rows[-21]["material_status"])
        bindings, issues = plan_witness_realizations(
            projection.records, [native(row) for row in projection.records], witness)
        self.assertEqual([], issues)
        self.assertEqual([MATERIAL_B],
                         [dep["target_guid"] for dep in
                          plan_witness_material_dependencies(bindings, PACKAGE_SHA)])

    def test_counterfactual_missing_witness_fails_closed(self):
        # E7: no accepted model witness means no projected model Renderer, not
        # an empty-success status that could authorize a guessed binding.
        fixture(self.temp.name)
        prefab = parse_prefab(Path(self.temp.name) / "root.prefab")
        root = PrefabSource(prefab, "pkg", "root-member", "root-revision")
        model = PrefabSource(None, "pkg", "model-member", FBX_SHA, MODEL)
        projection = project_occurrences(root, "root-context", lambda _pkg, _guid: model)
        self.assertEqual([], projection.records)
        self.assertEqual(["UNRESOLVED_SOURCE"] + ["UNRESOLVED_OVERRIDE"] * 4,
                         [issue["code"] for issue in projection.issues])


if __name__ == "__main__":
    unittest.main()
