"""Unity 2022.3.22f1 authored nested/stripped Material alias regression.

The checked-in Oracle report is independent of VAPB projection. Model UID
placeholders here are unused by projection; this test does not prove native
FBX realization. The source Renderer/GameObject/Mesh IDs come from Unity's
public AssetDatabase API on the exact checked-in synthetic FBX revision.
"""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest

from unitypackage_blender_importer.blender.model_witness_bridge import plan_witness_material_dependencies
from unitypackage_blender_importer.unity.model_identity_witness import (
    ModelIdentityRow, ModelWitnessIndex,
)
from unitypackage_blender_importer.unity.occurrence_projection import (
    PrefabSource, project_occurrences,
)
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab, ref_file_id, ref_guid


ASSETS = Path(__file__).with_name("unity_alias_oracle") / "Assets" / "Oracle"
ORACLE = Path(__file__).with_name("unity_alias_oracle") / "oracle_expected.json"
GRAPH = ORACLE.with_name("alias_graph.json")


def source(filename):
    path = ASSETS / filename
    prefab = parse_prefab(path)
    return PrefabSource(prefab, "synthetic", filename,
                        hashlib.sha256(path.read_bytes()).hexdigest(), prefab.asset_guid)


class PrefabMaterialAliasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
        cls.cases = {case["caseName"]: case for case in cls.oracle["cases"]}
        cls.model_guid = cls.oracle["modelR1"]["guid"].lower()
        cls.model_sha = hashlib.sha256((ASSETS / "Model.fbx").read_bytes()).hexdigest()
        cls.model = PrefabSource(None, "synthetic", "Model.fbx", cls.model_sha, cls.model_guid)
        cls.variant = source("ModelVariant.prefab")
        cls.container = source("Container.prefab")
        cls.e0 = source("E0_Direct.prefab")
        cls.e1 = source("E1_Alias.prefab")
        cls.e2 = source("E2_Unrelated.prefab")
        cls.sources = {item.asset_guid: item for item in (cls.model, cls.variant, cls.container)}
        rows = []
        for number, role in enumerate(("R1", "R2"), start=1):
            def local_id(suffix):
                identity = cls.oracle[f"model{role}{suffix}"]
                if identity["guid"].lower() != cls.model_guid:
                    raise AssertionError("Oracle source ID is outside the model asset")
                return int(identity["fileId"])
            rows.append(ModelIdentityRow(cls.model_guid, number, number + 100,
                                         local_id("Transform"), local_id("Owner"),
                                         23, local_id(""), local_id("Mesh")))
        cls.witness = ModelWitnessIndex(rows, {cls.model_guid: cls.model_sha})

    @staticmethod
    def identity(value):
        return (str(value.get("guid", "")).lower(),
                str(value.get("fileId", value.get("fileID", ""))))

    @staticmethod
    def slot_matches(record, oracle_renderer):
        actual = record["materials"].get(0)
        expected = oracle_renderer["slotZeroMaterial"]
        return (isinstance(actual, dict)
                and actual["guid"].lower() == expected["guid"].lower()
                and str(actual["file_id"]) == expected["fileId"])

    def project(self, root, witness=None):
        return project_occurrences(root, root.member_id,
                                   lambda _package, guid: self.sources.get(guid),
                                   model_witness=self.witness if witness is None else witness)

    def project_with_container(self, root, container, witness=None):
        sources = {**self.sources, self.container.asset_guid: container}
        return project_occurrences(root, root.member_id,
                                   lambda _package, guid: sources.get(guid),
                                   model_witness=self.witness if witness is None else witness)

    def material_override(self, source):
        rows = [item for item in source.prefab.modifications()
                if item.property_path == "m_Materials.Array.data[0]"]
        self.assertEqual(1, len(rows))
        return rows[0]

    def alias_document(self, modification):
        self.assertEqual(self.container.asset_guid, modification.target_guid)
        matches = [doc for doc in self.container.prefab.documents
                   if doc.file_id == modification.target_file_id]
        self.assertEqual(1, len(matches))
        self.assertIn("stripped", matches[0].raw)
        return matches[0]

    def model_records(self, projection, renderer_id, instance_id=None):
        rows = [record for record in projection.records
                if record["source_key"]["source_asset_guid"] == self.model_guid
                and record["source_key"]["renderer_file_id"] == renderer_id]
        if instance_id is not None:
            rows = [record for record in rows if any(
                step["container_asset_guid"] == self.container.asset_guid
                and step["prefab_instance_file_id"] == instance_id
                for step in record["instance_edge_path"])]
        return rows

    def test_unity_oracle_proves_stripped_alias_and_one_instance_effect(self):
        self.assertEqual("2022.3.22f1", self.oracle["unityVersion"])
        self.assertEqual("Variant", self.cases["E1_E4_E5"]["prefabType"])
        modification = self.material_override(self.e1)
        alias = self.alias_document(modification)
        self.assertEqual(23, alias.class_id)
        self.assertEqual(self.variant.asset_guid,
                         ref_guid(alias.data["m_CorrespondingSourceObject"]))
        variant_alias_id = ref_file_id(alias.data["m_CorrespondingSourceObject"])
        # Unity exposes the next alias edge through its public API. This local
        # ID does not occur in the serialized Variant or its meta, so the
        # package-only graph cannot silently infer the final model Renderer.
        self.assertFalse(any(doc.file_id == variant_alias_id
                             for doc in self.variant.prefab.documents))
        oracle_rows = {row["role"]: row for row in self.cases["E1_E4_E5"]["renderers"]}
        chain = [self.identity(item)
                 for item in oracle_rows["target_R1"]["correspondingSourceChain"]]
        self.assertEqual((self.variant.asset_guid, str(variant_alias_id)), chain[1])
        self.assertEqual(self.identity(self.oracle["modelR1"]), chain[-1])
        self.assertEqual((modification.target_guid, str(modification.target_file_id)),
                         self.identity(oracle_rows["target_R1"]["sourceAtContainer"]))
        self.assertEqual(self.identity(self.oracle["modelR1"]),
                         self.identity(oracle_rows["target_R1"]["originalSource"]))
        self.assertEqual(self.identity(self.oracle["modelR1"]),
                         self.identity(oracle_rows["other_R1"]["originalSource"]))
        self.assertEqual(self.identity(self.oracle["modelR2"]),
                         self.identity(oracle_rows["sibling_R2"]["originalSource"]))
        self.assertEqual(self.identity(modification.object_reference),
                         self.identity(oracle_rows["target_R1"]["slotZeroMaterial"]))
        self.assertNotEqual(self.identity(oracle_rows["target_R1"]["slotZeroMaterial"]),
                            self.identity(oracle_rows["other_R1"]["slotZeroMaterial"]))
        self.assertEqual(self.identity(oracle_rows["other_R1"]["slotZeroMaterial"]),
                         self.identity(oracle_rows["sibling_R2"]["slotZeroMaterial"]))

    def test_machine_readable_graph_marks_serialized_identity_break(self):
        graph = json.loads(GRAPH.read_text(encoding="utf-8"))
        self.assertEqual("2022.3.22f1", graph["unity_version"])
        self.assertEqual(self.model_sha, graph["source_sha256"]["Model.fbx"])
        self.assertEqual({"E1", "E2"}, {row["case"] for row in graph["cases"]})
        for row in graph["cases"]:
            source = self.e1 if row["case"] == "E1" else self.e2
            case = self.cases["E1_E4_E5" if row["case"] == "E1" else "E2"]
            override = self.material_override(source)
            alias = self.alias_document(override)
            self.assertEqual((override.target_guid, str(override.target_file_id)),
                             (row["override_target"]["guid"],
                              row["override_target"]["file_id"]))
            self.assertEqual(str(ref_file_id(alias.data["m_PrefabInstance"])),
                             row["container_alias"]["nested_instance_file_id"])
            self.assertEqual((ref_guid(alias.data["m_CorrespondingSourceObject"]),
                              str(ref_file_id(alias.data["m_CorrespondingSourceObject"]))),
                             (row["container_alias"]["corresponding_source"]["guid"],
                              row["container_alias"]["corresponding_source"]["file_id"]))
            oracle_rows = [entry for entry in case["renderers"]
                           if self.identity(entry["sourceAtContainer"])
                           == (override.target_guid, str(override.target_file_id))]
            self.assertEqual(1, len(oracle_rows))
            self.assertEqual([self.identity(entry) for entry in oracle_rows[0]["correspondingSourceChain"]],
                             [(entry["guid"], entry["file_id"])
                              for entry in row["unity_public_api_source_chain"]])
            self.assertEqual("variant_alias_to_model_renderer", row["package_only_break"])
            self.assertFalse(row["serialized_variant_alias_document_present"])

    def test_direct_e0_matches_independent_unity_oracle(self):
        result = self.project(self.e0)
        rows = self.model_records(result, int(self.oracle["modelR1"]["fileId"]))
        self.assertEqual(1, len(rows))
        self.assertTrue(self.slot_matches(rows[0], self.cases["E0"]["renderers"][0]))

    def test_nested_alias_e1_fails_closed_only_in_its_instance(self):
        modification = self.material_override(self.e1)
        instance_id = ref_file_id(self.alias_document(modification).data["m_PrefabInstance"])
        result = self.project(self.e1)
        r1_id = int(self.oracle["modelR1"]["fileId"])
        r2_id = int(self.oracle["modelR2"]["fileId"])
        affected = self.model_records(result, r1_id, instance_id)
        other = [row for row in self.model_records(result, r1_id) if row not in affected]
        sibling = self.model_records(result, r2_id, instance_id)
        other_sibling = [row for row in self.model_records(result, r2_id) if row not in sibling]
        self.assertEqual((1, 1, 1, 1),
                         (len(affected), len(other), len(sibling), len(other_sibling)))
        oracle_rows = {row["role"]: row for row in self.cases["E1_E4_E5"]["renderers"]}
        self.assertTrue(self.slot_matches(other[0], oracle_rows["other_R1"]))
        self.assertEqual(["UNKNOWN", "UNKNOWN"],
                         [affected[0]["material_status"], sibling[0]["material_status"]])
        self.assertEqual(["PARTIAL", "PARTIAL"],
                         [other[0]["material_status"], other_sibling[0]["material_status"]])
        self.assertTrue(any(issue["code"] == "UNRESOLVED_ALIAS_OVERRIDE"
                            and issue.get("target_renderer_file_id") == modification.target_file_id
                            and issue.get("uncertainty_scope") == "NESTED_INSTANCE"
                            for issue in result.issues))

    def test_other_instance_e2_does_not_poison_target_instance(self):
        modification = self.material_override(self.e2)
        instance_id = ref_file_id(self.alias_document(modification).data["m_PrefabInstance"])
        result = self.project(self.e2)
        r1_affected = self.model_records(result, int(self.oracle["modelR1"]["fileId"]), instance_id)
        r2_affected = self.model_records(result, int(self.oracle["modelR2"]["fileId"]), instance_id)
        r1_target = [row for row in self.model_records(result, int(self.oracle["modelR1"]["fileId"]))
                     if row not in r1_affected]
        r2_target = [row for row in self.model_records(result, int(self.oracle["modelR2"]["fileId"]))
                     if row not in r2_affected]
        self.assertEqual((1, 1, 1, 1),
                         tuple(map(len, (r1_affected, r2_affected, r1_target, r2_target))))
        oracle_rows = {row["role"]: row for row in self.cases["E2"]["renderers"]}
        self.assertTrue(self.slot_matches(r1_target[0], oracle_rows["target_R1"]))
        self.assertTrue(self.slot_matches(r2_target[0], oracle_rows["sibling_R2"]))
        self.assertEqual(["UNKNOWN", "UNKNOWN"],
                         [r1_affected[0]["material_status"], r2_affected[0]["material_status"]])
        self.assertEqual(["PARTIAL", "PARTIAL"],
                         [r1_target[0]["material_status"], r2_target[0]["material_status"]])
        self.assertEqual(["NESTED_INSTANCE"],
                         [issue["uncertainty_scope"] for issue in result.issues
                          if issue["code"] == "UNRESOLVED_ALIAS_OVERRIDE"])

    def test_wrong_override_guid_or_local_id_does_not_bind(self):
        modification = self.material_override(self.e1)
        for replacement in (
                f"fileID: {modification.target_file_id}, guid: {'f' * 32}",
                f"fileID: {modification.target_file_id + 1}, guid: {modification.target_guid}"):
            with self.subTest(replacement=replacement):
                prefab = deepcopy(self.e1.prefab)
                token = (f"fileID: {modification.target_file_id}, "
                         f"guid: {modification.target_guid}")
                document = next(doc for doc in prefab.documents if doc.class_id == 1001)
                self.assertEqual(1, document.raw.count(token))
                document.raw = document.raw.replace(token, replacement)
                result = self.project(replace(self.e1, prefab=prefab))
                self.assertEqual(4, len(result.records))
                changed = self.cases["E1_E4_E5"]["renderers"][0]["slotZeroMaterial"]["guid"]
                self.assertTrue(all(row["material_status"] == "PARTIAL"
                                    and row["materials"].get(0, {}).get("guid") != changed
                                    for row in result.records))
                self.assertIn("UNRESOLVED_OVERRIDE", [issue["code"] for issue in result.issues])

    def test_bad_corresponding_source_or_instance_never_guesses_binding(self):
        modification = self.material_override(self.e1)
        for field, bad_value in (
                ("m_CorrespondingSourceObject", {"fileID": -1, "guid": "f" * 32}),
                ("m_PrefabInstance", {"fileID": -1})):
            with self.subTest(field=field):
                prefab = deepcopy(self.container.prefab)
                alias = next(doc for doc in prefab.documents
                             if doc.file_id == modification.target_file_id)
                alias.data[field] = bad_value
                result = self.project_with_container(
                    self.e1, replace(self.container, prefab=prefab))
                self.assertEqual(4, len(result.records))
                changed = self.cases["E1_E4_E5"]["renderers"][0]["slotZeroMaterial"]["guid"]
                self.assertTrue(all(row["materials"].get(0, {}).get("guid") != changed
                                    for row in result.records))
                self.assertIn("UNRESOLVED_ALIAS_OVERRIDE",
                              [issue["code"] for issue in result.issues])
                self.assertEqual(["CHILD_PREFAB"],
                                 [issue["uncertainty_scope"] for issue in result.issues
                                  if issue["code"] == "UNRESOLVED_ALIAS_OVERRIDE"])
                self.assertTrue(any(row["material_status"] == "UNKNOWN"
                                    for row in result.records))

    def test_wrong_model_witness_revision_rejects_projection(self):
        stale = ModelWitnessIndex(self.witness.source_rows(self.model_guid),
                                  {self.model_guid: "0" * 64})
        result = self.project(self.e1, witness=stale)
        self.assertEqual([], result.records)
        self.assertIn("UNRESOLVED_SOURCE", [issue["code"] for issue in result.issues])

    def test_alias_unknown_rows_do_not_plan_native_material_writes(self):
        result = self.project(self.e1)
        bindings = []
        for index, record in enumerate(result.records):
            record["mesh"].update(source_package_id="synthetic",
                                  source_sha256=self.model_sha)
            bindings.append((record, {
                "_vapb_fbx_realization_id": f"native-{index}",
                "_vapb_fbx_model_uid": str(index + 1),
                "_vapb_fbx_geometry_uid": str(index + 101),
                "_vapb_fbx_object_receipt_id": f"object-{index}",
                "_vapb_fbx_mesh_receipt_id": f"mesh-{index}",
            }))
        dependencies = plan_witness_material_dependencies(bindings, "a" * 64)
        self.assertEqual(2, len(dependencies))
        known = {record["occurrence_id"] for record in result.records
                 if record["material_status"] == "PARTIAL"}
        self.assertEqual(known, {row["consumer_occurrence_id"] for row in dependencies})


if __name__ == "__main__":
    unittest.main()
