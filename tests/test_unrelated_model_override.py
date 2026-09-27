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


class Native(dict):
    type = "MESH"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {"_vapb_fbx_receipt_version": "vapb_fbx_realization_receipt_v1",
                     "_vapb_fbx_source_asset_sha256": FBX_SHA,
                     "_vapb_fbx_geometry_uid": str(kwargs["_vapb_fbx_geometry_uid"]),
                     "_vapb_fbx_mesh_receipt_id": str(kwargs["_vapb_fbx_mesh_receipt_id"])}


def fixture(directory, model_revision=FBX_SHA):
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
    modifications = []
    for renderer_id, material in ((-20, MATERIAL_A), (-21, MATERIAL_B)):
        modifications.append(f"""    - target: {{fileID: {renderer_id}, guid: {MODEL}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 2100000, guid: {material}, type: 2}}
""")
    # C has an identified Renderer but an invalid Material reference. A further
    # unmatched target on the same model source must not poison A or B.
    modifications.append(f"""    - target: {{fileID: -22, guid: {MODEL}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 0}}
    - target: {{fileID: -999, guid: {MODEL}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 2100000, guid: {'3' * 32}, type: 2}}
""")
    path = Path(directory) / "root.prefab"
    path.write_text(f"""%YAML 1.1
--- !u!1001 &10
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {MODEL}, type: 3}}
  m_Modification:
    m_Modifications:
{''.join(modifications)}""", encoding="utf-8")
    path.with_name(path.name + ".meta").write_text(f"guid: {ROOT}\n", encoding="utf-8")
    root = PrefabSource(parse_prefab(path), "pkg", "root-member", "root-revision")
    model = PrefabSource(None, "pkg", "model-member", model_revision, MODEL)
    projection = project_occurrences(root, "root-context", lambda _pkg, _guid: model,
                                     model_witness=witness)
    for record in projection.records:
        record["mesh"].update(source_package_id="pkg", source_sha256=FBX_SHA)
    return projection, witness


def native(record):
    row_index = -int(record["source_key"]["renderer_file_id"]) - 20
    return Native(_vapb_root_context_id="root-context", unity_source_package_id="pkg",
                  _vapb_fbx_source_asset_guid=MODEL, _vapb_fbx_source_asset_sha256=FBX_SHA,
                  _vapb_fbx_model_uid=str(101 + row_index),
                  _vapb_fbx_geometry_uid=str(201 + row_index),
                  _vapb_model_instance_edge_path=json.dumps(record["instance_edge_path"], sort_keys=True),
                  _vapb_fbx_realization_id=f"native-{row_index}",
                  _vapb_fbx_receipt_version="vapb_fbx_realization_receipt_v1",
                  _vapb_fbx_object_receipt_id=f"object-{row_index}",
                  _vapb_fbx_mesh_receipt_id=f"mesh-{row_index}")


class UnrelatedModelOverrideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projection, self.witness = fixture(self.temp.name)
        self.records = sorted(self.projection.records,
                              key=lambda row: row["source_key"]["renderer_file_id"], reverse=True)
        self.objects = [native(record) for record in self.records]

    def test_unrelated_unknown_cannot_poison_two_proven_renderer_slots(self):
        self.assertEqual([-20, -21, -22],
                         [record["source_key"]["renderer_file_id"] for record in self.records])
        self.assertEqual(["PARTIAL", "PARTIAL", "UNKNOWN"],
                         [record["material_status"] for record in self.records])
        self.assertEqual(["UNRESOLVED_OVERRIDE", "UNRESOLVED_OVERRIDE"],
                         [issue["code"] for issue in self.projection.issues])
        self.assertEqual(-999, self.projection.issues[1]["target_renderer_file_id"])
        bindings, issues = plan_witness_realizations(self.records, self.objects, self.witness)
        self.assertEqual([], issues)
        dependencies = plan_witness_material_dependencies(bindings, PACKAGE_SHA)
        self.assertEqual([MATERIAL_A, MATERIAL_B],
                         [dependency["target_guid"] for dependency in dependencies])
        self.assertEqual(["native-0", "native-1"],
                         [dependency["consumer_native_realization_id"] for dependency in dependencies])
        self.assertEqual({}, self.records[2]["materials"])
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


if __name__ == "__main__":
    unittest.main()
