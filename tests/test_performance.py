from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unitypackage_blender_importer.blender.performance import PerformanceTimer
from unitypackage_blender_importer.unity.asset_database import AssetDatabase
from unitypackage_blender_importer.unity.package_identity import PackageIdentity


class PerformanceTests(unittest.TestCase):
    def test_timer_accumulates_named_phases(self):
        timer = PerformanceTimer()
        self.assertEqual("value", timer.measure("test", lambda: "value"))
        timer.add("test", 0.25)
        timer.finish()
        self.assertGreaterEqual(timer.timings["test"], 0.25)
        self.assertIn("total", timer.timings)

    def test_package_identity_changes_when_package_size_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "avatar.unitypackage"
            package.write_bytes(b"one")
            first = PackageIdentity.from_path(package)
            package.write_bytes(b"two bytes")
            os.utime(package, None)
            second = PackageIdentity.from_path(package)
            self.assertNotEqual(first, second)

    def test_package_identity_changes_when_contents_change_with_same_stat(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "avatar.unitypackage"
            package.write_bytes(b"same-size-a")
            first_stat = package.stat()
            first = PackageIdentity.from_path(package)
            package.write_bytes(b"same-size-b")
            os.utime(package, ns=(first_stat.st_atime_ns, first_stat.st_mtime_ns))
            second = PackageIdentity.from_path(package)
            self.assertEqual(first.path, second.path)
            self.assertEqual(first.size, second.size)
            self.assertEqual(first.mtime_ns, second.mtime_ns)
            self.assertNotEqual(first.sha256, second.sha256)

    def test_asset_database_reuses_index_after_meta_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "Assets" / "Avatar.fbx"
            meta = root / "Assets" / "Avatar.fbx.meta"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"fbx")
            meta.write_text("guid: abcdef0123456789\n", encoding="utf-8")
            database = AssetDatabase(root)
            database.scan_missing_meta()
            with patch.object(Path, "rglob", side_effect=AssertionError("unexpected tree scan")):
                self.assertEqual([asset], database.fbxs())


if __name__ == "__main__":
    unittest.main()
