from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common, alpha_mode
from ..material_model import UnityMaterialData


class StandardProfile(ShaderProfile):
    family = "standard"
    lighting = "pbr"

    def matches(self, material: UnityMaterialData) -> bool:
        return material.has("_MainTex", "_BaseMap") and material.has("_Metallic") and material.has("_Glossiness", "_Smoothness") and not material.has("_ShadowStrength", "_ShadeTexture", "_PoiVersion")

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        normalized.family = "standard"
        normalized.lighting = "pbr"
        normalized.alpha_mode = alpha_mode(material, normalized.alpha_mode)
        normalized.extras["standard"] = {
            "mode": int(material.f("_Mode", 0)),
            "surface": int(material.f("_Surface", 0)),
            "alpha_clip": bool(material.flag("_AlphaClip")),
        }
        if "_EMISSION" in material.invalid_keywords:
            normalized.emission_tex = None
            normalized.emission_color = (0.0, 0.0, 0.0, 1.0)
            normalized.warnings.append("_EMISSION was invalid for the current shader and was ignored")
        return normalized

