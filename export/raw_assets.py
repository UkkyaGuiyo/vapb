"""Raw source UnityPackage byte access for PRESERVE_VERBATIM assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import tarfile

from .staging import normalize_guid, normalize_unity_path


@dataclass(frozen=True)
class RawAsset:
    guid: str
    pathname: str
    asset_bytes: bytes
    meta_bytes: bytes


class RawAssetRepository:
    def __init__(self, package_path: Path):
        self.package_path = Path(package_path)

    def read(self, guid: str) -> RawAsset:
        wanted = normalize_guid(guid)
        with tarfile.open(self.package_path, mode="r:*") as archive:
            payloads: dict[str, bytes] = {}
            for member in archive.getmembers():
                parts = PurePosixPath(member.name.replace("\\", "/")).parts
                if len(parts) != 2 or parts[0].lower() != wanted or parts[1] not in {"asset", "asset.meta", "pathname"} or not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"missing payload for {wanted}/{parts[1]}")
                payloads[parts[1]] = stream.read()
        if "asset" not in payloads or "asset.meta" not in payloads or "pathname" not in payloads:
            raise ValueError(f"source asset is incomplete: {wanted}")
        pathname = normalize_unity_path(payloads["pathname"].decode("utf-8-sig").strip())
        return RawAsset(wanted, pathname, payloads["asset"], payloads["asset.meta"])
