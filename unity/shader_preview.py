"""Conservative, shader-independent preview IR for Blender material building.

The IR deliberately keeps Unity identity and provider state separate from the
best-effort visual approximation.  A missing shader provider must never make a
material import fail.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .material_model import Color, NormalizedMaterial, UnityMaterialData, UnityTextureRef
from .profiles.base import BUILTIN_SHADER_GUID, BUILTIN_SHADERS


SEMANTIC_PREVIEW = "SEMANTIC_PREVIEW"
GENERIC_FALLBACK_PREVIEW = "GENERIC_FALLBACK_PREVIEW"

BUILTIN_SHADER = "BUILTIN_SHADER"
LOCAL_PROVIDER_FOUND = "LOCAL_PROVIDER_FOUND"
CORPUS_PROVIDER_FOUND = "CORPUS_PROVIDER_FOUND"
EXTERNAL_PROVIDER_MISSING = "EXTERNAL_PROVIDER_MISSING"
COMPILE_FAILED = "COMPILE_FAILED"
DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
OPAQUE_UNSUPPORTED = "OPAQUE_UNSUPPORTED"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ShaderPreviewIR:
    """Stable handoff from Unity material interpretation to Blender nodes."""

    material_guid: str
    material_path: str
    material_name: str
    shader_guid: str
    shader_name: str
    provider_status: str
    mode: str
    confidence: str
    base_color: Color = (1.0, 1.0, 1.0, 1.0)
    base_color_tex: Optional[UnityTextureRef] = None
    normal_tex: Optional[UnityTextureRef] = None
    normal_strength: float = 1.0
    emission_color: Color = (0.0, 0.0, 0.0, 1.0)
    emission_tex: Optional[UnityTextureRef] = None
    emission_strength: float = 1.0
    metallic: float = 0.0
    roughness: float = 0.5
    metallic_tex: Optional[UnityTextureRef] = None
    alpha_mode: str = "opaque"
    alpha_cutoff: float = 0.5
    cull_backface: bool = True
    unsupported_features: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("base_color_tex", "normal_tex", "emission_tex", "metallic_tex"):
            value = getattr(self, key)
            result[key] = value.to_dict() if value else None
        result["base_color"] = list(self.base_color)
        result["emission_color"] = list(self.emission_color)
        result["unsupported_features"] = list(self.unsupported_features)
        return result


def _provider_status(data: UnityMaterialData, asset_db) -> str:
    if not data.shader_guid or data.shader_guid.lower() == BUILTIN_SHADER_GUID:
        return BUILTIN_SHADER if data.shader_file_id in BUILTIN_SHADERS or data.shader_file_id else UNKNOWN
    entry = asset_db.find_guid(data.shader_guid) if asset_db is not None else None
    if entry is not None and entry.path.suffix.lower() in {".shader", ".shadergraph", ".shadersubgraph"}:
        return LOCAL_PROVIDER_FOUND
    return EXTERNAL_PROVIDER_MISSING


def _known_scalar(data: UnityMaterialData, *names: str) -> bool:
    return any(name in data.floats or name in data.ints for name in names)


def build_shader_preview_ir(
    data: UnityMaterialData,
    normalized: NormalizedMaterial,
    asset_db=None,
) -> ShaderPreviewIR:
    """Build a conservative visual preview without guessing unknown semantics."""

    provider = _provider_status(data, asset_db)
    semantic = provider in {BUILTIN_SHADER, LOCAL_PROVIDER_FOUND, CORPUS_PROVIDER_FOUND}
    mode = SEMANTIC_PREVIEW if semantic else GENERIC_FALLBACK_PREVIEW
    confidence = "HIGH" if provider in {BUILTIN_SHADER, LOCAL_PROVIDER_FOUND} else "MEDIUM" if normalized.base_color_tex or normalized.normal_tex else "LOW"
    unsupported: set[str] = set()

    known_texture_properties = {
        ref.property_name for ref in (
            normalized.base_color_tex,
            normalized.normal_tex,
            normalized.emission_tex,
            normalized.metallic_tex,
        ) if ref is not None
    }
    for property_name in data.textures:
        if property_name not in known_texture_properties:
            unsupported.add(f"texture:{property_name}")
    if data.shader_guid and provider == EXTERNAL_PROVIDER_MISSING:
        unsupported.add("external_shader_provider")
    if data.keywords or data.invalid_keywords:
        unsupported.add("keyword_variant")
    if normalized.extras:
        unsupported.add("shader_specific_features")

    # Only expose scalar values when the source property is explicit.  This
    # avoids turning an arbitrary custom float into metallic/roughness.
    metallic = normalized.metallic if _known_scalar(data, "_Metallic", "_MetallicStrength") else 0.0
    roughness = normalized.roughness if _known_scalar(data, "_Glossiness", "_Smoothness", "roughness") else 0.5
    emission_color = normalized.emission_color if "_EmissionColor" in data.colors else (0.0, 0.0, 0.0, 1.0)
    emission_tex = normalized.emission_tex if "_EmissionMap" in data.textures or "_EmissionTex" in data.textures else None
    emission_strength = normalized.emission_strength if _known_scalar(data, "_EmissionStrength", "_EmissionPower") else 1.0

    return ShaderPreviewIR(
        material_guid=data.guid,
        material_path=data.unity_path,
        material_name=data.name,
        shader_guid=data.shader_guid,
        shader_name=normalized.shader_name or data.shader_name,
        provider_status=provider,
        mode=mode,
        confidence=confidence,
        base_color=normalized.base_color,
        base_color_tex=normalized.base_color_tex,
        normal_tex=normalized.normal_tex,
        normal_strength=normalized.normal_strength,
        emission_color=emission_color,
        emission_tex=emission_tex,
        emission_strength=emission_strength,
        metallic=metallic,
        roughness=max(0.0, min(1.0, roughness)),
        metallic_tex=normalized.metallic_tex if "_MetallicGlossMap" in data.textures else None,
        alpha_mode=normalized.alpha_mode,
        alpha_cutoff=normalized.alpha_cutoff,
        cull_backface=normalized.cull_backface,
        unsupported_features=tuple(sorted(unsupported)),
    )


__all__ = [
    "BUILTIN_SHADER", "COMPILE_FAILED", "CORPUS_PROVIDER_FOUND",
    "DEPENDENCY_BLOCKED", "EXTERNAL_PROVIDER_MISSING", "GENERIC_FALLBACK_PREVIEW",
    "LOCAL_PROVIDER_FOUND", "OPAQUE_UNSUPPORTED", "SEMANTIC_PREVIEW", "ShaderPreviewIR",
    "UNKNOWN", "build_shader_preview_ir",
]
