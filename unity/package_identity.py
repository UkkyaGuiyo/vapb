"""Stable identity for safely reusing one selected UnityPackage."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .identity import package_id_from_sha256


@dataclass(frozen=True)
class PackageIdentity:
    path: str
    size: int
    mtime_ns: int
    sha256: str

    @property
    def source_package_id(self) -> str:
        return package_id_from_sha256(self.sha256)

    @property
    def package_name(self) -> str:
        return Path(self.path).name

    @classmethod
    def from_path(cls, path: Path) -> "PackageIdentity":
        resolved = Path(path).resolve()
        stat = resolved.stat()
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return cls(str(resolved), int(stat.st_size), int(stat.st_mtime_ns), digest.hexdigest())
