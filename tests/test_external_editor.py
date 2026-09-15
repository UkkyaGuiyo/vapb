from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from unitypackage_blender_importer.external_editor import (
    EDITOR_NOT_FOUND,
    LAUNCH_OK,
    discover_editors,
    launch_editor,
    validate_editor_path,
)


class ExternalEditorTests(unittest.TestCase):
    def test_discovery_deduplicates_known_editor_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "krita.exe"
            executable.write_bytes(b"test")
            found = discover_editors(
                which=lambda name: str(executable) if name == "krita.exe" else None,
                registry_paths={"Krita": [executable]},
                common_paths={"Krita": [executable]},
            )
            self.assertEqual(found, [{"name": "Krita", "path": str(executable.resolve())}])

    def test_launch_uses_argument_list_and_shell_false(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "editor.exe"
            texture = Path(temp) / "texture.png"
            executable.write_bytes(b"editor")
            texture.write_bytes(b"texture")
            calls = []

            def fake_popen(*args, **kwargs):
                calls.append((args, kwargs))

            self.assertEqual(launch_editor(executable, texture, popen=fake_popen), LAUNCH_OK)
            self.assertEqual(calls, [(([str(executable.resolve()), str(texture.resolve())],), {"shell": False})])

    def test_missing_editor_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            texture = Path(temp) / "texture.png"
            texture.write_bytes(b"texture")
            self.assertIsNone(validate_editor_path(Path(temp) / "missing.exe"))
            self.assertEqual(launch_editor(Path(temp) / "missing.exe", texture), EDITOR_NOT_FOUND)
