"""Unity-authored explicit-null Material override remains a known null slot."""

import copy
import hashlib
import json
from pathlib import Path
import unittest

from unitypackage_blender_importer.blender.fbx_receipt import source_sha256
from unitypackage_blender_importer.blender.model_witness_bridge import matches_witnessed_source
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelIdentityRow, ModelWitnessIndex,
)
from unitypackage_blender_importer.unity.occurrence_projection import (
    PrefabSource, model_instance_plans, model_instance_sources, occurrence_identity, project_occurrences,
)
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab


ASSETS = Path(__file__).with_name("unity_alias_oracle") / "Assets" / "Oracle"
EXPECTED = ASSETS.parents[1] / "null_expected.json"


def source(filename):
    path = ASSETS / filename
    prefab = parse_prefab(path)
    return PrefabSource(prefab, "synthetic", filename,
                        hashlib.sha256(path.read_bytes()).hexdigest(), prefab.asset_guid)


class UnityNullMaterialOracleTests(unittest.TestCase):
    def test_witnessed_prefab_source_excludes_other_meshes_in_same_fbx(self):
        class NativeObject(dict):
            type = "MESH"

        guid, sha = "a" * 32, "b" * 64
        target = NativeObject(_vapb_fbx_source_asset_guid=guid,
                              _vapb_fbx_source_asset_sha256=sha,
                              _vapb_fbx_model_uid="101", _vapb_fbx_geometry_uid="201")
        other = NativeObject(target, _vapb_fbx_model_uid="102", _vapb_fbx_geometry_uid="202")
        wrong_revision = NativeObject(target, _vapb_fbx_source_asset_sha256="c" * 64)
        self.assertEqual([target], [obj for obj in (target, other, wrong_revision)
                                    if matches_witnessed_source(obj, guid, sha, ((101, 201),))])

    def test_two_unity_instances_keep_distinct_occurrences_and_paths(self):
        observed = json.loads((EXPECTED.parent / "null_pair_expected.json").read_text(encoding="utf-8"))
        self.assertEqual("2022.3.22f1", observed["unityVersion"])
        self.assertTrue(all(observed[key] for key in (
            "sameSourceRenderer", "sameMesh", "distinctInstanceRoots", "materialA", "explicitNull")))
        self.assertEqual((1, 1), (observed["materialASlots"], observed["nullSlots"]))
        self.assertEqual((-1.0, 1.0), (observed["materialALocalPosition"]["x"],
                                        observed["nullLocalPosition"]["x"]))
        base = source("Null_Source.prefab")
        pair = source("Null_TwoInstances.prefab")
        self.assertEqual(pair.asset_guid, observed["pairGuid"])
        self.assertEqual(base.asset_guid, observed["sourceGuid"])
        load = lambda _package, guid: base if guid == base.asset_guid else None
        first = project_occurrences(pair, "root-one", load)
        second = project_occurrences(pair, "root-two", load)
        broken = project_occurrences(pair, "broken-root", lambda _package, _guid: None)
        self.assertEqual([], broken.records)
        self.assertEqual(["MISSING_SOURCE", "MISSING_SOURCE"],
                         [issue["code"] for issue in broken.issues])
        self.assertEqual([], model_instance_sources(broken))
        self.assertEqual(([], []), (first.issues, second.issues))
        self.assertEqual((2, 2), (len(first.records), len(second.records)))
        self.assertEqual({(base.asset_guid, int(observed["sourceRendererFileId"]))}, {
            (row["source_key"]["source_asset_guid"], row["source_key"]["renderer_file_id"])
            for row in first.records})
        self.assertEqual({(observed["meshGuid"], int(observed["meshFileId"]))}, {
            (row["mesh"]["mesh_guid"], row["mesh"]["mesh_file_id"])
            for row in first.records})
        self.assertEqual(2, len({row["occurrence_id"] for row in first.records}))
        self.assertEqual(2, len({row["instance_edge_path"][0]["prefab_instance_file_id"]
                                 for row in first.records}))
        base_material_guid = next(line.split(":", 1)[1].strip() for line in
                                  (ASSETS / "Materials" / "Base.mat.meta").read_text(
                                      encoding="utf-8").splitlines() if line.startswith("guid:"))
        self.assertEqual({base_material_guid, None}, {
            row["materials"][0]["guid"] if row["materials"][0] else None
            for row in first.records})
        self.assertTrue(set(row["occurrence_id"] for row in first.records).isdisjoint(
            row["occurrence_id"] for row in second.records))

    def test_prefab_local_model_source_requires_exact_chain_and_witness(self):
        observed = json.loads((EXPECTED.parent / "null_chain_expected.json").read_text(encoding="utf-8"))
        mapping = json.loads((EXPECTED.parent / "null_fbx_witness_mapping.json").read_text(encoding="utf-8"))
        model = ASSETS / "Model.fbx"
        meta = ASSETS / "Model.fbx.meta"
        model_sha, meta_sha = source_sha256(model), source_sha256(meta)
        self.assertEqual((model_sha, meta_sha),
                         (mapping["source_fbx_sha256"], mapping["source_meta_sha256"]))
        mapped = next(item for item in mapping["models"]
                      if any(str(row["mesh_local_id"]) == observed["meshFileId"]
                             for row in item["renderers"]))
        renderer = next(row for row in mapped["renderers"]
                        if str(row["mesh_local_id"]) == observed["meshFileId"])
        # The Blender integration probe checks the raw FBX Geometry UID; this
        # pure-Python witness row tests only source-chain candidate gating.
        witness = ModelWitnessIndex([ModelIdentityRow(
            mapping["model_guid"], int(mapped["model_uid"]), 87319098,
            int(mapped["transform_local_id"]), int(mapped["game_object_local_id"]),
            int(renderer["class_id"]), int(renderer["renderer_local_id"]),
            int(renderer["mesh_local_id"]))], {mapping["model_guid"]: model_sha})
        base = source("Null_Source.prefab")
        variant = source("Null_Override.prefab")
        projection = project_occurrences(
            variant, "null-chain", lambda _package, guid: base if guid == base.asset_guid else None)
        self.assertEqual([], projection.issues)
        row, = projection.records
        row["mesh"].update(source_package_id="synthetic", source_sha256=model_sha)
        self.assertEqual("PREFAB_LOCAL", row["source_key"]["source_kind"])
        self.assertEqual((observed["variantGuid"], observed["sourceGuid"]),
                         (row["root_asset_guid"], row["instance_edge_path"][0]["source_prefab_guid"]))
        self.assertEqual((observed["immediateRendererGuid"], int(observed["immediateRendererFileId"])),
                         (row["source_key"]["source_asset_guid"], row["source_key"]["renderer_file_id"]))
        self.assertEqual((observed["originalRendererGuid"], int(observed["originalRendererFileId"])),
                         (row["source_key"]["source_asset_guid"], row["source_key"]["renderer_file_id"]))
        self.assertEqual(observed["sourceOwnerGuid"], row["owner"]["source_asset_guid"])
        self.assertEqual(int(observed["sourceOwnerFileId"]), row["owner"]["owner_game_object_id"])
        self.assertEqual("MeshRenderer", observed["rendererType"])
        self.assertEqual(23, row["renderer_class_id"])
        self.assertEqual("Assets/Oracle/Model.fbx", observed["modelAssetPath"])
        self.assertEqual((observed["meshGuid"], int(observed["meshFileId"])),
                         (row["mesh"]["mesh_guid"], row["mesh"]["mesh_file_id"]))
        self.assertEqual((1, {0: None}, "EXACT"),
                         (row["material_slot_count"], row["materials"], row["material_status"]))
        expected = [(observed["meshGuid"], row["instance_edge_path"])]
        self.assertEqual(expected, model_instance_sources(projection, witness))
        self.assertEqual([(observed["meshGuid"], row["instance_edge_path"],
                           ((int(mapped["model_uid"]), 87319098),))],
                         model_instance_plans(projection, witness))
        self.assertEqual([], model_instance_sources(projection))
        self.assertEqual([], model_instance_plans(projection))
        for field, wrong in (("mesh_guid", "a" * 32), ("mesh_file_id", -1),
                             ("source_sha256", "0" * 64)):
            changed = copy.deepcopy(row)
            changed["mesh"][field] = wrong
            with self.subTest(field=field):
                self.assertEqual([], model_instance_sources(type(projection)([changed], []), witness))
        changed = copy.deepcopy(row)
        changed["instance_edge_path"][0]["source_prefab_guid"] = "a" * 32
        changed["occurrence_id"] = occurrence_identity(changed)
        self.assertEqual([], model_instance_sources(type(projection)([changed], []), witness))
        changed = copy.deepcopy(row)
        changed["renderer_class_id"] = 137
        self.assertEqual([], model_instance_sources(type(projection)([changed], []), witness))

    def test_unity_authored_null_is_known_not_unresolved(self):
        observed = json.loads(EXPECTED.read_text(encoding="utf-8"))
        self.assertEqual("2022.3.22f1", observed["unityVersion"])
        self.assertEqual(1, observed["sourceSlots"])
        self.assertTrue(observed["sourceHasMaterial"])
        self.assertEqual(1, observed["variantSlots"])
        self.assertTrue(observed["variantIsNull"])
        self.assertEqual(1, observed["nullModifications"])
        self.assertTrue(observed["sharedMeshSame"])
        model_guid = next(line.split(":", 1)[1].strip() for line in
                          (ASSETS / "Model.fbx.meta").read_text(encoding="utf-8").splitlines()
                          if line.startswith("guid:"))
        self.assertEqual(model_guid, observed["meshGuid"])
        base = source("Null_Source.prefab")
        variant = source("Null_Override.prefab")
        modifications = [item for item in variant.prefab.modifications()
                         if item.property_path == "m_Materials.Array.data[0]"]
        self.assertEqual(1, len(modifications))
        self.assertEqual({"fileID": 0}, modifications[0].object_reference)
        projection = project_occurrences(
            variant, "synthetic", lambda _package, guid: base if guid == base.asset_guid else None)
        self.assertEqual([], projection.issues)
        self.assertEqual(1, len(projection.records))
        self.assertEqual(1, projection.records[0]["material_slot_count"])
        self.assertEqual({0: None}, projection.records[0]["materials"])
        self.assertEqual("EXACT", projection.records[0]["material_status"])
        self.assertEqual(model_guid, projection.records[0]["mesh"]["mesh_guid"])
        self.assertEqual(int(observed["meshFileId"]), projection.records[0]["mesh"]["mesh_file_id"])


if __name__ == "__main__":
    unittest.main()
