from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
from unitypackage_blender_importer.unity.prefab_parser import parse_prefab


def make_package(path: Path, records: list[tuple[str, str, bytes, bytes | None]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload, meta in records:
            for name, data in (("asset", payload), ("pathname", unity_path.encode("utf-8"))):
                info = tarfile.TarInfo(f"{guid}/{name}")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            if meta is not None:
                info = tarfile.TarInfo(f"{guid}/asset.meta")
                info.size = len(meta)
                archive.addfile(info, io.BytesIO(meta))


class PackageReaderTests(unittest.TestCase):
    def test_extracts_unicode_path_and_indexes_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "test.unitypackage"
            make_package(package, [
                ("a" * 32, "Assets/衣装/体.fbx", b"FBX", b"guid: " + b"a" * 32),
                ("b" * 32, "Assets/衣装/布.png", b"PNG", b"guid: " + b"b" * 32),
            ])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual([], extracted.errors)
            reader = UnityPackageReader(package)
            reader.extract(root / "timed-out")
            self.assertTrue({"package_open", "archive_scan", "extract"}.issubset(reader.last_timings))
            self.assertTrue(all(value >= 0.0 for value in reader.last_timings.values()))
            self.assertTrue((root / "out/Assets/衣装/体.fbx").is_file())
            self.assertTrue((root / "out/Assets/衣装/体.fbx.meta").is_file())
            db = AssetDatabase.from_extraction(extracted.root, extracted.assets)
            self.assertEqual(1, len(db.fbxs()))
            self.assertEqual(1, len(db.textures()))

    def test_sequential_extract_handles_reverse_guid_order_and_streams_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "ordered.unitypackage"
            large_payload = b"F" * (2 * 1024 * 1024)
            make_package(
                package,
                [
                    ("f" * 32, "Assets/Z-last.fbx", large_payload, None),
                    ("a" * 32, "Assets/A-first.fbx", b"small", None),
                ],
            )
            with patch.object(Path, "write_bytes", side_effect=AssertionError("asset must be streamed")):
                extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual([], extracted.errors)
            self.assertEqual(["a" * 32, "f" * 32], [asset.guid for asset in extracted.assets])
            self.assertEqual(large_payload, (root / "out/Assets/Z-last.fbx").read_bytes())

    def test_selective_extract_writes_only_requested_guid_and_caches_small_meta(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "selective.unitypackage"
            selected_guid = "a" * 32
            ignored_guid = "b" * 32
            make_package(
                package,
                [
                    (selected_guid, "Assets/Selected.fbx", b"selected", b"guid: " + selected_guid.encode()),
                    (ignored_guid, "Assets/Ignored.png", b"ignored", b"guid: " + ignored_guid.encode()),
                ],
            )
            reader = UnityPackageReader(package)
            index = reader.build_index()
            self.assertEqual(selected_guid, index.records[selected_guid].guid)
            self.assertIsNotNone(index.records[selected_guid].meta_bytes)
            extracted = reader.extract_selective(root / "out", index, {selected_guid})
            self.assertEqual([], extracted.errors)
            self.assertEqual([selected_guid], [asset.guid for asset in extracted.assets])
            self.assertTrue((root / "out/Assets/Selected.fbx").is_file())
            self.assertTrue((root / "out/Assets/Selected.fbx.meta").is_file())
            self.assertFalse((root / "out/Assets/Ignored.png").exists())
            self.assertFalse((root / "out/Assets/Ignored.png.meta").exists())

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "unsafe.unitypackage"
            make_package(package, [("c" * 32, "../escape.fbx", b"bad", None)])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual(0, len(extracted.assets))
            self.assertTrue(any("Unsafe pathname" in error for error in extracted.errors))
            self.assertFalse((root / "escape.fbx").exists())

    def test_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "absolute.unitypackage"
            make_package(package, [("e" * 32, "C:/outside.fbx", b"bad", None)])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual(0, len(extracted.assets))
            self.assertTrue(any("Absolute pathname" in error for error in extracted.errors))

    def test_prefab_parser_extracts_hierarchy_and_refs(self):
        with tempfile.TemporaryDirectory() as temp:
            prefab_path = Path(temp) / "Avatar.prefab"
            prefab_path.write_text(
                """%YAML 1.1
--- !u!1 &100
GameObject:
  m_Name: Avatar
  m_Component:
  - component: {fileID: 101}
--- !u!4 &101
Transform:
  m_GameObject: {fileID: 100}
  m_Father: {fileID: 0}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 1, y: 2, z: 3}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!137 &200
SkinnedMeshRenderer:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 4300000, guid: dddddddddddddddddddddddddddddddd, type: 3}
""",
                encoding="utf-8",
            )
            prefab = parse_prefab(prefab_path)
            self.assertEqual("Avatar", prefab.display_name)
            self.assertEqual(1, len(prefab.transforms))
            self.assertIn("d" * 32, prefab.referenced_fbx_guids())


if __name__ == "__main__":
    unittest.main()
