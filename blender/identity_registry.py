"""Blender Scene persistence for the package-scoped identity registry."""

from __future__ import annotations

from typing import Any, Iterable

from ..unity.identity import AssetIdentity, SceneIdentityRegistry
from .performance import diagnostic_add


SCENE_IDENTITY_REGISTRY = "unitypackage_identity_registry"


def load_scene_registry(scene: Any) -> SceneIdentityRegistry:
    diagnostic_add("identity_registry_loads")
    try:
        payload = scene.get(SCENE_IDENTITY_REGISTRY, "")
    except AttributeError:
        payload = ""
    if not payload:
        return SceneIdentityRegistry()
    try:
        return SceneIdentityRegistry.from_json(str(payload))
    except (TypeError, ValueError, KeyError):
        return SceneIdentityRegistry()


def save_scene_registry(scene: Any, registry: SceneIdentityRegistry) -> None:
    diagnostic_add("identity_registry_writes")
    diagnostic_add("identity_registry_packages", len(registry.packages))
    diagnostic_add("identity_registry_assets", len(registry.assets))
    scene[SCENE_IDENTITY_REGISTRY] = registry.to_json()


def register_package(scene: Any, metadata: dict[str, Any]) -> tuple[SceneIdentityRegistry, str]:
    registry = load_scene_registry(scene)
    status = registry.register_package(metadata)
    save_scene_registry(scene, registry)
    return registry, status


def register_datablocks(
    scene: Any,
    datablocks: Iterable[Any],
    source_package_id: str,
    asset_type: str,
) -> SceneIdentityRegistry:
    registry = load_scene_registry(scene)
    diagnostic_add("identity_datablock_batches")
    items = list(datablocks)
    diagnostic_add("identity_datablocks_registered", len(items))
    for datablock in items:
        source_path = datablock.get("unity_source_prefab", datablock.get("unity_source_fbx", ""))
        identity = AssetIdentity(
            source_package_id,
            datablock.get("unity_guid", datablock.get("unity_material_guid", "")),
            datablock.get("unity_asset_path", datablock.get("unity_material_path", source_path)),
            datablock.get("unity_prefab_file_id") or None,
            asset_type=asset_type,
        )
        registry.register_asset(identity, asset_type=asset_type, display_name=getattr(datablock, "name", ""))
    save_scene_registry(scene, registry)
    return registry
