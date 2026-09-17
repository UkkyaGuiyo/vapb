"""Stream UnityPackage metadata without inflating binary payloads."""

from __future__ import annotations

import copy
import json
import re
import tarfile
from pathlib import Path
from typing import Iterable


GUID_RE = re.compile(r"(?i)\bguid:\s*([0-9a-f]{32})\b")
TEXT_EXTENSIONS = {
    ".asset", ".anim", ".controller", ".cs", ".json", ".mat", ".meta",
    ".prefab", ".shader", ".shadergraph", ".shadersubgraph", ".txt",
}
TEXT_PATH_SUFFIXES = ("package.json", ".fbx.meta")
TEXT_LIMIT = 8 * 1024 * 1024


class CorpusPackageError(ValueError):
    """A package could not be safely read as a UnityPackage archive."""


def _is_guid(value: str) -> bool:
    return bool(re.fullmatch(r"(?i)[0-9a-f]{32}", value))


def _read_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    if member.size > TEXT_LIMIT:
        return ""
    handle = archive.extractfile(member)
    if handle is None:
        return ""
    return handle.read(TEXT_LIMIT + 1).decode("utf-8", errors="replace")[:TEXT_LIMIT]


def _kind(pathname: str) -> str:
    lower = pathname.lower().rstrip("/")
    return Path(lower).suffix


def _empty_observed() -> dict:
    return {
        "prefab_instance_documents": 0,
        "direct_renderer_documents": 0,
        "skinned_mesh_renderer_documents": 0,
        "mesh_renderer_documents": 0,
        "mesh_filter_documents": 0,
        "property_modification_count": 0,
        "material_override_count": 0,
        "external_objects_files": 0,
        "mono_behaviour_documents": 0,
        "custom_shader_references": 0,
        "assetpostprocessor_script_count": 0,
        "scripted_importer_script_count": 0,
        "referenced_guids": [],
        "source_prefab_guids": [],
        "fbx_guids": [],
        "material_guids": [],
        "texture_guids": [],
    }


def _append_unique(target: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def _signatures(record: dict) -> tuple[list[str], list[str]]:
    observed = record["observed"]
    metrics = record["metrics"]
    signatures: list[str] = []
    heuristics: list[str] = []
    if observed["prefab_instance_documents"]:
        signatures.append("PREFAB_INSTANCE")
    if observed["skinned_mesh_renderer_documents"]:
        signatures.append("SKINNED_MESH")
    if observed["mesh_renderer_documents"]:
        signatures.append("MESH_RENDERER")
    if observed["mesh_filter_documents"]:
        signatures.append("MESH_FILTER")
    if observed["material_override_count"]:
        signatures.append("MATERIAL_OVERRIDE")
    if observed["external_objects_files"]:
        signatures.append("EXTERNAL_OBJECTS")
    if metrics["material_count"] and metrics["texture_count"]:
        signatures.append("MATERIAL_TEXTURE")
    if metrics["prefab_count"] and metrics["fbx_count"]:
        signatures.append("MODEL_PREFAB")
    if metrics["material_count"] > 1:
        signatures.append("MULTIPLE_MATERIAL_ASSETS")
    if observed["mono_behaviour_documents"]:
        signatures.append("MONOBEHAVIOUR")
    if observed["custom_shader_references"]:
        signatures.append("CUSTOM_SHADER_REFERENCE")
    if observed["assetpostprocessor_script_count"]:
        signatures.append("ASSETPOSTPROCESSOR_SCRIPT")
    if observed["scripted_importer_script_count"]:
        signatures.append("SCRIPTED_IMPORTER_SCRIPT")
    if observed["prefab_instance_documents"] > 1:
        heuristics.append("LIKELY_NESTED_PREFAB_OR_VARIANT")
    if metrics["prefab_count"] and not observed["prefab_instance_documents"]:
        heuristics.append("LIKELY_EXPANDED_DIRECT_PREFAB")
    if metrics["fbx_count"] and metrics["material_count"] == 0:
        heuristics.append("LIKELY_GEOMETRY_PROVIDER")
    if metrics["material_count"] and metrics["fbx_count"] == 0:
        heuristics.append("LIKELY_MATERIAL_PROVIDER")
    return sorted(set(signatures)), sorted(set(heuristics))


def inventory_package(path: Path, case_id: str) -> dict:
    """Return a deterministic metadata inventory for one UnityPackage."""
    path = Path(path)
    if path.suffix.lower() != ".unitypackage":
        raise CorpusPackageError(f"not a unitypackage: {path}")
    metrics = {
        "archive_bytes": path.stat().st_size,
        "total_assets": 0,
        "prefab_count": 0,
        "fbx_count": 0,
        "material_count": 0,
        "texture_count": 0,
        "shader_count": 0,
        "animation_controller_count": 0,
        "script_count": 0,
        "editor_script_count": 0,
        "folder_count": 0,
        "meta_count": 0,
    }
    observed = _empty_observed()
    provided_guids: list[str] = []
    pathnames: list[str] = []
    asset_members_by_pathname: dict[str, tarfile.TarInfo] = {}
    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = {member.name: member for member in archive if member.isfile()}
            for name, member in members.items():
                parts = name.split("/", 1)
                if parts and _is_guid(parts[0]) and parts[0] not in provided_guids:
                    provided_guids.append(parts[0].lower())
                if len(parts) != 2 or parts[1] != "pathname":
                    continue
                pathname = _read_member(archive, member).strip().replace("\\", "/")
                if not pathname:
                    continue
                pathnames.append(pathname)
                asset_members_by_pathname[pathname] = members.get(f"{parts[0]}/asset")
                lower = pathname.lower()
                if lower.endswith("/"):
                    metrics["folder_count"] += 1
                    continue
                metrics["total_assets"] += 1
                suffix = _kind(pathname)
                if suffix == ".meta":
                    metrics["meta_count"] += 1
                if suffix == ".prefab":
                    metrics["prefab_count"] += 1
                elif suffix == ".fbx":
                    metrics["fbx_count"] += 1
                elif suffix in {".mat", ".material"}:
                    metrics["material_count"] += 1
                elif suffix in {".png", ".jpg", ".jpeg", ".tga", ".psd", ".tif", ".tiff", ".exr", ".dds", ".bmp", ".gif"}:
                    metrics["texture_count"] += 1
                elif suffix in {".shader", ".shadergraph", ".shadersubgraph"}:
                    metrics["shader_count"] += 1
                elif suffix in {".anim", ".controller", ".overridecontroller"}:
                    metrics["animation_controller_count"] += 1
                elif suffix in {".cs", ".js", ".boo"}:
                    metrics["script_count"] += 1
                    if "/editor/" in lower or lower.startswith("editor/"):
                        metrics["editor_script_count"] += 1

            for pathname in pathnames:
                asset_member = asset_members_by_pathname.get(pathname)
                if asset_member is None:
                    continue
                lower = pathname.lower()
                is_text = Path(lower).suffix in TEXT_EXTENSIONS or lower.endswith(TEXT_PATH_SUFFIXES)
                if not is_text:
                    continue
                text = _read_member(archive, asset_member)
                refs = [value.lower() for value in GUID_RE.findall(text)]
                _append_unique(observed["referenced_guids"], refs)
                if lower.endswith(".prefab"):
                    observed["prefab_instance_documents"] += text.count("PrefabInstance:")
                    observed["direct_renderer_documents"] += text.count("Renderer:")
                    observed["skinned_mesh_renderer_documents"] += text.count("SkinnedMeshRenderer:")
                    observed["mesh_renderer_documents"] += text.count("MeshRenderer:")
                    observed["mesh_filter_documents"] += text.count("MeshFilter:")
                    observed["property_modification_count"] += len(re.findall(r"(?m)^\s*-\s+target:\s*\{", text))
                    observed["material_override_count"] += len(re.findall(r"propertyPath:\s*m_Materials\.Array\.data\[", text))
                    _append_unique(observed["source_prefab_guids"], re.findall(r"m_SourcePrefab:.*?guid:\s*([0-9a-f]{32})", text, re.I))
                if lower.endswith(".fbx.meta"):
                    if "externalObjects:" in text:
                        observed["external_objects_files"] += 1
                observed["mono_behaviour_documents"] += text.count("MonoBehaviour:")
                observed["custom_shader_references"] += len(re.findall(r"(?m)^\s*m_Shader:\s*\{", text))
                if lower.endswith((".shader", ".shadergraph", ".shadersubgraph")):
                    observed["custom_shader_references"] += 1
                if lower.endswith((".cs", ".js", ".boo")):
                    observed["assetpostprocessor_script_count"] += len(re.findall(r"AssetPostprocessor", text))
                    observed["scripted_importer_script_count"] += len(re.findall(r"ScriptedImporter", text))
                if lower.endswith(".fbx"):
                    _append_unique(observed["fbx_guids"], refs)
                elif lower.endswith((".mat", ".material")):
                    _append_unique(observed["material_guids"], refs)
                elif Path(lower).suffix in {".png", ".jpg", ".jpeg", ".tga", ".psd", ".tif", ".tiff", ".exr", ".dds", ".bmp", ".gif"}:
                    _append_unique(observed["texture_guids"], refs)
    except (OSError, tarfile.TarError) as exc:
        raise CorpusPackageError(f"could not read {path}: {exc}") from exc
    record = {
        "case_id": case_id,
        "source_directory": str(path.parent),
        "source_filename": path.name,
        "source_path": str(path.resolve()),
        "metrics": metrics,
        "observed": observed,
        "provided_guids": sorted(provided_guids),
        "pathnames": sorted(pathnames),
    }
    record["signatures"], record["heuristics"] = _signatures(record)
    return record


def infer_package_groups(packages: list[dict]) -> list[list[str]]:
    """Infer groups from GUID provider/consumer evidence only."""
    parent = {item["case_id"]: item["case_id"] for item in packages}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    for index, left in enumerate(packages):
        left_provided = set(left["provided_guids"])
        left_references = set(left["observed"]["referenced_guids"])
        for right in packages[index + 1:]:
            right_provided = set(right["provided_guids"])
            right_references = set(right["observed"]["referenced_guids"])
            if (left_references & right_provided) or (right_references & left_provided):
                union(left["case_id"], right["case_id"])
    grouped: dict[str, list[str]] = {}
    for item in packages:
        root = find(item["case_id"])
        grouped.setdefault(root, []).append(item["case_id"])
    return sorted(sorted(values) for values in grouped.values() if len(values) > 1)


def cluster_packages(packages: list[dict]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for item in packages:
        key = "+".join(item["signatures"] + item["heuristics"]) or "UNCLASSIFIED"
        clusters.setdefault(key, []).append(item["case_id"])
    return {key: sorted(value) for key, value in sorted(clusters.items())}


def select_representatives(packages: list[dict], limit: int = 8) -> list[str]:
    remaining = {item["case_id"]: set(item["signatures"] + item["heuristics"]) for item in packages}
    selected: list[str] = []
    covered: set[str] = set()
    while remaining and len(selected) < limit:
        case_id, features = max(remaining.items(), key=lambda pair: (len(pair[1] - covered), -int(pair[0].split("-")[-1])))
        gained = features - covered
        if not gained:
            break
        selected.append(case_id)
        covered |= features
        remaining.pop(case_id)
    cluster_cases: dict[str, list[str]] = {}
    for item in packages:
        key = "+".join(item["signatures"] + item["heuristics"]) or "UNCLASSIFIED"
        cluster_cases.setdefault(key, []).append(item["case_id"])
    for cases in sorted(cluster_cases.values(), key=lambda values: values[0]):
        if len(selected) >= limit:
            break
        case_id = sorted(cases)[0]
        if case_id not in selected:
            selected.append(case_id)
    return selected


def scan_corpus(root: Path) -> dict:
    root = Path(root).resolve()
    paths = sorted(root.rglob("*.unitypackage"), key=lambda path: str(path).lower())
    packages: list[dict] = []
    failures: list[dict] = []
    for index, path in enumerate(paths, start=1):
        case_id = f"CASE-{index:04d}"
        try:
            packages.append(inventory_package(path, case_id))
        except CorpusPackageError as exc:
            failures.append({"case_id": case_id, "source_path": str(path.resolve()), "error": str(exc)})
    return {
        "schema_version": "0.1",
        "corpus_root": str(root),
        "directories_scanned": sum(1 for _ in root.rglob("*" ) if _.is_dir()) + 1,
        "packages": packages,
        "failures": failures,
        "package_groups": infer_package_groups(packages),
        "clusters": cluster_packages(packages),
        "representative_case_ids": select_representatives(packages),
        "totals": {
            "unitypackages": len(paths),
            "successful_packages": len(packages),
            "failed_packages": len(failures),
            "archive_bytes": sum(item["metrics"]["archive_bytes"] for item in packages),
            "prefabs": sum(item["metrics"]["prefab_count"] for item in packages),
            "fbxs": sum(item["metrics"]["fbx_count"] for item in packages),
            "materials": sum(item["metrics"]["material_count"] for item in packages),
            "textures": sum(item["metrics"]["texture_count"] for item in packages),
            "packages_with_prefab_instances": sum(bool(item["observed"]["prefab_instance_documents"]) for item in packages),
            "packages_with_direct_renderers": sum(bool(item["observed"]["direct_renderer_documents"]) for item in packages),
            "packages_with_external_objects": sum(bool(item["observed"]["external_objects_files"]) for item in packages),
            "packages_with_material_overrides": sum(bool(item["observed"]["material_override_count"]) for item in packages),
        },
    }


def public_safe_summary(inventory: dict) -> dict:
    """Strip names, paths, GUIDs, and per-package reconstructive details."""
    safe = copy.deepcopy(inventory)
    safe.pop("corpus_root", None)
    safe["packages"] = [
        {
            "case_id": item["case_id"],
            "metrics": item["metrics"],
            "signatures": item["signatures"],
            "heuristics": item["heuristics"],
        }
        for item in inventory["packages"]
    ]
    safe["failures"] = [{"case_id": item["case_id"], "error_category": "PACKAGE_READ_FAILURE"} for item in inventory["failures"]]
    return safe


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
