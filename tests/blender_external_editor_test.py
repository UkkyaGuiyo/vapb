"""Blender 5.2.1 integration checks for the external texture editor launcher."""

from __future__ import annotations

import base64
from pathlib import Path
import sys
import tempfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> None:
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer import preferences
    from unitypackage_blender_importer.external_editor import EDITOR_LAUNCH_FAILED
    from unitypackage_blender_importer.operators import texture_editing

    with tempfile.TemporaryDirectory(prefix="external_editor_test_") as temp:
        root = Path(temp)
        editor = root / "PortablePaint.exe"
        source = root / "SampleGarment_col.png"
        editor.write_bytes(b"test executable")
        source.write_bytes(PNG)

        assert "FINISHED" in bpy.ops.preferences.addon_enable(module=addon.__name__)
        image = bpy.data.images.load(str(source), check_existing=True)
        image["unity_guid"] = "c" * 32
        image["unity_asset_path"] = "Assets/SampleGarment_col.png"
        image["unity_source_path"] = str(source)
        image["unity_source_mtime_ns"] = str(source.stat().st_mtime_ns)
        image_pointer = image.as_pointer()
        identity = (image["unity_guid"], image["unity_asset_path"], image["unity_source_path"], image.filepath)

        prefs = preferences.get_preferences()
        assert prefs is not None
        original_save_preferences = texture_editing.save_preferences
        texture_editing.save_preferences = lambda: None
        prefs.external_editor_path = str(editor)
        prefs.external_editor_name = "Portable Paint"
        assert texture_editing.get_preferences().external_editor_path == str(editor)
        assert texture_editing.get_preferences().external_editor_name == "Portable Paint"

        calls = []
        original_launcher = texture_editing.launch_editor
        texture_editing.launch_editor = lambda path, texture: calls.append((str(path), str(texture))) or "OK"
        try:
            assert texture_editing.launch_image_in_editor(image, editor) == "OK"
            assert calls == [(str(editor), str(source))]
            assert image.as_pointer() == image_pointer
            assert identity == (image["unity_guid"], image["unity_asset_path"], image["unity_source_path"], image.filepath)

            packed = image.copy()
            packed.pack()
            assert texture_editing.launch_image_in_editor(packed, editor) == texture_editing.PACKED_SOURCE_CONFLICT
            bpy.data.images.remove(packed)

            def mutate_identity(path, texture):
                image["unity_guid"] = "d" * 32
                return "OK"

            texture_editing.launch_editor = mutate_identity
            assert texture_editing.launch_image_in_editor(image, editor) == texture_editing.INVALID_SOURCE
            image["unity_guid"] = identity[0]
            texture_editing.launch_editor = lambda path, texture: calls.append((str(path), str(texture))) or "OK"

            image.pixels[0] = 0.4
            image.update()
            assert texture_editing.launch_image_in_editor(image, editor) == texture_editing.UNSAVED_CHANGES
            assert len(calls) == 1

            image.filepath = str(root / "missing.png")
            assert texture_editing.launch_image_in_editor(image, editor) == texture_editing.INVALID_SOURCE

            report_calls = []

            class FakeOperator:
                def report(self, levels, message):
                    report_calls.append((levels, message))

            texture_editing._report_result(FakeOperator(), EDITOR_LAUNCH_FAILED)
            assert report_calls == [({"ERROR"}, EDITOR_LAUNCH_FAILED)]
        finally:
            texture_editing.launch_editor = original_launcher
            texture_editing.save_preferences = original_save_preferences
            assert "FINISHED" in bpy.ops.preferences.addon_disable(module=addon.__name__)
    print("EXTERNAL_TEXTURE_EDITOR_OK")


main()
