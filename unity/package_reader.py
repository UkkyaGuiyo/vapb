"""Safe reader/extractor for Unity's tar.gz based .unitypackage format."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from time import perf_counter
from typing import Callable, Dict, Optional

from ..blender.performance import diagnostic_add


class UnityPackageError(Exception):
    """Raised when a package cannot be safely interpreted."""


@dataclass(frozen=True)
class PackageAsset:
    guid: str
    unity_path: str
    extracted_path: Path
    meta_path: Optional[Path]


@dataclass(frozen=True)
class PackageRecord:
    guid: str
    unity_path: str
    has_asset: bool
    has_meta: bool
    asset_size: int
    meta_size: int
    meta_bytes: Optional[bytes] = None


@dataclass(frozen=True)
class PackageIndex:
    records: dict[str, PackageRecord]


@dataclass
class ExtractionResult:
    root: Path
    assets: list[PackageAsset]
    errors: list[str]


_GUID_RE = re.compile(r"^[0-9a-fA-F]{8,64}$")
_STREAM_CHUNK_SIZE = 4 * 1024 * 1024
_SMALL_ENTRY_CACHE_LIMIT = 4 * 1024 * 1024


@dataclass
class _SequentialAssetState:
    guid: str
    entries: Dict[str, tarfile.TarInfo]
    pathname: Optional[str] = None
    target: Optional[Path] = None
    asset_spool: Optional[Path] = None
    meta_bytes: Optional[bytes] = None
    meta_spool: Optional[Path] = None
    error: Optional[str] = None


def _decode_path(raw: bytes) -> str:
    return raw.decode("utf-8-sig", errors="strict").strip("\x00\r\n ")


def safe_relative_path(base: Path, relative: str) -> Path:
    """Return a path below *base*, rejecting absolute and traversal paths."""
    value = relative.replace("\\", "/").strip()
    if not value or "\x00" in value:
        raise UnityPackageError(f"Invalid empty/NUL pathname: {relative!r}")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise UnityPackageError(f"Absolute pathname is not allowed: {relative!r}")
    parts = PurePosixPath(value).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise UnityPackageError(f"Unsafe pathname: {relative!r}")
    base_resolved = base.resolve()
    candidate = (base_resolved.joinpath(*parts)).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise UnityPackageError(f"Path escapes extraction directory: {relative!r}") from exc
    return candidate


class UnityPackageReader:
    """Inspect and extract records without tarfile.extractall."""

    def __init__(self, package_path: Path):
        self.package_path = Path(package_path)
        self.last_timings: dict[str, float] = {}

    def _groups(self) -> Dict[str, Dict[str, tarfile.TarInfo]]:
        if not self.package_path.is_file():
            raise UnityPackageError(f"Package does not exist: {self.package_path}")
        groups: Dict[str, Dict[str, tarfile.TarInfo]] = {}
        self.last_timings = {}
        open_started = perf_counter()
        try:
            archive = tarfile.open(self.package_path, mode="r:*")
        except (tarfile.TarError, OSError) as exc:
            raise UnityPackageError(f"Cannot open UnityPackage: {exc}") from exc
        self.last_timings["package_open"] = perf_counter() - open_started
        scan_started = perf_counter()
        with archive:
            for member in archive.getmembers():
                member_parts = PurePosixPath(member.name.replace("\\", "/")).parts
                if len(member_parts) != 2 or member_parts[0] in ("", ".", ".."):
                    continue
                guid, entry = member_parts
                if not _GUID_RE.match(guid) or entry not in {"asset", "asset.meta", "pathname"}:
                    continue
                if member.isfile():
                    groups.setdefault(guid, {})[entry] = member
        self.last_timings["archive_scan"] = perf_counter() - scan_started
        return groups

    def inspect(self) -> list[tuple[str, str, bool, bool]]:
        records = []
        groups = self._groups()
        with tarfile.open(self.package_path, mode="r:*") as archive:
            for guid, entries in sorted(groups.items()):
                pathname_member = entries.get("pathname")
                if not pathname_member:
                    continue
                path_file = archive.extractfile(pathname_member)
                if path_file is None:
                    continue
                try:
                    unity_path = _decode_path(path_file.read())
                except UnicodeDecodeError:
                    continue
                records.append((guid, unity_path, "asset" in entries, "asset.meta" in entries))
        return records

    def build_index(self) -> PackageIndex:
        """Scan archive order once and cache only small dependency metadata."""
        if not self.package_path.is_file():
            raise UnityPackageError(f"Package does not exist: {self.package_path}")
        diagnostic_add("package_index_builds")
        mutable: dict[str, dict[str, object]] = {}
        self.last_timings = {}
        open_started = perf_counter()
        try:
            archive = tarfile.open(self.package_path, mode="r:*")
        except (tarfile.TarError, OSError) as exc:
            raise UnityPackageError(f"Cannot open UnityPackage: {exc}") from exc
        self.last_timings["package_open"] = perf_counter() - open_started
        scan_started = perf_counter()
        with archive:
            for member in archive:
                diagnostic_add("archive_members_seen")
                parts = PurePosixPath(member.name.replace("\\", "/")).parts
                if len(parts) != 2:
                    continue
                guid, entry = parts
                if not _GUID_RE.match(guid) or entry not in {"asset", "asset.meta", "pathname"}:
                    continue
                if not member.isfile():
                    continue
                record = mutable.setdefault(
                    guid.lower(),
                    {
                        "guid": guid.lower(),
                        "unity_path": "",
                        "has_asset": False,
                        "has_meta": False,
                        "asset_size": 0,
                        "meta_size": 0,
                        "meta_bytes": None,
                    },
                )
                if entry == "asset":
                    record["has_asset"] = True
                    record["asset_size"] = int(member.size)
                elif entry == "asset.meta":
                    record["has_meta"] = True
                    record["meta_size"] = int(member.size)
                    if member.size <= _SMALL_ENTRY_CACHE_LIMIT:
                        try:
                            record["meta_bytes"] = self._read_small_member(archive, member)
                        except (OSError, UnityPackageError):
                            record["meta_bytes"] = None
                else:
                    try:
                        record["unity_path"] = _decode_path(self._read_small_member(archive, member))
                    except (OSError, UnicodeError, UnityPackageError):
                        record["unity_path"] = ""
        self.last_timings["archive_scan"] = perf_counter() - scan_started
        records = {
            guid: PackageRecord(
                guid=guid,
                unity_path=str(values["unity_path"]),
                has_asset=bool(values["has_asset"]),
                has_meta=bool(values["has_meta"]),
                asset_size=int(values["asset_size"]),
                meta_size=int(values["meta_size"]),
                meta_bytes=values["meta_bytes"] if isinstance(values["meta_bytes"], bytes) else None,
            )
            for guid, values in mutable.items()
            if values["unity_path"]
        }
        return PackageIndex(records)

    @staticmethod
    def _copy_member_stream(archive: tarfile.TarFile, member: tarfile.TarInfo, target: Path) -> None:
        source = archive.extractfile(member)
        if source is None:
            raise UnityPackageError("cannot read archive entry")
        target.parent.mkdir(parents=True, exist_ok=True)
        with source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=_STREAM_CHUNK_SIZE)

    @staticmethod
    def _read_small_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
        source = archive.extractfile(member)
        if source is None:
            raise UnityPackageError("cannot read archive entry")
        with source:
            data = source.read(_SMALL_ENTRY_CACHE_LIMIT + 1)
        if len(data) > _SMALL_ENTRY_CACHE_LIMIT:
            raise UnityPackageError("small archive entry exceeds cache limit")
        return data

    def _extract_sequential(
        self,
        output_dir: Path,
        groups: Dict[str, Dict[str, tarfile.TarInfo]],
        cancel_check: Callable[[], bool] | None,
    ) -> tuple[list[PackageAsset], list[str]]:
        states = {guid: _SequentialAssetState(guid, entries) for guid, entries in groups.items()}
        errors: list[str] = []
        assets: list[PackageAsset] = []
        spool_root = Path(tempfile.mkdtemp(prefix=".unitypackage_spool_", dir=output_dir))
        sequential_started = perf_counter()
        try:
            open_started = perf_counter()
            with tarfile.open(self.package_path, mode="r:*") as archive:
                self.last_timings["package_open"] += perf_counter() - open_started
                for member in archive:
                    if cancel_check is not None and cancel_check():
                        raise UnityPackageError("Import cancelled")
                    parts = PurePosixPath(member.name.replace("\\", "/")).parts
                    if len(parts) != 2:
                        continue
                    guid, entry = parts
                    state = states.get(guid)
                    if state is None or entry not in {"asset", "asset.meta", "pathname"} or not member.isfile():
                        continue
                    try:
                        if entry == "pathname":
                            unity_path = _decode_path(self._read_small_member(archive, member))
                            state.pathname = unity_path
                            state.target = safe_relative_path(output_dir, unity_path)
                        elif entry == "asset":
                            diagnostic_add("extracted_asset_members")
                            diagnostic_add("extracted_payload_bytes", int(member.size))
                            state.asset_spool = spool_root / f"{guid}.asset"
                            self._copy_member_stream(archive, member, state.asset_spool)
                        else:
                            diagnostic_add("extracted_meta_members")
                            diagnostic_add("extracted_meta_bytes", int(member.size))
                            if member.size <= _SMALL_ENTRY_CACHE_LIMIT:
                                state.meta_bytes = self._read_small_member(archive, member)
                            else:
                                state.meta_spool = spool_root / f"{guid}.meta"
                                self._copy_member_stream(archive, member, state.meta_spool)
                    except (OSError, UnicodeError, UnityPackageError) as exc:
                        state.error = str(exc)
            self.last_timings["extract_sequential"] = self.last_timings.get("extract_sequential", 0.0) + perf_counter() - sequential_started

            for guid, state in sorted(states.items()):
                if state.pathname is None:
                    errors.append(f"{guid}: missing pathname")
                    continue
                if state.error is not None:
                    errors.append(f"{state.pathname}: extraction failed ({state.error})")
                    continue
                target = state.target
                if target is None:
                    errors.append(f"{guid}: invalid pathname")
                    continue
                try:
                    meta_probe = state.meta_bytes
                    if meta_probe is None and state.meta_spool is not None and state.meta_spool.exists() and state.meta_spool.stat().st_size <= 4096:
                        meta_probe = state.meta_spool.read_bytes()
                    is_folder_asset = bool(meta_probe and re.search(rb"(?m)^folderAsset:\s*(?:yes|true|1)\s*$", meta_probe, re.IGNORECASE))
                    if state.asset_spool is not None:
                        if is_folder_asset or (state.pathname.endswith("/") and state.asset_spool.stat().st_size == 0):
                            state.asset_spool.unlink(missing_ok=True)
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            os.replace(state.asset_spool, target)
                    elif is_folder_asset:
                        target.mkdir(parents=True, exist_ok=True)
                    meta_target: Optional[Path] = None
                    if state.meta_bytes is not None or state.meta_spool is not None:
                        meta_target = safe_relative_path(output_dir, state.pathname + ".meta")
                        meta_target.parent.mkdir(parents=True, exist_ok=True)
                        if state.meta_bytes is not None:
                            meta_target.write_bytes(state.meta_bytes)
                        else:
                            os.replace(state.meta_spool, meta_target)
                    assets.append(PackageAsset(guid, state.pathname, target, meta_target))
                except (OSError, UnityPackageError) as exc:
                    errors.append(f"{state.pathname}: extraction failed ({exc})")
        finally:
            shutil.rmtree(spool_root, ignore_errors=True)
        return assets, errors

    def extract(self, output_dir: Path, cancel_check: Callable[[], bool] | None = None) -> ExtractionResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        groups = self._groups()
        extract_started = perf_counter()
        assets, errors = self._extract_sequential(output_dir, groups, cancel_check)
        self.last_timings["extract"] = self.last_timings.get("extract", 0.0) + perf_counter() - extract_started
        return ExtractionResult(output_dir, assets, errors)

    def extract_selective(
        self,
        output_dir: Path,
        index: PackageIndex,
        wanted_guids: set[str],
        cancel_check: Callable[[], bool] | None = None,
    ) -> ExtractionResult:
        """Stream only selected records while preserving archive physical order."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        selected = {
            str(guid).lower()
            for guid in wanted_guids
            if str(guid).lower() in index.records
        }
        extract_started = perf_counter()
        assets, errors = self._extract_sequential(
            output_dir,
            {guid: {} for guid in selected},
            cancel_check,
        )
        self.last_timings["extract"] = self.last_timings.get("extract", 0.0) + perf_counter() - extract_started
        return ExtractionResult(output_dir, assets, errors)


def is_unitypackage(path: Path) -> bool:
    return Path(path).suffix.lower() == ".unitypackage"
