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
    record["binding_source"] = "dependency_resolver"
    return True


def _bind_texture(record: dict[str, Any], image: Any) -> bool:
    material = next((item for item in bpy.data.materials if item.get("unity_material_guid") == record.get("consumer_asset_guid") and item.get("unity_source_package_id") == record.get("consumer_package_id")), None)
    if material is None:
        record["status"] = MISSING_CONSUMER
        return False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    label = str(record.get("texture_label", "Base Color"))
    texture_data = record.get("texture_ref") or {}
    try:
        from .material_builder import _texture_node
        from ..unity.material_model import UnityTextureRef
        ref = UnityTextureRef(
            property_name=str(texture_data.get("property_name", label)),
            guid=str(texture_data.get("guid", record.get("target_guid", ""))),
            file_id=int(texture_data.get("file_id", 0) or 0),
            scale=tuple(texture_data.get("scale", (1.0, 1.0)))[:2],
            offset=tuple(texture_data.get("offset", (0.0, 0.0)))[:2],
        )
        tex = _texture_node(nodes, links, material.name, label, ref, image)
    except (TypeError, ValueError, AttributeError, RuntimeError, ImportError):
        tex_name = f"Unity {label} {material.name}"
        tex = nodes.get(tex_name) or nodes.new("ShaderNodeTexImage")
        tex.name = tex.label = tex_name
        tex.image = image
    tex["unity_dependency_binding_source"] = "dependency_resolver"
    tex["unity_dependency_provider_guid"] = image.get("unity_guid", "")
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return True

    def replace_input(socket, output):
        if socket is None or output is None:
            return
        for link in list(socket.links):
            links.remove(link)
        links.new(output, socket)

    def material_color(key, default):
        try:
            props = json.loads(str(material.get("unity_props", "{}")))
            value = props.get("colors", {}).get(key)
            return tuple(value) if value is not None else default
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    if label == "Base Color":
        mix = nodes.get(f"Unity Base Color Mix {material.name}") or nodes.new("ShaderNodeMixRGB")
        mix.name = mix.label = f"Unity Base Color Mix {material.name}"
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        mix.inputs[1].default_value = material_color("_Color", (1.0, 1.0, 1.0, 1.0))
        replace_input(mix.inputs.get("Color2"), tex.outputs.get("Color"))
        replace_input(bsdf.inputs.get("Base Color"), mix.outputs.get("Color"))
    elif label == "Normal":
        normal = nodes.get(f"Unity Normal Map {material.name}") or nodes.new("ShaderNodeNormalMap")
        normal.name = normal.label = f"Unity Normal Map {material.name}"
        replace_input(normal.inputs.get("Color"), tex.outputs.get("Color"))
        replace_input(bsdf.inputs.get("Normal"), normal.outputs.get("Normal"))
    elif label == "Emission":
        replace_input(bsdf.inputs.get("Emission Color"), tex.outputs.get("Color"))
    elif label == "Metallic":
        replace_input(bsdf.inputs.get("Metallic"), tex.outputs.get("Color"))
        invert = nodes.get(f"Unity Smoothness to Roughness {material.name}") or nodes.new("ShaderNodeMath")
        invert.name = invert.label = f"Unity Smoothness to Roughness {material.name}"
        invert.operation = "SUBTRACT"
        invert.inputs[0].default_value = 1.0
        replace_input(invert.inputs[1], tex.outputs.get("Alpha"))
        replace_input(bsdf.inputs.get("Roughness"), invert.outputs.get("Value"))
    return True


def resolve_scene_dependencies(scene: Any) -> dict[str, int]:
    registry = load_dependency_registry(scene)
    counts = {"resolved_local": 0, "resolved_cross_package": 0, "unresolved": 0, "ambiguous": 0, "late_bindings_applied": 0}
    changed = False
    for record in registry.get("dependencies", []):
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
        if status in {AMBIGUOUS_PROVIDER, UNRESOLVED} and record.get("binding_source") == "dependency_resolver":
            _unbind_dependency(record)
        record["status"] = status
        counts["ambiguous" if status == AMBIGUOUS_PROVIDER else "unresolved"] += 1
        changed = True
    if changed:
        save_dependency_registry(scene, registry)
    return counts


def _unbind_dependency(record: dict[str, Any]) -> None:
    if record.get("dependency_type") == "MATERIAL_TEXTURE":
        material = next((item for item in bpy.data.materials if item.get("unity_material_guid") == record.get("consumer_asset_guid") and item.get("unity_source_package_id") == record.get("consumer_package_id")), None)
        if material is None:
            return
        provider_guid = record.get("resolved_provider_guid", "")
        for node in list(material.node_tree.nodes):
            if node.get("unity_dependency_binding_source") == "dependency_resolver" and node.get("unity_dependency_provider_guid") == provider_guid:
                node.image = None
        return
    consumer = _find_consumer(record)
    if consumer is None or not getattr(consumer, "data", None) or not hasattr(consumer.data, "materials"):
        return
    slot = int(record.get("consumer_slot_index", 0))
    if slot >= len(consumer.data.materials):
        return
    current = consumer.data.materials[slot]
    if current is not None and current.get("unity_source_package_id") == record.get("resolved_provider_package_id") and current.get("unity_material_guid") == record.get("resolved_provider_guid"):
        consumer.data.materials[slot] = None
    record["binding_source"] = ""


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
                "texture_ref": dict(texture),
            })
