"""Raw source UnityPackage byte access for PRESERVE_VERBATIM assets."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path, PurePosixPath
import re
import tarfile

from .staging import normalize_guid, normalize_unity_path


@dataclass(frozen=True)
class RawAsset:
    guid: str
    pathname: str
    asset_bytes: bytes
    meta_bytes: bytes
    preview_bytes: bytes | None = None


class RawAssetRepository:
    def __init__(self, package_path: Path):
        self.package_path = Path(package_path)

    def read(self, guid: str) -> RawAsset:
        wanted = normalize_guid(guid)
        for asset in self.read_all():
            if asset.guid == wanted:
                return asset
        raise ValueError(f"source asset is missing: {guid}")

    def read_all(self, archive_bytes: bytes | None = None) -> tuple[RawAsset, ...]:
        """Read a complete archive without extracting paths to the filesystem."""
        groups: dict[str, dict[str, bytes]] = {}
        archive_source = {"fileobj": io.BytesIO(archive_bytes)} if archive_bytes is not None else {"name": self.package_path}
        with tarfile.open(mode="r:*", **archive_source) as archive:
            for member in archive.getmembers():
                parts = PurePosixPath(member.name.replace("\\", "/")).parts
                if member.isdir() and len(parts) == 1 and re.fullmatch(r"[0-9a-fA-F]{32}", parts[0]):
                    continue
                if len(parts) != 2 or parts[1] not in {"asset", "asset.meta", "pathname", "preview.png"}:
                    raise ValueError("unsupported UnityPackage tar entry")
                guid = normalize_guid(parts[0])
                if not member.isfile():
                    raise ValueError("UnityPackage payload is not a regular file")
                payloads = groups.setdefault(guid, {})
                if parts[1] in payloads:
                    raise ValueError("duplicate UnityPackage tar field")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("missing UnityPackage payload")
                payloads[parts[1]] = stream.read()
        result = []
        for guid, payloads in sorted(groups.items()):
            if "asset.meta" not in payloads or "pathname" not in payloads:
                raise ValueError(f"source asset is incomplete: {guid}")
            meta = payloads["asset.meta"]
            folder = bool(re.search(rb"(?m)^folderAsset:\s*yes\s*$", meta))
            if "asset" not in payloads and not folder:
                raise ValueError(f"source asset is incomplete: {guid}")
            if folder and "asset" in payloads:
                raise ValueError(f"folder asset unexpectedly has payload: {guid}")
            pathname = normalize_unity_path(payloads["pathname"].decode("utf-8-sig").strip())
            result.append(RawAsset(guid, pathname, payloads.get("asset", b""), meta, payloads.get("preview.png")))
        if not result:
            raise ValueError("source package has no assets")
        return tuple(result)
