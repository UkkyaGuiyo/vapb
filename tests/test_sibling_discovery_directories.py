# SPDX-License-Identifier: GPL-3.0-or-later
"""Public synthetic reproduction: directories are not UnityPackage providers."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.unity.sibling_discovery import discover_siblings, inspect_provider_folder
from .test_sibling_discovery import _package, _visual_prefab


class SiblingDirectoryCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.primary = self.root / 'Primary.unitypackage'
        self.required = 'a' * 32
        _package(self.primary, [('b' * 32, 'Assets/Public.prefab', _visual_prefab(self.required))])
        self.initial_sha = hashlib.sha256(self.primary.read_bytes()).hexdigest()
        self.fake = self.root / 'Fake.unitypackage'
        self.fake.mkdir()
        self.marker = self.fake / 'preserve.txt'
        self.marker.write_bytes(b'unchanged synthetic directory')

    def assert_sources_unchanged(self):
        self.assertEqual(hashlib.sha256(self.primary.read_bytes()).hexdigest(), self.initial_sha)
        self.assertTrue(self.fake.is_dir())
        self.assertEqual(self.marker.read_bytes(), b'unchanged synthetic directory')

    def test_automatic_discovery_ignores_directory_with_package_suffix(self):
        try:
            result = discover_siblings(self.primary, required_visual_guids={self.required})
        finally:
            self.assert_sources_unchanged()
        self.assertEqual(result.packages, [])
        self.assertEqual(result.unresolved_visual_guids, {self.required})

    def test_manual_provider_folder_ignores_directory_with_package_suffix(self):
        try:
            candidates, ambiguous = inspect_provider_folder(self.root, {self.required})
        finally:
            self.assert_sources_unchanged()
        self.assertFalse(any(Path(candidate.path) == self.fake for candidate in candidates))
        self.assertEqual(ambiguous, set())


if __name__ == '__main__':
    unittest.main()
