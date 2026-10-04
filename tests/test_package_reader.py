from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.package_reader import PackageAsset, UnityPackageError, UnityPackageReader
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
    def test_extracts_folder_asset_as_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "folder.unitypackage"
            guid = "f" * 32
            make_package(package, [(guid, "Assets/SyntheticFolder", b"", b"guid: " + guid.encode() + b"\nfolderAsset: true\n")])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual([], extracted.errors)
            self.assertTrue((root / "out/Assets/SyntheticFolder").is_dir())
            self.assertTrue((root / "out/Assets/SyntheticFolder.meta").is_file())

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

    def test_selective_extract_matches_uppercase_archive_guid(self):
        guids = (
            ("ABCDEF0123456789ABCDEF0123456789", "abcdef0123456789abcdef0123456789"),
            ("aBcDeF0123456789abCDef0123456789", "ABCDEF0123456789ABCDEF0123456789"),
        )
        for archive_guid, requested_guid in guids:
            with self.subTest(archive_guid=archive_guid), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package = root / "case-guid.unitypackage"
                canonical_guid = archive_guid.lower()
                make_package(
                    package,
                    [
                        (archive_guid, "Assets/Selected.prefab", b"selected payload", b"guid: " + archive_guid.encode()),
                        ("f" * 32, "Assets/Ignored.txt", b"ignored", None),
                    ],
                )
                reader = UnityPackageReader(package)
                index = reader.build_index()
                self.assertIn(canonical_guid, index.records)

                extracted = reader.extract_selective(root / "selective", index, {requested_guid})

                self.assertEqual([], extracted.errors)
                self.assertEqual([canonical_guid], [asset.guid for asset in extracted.assets])
                self.assertEqual(b"selected payload", (root / "selective/Assets/Selected.prefab").read_bytes())
                self.assertEqual(
                    b"guid: " + archive_guid.encode(),
                    (root / "selective/Assets/Selected.prefab.meta").read_bytes(),
                )
                self.assertFalse((root / "selective/Assets/Ignored.txt").exists())

                full = reader.extract(root / "full")
                self.assertEqual([], full.errors)
                self.assertIn(archive_guid, [asset.guid for asset in full.assets])
                self.assertEqual(b"selected payload", (root / "full/Assets/Selected.prefab").read_bytes())

    def test_selective_extract_rejects_case_variant_guid_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "case-variant-guid.unitypackage"
            uppercase_guid = "ABCDEF0123456789ABCDEF0123456789"
            lowercase_guid = uppercase_guid.lower()
            make_package(
                package,
                [
                    (uppercase_guid, "Assets/First.txt", b"first payload", None),
                    (lowercase_guid, "Assets/Second.txt", b"second payload", None),
                ],
            )
            reader = UnityPackageReader(package)
            index = reader.build_index()

            with self.assertRaisesRegex(UnityPackageError, "case-variant GUID"):
                reader.extract_selective(root / "out", index, {lowercase_guid})

            self.assertFalse((root / "out/Assets").exists())
            self.assertEqual([], list((root / "out").glob(".unitypackage_spool_*")))

            with self.assertRaisesRegex(UnityPackageError, "case-variant GUID"):
                reader.extract(root / "full-out")

            self.assertFalse((root / "full-out/Assets").exists())
            self.assertEqual([], list((root / "full-out").glob(".unitypackage_spool_*")))

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "unsafe.unitypackage"
            make_package(package, [("c" * 32, "../escape.fbx", b"bad", None)])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual(0, len(extracted.assets))
            self.assertTrue(any("Unsafe pathname" in error for error in extracted.errors))
            self.assertFalse((root / "escape.fbx").exists())

    def test_rejects_duplicate_destinations_before_publishing_any_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "duplicate.unitypackage"
            output = root / "out"
            output.mkdir()
            target = output / "Assets" / "Duplicate.prefab"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"preexisting asset sentinel")
            target.with_name(target.name + ".meta").write_bytes(b"preexisting meta sentinel")
            first_guid = "1" * 32
            second_guid = "2" * 32
            make_package(
                package,
                [
                    (second_guid, "Assets/Duplicate.prefab", b"second payload", b"guid: " + second_guid.encode()),
                    ("0" * 32, "Assets/Unrelated.txt", b"must not publish", None),
                    (first_guid, "Assets/Duplicate.prefab", b"first payload", b"guid: " + first_guid.encode()),
                ],
            )

            with self.assertRaisesRegex(UnityPackageError, "destination collision"):
                UnityPackageReader(package).extract(output)

            self.assertEqual(b"preexisting asset sentinel", target.read_bytes())
            self.assertEqual(b"preexisting meta sentinel", target.with_name(target.name + ".meta").read_bytes())
            self.assertFalse((output / "Assets" / "Unrelated.txt").exists())
            self.assertEqual([], list(output.glob(".unitypackage_spool_*")))

    def test_rejects_portable_path_aliases(self):
        aliases = [
            ("casefold", "Assets/Case/Body.prefab", "assets/case/body.PREFAB"),
            ("unicode", "Assets/Caf\u00e9/Body.prefab", "Assets/Cafe\u0301/Body.prefab"),
            ("separator_and_dot", "Assets/Slash/Body.prefab", "Assets\\Slash\\.\\Body.prefab"),
            ("windows_trailing_dot", "Assets/WindowsAlias/Body.prefab", "Assets/WindowsAlias/Body.prefab."),
        ]
        for name, first_path, second_path in aliases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package = root / "alias.unitypackage"
                make_package(
                    package,
                    [
                        ("1" * 32, first_path, b"first", None),
                        ("2" * 32, second_path, b"second", None),
                    ],
                )
                output = root / "out"
                reader = UnityPackageReader(package)
                index = reader.build_index()
                with self.assertRaises(UnityPackageError):
                    reader.extract_selective(output, index, {"1" * 32, "2" * 32})
                self.assertFalse((output / "Assets").exists())
                self.assertEqual([], list(output.glob(".unitypackage_spool_*")))

    def test_rejects_metadata_file_and_parent_directory_collisions(self):
        cases = [
            (
                "asset_meta_alias",
                [
                    ("1" * 32, "Assets/Artifact", b"asset", None),
                    ("2" * 32, "Assets/Artifact.meta", b"other asset", None),
                ],
            ),
            (
                "file_as_parent_directory",
                [
                    ("1" * 32, "Assets/Parent", b"file", None),
                    ("2" * 32, "Assets/Parent/Child.asset", b"child", None),
                ],
            ),
            (
                "duplicate_explicit_folders",
                [
                    ("1" * 32, "Assets/Folder", b"", b"guid: " + b"1" * 32 + b"\nfolderAsset: true\n"),
                    ("2" * 32, "Assets/Folder", b"", b"guid: " + b"2" * 32 + b"\nfolderAsset: true\n"),
                ],
            ),
        ]
        for name, records in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package = root / "collision.unitypackage"
                make_package(package, records)
                output = root / "out"
                with self.assertRaisesRegex(UnityPackageError, "destination collision"):
                    UnityPackageReader(package).extract(output)
                self.assertFalse((output / "Assets").exists())
                self.assertEqual([], list(output.glob(".unitypackage_spool_*")))

    def test_allows_explicit_folder_and_child_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "folder-and-child.unitypackage"
            folder_guid = "1" * 32
            child_guid = "2" * 32
            make_package(
                package,
                [
                    (folder_guid, "Assets/Folder", b"", b"guid: " + folder_guid.encode() + b"\nfolderAsset: true\n"),
                    (child_guid, "Assets/Folder/Child.txt", b"child", None),
                ],
            )
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual([], extracted.errors)
            self.assertEqual({folder_guid, child_guid}, {asset.guid for asset in extracted.assets})
            self.assertTrue((root / "out/Assets/Folder").is_dir())
            self.assertEqual(b"child", (root / "out/Assets/Folder/Child.txt").read_bytes())

    def test_rejects_existing_output_file_directory_type_conflicts_before_publication(self):
        cases = ("directory_blocks_file", "file_blocks_folder")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                output = root / "out"
                blocked = output / "Assets" / "Blocked"
                blocked.parent.mkdir(parents=True)
                if case == "directory_blocks_file":
                    blocked.mkdir()
                    blocked_path = "Assets/Blocked"
                    blocked_record = ("2" * 32, blocked_path, b"payload", None)
                else:
                    blocked.write_bytes(b"existing file sentinel")
                    folder_guid = "2" * 32
                    blocked_record = (
                        folder_guid,
                        "Assets/Blocked",
                        b"",
                        b"guid: " + folder_guid.encode() + b"\nfolderAsset: true\n",
                    )
                package = root / "existing-output-conflict.unitypackage"
                make_package(
                    package,
                    [
                        ("1" * 32, "Assets/Unrelated.txt", b"must not publish", None),
                        blocked_record,
                    ],
                )

                with self.assertRaisesRegex(UnityPackageError, "destination collision"):
                    UnityPackageReader(package).extract(output)

                self.assertFalse((output / "Assets" / "Unrelated.txt").exists())
                self.assertEqual([], list(output.glob(".unitypackage_spool_*")))
                if case == "file_blocks_folder":
                    self.assertEqual(b"existing file sentinel", blocked.read_bytes())

    def test_checks_each_unicode_directory_spelling_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "out"
            blocked_parent = output / "Assets" / "Cafe\u0301"
            blocked_parent.parent.mkdir(parents=True)
            blocked_parent.write_bytes(b"blocked directory sentinel")
            package = root / "unicode-parent-obstruction.unitypackage"
            make_package(
                package,
                [
                    ("1" * 32, "Assets/Caf\u00e9/First.txt", b"must not publish", None),
                    ("2" * 32, "Assets/Cafe\u0301/Second.txt", b"blocked", None),
                ],
            )

            with self.assertRaises(UnityPackageError):
                UnityPackageReader(package).extract(output)

            self.assertFalse((output / "Assets" / "Caf\u00e9" / "First.txt").exists())
            self.assertEqual(b"blocked directory sentinel", blocked_parent.read_bytes())
            self.assertEqual([], list(output.glob(".unitypackage_spool_*")))

    def test_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "absolute.unitypackage"
            make_package(package, [("e" * 32, "C:/outside.fbx", b"bad", None)])
            extracted = UnityPackageReader(package).extract(root / "out")
            self.assertEqual(0, len(extracted.assets))
            self.assertTrue(any("Absolute pathname" in error for error in extracted.errors))

    def test_package_index_never_indexes_unextracted_paths_outside_extraction_root(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            outside_prefab = base / "outside.prefab"
            outside_fbx = base / "outside.fbx"
            outside_material = base / "outside.mat"
            external_bytes = {
                outside_prefab: b"synthetic prefab",
                outside_fbx: b"synthetic fbx",
                outside_material: b"synthetic material",
            }
            for path, content in external_bytes.items():
                path.write_bytes(content)

            package = base / "indexed.unitypackage"
            good_guid = "1" * 32
            missing_guid = "2" * 32
            hostile_prefab_guid = "3" * 32
            hostile_fbx_guid = "4" * 32
            hostile_material_guid = "5" * 32
            mismatched_extraction_guid = "6" * 32
            unicode_guid = "7" * 32
            unc_slash_guid = "8" * 32
            unc_backslash_guid = "9" * 32
            drive_relative_guid = "a" * 32
            make_package(
                package,
                [
                    (good_guid, "Assets/Good.fbx", b"good", None),
                    (missing_guid, "Assets/Missing.fbx", b"missing", None),
                    (hostile_prefab_guid, outside_prefab.resolve().as_posix(), b"hostile", None),
                    (hostile_fbx_guid, "../outside.fbx", b"hostile", None),
                    (hostile_material_guid, "../outside.mat", b"hostile", None),
                    (mismatched_extraction_guid, "Assets/Mismatched.mat", b"in package", None),
                    (unicode_guid, "Assets\\日本語\\Backslash.fbx", b"unicode", None),
                    (unc_slash_guid, "//server/share/asset.prefab", b"remote path", None),
                    (unc_backslash_guid, r"\\server\share\asset.prefab", b"remote path", None),
                    (drive_relative_guid, "C:foo.mat", b"drive-relative path", None),
                ],
            )
            reader = UnityPackageReader(package)
            index = reader.build_index()

            first_root = base / "first-extraction"
            first_extraction = reader.extract_selective(
                first_root,
                index,
                {
                    good_guid,
                    hostile_prefab_guid,
                    hostile_fbx_guid,
                    hostile_material_guid,
                    unicode_guid,
                    unc_slash_guid,
                    unc_backslash_guid,
                    drive_relative_guid,
                },
            )
            self.assertEqual([good_guid, unicode_guid], [asset.guid for asset in first_extraction.assets])
            self.assertGreaterEqual(len(first_extraction.errors), 6)
            self.assertTrue(all("extraction failed" in error for error in first_extraction.errors))
            first_db = AssetDatabase.from_package_index(first_root, index, first_extraction.assets)

            self.assertEqual(first_root / "Assets/Good.fbx", first_db.find_guid(good_guid).path)
            unicode_path = first_root / "Assets/日本語/Backslash.fbx"
            self.assertEqual(unicode_path, first_db.find_path("Assets/日本語/Backslash.fbx").path)
            self.assertEqual(first_db.find_path("Assets/日本語/Backslash.fbx"), first_db.find_guid(unicode_guid))
            self.assertEqual("Assets/Missing.fbx", first_db.find_guid(missing_guid).unity_path)
            self.assertNotIn(first_root / "Assets/Missing.fbx", first_db.fbxs())
            rejected_guids = (
                hostile_prefab_guid,
                hostile_fbx_guid,
                hostile_material_guid,
                unc_slash_guid,
                unc_backslash_guid,
                drive_relative_guid,
            )
            for guid in rejected_guids:
                self.assertIsNone(first_db.find_guid(guid))
            self.assertEqual([], first_db.prefabs())
            self.assertEqual([first_root / "Assets/Good.fbx", unicode_path], first_db.fbxs())
            self.assertEqual([], first_db.materials())

            second_root = base / "second-extraction"
            second_root.mkdir()
            mismatched = PackageAsset(
                mismatched_extraction_guid,
                "Assets/Mismatched.mat",
                outside_material,
                None,
            )
            second_db = AssetDatabase.from_package_index(
                second_root,
                index,
                [mismatched],
            )
            for guid in rejected_guids:
                self.assertIsNone(second_db.find_guid(guid))
            self.assertEqual([], second_db.prefabs())
            self.assertEqual([], second_db.fbxs())
            self.assertEqual([], second_db.materials())
            self.assertIsNone(second_db.find_guid(mismatched_extraction_guid))
            self.assertNotIn(outside_material, second_db.materials())
            self.assertEqual(external_bytes, {path: path.read_bytes() for path in external_bytes})

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
