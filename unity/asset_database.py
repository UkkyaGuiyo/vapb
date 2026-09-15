"""A small GUID/path index for an extracted Unity project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Optional

from .package_reader import PackageAsset, PackageIndex


@dataclass(frozen=True)
class AssetEntry:
    guid: str
    unity_path: str
    path: Path
    source_package_id: str = "LEGACY_UNSCOPED"

_GUID_LINE_RE = re.compile(r"^\s*guid:\s*([0-9a-fA-F]+)\s*$", re.MULTILINE)


class AssetDatabase:
    def __init__(self, root: Path, entries: Iterable[AssetEntry] = (), source_package_id: str = "LEGACY_UNSCOPED"):
        self.root = Path(root)
        self.source_package_id = source_package_id
        self.by_guid: dict[str, AssetEntry] = {}
        self.by_unity_path: dict[str, AssetEntry] = {}
        self._files_by_extension: dict[str, set[Path]] = {}
        for entry in entries:
            self.add(entry)

    @classmethod
    def from_extraction(
        cls,
        root: Path,
        assets: Iterable[PackageAsset],
        source_package_id: str = "LEGACY_UNSCOPED",
    ) -> "AssetDatabase":
        db = cls(root, source_package_id=source_package_id)
        for asset in assets:
            db.add(AssetEntry(asset.guid, asset.unity_path, asset.extracted_path, db.source_package_id))
        return db

    @classmethod
    def from_package_index(
        cls,
        root: Path,
        index: PackageIndex,
        assets: Iterable[PackageAsset] = (),
        source_package_id: str = "LEGACY_UNSCOPED",
    ) -> "AssetDatabase":
        """Index all package GUIDs, including records not yet extracted."""
        db = cls(root, source_package_id=source_package_id)
        extracted_by_guid = {asset.guid.lower(): asset for asset in assets}
        for guid, record in index.records.items():
            asset = extracted_by_guid.get(guid.lower())
            path = asset.extracted_path if asset is not None else Path(root) / record.unity_path
            db.add(AssetEntry(guid, record.unity_path, path, db.source_package_id))
        return db

    def add(self, entry: AssetEntry) -> None:
        self.by_guid[entry.guid.lower()] = entry
        self.by_unity_path[entry.unity_path.replace("\\", "/")] = entry
        if entry.path.is_file() and not entry.path.name.endswith(".meta"):
            self._files_by_extension.setdefault(entry.path.suffix.lower(), set()).add(entry.path)

    def scan_missing_meta(self) -> None:
        for meta in self.root.rglob("*.meta"):
            try:
                match = _GUID_LINE_RE.search(meta.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            if not match:
                continue
            asset_path = meta.with_name(meta.name[:-5])
            if not asset_path.exists():
                continue
            rel = asset_path.relative_to(self.root).as_posix()
            self.add(AssetEntry(match.group(1), rel, asset_path, self.source_package_id))

    def find_guid(self, guid: Optional[str]) -> Optional[AssetEntry]:
        return self.by_guid.get(str(guid).lower()) if guid else None

    def find_path(self, unity_path: str) -> Optional[AssetEntry]:
        return self.by_unity_path.get(unity_path.replace("\\", "/"))

    def guid_for_path(self, path: Path) -> str:
        """Return the indexed Unity GUID for an extracted filesystem path."""
        try:
            unity_path = Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except (OSError, ValueError):
            unity_path = str(path).replace("\\", "/")
        entry = self.find_path(unity_path)
        return entry.guid if entry else ""

    def files_with_extensions(self, extensions: Iterable[str]) -> list[Path]:
        allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
        paths: set[Path] = set()
        for extension in allowed:
            paths.update(self._files_by_extension.get(extension, set()))
        return sorted(paths)

    def fbxs(self) -> list[Path]:
        return self.files_with_extensions({".fbx"})

    def prefabs(self) -> list[Path]:
        return self.files_with_extensions({".prefab"})

    def textures(self) -> list[Path]:
        return self.files_with_extensions({".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".exr", ".psd"})

    def materials(self) -> list[Path]:
        return self.files_with_extensions({".mat"})
