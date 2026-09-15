"""Safe, manual editing operations for imported Unity texture Images."""

from __future__ import annotations

import os
from pathlib import Path

import bpy  # type: ignore


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


def _report_result(operator, status):
    messages = {
        STATUS_OK: {"INFO"},
        MISSING_SOURCE: {"ERROR"},
        UNSAVED_CHANGES: {"WARNING"},
        PACKED_SOURCE_CONFLICT: {"WARNING"},
        NOT_UNITY_TEXTURE: {"WARNING"},
        INVALID_SOURCE: {"ERROR"},
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


TEXTURE_EDITING_CLASSES = (
    UNITYTEXTURE_OT_save_source,
    UNITYTEXTURE_OT_reload_source,
    UNITYTEXTURE_OT_reload_changed,
)
