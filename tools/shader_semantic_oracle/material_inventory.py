"""Metadata-first Material/Shader characterization for private UnityPackages."""

from __future__ import annotations

import copy
import re
import tarfile
from collections import Counter
from pathlib import Path


GUID_RE = re.compile(r"(?i)\bguid:\s*([0-9a-f]{32})\b")
TEXT_LIMIT = 8 * 1024 * 1024
SECTION_NAMES = {"m_TexEnvs": "Texture", "m_Colors": "Color", "m_Floats": "Float", "m_Vectors": "Vector", "m_Ints": "Int"}


def _read(archive, member):
    if member is None or member.size > TEXT_LIMIT:
        return ""
    handle = archive.extractfile(member)
    return "" if handle is None else handle.read(TEXT_LIMIT + 1).decode("utf-8", errors="replace")[:TEXT_LIMIT]


def _number_map(value):
    return {key: float(number) for key, number in re.findall(r"([xyzw]):\s*(-?[0-9.eE+]+)", value)}


def _material_record(material_id, pathname, guid, text):
    shader_match = re.search(r"m_Shader:.*?guid:\s*([0-9a-f]{32})", text, re.I)
    records = {name: [] for name in SECTION_NAMES.values()}
    transforms = {}
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        section_key = stripped.rstrip(":")
        if stripped.endswith(":") and section_key in SECTION_NAMES:
            section = SECTION_NAMES[section_key]
            continue
        if stripped.startswith("m_") and stripped.endswith(":"):
            section = None
        match = re.match(r"^\s*-\s+([A-Za-z0-9_]+):\s*(.*)$", line)
        if match and section:
            name, value = match.groups()
            records[section].append(name)
            if section == "Texture":
                block = value
                transforms[name] = {"scale": {}, "offset": {}}
        if section == "Texture" and line.strip().startswith("m_Scale:") and transforms:
            transforms[list(transforms)[-1]]["scale"] = _number_map(line)
        if section == "Texture" and line.strip().startswith("m_Offset:") and transforms:
            transforms[list(transforms)[-1]]["offset"] = _number_map(line)
    textures = []
    if records["Texture"]:
        for guid in GUID_RE.findall(text):
            if guid.lower() != (shader_match.group(1).lower() if shader_match else "") and guid.lower() not in textures:
                textures.append(guid.lower())
    property_counts = {kind: len(values) for kind, values in records.items() if values}
    return {
        "material_id": material_id,
        "asset_path": pathname,
        "asset_guid": guid,
        "shader_guid": shader_match.group(1).lower() if shader_match else None,
        "property_names": records,
        "property_counts": property_counts,
        "texture_references": textures,
        "texture_transforms": transforms,
        "render_queue": int(re.search(r"m_CustomRenderQueue:\s*(-?\d+)", text).group(1)) if re.search(r"m_CustomRenderQueue:\s*(-?\d+)", text) else None,
        "keywords_present": "m_ShaderKeywords:" in text,
    }


def inventory_material_package(path: Path) -> dict:
    path = Path(path)
    materials = []
    with tarfile.open(path, "r:*") as archive:
        members = {member.name: member for member in archive if member.isfile()}
        for name, pathname_member in members.items():
            if not name.endswith("/pathname"):
                continue
            pathname = _read(archive, pathname_member).strip().replace("\\", "/")
            if not pathname.lower().endswith(".mat"):
                continue
            guid = name.split("/", 1)[0]
            text = _read(archive, members.get(f"{guid}/asset"))
            materials.append(_material_record(f"M-{len(materials) + 1:05d}", pathname, guid.lower(), text))
    shader_frequency = Counter(item["shader_guid"] or "SHADER_MISSING" for item in materials)
    properties = Counter(kind for item in materials for kind, count in item["property_counts"].items() for _ in range(count))
    return {
        "package_path": str(path.resolve()),
        "material_count": len(materials),
        "materials": materials,
        "shader_frequency": dict(shader_frequency),
        "property_frequency": dict(properties),
    }


def scan_material_corpus(root: Path) -> dict:
    packages = []
    materials = []
    material_index = 0
    for package in sorted(Path(root).rglob("*.unitypackage"), key=lambda p: str(p).lower()):
        result = inventory_material_package(package)
        for item in result["materials"]:
            material_index += 1
            item["material_id"] = f"M-{material_index:05d}"
            materials.append(item)
        packages.append({"package_path": result["package_path"], "material_count": result["material_count"]})
    shaders = Counter(item["shader_guid"] or "SHADER_MISSING" for item in materials)
    property_frequency = Counter(kind for item in materials for kind, count in item["property_counts"].items() for _ in range(count))
    return {
        "schema_version": "0.1",
        "corpus_root": str(Path(root).resolve()),
        "material_count": len(materials),
        "unique_shader_count": len(shaders),
        "shader_frequency": dict(shaders),
        "property_frequency": dict(property_frequency),
        "packages": packages,
        "materials": materials,
    }


def public_safe_summary(result: dict) -> dict:
    safe = copy.deepcopy(result)
    safe.pop("corpus_root", None)
    safe.pop("shader_frequency", None)
    safe["materials"] = [
        {"material_id": item["material_id"], "property_counts": item["property_counts"], "has_shader": bool(item.get("shader_guid")), "texture_count": len(item.get("texture_references", []))}
        for item in result["materials"]
    ]
    safe["packages"] = [{"material_count": item["material_count"]} for item in result.get("packages", [])]
    return safe
