"""UnityPackage / VRChat asset importer for Blender 5.2.1 LTS."""

bl_info = {
    "name": "Unity Package / VRChat Avatar Importer",
    "author": "OpenAI",
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

    def register():
        for cls in PREFERENCES_CLASSES:
            bpy.utils.register_class(cls)
        for cls in UNITYPACKAGE_CLASSES:
            bpy.utils.register_class(cls)
        for cls in ROUNDTRIP_EXPORT_CLASSES:
            bpy.utils.register_class(cls)
        for cls in TEXTURE_EDITING_CLASSES + TEXTURE_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        for cls in PHYSICS_PREVIEW_CLASSES:
            bpy.utils.register_class(cls)
        register_properties()
        for cls in WEIGHT_TRANSFER_CLASSES + WEIGHT_TRANSFER_PANEL_CLASSES:
            bpy.utils.register_class(cls)
        register_weight_transfer_properties()
        for cls in UNITYPACKAGE_FILE_HANDLER_CLASSES:
            bpy.utils.register_class(cls)
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    def unregister():
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
