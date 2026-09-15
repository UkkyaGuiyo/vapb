from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common, alpha_mode
from ..material_model import UnityMaterialData


class MToonProfile(ShaderProfile):
    family = "mtoon"
    lighting = "toon"

    def matches(self, material: UnityMaterialData) -> bool:
        return material.has("_MToonVersion") or (material.has("_ShadeTexture", "_ShadeColor") and material.has("_BlendMode", "_AlphaMode"))

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        normalized.family = "mtoon"
        normalized.lighting = "toon"
        normalized.alpha_mode = alpha_mode(material, normalized.alpha_mode)
        normalized.extras["shade"] = {
            "color": list(material.color("_ShadeColor")),
            "texture": material.tex("_ShadeTex", "_ShadeTexture").to_dict() if material.tex("_ShadeTex", "_ShadeTexture") else None,
            "shift": material.f("_ShadingShiftFactor", material.f("_ShadeShift", 0.0)),
            "toony": material.f("_ShadingToonyFactor", material.f("_ShadeToony", 0.9)),
        }
        normalized.extras["rim"] = {"color": list(material.color("_RimColor", default=(0.0, 0.0, 0.0, 1.0)))}
        normalized.extras["outline"] = {"color": list(material.color("_OutlineColor", default=(0.0, 0.0, 0.0, 1.0))), "width": material.f("_OutlineWidth", 0.0)}
        return normalized

