from __future__ import annotations

from pathlib import Path
import io
import tarfile
import tempfile
import unittest

from unitypackage_blender_importer.unity.sibling_discovery import discover_siblings


def _add(archive, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _package(path: Path, records):
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            _add(archive, f"{guid}/asset", payload.encode())
            _add(archive, f"{guid}/pathname", unity_path.encode())
            _add(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode())


class SiblingDiscoveryTests(unittest.TestCase):
    def test_guid_exact_transitive_and_unrelated_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid, texture_guid = "a" * 32, "b" * 32
            _package(root / "SyntheticAvatar.unitypackage", [("c" * 32, "Assets/SyntheticAvatar.prefab", f"guid: {material_guid}\n")])
            _package(root / "unrelated-name.unitypackage", [(material_guid, "Assets/X.mat", f"guid: {texture_guid}\n")])
            _package(root / "textures-only.unitypackage", [(texture_guid, "Assets/X.png", "PNG")])
            _package(root / "other-product.unitypackage", [("d" * 32, "Assets/Other.mat", "")])
            result = discover_siblings(root / "SyntheticAvatar.unitypackage")
            self.assertEqual(result.status, "COMPLETE")
            self.assertEqual({Path(item.path).name for item in result.packages}, {"unrelated-name.unitypackage", "textures-only.unitypackage"})

    def test_duplicate_provider_is_ambiguous_and_same_folder_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "other"
            nested.mkdir()
            guid = "a" * 32
            _package(root / "root.unitypackage", [("c" * 32, "Assets/root.prefab", f"guid: {guid}\n")])
            _package(root / "provider-a.unitypackage", [(guid, "Assets/A.mat", "")])
            _package(root / "provider-b.unitypackage", [(guid, "Assets/B.mat", "")])
            _package(nested / "outside.unitypackage", [(guid, "Assets/out.mat", "")])
            result = discover_siblings(root / "root.unitypackage")
            self.assertEqual(result.status, "AMBIGUOUS")
            self.assertIn(guid, result.ambiguous_guids)
            self.assertNotIn(str(nested / "outside.unitypackage"), {item.path for item in result.packages})
