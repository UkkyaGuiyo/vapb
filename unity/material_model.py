"""Shader-independent material data used between Unity parsing and Blender nodes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


Color = tuple[float, float, float, float]
Vector2 = tuple[float, float]


@dataclass(frozen=True)
class UnityTextureRef:
    property_name: str
    guid: str = ""
    file_id: int = 0
    scale: Vector2 = (1.0, 1.0)
    offset: Vector2 = (0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_name": self.property_name,
            "guid": self.guid,
            "file_id": self.file_id,
            "scale": list(self.scale),
            "offset": list(self.offset),
        }


@dataclass
class UnityMaterialData:
    path: Any
    name: str
    guid: str = ""
    unity_path: str = ""
    shader_guid: str = ""
    shader_file_id: int = 0
    shader_name: str = ""
    textures: dict[str, UnityTextureRef] = field(default_factory=dict)
    colors: dict[str, Color] = field(default_factory=dict)
    floats: dict[str, float] = field(default_factory=dict)
    ints: dict[str, int] = field(default_factory=dict)
    render_queue: int = -1
    keywords: list[str] = field(default_factory=list)
    invalid_keywords: list[str] = field(default_factory=list)
    texture_slots: set[str] = field(default_factory=set)
    file_id: int | None = None

    def tex(self, *names: str) -> Optional[UnityTextureRef]:
        for name in names:
            if name in self.textures:
                return self.textures[name]
        return None

    def f(self, name: str, default: float = 0.0) -> float:
        value = self.floats.get(name)
        if value is None:
            value = self.ints.get(name)
        return float(value) if value is not None else default

    def flag(self, name: str, default: bool = False) -> bool:
        return bool(self.floats.get(name, self.ints.get(name, default)))

    def color(self, *names: str, default: Color = (1.0, 1.0, 1.0, 1.0)) -> Color:
        for name in names:
            if name in self.colors:
                return self.colors[name]
        return default

    def has(self, *names: str) -> bool:
        return any(name in self.floats or name in self.ints or name in self.colors or name in self.texture_slots for name in names)

    @property
    def texture_guids(self) -> dict[str, str]:
        return {name: ref.guid for name, ref in self.textures.items() if ref.guid}


@dataclass
class NormalizedMaterial:
    name: str
    family: str = "unknown"
    lighting: str = "pbr"
    shader_guid: str = ""
    shader_name: str = ""
    material_guid: str = ""
    material_path: str = ""
    base_color_tex: Optional[UnityTextureRef] = None
    base_color: Color = (1.0, 1.0, 1.0, 1.0)
    alpha_mode: str = "opaque"
    alpha_cutoff: float = 0.5
    normal_tex: Optional[UnityTextureRef] = None
    normal_strength: float = 1.0
    emission_tex: Optional[UnityTextureRef] = None
    emission_color: Color = (0.0, 0.0, 0.0, 1.0)
    emission_strength: float = 1.0
    metallic: float = 0.0
    roughness: float = 0.5
    metallic_tex: Optional[UnityTextureRef] = None
    cull_backface: bool = True
    extras: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("base_color_tex", "normal_tex", "emission_tex", "metallic_tex"):
            value = getattr(self, key)
            result[key] = value.to_dict() if value else None
        result["base_color"] = list(self.base_color)
        result["emission_color"] = list(self.emission_color)
        return result
