import copy
import json
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
import prepare_unity_manifest as adapter
from prepare_unity_manifest import adapt_manifest

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/coordinate_holdout_20261007/blender-20261008-01"

class UnityManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
        self.contract = json.loads((EVIDENCE / "contract.json").read_text(encoding="utf-8"))

    def test_frozen_cases_and_material_face_keys_reach_existing_probe(self):
        result = adapt_manifest(self.manifest, self.contract)
        self.assertIsInstance(result, dict)
        self.assertEqual([row["id"] for row in result["cases"]], ["H0", "H1", "H2", "H3"])
        self.assertEqual(result["cases"][0]["source_material_ids"], self.contract["geometry"]["materials"])
        face = result["spec"]["geometry"]["faces"][0]
        self.assertEqual(face["material"], self.contract["geometry"]["faces"][0]["material_id"])
        self.assertEqual(face["uvs"][0]["x"], 100.0)
        self.assertEqual(result["cases"][3]["sha256"], self.manifest["cases"][3]["sha256"])

    def test_reordered_case_and_changed_contract_are_rejected(self):
        wrong = copy.deepcopy(self.manifest)
        wrong["cases"].reverse()
        with self.assertRaises(ValueError): adapt_manifest(wrong, self.contract)
        wrong = copy.deepcopy(self.manifest)
        wrong["contract"]["unity_import_settings"]["globalScale"] = 2.0
        with self.assertRaises(ValueError): adapt_manifest(wrong, self.contract)

    def prepare_inputs(self, root):
        prereg_dir = root / "prereg"; prereg_dir.mkdir()
        contract_path = prereg_dir / "contract.json"
        contract_path.write_text(json.dumps(self.contract), encoding="utf-8")
        oracle_path = prereg_dir / "authored-oracle.json"; oracle_path.write_text("{}", encoding="utf-8")
        source_root = EVIDENCE.parents[2] / "coordinate_holdout_20261007"
        sources = {p.name: adapter.sha256(p) for p in source_root.glob("*.py")}
        prereg = {"status": "FROZEN_BEFORE_EXPORT_AND_IMPORT", "source_sha256": sources,
                  "contract_sha256": adapter.sha256(contract_path), "authored_oracle_sha256": adapter.sha256(oracle_path)}
        prereg_path = prereg_dir / "preregistration.json"
        prereg_path.write_text(json.dumps(prereg), encoding="utf-8")
        manifest = copy.deepcopy(self.manifest)
        manifest["preregistration_sha256"] = adapter.sha256(prereg_path); manifest["source_sha256"] = sources
        for row in manifest["cases"]:
            fbx = root / row["filename"]; fbx.write_bytes(b"test hash-only fixture")
            row["sha256"] = adapter.sha256(fbx)
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, prereg_dir, manifest

    def test_pinned_manifest_is_not_reopened_after_hashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, prereg, manifest = self.prepare_inputs(root)
            expected_sha = adapter.sha256(path); original_sha = adapter.sha256
            def hash_then_replace(candidate):
                digest = original_sha(candidate)
                if Path(candidate) == path:
                    changed = copy.deepcopy(manifest)
                    changed["cases"][0]["materials_by_fixture_identity"][0]["name"] = "CHANGED_AFTER_HASH"
                    path.write_text(json.dumps(changed), encoding="utf-8")
                return digest
            with patch.object(adapter, "sha256", hash_then_replace):
                result = adapter.prepare(path, prereg, expected_sha, root / "output.json")
            self.assertEqual(result["cases"][0]["source_material_names"][0], "VAPB_HO_MATERIAL_A")

    def test_invalid_case_is_rejected_before_any_fbx_path_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, prereg, manifest = self.prepare_inputs(root)
            manifest["cases"][0]["id"] = "../outside"
            manifest["cases"][0]["filename"] = "../outside.fbx"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            try:
                adapter.prepare(path, prereg, adapter.sha256(path), root / "output.json")
            except ValueError as error:
                self.assertIn("CASE_SET", str(error))
            except OSError as error:
                self.fail("Invalid case reached filesystem lookup: " + type(error).__name__)
            else:
                self.fail("Invalid case was accepted")
if __name__ == "__main__": unittest.main()
