"""Parse Unity YAML materials into a shader-independent intermediate model."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional

from .asset_database import AssetDatabase
from .material_model import UnityMaterialData, UnityTextureRef
from .yaml_parser import parse_scalar


_PROPERTY_HEADER_RE = re.compile(r"(?m)^[ \t]*-[ \t]*(_[A-Za-z0-9_]+):(?:[ \t]*(.*?))?[ \t]*$")


def _property_blocks(text: str) -> list[tuple[str, str, str]]:
    matches = list(_PROPERTY_HEADER_RE.finditer(text))
    blocks: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1), match.group(2) or "", text[match.end():end]))
    return blocks


def _inline_map(text: str, key: str = "") -> dict[str, Any]:
    if key:
        match = re.search(rf"(?m)^[ \t]*{re.escape(key)}:[ \t]*(\{{.*?\}})[ \t]*$", text)
    else:
        match = re.search(r"(\{[^\n]*\})", text)
    value = parse_scalar(match.group(1)) if match else None
    return value if isinstance(value, dict) else {}


def _parse_vector(body: str, key: str, default: tuple[float, float]) -> tuple[float, float]:
    value = _inline_map(body, key)
    try:
        return (float(value.get("x", default[0])), float(value.get("y", default[1])))
    except (TypeError, ValueError):
        return default


def _parse_color(body: str, inline: str) -> Optional[tuple[float, float, float, float]]:
    value = parse_scalar(inline) if inline else _inline_map(body)
    if not isinstance(value, dict):
        return None
    try:
        return tuple(float(value.get(channel, 1.0)) for channel in ("r", "g", "b", "a"))
    except (TypeError, ValueError):
        return None


def _parse_keyword_list(text: str, key: str) -> list[str]:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.*?)\s*$", text)
    if not match:
        return []
    parsed = parse_scalar(match.group(1))
    if isinstance(parsed, list):
        return [str(value) for value in parsed if value not in (None, "")]
    return [part for part in str(parsed).split() if part]


def _parse_number_collection(text: str, key: str, integer: bool = False) -> dict[str, float | int]:
    section_match = re.search(rf"(?ms)^\s*{re.escape(key)}:\s*\n(.*?)(?=^\s*m_[A-Za-z]+:|\Z)", text)
    if not section_match:
        return {}
    values: dict[str, float | int] = {}
    for name, inline, _body in _property_blocks(section_match.group(1)):
        raw = inline.strip()
        if not raw:
            continue
        parsed = parse_scalar(raw)
        if isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
            values[name] = int(parsed) if integer else float(parsed)
    return values


def _unity_path(path: Path, asset_db: AssetDatabase) -> str:
    try:
        return path.resolve().relative_to(asset_db.root.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def parse_material(path: Path, asset_db: AssetDatabase) -> UnityMaterialData:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    name_match = re.search(r"(?m)^\s*m_Name:\s*(.*?)\s*$", text)
    name = (name_match.group(1).strip().strip('"\'') if name_match else path.stem) or path.stem

    shader_match = re.search(r"(?m)^\s*m_Shader:\s*(\{.*?\})\s*$", text)
    shader = parse_scalar(shader_match.group(1)) if shader_match else {}
    shader = shader if isinstance(shader, dict) else {}
    shader_guid = str(shader.get("guid", ""))
    try:
        shader_file_id = int(shader.get("fileID", 0))
    except (TypeError, ValueError):
        shader_file_id = 0
    queue_match = re.search(r"(?m)^\s*m_CustomRenderQueue:\s*(-?\d+)", text)

    data = UnityMaterialData(
        path=path,
        name=name,
        guid=asset_db.guid_for_path(path),
        unity_path=_unity_path(path, asset_db),
        shader_guid=shader_guid,
        shader_file_id=shader_file_id,
        render_queue=int(queue_match.group(1)) if queue_match else -1,
        keywords=_parse_keyword_list(text, "m_ValidKeywords"),
        invalid_keywords=_parse_keyword_list(text, "m_InvalidKeywords"),
    )
    data.floats.update({key: float(value) for key, value in _parse_number_collection(text, "m_Floats").items()})
    data.ints.update({key: int(value) for key, value in _parse_number_collection(text, "m_Ints", integer=True).items()})
    for keyword in _parse_keyword_list(text, "m_ShaderKeywords"):
        if keyword not in data.keywords:
            data.keywords.append(keyword)

    for property_name, inline, body in _property_blocks(text):
        texture = _inline_map(body, "m_Texture")
        if texture or "m_Texture:" in body:
            try:
                file_id = int(texture.get("fileID", 0))
            except (TypeError, ValueError):
                file_id = 0
            data.textures[property_name] = UnityTextureRef(
                property_name=property_name,
                guid=str(texture.get("guid", "")),
                file_id=file_id,
                scale=_parse_vector(body, "m_Scale", (1.0, 1.0)),
                offset=_parse_vector(body, "m_Offset", (0.0, 0.0)),
            )
            data.texture_slots.add(property_name)
            continue
        color = _parse_color(body, inline)
        if color is not None:
            data.colors[property_name] = color

    if "_Glossiness" in data.floats:
        data.floats.setdefault("smoothness", data.floats["_Glossiness"])
    if "smoothness" in data.floats:
        data.floats.setdefault("roughness", 1.0 - max(0.0, min(1.0, data.floats["smoothness"])))

    from .profiles.base import shader_info

    info = shader_info(data)
    if info:
        data.shader_name = info.name
    elif shader_guid:
        data.shader_name = f"Unknown Shader ({shader_guid})"
    else:
        data.shader_name = "Unknown Shader"
    return data


__all__ = ["UnityMaterialData", "UnityTextureRef", "parse_material"]
