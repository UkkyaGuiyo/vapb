"""Persistent, package-scoped cross-package dependency capture and resolution."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Iterable

import bpy  # type: ignore

from ..unity.texture_roles import TextureRole, canonical_texture_properties, classify_texture_property
from ..unity.identity import select_package_provider
from .performance import diagnostic_add


SCENE_DEPENDENCY_REGISTRY = "unitypackage_dependency_registry"
UNRESOLVED = "UNRESOLVED"
RESOLVED_LOCAL = "RESOLVED_LOCAL"
RESOLVED_CROSS_PACKAGE = "RESOLVED_CROSS_PACKAGE"
AMBIGUOUS_PROVIDER = "AMBIGUOUS_PROVIDER"
MISSING_CONSUMER = "MISSING_CONSUMER"
USER_EDIT_PRESERVED = "USER_EDIT_PRESERVED"
UNVERIFIED_SLOT_STATE = "UNVERIFIED_SLOT_STATE"
UNVERIFIED_TEXTURE_STATE = "UNVERIFIED_TEXTURE_STATE"
UNSUPPORTED = "UNSUPPORTED"
INVALID_FBX_CONSUMER = "INVALID_FBX_CONSUMER"
INVALID_EXTERNAL_ROW = "INVALID_EXTERNAL_ROW"
EXTERNAL_SLOT_CLAIMED = "EXTERNAL_SLOT_CLAIMED"
MISSING_MATERIAL_FILE_ID = "MISSING_MATERIAL_FILE_ID"
RESOLVED_BUILTIN_PREVIEW = "RESOLVED_BUILTIN_PREVIEW"
BUILTIN_PREVIEW_GUID = "0000000000000000f000000000000000"
BUILTIN_PREVIEW_FILE_ID = "10303"
BUILTIN_PREVIEW_MARKER = "_vapb_builtin_preview_provider"


def load_dependency_registry(scene: Any) -> dict[str, Any]:
    diagnostic_add("dependency_registry_loads")
    try:
        raw = scene.get(SCENE_DEPENDENCY_REGISTRY, "")
        return json.loads(str(raw)) if raw else {"schema_version": 1, "dependencies": []}
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        return {"schema_version": 1, "dependencies": []}


def save_dependency_registry(scene: Any, registry: dict[str, Any]) -> None:
    diagnostic_add("dependency_registry_writes")
    diagnostic_add("dependency_registry_records", len(registry.get("dependencies", [])))
    scene[SCENE_DEPENDENCY_REGISTRY] = json.dumps(registry, ensure_ascii=False, sort_keys=True)


def _record_key(record: dict[str, Any]) -> tuple[Any, ...]:
    key = tuple(record.get(field, "") for field in (
        "dependency_type", "consumer_package_id", "consumer_asset_path",
        "consumer_file_id", "consumer_game_object_file_id", "consumer_slot_index",
        "consumer_prefab_instance_file_id",
        "consumer_occurrence_id", "consumer_native_realization_id",
        "target_guid", "target_file_id",
    ))
    if record.get("dependency_type") == "MATERIAL_TEXTURE":
        return key + (record.get("texture_label", ""),
                      (record.get("texture_ref") or {}).get("property_name", ""))
    if record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL":
        return key + (record.get("consumer_fbx_object_receipt_id", ""),
                      record.get("consumer_fbx_mesh_receipt_id", ""),
                      record.get("source_row_identity", ""))
    return key


def capture_dependency(scene: Any, record: dict[str, Any]) -> dict[str, Any]:
    diagnostic_add("dependency_capture_records")
    registry = load_dependency_registry(scene)
    dependencies = registry.setdefault("dependencies", [])
    key = _record_key(record)
    existing = next((item for item in dependencies if _record_key(item) == key), None)
    if existing is None:
        existing = dict(record)
        if record.get("dependency_type") in {"PREFAB_RENDERER_MATERIAL", "FBX_EXTERNAL_MATERIAL", "CLEAR_MATERIAL_SLOT"}:
            consumer = _find_consumer(record)
            if consumer is not None and getattr(consumer, "data", None) and hasattr(consumer.data, "materials"):
                slot = record.get("consumer_slot_index")
                if type(slot) is int and slot >= 0:
                    existing["initial_slot_state"] = _slot_signature(consumer, slot)
        existing.setdefault("status", UNRESOLVED)
        existing.setdefault("resolved_provider_package_id", "")
        existing.setdefault("resolved_provider_guid", "")
        existing.setdefault("resolved_provider_asset_path", "")
        existing.setdefault("resolution_provenance", "UNRESOLVED")
        existing.setdefault("provider_status", "UNRESOLVED")
        existing.setdefault("binding_status", "UNRESOLVED")
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
    if record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL":
        from .fbx_receipt import validate_persistent_receipt
        slot = record.get("consumer_slot_index")
        if (type(slot) is not int or slot < 0
                or record.get("consumer_receipt_version") != 1
                or record.get("consumer_fbx_receipt_version") != "vapb_fbx_realization_receipt_v1"
                or record.get("consumer_receipt_valid") is not True
                or not record.get("consumer_native_realization_id")
                or not record.get("consumer_package_id")):
            return None
        try:
            parsed_realization = uuid.UUID(str(record.get("consumer_native_realization_id", "")))
        except (ValueError, TypeError, AttributeError):
            return None
        if parsed_realization.version != 4 or parsed_realization.int == 0:
            return None
        rows = []
        for candidate in bpy.data.objects:
            try:
                candidate_id = uuid.UUID(str(candidate.get("_vapb_fbx_realization_id", "")))
            except (ValueError, TypeError, AttributeError):
                continue
            if candidate_id == parsed_realization:
                rows.append(candidate)
        if len(rows) != 1:
            return None
        obj = rows[0]
        if (obj.get("unity_source_package_id") != record.get("consumer_package_id")
                or str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() != str(record.get("consumer_fbx_guid", "")).lower()
                or str(obj.get("_vapb_fbx_source_asset_sha256", "")).lower() != str(record.get("consumer_fbx_sha256", "")).lower()
                or str(obj.get("_vapb_fbx_model_uid", "")) != str(record.get("consumer_fbx_model_uid", ""))
                or str(obj.get("_vapb_fbx_geometry_uid", "")) != str(record.get("consumer_fbx_geometry_uid", ""))
                or obj.get("_vapb_fbx_object_receipt_id") != record.get("consumer_fbx_object_receipt_id")
                or obj.get("_vapb_fbx_mesh_receipt_id") != record.get("consumer_fbx_mesh_receipt_id")
                or not re.fullmatch(r"[0-9a-f]{32}", str(record.get("consumer_fbx_guid", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("consumer_fbx_sha256", "")))
                or not validate_persistent_receipt(obj)
                or slot >= len(getattr(obj, "material_slots", []))):
            return None
        return obj
    if record.get("identity_bridge") == "UNITY_MODEL_WITNESS":
        from .model_witness_bridge import find_witness_consumer
        return find_witness_consumer(record, bpy.data.objects)
    package_id = record.get("consumer_package_id", "")
    file_id = str(record.get("consumer_game_object_file_id", ""))
    path = str(record.get("consumer_asset_path") or record.get("consumer_object_path", ""))
    if not package_id or not file_id or not path:
        return None
    candidates = [obj for obj in bpy.data.objects if obj.get("unity_source_package_id") == package_id]
    exact = [obj for obj in candidates
             if obj.get("unity_asset_path", "") == path
             and str(obj.get("unity_prefab_file_id", "")) == file_id]
    return exact[0] if len(exact) == 1 else None


def _material_token(material: Any) -> str | None:
    token = str(material.get("_vapb_dependency_material_token", ""))
    if not token:
        token = uuid.uuid4().hex
        material["_vapb_dependency_material_token"] = token
    return token if sum(str(item.get("_vapb_dependency_material_token", "")) == token
                        for item in bpy.data.materials) == 1 else None


def _slot_signature(consumer: Any, index: int) -> dict[str, Any] | None:
    """Persist a Blender Material datablock identity across save/reopen."""
    if index >= len(consumer.material_slots):
        return {"link": "ABSENT", "material": None}
    slot = consumer.material_slots[index]
    material = slot.material
    token = _material_token(material) if material is not None else None
    if material is not None and token is None:
        return None
    return {"link": slot.link, "material": token}


def _image_token(image: Any, *, create: bool = False) -> str | None:
    if image is None:
        return None
    token = str(image.get("_vapb_dependency_image_token", ""))
    if not token:
        if not create:
            return None
        token = uuid.uuid4().hex
        image["_vapb_dependency_image_token"] = token
    return token if sum(str(item.get("_vapb_dependency_image_token", "")) == token
                        for item in bpy.data.images) == 1 else None


def _texture_signature(record: dict[str, Any], material: Any) -> dict[str, Any] | None:
    """Snapshot only the managed texture node and its role's output connection."""
    tree = material.node_tree
    if tree is None:
        return None
    node = tree.nodes.get(str(record.get("texture_node_name", "")))
    if node is None or node.type != "TEX_IMAGE" or node.get("unity_dependency_binding_source") != "dependency_resolver":
        return None
    image = node.image
    image_token = _image_token(image)
    if image is not None and image_token is None:
        return None
    edges = sorted([link.from_node.name, link.from_socket.identifier,
                    link.to_node.name, link.to_socket.identifier]
                   for link in tree.links if link.from_node == node or link.to_node == node)
    bsdf = next((item for item in tree.nodes if item.type == "BSDF_PRINCIPLED"), None)
    socket_name = {"Base Color": "Base Color", "Normal": "Normal", "Emission": "Emission Color",
                   "Metallic": "Metallic", "Roughness": "Roughness"}.get(str(record.get("texture_label", "")))
    output_edges = sorted([link.from_node.name, link.from_socket.identifier]
                          for link in (bsdf.inputs.get(socket_name).links if bsdf is not None and socket_name and bsdf.inputs.get(socket_name) else []))
    return {"node": node.name, "image": image_token, "edges": edges, "output_edges": output_edges}


def _bind_material(record: dict[str, Any], material: Any) -> bool:
    if record.get("requires_occurrence_binding"):
        record["status"] = MISSING_CONSUMER
        return False
    is_fbx_external = record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL"
    if is_fbx_external:
        if (record.get("source_row_status") != "valid" or record.get("source_row_ambiguous") is not False
                or not record.get("source_row_identity") or not record.get("target_guid")
                or type(record.get("target_file_id")) is not str
                or not re.fullmatch(r"[0-9a-fA-F]{32}", str(record.get("target_guid", "")))
                or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)", str(record.get("target_file_id", "")))
                or not record.get("target_file_id") or record.get("consumer_slot_index") is None):
            record["status"] = INVALID_EXTERNAL_ROW
            return False
        file_id = int(record["target_file_id"])
        if file_id < -(1 << 63) or file_id > (1 << 63) - 1:
            record["status"] = INVALID_EXTERNAL_ROW
            return False
        if (str(material.get("unity_material_guid", "")).lower() != str(record.get("target_guid", "")).lower()
                or str(material.get("unity_material_file_id", "")) != str(record.get("target_file_id", ""))):
            record["status"] = MISSING_MATERIAL_FILE_ID
            return False
    consumer = _find_consumer(record)
    if consumer is None or not getattr(consumer, "data", None) or not hasattr(consumer.data, "materials"):
        record["status"] = INVALID_FBX_CONSUMER if is_fbx_external else MISSING_CONSUMER
        return False
    if record.get("identity_bridge") == "UNITY_MODEL_WITNESS":
        is_builtin_preview = (
            material.get(BUILTIN_PREVIEW_MARKER) == "UNITY_DEFAULT_MATERIAL"
            and material.get("_vapb_builtin_preview_approximate") is True)
        if is_builtin_preview:
            identity_matches = (
                record.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"
                and str(record.get("target_file_id", "")) == BUILTIN_PREVIEW_FILE_ID
                and str(record.get("target_guid", "")).lower() == BUILTIN_PREVIEW_GUID
                and str(material.get("_vapb_builtin_preview_file_id", "")) == BUILTIN_PREVIEW_FILE_ID
                and str(material.get("_vapb_builtin_preview_guid", "")).lower() == BUILTIN_PREVIEW_GUID)
        else:
            identity_matches = (
                str(material.get("unity_material_file_id", "")) == str(record.get("target_file_id", ""))
                and str(material.get("unity_material_guid", "")).lower() == str(record.get("target_guid", "")).lower())
        if not identity_matches:
            record["status"] = MISSING_CONSUMER
            return False
    slot = record.get("consumer_slot_index")
    if type(slot) is not int or slot < 0:
        record["status"] = INVALID_FBX_CONSUMER if is_fbx_external else MISSING_CONSUMER
        return False
    current_state = _slot_signature(consumer, slot)
    if current_state is None:
        record["status"] = UNVERIFIED_SLOT_STATE
        return False
    expected_state = record.get("applied_slot_state") or record.get("initial_slot_state")
    if expected_state is None:
        record["status"] = MISSING_CONSUMER
        return False
    if current_state != expected_state:
        record["status"] = USER_EDIT_PRESERVED
        return False
    if _material_token(material) is None:
        record["status"] = UNVERIFIED_SLOT_STATE
        return False
    from .material_builder import _assign_object_material

    _assign_object_material(consumer, slot, material)
    record["applied_slot_state"] = _slot_signature(consumer, slot)
    record["binding_source"] = "dependency_resolver"
    return True


def _bind_texture(record: dict[str, Any], image: Any) -> bool:
    material = next((item for item in bpy.data.materials if item.get("unity_material_guid") == record.get("consumer_asset_guid") and item.get("unity_source_package_id") == record.get("consumer_package_id")), None)
    if material is None:
        record["status"] = MISSING_CONSUMER
        return False
    label = str(record.get("texture_label", "Base Color"))
    if label == TextureRole.PRESERVE_ONLY.value:
        record["binding_source"] = "preserve_only"
        return True
    if record.get("binding_status") in {"BOUND", UNVERIFIED_TEXTURE_STATE} and not record.get("applied_texture_state"):
        record["status"] = UNVERIFIED_TEXTURE_STATE
        return False
    if record.get("applied_texture_state") is not None and _texture_signature(record, material) != record["applied_texture_state"]:
        record["status"] = USER_EDIT_PRESERVED
        return False
    if _image_token(image, create=True) is None:
        record["status"] = UNVERIFIED_TEXTURE_STATE
        return False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    existing_node = nodes.get(f"Unity {label} {material.name}")
    if (existing_node is not None
            and existing_node.get("unity_dependency_binding_source") != "dependency_resolver"
            and (existing_node.type != "TEX_IMAGE"
                 or (existing_node.image is not None and existing_node.image != image))):
        record["status"] = USER_EDIT_PRESERVED
        return False
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
    record["texture_node_name"] = tex.name
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        record["applied_texture_state"] = _texture_signature(record, material)
        record["binding_source"] = "dependency_resolver"
        return True

    def replace_input(socket, output):
        if socket is None or output is None:
            return
        for link in list(socket.links):
            links.remove(link)
        links.new(output, socket)

    def material_color(default):
        try:
            normalized = json.loads(str(material.get("unity_normalized", "{}")))
            value = normalized.get("base_color")
            if isinstance(value, list) and len(value) == 4:
                return tuple(value)
            props = json.loads(str(material.get("unity_props", "{}")))
            colors = props.get("colors", {})
            value = colors.get("_Color", colors.get("_BaseColor"))
            return tuple(value) if value is not None else default
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    if label == "Base Color":
        mix = nodes.get(f"Unity Base Color Mix {material.name}") or nodes.new("ShaderNodeMixRGB")
        mix.name = mix.label = f"Unity Base Color Mix {material.name}"
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        mix.inputs[1].default_value = material_color((1.0, 1.0, 1.0, 1.0))
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
    record["applied_texture_state"] = _texture_signature(record, material)
    record["binding_source"] = "dependency_resolver"
    return True


def _clear_material_slot(record: dict[str, Any]) -> bool:
    consumer = _find_consumer(record)
    slot = record.get("consumer_slot_index")
    if (consumer is None or not isinstance(slot, int) or slot < 0
            or slot >= len(consumer.material_slots)):
        record["status"] = MISSING_CONSUMER
        return False
    material_slot = consumer.material_slots[slot]
    applied_null = record.get("applied_slot_state") == {"link": "OBJECT", "material": None}
    if applied_null and (material_slot.link != "OBJECT" or material_slot.material is not None):
        record["status"] = USER_EDIT_PRESERVED
        return False
    current = ({"link": "OBJECT", "material": None} if applied_null
               else _slot_signature(consumer, slot))
    expected = record.get("applied_slot_state") or record.get("initial_slot_state")
    if current is None or expected is None:
        record["status"] = UNVERIFIED_SLOT_STATE
        return False
    if current != expected:
        record["status"] = USER_EDIT_PRESERVED
        return False
    material_slot.link = "OBJECT"
    material_slot.material = None
    record["applied_slot_state"] = _slot_signature(consumer, slot)
    record["binding_source"] = "dependency_resolver"
    return True


def _is_builtin_preview_reference(record: dict[str, Any]) -> bool:
    raw_file_id = record.get("target_file_id_raw")
    return (record.get("dependency_type") == "PREFAB_RENDERER_MATERIAL"
            and str(record.get("target_guid", "")).lower() == BUILTIN_PREVIEW_GUID
            and str(record.get("target_file_id", "")) == BUILTIN_PREVIEW_FILE_ID
            and type(raw_file_id) is int and raw_file_id == int(BUILTIN_PREVIEW_FILE_ID))


def _builtin_preview_material() -> Any:
    candidates = [material for material in bpy.data.materials
                  if material.get(BUILTIN_PREVIEW_MARKER) == "UNITY_DEFAULT_MATERIAL"
                  and str(material.get("_vapb_builtin_preview_guid", "")).lower() == BUILTIN_PREVIEW_GUID
                  and str(material.get("_vapb_builtin_preview_file_id", "")) == BUILTIN_PREVIEW_FILE_ID]
    if len(candidates) == 1:
        candidate = candidates[0]
        return (candidate if candidate.get("_vapb_builtin_preview_approximate") is True
                else None)
    if len(candidates) > 1:
        return None
    material = bpy.data.materials.new("Unity Built-in Default (Approximate Preview)")
    preview_color = (0.72, 0.72, 0.72, 1.0)
    material.diffuse_color = preview_color
    material.use_nodes = True
    shader = next((node for node in material.node_tree.nodes
                   if node.type == "BSDF_PRINCIPLED"), None)
    if shader is not None and shader.inputs.get("Base Color") is not None:
        shader.inputs["Base Color"].default_value = preview_color
    material[BUILTIN_PREVIEW_MARKER] = "UNITY_DEFAULT_MATERIAL"
    material["_vapb_builtin_preview_guid"] = BUILTIN_PREVIEW_GUID
    material["_vapb_builtin_preview_file_id"] = BUILTIN_PREVIEW_FILE_ID
    material["_vapb_builtin_preview_approximate"] = True
    material["_vapb_builtin_preview_note"] = "Display aid only; not a captured Unity Material asset."
    return material


def resolve_scene_dependencies(scene: Any) -> dict[str, int]:
    registry = load_dependency_registry(scene)
    try:
        provider_provenance = json.loads(str(scene.get("unitypackage_provider_provenance", "{}")))
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        provider_provenance = {}
    counts = {"resolved_local": 0, "resolved_cross_package": 0, "builtin_preview_bound": 0, "unresolved": 0, "ambiguous": 0, "missing_consumer": 0, "user_edit_preserved": 0, "unverified_slot_state": 0, "unverified_texture_state": 0, "null_realized": 0, "late_bindings_applied": 0, "external_slot_claimed": 0, "invalid_fbx_consumer": 0, "invalid_external_row": 0, "missing_material_file_id": 0, "provider_candidates_discovered": 0, "provider_discovered": 0, "material_binding_applied": 0}
    changed = False
    # Preflight exact witnessed Prefab claims before any FBX record can bind.
    # A pending provider and explicit null both reserve the witnessed slot.
    claims = {}
    for claim in registry.get("dependencies", []):
        if claim.get("dependency_type") not in {"PREFAB_RENDERER_MATERIAL", "CLEAR_MATERIAL_SLOT"}:
            continue
        if claim.get("identity_bridge") != "UNITY_MODEL_WITNESS":
            continue
        consumer = _find_consumer(claim)
        slot = claim.get("consumer_slot_index")
        if consumer is None or type(slot) is not int or slot < 0:
            continue
        key = (str(consumer.get("_vapb_fbx_realization_id", "")), slot)
        claims.setdefault(key, []).append(claim)
    for record in registry.get("dependencies", []):
        if record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL":
            slot = record.get("consumer_slot_index")
            if type(slot) is int:
                claim_rows = claims.get((str(record.get("consumer_native_realization_id", "")), slot), [])
                if claim_rows:
                    record["status"] = EXTERNAL_SLOT_CLAIMED
                    record["binding_status"] = EXTERNAL_SLOT_CLAIMED
                    record["provider_status"] = "SUPPRESSED_BY_PREFAB_CLAIM"
                    record["suppressed_by_claim_ids"] = [
                        str(row.get("consumer_occurrence_id", row.get("consumer_file_id", "")))
                        for row in claim_rows
                    ]
                    record["resolution_provenance"] = "EXACT_PREFAB_SLOT_CLAIM"
                    counts["external_slot_claimed"] += 1
                    changed = True
                    continue
            if record.get("consumer_slot_index") is None:
                record["status"] = "METADATA_ONLY"
                record["binding_status"] = "METADATA_ONLY"
                record["provider_status"] = "NOT_QUERIED"
                counts["unresolved"] += 1
                changed = True
                continue
            target_file_id = record.get("target_file_id")
            valid_target = (
                record.get("source_row_status") == "valid"
                and record.get("source_row_ambiguous") is False
                and bool(record.get("source_row_identity"))
                and bool(re.fullmatch(r"[0-9a-fA-F]{32}", str(record.get("target_guid", ""))))
                and type(target_file_id) is str
                and bool(re.fullmatch(r"-?(?:0|[1-9][0-9]*)", target_file_id))
            )
            if valid_target:
                file_id_value = int(target_file_id)
                valid_target = -(1 << 63) <= file_id_value <= (1 << 63) - 1
            if not valid_target:
                record["status"] = INVALID_EXTERNAL_ROW
                record["binding_status"] = INVALID_EXTERNAL_ROW
                record["provider_status"] = "NOT_QUERIED"
                counts["invalid_external_row"] += 1
                changed = True
                continue
            if _find_consumer(record) is None:
                record["status"] = INVALID_FBX_CONSUMER
                record["binding_status"] = INVALID_FBX_CONSUMER
                record["provider_status"] = "NOT_QUERIED"
                counts["invalid_fbx_consumer"] += 1
                changed = True
                continue
        if record.get("dependency_type") == "CLEAR_MATERIAL_SLOT":
            record["provider_status"] = "NOT_REQUIRED"
            applied = _clear_material_slot(record)
            record["binding_status"] = "BOUND" if applied else record["status"]
            if applied:
                record["status"] = "NULL_REALIZED"
                counts["null_realized"] += 1
                counts["late_bindings_applied"] += 1
            else:
                counts[{USER_EDIT_PRESERVED: "user_edit_preserved",
                        UNVERIFIED_SLOT_STATE: "unverified_slot_state"}.get(
                            record["status"], "missing_consumer")] += 1
            record["resolution_provenance"] = "SERIALIZED_EXPLICIT_NULL"
            changed = True
            continue
        if _is_builtin_preview_reference(record):
            preview = _builtin_preview_material()
            preview_candidates = [material for material in bpy.data.materials
                                  if material.get(BUILTIN_PREVIEW_MARKER) == "UNITY_DEFAULT_MATERIAL"
                                  and str(material.get("_vapb_builtin_preview_guid", "")).lower() == BUILTIN_PREVIEW_GUID
                                  and str(material.get("_vapb_builtin_preview_file_id", "")) == BUILTIN_PREVIEW_FILE_ID]
            preview_block = (AMBIGUOUS_PROVIDER if len(preview_candidates) > 1
                             else UNSUPPORTED if preview_candidates and preview is None
                             else None)
            record["provider_status"] = preview_block or "ENGINE_RESIDENT_BUILTIN"
            applied = preview is not None and _bind_material(record, preview)
            if applied:
                record["status"] = RESOLVED_BUILTIN_PREVIEW
                record["binding_status"] = "BOUND"
                record["resolved_provider_package_id"] = ""
                record["resolved_provider_guid"] = BUILTIN_PREVIEW_GUID
                record["resolved_provider_asset_path"] = ""
                record["resolution_provenance"] = "UNITY_BUILTIN_PREVIEW_APPROXIMATE"
                record["binding_source"] = "builtin_preview_resolver"
                counts["builtin_preview_bound"] += 1
                counts["late_bindings_applied"] += 1
            else:
                blocked_status = record.get("status") if record.get("status") in {
                    USER_EDIT_PRESERVED, UNVERIFIED_SLOT_STATE, UNVERIFIED_TEXTURE_STATE
                } else preview_block or MISSING_CONSUMER
                record["status"] = blocked_status
                record["binding_status"] = blocked_status
                record["resolution_provenance"] = "UNITY_BUILTIN_PREVIEW_APPROXIMATE"
                if blocked_status == USER_EDIT_PRESERVED:
                    counts["user_edit_preserved"] += 1
                elif blocked_status == UNVERIFIED_SLOT_STATE:
                    counts["unverified_slot_state"] += 1
                elif blocked_status == AMBIGUOUS_PROVIDER:
                    counts["ambiguous"] += 1
                elif blocked_status == UNSUPPORTED:
                    counts["unresolved"] += 1
                else:
                    counts["missing_consumer"] += 1
            changed = True
            continue
        provider_type = "Material" if record.get("dependency_type") in {"PREFAB_RENDERER_MATERIAL", "FBX_EXTERNAL_MATERIAL"} else "Image"
        candidates = _providers(record.get("target_guid", ""), provider_type)
        wrong_file_id = False
        if record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL":
            guid_candidates = [item for item in candidates
                               if str(item.get("unity_material_guid", "")).lower() == str(record.get("target_guid", "")).lower()]
            candidates = [item for item in candidates
                          if str(item.get("unity_material_guid", "")).lower() == str(record.get("target_guid", "")).lower()
                          and str(item.get("unity_material_file_id", "")) == str(record.get("target_file_id", ""))]
            wrong_file_id = bool(guid_candidates and not candidates)
            if wrong_file_id:
                record["provider_status"] = MISSING_MATERIAL_FILE_ID
                record["status"] = MISSING_MATERIAL_FILE_ID
            else:
                if record.get("status") == MISSING_MATERIAL_FILE_ID:
                    record["status"] = UNRESOLVED
                if record.get("binding_status") == MISSING_MATERIAL_FILE_ID:
                    record["binding_status"] = UNRESOLVED
        status, provider = select_package_provider(
            ((item.get("unity_source_package_id"), item) for item in candidates),
            record.get("consumer_package_id"))
        counts["provider_candidates_discovered"] += len(candidates)
        if not (record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL" and wrong_file_id):
            record["provider_status"] = status
        if provider is not None:
            counts["provider_discovered"] += 1
        if provider is not None:
            if record.get("dependency_type") == "MATERIAL_TEXTURE":
                applied = _bind_texture(record, provider)
            else:
                applied = _bind_material(record, provider)
            if applied:
                record["status"] = status
                record["binding_status"] = "BOUND"
                record["resolved_provider_package_id"] = provider.get("unity_source_package_id", "")
                record["resolved_provider_guid"] = provider.get("unity_material_guid", provider.get("unity_guid", ""))
                record["resolved_provider_asset_path"] = provider.get("unity_material_path", provider.get("unity_asset_path", ""))
                record["resolution_provenance"] = provider_provenance.get(
                    record["resolved_provider_package_id"],
                    "AUTO_LOCAL" if status == RESOLVED_LOCAL else "AUTO_BOUNDED_DISCOVERY",
                )
                counts["resolved_local" if status == RESOLVED_LOCAL else "resolved_cross_package"] += 1
                counts["late_bindings_applied"] += 1
                if record.get("dependency_type") == "FBX_EXTERNAL_MATERIAL":
                    counts["material_binding_applied"] += 1
                changed = True
                continue
            blocked_status = record.get("status") if record.get("status") in {USER_EDIT_PRESERVED, UNVERIFIED_SLOT_STATE, UNVERIFIED_TEXTURE_STATE, INVALID_FBX_CONSUMER, INVALID_EXTERNAL_ROW, MISSING_MATERIAL_FILE_ID} else MISSING_CONSUMER
            record["status"] = blocked_status
            record["binding_status"] = blocked_status
            record["resolution_provenance"] = provider_provenance.get(
                provider.get("unity_source_package_id", ""),
                "AUTO_LOCAL" if status == RESOLVED_LOCAL else "AUTO_BOUNDED_DISCOVERY",
            )
            blocked_key = {USER_EDIT_PRESERVED: "user_edit_preserved", UNVERIFIED_SLOT_STATE: "unverified_slot_state", UNVERIFIED_TEXTURE_STATE: "unverified_texture_state", INVALID_FBX_CONSUMER: "invalid_fbx_consumer", INVALID_EXTERNAL_ROW: "invalid_external_row", MISSING_MATERIAL_FILE_ID: "missing_material_file_id"}.get(blocked_status, "missing_consumer")
            counts[blocked_key] += 1
            changed = True
            continue
        if status in {AMBIGUOUS_PROVIDER, UNRESOLVED} and record.get("binding_source") == "dependency_resolver":
            _unbind_dependency(record)
        blocked_status = record.get("status") if record.get("status") in {USER_EDIT_PRESERVED, UNVERIFIED_TEXTURE_STATE, INVALID_FBX_CONSUMER, INVALID_EXTERNAL_ROW, MISSING_MATERIAL_FILE_ID} else status
        record["status"] = blocked_status
        record["binding_status"] = blocked_status
        record["resolution_provenance"] = "AMBIGUOUS" if status == AMBIGUOUS_PROVIDER else "UNRESOLVED"
        counts[{USER_EDIT_PRESERVED: "user_edit_preserved", UNVERIFIED_TEXTURE_STATE: "unverified_texture_state", INVALID_FBX_CONSUMER: "invalid_fbx_consumer", INVALID_EXTERNAL_ROW: "invalid_external_row", MISSING_MATERIAL_FILE_ID: "missing_material_file_id"}.get(
            blocked_status, "ambiguous" if status == AMBIGUOUS_PROVIDER else "unresolved")] += 1
        changed = True
    if changed:
        save_dependency_registry(scene, registry)
    return counts


def _unbind_dependency(record: dict[str, Any]) -> None:
    if record.get("dependency_type") == "MATERIAL_TEXTURE":
        material = next((item for item in bpy.data.materials if item.get("unity_material_guid") == record.get("consumer_asset_guid") and item.get("unity_source_package_id") == record.get("consumer_package_id")), None)
        if material is None:
            return
        expected = record.get("applied_texture_state")
        if expected is None:
            record["status"] = UNVERIFIED_TEXTURE_STATE
            return
        current = _texture_signature(record, material)
        if current != expected:
            provider_image_removed = (current is not None and current.get("image") is None
                                      and expected.get("image")
                                      and not any(item.get("_vapb_dependency_image_token") == expected["image"]
                                                  for item in bpy.data.images)
                                      and {key: value for key, value in current.items() if key != "image"}
                                      == {key: value for key, value in expected.items() if key != "image"})
            if not provider_image_removed:
                record["status"] = USER_EDIT_PRESERVED
                return
        node = material.node_tree.nodes.get(str(record.get("texture_node_name", "")))
        node.image = None
        node["unity_dependency_binding_source"] = ""
        node["unity_dependency_provider_guid"] = ""
        record["binding_source"] = ""
        record.pop("applied_texture_state", None)
        return
    consumer = _find_consumer(record)
    if consumer is None or not getattr(consumer, "data", None) or not hasattr(consumer.data, "materials"):
        return
    slot = int(record.get("consumer_slot_index", 0))
    if slot < 0 or slot >= len(consumer.material_slots):
        return
    material_slot = consumer.material_slots[slot]
    current = material_slot.material
    if (record.get("applied_slot_state") is not None
            and _slot_signature(consumer, slot) == record["applied_slot_state"]
            and current is not None
            and current.get("unity_source_package_id") == record.get("resolved_provider_package_id")
            and current.get("unity_material_guid") == record.get("resolved_provider_guid")):
        if material_slot.link == "OBJECT":
            material_slot.material = None
        else:
            consumer.data.materials[slot] = None
        record["binding_source"] = ""
        # The resolver-owned clear is itself the last managed state. Keep its
        # receipt so a later provider recovery can rebind from OBJECT+None
        # without mistaking that state for a user edit. initial_slot_state
        # remains the original FBX capture for provenance.
        record["applied_slot_state"] = _slot_signature(consumer, slot)


def resolve_after_import(scene: Any) -> dict[str, int]:
    return resolve_scene_dependencies(scene)


def capture_material_texture_dependencies(scene: Any, materials: Iterable[Any]) -> None:
    diagnostic_add("dependency_capture_material_batches")
    for material in materials:
        try:
            props = json.loads(str(material.get("unity_props", "{}")))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        textures = props.get("textures") or {}
        normalized = {}
        try:
            normalized = json.loads(str(material.get("unity_normalized", "{}")))
        except (TypeError, ValueError, json.JSONDecodeError):
            normalized = {}
        family = str(material.get("unity_shader_family", ""))
        shader_name = str(material.get("unity_shader_name", ""))
        canonical = canonical_texture_properties(textures, family, shader_name)
        canonical_properties = {property_name: role for role, property_name in canonical.items()}
        roles_by_guid: dict[str, set[TextureRole]] = {}
        for role, property_name in canonical.items():
            guid = str((textures.get(property_name) or {}).get("guid", ""))
            if guid:
                roles_by_guid.setdefault(guid, set()).add(role)
        for key, role in (("base_color_tex", TextureRole.BASE_COLOR), ("normal_tex", TextureRole.NORMAL), ("emission_tex", TextureRole.EMISSION), ("metallic_tex", TextureRole.METALLIC)):
            guid = str((normalized.get(key) or {}).get("guid", ""))
            if guid:
                roles_by_guid.setdefault(guid, set()).add(role)
        seen_roles: set[TextureRole] = set()
        for property_name, texture in textures.items():
            target_guid = str((texture or {}).get("guid", ""))
            if not target_guid:
                continue
            role = canonical_properties.get(property_name) or classify_texture_property(family, shader_name, property_name)
            if role == TextureRole.PRESERVE_ONLY:
                candidates = roles_by_guid.get(target_guid, set())
                if len(candidates) == 1:
                    role = next(iter(candidates))
            if role in {TextureRole.BASE_COLOR, TextureRole.NORMAL, TextureRole.EMISSION, TextureRole.METALLIC, TextureRole.ROUGHNESS, TextureRole.OCCLUSION}:
                if role in seen_roles:
                    continue
                seen_roles.add(role)
            label = role.value
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

