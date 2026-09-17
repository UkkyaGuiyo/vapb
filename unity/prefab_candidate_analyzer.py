"""Metadata-first Prefab candidate analysis and deterministic selection.

The analyzer deliberately stops at Unity metadata and textual material data.  It
does not read FBX or texture payloads, and it caches every package index and
textual material read for the lifetime of one analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tarfile
import tempfile
from typing import Iterable

from .asset_database import AssetDatabase
from .material_mapping import parse_external_objects
from .package_reader import PackageIndex, PackageRecord, UnityPackageReader
from .prefab_parser import MESH_RENDERER, SKINNED_MESH_RENDERER, PrefabData, parse_prefab


_TEXTURE_RE = re.compile(r"m_Texture:\s*\{[^}]*?guid:\s*([0-9a-fA-F]{8,64})")
_VISUAL_EXTENSIONS = {".fbx", ".mat", ".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"}


@dataclass(frozen=True)
class PackageSource:
    path: Path
    index: PackageIndex
    primary: bool = False


@dataclass
class PrefabCandidateAnalysis:
    token: str
    prefab_path: Path
    unity_path: str
    guid: str
    display_name: str
    candidate_kind: str
    visual_status: str
    renderer_count: int
    skinned_renderer_count: int
    mesh_renderer_count: int
    game_object_count: int
    transform_count: int
    material_slot_count: int
    referenced_fbx_guids: set[str] = field(default_factory=set)
    referenced_material_guids: set[str] = field(default_factory=set)
    required_visual_guids: set[str] = field(default_factory=set)
    resolved_visual_guids: set[str] = field(default_factory=set)
    unresolved_visual_guids: set[str] = field(default_factory=set)
    ambiguous_visual_guids: set[str] = field(default_factory=set)
    provider_packages: set[Path] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PrefabSelection:
    mode: str
    token: str | None
    reason: str


class PackageArchiveCache:
    """Index and textual payload cache shared by all candidate analyses."""

    def __init__(self, primary_path: Path, primary_index: PackageIndex):
        self.primary_path = Path(primary_path).resolve()
        self._sources: dict[Path, PackageSource] = {
            self.primary_path: PackageSource(self.primary_path, primary_index, True)
        }
        self.index_build_counts: dict[Path, int] = {self.primary_path: 0}
        self.asset_read_counts: dict[tuple[Path, str], int] = {}
        self._text_cache: dict[tuple[Path, str], bytes] = {}

    def source(self, path: Path) -> PackageSource:
        path = Path(path).resolve()
        source = self._sources.get(path)
        if source is None:
            reader = UnityPackageReader(path)
            index = reader.build_index()
            self.index_build_counts[path] = self.index_build_counts.get(path, 0) + 1
            source = PackageSource(path, index, False)
            self._sources[path] = source
        return source

    @property
    def sources(self) -> tuple[PackageSource, ...]:
        return tuple(self._sources.values())

    def read_asset(self, source: PackageSource, guid: str) -> bytes:
        key = (source.path, str(guid).lower())
        if key in self._text_cache:
            return self._text_cache[key]
        record = source.index.records.get(key[1])
        if record is None or not record.has_asset:
            return b""
        with tarfile.open(source.path, "r:*") as archive:
            member = archive.getmember(f"{record.guid}/asset")
            handle = archive.extractfile(member)
            payload = handle.read() if handle is not None else b""
        self._text_cache[key] = payload
        self.asset_read_counts[key] = self.asset_read_counts.get(key, 0) + 1
        return payload


class PrefabCandidateAnalyzer:
    """Analyze all Prefabs in one prepared package with one shared cache."""

    def __init__(
        self,
        package_path: Path,
        package_index: PackageIndex,
        extraction_root: Path,
        prefab_paths: Iterable[Path],
        asset_db: AssetDatabase | None = None,
        extra_package_paths: Iterable[Path] = (),
    ):
        self.package_path = Path(package_path).resolve()
        self.extraction_root = Path(extraction_root)
        self.asset_db = asset_db
        self.cache = PackageArchiveCache(self.package_path, package_index)
        self.extra_package_paths = {Path(path).resolve() for path in extra_package_paths}
        self.prefab_paths = list(prefab_paths)

    def _candidate_package_paths(self) -> list[Path]:
        """Return the bounded sibling neighborhood without reading archives."""
        parent = self.package_path.parent
        candidates = {path.resolve() for path in parent.glob("*.unitypackage")}
        bundle_root = parent.parent
        # A synthetic fixture is commonly placed directly below the OS temp
        # directory.  Expanding every temp child would create false provider
        # ambiguity from unrelated test archives; real bundle expansion starts
        # one level below a named bundle directory.
        if bundle_root.is_dir() and bundle_root != Path(tempfile.gettempdir()).resolve():
            candidates.update(path.resolve() for path in bundle_root.glob("*.unitypackage"))
            for directory in bundle_root.iterdir():
                if directory.is_dir():
                    candidates.update(path.resolve() for path in directory.glob("*.unitypackage"))
        candidates.update(self.extra_package_paths)
        candidates.discard(self.package_path)
        return sorted(path for path in candidates if path.is_file())

    def _load_external_sources(self) -> None:
        for path in self._candidate_package_paths():
            self.cache.source(path)

    def _primary_record(self, path: Path) -> tuple[str, PackageRecord | None]:
        source = self.cache.source(self.package_path)
        unity_path = ""
        if self.asset_db is not None:
            entry = self.asset_db.find_path(self._unity_path(path))
            if entry is not None:
                return entry.guid.lower(), source.index.records.get(entry.guid.lower())
        for guid, record in source.index.records.items():
            if record.unity_path.replace("\\", "/") == self._unity_path(path):
                unity_path = record.unity_path
                return guid.lower(), source.index.records.get(guid)
        return "", source.index.records.get(unity_path)

    def _unity_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.extraction_root.resolve()).as_posix()
        except (OSError, ValueError):
            return str(path).replace("\\", "/")

    @staticmethod
    def _prefab_refs(prefab: PrefabData) -> tuple[set[str], set[str], int]:
        fbx: set[str] = set()
        materials: set[str] = set()
        slots = 0
        for document in prefab.renderer_documents():
            mesh = document.data.get("m_Mesh")
            if isinstance(mesh, dict) and mesh.get("guid"):
                fbx.add(str(mesh["guid"]).lower())
            values = document.data.get("m_Materials")
            if not isinstance(values, list):
                values = [document.data.get("m_Material")]
            for value in values:
                if isinstance(value, dict) and value.get("guid"):
                    materials.add(str(value["guid"]).lower())
                slots += 1
        return fbx, materials, slots

    @staticmethod
    def _kind(prefab: PrefabData, renderer_count: int, skinned_count: int) -> str:
        if renderer_count == 0:
            return "EMPTY_OR_UNSUPPORTED"
        if skinned_count > 0 and (
            renderer_count >= 2 or len(prefab.game_objects) >= 2 or len(prefab.transforms) >= 2
        ):
            return "AVATAR_LIKE"
        if renderer_count <= 2 and len(prefab.game_objects) <= 8:
            return "PROP_LIKE"
        if renderer_count >= 2 and len(prefab.transforms) >= 2:
            return "AVATAR_LIKE"
        return "UNKNOWN"

    def _providers(self, guid: str) -> list[PackageSource]:
        return [source for source in self.cache.sources if guid.lower() in source.index.records]

    def _record(self, source: PackageSource, guid: str) -> PackageRecord | None:
        return source.index.records.get(guid.lower())

    def _material_texture_guids(self, source: PackageSource, guid: str) -> set[str]:
        record = self._record(source, guid)
        if record is None or Path(record.unity_path).suffix.lower() != ".mat":
            return set()
        payload = self.cache.read_asset(source, guid)
        return {value.lower() for value in _TEXTURE_RE.findall(payload.decode("utf-8", "replace"))}

    def _fbx_external_guids(self, source: PackageSource, guid: str) -> set[str]:
        record = self._record(source, guid)
        if record is None or Path(record.unity_path).suffix.lower() != ".fbx" or not record.meta_bytes:
            return set()
        return {value.lower() for value in parse_external_objects(record.meta_bytes.decode("utf-8", "replace")).values()}

    def _closure(self, direct: set[str]) -> tuple[set[str], set[str], set[str], set[str], set[Path]]:
        required: set[str] = set()
        resolved: set[str] = set()
        unresolved: set[str] = set()
        ambiguous: set[str] = set()
        providers: set[Path] = set()
        queue = list(sorted(guid.lower() for guid in direct if guid))
        visited: set[str] = set()
        while queue:
            guid = queue.pop(0)
            if guid in visited:
                continue
            visited.add(guid)
            required.add(guid)
            matches = self._providers(guid)
            if not matches:
                unresolved.add(guid)
                continue
            if len(matches) > 1:
                ambiguous.add(guid)
                continue
            source = matches[0]
            if not source.primary:
                providers.add(source.path)
            resolved.add(guid)
            record = self._record(source, guid)
            if record is None:
                continue
            suffix = Path(record.unity_path).suffix.lower()
            if suffix == ".mat":
                queue.extend(sorted(self._material_texture_guids(source, guid) - visited))
            elif suffix == ".fbx":
                queue.extend(sorted(self._fbx_external_guids(source, guid) - visited))
        return required, resolved, unresolved, ambiguous, providers

    def analyze(self) -> list[PrefabCandidateAnalysis]:
        def analyze_once() -> list[PrefabCandidateAnalysis]:
            result: list[PrefabCandidateAnalysis] = []
            for index, path in enumerate(self.prefab_paths):
                prefab = parse_prefab(path)
                renderers = prefab.renderer_documents()
                skinned = sum(document.class_id == SKINNED_MESH_RENDERER for document in renderers)
                mesh_renderers = sum(document.class_id == MESH_RENDERER for document in renderers)
                fbx, materials, slots = self._prefab_refs(prefab)
                required, resolved, unresolved, ambiguous, providers = self._closure(fbx | materials)
                if ambiguous:
                    status = "AMBIGUOUS"
                elif unresolved:
                    status = "PARTIAL"
                elif required:
                    status = "COMPLETE"
                else:
                    status = "NONE"
                kind = self._kind(prefab, len(renderers), skinned)
                reasons = [f"{kind}", f"{status}"]
                if not renderers:
                    reasons.append("NO_RENDERERS")
                if ambiguous:
                    reasons.append("AMBIGUOUS_PROVIDER")
                if unresolved:
                    reasons.append("UNRESOLVED_VISUAL_DEPENDENCY")
                guid, record = self._primary_record(path)
                result.append(PrefabCandidateAnalysis(
                    token=f"PREFAB_{index}",
                    prefab_path=path,
                    unity_path=record.unity_path if record else self._unity_path(path),
                    guid=guid,
                    display_name=prefab.display_name,
                    candidate_kind=kind,
                    visual_status=status,
                    renderer_count=len(renderers),
                    skinned_renderer_count=skinned,
                    mesh_renderer_count=mesh_renderers,
                    game_object_count=len(prefab.game_objects),
                    transform_count=len(prefab.transforms),
                    material_slot_count=slots,
                    referenced_fbx_guids=fbx,
                    referenced_material_guids=materials,
                    required_visual_guids=required,
                    resolved_visual_guids=resolved,
                    unresolved_visual_guids=unresolved,
                    ambiguous_visual_guids=ambiguous,
                    provider_packages=providers,
                    reasons=reasons,
                ))
            return result

        result = analyze_once()
        if any(item.unresolved_visual_guids for item in result):
            self._load_external_sources()
            result = analyze_once()
        return result

    @staticmethod
    def select(analyses: Iterable[PrefabCandidateAnalysis]) -> PrefabSelection:
        items = list(analyses)
        supported = [item for item in items if item.renderer_count > 0]
        if len(supported) == 1 and supported[0].visual_status != "AMBIGUOUS":
            return PrefabSelection("AUTO_SELECTED", supported[0].token, "ONLY_SUPPORTED_PREFAB")
        if len(supported) == 1 and supported[0].visual_status == "AMBIGUOUS":
            return PrefabSelection("USER_CHOICE_REQUIRED", None, "AMBIGUOUS_PROVIDER")
        complete_avatars = [item for item in supported if item.candidate_kind == "AVATAR_LIKE" and item.visual_status == "COMPLETE"]
        if len(complete_avatars) == 1:
            return PrefabSelection("AUTO_SELECTED", complete_avatars[0].token, "ONLY_COMPLETE_AVATAR_CANDIDATE")
        if len(complete_avatars) > 1:
            return PrefabSelection("USER_CHOICE_REQUIRED", None, "MULTIPLE_COMPLETE_AVATAR_CANDIDATES")
        if len(supported) > 1:
            return PrefabSelection("USER_CHOICE_REQUIRED", None, "NO_UNIQUE_COMPLETE_AVATAR_CANDIDATE")
        return PrefabSelection("NO_SUPPORTED_PREFAB", None, "NO_SUPPORTED_PREFAB")


__all__ = [
    "PackageArchiveCache",
    "PrefabCandidateAnalysis",
    "PrefabCandidateAnalyzer",
    "PrefabSelection",
]
