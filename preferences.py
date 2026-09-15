"""Persistent add-on preferences for the external texture editor."""

from __future__ import annotations

import bpy  # type: ignore
from bpy.props import StringProperty  # type: ignore


ADDON_ID = "unitypackage_blender_importer"


def get_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_ID)
    return addon.preferences if addon else None


def save_preferences():
    try:
        bpy.ops.wm.save_userpref()
    except (RuntimeError, AttributeError):
        pass


class UNITYPACKAGE_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    external_editor_path: StringProperty(name="External Editor Path", subtype="FILE_PATH", default="")
    external_editor_name: StringProperty(name="External Editor Name", default="")

    def draw(self, context):
        layout = self.layout
        layout.label(text="External Texture Editor")
        layout.prop(self, "external_editor_name", text="Editor")
        layout.prop(self, "external_editor_path", text="Executable")


PREFERENCES_CLASSES = (UNITYPACKAGE_AddonPreferences,)
