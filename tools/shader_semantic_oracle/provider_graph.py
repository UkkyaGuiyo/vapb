"""Private, metadata-first Shader provider discovery for the semantic oracle.

This module intentionally does not implement Blender shader preview behavior.  It
only builds a deterministic graph from UnityPackage metadata and Material YAML.
Raw asset payloads are never returned by the public API.
"""

from __future__ import annotations

import re
import tarfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable


GUID_RE = re.compile(r"^[0-9a-f]{32}$")
SHADER_REF_RE = re.compile(
    r"m_Shader:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-fA-F]{32})"
)
BUILTIN_SHADER_GUIDS = frozenset(
    {
        "0000000000000000f000000000000000",
        "0000000000000000e000000000000000",
    }
)
SHADER_EXTENSIONS = frozenset({".shader", ".shadergraph", ".shadersubgraph"})


def _guid(value: str) -> str | None:
    value = value.strip().lower()
    return value if GUID_RE.fullmatch(value) else None


def _asset_type(pathname: str) -> str:
    suffix = Path(pathname).suffix.lower()
    return {
        ".mat": "material",
        ".shader": "shader",
        ".shadergraph": "shadergraph",
        ".shadersubgraph": "shadersubgraph",
    }.get(suffix, "other")


def _package_alias(package: Path, index: int) -> str:
    return f"PACKAGE_{index + 1:02d}"


def _read_text(tar: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    handle = tar.extractfile(member)
    return handle.read().decode("utf-8", "replace") if handle else ""


def scan_package(package: Path, alias: str) -> dict:
    """Read package metadata and material shader references without extracting."""
    providers: list[dict] = []
    materials: list[dict] = []
    with tarfile.open(package, "r:gz") as tar:
        members = {member.name: member for member in tar.getmembers()}
        for name, pathname_member in members.items():
            if not name.endswith("/pathname"):
                continue
            asset_guid = _guid(name.rsplit("/", 1)[0])
            if not asset_guid:
                continue
            pathname = _read_text(tar, pathname_member).strip()
            asset_type = _asset_type(pathname)
            record = {
                "package": alias,
                "asset_guid": asset_guid,
                "asset_path": pathname,
                "asset_type": asset_type,
            }
            if asset_type in {"shader", "shadergraph", "shadersubgraph"}:
                providers.append(record)
            elif asset_type == "material":
                asset_member = members.get(f"{asset_guid}/asset")
                text = _read_text(tar, asset_member) if asset_member else ""
                matches = [_guid(value) for value in SHADER_REF_RE.findall(text)]
                shader_guid = next((value for value in matches if value), None)
                materials.append({**record, "shader_guid": shader_guid})
    return {"package": alias, "providers": providers, "materials": materials}


def build_provider_graph(packages: Iterable[Path]) -> dict:
    """Return a privacy-safe GUID -> provider graph and material classifications."""
    package_paths = [Path(path) for path in packages]
    scanned = [scan_package(path, _package_alias(path, i)) for i, path in enumerate(package_paths)]
    by_guid: dict[str, list[dict]] = defaultdict(list)
    for package in scanned:
        for provider in package["providers"]:
            by_guid[provider["asset_guid"]].append(provider)

    materials: list[dict] = []
    for package in scanned:
        for material in package["materials"]:
            shader_guid = material["shader_guid"]
            if not shader_guid:
                classification = "SHADER_REFERENCE_MISSING"
                candidates: list[dict] = []
            elif shader_guid in BUILTIN_SHADER_GUIDS:
                classification = "BUILTIN_SHADER"
                candidates = []
            else:
                all_candidates = list(by_guid.get(shader_guid, []))
                local_candidates = [
                    candidate for candidate in all_candidates
                    if candidate["package"] == package["package"]
                ]
                candidates = local_candidates or all_candidates
                if len(candidates) > 1:
                    classification = "SHADER_REFERENCE_AMBIGUOUS"
                elif not candidates:
                    classification = "EXTERNAL_PROVIDER_MISSING"
                elif candidates[0]["package"] == package["package"]:
                    classification = "LOCAL_PROVIDER_FOUND"
                else:
                    classification = "CORPUS_PROVIDER_FOUND"
            materials.append(
                {
                    "package": package["package"],
                    "material_guid": material["asset_guid"],
                    "material_path": material["asset_path"],
                    "shader_guid": shader_guid,
                    "classification": classification,
                    "provider_candidates": candidates,
                }
            )

    shader_identities = {}
    for material in materials:
        shader_guid = material["shader_guid"]
        if shader_guid:
            shader_identities.setdefault(shader_guid, {"material_count": 0, "classifications": {}})
            identity = shader_identities[shader_guid]
            identity["material_count"] += 1
            counts = identity["classifications"]
            counts[material["classification"]] = counts.get(material["classification"], 0) + 1

    return {
        "schema_version": 1,
        "package_count": len(scanned),
        "provider_count": sum(len(package["providers"]) for package in scanned),
        "material_count": len(materials),
        "shader_identity_count": len(shader_identities),
        "shader_identities": shader_identities,
        "materials": materials,
        "providers": [provider for package in scanned for provider in package["providers"]],
    }


def classify_unity_validation(*, shader_loaded: bool, shader_name: str | None,
                              supported: bool = True, compile_error: bool = False) -> str:
    """Map a Unity observation to a non-ambiguous provider validation category."""
    if compile_error:
        return "PROVIDER_PRESENT_COMPILE_FAILED"
    if not shader_loaded or not shader_name or shader_name == "Hidden/InternalErrorShader" or not supported:
        return "DEPENDENCY_BLOCKED"
    return "VALID_SHADER"
