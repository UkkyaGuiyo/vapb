# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 UkkyaGuiyo and VAPB contributors

"""UnityPackage / VRChat asset importer for Blender 5.2.1 LTS."""

bl_info = {
    "name": "Unity Package / VRChat Avatar Importer",
    "author": "UkkyaGuiyo and VAPB contributors",
    "version": (0, 4, 0),
    "blender": (5, 2, 0),
    "location": "File > Import > Unity Package / VRChat Avatar (.unitypackage)",
    "description": "Imports UnityPackage assets and exports FBX with Unity Material reconnect metadata for Blender 5.2.1 LTS.",
    "category": "Import-Export",
}

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover
    bpy = None

if bpy is not None:
    from .preferences import PREFERENCES_CLASSES
    from .operators.import_unitypackage import UNITYPACKAGE_CLASSES, menu_func_import
    from .operators.unitypackage_drop import UNITYPACKAGE_FILE_HANDLER_CLASSES
    from .blender.roundtrip_export import ROUNDTRIP_EXPORT_CLASSES, menu_func_export
    from .operators.texture_editing import TEXTURE_EDITING_CLASSES
    from .ui.texture_panel import TEXTURE_PANEL_CLASSES
    from .ui.physics_preview_panel import PHYSICS_PREVIEW_CLASSES, register_properties, unregister_properties
    from .operators.weight_transfer import (
        WEIGHT_TRANSFER_CLASSES, register_weight_transfer_properties,
        unregister_weight_transfer_properties,
    )
    from .ui.weight_transfer_panel import WEIGHT_TRANSFER_PANEL_CLASSES
    from .operators.bone_merge import (
        BONE_MERGE_CLASSES, register_bone_merge_properties, unregister_bone_merge_properties,
    )
    from .ui.bone_merge_panel import BONE_MERGE_PANEL_CLASSES
    from .operators.semantic_cleanup import (
        SEMANTIC_CLEANUP_CLASSES, register_semantic_cleanup_properties,
        unregister_semantic_cleanup_properties,
    )
    from .ui.semantic_cleanup_panel import SEMANTIC_CLEANUP_PANEL_CLASSES
    from .operators.export_unitypackage import CLASSES as PACKAGE_EXPORT_CLASSES, menu_export as menu_package_export
    from .operators.renderer_binding import CLASSES as RENDERER_OPERATOR_CLASSES
    from .ui.renderer_binding_panel import (
        CLASSES as RENDERER_PANEL_CLASSES,
        register_scene_properties as register_renderer_properties,
        unregister_scene_properties as unregister_renderer_properties,
    )

    def register():
        for cls in PREFERENCES_CLASSES:
            bpy.utils.register_class(cls)
        for cls in UNITYPACKAGE_CLASSES:
            bpy.utils.register_class(cls)
        for cls in ROUNDTRIP_EXPORT_CLASSES:
            bpy.utils.register_class(cls)
        for cls in PACKAGE_EXPORT_CLASSES:
            bpy.utils.register_class(cls)
        for cls in TEXTURE_EDITING_CLASSES + TEXTURE_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        for cls in PHYSICS_PREVIEW_CLASSES:
            bpy.utils.register_class(cls)
        register_properties()
        for cls in WEIGHT_TRANSFER_CLASSES + WEIGHT_TRANSFER_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        register_weight_transfer_properties()
        for cls in BONE_MERGE_CLASSES + BONE_MERGE_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        register_bone_merge_properties()
        for cls in SEMANTIC_CLEANUP_CLASSES + SEMANTIC_CLEANUP_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        register_semantic_cleanup_properties()
        for cls in RENDERER_OPERATOR_CLASSES + RENDERER_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        register_renderer_properties()
        for cls in UNITYPACKAGE_FILE_HANDLER_CLASSES:
            bpy.utils.register_class(cls)
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        bpy.types.TOPBAR_MT_file_export.append(menu_package_export)

    def unregister():
        unregister_semantic_cleanup_properties()
        for cls in reversed(SEMANTIC_CLEANUP_CLASSES + SEMANTIC_CLEANUP_PANEL_CLASSES):
            bpy.utils.unregister_class(cls)
        unregister_bone_merge_properties()
        for cls in reversed(BONE_MERGE_CLASSES + BONE_MERGE_PANEL_CLASSES):
            bpy.utils.unregister_class(cls)
        bpy.types.TOPBAR_MT_file_export.remove(menu_package_export)
        for cls in reversed(PACKAGE_EXPORT_CLASSES):
            bpy.utils.unregister_class(cls)
        unregister_renderer_properties()
        for cls in reversed(RENDERER_OPERATOR_CLASSES + RENDERER_PANEL_CLASSES):
            bpy.utils.unregister_class(cls)
        unregister_weight_transfer_properties()
        for cls in reversed(WEIGHT_TRANSFER_CLASSES + WEIGHT_TRANSFER_PANEL_CLASSES):
            bpy.utils.unregister_class(cls)
        unregister_properties()
        for cls in reversed(PHYSICS_PREVIEW_CLASSES):
            bpy.utils.unregister_class(cls)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        for cls in reversed(TEXTURE_EDITING_CLASSES + TEXTURE_PANEL_CLASSES):
            bpy.utils.unregister_class(cls)
        for cls in reversed(UNITYPACKAGE_FILE_HANDLER_CLASSES):
            bpy.utils.unregister_class(cls)
        for cls in reversed(ROUNDTRIP_EXPORT_CLASSES):
            bpy.utils.unregister_class(cls)
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        for cls in reversed(UNITYPACKAGE_CLASSES):
            bpy.utils.unregister_class(cls)
        for cls in reversed(PREFERENCES_CLASSES):
            bpy.utils.unregister_class(cls)
