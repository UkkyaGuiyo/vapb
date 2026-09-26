from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
from unitypackage_blender_importer.unity.occurrence_projection import PrefabSource, project_occurrences


ROOT = "a" * 32
CHILD = "b" * 32
MESH = "c" * 32
MAT = "d" * 32
OVERRIDE = "e" * 32


def direct(guid=MESH, renderer=-20, owner=10, valid=True, mesh_filter=False):
    components = f"  - component: {{fileID: {renderer}}}\n"
    if mesh_filter:
        components += "  - component: {fileID: 30}\n"
    if not valid:
        components = "  - component: {fileID: 999}\n"
    filter_doc = f"""--- !u!33 &30
MeshFilter:
  m_GameObject: {{fileID: {owner}}}
  m_Mesh: {{fileID: -31, guid: {guid}, type: 3}}
""" if mesh_filter else ""
    mesh_ref = "{fileID: 0}" if mesh_filter else f"{{fileID: -31, guid: {guid}, type: 3}}"
    return f"""%YAML 1.1
--- !u!1 &{owner}
GameObject:
  m_Name: DisplayOnly
  m_Component:
{components}{filter_doc}--- !u!{23 if mesh_filter else 137} &{renderer}
Renderer:
  m_GameObject: {{fileID: {owner}}}
  m_Mesh: {mesh_ref}
  m_Materials:
  - {{fileID: 2100000, guid: {MAT}, type: 2}}
"""


def instance(source=CHILD, ids=(-101, -102), target=None, material=OVERRIDE):
    chunks = ["%YAML 1.1\n"]
    for i in ids:
        change = ""
        if target is not None:
            change = f"""  m_Modification:
    m_Modifications:
    - target: {{fileID: {target}, guid: {source}, type: 3}}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {{fileID: 2100000, guid: {material}, type: 2}}
"""
        chunks.append(f"""--- !u!1001 &{i}
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {source}, type: 3}}
{change}""")
    return "".join(chunks)


class OccurrenceProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def source(self, guid, body, member=None, package="pkg", revision="rev1"):
        path = self.directory / f"{guid}.prefab"
        path.write_text(body, encoding="utf-8")
        path.with_name(path.name + ".meta").write_text(f"guid: {guid}\n", encoding="utf-8")
        return PrefabSource(parse_prefab(path), package, member or guid, revision)

    def project(self, root, *sources):
        by_guid = {(s.package_id, s.asset_guid or s.prefab.asset_guid): s for s in sources}
        return project_occurrences(root, "import-1:member-1", lambda package, guid: by_guid.get((package, guid)))

    def test_direct_signed_renderer_mesh_and_scope(self):
        result = self.project(self.source(ROOT, direct()))
        self.assertEqual([], result.issues)
        self.assertEqual(1, len(result.records))
        record = result.records[0]
        self.assertEqual([], record["instance_edge_path"])
        self.assertEqual(-20, record["source_key"]["renderer_file_id"])
        self.assertEqual(-31, record["mesh"]["mesh_file_id"])
        self.assertEqual("rev1", record["source_revision_sha256"])
        self.assertEqual("pkg", record["source_package_id"])
        self.assertEqual(MAT, record["materials"][0]["guid"])
        self.assertEqual("pkg", record["materials"][0]["source_package_id"])
        self.assertEqual(ROOT, record["root_asset_guid"])
        self.assertEqual("EXACT", record["material_status"])

    def test_direct_local_skin_refs_preserve_signed_transform_ids(self):
        payload = direct().replace("  m_Materials:", "  m_Bones:\n  - {fileID: -101}\n  - {fileID: -102}\n  m_RootBone: {fileID: -101}\n  m_Materials:")
        payload += """--- !u!1 &11
GameObject:
  m_Name: Root
--- !u!4 &-101
Transform:
  m_GameObject: {fileID: 11}
  m_Father: {fileID: 0}
--- !u!1 &12
GameObject:
  m_Name: Child
--- !u!4 &-102
Transform:
  m_GameObject: {fileID: 12}
  m_Father: {fileID: -101}
"""
        record = self.project(self.source(ROOT, payload)).records[0]
        self.assertEqual("EXACT", record["skin"]["status"])
        self.assertEqual(["-101", "-102"], [row["transform_file_id"] for row in record["skin"]["bones"]])
        self.assertEqual("-101", record["skin"]["bones"][1]["parent_transform_file_id"])
        self.assertEqual("-101", record["skin"]["root_bone_transform_file_id"])

    def test_missing_and_external_skin_refs_are_unknown(self):
        missing = self.project(self.source(ROOT, direct())).records[0]
        self.assertEqual("UNKNOWN", missing["skin"]["status"])
        external = direct().replace("  m_Materials:",
                                   f"  m_Bones:\n  - {{fileID: -101, guid: {CHILD}}}\n  m_RootBone: {{fileID: -101}}\n  m_Materials:")
        self.assertEqual("UNKNOWN", self.project(self.source(CHILD, external)).records[0]["skin"]["status"])

    def test_nested_skin_override_is_unknown(self):
        root = self.source(ROOT, instance(ids=(10,), target=-20).replace(
            "m_Materials.Array.data[0]", "m_Bones.Array.data[0]"))
        result = self.project(root, self.source(CHILD, direct()))
        self.assertEqual("UNKNOWN", result.records[0]["skin"]["status"])
        self.assertEqual("UNRESOLVED_SKIN_OVERRIDE", result.issues[0]["code"])

    def test_repeated_real_edges_and_exact_per_instance_override(self):
        root = self.source(ROOT, instance(target=-20))
        child = self.source(CHILD, direct())
        result = self.project(root, child)
        self.assertEqual([], result.issues)
        self.assertEqual([-101, -102], [r["instance_edge_path"][0]["prefab_instance_file_id"] for r in result.records])
        self.assertEqual([OVERRIDE, OVERRIDE], [r["materials"][0]["guid"] for r in result.records])
        self.assertNotEqual(result.records[0]["occurrence_id"], result.records[1]["occurrence_id"])
        self.assertEqual([CHILD, CHILD], [r["source_key"]["source_asset_guid"] for r in result.records])

    def test_no_cross_product_or_wrong_guid_collision(self):
        unrelated = "f" * 32
        root = self.source(ROOT, instance(ids=(10,)))
        child = self.source(CHILD, direct())
        other = self.source(unrelated, direct(renderer=-20))
        result = self.project(root, child, other)
        self.assertEqual(1, len(result.records))
        self.assertEqual(CHILD, result.records[0]["source_key"]["source_asset_guid"])

    def test_invalid_owner_and_missing_source_fail_closed(self):
        bad = self.project(self.source(ROOT, direct(valid=False)))
        self.assertEqual([], bad.records)
        self.assertEqual("INVALID_OWNER", bad.issues[0]["code"])
        missing = self.project(self.source(ROOT, instance(ids=(10,))))
        self.assertEqual([], missing.records)
        self.assertEqual("MISSING_SOURCE", missing.issues[0]["code"])

    def test_cycle_and_revision_provenance(self):
        root = self.source(ROOT, instance(ids=(10,)), revision="root-sha")
        child = self.source(CHILD, direct() + instance(source=ROOT, ids=(11,)).replace("%YAML 1.1\n", ""), revision="child-sha")
        result = self.project(root, child, root)
        self.assertEqual(1, len(result.records))
        self.assertEqual("child-sha", result.records[0]["source_revision_sha256"])
        self.assertEqual("CYCLE", result.issues[0]["code"])

    def test_each_instance_keeps_its_own_material_override(self):
        left = instance(ids=(10,), target=-20, material=OVERRIDE)
        right = instance(ids=(11,), target=-20, material="9" * 32).replace("%YAML 1.1\n", "")
        root = self.source(ROOT, left + right)
        result = self.project(root, self.source(CHILD, direct()))
        self.assertEqual([], result.issues)
        self.assertEqual([OVERRIDE, "9" * 32], [r["materials"][0]["guid"] for r in result.records])

    def test_ambiguous_override_under_one_instance_does_not_choose(self):
        nested = "f" * 32
        root = self.source(ROOT, instance(source=nested, ids=(10,), target=-20))
        middle = self.source(nested, instance(source=CHILD, ids=(11, 12)))
        leaf = self.source(CHILD, direct())
        # The parent target identifies CHILD, not the immediate nested Prefab.
        root.prefab.documents[0].raw = root.prefab.documents[0].raw.replace(
            f"fileID: -20, guid: {nested}", f"fileID: -20, guid: {CHILD}"
        )
        result = self.project(root, middle, leaf)
        self.assertEqual(2, len(result.records))
        self.assertEqual([MAT, MAT], [r["materials"][0]["guid"] for r in result.records])
        self.assertEqual(["UNKNOWN", "UNKNOWN"], [r["material_status"] for r in result.records])
        self.assertEqual("AMBIGUOUS_OVERRIDE_TARGET", result.issues[0]["code"])

    def test_mesh_renderer_requires_explicit_valid_mesh_filter(self):
        good = self.project(self.source(ROOT, direct(mesh_filter=True)))
        self.assertEqual(1, len(good.records))
        self.assertEqual(-31, good.records[0]["mesh"]["mesh_file_id"])
        bad = self.project(self.source(CHILD, direct(mesh_filter=False).replace("!u!137", "!u!23")))
        self.assertEqual([], bad.records)
        self.assertEqual("INVALID_MESH_FILTER", bad.issues[0]["code"])

    def test_binary_model_source_stays_unresolved(self):
        model = PrefabSource(None, "pkg", "model-member", "binary-sha", CHILD)
        result = self.project(self.source(ROOT, instance(ids=(10,))), model)
        self.assertEqual([], result.records)
        self.assertEqual("UNRESOLVED_SOURCE", result.issues[0]["code"])

    def test_null_override_marks_material_unknown(self):
        root = self.source(ROOT, instance(ids=(10,), target=-20).replace(
            f"objectReference: {{fileID: 2100000, guid: {OVERRIDE}, type: 2}}",
            "objectReference: {fileID: 0}",
        ))
        result = self.project(root, self.source(CHILD, direct()))
        self.assertEqual(1, len(result.records))
        self.assertEqual("UNKNOWN", result.records[0]["material_status"])
        self.assertEqual("UNRESOLVED_OVERRIDE", result.issues[0]["code"])

    def test_duplicate_source_document_id_rejected(self):
        payload = direct() + direct(renderer=-20, owner=11).replace("%YAML 1.1\n", "")
        result = self.project(self.source(ROOT, payload))
        self.assertEqual([], result.records)
        self.assertEqual("DUPLICATE_SOURCE_FILE_ID", result.issues[0]["code"])

    def test_occurrence_identity_excludes_revision_but_preserves_scope(self):
        first = self.project(self.source(ROOT, direct(), revision="rev-one")).records[0]
        second = self.project(self.source(ROOT, direct(), revision="rev-two")).records[0]
        self.assertEqual(first["occurrence_id"], second["occurrence_id"])
        self.assertNotEqual(first["source_revision_sha256"], second["source_revision_sha256"])

    def test_cross_package_source_and_container_material_scope(self):
        root = self.source(ROOT, instance(ids=(10,), target=-20), package="container")
        child = self.source(CHILD, direct(), package="provider")
        result = project_occurrences(root, "import-1:member-1", lambda package, guid: child)
        self.assertEqual([], result.issues)
        record = result.records[0]
        self.assertEqual("provider", record["source_package_id"])
        self.assertEqual("container", record["materials"][0]["source_package_id"])
        self.assertEqual("provider", record["instance_edge_path"][0]["source_package_id"])

    def test_wrapped_source_prefab_reference(self):
        payload = instance(ids=(10,)).replace(
            f"m_SourcePrefab: {{fileID: 1001, guid: {CHILD}, type: 3}}",
            f"m_SourcePrefab: {{fileID: 1001,\n    guid: {CHILD}, type: 3}}",
        )
        result = self.project(self.source(ROOT, payload), self.source(CHILD, direct()))
        self.assertEqual([], result.issues)
        self.assertEqual(1, len(result.records))

    def test_missing_override_target_marks_subtree_material_unknown(self):
        root = self.source(ROOT, instance(ids=(10,), target=-999))
        result = self.project(root, self.source(CHILD, direct()))
        self.assertEqual(1, len(result.records))
        self.assertEqual("UNKNOWN", result.records[0]["material_status"])
        self.assertEqual("UNRESOLVED_OVERRIDE", result.issues[0]["code"])

    def test_material_slot_count_and_explicit_null(self):
        payload = direct().replace(
            f"{{fileID: 2100000, guid: {MAT}, type: 2}}", "{fileID: 0}"
        )
        record = self.project(self.source(ROOT, payload)).records[0]
        self.assertEqual(1, record["material_slot_count"])
        self.assertEqual({0: None}, record["materials"])
        self.assertEqual("EXACT", record["material_status"])

    def test_absent_material_fields_mean_zero_slots(self):
        payload = direct().replace(
            f"  m_Materials:\n  - {{fileID: 2100000, guid: {MAT}, type: 2}}\n", ""
        )
        record = self.project(self.source(ROOT, payload)).records[0]
        self.assertEqual(0, record["material_slot_count"])
        self.assertEqual({}, record["materials"])

    def test_malformed_material_slot_is_unknown(self):
        payload = direct().replace(
            f"{{fileID: 2100000, guid: {MAT}, type: 2}}", "{fileID: 2100000}"
        )
        record = self.project(self.source(ROOT, payload)).records[0]
        self.assertEqual(1, record["material_slot_count"])
        self.assertEqual("UNKNOWN", record["material_status"])

    def test_override_outside_serialized_slots_is_unknown(self):
        root = self.source(ROOT, instance(ids=(10,), target=-20).replace(
            "m_Materials.Array.data[0]", "m_Materials.Array.data[2]"
        ))
        result = self.project(root, self.source(CHILD, direct()))
        self.assertEqual("UNKNOWN", result.records[0]["material_status"])
        self.assertEqual(1, result.records[0]["material_slot_count"])
        self.assertEqual("OVERRIDE_SLOT_OUT_OF_RANGE", result.issues[0]["code"])


if __name__ == "__main__":
    unittest.main()
