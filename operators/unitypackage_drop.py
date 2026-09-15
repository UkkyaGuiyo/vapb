"""Blender-native drag-and-drop adapter for UnityPackage files."""

from __future__ import annotations

import bpy  # type: ignore


class UNITYPACKAGE_FH_drop(bpy.types.FileHandler):
    """Route a dropped UnityPackage to the existing import operator."""

    bl_idname = "UNITYPACKAGE_FH_drop"
    bl_label = "UnityPackage"
    bl_import_operator = "import_scene.unitypackage"
    bl_file_extensions = ".unitypackage"

    @classmethod
    def poll_drop(cls, context):
        area = getattr(context, "area", None)
        return area is not None and getattr(area, "type", "") == "VIEW_3D"


UNITYPACKAGE_FILE_HANDLER_CLASSES = (UNITYPACKAGE_FH_drop,)
