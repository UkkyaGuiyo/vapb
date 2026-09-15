"""Persistent, package-scoped cross-package dependency capture and resolution."""

from __future__ import annotations

import json
from typing import Any, Iterable

import bpy  # type: ignore


SCENE_DEPENDENCY_REGISTRY = "unitypackage_dependency_registry"
UNRESOLVED = "UNRESOLVED"
RESOLVED_LOCAL = "RESOLVED_LOCAL"
RESOLVED_CROSS_PACKAGE = "RESOLVED_CROSS_PACKAGE"
AMBIGUOUS_PROVIDER = "AMBIGUOUS_PROVIDER"
MISSING_CONSUMER = "MISSING_CONSUMER"
UNSUPPORTED = "UNSUPPORTED"


def load_dependency_registry(scene: Any) -> dict[str, Any]:
    try:
        raw = scene.get(SCENE_DEPENDENCY_REGISTRY, "")
        return json.loads(str(raw)) if raw else {"schema_version": 1, "dependencies": []}
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        return {"schema_version": 1, "dependencies": []}


def save_dependency_registry(scene: Any, registry: dict[str, Any]) -> None:
    scene[SCENE_DEPENDENCY_REGISTRY] = json.dumps(registry, ensure_ascii=False, sort_keys=True)


def _record_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(record.get(key, "") for key in (
        "dependency_type", "consumer_package_id", "consumer_asset_path",
        "consumer_file_id", "consumer_game_object_file_id", "consumer_slot_index",
        "target_guid", "target_file_id",
    ))


def capture_dependency(scene: Any, record: dict[str, Any]) -> dict[str, Any]:
    registry = load_dependency_registry(scene)
    dependencies = registry.setdefault("dependencies", [])
    key = _record_key(record)
    existing = next((item for item in dependencies if _record_key(item) == key), None)
    if existing is None:
        existing = dict(record)
        existing.setdefault("status", UNRESOLVED)
        existing.setdefault("resolved_provider_package_id", "")
        existing.setdefault("resolved_provider_guid", "")
        existing.setdefault("resolved_provider_asset_path", "")
        dependencies.append(existing)
    save_dependency_registry(scene, registry)
    return existing


def _providers(target_guid: str, provider_type: str) -> list[Any]:
    target = str(target_guid or "").lower()
    if provider_type == "Material":
        return [item for item in bpy.data.materials if str(item.get("unity_material_guid", "")).lower() == target and item.get("unity_source_package_id") not in {None, "", "LEGACY_UNSCOPED"}]
    if provider_type == "Image":
        return [item for item in bpy.data.images if str(item.get("unity_guid", "")).lower() == target and item.get("unity_source_package_id") not in {None, "", "LEGACY_UNSCOPED"}]
    return []


def _find_consumer(record: dict[str, Any]) -> Any | None:
    package_id = record.get("consumer_package_id", "")
    file_id = str(record.get("consumer_game_object_file_id", ""))
    path = str(record.get("consumer_object_path", ""))
    candidates = [obj for obj in bpy.data.objects if obj.get("unity_source_package_id") == package_id]
    if path:
        candidates = [obj for obj in candidates if obj.get("unity_asset_path", "") == path]
    if file_id:
        exact = [obj for obj in candidates if str(obj.get("unity_prefab_file_id", "")) == file_id]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            return None
    if len(candidates) == 1:
        return candidates[0]
    return None


def _bind_material(record: dict[str, Any], material: Any) -> bool:
    consumer = _find_consumer(record)
    if consumer is None or not getattr(consumer, "data", None) or not hasattr(consumer.data, "materials"):
        record["status"] = MISSING_CONSUMER
        return False
    slot = int(record.get("consumer_slot_index", 0))
    while len(consumer.data.materials) <= slot:
        consumer.data.materials.append(None)
    consumer.data.materials[slot] = material
    return True


def _bind_texture(record: dict[str, Any], image: Any) -> bool:
    material_name = str(record.get("consumer_object_path", ""))
    material = next((item for item in bpy.data.materials if item.get("unity_material_guid") == record.get("consumer_asset_guid") and item.get("unity_source_package_id") == record.get("consumer_package_id")), None)
    if material is None:
        record["status"] = MISSING_CONSUMER
        return False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    label = str(record.get("texture_label", "Base Color"))
    node_name = f"Unity {label} {material.name}"
    tex = nodes.get(node_name) or next(
        (node for node in nodes if node.type == "TEX_IMAGE" and node.name.startswith(f"Unity {label} ")),
        None,
    ) or nodes.new("ShaderNodeTexImage")
    tex.name = tex.label = node_name
    tex.image = image
    if label == "Base Color":
        bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None and bsdf.inputs.get("Base Color") is not None:
            links.new(tex.outputs.get("Color"), bsdf.inputs.get("Base Color"))
    return True


def resolve_scene_dependencies(scene: Any) -> dict[str, int]:
    registry = load_dependency_registry(scene)
    counts = {"resolved_local": 0, "resolved_cross_package": 0, "unresolved": 0, "ambiguous": 0, "late_bindings_applied": 0}
    changed = False
    for record in registry.get("dependencies", []):
        if record.get("status") == RESOLVED_LOCAL or record.get("status") == RESOLVED_CROSS_PACKAGE:
            continue
        provider_type = "Material" if record.get("dependency_type") in {"PREFAB_RENDERER_MATERIAL", "FBX_EXTERNAL_MATERIAL"} else "Image"
        candidates = _providers(record.get("target_guid", ""), provider_type)
        local = [item for item in candidates if item.get("unity_source_package_id") == record.get("consumer_package_id")]
        status = ""
        provider = None
        if len(local) == 1:
            status, provider = RESOLVED_LOCAL, local[0]
        elif len(local) > 1:
            status = AMBIGUOUS_PROVIDER
        elif len(candidates) == 1:
            status, provider = RESOLVED_CROSS_PACKAGE, candidates[0]
        elif len(candidates) > 1:
            status = AMBIGUOUS_PROVIDER
        else:
            status = UNRESOLVED
        if provider is not None:
            if record.get("dependency_type") == "MATERIAL_TEXTURE":
                applied = _bind_texture(record, provider)
            else:
                applied = _bind_material(record, provider)
            if applied:
                record["status"] = status
                record["resolved_provider_package_id"] = provider.get("unity_source_package_id", "")
                record["resolved_provider_guid"] = provider.get("unity_material_guid", provider.get("unity_guid", ""))
                record["resolved_provider_asset_path"] = provider.get("unity_material_path", provider.get("unity_asset_path", ""))
                counts["resolved_local" if status == RESOLVED_LOCAL else "resolved_cross_package"] += 1
                counts["late_bindings_applied"] += 1
                changed = True
                continue
        record["status"] = status
        counts["ambiguous" if status == AMBIGUOUS_PROVIDER else "unresolved"] += 1
        changed = True
    if changed:
        save_dependency_registry(scene, registry)
    return counts


def resolve_after_import(scene: Any) -> dict[str, int]:
    return resolve_scene_dependencies(scene)


def capture_material_texture_dependencies(scene: Any, materials: Iterable[Any]) -> None:
    for material in materials:
        try:
            props = json.loads(str(material.get("unity_props", "{}")))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for property_name, texture in (props.get("textures") or {}).items():
            target_guid = str((texture or {}).get("guid", ""))
            if not target_guid:
                continue
            label = "Normal" if "normal" in property_name.lower() else "Emission" if "emission" in property_name.lower() else "Metallic" if any(key in property_name.lower() for key in ("metallic", "smoothness")) else "Base Color"
            capture_dependency(scene, {
                "dependency_type": "MATERIAL_TEXTURE",
                "consumer_package_id": material.get("unity_source_package_id", ""),
                "consumer_asset_guid": material.get("unity_material_guid", ""),
                "consumer_asset_path": material.get("unity_material_path", ""),
                "consumer_object_path": material.name,
                "consumer_slot_index": 0,
                "target_guid": target_guid,
                "target_file_id": "",
                "texture_label": label,
            })
