"""Convert normalized Unity materials into editable Blender node graphs."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Iterable, Optional

import bpy  # type: ignore

from ..unity.material_mapping import (
    external_object_guid_for_name,
    resolve_material_entry,
    strip_material_suffix,
)
from ..unity.material_model import NormalizedMaterial, UnityMaterialData, UnityTextureRef
from ..unity.material_parser import parse_material
from ..unity.prefab_parser import PrefabData, ref_file_id, ref_guid
from ..unity.profiles.base import normalize_material
from .texture_loader import load_texture_by_guid
from .dependency_resolver import capture_dependency


def _measure(tracker, phase: str, function, *args, **kwargs):
    if tracker is None:
        return function(*args, **kwargs)
    return tracker.measure(phase, function, *args, **kwargs)


def _input(node, name: str):
    return node.inputs.get(name)


def _set_input(node, name: str, value) -> None:
    socket = _input(node, name)
    if socket is not None:
        socket.default_value = value


def _existing_material(data: UnityMaterialData, source_package_id: str = ""):
    for material in bpy.data.materials:
        if (
            data.guid
            and material.get("unity_material_guid") == data.guid
            and material.get("unity_source_package_id", "") == source_package_id
        ):
            return material
        if (
            not data.guid
            and material.get("unity_material_path") == data.unity_path
            and material.get("unity_source_package_id", "") == source_package_id
        ):
            return material
    return bpy.data.materials.new(data.name)


def _material_output(nodes):
    outputs = [node for node in nodes if node.type == "OUTPUT_MATERIAL"]
    active = next((node for node in outputs if getattr(node, "is_active_output", False)), None)
    output = active or (outputs[0] if outputs else None)
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    try:
        output.is_active_output = True
    except (AttributeError, TypeError, RuntimeError):
        pass
    return output


def _principled_node(nodes, output):
    candidates = [node for node in nodes if node.type == "BSDF_PRINCIPLED"]
    surface = output.inputs.get("Surface") if output else None
    if surface is not None and surface.is_linked:
        connected = surface.links[0].from_node
        if connected.type == "BSDF_PRINCIPLED":
            return connected
    return candidates[0] if candidates else nodes.new("ShaderNodeBsdfPrincipled")


def _texture_node(nodes, links, material_name: str, label: str, ref: UnityTextureRef, image):
    tex_name = f"Unity {label} {material_name}"
    tex = nodes.get(tex_name) or nodes.new("ShaderNodeTexImage")
    tex.name = tex.label = tex_name
    tex.image = image
    # Always make the UV source explicit.  Relying on an unconnected Image
    # Texture Vector input leaves the coordinate source implicit and produced
    # untrustworthy Material Preview results in Blender 5.2.1.
    texcoord_name = f"Unity {label} UV {material_name}"
    texcoord = nodes.get(texcoord_name) or nodes.new("ShaderNodeTexCoord")
    texcoord.name = texcoord.label = texcoord_name
    vector_output = texcoord.outputs.get("UV")
    vector_input = tex.inputs.get("Vector")
    if ref.scale != (1.0, 1.0) or ref.offset != (0.0, 0.0):
        mapping_name = f"Unity {label} Mapping {material_name}"
        mapping = nodes.get(mapping_name) or nodes.new("ShaderNodeMapping")
        mapping.name = mapping.label = mapping_name
        _set_input(mapping, "Scale", (*ref.scale, 1.0))
        _set_input(mapping, "Location", (*ref.offset, 0.0))
        links.new(vector_output, mapping.inputs.get("Vector"))
        vector_output = mapping.outputs.get("Vector")
    links.new(vector_output, vector_input)
    if image.get("unity_wrap_u", 0) or image.get("unity_wrap_v", 0):
        try:
            tex.extension = "CLIP"
        except (AttributeError, TypeError, RuntimeError):
            pass
    return tex


def _set_surface_mode(material, normalized: NormalizedMaterial) -> None:
    if normalized.alpha_mode not in {"blend", "cutout"}:
        return
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "BLENDED" if normalized.alpha_mode == "blend" else "DITHERED"
        except (AttributeError, TypeError, RuntimeError):
            pass
    elif hasattr(material, "blend_method"):
        try:
            material.blend_method = "BLEND" if normalized.alpha_mode == "blend" else "CLIP"
        except (AttributeError, TypeError, RuntimeError):
            pass


def _save_metadata(material, data: UnityMaterialData, normalized: NormalizedMaterial, source_package_id: str = "") -> None:
    material["unity_source_material"] = str(data.path)
    material["unity_material_guid"] = data.guid
    material["unity_material_file_id"] = str(data.file_id) if data.file_id is not None else ""
    material["unity_material_path"] = data.unity_path
    if source_package_id:
        material["unity_source_package_id"] = source_package_id
    material["unity_material_name"] = data.name
    material["_vapb_source_material_sha256"] = hashlib.sha256(data.path.read_bytes()).hexdigest()
    material["unity_shader_guid"] = data.shader_guid
    material["unity_shader_name"] = normalized.shader_name or data.shader_name
    material["unity_shader_family"] = normalized.family
    material["unity_shader_variant"] = str(normalized.extras.get("variant", ""))
    material["unity_props"] = json.dumps(
        {
            "floats": data.floats,
            "ints": data.ints,
            "colors": {key: list(value) for key, value in data.colors.items()},
            "textures": {key: value.to_dict() for key, value in data.textures.items()},
            "keywords": data.keywords,
            "invalid_keywords": data.invalid_keywords,
            "render_queue": data.render_queue,
            "normalized_extras": normalized.extras,
            "warnings": normalized.warnings,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    material["unity_normalized"] = json.dumps(normalized.to_dict(), ensure_ascii=False, sort_keys=True)


def build_material(
    data: UnityMaterialData,
    asset_db,
    pack_textures: bool = False,
    use_textures: bool = True,
    timing=None,
):
    normalized = normalize_material(data)
    source_package_id = getattr(asset_db, "source_package_id", "")
    material = _existing_material(data, source_package_id)
    material.use_nodes = True
    material.diffuse_color = normalized.base_color
    material.use_backface_culling = normalized.cull_backface
    _set_surface_mode(material, normalized)
    _save_metadata(material, data, normalized, source_package_id)
    # A provider package can arrive before its consumer. Keep its Material
    # datablock in the .blend so save/reopen does not erase the pending source.
    material.use_fake_user = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = _material_output(nodes)
    bsdf = _principled_node(nodes, output)
    links.new(bsdf.outputs.get("BSDF"), output.inputs.get("Surface"))
    _set_input(bsdf, "Base Color", normalized.base_color)
    _set_input(bsdf, "Metallic", max(0.0, min(1.0, normalized.metallic)))
    _set_input(bsdf, "Roughness", max(0.0, min(1.0, normalized.roughness)))
    _set_input(bsdf, "Alpha", normalized.base_color[3] if normalized.alpha_mode != "opaque" else 1.0)
    _set_input(bsdf, "Emission Color", normalized.emission_color)
    _set_input(bsdf, "Emission Strength", normalized.emission_strength)

    if not use_textures:
        return material

    base_image = _measure(
        timing,
        "texture_load",
        load_texture_by_guid,
        asset_db,
        normalized.base_color_tex.guid if normalized.base_color_tex else None,
        pack=pack_textures,
    )
    if base_image and normalized.base_color_tex:
        tex = _texture_node(nodes, links, data.name, "Base Color", normalized.base_color_tex, base_image)
        mix = nodes.get(f"Unity Base Color Mix {data.name}") or nodes.new("ShaderNodeMixRGB")
        mix.name = mix.label = f"Unity Base Color Mix {data.name}"
        mix.blend_type = "MULTIPLY"
        _set_input(mix, "Fac", 1.0)
        _set_input(mix, "Color1", normalized.base_color)
        links.new(tex.outputs.get("Color"), mix.inputs.get("Color2"))
        links.new(mix.outputs.get("Color"), _input(bsdf, "Base Color"))
        alpha_socket = _input(bsdf, "Alpha")
        if alpha_socket is not None:
            if normalized.alpha_mode == "cutout":
                alpha = nodes.get(f"Unity Alpha Cutout {data.name}") or nodes.new("ShaderNodeMath")
                alpha.name = alpha.label = f"Unity Alpha Cutout {data.name}"
                alpha.operation = "GREATER_THAN"
                alpha.inputs[1].default_value = normalized.alpha_cutoff
                links.new(tex.outputs.get("Alpha"), alpha.inputs[0])
                links.new(alpha.outputs[0], alpha_socket)
            elif normalized.alpha_mode == "blend":
                links.new(tex.outputs.get("Alpha"), alpha_socket)

    normal_image = _measure(
        timing,
        "texture_load",
        load_texture_by_guid,
        asset_db,
        normalized.normal_tex.guid if normalized.normal_tex else None,
        pack=pack_textures,
    )
    if normal_image and normalized.normal_tex and _input(bsdf, "Normal"):
        tex = _texture_node(nodes, links, data.name, "Normal", normalized.normal_tex, normal_image)
        normal = nodes.get(f"Unity Normal Map {data.name}") or nodes.new("ShaderNodeNormalMap")
        normal.name = normal.label = f"Unity Normal Map {data.name}"
        _set_input(normal, "Strength", normalized.normal_strength)
        links.new(tex.outputs.get("Color"), _input(normal, "Color"))
        links.new(normal.outputs.get("Normal"), _input(bsdf, "Normal"))

    emission_image = _measure(
        timing,
        "texture_load",
        load_texture_by_guid,
        asset_db,
        normalized.emission_tex.guid if normalized.emission_tex else None,
        pack=pack_textures,
    )
    if emission_image and normalized.emission_tex and _input(bsdf, "Emission Color"):
        tex = _texture_node(nodes, links, data.name, "Emission", normalized.emission_tex, emission_image)
        if normalized.emission_color != (0.0, 0.0, 0.0, 1.0):
            mix = nodes.get(f"Unity Emission Mix {data.name}") or nodes.new("ShaderNodeMixRGB")
            mix.name = mix.label = f"Unity Emission Mix {data.name}"
            mix.blend_type = "MULTIPLY"
            _set_input(mix, "Fac", 1.0)
            _set_input(mix, "Color1", normalized.emission_color)
            links.new(tex.outputs.get("Color"), mix.inputs.get("Color2"))
            links.new(mix.outputs.get("Color"), _input(bsdf, "Emission Color"))
        else:
            links.new(tex.outputs.get("Color"), _input(bsdf, "Emission Color"))

    metallic_image = _measure(
        timing,
        "texture_load",
        load_texture_by_guid,
        asset_db,
        normalized.metallic_tex.guid if normalized.metallic_tex else None,
        pack=pack_textures,
    )
    if metallic_image and normalized.metallic_tex:
        tex = _texture_node(nodes, links, data.name, "Metallic", normalized.metallic_tex, metallic_image)
        if _input(bsdf, "Metallic"):
            links.new(tex.outputs.get("Color"), _input(bsdf, "Metallic"))
        if _input(bsdf, "Roughness"):
            invert = nodes.get(f"Unity Smoothness to Roughness {data.name}") or nodes.new("ShaderNodeMath")
            invert.name = invert.label = f"Unity Smoothness to Roughness {data.name}"
            invert.operation = "SUBTRACT"
            invert.inputs[0].default_value = 1.0
            links.new(tex.outputs.get("Alpha"), invert.inputs[1])
            links.new(invert.outputs[0], _input(bsdf, "Roughness"))

    return material


def build_material_library(
    asset_db,
    pack_textures: bool = False,
    use_textures: bool = True,
    timing=None,
) -> dict[str, bpy.types.Material]:
    result: dict[str, bpy.types.Material] = {}
    for path in asset_db.materials():
        try:
            data = _measure(timing, "material_parse", parse_material, path, asset_db)
            result[str(path)] = _measure(
                timing,
                "material_build",
                build_material,
                data,
                asset_db,
                pack_textures=pack_textures,
                use_textures=use_textures,
                timing=timing,
            )
        except (OSError, UnicodeError, ValueError, RuntimeError):
            continue
    return result


def _material_maps(materials: Iterable[bpy.types.Material]):
    materials = list(materials)
    by_name = {}
    for material in materials:
        for name in {material.name.casefold(), strip_material_suffix(material.name).casefold()}:
            if name in by_name:
                # A name is not an identity.  Refuse the fallback when two
                # Unity assets normalize to the same name; GUID/path mapping
                # remains authoritative.
                by_name[name] = None
            else:
                by_name[name] = material
    by_guid = {material.get("unity_material_guid"): material for material in materials if material.get("unity_material_guid")}
    return by_name, by_guid


def apply_materials_by_name(
    objects: Iterable[bpy.types.Object],
    materials: Iterable[bpy.types.Material],
    asset_db=None,
    material_library: Optional[dict[str, bpy.types.Material]] = None,
    scene=None,
) -> None:
    materials = list(materials)
    by_name, by_guid = _material_maps(materials)
    material_library = material_library or {}
    for obj in objects:
        if not getattr(obj, "data", None) or not hasattr(obj.data, "materials"):
            continue
        meta_text = ""
        source_fbx = obj.get("unity_source_fbx")
        if asset_db and source_fbx:
            try:
                meta_text = Path(str(source_fbx) + ".meta").read_text(encoding="utf-8", errors="replace")
            except OSError:
                meta_text = ""
        external_objects = {}
        if asset_db and meta_text:
            from ..unity.material_mapping import parse_external_objects
            external_objects = parse_external_objects(meta_text)
        for index, slot in enumerate(obj.data.materials):
            if slot is None:
                continue
            externally_mapped, target_guid = external_object_guid_for_name(
                external_objects, slot.name
            )
            if scene and external_objects:
                if target_guid and asset_db.find_guid(target_guid) is None:
                    capture_dependency(scene, {
                        "dependency_type": "FBX_EXTERNAL_MATERIAL",
                        "consumer_package_id": asset_db.source_package_id,
                        "consumer_asset_path": obj.get("unity_asset_path", obj.get("unity_source_fbx", "")),
                        "consumer_object_path": obj.get("unity_asset_path", ""),
                        "consumer_slot_index": index,
                        "target_guid": target_guid,
                        "target_file_id": "",
                    })
            replacement = None
            if asset_db and meta_text:
                entry = resolve_material_entry(meta_text, slot.name, asset_db)
                if entry:
                    replacement = material_library.get(str(entry.path)) or by_guid.get(entry.guid)
            if replacement is None and not externally_mapped:
                replacement = by_name.get(slot.name.casefold()) or by_name.get(strip_material_suffix(slot.name).casefold())
            if replacement is not None:
                obj.data.materials[index] = replacement
        # A model can carry externalObjects metadata before Blender has
        # created material slots (for example, a geometry-only FBX). Keep the
        # dependency as unresolved metadata instead of dropping it. It is
        # intentionally limited to the no-slot case so real slot indices are
        # never guessed.
        if scene and external_objects and len(obj.data.materials) == 0:
            for target_guid in external_objects.values():
                if target_guid and asset_db.find_guid(target_guid) is None:
                    capture_dependency(scene, {
                        "dependency_type": "FBX_EXTERNAL_MATERIAL",
                        "consumer_package_id": asset_db.source_package_id,
                        "consumer_asset_path": obj.get("unity_asset_path", obj.get("unity_source_fbx", "")),
                        "consumer_object_path": obj.get("unity_asset_path", ""),
                        "consumer_slot_index": 0,
                        "target_guid": target_guid,
                        "target_file_id": "",
                    })


def _append_renderer_provenance(obj, member_id, source_prefab_guid, renderer_file_id,
                                 game_object_file_id, renderer_type, mesh_ref,
                                 slots, renderer_source_kind="", mapping_confidence="") -> None:
    """Persist the semantic renderer-to-object join used for assignment/audit."""
    try:
        payload = json.loads(str(obj.get("_vapb_renderer_bindings", "{}")))
        records = list(payload.get("renderers", []))
    except (TypeError, ValueError, AttributeError):
        records = []
    source_guid = ref_guid(mesh_ref) if isinstance(mesh_ref, dict) else ""
    mesh_file_id = ref_file_id(mesh_ref) if isinstance(mesh_ref, dict) else None
    record = {
        "schema_version": 1,
        "semantic_id": f"v1:{member_id}:{source_prefab_guid}:{renderer_file_id}",
        "member_id": str(member_id or ""),
        "source_prefab_guid": str(source_prefab_guid or "").lower(),
        "renderer_identity_guid": str(source_prefab_guid or "").lower(),
        "source_asset_guid": str(
            obj.get("unity_source_fbx_guid") or source_prefab_guid or ""
        ).lower(),
        "renderer_source_kind": str(renderer_source_kind or ""),
        "mapping_confidence": str(mapping_confidence or ""),
        "renderer_file_id": str(renderer_file_id),
        "game_object_semantic_id": str(obj.get("_vapb_semantic_id", "")),
        "game_object_file_id": str(game_object_file_id or obj.get("unity_prefab_file_id", "")),
        "renderer_type": int(renderer_type or 0),
        "mesh_guid": str(source_guid or "").lower(),
        "mesh_file_id": str(mesh_file_id or ""),
        "material_slots": slots,
    }
    existing = next((item for item in records if item.get("semantic_id") == record["semantic_id"]), None)
    if existing is not None:
        merged = {str(item.get("slot")): item for item in existing.get("material_slots", [])}
        merged.update({str(item.get("slot")): item for item in record["material_slots"]})
        existing.update(record)
        existing["material_slots"] = [merged[key] for key in sorted(merged, key=lambda value: int(value))]
    else:
        records.append(record)
    obj["_vapb_renderer_bindings"] = json.dumps(
        {"schema_version": 1, "renderers": records}, ensure_ascii=False, sort_keys=True
    )


def _renderer_slot_records(references, material_library, asset_db):
    def texture_guid(material, label):
        if material is None or not getattr(material, "node_tree", None):
            return ""
        prefix = f"Unity {label} "
        node = next((item for item in material.node_tree.nodes
                     if item.type == "TEX_IMAGE" and str(item.name).startswith(prefix)), None)
        return str(node.image.get("unity_guid", "")) if node is not None and node.image else ""

    def expected_texture_guid(material, key):
        if material is None:
            return ""
        try:
            normalized = json.loads(str(material.get("unity_normalized", "{}")))
            value = normalized.get(key) or {}
            return str(value.get("guid", ""))
        except (TypeError, ValueError, AttributeError):
            return ""

    result = []
    for index, reference in enumerate(references):
        guid = ref_guid(reference)
        entry = asset_db.find_guid(guid) if guid else None
        material = material_library.get(str(entry.path)) if entry else None
        result.append({
            "slot": index,
            "effective_material_guid": str(guid or "").lower(),
            "effective_material_file_id": str(ref_file_id(reference) or ""),
            "realized_material_guid": str(material.get("unity_material_guid", "")) if material else "",
            "base_color_texture_guid": expected_texture_guid(material, "base_color_tex"),
            "realized_base_color_texture_guid": texture_guid(material, "Base Color"),
            "normal_texture_guid": expected_texture_guid(material, "normal_tex"),
            "realized_normal_texture_guid": texture_guid(material, "Normal"),
        })
    return result


def apply_prefab_materials(prefab: PrefabData, object_map: dict[int, bpy.types.Object], asset_db, material_library, scene=None, imported_objects=None, member_id="") -> None:
    """Follow Prefab Renderer ``m_Materials`` GUIDs into Blender slots."""
    for document in prefab.renderer_documents():
        game_object_id = ref_file_id(document.data.get("m_GameObject"))
        obj = object_map.get(game_object_id)
        if obj is None:
            continue
        targets = [obj]
        if not getattr(obj, "data", None) or not hasattr(obj.data, "materials"):
            # A wrapper or empty owner is not proof of the native FBX
            # realization. Do not select a descendant or package-wide unique
            # mesh without an explicit semantic bridge.
            targets = []
        targets = [candidate for candidate in targets if getattr(candidate, "data", None) and hasattr(candidate.data, "materials")]
        if not targets:
            continue
        references = document.data.get("m_Materials")
        if references is None:
            references = [document.data.get("m_Material")]
        if not isinstance(references, list):
            references = [references]
        slots = _renderer_slot_records(references, material_library, asset_db)
        mesh_ref = document.data.get("m_Mesh")
        mesh_guid = ref_guid(mesh_ref) if isinstance(mesh_ref, dict) else ""
        direct_mesh = isinstance(mesh_ref, dict) and bool(mesh_ref.get("guid"))
        renderer_identity_guid = str(prefab.asset_guid if direct_mesh and prefab.asset_guid else mesh_guid).lower()
        renderer_source_kind = "PREFAB_LOCAL" if direct_mesh and prefab.asset_guid else "MODEL_SOURCE"
        for target in targets:
            _append_renderer_provenance(
                target,
                member_id or target.get("unity_composition_member_id", ""),
                renderer_identity_guid,
                document.file_id,
                game_object_id,
                document.class_id,
                mesh_ref,
                slots,
                renderer_source_kind,
                str(target.get("_vapb_mapping_confidence", "UNKNOWN")),
            )
        for index, reference in enumerate(references):
            guid = ref_guid(reference)
            entry = asset_db.find_guid(guid)
            material = material_library.get(str(entry.path)) if entry else None
            if material is None:
                if scene and guid:
                    capture_dependency(scene, {
                        "dependency_type": "PREFAB_RENDERER_MATERIAL",
                        "consumer_package_id": asset_db.source_package_id,
                        "consumer_asset_path": obj.get("unity_asset_path", ""),
                        "consumer_object_path": obj.get("unity_asset_path", ""),
                        "consumer_game_object_file_id": str(game_object_id),
                        "consumer_slot_index": index,
                        "target_guid": guid,
                        "target_file_id": ref_file_id(reference) or "",
                        "target_file_id_raw": reference.get("fileID") if isinstance(reference, dict) else None,
                        "source_prefab_asset_path": obj.get("unity_asset_path", ""),
                    })
                continue
            for target in targets:
                while len(target.data.materials) <= index:
                    target.data.materials.append(None)
                _assign_object_material(target, index, material)


def apply_prefab_modification_materials(prefab: PrefabData, source_to_member, asset_db, material_library, scene=None, member_id="") -> None:
    """Capture overrides that still require an occurrence-scoped realization.

    A source Renderer localID cannot be compared with an Object's GameObject
    localID. The scoped projection/confirmation path performs actual assignment.
    This compatibility entry point records dependencies without guessing a join.
    """
    if scene is None:
        return
    for override in prefab.modification_materials():
        if override.get("material_guid"):
            capture_dependency(scene, {
                "dependency_type": "PREFAB_RENDERER_MATERIAL",
                "consumer_package_id": asset_db.source_package_id,
                "consumer_asset_path": str(prefab.path),
                "consumer_object_path": str(prefab.path),
                "consumer_file_id": str(override['target_file_id']),
                "consumer_prefab_instance_file_id": str(override['prefab_instance_file_id']),
                "requires_occurrence_binding": True,
                "consumer_slot_index": int(override["slot_index"]),
                "target_guid": str(override["material_guid"]),
                "target_file_id": str(override.get("material_file_id", "")),
                "target_file_id_raw": override.get("material_file_id_raw"),
                "source_prefab_asset_path": str(prefab.path),
            })


def _assign_object_material(obj, index: int, material) -> None:
    """Assign renderer state without mutating a shared Mesh material table."""
    if not getattr(obj, "data", None) or not hasattr(obj.data, "materials"):
        return
    while len(obj.data.materials) <= index:
        obj.data.materials.append(None)
    # Renderer state belongs to the Object occurrence, even when a current
    # composition has only one member. Never use the shared Mesh as a fallback.
    slot = obj.material_slots[index]
    slot.link = "OBJECT"
    slot.material = material
