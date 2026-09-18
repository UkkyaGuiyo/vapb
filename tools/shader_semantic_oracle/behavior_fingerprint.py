"""Generic, conservative behavior fingerprints from public Material evidence."""

from __future__ import annotations

from collections import Counter


STATES = {"DETECTED", "PROBABLE", "NOT_OBSERVED", "NOT_TESTED", "UNSUPPORTED", "INCONCLUSIVE"}


def _feature(state: str, confidence: str, evidence: list[dict]) -> dict:
    if state not in STATES:
        raise ValueError(state)
    return {"state": state, "confidence": confidence, "evidence": evidence}


def _evidence(names: set[str], matched: set[str], source: str = "PUBLIC_API") -> list[dict]:
    return [{"source": source, "detail": "property names observed: " + ", ".join(sorted(names & matched))}] if names & matched else []


def fingerprint_from_metadata(record: dict) -> dict:
    names = {name.lower() for values in record.get("property_names", {}).values() for name in values}
    textures = {name.lower() for name in record.get("property_names", {}).get("Texture", [])}
    texture = lambda keys: _feature("DETECTED", "MEDIUM", _evidence(textures, keys)) if textures & keys else _feature("NOT_OBSERVED", "MEDIUM", [])
    prop = lambda keys: _feature("DETECTED", "MEDIUM", _evidence(names, keys)) if names & keys else _feature("NOT_OBSERVED", "MEDIUM", [])
    return {
        "base_texture": texture({"_maintex", "_basemap", "_basecolor"}),
        "base_color": prop({"_color", "_basecolor", "_basecolortint"}),
        "normal": texture({"_bumpmap", "_normalmap", "_normal"}),
        "height_cavity": prop({"_heightmap", "_height", "_cavity", "_occlusionmap"}),
        "metallic_smoothness": prop({"_metallic", "_metallicglossmap", "_smoothness", "_glossiness", "_roughness"}),
        "alpha": prop({"_cutoff", "_alpha", "_alphaclip", "_surface"}),
        "emission": prop({"_emissionmap", "_emissioncolor", "_emission"}),
        "rim_fresnel": prop({"_rimcolor", "_rimpower", "_fresnel"}),
        "toon_lighting": prop({"_shadingshift", "_shadingtoony", "_shadowcolor", "_toon"}),
        "uv_behavior": prop({"_uvscale", "_uvoffset", "_mainscroll"}),
        "time_animation": _feature("NOT_TESTED", "NONE", []),
        "view_dependent": _feature("NOT_TESTED", "NONE", []),
        "light_dependent": _feature("NOT_TESTED", "NONE", []),
        "billboard": _feature("NOT_TESTED", "NONE", []),
        "vertex_deform": _feature("NOT_TESTED", "NONE", []),
        "outline": prop({"_outlinewidth", "_outlinecolor", "_outline"}),
        "multi_pass": _feature("NOT_TESTED", "NONE", []),
        "stencil_dependent": _feature("NOT_TESTED", "NONE", []),
        "unknown_dynamic": _feature("NOT_TESTED", "NONE", []),
    }


def schema_signature(record: dict) -> str:
    names = record.get("property_names", {})
    parts = []
    for kind in sorted(names):
        parts.append(kind + ":" + ",".join(sorted(str(value).lower() for value in names[kind])))
    return "|".join(parts)


def select_representatives(records: list[dict], limit: int = 16) -> list[dict]:
    if limit < 1:
        return []
    remaining = sorted(records, key=lambda item: (schema_signature(item), item.get("material_id", "")))
    selected: list[dict] = []
    seen_schemas: set[str] = set()
    covered: set[str] = set()
    while remaining and len(selected) < limit:
        best = max(remaining, key=lambda item: (_score(item, seen_schemas, covered), schema_signature(item), item.get("material_id", "")))
        remaining.remove(best)
        selected.append(best)
        seen_schemas.add(schema_signature(best))
        covered |= _coverage_keys(best)
    return selected


def _coverage_keys(record: dict) -> set[str]:
    fp = fingerprint_from_metadata(record)
    return {key for key, value in fp.items() if value["state"] == "DETECTED"}


def _score(record: dict, schemas: set[str], covered: set[str]) -> int:
    return (schema_signature(record) not in schemas) * 4 + len(_coverage_keys(record) - covered) * 3 + len(record.get("texture_references", []))


def aggregate_prevalence(fingerprints: list[dict]) -> dict:
    return {key: dict(Counter(item[key]["state"] for item in fingerprints)) for key in fingerprints[0]} if fingerprints else {}
