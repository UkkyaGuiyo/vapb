from __future__ import annotations

from pathlib import Path
import io
import tarfile
import tempfile
from unittest.mock import patch
import unittest

from unitypackage_blender_importer.unity.sibling_discovery import discover_siblings


def _add(archive, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def _package(path: Path, records, metas=None):
    metas = metas or {}
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            _add(archive, f"{guid}/asset", payload.encode())
            _add(archive, f"{guid}/pathname", unity_path.encode())
            _add(archive, f"{guid}/asset.meta", metas.get(guid, f"guid: {guid}\n").encode())


def _visual_prefab(material_guid: str) -> str:
    return f"MeshRenderer:\n  m_Materials:\n  - {{fileID: 2100000, guid: {material_guid}, type: 2}}\n"


class SiblingDiscoveryTests(unittest.TestCase):
    def test_single_package_skips_archive_payload_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            package_path = Path(temp) / "single.unitypackage"
            _package(package_path, [("a" * 32, "Assets/single.prefab", "")])
            module = __import__("unitypackage_blender_importer.unity.sibling_discovery", fromlist=["_manifest"])
            with patch("unitypackage_blender_importer.unity.sibling_discovery._manifest", wraps=module._manifest) as scan:
                result = discover_siblings(package_path)
            self.assertEqual(result.status, "NONE")
            self.assertEqual(scan.call_count, 1)
            self.assertEqual(result.accounting["texture_payload_bytes_read"], 0)
            self.assertEqual(result.accounting["fbx_payload_bytes_read"], 0)

    def test_discovery_reuses_each_archive_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid, texture_guid = "a" * 32, "b" * 32
            root_package = root / "root.unitypackage"
            provider = root / "provider.unitypackage"
            _package(root_package, [("c" * 32, "Assets/root.prefab", _visual_prefab(material_guid))])
            _package(provider, [(material_guid, "Assets/provider.mat", f"m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}\n")])
            module = __import__("unitypackage_blender_importer.unity.sibling_discovery", fromlist=["_manifest"])
            original = module._manifest
            calls = []

            def traced(path, accounting=None):
                calls.append(Path(path).resolve())
                return original(path, accounting)

            with patch("unitypackage_blender_importer.unity.sibling_discovery._manifest", traced):
                result = discover_siblings(root_package)
            self.assertEqual(result.status, "PARTIAL")
            self.assertEqual(calls.count(root_package.resolve()), 1)
            self.assertEqual(calls.count(provider.resolve()), 1)
    def test_no_related_package_is_none(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _package(root / "root.unitypackage", [("a" * 32, "Assets/root.prefab", "guid: " + "b" * 32)])
            _package(root / "unrelated.unitypackage", [("c" * 32, "Assets/unrelated.mat", "")])
            result = discover_siblings(root / "root.unitypackage")
            self.assertEqual(result.status, "NONE")
            self.assertFalse(result.packages)

    def test_partial_does_not_guess_unresolved_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid, texture_guid = "a" * 32, "b" * 32
            _package(root / "root.unitypackage", [("c" * 32, "Assets/root.prefab", _visual_prefab(material_guid))])
            _package(root / "provider.unitypackage", [(material_guid, "Assets/provider.mat", f"m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}\n")])
            result = discover_siblings(root / "root.unitypackage")
            self.assertEqual(result.status, "PARTIAL")
            self.assertEqual([Path(item.path).name for item in result.packages], ["provider.unitypackage"])
            self.assertIn(texture_guid, result.unresolved_guids)

    def test_guid_exact_transitive_and_unrelated_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid, texture_guid = "a" * 32, "b" * 32
            _package(root / "SyntheticAvatar.unitypackage", [("c" * 32, "Assets/SyntheticAvatar.prefab", _visual_prefab(material_guid))])
            _package(root / "unrelated-name.unitypackage", [(material_guid, "Assets/X.mat", f"m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}\n")])
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
            _package(root / "root.unitypackage", [("c" * 32, "Assets/root.prefab", _visual_prefab(guid))])
            _package(root / "provider-a.unitypackage", [(guid, "Assets/A.mat", "m_Texture: {fileID: 2800000, guid: " + "b" * 32 + ", type: 3}\n")])
            _package(root / "provider-b.unitypackage", [(guid, "Assets/B.mat", "m_Texture: {fileID: 2800000, guid: " + "b" * 32 + ", type: 3}\n")])
            _package(nested / "outside.unitypackage", [(guid, "Assets/out.mat", "")])
            result = discover_siblings(root / "root.unitypackage")
            self.assertEqual(result.status, "AMBIGUOUS")
            self.assertIn(guid, result.ambiguous_guids)
            self.assertNotIn(str(nested / "outside.unitypackage"), {item.path for item in result.packages})

    def test_adjacent_sibling_directory_provider_is_found_by_guid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            geometry = root / "Geometry"
            appearance = root / "Appearance"
            geometry.mkdir()
            appearance.mkdir()
            material_guid = "a" * 32
            _package(geometry / "geometry.unitypackage", [("c" * 32, "Assets/geometry.prefab", _visual_prefab(material_guid))])
            _package(appearance / "appearance.unitypackage", [(material_guid, "Assets/appearance.mat", "")])
            result = discover_siblings(geometry / "geometry.unitypackage")
            self.assertEqual(result.visual_status, "COMPLETE")
            self.assertEqual([Path(item.path).name for item in result.packages], ["appearance.unitypackage"])

    def test_manifest_discovery_never_reads_texture_or_fbx_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid, texture_guid, fbx_guid = "a" * 32, "b" * 32, "c" * 32
            fbx_meta = "externalObjects:\n- first: Material\n  second: {fileID: 2100000, guid: " + material_guid + ", type: 2}\n"
            _package(root / "root.unitypackage", [("d" * 32, "Assets/root.prefab", _visual_prefab(material_guid)), (fbx_guid, "Assets/root.fbx", "FBX")], {fbx_guid: f"guid: {fbx_guid}\n{fbx_meta}"})
            _package(root / "provider.unitypackage", [(material_guid, "Assets/provider.mat", "m_Texture: {fileID: 2800000, guid: " + texture_guid + ", type: 3}\n"), (texture_guid, "Assets/provider.png", "PNG-BINARY")])
            original_extractfile = tarfile.TarFile.extractfile

            def guarded_extractfile(archive, member, *args, **kwargs):
                name = member.name if hasattr(member, "name") else str(member)
                self.assertNotEqual(f"{texture_guid}/asset", name)
                self.assertNotEqual(f"{fbx_guid}/asset", name)
                return original_extractfile(archive, member, *args, **kwargs)

            with patch.object(tarfile.TarFile, "extractfile", guarded_extractfile):
                result = discover_siblings(root / "root.unitypackage")
            self.assertEqual(result.accounting["texture_payload_bytes_read"], 0)
            self.assertEqual(result.accounting["fbx_payload_bytes_read"], 0)
            self.assertGreater(result.accounting["metadata_text_bytes_read"], 0)
