from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common, alpha_mode
from ..material_model import UnityMaterialData
from .standard import StandardProfile


class PoiyomiProfile(StandardProfile):
    family = "poiyomi"
    lighting = "toon"

    def matches(self, material: UnityMaterialData) -> bool:
        return material.has("_PoiVersion", "_PoiyomiVersion") or (material.has("_ShaderOptimizerEnabled") and material.has("_MainTex") and material.has("_ShadingEnabled", "_LightingMode"))

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        normalized.family = "poiyomi"
        normalized.lighting = "toon"
        normalized.alpha_mode = alpha_mode(material, normalized.alpha_mode)
        if material.has("_EnableEmission") and not material.flag("_EnableEmission"):
            normalized.emission_tex = None
            normalized.emission_color = (0.0, 0.0, 0.0, 1.0)
        normalized.emission_strength = max(material.f("_EmissionStrength", 1.0), 0.0)
        normalized.extras["shading"] = {
            "mode": int(material.f("_LightingMode", 0)),
            "shadow_strength": material.f("_ShadowStrength", 1.0),
            "shadow_offset": material.f("_ShadowOffset", 0.0),
        }
        if material.flag("_EnableOutlines"):
            normalized.extras["outline"] = {"color": list(material.color("_LineColor")), "width": material.f("_LineWidth", 0.0)}
        return normalized

