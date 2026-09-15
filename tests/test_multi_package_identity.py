from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from unitypackage_blender_importer.unity.identity import (
    CROSS_PACKAGE_GUID_COLLISION,
    CROSS_PACKAGE_PATH_COLLISION,
    DUPLICATE_PACKAGE_IMPORT,
    LEGACY_UNSCOPED,
    NO_COLLISION,
    AssetIdentity,
    SceneIdentityRegistry,
    get_asset_identity,
    package_id_from_sha256,
)
from unitypackage_blender_importer.unity.package_identity import PackageIdentity


class MultiPackageIdentityTests(unittest.TestCase):
    def test_package_fingerprint_is_stable_when_path_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "A.unitypackage"
            second = root / "moved" / "A.unitypackage"
            first.write_bytes(b"same package bytes")
            second.parent.mkdir()
            second.write_bytes(first.read_bytes())
            self.assertEqual(PackageIdentity.from_path(first).sha256, PackageIdentity.from_path(second).sha256)
            self.assertEqual(package_id_from_sha256(PackageIdentity.from_path(first).sha256), "sha256:" + PackageIdentity.from_path(second).sha256)

    def test_canonical_identity_is_package_scoped(self):
        left = AssetIdentity("sha256:" + "a" * 64, "f" * 32, "Assets/Shared.png")
        right = AssetIdentity("sha256:" + "b" * 64, "f" * 32, "Assets/Shared.png")
        self.assertNotEqual(left, right)
        self.assertNotEqual(left.key, right.key)

    def test_different_package_bytes_have_different_package_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left = root / "left.unitypackage"
            right = root / "right.unitypackage"
            left.write_bytes(b"package A")
            right.write_bytes(b"package B")
            self.assertNotEqual(PackageIdentity.from_path(left).source_package_id, PackageIdentity.from_path(right).source_package_id)

    def test_same_name_different_path_is_not_a_collision(self):
        registry = SceneIdentityRegistry()
        a = AssetIdentity("sha256:" + "a" * 64, "a" * 32, "Assets/Textures/Main.png")
        b = AssetIdentity("sha256:" + "b" * 64, "b" * 32, "Assets/Other/Main.png")
        registry.register_asset(a, asset_type="Image")
        registry.register_asset(b, asset_type="Image")
        self.assertEqual(registry.detect_collisions(), [])

    def test_registry_reports_guid_and_path_collisions_without_merging(self):
        registry = SceneIdentityRegistry()
        package_a = "sha256:" + "a" * 64
        package_b = "sha256:" + "b" * 64
        self.assertEqual(registry.register_package({"source_package_id": package_a}), NO_COLLISION)
        self.assertEqual(registry.register_package({"source_package_id": package_b}), NO_COLLISION)
        same_guid_a = AssetIdentity(package_a, "f" * 32, "Assets/Shared.png")
        same_guid_b = AssetIdentity(package_b, "f" * 32, "Assets/Other.png")
        same_path_b = AssetIdentity(package_b, "e" * 32, "Assets/Shared.png")
        registry.register_asset(same_guid_a, asset_type="Image", display_name="Shared.png")
        registry.register_asset(same_guid_b, asset_type="Image", display_name="Other.png")
        registry.register_asset(same_path_b, asset_type="Image", display_name="Shared.png")
        statuses = {item["status"] for item in registry.detect_collisions()}
        self.assertIn(CROSS_PACKAGE_GUID_COLLISION, statuses)
        self.assertIn(CROSS_PACKAGE_PATH_COLLISION, statuses)
        self.assertEqual(len(registry.find_by_guid("f" * 32)), 2)
        self.assertEqual(len(registry.find_by_asset_path("Assets/Shared.png")), 2)

    def test_duplicate_package_and_legacy_are_explicit(self):
        registry = SceneIdentityRegistry()
        package_id = "sha256:" + "c" * 64
        self.assertEqual(registry.register_package({"source_package_id": package_id}), NO_COLLISION)
        self.assertEqual(registry.register_package({"source_package_id": package_id}), DUPLICATE_PACKAGE_IMPORT)
        legacy = get_asset_identity({"unity_guid": "a" * 32, "unity_asset_path": "Assets/Old.png"})
        self.assertEqual(legacy.source_package_id, LEGACY_UNSCOPED)
        self.assertTrue(legacy.is_legacy)

    def test_property_propagation_and_reverse_lookup(self):
        props = {
            "unity_source_package_id": "sha256:" + "e" * 64,
            "unity_guid": "a" * 32,
            "unity_asset_path": "Assets/A.png",
        }
        identity = get_asset_identity(props, "Image")
        self.assertEqual(identity.asset_type, "Image")
        self.assertEqual(identity.key, ("sha256:" + "e" * 64, "a" * 32, "Assets/A.png"))
        registry = SceneIdentityRegistry()
        registry.register_asset(identity, asset_type="Image")
        self.assertEqual(registry.lookup_by_identity(identity)[0]["asset_type"], "Image")

    def test_sequential_package_registration_keeps_first_identity(self):
        registry = SceneIdentityRegistry()
        first = AssetIdentity("sha256:" + "a" * 64, "a" * 32, "Assets/A.png")
        second = AssetIdentity("sha256:" + "b" * 64, "a" * 32, "Assets/A.png")
        registry.register_asset(first, asset_type="Image", display_name="A")
        registry.register_asset(second, asset_type="Image", display_name="B")
        self.assertEqual(registry.lookup_by_identity(first)[0]["display_name"], "A")
        self.assertEqual(registry.lookup_by_identity(second)[0]["display_name"], "B")

    def test_registry_roundtrip_is_json_serializable(self):
        registry = SceneIdentityRegistry()
        package_id = "sha256:" + "d" * 64
        registry.register_package({"source_package_id": package_id, "source_package_name": "A"})
        registry.register_asset(AssetIdentity(package_id, "a" * 32, "Assets/A.mat"), asset_type="Material")
        restored = SceneIdentityRegistry.from_json(registry.to_json())
        self.assertEqual(restored.to_dict(), registry.to_dict())
        self.assertEqual(json.loads(restored.to_json())["schema_version"], 1)
