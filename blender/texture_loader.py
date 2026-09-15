"""Texture discovery/loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import bpy  # type: ignore


SUPPORTED_TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"}


def load_texture(
    path: Path,
    pack: bool = False,
    guid: str = "",
    unity_path: str = "",
    meta_path: Optional[Path] = None,
    source_package_id: str = "",
):
    image = bpy.data.images.load(str(path), check_existing=True)
    if pack and image.packed_file is None:
        image.pack()
    image["unity_source_path"] = str(path)
    try:
        image["unity_source_mtime_ns"] = str(path.stat().st_mtime_ns)
    except OSError:
        pass
    if guid:
        image["unity_guid"] = guid
    if unity_path:
        image["unity_asset_path"] = unity_path
    if source_package_id:
        image["unity_source_package_id"] = source_package_id
    meta = Path(meta_path) if meta_path else path.with_name(path.name + ".meta")
    try:
        meta_text = meta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        meta_text = ""
    if meta_text:
        image["unity_texture_type"] = int(_meta_int(meta_text, "textureType", -1))
        image["unity_srgb"] = int(_meta_int(meta_text, "sRGBTexture", 1))
        image["unity_wrap_u"] = int(_meta_int(meta_text, "wrapU", 0))
        image["unity_wrap_v"] = int(_meta_int(meta_text, "wrapV", 0))
        if _meta_int(meta_text, "textureType", 0) == 1 or _meta_int(meta_text, "sRGBTexture", 1) == 0:
            try:
                image.colorspace_settings.name = "Non-Color"
            except (AttributeError, TypeError, RuntimeError):
                pass
    return image


def _meta_int(text: str, key: str, default: int) -> int:
    import re

    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(-?\d+)", text)
    return int(match.group(1)) if match else default


def load_texture_by_guid(asset_db, guid: Optional[str], pack: bool = False):
    entry = asset_db.find_guid(guid)
    if not entry or entry.path.suffix.lower() not in SUPPORTED_TEXTURE_EXTENSIONS:
        return None
    try:
        return load_texture(
            entry.path,
            pack=pack,
            guid=entry.guid,
            unity_path=entry.unity_path,
            source_package_id=getattr(asset_db, "source_package_id", ""),
        )
    except (RuntimeError, OSError):
        return None
