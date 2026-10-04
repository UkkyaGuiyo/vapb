import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.unity_final_state_v2.stage3_test_root import (
    ROOT_MARKER,
    ROOT_MARKER_VALUE,
    SOURCE_MARKER,
    SOURCE_MARKER_VALUE,
    TARGET_MARKER,
    assert_owned_path,
    resolve_stage3_test_root,
)


class Stage3TestRootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"
        self.root.mkdir()
        self.source = self.root / "SourceProject"
        self.target = self.root / "TargetProject"
        self.source.mkdir()
        self.target.mkdir()
        (self.root / ROOT_MARKER).write_text(ROOT_MARKER_VALUE + "\n", encoding="utf-8")
        (self.source / SOURCE_MARKER).write_text(SOURCE_MARKER_VALUE + "\n", encoding="utf-8")
        (self.target / TARGET_MARKER).touch()

    def test_resolves_only_marked_direct_project_children(self):
        paths = resolve_stage3_test_root(self.root)
        self.assertEqual(self.root.resolve(), paths.root)
        self.assertEqual(self.source.resolve(), paths.source_project)
        self.assertEqual(self.target.resolve(), paths.target_project)

    def test_rejects_missing_or_unmarked_root(self):
        (self.root / ROOT_MARKER).unlink()
        with self.assertRaisesRegex(ValueError, "marker is missing"):
            resolve_stage3_test_root(self.root)
        (self.root / ROOT_MARKER).write_text("wrong marker\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected value"):
            resolve_stage3_test_root(self.root)

    def test_rejects_git_checkout_even_if_marked(self):
        (self.root / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Git checkout"):
            resolve_stage3_test_root(self.root)

    def test_rejects_marked_root_nested_inside_git_checkout(self):
        (Path(self.temp.name) / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "inside a Git checkout"):
            resolve_stage3_test_root(self.root)

    def test_rejects_parent_traversal_outside_owned_root(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            assert_owned_path(self.root / ".." / "outside", self.root)

    def test_rejects_nested_assets_reparse_component(self):
        destination = self.source / "Assets" / "SyntheticMaterialFixture" / "R2Stage3"
        destination.mkdir(parents=True)
        reparse = self.source / "Assets"
        real_lstat = os.lstat

        def lstat_with_nested_reparse(path):
            if Path(path) == reparse:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return real_lstat(path)

        with patch("tests.unity_final_state_v2.stage3_test_root.os.lstat", side_effect=lstat_with_nested_reparse):
            with self.assertRaisesRegex(ValueError, "reparse point"):
                assert_owned_path(destination, self.root)

    def test_rejects_missing_source_or_target_marker(self):
        (self.source / SOURCE_MARKER).unlink()
        with self.assertRaisesRegex(ValueError, "marker is missing"):
            resolve_stage3_test_root(self.root)
        (self.source / SOURCE_MARKER).write_text(SOURCE_MARKER_VALUE, encoding="utf-8")
        (self.target / TARGET_MARKER).unlink()
        with self.assertRaisesRegex(ValueError, "marker is missing"):
            resolve_stage3_test_root(self.root)

    def test_rejects_source_project_symlink_outside_root(self):
        outside = Path(self.temp.name) / "outside-source"
        outside.mkdir()
        (outside / SOURCE_MARKER).write_text(SOURCE_MARKER_VALUE, encoding="utf-8")
        old_source = self.source
        (old_source / SOURCE_MARKER).unlink()
        old_source.rmdir()
        try:
            os.symlink(outside, old_source, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            old_source.mkdir()
            (old_source / SOURCE_MARKER).write_text(SOURCE_MARKER_VALUE, encoding="utf-8")
            self.skipTest("directory symlinks are unavailable: " + str(exc))
        with self.assertRaisesRegex(ValueError, "reparse point|direct child"):
            resolve_stage3_test_root(self.root)


if __name__ == "__main__":
    unittest.main()
