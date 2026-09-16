"""Bounded, metadata-first UnityPackage visual dependency discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tarfile

from .material_mapping import parse_external_objects
from .package_identity import PackageIdentity


TEXTUAL_EXTENSIONS = {".prefab", ".mat"}
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"}


@dataclass(frozen=True)
class PackageManifestEntry:
    guid: str
    asset_path: str
    extension: str
    has_asset: bool
    has_meta: bool
    asset_size: int = 0
    meta_size: int = 0
    meta_bytes: bytes = b""


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
    visual_status: str = "NONE"
    unresolved_visual_guids: set[str] = field(default_factory=set)
    ambiguous_visual_guids: set[str] = field(default_factory=set)
    unresolved_external_guids: set[str] = field(default_factory=set)
    manifest_entries: int = 0
    accounting: dict[str, int] = field(default_factory=dict)


def _manifest(path: Path, accounting: dict[str, int] | None = None) -> list[PackageManifestEntry]:
    """Read pathname and FBX metadata only; never read an asset member."""
    accounting = accounting if accounting is not None else {}
    groups: dict[str, dict[str, tarfile.TarInfo]] = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            parts = member.name.replace("\\", "/").split("/")
            if len(parts) != 2 or parts[1] not in {"asset", "asset.meta", "pathname"} or not member.isfile():
                continue
            groups.setdefault(parts[0].lower(), {})[parts[1]] = member
        result: list[PackageManifestEntry] = []
        for guid, members in groups.items():
            pathname = members.get("pathname")
            if pathname is None:
                continue
            path_file = archive.extractfile(pathname)
            if path_file is None:
                continue
            asset_path = path_file.read().decode("utf-8", "replace").strip()
            extension = Path(asset_path).suffix.casefold()
            if extension not in TEXTUAL_EXTENSIONS | TEXTURE_EXTENSIONS | {".fbx"}:
                continue
            asset = members.get("asset")
            meta = members.get("asset.meta")
            meta_bytes = b""
            if meta is not None and extension == ".fbx":
                meta_file = archive.extractfile(meta)
                meta_bytes = meta_file.read() if meta_file else b""
                accounting["metadata_bytes_read"] = accounting.get("metadata_bytes_read", 0) + len(meta_bytes)
            result.append(PackageManifestEntry(guid, asset_path, extension, asset is not None, meta is not None, asset.size if asset else 0, meta.size if meta else 0, meta_bytes))
    accounting["manifest_scans"] = accounting.get("manifest_scans", 0) + 1
    accounting.setdefault("texture_payload_bytes_read", 0)
    accounting.setdefault("fbx_payload_bytes_read", 0)
    return result


def _read_asset(path: Path, guid: str, extension: str, accounting: dict[str, int]) -> bytes:
    """Read a recognized textual dependency source on demand."""
    with tarfile.open(path, "r:*") as archive:
        handle = archive.extractfile(archive.getmember(f"{guid}/asset"))
        payload = handle.read() if handle else b""
    accounting["metadata_text_bytes_read"] = accounting.get("metadata_text_bytes_read", 0) + len(payload)
    accounting[f"{extension.lstrip('.').lower()}_text_reads"] = accounting.get(f"{extension.lstrip('.').lower()}_text_reads", 0) + 1
    return payload


def _visual_guids_from_text(extension: str, payload: bytes) -> set[str]:
    text = payload.decode("utf-8", "replace")
    if extension == ".prefab":
        found = {guid.lower() for guid in re.findall(r"m_Materials(?:\.Array\.data\[\d+\])?[\s\S]{0,420}?guid:\s*([0-9a-fA-F]{32})", text)}
        found.update(guid.lower() for guid in re.findall(r"propertyPath:\s*m_Materials\.Array\.data\[\d+\][\s\S]{0,260}?objectReference:\s*\{[^}]*guid:\s*([0-9a-fA-F]{32})", text))
        return found
    if extension == ".mat":
        return {guid.lower() for guid in re.findall(r"m_Texture:\s*\{[^}]*guid:\s*([0-9a-fA-F]{32})", text)}
    return set()


def _visual_requirements(path: Path, entries: list[PackageManifestEntry], accounting: dict[str, int]) -> set[str]:
    required: set[str] = set()
    for entry in entries:
        if entry.extension in TEXTUAL_EXTENSIONS and entry.has_asset:
            required.update(_visual_guids_from_text(entry.extension, _read_asset(path, entry.guid, entry.extension, accounting)))
        elif entry.extension == ".fbx" and entry.meta_bytes:
            required.update(value.lower() for value in parse_external_objects(entry.meta_bytes.decode("utf-8", "replace")).values())
    return {guid for guid in required if guid not in {"0" * 32, "0000000000000000f000000000000000"}}


def _candidate_paths(root_path: Path, unresolved: set[str], *, include_adjacent: bool = False) -> list[Path]:
    candidates = {path.resolve() for path in root_path.parent.glob("*.unitypackage") if path.resolve() != root_path}
    # Start with the package's own directory. If visual requirements remain
    # unresolved, expand once to the bounded bundle neighborhood. This keeps
    # discovery deterministic without arbitrary recursive scans.
    if unresolved and include_adjacent:
        bundle_root = root_path.parent.parent
        if bundle_root.is_dir():
            candidates.update(path.resolve() for path in bundle_root.glob("*.unitypackage"))
            for directory in bundle_root.iterdir():
                if directory.is_dir():
                    candidates.update(path.resolve() for path in directory.glob("*.unitypackage"))
    return sorted(candidates)


def discover_siblings(root_path: Path, *, max_depth: int = 32, selected_asset_paths: set[str] | None = None) -> SiblingDiscoveryResult:
    del max_depth
    root_path = Path(root_path).resolve()
    accounting: dict[str, int] = {}
    root_manifest = _manifest(root_path, accounting)
    selected = {str(path).replace("\\", "/") for path in (selected_asset_paths or set())}
    relevant = [entry for entry in root_manifest if not selected or entry.asset_path in selected or entry.extension == ".fbx"]
    required = _visual_requirements(root_path, relevant, accounting)
    if not required:
        return SiblingDiscoveryResult(str(root_path), [], set(), set(), [], "NONE", "NONE", manifest_entries=len(root_manifest), accounting=accounting)
    sibling_paths = _candidate_paths(root_path, required)

    manifests: dict[Path, list[PackageManifestEntry]] = {}
    provided: dict[Path, set[str]] = {}
    unresolved = set(required)
    selected_paths = {root_path}
    candidates: list[SiblingPackageCandidate] = []
    ambiguous: set[str] = set()
    expanded = False
    changed = True
    while changed and unresolved:
        changed = False
        providers: dict[str, list[Path]] = {}
        for path in sibling_paths:
            if path in selected_paths:
                continue
            manifests[path] = manifests.get(path) or _manifest(path, accounting)
            provided[path] = {entry.guid for entry in manifests[path]}
            for guid in unresolved & provided[path]:
                providers.setdefault(guid, []).append(path)
        ambiguous_now = {guid for guid, paths in providers.items() if len(paths) > 1}
        ambiguous |= ambiguous_now
        for path in sibling_paths:
            if path in selected_paths:
                continue
            matched = (unresolved & provided.get(path, set())) - ambiguous_now
            if not matched:
                continue
            candidate = SiblingPackageCandidate(str(path), PackageIdentity.from_path(path).source_package_id, provided[path])
            candidate.matched_guids = matched
            candidate.match_count = len(matched)
            candidate.coverage_ratio = candidate.match_count / len(unresolved) if unresolved else 0.0
            candidates.append(candidate)
            selected_paths.add(path)
            unresolved -= provided[path]
            unresolved |= _visual_requirements(path, manifests[path], accounting) - provided[path]
            changed = True
            break
        if not changed and unresolved and not expanded:
            extra_paths = _candidate_paths(root_path, unresolved, include_adjacent=True)
            new_paths = [path for path in extra_paths if path not in sibling_paths]
            if new_paths:
                sibling_paths.extend(new_paths)
                expanded = True
                changed = True
    visual_ambiguous = ambiguous & required
    visual_unresolved = unresolved | visual_ambiguous
    visual_status = "AMBIGUOUS" if visual_ambiguous else "COMPLETE" if not visual_unresolved else "PARTIAL" if candidates else "NONE"
    edges = [{"from": str(root_path), "to": candidate.path, "reason": "GUID_MATCH"} for candidate in candidates]
    return SiblingDiscoveryResult(str(root_path), candidates, visual_unresolved, visual_ambiguous, edges, visual_status, visual_status, visual_unresolved, visual_ambiguous, set(), len(root_manifest) + sum(len(items) for items in manifests.values()), accounting)


def required_guids(package_path: Path, records: list[tuple[str, str, bytes]] | None = None) -> set[str]:
    del package_path
    return {guid for _guid, path, payload in records or [] for guid in _visual_guids_from_text(Path(path).suffix.casefold(), payload)}


def provided_guids(package_path: Path, records: list[tuple[str, str, bytes]] | None = None) -> set[str]:
    if records is not None:
        return {guid.lower() for guid, _path, _payload in records}
    return {entry.guid for entry in _manifest(Path(package_path))}
