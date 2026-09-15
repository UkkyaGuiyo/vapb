"""Safe, manual editing operations for imported Unity texture Images."""

from __future__ import annotations

import os
from pathlib import Path

import bpy  # type: ignore

from ..external_editor import EDITOR_LAUNCH_FAILED, EDITOR_NOT_FOUND, launch_editor, discover_editors, validate_editor_path
from ..preferences import get_preferences, save_preferences


STATUS_OK = "OK"
MISSING_SOURCE = "MISSING_SOURCE"
UNSAVED_CHANGES = "UNSAVED_CHANGES"
PACKED_SOURCE_CONFLICT = "PACKED_SOURCE_CONFLICT"
NOT_UNITY_TEXTURE = "NOT_UNITY_TEXTURE"
INVALID_SOURCE = "INVALID_SOURCE"

IDENTITY_KEYS = ("unity_guid", "unity_asset_path", "unity_source_path")


def _absolute_filepath(image):
    filepath = str(getattr(image, "filepath", "") or "")
    if not filepath:
        return None
    return Path(bpy.path.abspath(filepath))


def _identity_snapshot(image):
    return {key: image.get(key) for key in IDENTITY_KEYS if image.get(key) is not None}


def _restore_identity(image, snapshot):
    for key, value in snapshot.items():
        image[key] = value


def _source_status(image):
    if image is None:
        return NOT_UNITY_TEXTURE, None
    if not image.get("unity_guid") or not image.get("unity_asset_path"):
        return NOT_UNITY_TEXTURE, None
    path = _absolute_filepath(image)
    if path is None:
        return INVALID_SOURCE, None
    source_path = str(image.get("unity_source_path", "") or "")
    if not source_path or Path(source_path).resolve() != path.resolve():
        return INVALID_SOURCE, path
    if image.packed_file is not None:
        return PACKED_SOURCE_CONFLICT, path
    if not path.is_file():
        return MISSING_SOURCE, path
    if not os.access(path, os.W_OK):
        return INVALID_SOURCE, path
    return STATUS_OK, path


def _update_source_mtime(image, path):
    image["unity_source_mtime_ns"] = str(path.stat().st_mtime_ns)


def _dirty(image):
    return bool(getattr(image, "is_dirty", False))


def save_image_to_unity_source(image):
    """Save the current pixels to the existing Unity working file."""
    status, path = _source_status(image)
    if status != STATUS_OK:
        return status
    original_filepath = image.filepath
    snapshot = _identity_snapshot(image)
    try:
        image.save(filepath=str(path))
        image.filepath = original_filepath
        _restore_identity(image, snapshot)
        _update_source_mtime(image, path)
    except (OSError, RuntimeError, ValueError):
        image.filepath = original_filepath
        return INVALID_SOURCE
    return STATUS_OK


def reload_image_from_disk(image):
    """Reload the existing Image datablock without discarding dirty edits."""
    status, path = _source_status(image)
    if status != STATUS_OK:
        return status
    if _dirty(image):
        return UNSAVED_CHANGES
    snapshot = _identity_snapshot(image)
    try:
        image.reload()
        _restore_identity(image, snapshot)
        _update_source_mtime(image, path)
    except (OSError, RuntimeError, ValueError):
        return INVALID_SOURCE
    return STATUS_OK


def reload_changed_unity_textures():
    """Manually reload changed Unity images; no watcher or background thread."""
    result = {"reloaded": [], "skipped": [], "missing": [], "conflicts": []}
    for image in bpy.data.images:
        if not image.get("unity_guid") or not image.get("unity_asset_path"):
            continue
        status, path = _source_status(image)
        if status == MISSING_SOURCE:
            result["missing"].append(image.name)
            continue
        if status == PACKED_SOURCE_CONFLICT:
            result["conflicts"].append(image.name)
            continue
        if status != STATUS_OK:
            result["skipped"].append((image.name, status))
            continue
        try:
            current_mtime = path.stat().st_mtime_ns
        except OSError:
            result["missing"].append(image.name)
            continue
        if int(image.get("unity_source_mtime_ns", "0")) == current_mtime:
            continue
        if _dirty(image):
            result["skipped"].append((image.name, UNSAVED_CHANGES))
            continue
        status = reload_image_from_disk(image)
        if status == STATUS_OK:
            result["reloaded"].append(image.name)
        else:
            result["skipped"].append((image.name, status))
    return result


def launch_image_in_editor(image, editor_path):
    """Validate the imported source and launch it without changing the Image."""
    status, path = _source_status(image)
    if status != STATUS_OK:
        return status
    if _dirty(image):
        return UNSAVED_CHANGES
    identity = (image.as_pointer(), image.get("unity_guid"), image.get("unity_asset_path"), image.get("unity_source_path"), image.filepath)
    result = launch_editor(editor_path, path)
    after = (image.as_pointer(), image.get("unity_guid"), image.get("unity_asset_path"), image.get("unity_source_path"), image.filepath)
    return result if identity == after else INVALID_SOURCE


def _report_result(operator, status):
    messages = {
        STATUS_OK: {"INFO"},
        MISSING_SOURCE: {"ERROR"},
        UNSAVED_CHANGES: {"WARNING"},
        PACKED_SOURCE_CONFLICT: {"WARNING"},
        NOT_UNITY_TEXTURE: {"WARNING"},
        INVALID_SOURCE: {"ERROR"},
        EDITOR_NOT_FOUND: {"ERROR"},
        EDITOR_LAUNCH_FAILED: {"ERROR"},
    }
    operator.report(messages.get(status, {"ERROR"}), status)


class UNITYTEXTURE_OT_save_source(bpy.types.Operator):
    bl_idname = "unity_texture.save_to_source"
    bl_label = "Save to Unity Source"
    bl_description = "Save this imported Unity image to its existing working file"

    @classmethod
    def poll(cls, context):
        return getattr(getattr(context, "space_data", None), "image", None) is not None

    def execute(self, context):
        status = save_image_to_unity_source(context.space_data.image)
        _report_result(self, status)
        return {"FINISHED"} if status == STATUS_OK else {"CANCELLED"}


class UNITYTEXTURE_OT_reload_source(bpy.types.Operator):
    bl_idname = "unity_texture.reload_from_disk"
    bl_label = "Reload from Disk"
    bl_description = "Reload this existing Unity image from its working file"

    @classmethod
    def poll(cls, context):
        return getattr(getattr(context, "space_data", None), "image", None) is not None

    def execute(self, context):
        status = reload_image_from_disk(context.space_data.image)
        _report_result(self, status)
        return {"FINISHED"} if status == STATUS_OK else {"CANCELLED"}


class UNITYTEXTURE_OT_reload_changed(bpy.types.Operator):
    bl_idname = "unity_texture.reload_changed"
    bl_label = "Reload Changed Unity Textures"
    bl_description = "Manually reload changed Unity images by file modification time"

    def execute(self, context):
        result = reload_changed_unity_textures()
        self.report(
            {"INFO"},
            "Reloaded "
            f"{len(result['reloaded'])}; skipped {len(result['skipped'])}; "
            f"missing {len(result['missing'])}; packed/conflict {len(result['conflicts'])}",
        )
        return {"FINISHED"}


class UNITYTEXTURE_MT_external_editor(bpy.types.Menu):
    bl_label = "Select External Editor"
    bl_idname = "UNITYTEXTURE_MT_external_editor"

    def draw(self, context):
        layout = self.layout
        editors = discover_editors()
        for editor in editors:
            operator = layout.operator("unity_texture.select_external_editor", text=editor["name"])
            operator.editor_path = editor["path"]
            operator.editor_name = editor["name"]
        if editors:
            layout.separator()
        layout.operator("unity_texture.browse_external_editor", text="Browse for executable...")


class UNITYTEXTURE_OT_choose_external_editor(bpy.types.Operator):
    bl_idname = "unity_texture.choose_external_editor"
    bl_label = "Change External Editor"

    def execute(self, context):
        bpy.ops.wm.call_menu(name=UNITYTEXTURE_MT_external_editor.bl_idname)
        return {"FINISHED"}


class UNITYTEXTURE_OT_open_external_editor(bpy.types.Operator):
    bl_idname = "unity_texture.open_external_editor"
    bl_label = "Open in External Editor"

    @classmethod
    def poll(cls, context):
        return getattr(getattr(context, "space_data", None), "image", None) is not None

    def invoke(self, context, event):
        preferences = get_preferences(context)
        if not preferences or not preferences.external_editor_path:
            bpy.ops.wm.call_menu(name=UNITYTEXTURE_MT_external_editor.bl_idname)
            return {"FINISHED"}
        return self.execute(context)

    def execute(self, context):
        preferences = get_preferences(context)
        if not preferences or not preferences.external_editor_path:
            bpy.ops.wm.call_menu(name=UNITYTEXTURE_MT_external_editor.bl_idname)
            return {"FINISHED"}
        status = launch_image_in_editor(context.space_data.image, preferences.external_editor_path)
        _report_result(self, status)
        return {"FINISHED"} if status == STATUS_OK else {"CANCELLED"}


class UNITYTEXTURE_OT_select_external_editor(bpy.types.Operator):
    bl_idname = "unity_texture.select_external_editor"
    bl_label = "Use External Editor"

    editor_path: bpy.props.StringProperty(subtype="FILE_PATH")
    editor_name: bpy.props.StringProperty()

    def execute(self, context):
        path = validate_editor_path(self.editor_path)
        if path is None:
            self.report({"ERROR"}, EDITOR_NOT_FOUND)
            return {"CANCELLED"}
        preferences = get_preferences(context)
        if preferences is None:
            self.report({"ERROR"}, "Addon preferences unavailable")
            return {"CANCELLED"}
        preferences.external_editor_path = str(path)
        preferences.external_editor_name = self.editor_name or path.stem
        save_preferences()
        status = launch_image_in_editor(context.space_data.image, path)
        _report_result(self, status)
        return {"FINISHED"} if status == STATUS_OK else {"CANCELLED"}


class UNITYTEXTURE_OT_browse_external_editor(bpy.types.Operator):
    bl_idname = "unity_texture.browse_external_editor"
    bl_label = "Browse for executable..."

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.exe", options={"HIDDEN"})
    image_name: bpy.props.StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        image = getattr(getattr(context, "space_data", None), "image", None)
        if image is None:
            self.report({"WARNING"}, NOT_UNITY_TEXTURE)
            return {"CANCELLED"}
        self.image_name = image.name
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        path = validate_editor_path(self.filepath)
        if path is None:
            self.report({"ERROR"}, EDITOR_NOT_FOUND)
            return {"CANCELLED"}
        preferences = get_preferences(context)
        image = bpy.data.images.get(self.image_name)
        if preferences is None or image is None:
            self.report({"ERROR"}, NOT_UNITY_TEXTURE)
            return {"CANCELLED"}
        preferences.external_editor_path = str(path)
        preferences.external_editor_name = path.stem
        save_preferences()
        status = launch_image_in_editor(image, path)
        _report_result(self, status)
        return {"FINISHED"} if status == STATUS_OK else {"CANCELLED"}


TEXTURE_EDITING_CLASSES = (
    UNITYTEXTURE_OT_save_source,
    UNITYTEXTURE_OT_reload_source,
    UNITYTEXTURE_OT_reload_changed,
    UNITYTEXTURE_MT_external_editor,
    UNITYTEXTURE_OT_choose_external_editor,
    UNITYTEXTURE_OT_open_external_editor,
    UNITYTEXTURE_OT_select_external_editor,
    UNITYTEXTURE_OT_browse_external_editor,
)
