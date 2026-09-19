import json
import tempfile
import unittest
from pathlib import Path

from tools.vapb_oracle_analysis.analysis import analyze_observation
from tools.vapb_oracle_analysis.ingest import ingest_raw
from tools.vapb_oracle_analysis.index import build_sqlite_index
from tools.vapb_oracle_analysis.model import adapt_observation, InputInvalid
from tools.vapb_oracle_analysis.report import public_report
from tools.vapb_oracle_analysis.legacy import legacy_assertions
from tools.vapb_oracle_analysis.version import compare_versions
from tools.vapb_oracle_analysis.roundtrip import roundtrip_diff


def fixture():
    def prefab(guid, name, mesh_guid):
        return {
            "guid": guid,
            "assetPath": f"Assets/{name}.prefab",
            "objects": [
                {"type": "UnityEngine.Transform", "hierarchyPath": "Root", "globalObjectId": guid + "0000000000000000", "materials": []},
                {"type": "UnityEngine.Animator", "hierarchyPath": "Root", "globalObjectId": guid + "0000000000000001", "hasAvatar": True, "avatarIsHuman": True, "avatarIsValid": True, "materials": []},
                {"type": "UnityEngine.SkinnedMeshRenderer", "hierarchyPath": "Root/Body", "globalObjectId": guid + "0000000000000002", "meshGuid": mesh_guid, "meshLocalFileID": "1", "blendShapeCount": 2, "boneCount": 4, "hasRootBone": True, "materials": [{"slot": 0, "guid": "a" * 32, "localFileID": "1", "shaderName": "Synthetic" , "textureProperties": [{"propertyName": "_MainTex", "guid": "b" * 32, "localFileID": "2", "resolved": True}]}]},
            ],
            "propertyModifications": [{"resolutionStatus": "RESOLVED_BY_PREFAB_API", "propertyPath": "m_Name"}],
            "structuralSummary": {"animatorCount": 1, "avatarCount": 1, "validAvatarCount": 1, "humanAvatarCount": 1, "skinnedMeshRendererCount": 1, "uniqueMeshCount": 1, "materialSlotCount": 1, "blendShapeCount": 2, "boneReferenceCount": 4, "rootBoneCount": 1},
        }
    return {"schemaVersion": "0.2", "runId": "synthetic-run", "unityVersion": "2022.3", "accessMethod": "synthetic", "caseId": "synthetic", "checkpoint": "COMPLETE", "observed": {"prefabs": [prefab("1" * 32, "A", "c" * 32), prefab("2" * 32, "B", "d" * 32)]}, "derived": {"prefabCount": 2, "objectCount": 6, "materialSlotCount": 2}, "limitations": []}


class OracleAnalysisTests(unittest.TestCase):
    def test_adapter_preserves_observed_and_builds_typed_edges(self):
        canonical = adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json")
        self.assertEqual(canonical["canonicalVersion"], "1")
        self.assertEqual(canonical["provenance"]["rawSha256"], "hash")
        self.assertTrue(any(edge["role"] == "REFERENCES_TEXTURE" for edge in canonical["observed"]["edges"]))

    def test_analysis_is_name_and_order_invariant(self):
        first = analyze_observation(adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json"))
        changed = fixture()
        changed["observed"]["prefabs"].reverse()
        changed["observed"]["prefabs"][0]["assetPath"] = "Assets/renamed.prefab"
        second = analyze_observation(adapt_observation(changed, raw_sha256="hash", source_label="synthetic.json"))
        self.assertEqual(first["prefabSignatures"], second["prefabSignatures"])
        self.assertEqual(first["candidateComparison"]["classification"], "MULTIPLE_VALID_VARIANTS")

    def test_invalid_input_fails_closed(self):
        with self.assertRaises(InputInvalid):
            adapt_observation({"schemaVersion": "9.9"}, raw_sha256="x", source_label="bad.json")

    def test_public_report_allowlist_has_no_raw_identity(self):
        canonical = adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json")
        report = public_report(analyze_observation(canonical))
        encoded = json.dumps(report)
        self.assertNotIn("a" * 32, encoded)
        self.assertNotIn("Assets/", encoded)
        self.assertIn("candidateComparison", report)

    def test_sqlite_index_is_rebuildable(self):
        canonical = adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json")
        with tempfile.TemporaryDirectory() as directory:
            path = build_sqlite_index(canonical, Path(directory) / "index.sqlite")
            self.assertTrue(path.exists())
            import sqlite3
            db = sqlite3.connect(path)
            try:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM signatures WHERE entity_id NOT IN (SELECT entity_id FROM entities)").fetchone()[0], 0)
            finally:
                db.close()

    def test_ingest_does_not_modify_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.json"
            raw.write_text(json.dumps(fixture()), encoding="utf-8")
            before = raw.read_bytes()
            record = ingest_raw(raw, Path(directory) / "vault")
            self.assertEqual(before, raw.read_bytes())
            self.assertTrue(Path(record["vaultPath"]).exists())

    def test_ambiguity_never_automatically_selects(self):
        result = analyze_observation(adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json"))
        self.assertFalse(result["candidateComparison"]["automaticSelection"])
        self.assertIn(result["candidateComparison"]["classification"], {"MULTIPLE_VALID_VARIANTS", "USER_CHOICE_REQUIRED"})

    def test_version_and_roundtrip_are_explicit_about_unknowns(self):
        result = analyze_observation(adapt_observation(fixture(), raw_sha256="hash", source_label="synthetic.json"))
        self.assertEqual(compare_versions(result, {"coverage": result["coverage"]})["status"], "UNKNOWN")
        self.assertEqual(roundtrip_diff({"globalObjectId": "a"}, {"globalObjectId": "b"})["status"], "NOT_COMPARABLE")
        self.assertEqual(roundtrip_diff({"globalObjectId": "a"}, {"globalObjectId": "b"}, {"a": "b"})["status"], "EXPECTED_CHANGE")
        self.assertEqual(legacy_assertions(result)[0]["status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
