"""Narrow semantic Material texture-reference patching."""

from __future__ import annotations

import re

from .staging import normalize_guid


_REFERENCE_RE = re.compile(r"(?P<prefix>\{[^{}\n]*\bfileID\s*:\s*-?\d+[^{}\n]*\bguid\s*:\s*)(?P<guid>[0-9a-fA-F]{32})(?P<suffix>\b[^{}\n]*\})")
_PROPERTY_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?(?P<name>[^\s:]+):\s*$")


def patch_material_texture_guid(payload: bytes, old_guid: str, new_guid: str, *, property_name: str | None = None) -> bytes:
    old = normalize_guid(old_guid)
    new = normalize_guid(new_guid)
    text = payload.decode("utf-8")
    lines = text.splitlines(keepends=True)
    changed = 0
    in_saved_properties = False
    saved_properties_indent = -1
    in_tex_envs = False
    tex_envs_indent = -1
    current_property: str | None = None
    matches: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if stripped == "m_TexEnvs:":
            if not in_saved_properties or indent <= saved_properties_indent:
                continue
            in_tex_envs = True
            tex_envs_indent = indent
            current_property = None
            continue
        if stripped == "m_SavedProperties:":
            in_saved_properties = True
            saved_properties_indent = indent
            in_tex_envs = False
            current_property = None
            continue
        if in_saved_properties and indent <= saved_properties_indent and stripped and not stripped.startswith("-"):
            in_saved_properties = False
            in_tex_envs = False
            current_property = None
            continue
        if not in_tex_envs:
            continue
        if stripped.startswith("m_") and indent <= tex_envs_indent:
            in_tex_envs = False
            current_property = None
            continue
        property_match = _PROPERTY_RE.match(line.rstrip("\r\n"))
        if property_match and indent >= tex_envs_indent:
            candidate = property_match.group("name")
            if candidate != "m_Texture" and candidate != "m_Scale" and candidate != "m_Offset":
                current_property = candidate
        if current_property is None or (property_name is not None and current_property != property_name):
            continue
        match = _REFERENCE_RE.search(line)
        if match and match.group("guid").lower() == old:
            matches.append((index, match))
    if len(matches) != 1:
        raise ValueError("material texture reference was not uniquely found")
    index, match = matches[0]
    lines[index] = lines[index][: match.start("guid")] + new + lines[index][match.end("guid") :]
    return "".join(lines).encode("utf-8")
