"""Safe same-directory UnityPackage dependency discovery by GUID graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tarfile
from typing import Iterable

from .material_mapping import parse_external_objects
from .package_identity import PackageIdentity
from .package_reader import UnityPackageReader


@dataclass
class SiblingPackageCandidate:
    path: str
    package_id: str
    provided_guids: set[str] = field(default_factory=set)
    matched_guids: set[str] = field(default_factory=set)
    match_count: int = 0
    coverage_ratio: float = 0.0


@dataclass
class SiblingDiscoveryResult:
    root_package: str
    packages: list[SiblingPackageCandidate]
    unresolved_guids: set[str]
    ambiguous_guids: set[str]
    dependency_edges: list[dict[str, str]]
    status: str


def _asset_texts(path: Path) -> list[tuple[str, str, bytes]]:
    result = []
    with tarfile.open(path, "r:*") as archive:
        groups: dict[str, dict[str, object]] = {}
        for member in archive:
            parts = member.name.replace("\\", "/").split("/")
            if len(parts) != 2 or parts[1] not in {"asset", "asset.meta", "pathname"} or not member.isfile():
                continue
            groups.setdefault(parts[0], {})[parts[1]] = member
        for guid, members in groups.items():
            pathname = members.get("pathname")
            asset = members.get("asset")
            if pathname is None or asset is None:
                continue
            path_value = archive.extractfile(pathname).read().decode("utf-8", "replace").strip()
            if Path(path_value).suffix.lower() not in {".prefab", ".fbx", ".mat", ".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"}:
                continue
            payload = archive.extractfile(asset).read()
            result.append((guid.lower(), path_value, payload))
    return result


def required_guids(package_path: Path, records: list[tuple[str, str, bytes]] | None = None) -> set[str]:
    required: set[str] = set()
    for _guid, unity_path, payload in (records if records is not None else _asset_texts(package_path)):
        text = payload.decode("utf-8", "replace")
        if unity_path.lower().endswith(".prefab"):
            required.update(re.findall(r"guid:\s*([0-9a-fA-F]{32})", text))
        elif unity_path.lower().endswith(".mat"):
            required.update(re.findall(r"guid:\s*([0-9a-fA-F]{32})", text))
        elif unity_path.lower().endswith(".fbx"):
            required.update(parse_external_objects(text).values())
    return {
        guid.lower() for guid in required
        if guid.lower() not in {"0000000000000000f000000000000000", "00000000000000000000000000000000"}
    }


def provided_guids(package_path: Path, records: list[tuple[str, str, bytes]] | None = None) -> set[str]:
    return {guid.lower() for guid, _path, _payload in (records if records is not None else _asset_texts(package_path))}


def discover_siblings(root_path: Path, *, max_depth: int = 32) -> SiblingDiscoveryResult:
    root_path = Path(root_path).resolve()
    sibling_paths = sorted(path for path in root_path.parent.glob("*.unitypackage") if path.resolve() != root_path)
    record_cache: dict[Path, list[tuple[str, str, bytes]]] = {}

    def records_for(path: Path) -> list[tuple[str, str, bytes]]:
        key = path.resolve()
        if key not in record_cache:
            record_cache[key] = _asset_texts(path)
        return record_cache[key]

    selected = {root_path.resolve()}
    # A package with no same-directory sibling has no discovery work to do.
    # In particular, do not read the full primary archive just to prove that
    # there are no candidates; the normal import path already builds its own
    # index and this scan is only an optional cross-package pass.
    if not sibling_paths:
        return SiblingDiscoveryResult(str(root_path), [], set(), set(), [], "NONE")
    root_records = records_for(root_path)
    unresolved = required_guids(root_path, root_records) - provided_guids(root_path, root_records)
    candidates: list[SiblingPackageCandidate] = []
    providers: dict[str, list[Path]] = {}
    changed = True
    while changed and unresolved:
        changed = False
        providers.clear()
        for path in sibling_paths:
            if path.resolve() in selected:
                continue
            provided = provided_guids(path, records_for(path))
            for guid in unresolved & provided:
                providers.setdefault(guid, []).append(path)
        ambiguous_now = {guid for guid, paths in providers.items() if len(paths) > 1}
        for path in sibling_paths:
            if path.resolve() in selected:
                continue
            provided = provided_guids(path, records_for(path))
            matched = (unresolved & provided) - ambiguous_now
            if not matched:
                continue
            candidate = SiblingPackageCandidate(str(path), PackageIdentity.from_path(path).source_package_id, provided)
            candidate.matched_guids = matched
            candidate.match_count = len(matched)
            candidate.coverage_ratio = candidate.match_count / len(unresolved) if unresolved else 0.0
            candidates.append(candidate)
            selected.add(path.resolve())
            unresolved = (unresolved - provided) | (required_guids(path, records_for(path)) - provided)
            changed = True
            break
    ambiguous = {guid for guid, paths in providers.items() if len(paths) > 1}
    remaining = unresolved | ambiguous
    status = "AMBIGUOUS" if ambiguous else "COMPLETE" if not remaining else "PARTIAL" if candidates else "NONE"
    edges = [{"from": str(root_path), "to": candidate.path, "reason": "GUID_MATCH"} for candidate in candidates]
    return SiblingDiscoveryResult(str(root_path), candidates, remaining, ambiguous, edges, status)
