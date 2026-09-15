"""Convert normalized Unity materials into editable Blender node graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import bpy  # type: ignore

from ..unity.material_mapping import resolve_material_entry, strip_material_suffix
from ..unity.material_model import NormalizedMaterial, UnityMaterialData, UnityTextureRef
from ..unity.material_parser import parse_material
from ..unity.prefab_parser import PrefabData, ref_file_id, ref_guid
from ..unity.profiles.base import normalize_material
from .texture_loader import load_texture_by_guid


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
    material["unity_material_path"] = data.unity_path
    if source_package_id:
        material["unity_source_package_id"] = source_package_id
    material["unity_material_name"] = data.name
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
                _set_input(alpha, 1, normalized.alpha_cutoff)
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
            _set_input(invert, 0, 1.0)
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
        for index, slot in enumerate(obj.data.materials):
            if slot is None:
                continue
            replacement = None
            if asset_db and meta_text:
                entry = resolve_material_entry(meta_text, slot.name, asset_db)
                if entry:
                    replacement = material_library.get(str(entry.path)) or by_guid.get(entry.guid)
            if replacement is None:
                replacement = by_name.get(slot.name.casefold()) or by_name.get(strip_material_suffix(slot.name).casefold())
            if replacement is not None:
                obj.data.materials[index] = replacement


def apply_prefab_materials(prefab: PrefabData, object_map: dict[int, bpy.types.Object], asset_db, material_library) -> None:
    """Follow Prefab Renderer ``m_Materials`` GUIDs into Blender slots."""
    for document in prefab.renderer_documents():
        game_object_id = ref_file_id(document.data.get("m_GameObject"))
        obj = object_map.get(game_object_id)
        if obj is None or not getattr(obj, "data", None) or not hasattr(obj.data, "materials"):
            continue
        references = document.data.get("m_Materials")
        if references is None:
            references = [document.data.get("m_Material")]
        if not isinstance(references, list):
            references = [references]
        for index, reference in enumerate(references):
            guid = ref_guid(reference)
            entry = asset_db.find_guid(guid)
            material = material_library.get(str(entry.path)) if entry else None
            if material is None:
                continue
            while len(obj.data.materials) <= index:
                obj.data.materials.append(None)
            obj.data.materials[index] = material
