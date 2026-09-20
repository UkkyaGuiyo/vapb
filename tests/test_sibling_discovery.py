from __future__ import annotations

from pathlib import Path
import io
import tarfile
import tempfile
from unittest.mock import patch
import unittest

from unitypackage_blender_importer.unity.package_reader import UnityPackageReader
from unitypackage_blender_importer.unity.sibling_discovery import discover_siblings, inspect_provider_folder, inspect_provider_package


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


def _material(texture_guid: str) -> str:
    return f"m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}\n"


class SiblingDiscoveryTests(unittest.TestCase):
    def test_all_renderer_slots_are_required_in_selected_visual_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = "a" * 32, "b" * 32
            payload = f"""--- !u!137 &10
SkinnedMeshRenderer:
  m_Materials:
  - {{fileID: 2100000, guid: {first}, type: 2}}
  - {{fileID: 2100000, guid: {second},
      type: 2}}
"""
            _package(root / "geometry.unitypackage", [("c" * 32, "Assets/root.prefab", payload)])
            _package(root / "appearance.unitypackage", [(first, "Assets/A.mat", ""), (second, "Assets/B.mat", "")])
            result = discover_siblings(root / "geometry.unitypackage")
            self.assertEqual(result.packages[0].matched_guids, {first, second})
            self.assertEqual(result.packages[0].match_count, 2)

    def test_closure_001_ignores_unrelated_broken_material(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_a, material_b = "a" * 32, "b" * 32
            texture_x, texture_y = "c" * 32, "d" * 32
            _package(root / "geometry.unitypackage", [("e" * 32, "Assets/root.prefab", _visual_prefab(material_a))])
            _package(root / "appearance.unitypackage", [
                (material_a, "Assets/A.mat", _material(texture_x)),
                (material_b, "Assets/B.mat", _material(texture_y)),
                (texture_x, "Assets/X.png", "PNG"),
            ])
            result = discover_siblings(root / "geometry.unitypackage")
            self.assertEqual(result.visual_status, "COMPLETE")
            self.assertNotIn(texture_y, result.unresolved_visual_guids)

    def test_closure_002_resolves_selected_material_texture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_a, texture_x = "a" * 32, "b" * 32
            _package(root / "geometry.unitypackage", [("c" * 32, "Assets/root.prefab", _visual_prefab(material_a))])
            _package(root / "appearance.unitypackage", [(material_a, "Assets/A.mat", _material(texture_x)), (texture_x, "Assets/X.png", "PNG")])
            self.assertEqual(discover_siblings(root / "geometry.unitypackage").visual_status, "COMPLETE")

    def test_closure_003_missing_selected_texture_is_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_a, texture_x = "a" * 32, "b" * 32
            _package(root / "geometry.unitypackage", [("c" * 32, "Assets/root.prefab", _visual_prefab(material_a))])
            _package(root / "appearance.unitypackage", [(material_a, "Assets/A.mat", _material(texture_x))])
            result = discover_siblings(root / "geometry.unitypackage")
            self.assertEqual(result.visual_status, "PARTIAL")
            self.assertIn(texture_x, result.unresolved_visual_guids)

    def test_closure_005_provider_record_order_does_not_change_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_a, texture_x = "a" * 32, "b" * 32
            _package(root / "geometry.unitypackage", [("c" * 32, "Assets/root.prefab", _visual_prefab(material_a))])
            records = [(texture_x, "Assets/X.png", "PNG"), (material_a, "Assets/A.mat", _material(texture_x))]
            _package(root / "appearance.unitypackage", records)
            first = discover_siblings(root / "geometry.unitypackage")
            _package(root / "appearance.unitypackage", list(reversed(records)))
            second = discover_siblings(root / "geometry.unitypackage")
            self.assertEqual(first.visual_status, second.visual_status)
            self.assertEqual(first.unresolved_visual_guids, second.unresolved_visual_guids)

    def test_closure_selected_prefab_does_not_include_other_prefab_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_a, material_b = "a" * 32, "b" * 32
            texture_a, texture_b = "c" * 32, "d" * 32
            _package(root / "geometry.unitypackage", [
                ("e" * 32, "Assets/A.prefab", _visual_prefab(material_a)),
                ("f" * 32, "Assets/B.prefab", _visual_prefab(material_b)),
            ])
            _package(root / "appearance.unitypackage", [
                (material_a, "Assets/A.mat", _material(texture_a)),
                (texture_a, "Assets/A.png", "PNG"),
                (material_b, "Assets/B.mat", _material(texture_b)),
            ])
            selected = discover_siblings(root / "geometry.unitypackage", selected_asset_paths={"Assets/A.prefab"})
            self.assertEqual(selected.visual_status, "COMPLETE")
            self.assertNotIn(texture_b, selected.unresolved_visual_guids)

    def test_primary_local_fbx_guid_is_not_reported_as_external_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fbx_guid, material_guid = "a" * 32, "b" * 32
            prefab_payload = _visual_prefab(material_guid) + f"m_SourcePrefab: {{guid: {fbx_guid}, type: 3}}\n"
            fbx_meta = f"guid: {fbx_guid}\nexternalObjects:\n- first: Material\n  second: {{fileID: 2100000, guid: {material_guid}, type: 2}}\n"
            _package(root / "geometry.unitypackage", [
                ("c" * 32, "Assets/root.prefab", prefab_payload),
                (fbx_guid, "Assets/root.fbx", "FBX"),
            ], {fbx_guid: fbx_meta})
            _package(root / "appearance.unitypackage", [(material_guid, "Assets/A.mat", "")])
            result = discover_siblings(root / "geometry.unitypackage")
            self.assertEqual(result.visual_status, "COMPLETE")
            self.assertNotIn(fbx_guid, result.unresolved_visual_guids)

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

    def test_prebuilt_indexes_skip_duplicate_manifest_scans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            material_guid = "a" * 32
            primary = root / "primary.unitypackage"
            provider = root / "provider.unitypackage"
            _package(primary, [("b" * 32, "Assets/Avatar.prefab", _visual_prefab(material_guid))])
            _package(provider, [(material_guid, "Assets/Avatar.mat", "")])
            indexes = {
                primary.resolve(): UnityPackageReader(primary).build_index(),
                provider.resolve(): UnityPackageReader(provider).build_index(),
            }
            with patch("unitypackage_blender_importer.unity.sibling_discovery._manifest", side_effect=AssertionError("archive manifest rescanned")):
                result = discover_siblings(primary, prebuilt_indexes=indexes)
            self.assertEqual(result.visual_status, "COMPLETE")
            self.assertEqual([Path(item.path).name for item in result.packages], [provider.name])

    def test_manual_package_coverage_reports_zero_partial_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            guid_a, guid_b = "a" * 32, "b" * 32
            package_path = root / "provider.unitypackage"
            _package(package_path, [(guid_a, "Assets/A.mat", "")])
            zero = inspect_provider_package(package_path, {guid_b})
            partial = inspect_provider_package(package_path, {guid_a, guid_b})
            complete = inspect_provider_package(package_path, {guid_a})
            self.assertEqual(zero.match_count, 0)
            self.assertEqual(partial.matched_guids, {guid_a})
            self.assertEqual(complete.coverage_ratio, 1.0)
            self.assertEqual(complete.resolution_provenance, "USER_SELECTED_PACKAGE")

    def test_manual_folder_marks_duplicate_guid_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            guid = "a" * 32
            _package(root / "one.unitypackage", [(guid, "Assets/A.mat", "")])
            _package(root / "two.unitypackage", [(guid, "Assets/B.mat", "")])
            candidates, ambiguous = inspect_provider_folder(root, {guid})
            self.assertEqual(len(candidates), 2)
            self.assertEqual(ambiguous, {guid})
            self.assertTrue(all(candidate.ambiguous_guids == {guid} for candidate in candidates))

    def test_explicit_manual_package_resolves_automatic_ambiguity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            guid = "a" * 32
            geometry = root / "geometry.unitypackage"
            first = root / "one.unitypackage"
            second = root / "two.unitypackage"
            _package(geometry, [("b" * 32, "Assets/root.prefab", _visual_prefab(guid))])
            _package(first, [(guid, "Assets/A.mat", "")])
            _package(second, [(guid, "Assets/B.mat", "")])
            result = discover_siblings(
                geometry,
                extra_package_paths={second},
                provenance_by_path={str(second.resolve()): "USER_SELECTED_PACKAGE"},
            )
            self.assertEqual(result.visual_status, "COMPLETE")
            self.assertEqual([Path(item.path).name for item in result.packages], ["two.unitypackage"])
            self.assertEqual(result.resolution_provenance[result.packages[0].package_id], "USER_SELECTED_PACKAGE")

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
