import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.corpus_survey.inventory import (
    CorpusPackageError,
    infer_package_groups,
    inventory_package,
    public_safe_summary,
    scan_corpus,
)
from tools.corpus_survey.survey import validate_output_root


def write_unitypackage(path, entries):
    with tarfile.open(path, "w:gz") as archive:
        for guid, pathname, asset in entries:
            for name, payload in (
                (f"{guid}/pathname", pathname.encode()),
                (f"{guid}/asset", asset.encode()),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))


class CorpusInventoryTests(unittest.TestCase):
    def test_raw_output_inside_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_output_root(Path(__file__).resolve().parents[2] / "diagnostics")

    def test_malformed_package_fails_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "broken.unitypackage"
            package.write_bytes(b"not a tar archive")
            with self.assertRaises(CorpusPackageError):
                inventory_package(package, "CASE-0001")

    def test_metadata_inventory_counts_without_reading_binary_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "sample.unitypackage"
            write_unitypackage(package, [
                ("a" * 32, "Assets/Avatar/Body.prefab", """
--- !u!1001 &1
PrefabInstance:
  m_SourcePrefab: {fileID: 100100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, type: 3}
  m_Modification:
    m_Modifications:
    - target: {fileID: 2, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, type: 3}
      propertyPath: m_Materials.Array.data[0]
--- !u!137 &2
SkinnedMeshRenderer:
"""),
                ("b" * 32, "Assets/Avatar/Body.fbx", "binary must not be decoded"),
                ("c" * 32, "Assets/Avatar/Body.fbx.meta", "externalObjects:\n  1: {fileID: 2, guid: dddddddddddddddddddddddddddddddd, type: 2}"),
                ("d" * 32, "Assets/Avatar/Body.mat", "m_Shader: {fileID: 2, guid: eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee, type: 3}\n_MatTex: {fileID: 2800000, guid: ffffffffffffffffffffffffffffffff, type: 3}"),
            ])
            result = inventory_package(package, "CASE-0001")
            self.assertEqual(result["metrics"]["prefab_count"], 1)
            self.assertEqual(result["metrics"]["fbx_count"], 1)
            self.assertEqual(result["metrics"]["material_count"], 1)
            self.assertEqual(result["observed"]["prefab_instance_documents"], 1)
            self.assertEqual(result["observed"]["skinned_mesh_renderer_documents"], 1)
            self.assertEqual(result["observed"]["property_modification_count"], 1)
            self.assertEqual(result["observed"]["material_override_count"], 1)
            self.assertEqual(result["observed"]["external_objects_files"], 1)
            self.assertIn("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", result["observed"]["referenced_guids"])

    def test_group_inference_uses_guid_evidence_not_filename_only(self):
        left = {"case_id": "CASE-0001", "provided_guids": ["a"], "observed": {"referenced_guids": ["b"]}, "source_directory": "same"}
        right = {"case_id": "CASE-0002", "provided_guids": ["b"], "observed": {"referenced_guids": []}, "source_directory": "same"}
        unrelated = {"case_id": "CASE-0003", "provided_guids": ["c"], "observed": {"referenced_guids": []}, "source_directory": "same"}
        groups = infer_package_groups([left, right, unrelated])
        self.assertEqual(groups, [["CASE-0001", "CASE-0002"]])

    def test_scan_and_public_safe_summary_are_deterministic_and_anonymous(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_unitypackage(root / "one.unitypackage", [("a" * 32, "Assets/One.mat", "")])
            (root / "nested").mkdir()
            write_unitypackage(root / "nested" / "two.unitypackage", [("b" * 32, "Assets/Two.mat", "")])
            result = scan_corpus(root)
            self.assertEqual([item["case_id"] for item in result["packages"]], ["CASE-0001", "CASE-0002"])
            safe = public_safe_summary(result)
            encoded = json.dumps(safe, ensure_ascii=False)
            self.assertNotIn(str(root), encoded)
            self.assertNotIn("one.unitypackage", encoded)
            self.assertNotIn("a" * 32, encoded)


if __name__ == "__main__":
    unittest.main()
