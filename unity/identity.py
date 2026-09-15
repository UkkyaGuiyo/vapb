"""Package-scoped Unity asset identity and scene-level collision indexing."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable


LEGACY_UNSCOPED = "LEGACY_UNSCOPED"
NO_COLLISION = "NO_COLLISION"
SAME_PACKAGE_SAME_ASSET = "SAME_PACKAGE_SAME_ASSET"
CROSS_PACKAGE_GUID_COLLISION = "CROSS_PACKAGE_GUID_COLLISION"
CROSS_PACKAGE_PATH_COLLISION = "CROSS_PACKAGE_PATH_COLLISION"
AMBIGUOUS_IDENTITY = "AMBIGUOUS_IDENTITY"
DUPLICATE_PACKAGE_IMPORT = "DUPLICATE_PACKAGE_IMPORT"


def _normalize_path(value: Any) -> str:
    return str(value or "").replace("\\", "/")


@dataclass(frozen=True)
class AssetIdentity:
    """Immutable canonical identity for one Unity asset or sub-asset."""

    source_package_id: str = LEGACY_UNSCOPED
    source_guid: str = ""
    source_asset_path: str = ""
    source_file_id: str | None = None
    source_object_path: str = ""
    asset_type: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_package_id", str(self.source_package_id or LEGACY_UNSCOPED))
        object.__setattr__(self, "source_guid", str(self.source_guid or "").lower())
        object.__setattr__(self, "source_asset_path", _normalize_path(self.source_asset_path))
        object.__setattr__(self, "source_object_path", _normalize_path(self.source_object_path))
        if self.source_file_id is not None and str(self.source_file_id) != "":
            object.__setattr__(self, "source_file_id", str(self.source_file_id))
        else:
            object.__setattr__(self, "source_file_id", None)

    @property
    def key(self) -> tuple[str, ...]:
        if self.source_guid:
            return (self.source_package_id, "guid", self.source_guid, "file_id", self.source_file_id or "")
        if self.source_asset_path:
            return (self.source_package_id, "path", self.source_asset_path, "file_id", self.source_file_id or "")
        return (self.source_package_id, "ambiguous", "file_id", self.source_file_id or "")

    @property
    def is_ambiguous(self) -> bool:
        return not self.source_guid and not self.source_asset_path

    @property
    def is_legacy(self) -> bool:
        return self.source_package_id == LEGACY_UNSCOPED

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_package_id": self.source_package_id,
            "source_guid": self.source_guid,
            "source_asset_path": self.source_asset_path,
            "source_file_id": self.source_file_id,
            "source_object_path": self.source_object_path,
            "asset_type": self.asset_type,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AssetIdentity":
        return cls(
            source_package_id=value.get("source_package_id", LEGACY_UNSCOPED),
            source_guid=value.get("source_guid", ""),
            source_asset_path=value.get("source_asset_path", ""),
            source_file_id=value.get("source_file_id"),
            source_object_path=value.get("source_object_path", ""),
            asset_type=value.get("asset_type", ""),
        )


def package_id_from_sha256(sha256: str) -> str:
    value = str(sha256 or "").lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("package SHA-256 must be exactly 64 hexadecimal characters")
    return f"sha256:{value}"


def get_asset_identity(datablock: Any, asset_type: str = "") -> AssetIdentity:
    """Read identity properties without guessing a package for legacy data."""
    def prop(*names: str) -> Any:
        for name in names:
            try:
                value = datablock.get(name)
            except AttributeError:
                value = None
            if value not in (None, ""):
                return value
        return ""

    return AssetIdentity(
        source_package_id=prop("unity_source_package_id") or LEGACY_UNSCOPED,
        source_guid=prop("unity_guid", "unity_material_guid", "unity_asset_guid"),
        source_asset_path=prop("unity_asset_path", "unity_material_path", "unity_source_prefab", "unity_source_fbx"),
        source_file_id=prop("unity_prefab_file_id") or None,
        source_object_path=prop("unity_object_path"),
        asset_type=asset_type,
    )


class SceneIdentityRegistry:
    """Small serializable registry for package metadata and canonical assets."""

    def __init__(self, packages: Iterable[dict[str, Any]] = (), assets: Iterable[dict[str, Any]] = ()):
        self.packages: dict[str, dict[str, Any]] = {}
        self.assets: dict[tuple[str, ...], dict[str, Any]] = {}
        self.ambiguous_assets: list[dict[str, Any]] = []
        for package in packages:
            self.packages[str(package["source_package_id"])] = dict(package)
        for asset in assets:
            identity = AssetIdentity.from_dict(asset["identity"])
            record = dict(asset)
            record["identity"] = identity.to_dict()
            if identity.is_ambiguous:
                self.ambiguous_assets.append(record)
            else:
                self.assets[identity.key] = record

    def register_package(self, metadata: dict[str, Any]) -> str:
        package_id = str(metadata["source_package_id"])
        if package_id in self.packages:
            return DUPLICATE_PACKAGE_IMPORT
        self.packages[package_id] = dict(metadata)
        return NO_COLLISION

    def register_asset(self, identity: AssetIdentity, *, asset_type: str = "", display_name: str = "") -> str:
        if identity.is_ambiguous:
            self.ambiguous_assets.append(
                {
                    "identity": identity.to_dict(),
                    "asset_type": asset_type or identity.asset_type,
                    "display_name": display_name,
                }
            )
            return AMBIGUOUS_IDENTITY
        existing = self.assets.get(identity.key)
        if existing is not None:
            return SAME_PACKAGE_SAME_ASSET
        self.assets[identity.key] = {
            "identity": identity.to_dict(),
            "asset_type": asset_type or identity.asset_type,
            "display_name": display_name,
        }
        return NO_COLLISION

    def lookup_by_identity(self, identity: AssetIdentity) -> list[dict[str, Any]]:
        record = self.assets.get(identity.key)
        return [record] if record is not None else []

    def find_by_guid(self, guid: str) -> list[dict[str, Any]]:
        normalized = str(guid or "").lower()
        return [record for record in self.assets.values() if record["identity"].get("source_guid", "").lower() == normalized]

    def find_by_asset_path(self, asset_path: str) -> list[dict[str, Any]]:
        normalized = _normalize_path(asset_path)
        return [record for record in self.assets.values() if record["identity"].get("source_asset_path", "") == normalized]

    def detect_collisions(self) -> list[dict[str, Any]]:
        records = list(self.assets.values())
        collisions: list[dict[str, Any]] = []
        for index, left in enumerate(records):
            left_identity = AssetIdentity.from_dict(left["identity"])
            for right in records[index + 1 :]:
                right_identity = AssetIdentity.from_dict(right["identity"])
                if left_identity.key == right_identity.key:
                    continue
                if left_identity.source_package_id != right_identity.source_package_id:
                    if left_identity.source_guid and left_identity.source_guid == right_identity.source_guid:
                        collisions.append({"status": CROSS_PACKAGE_GUID_COLLISION, "left": left["identity"], "right": right["identity"]})
                    if left_identity.source_asset_path and left_identity.source_asset_path == right_identity.source_asset_path:
                        collisions.append({"status": CROSS_PACKAGE_PATH_COLLISION, "left": left["identity"], "right": right["identity"]})
        return collisions

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "packages": list(self.packages.values()),
            "assets": list(self.assets.values()),
            "ambiguous_assets": list(self.ambiguous_assets),
            "collisions": self.detect_collisions(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "SceneIdentityRegistry":
        payload = json.loads(value)
        registry = cls(payload.get("packages", ()), payload.get("assets", ()))
        registry.ambiguous_assets.extend(payload.get("ambiguous_assets", ()))
        return registry
