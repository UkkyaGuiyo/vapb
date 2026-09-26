"""Preserve an imported UnityPackage as an exact, content-addressed source."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile


_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


def _fingerprint(stat):
    # Windows reports st_ctime_ns as creation time, and fstat/path.stat can
    # briefly disagree about it even when the file contents are unchanged.
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_source(package_path: Path, expected_sha256: str) -> None:
    with package_path.open("rb") as source:
        before = _fingerprint(os.fstat(source.fileno()))
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
        after = _fingerprint(os.fstat(source.fileno()))
    if before != after or after != _fingerprint(package_path.stat()) or digest.hexdigest() != expected_sha256:
        raise ValueError("source UnityPackage changed or does not match expected SHA-256")


def _verify_existing(path: Path, expected_sha256: str) -> None:
    if path.is_symlink() or not path.is_file() or _hash_file(path) != expected_sha256:
        raise ValueError("stored UnityPackage does not match expected SHA-256")


def archive_source(package_path: Path, storage_root: Path, expected_sha256: str) -> Path:
    """Publish exact source bytes once; never overwrite a stored archive."""
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be a full SHA-256 hex digest")
    expected_sha256 = expected_sha256.lower()
    package_path = Path(package_path)
    storage_root = Path(storage_root)
    destination = storage_root / f"{expected_sha256}.unitypackage"

    if os.path.lexists(destination):
        _verify_source(package_path, expected_sha256)
        _verify_existing(destination, expected_sha256)
        return destination

    storage_root.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".vapb-source-", suffix=".tmp", dir=storage_root)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with package_path.open("rb") as source, temporary.open("wb") as target:
            before = _fingerprint(os.fstat(source.fileno()))
            shutil.copyfileobj(source, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
            after = _fingerprint(os.fstat(source.fileno()))
        if (before != after or after != _fingerprint(package_path.stat())
                or _hash_file(temporary) != expected_sha256):
            raise ValueError("source UnityPackage changed or does not match expected SHA-256")
        try:
            os.link(temporary, destination)
        except FileExistsError:
            _verify_existing(destination, expected_sha256)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
