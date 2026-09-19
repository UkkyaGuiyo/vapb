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
from tools.vapb_oracle.observation_context import require_isolated
from tools.unity_semantic_oracle.baseline_manifest import manifest


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

    def test_merged_context_is_not_valid_isolated_evidence(self):
        raw = fixture(); raw["observationContext"] = "MERGED_CORPUS"
        canonical = adapt_observation(raw, raw_sha256="hash", source_label="merged.json")
        with self.assertRaises(ValueError): require_isolated(canonical)
        result = analyze_observation(canonical)
        self.assertEqual(result["contaminationStatus"], "CONTAMINATED_CONTEXT")

    def test_isolated_context_can_be_required(self):
        raw = fixture(); raw["observationContext"] = "ISOLATED_PACKAGE"; raw["packageProvenance"] = {"isolationVerified": True, "baselineId": "baseline", "baselineHash": "a" * 64, "packageSha256": "b" * 64}
        canonical = adapt_observation(raw, raw_sha256="hash", source_label="isolated.json")
        require_isolated(canonical)

    def test_isolated_context_requires_attested_baseline_and_package_hash(self):
        raw = fixture(); raw["observationContext"] = "ISOLATED_PACKAGE"; raw["packageProvenance"] = {"isolationVerified": True}
        canonical = adapt_observation(raw, raw_sha256="hash", source_label="isolated.json")
        with self.assertRaises(ValueError): require_isolated(canonical)

    def test_isolated_context_rejects_invalid_hashes_and_collisions(self):
        raw = fixture(); raw["observationContext"] = "ISOLATED_PACKAGE"; raw["packageProvenance"] = {"isolationVerified": True, "baselineId": "baseline", "baselineHash": "z" * 64, "packageSha256": "z" * 64}; raw["collisionEvents"] = [{"code": "PATH_COLLISION"}]
        canonical = adapt_observation(raw, raw_sha256="hash", source_label="isolated.json")
        with self.assertRaises(ValueError): require_isolated(canonical)

    def test_baseline_manifest_does_not_include_its_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"; root.mkdir()
            (root / "ProjectSettings").mkdir()
            (root / "ProjectSettings" / "ProjectVersion.txt").write_text("2022.3", encoding="utf-8")
            self.assertNotIn("baseline.json", {item["path"] for item in manifest(root, exclude_paths={root / "baseline.json"})["files"]})


if __name__ == "__main__":
    unittest.main()
