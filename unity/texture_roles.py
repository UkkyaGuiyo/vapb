"""Single source of truth for Unity texture-property semantics."""

from __future__ import annotations

from enum import Enum


class TextureRole(str, Enum):
    BASE_COLOR = "Base Color"
    NORMAL = "Normal"
    EMISSION = "Emission"
    METALLIC = "Metallic"
    ROUGHNESS = "Roughness"
    OCCLUSION = "Occlusion"
    PRESERVE_ONLY = "Preserve Only"


_BASE_COLOR = ("_maintex", "_basemap", "_basecolormap")
_NORMAL = ("_bumpmap", "_normalmap")
_EMISSION = ("_emissionmap", "_emissiontex")
_METALLIC = ("_metallicglossmap",)
_ROUGHNESS = ("_roughnessmap", "_smoothnesstex")
_OCCLUSION = ("_occlusionmap",)


def classify_texture_property(shader_family: str, shader_name: str, property_name: str) -> TextureRole:
    """Classify only explicitly supported properties; unknowns are preserved."""
    del shader_family, shader_name
    name = str(property_name or "").casefold()
    if name in _BASE_COLOR:
        return TextureRole.BASE_COLOR
    if name in _NORMAL:
        return TextureRole.NORMAL
    if name in _EMISSION:
        return TextureRole.EMISSION
    if name in _METALLIC:
        return TextureRole.METALLIC
    if name in _ROUGHNESS:
        return TextureRole.ROUGHNESS
    if name in _OCCLUSION:
        return TextureRole.OCCLUSION
    return TextureRole.PRESERVE_ONLY


def canonical_texture_properties(texture_properties: dict[str, object], shader_family: str = "", shader_name: str = "") -> dict[TextureRole, str]:
    """Return one deterministic property per Blender-supported role."""
    result: dict[TextureRole, str] = {}
    precedence = (
        (TextureRole.BASE_COLOR, _BASE_COLOR),
        (TextureRole.NORMAL, _NORMAL),
        (TextureRole.EMISSION, _EMISSION),
        (TextureRole.METALLIC, _METALLIC),
        (TextureRole.ROUGHNESS, _ROUGHNESS),
        (TextureRole.OCCLUSION, _OCCLUSION),
    )
    lowered = {str(key).casefold(): str(key) for key in texture_properties}
    for role, names in precedence:
        for name in names:
            actual = lowered.get(name)
            if actual is not None and texture_properties.get(actual):
                result[role] = actual
                break
    return result
