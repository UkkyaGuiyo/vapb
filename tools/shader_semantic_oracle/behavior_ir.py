"""Conservative, public-safe Shader Preview IR classification.

The classifier reports observed property evidence only. It never infers a
shader implementation from a private shader binary or source file.
"""

from __future__ import annotations


def _names(record: dict) -> set[str]:
    return {name.lower() for values in record.get("property_names", {}).values() for name in values}


def _feature(state: str, evidence: list[str] | None = None) -> dict:
    return {"state": state, "evidence": evidence or []}


def classify_material_schema(record: dict) -> dict:
    names = _names(record)
    texture = {name.lower() for name in record.get("property_names", {}).get("Texture", [])}
    result = {
        "schema_version": "0.1",
        "identity": {"shader_guid_observed": bool(record.get("shader_guid"))},
        "base_surface": _feature("DETECTED" if names & {"_maintex", "_basemap", "_color", "_basecolor"} else "NOT_OBSERVED", sorted(names & {"_maintex", "_basemap", "_color", "_basecolor"})),
        "alpha": _feature("DETECTED" if names & {"_cutoff", "_alpha", "_alphaclip", "_alphapremultiply"} else "NOT_OBSERVED", sorted(names & {"_cutoff", "_alpha", "_alphaclip", "_alphapremultiply"})),
        "normal": _feature("DETECTED" if texture & {"_bumpmap", "_normalmap", "_normal"} else "NOT_OBSERVED", sorted(texture & {"_bumpmap", "_normalmap", "_normal"})),
        "emission": _feature("DETECTED" if names & {"_emissionmap", "_emissioncolor", "_emission"} else "NOT_OBSERVED", sorted(names & {"_emissionmap", "_emissioncolor", "_emission"})),
        "metallic_smoothness": _feature("DETECTED" if names & {"_metallic", "_metallicglossmap", "_glossiness", "_smoothness", "_roughness"} else "NOT_OBSERVED", sorted(names & {"_metallic", "_metallicglossmap", "_glossiness", "_smoothness", "_roughness"})),
        "rim_fresnel": _feature("DETECTED" if names & {"_rimcolor", "_rimpower", "_fresnel"} else "NOT_OBSERVED", sorted(names & {"_rimcolor", "_rimpower", "_fresnel"})),
        "toon_lighting": _feature("DETECTED" if names & {"_shadingshift", "_shadingtoony", "_shadowcolor", "_toon"} else "NOT_OBSERVED", sorted(names & {"_shadingshift", "_shadingtoony", "_shadowcolor", "_toon"})),
        "uv_behavior": _feature("DETECTED" if any(name in names for name in {"_mainscroll", "_uvscale", "_uvoffset"}) else "NOT_OBSERVED", sorted(names & {"_mainscroll", "_uvscale", "_uvoffset"})),
        "time_behavior": _feature("NOT_TESTED"),
        "view_behavior": _feature("NOT_TESTED"),
        "light_behavior": _feature("NOT_TESTED"),
        "unsupported_features": [],
    }
    return result
