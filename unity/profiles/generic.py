from __future__ import annotations

from .base import ShaderInfo, ShaderProfile, _common, alpha_mode
from ..material_model import UnityMaterialData


class GenericProfile(ShaderProfile):
    family = "unknown"

    def normalize(self, material: UnityMaterialData, info: ShaderInfo | None = None):
        normalized = _common(material, info)
        normalized.family = "unknown"
        normalized.alpha_mode = alpha_mode(material, normalized.alpha_mode)
        normalized.extras["unclassified_properties"] = {
            "floats": dict(material.floats),
            "ints": dict(material.ints),
            "colors": {key: list(value) for key, value in material.colors.items()},
            "textures": {key: value.to_dict() for key, value in material.textures.items()},
        }
        normalized.warnings.append("Unknown shader; generic Unity texture/color rules were used")
        return normalized

