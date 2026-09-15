"""Blender 5.2.1 integration checks for the manual editable texture workflow."""

from __future__ import annotations

import base64
from pathlib import Path
import sys
import tempfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


PNG_A = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
PNG_B = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def main() -> None:
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer.operators.texture_editing import (
        MISSING_SOURCE,
        PACKED_SOURCE_CONFLICT,
        STATUS_OK,
        UNSAVED_CHANGES,
        reload_image_from_disk,
        save_image_to_unity_source,
    )

    with tempfile.TemporaryDirectory(prefix="editable_texture_test_") as temp:
        root = Path(temp)
        source = root / "Avatar_Face.png"
        source.write_bytes(PNG_A)
        blend_path = root / "editable.blend"

        addon.register()
        image = bpy.data.images.load(str(source), check_existing=True)
        image["unity_guid"] = "b" * 32
        image["unity_asset_path"] = "Assets/Avatar_Face.png"
        image["unity_source_path"] = str(source)
        image["unity_meta_guid"] = "b" * 32
        image["unity_source_mtime_ns"] = str(source.stat().st_mtime_ns)
        material = bpy.data.materials.new("Editable Texture Material")
        material.use_nodes = True
        texture_node = material.node_tree.nodes.new("ShaderNodeTexImage")
        texture_node.image = image

        identity = (image.as_pointer(), image.filepath, image["unity_guid"], image["unity_asset_path"])
        image.pixels[0] = 0.25
        image.update()
        source.write_bytes(PNG_B)
        assert reload_image_from_disk(image) == UNSAVED_CHANGES
        assert save_image_to_unity_source(image) == STATUS_OK
        assert identity == (image.as_pointer(), image.filepath, image["unity_guid"], image["unity_asset_path"])
        assert source.read_bytes() != b"", "source was not written"
        assert not list(root.glob("*_modified*"))
        assert not list(root.glob("*_copy*"))
        assert not list(root.glob("*_backup*"))

        source.write_bytes(PNG_B)
        assert reload_image_from_disk(image) == STATUS_OK
        assert image.as_pointer() == identity[0]
        assert texture_node.image.as_pointer() == identity[0]
        assert image["unity_guid"] == "b" * 32
        assert image["unity_meta_guid"] == "b" * 32

        packed = image.copy()
        packed.pack()
        assert reload_image_from_disk(packed) == PACKED_SOURCE_CONFLICT
        bpy.data.images.remove(packed)

        image_name = image.name
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        reopened = bpy.data.images.get(image_name)
        assert reopened is not None, "Image missing after .blend reopen"
        assert reopened["unity_guid"] == "b" * 32
        assert reopened["unity_asset_path"] == "Assets/Avatar_Face.png"
        assert Path(bpy.path.abspath(reopened.filepath)) == source

        source.unlink()
        assert reload_image_from_disk(reopened) == MISSING_SOURCE
        assert bpy.data.images.get(reopened.name) is reopened
        reopened.filepath = str(root / "different.png")
        assert reload_image_from_disk(reopened) not in (STATUS_OK, MISSING_SOURCE)
        addon.unregister()
    print("EDITABLE_TEXTURE_WORKFLOW_OK")


main()
