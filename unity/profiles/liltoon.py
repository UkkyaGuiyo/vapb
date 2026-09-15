from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common, alpha_mode
from ..material_model import UnityMaterialData


class LilToonProfile(ShaderProfile):
    family = "liltoon"
    lighting = "toon"

    def matches(self, material: UnityMaterialData) -> bool:
        return material.has("_lilToonVersion") or (material.has("_UseShadow", "_ShadowStrength") and material.has("_BaseMap", "_MainTex") and material.has("_MatCapTex", "_UseMatCap"))

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        normalized.family = "liltoon"
        normalized.lighting = "toon"
        if material.has("_UseBumpMap") and not material.flag("_UseBumpMap"):
            normalized.normal_tex = None
        if material.has("_UseEmission") and not material.flag("_UseEmission"):
            normalized.emission_tex = None
            normalized.emission_color = (0.0, 0.0, 0.0, 1.0)
        if material.has("_UseReflection") and not material.flag("_UseReflection"):
            normalized.metallic = 0.0
            normalized.roughness = 1.0
            normalized.metallic_tex = None
        normalized.alpha_mode = info.alpha if info and info.alpha else alpha_mode(material, normalized.alpha_mode)
        normalized.extras["shadow"] = {
            "color": list(material.color("_ShadowColor")),
            "color2nd": list(material.color("_Shadow2ndColor")),
            "strength": material.f("_ShadowStrength", 1.0),
            "border": material.f("_ShadowBorder", 0.5),
            "blur": material.f("_ShadowBlur", 0.1),
        }
        normalized.extras["matcap"] = {
            "texture": material.tex("_MatCapTex", "_MatCap2ndTex").to_dict() if material.tex("_MatCapTex", "_MatCap2ndTex") else None,
            "color": list(material.color("_MatCapColor")),
        }
        normalized.extras["rim"] = {"color": list(material.color("_RimColor")), "strength": material.f("_RimFresnelPower", 0.0)}
        if (info and info.outline) or material.flag("_UseOutline"):
            normalized.extras["outline"] = {"color": list(material.color("_OutlineColor")), "width": material.f("_OutlineWidth", 0.08)}
        return normalized

