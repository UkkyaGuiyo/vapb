"""Shader identification and shared normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..material_model import NormalizedMaterial, UnityMaterialData
from ..texture_roles import canonical_texture_properties, TextureRole


BUILTIN_SHADER_GUID = "0000000000000000f000000000000000"


@dataclass(frozen=True)
class ShaderInfo:
    family: str
    name: str
    variant: str = ""
    alpha: str = ""
    lighting: str = ""
    outline: bool = False


# This is a deliberately small, independently maintained table. Property
# fingerprints remain the primary fallback because third-party shader GUIDs
# vary by package/version.
KNOWN_SHADERS: dict[str, ShaderInfo] = {
    "efa77a80ca0344749b4f19fdd5891cbe": ShaderInfo("liltoon", "lilToon/lts_o", outline=True),
    "df12117ecd77c31469c224178886498e": ShaderInfo("liltoon", "lilToon/lts"),
    "1a97144e4ad27a04aafd70f7b915cedb": ShaderInfo("mtoon", "VRM/MToon"),
    "e0edbf68d81d1f340ae8b110086b7063": ShaderInfo("mtoon", "VRM10/MToon10"),
    "933532a4fcc9baf4fa0491de14d08ed7": ShaderInfo("standard", "Universal Render Pipeline/Lit"),
    "affc81f3d164d734d8f13053effb1c5c": ShaderInfo("vrchat_mobile", "VRChat/Mobile/Toon Lit", variant="toon_lit", lighting="unlit"),
    "0b7113dea2069fc4e8943843eff19f70": ShaderInfo("vrchat_mobile", "VRChat/Mobile/Standard Lite", variant="standard_lite"),
    "e765db0afa7ecfc44ade2e4e2491f65a": ShaderInfo("vrchat_mobile", "VRChat/Mobile/Toon Standard", variant="toon_standard", lighting="toon"),
    "051a0ed2f2aedd741aa8186ae92f97e0": ShaderInfo("vrchat_mobile", "VRChat/Mobile/Toon Standard (Outline)", variant="toon_standard", lighting="toon", outline=True),
}

BUILTIN_SHADERS: dict[int, ShaderInfo] = {
    46: ShaderInfo("standard", "Standard"),
    45: ShaderInfo("standard", "Standard (Specular setup)"),
    10752: ShaderInfo("generic", "Unlit/Texture", lighting="unlit"),
    10750: ShaderInfo("generic", "Unlit/Transparent", lighting="unlit", alpha="blend"),
    10751: ShaderInfo("generic", "Unlit/Transparent Cutout", lighting="unlit", alpha="cutout"),
}


def shader_info(material: UnityMaterialData) -> ShaderInfo | None:
    guid = material.shader_guid.lower()
    if guid and guid != BUILTIN_SHADER_GUID:
        return KNOWN_SHADERS.get(guid)
    return BUILTIN_SHADERS.get(material.shader_file_id)


def _common(material: UnityMaterialData, info: ShaderInfo | None = None) -> NormalizedMaterial:
    info = info or ShaderInfo("unknown", "")
    canonical = canonical_texture_properties(material.textures, info.family, info.name)
    normalized = NormalizedMaterial(
        name=material.name,
        family=info.family,
        lighting=info.lighting or ("unlit" if info.family == "generic" and material.shader_name.startswith("Unlit/") else "pbr"),
        shader_guid=material.shader_guid,
        shader_name=material.shader_name or info.name,
        material_guid=material.guid,
        material_path=material.unity_path,
        base_color_tex=material.textures.get(canonical.get(TextureRole.BASE_COLOR, "")),
        base_color=material.color("_Color", "_BaseColor"),
        alpha_mode=info.alpha or "opaque",
        alpha_cutoff=material.f("_Cutoff", 0.5),
        normal_tex=material.textures.get(canonical.get(TextureRole.NORMAL, "")),
        normal_strength=material.f("_BumpScale", material.f("_NormalScale", 1.0)),
        emission_tex=material.textures.get(canonical.get(TextureRole.EMISSION, "")),
        emission_color=material.color("_EmissionColor", default=(0.0, 0.0, 0.0, 1.0)),
        metallic=material.f("_Metallic", 0.0),
        roughness=max(0.0, min(1.0, 1.0 - material.f("_Glossiness", material.f("_Smoothness", 0.5)))),
        metallic_tex=material.textures.get(canonical.get(TextureRole.METALLIC, "")),
        cull_backface=int(material.f("_Cull", material.f("_CullMode", material.f("_Culling", 2)))) == 2,
    )
    return normalized


def alpha_mode(material: UnityMaterialData, fallback: str = "opaque") -> str:
    if material.has("_Mode"):
        mode = int(material.f("_Mode", 0))
        if mode == 1:
            return "cutout"
        if mode in (2, 3):
            return "blend"
        return "opaque"
    if material.has("_AlphaMode"):
        return ("opaque", "cutout", "blend")[max(0, min(2, int(material.f("_AlphaMode", 0))))]
    if material.has("_BlendMode"):
        mode = int(material.f("_BlendMode", 0))
        if mode == 1:
            return "cutout"
        if mode in (2, 3):
            return "blend"
    if material.flag("_AlphaClip") or material.flag("_AlphaMaskMode") or material.flag("_AlphaToMask"):
        return "cutout"
    if int(material.f("_DstBlend", -1)) == 10 or material.render_queue >= 3000:
        return "blend"
    return fallback


class ShaderProfile:
    family = "unknown"
    lighting = "pbr"

    def matches(self, material: UnityMaterialData) -> bool:
        return False

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None) -> NormalizedMaterial:
        return _common(material, info)


def select_profile(material: UnityMaterialData) -> tuple[ShaderProfile, ShaderInfo | None]:
    info = shader_info(material)
    from .generic import GenericProfile
    from .liltoon import LilToonProfile
    from .mtoon import MToonProfile
    from .poiyomi import PoiyomiProfile
    from .standard import StandardProfile
    from .vrchat_mobile import VRChatMobileProfile

    profiles = {
        "liltoon": LilToonProfile(),
        "mtoon": MToonProfile(),
        "poiyomi": PoiyomiProfile(),
        "vrchat_mobile": VRChatMobileProfile(),
        "standard": StandardProfile(),
        "urp": StandardProfile(),
        "hdrp": StandardProfile(),
        "generic": GenericProfile(),
    }
    if info and info.family in profiles:
        return profiles[info.family], info
    for profile in (profiles["liltoon"], profiles["mtoon"], profiles["poiyomi"], profiles["vrchat_mobile"], profiles["standard"]):
        if profile.matches(material):
            return profile, info
    return profiles["generic"], info


def normalize_material(material: UnityMaterialData) -> NormalizedMaterial:
    profile, info = select_profile(material)
    normalized = profile.normalize(material, info)
    if not normalized.shader_name:
        normalized.shader_name = material.shader_name or (f"Unknown Shader ({material.shader_guid})" if material.shader_guid else "Unknown Shader")
    return normalized
