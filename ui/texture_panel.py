"""Image Editor sidebar for the manual Unity texture workflow."""

from __future__ import annotations

from pathlib import Path

import bpy  # type: ignore

from ..preferences import get_preferences


class UNITYTEXTURE_PT_identity(bpy.types.Panel):
    bl_label = "Unity Texture"
    bl_idname = "UNITYTEXTURE_PT_identity"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Unity Texture"

    def draw(self, context):
        layout = self.layout
        image = getattr(context.space_data, "image", None)
        if image is None:
            layout.label(text="Select an imported Unity image")
            return
        layout.label(text=f"Image: {image.name}")
        for label, value in (
            ("Unity Asset Path", image.get("unity_asset_path", "")),
            ("Unity GUID", image.get("unity_guid", "")),
            ("Unity Source Path", image.get("unity_source_path", "")),
            ("Working File Path", image.filepath or ""),
        ):
            row = layout.row()
            row.label(text=label)
            row.label(text=str(value) or "-")
        path = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
        layout.label(text=f"File Exists: {bool(path and path.is_file())}")
        layout.label(text=f"Dirty: {bool(getattr(image, 'is_dirty', False))}")
        layout.label(text=f"Packed: {image.packed_file is not None}")
        preferences = get_preferences(context)
        editor_name = preferences.external_editor_name if preferences else ""
        layout.label(text=f"External Editor: {editor_name or 'Not set'}")
        if image.get("unity_guid") and image.get("unity_asset_path"):
            layout.operator("unity_texture.open_external_editor")
            layout.operator("unity_texture.choose_external_editor", text="Change External Editor")
            layout.operator("unity_texture.save_to_source")
            layout.operator("unity_texture.reload_from_disk")
        layout.operator("unity_texture.reload_changed")


TEXTURE_PANEL_CLASSES = (UNITYTEXTURE_PT_identity,)
