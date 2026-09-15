from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common
from ..material_model import UnityMaterialData


class VRChatMobileProfile(ShaderProfile):
    family = "vrchat_mobile"
    lighting = "unlit"

    def matches(self, material: UnityMaterialData) -> bool:
        return material.has("_ShadowBoost", "_MinBrightness", "_MetallicStrength") and "_Ramp" in material.texture_slots

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        variant = info.variant if info else "toon_standard"
        normalized.family = "vrchat_mobile"
        normalized.extras["variant"] = variant
        if variant == "toon_lit":
            normalized.lighting = "unlit"
            normalized.emission_tex = normalized.base_color_tex
            normalized.emission_color = normalized.base_color
        elif variant == "standard_lite":
            normalized.lighting = "pbr"
            normalized.metallic = material.f("_Metallic", 1.0)
            normalized.roughness = max(0.0, min(1.0, 1.0 - material.f("_Glossiness", 1.0)))
        else:
            normalized.lighting = "toon"
            normalized.metallic = 0.0
            normalized.roughness = 1.0
            normalized.extras["toon_standard"] = {
                "shadow_boost": material.f("_ShadowBoost", 0.0),
                "min_brightness": material.f("_MinBrightness", 0.0),
                "metallic_strength": material.f("_MetallicStrength", 0.0),
                "ramp": material.tex("_Ramp").to_dict() if material.tex("_Ramp") else None,
            }
        normalized.alpha_mode = "opaque"
        return normalized

