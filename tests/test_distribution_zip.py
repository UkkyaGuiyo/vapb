"""Distribution ZIP completeness and import-graph checks."""

from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_distribution_zip import (
    build,
    distribution_filename,
    git_files,
    is_runtime_python,
    runtime_python_paths,
    validate_zip,
)  # noqa: E402


class DistributionZipTests(unittest.TestCase):
    def test_export_finalizer_sources_are_packaged(self):
        helpers = {
            'unity_editor/VapbRealizationMarker.cs',
            'unity_editor/Editor/VapbReferenceFinalizer.cs',
            'unity_editor/Editor/VapbModelSkinFinalizer.cs',
        }
        members = git_files(ROOT, 'HEAD')
        self.assertTrue(helpers <= set(members))
        self.assertTrue({"LICENSE", "LICENSES.md", "unity_editor/LICENSE"} <= set(members))
        self.assertFalse(any(path.startswith('tests/') for path in members))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'addon.zip'
            build(ROOT, 'HEAD', output)
            with zipfile.ZipFile(output) as archive:
                for path in helpers:
                    self.assertGreater(len(archive.read(f'unitypackage_blender_importer/{path}')), 0)

    def test_source_runtime_set_contains_preferences(self):
        members = git_files(ROOT, "HEAD")
        self.assertIn("preferences.py", members)
        self.assertIn("operators/import_unitypackage.py", members)
        self.assertIn("blender/roundtrip_export.py", members)
        self.assertIn("operators/texture_editing.py", members)
        self.assertIn("ui/texture_panel.py", members)

    def test_current_revision_builds_complete_temporary_zip(self):
        members = git_files(ROOT, "HEAD")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / distribution_filename(ROOT, "HEAD")
            digest, _ = build(ROOT, "HEAD", output)
            self.assertTrue(digest)
            validate_zip(output, members)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("unitypackage_blender_importer/preferences.py", archive.namelist())

    def test_exclusion_policy_is_future_directory_safe(self):
        self.assertTrue(is_runtime_python("future_runtime/example.py"))
        self.assertTrue(is_runtime_python("root_module.py"))
        self.assertFalse(is_runtime_python("tests/example.py"))
        self.assertFalse(is_runtime_python("tools/example.py"))
        self.assertFalse(is_runtime_python("experiment_logs/example.py"))

    def test_runtime_set_is_normalized_by_relative_path(self):
        members = ["__init__.py", "preferences.py", "future_runtime/example.py", "tests/example.py"]
        self.assertEqual(runtime_python_paths(members), {"__init__.py", "preferences.py", "future_runtime/example.py"})
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "runtime.zip"
            with zipfile.ZipFile(output, "w") as archive:
                for member in runtime_python_paths(members):
                    archive.writestr(f"unitypackage_blender_importer/{member}", "# fixture\n")
                archive.writestr("unitypackage_blender_importer/README.md", "fixture\n")
            validate_zip(output, [*runtime_python_paths(members), "README.md"])


if __name__ == "__main__":
    unittest.main()
