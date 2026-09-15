"""Summarize visual graph and image data before BUG-003 changes."""

from pathlib import Path
import json
import bpy

OUT = Path(__file__).with_name("before_visual_summary.json")


def linked(node, socket_name):
    socket = node.inputs.get(socket_name)
    if socket is None:
        return []
    return [{"node": link.from_node.name, "socket": link.from_socket.name} for link in socket.links]


def one(material):
    nodes = material.node_tree.nodes if material.node_tree else []
    links = material.node_tree.links if material.node_tree else []
    bsdf = nodes.get("Principled BSDF")
    output = nodes.get("Material Output")
    textures = []
    for node in nodes:
        if node.type != "TEX_IMAGE" or node.image is None:
            continue
        image = node.image
        sample = []
        try:
            sample = list(image.pixels[:4])
        except (RuntimeError, TypeError):
            pass
        textures.append({"node": node.name, "image": image.name, "guid": image.get("unity_guid", ""), "filepath": image.filepath, "colorspace": image.colorspace_settings.name, "size": list(image.size), "sample": sample, "packed": image.packed_file is not None})
    mixes = []
    for node in nodes:
        if node.type == "MIX_RGB":
            mixes.append({"name": node.name, "blend_type": node.blend_type, "inputs": {socket.name: list(socket.default_value) if hasattr(socket.default_value, "__len__") and not isinstance(socket.default_value, str) else socket.default_value for socket in node.inputs}, "links": [{"from": link.from_node.name, "from_socket": link.from_socket.name, "to_socket": link.to_socket.name} for link in links if link.to_node == node]})
    return {
        "name": material.name,
        "guid": material.get("unity_material_guid", ""),
        "path": material.get("unity_material_path", ""),
        "family": material.get("unity_shader_family", ""),
        "use_nodes": material.use_nodes,
        "textures": textures,
        "mixes": mixes,
        "base_color_inputs": linked(bsdf, "Base Color") if bsdf else [],
        "alpha_inputs": linked(bsdf, "Alpha") if bsdf else [],
        "normal_inputs": linked(bsdf, "Normal") if bsdf else [],
        "surface_inputs": linked(output, "Surface") if output else [],
        "link_count": len(links),
    }


materials = [one(material) for material in bpy.data.materials if material.get("unity_material_guid")]
result = {
    "materials_total": len(materials),
    "materials_with_nodes": sum(item["use_nodes"] for item in materials),
    "materials_with_surface_shader": sum(bool(item["surface_inputs"]) for item in materials),
    "materials_with_base_texture": sum(bool(item["textures"]) for item in materials),
    "materials_with_basecolor_link": sum(bool(item["base_color_inputs"]) for item in materials),
    "materials_with_missing_image": sum(any(not item["size"] or item["size"] == [0, 0] for item in material["textures"]) for material in materials),
    "materials_with_broken_surface_link": sum(not item["surface_inputs"] for item in materials),
    "representatives": {name: next((item for item in materials if item["name"] == name), None) for name in ("SyntheticMaterial", "Body", "Hair")},
    "materials": materials,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("BUG003_BEFORE_SUMMARY=" + json.dumps({key: result[key] for key in result if key != "materials"}, ensure_ascii=False), flush=True)
bpy.ops.wm.quit_blender()
