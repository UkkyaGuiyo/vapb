"""Dump one real Material graph before BUG-003 changes."""

from pathlib import Path
import json
import bpy

OUT = Path(__file__).with_name("before_sample_garment_graph.json")
TARGETS = ("SyntheticMaterial", "Body", "Hair")


def dump(material):
    nodes = []
    for node in material.node_tree.nodes if material.node_tree else []:
        item = {"type": node.type, "name": node.name, "label": node.label}
        if node.type == "TEX_IMAGE" and node.image:
            item["image"] = {"name": node.image.name, "filepath": node.image.filepath, "unity_guid": node.image.get("unity_guid", "")}
        if node.type == "BSDF_PRINCIPLED":
            item["inputs"] = {socket.name: list(socket.default_value) if hasattr(socket.default_value, "__len__") and not isinstance(socket.default_value, str) else socket.default_value for socket in node.inputs if socket.name in {"Base Color", "Alpha", "Roughness", "Metallic", "Normal", "Emission Color"}}
        nodes.append(item)
    links = [{"from_node": link.from_node.name, "from_socket": link.from_socket.name, "to_node": link.to_node.name, "to_socket": link.to_socket.name} for link in material.node_tree.links] if material.node_tree else []
    return {"name": material.name, "unity_material_guid": material.get("unity_material_guid", ""), "unity_material_path": material.get("unity_material_path", ""), "unity_shader_family": material.get("unity_shader_family", ""), "unity_normalized": material.get("unity_normalized", ""), "unity_props": material.get("unity_props", ""), "use_nodes": material.use_nodes, "nodes": nodes, "links": links}


selected = next((bpy.data.materials.get(name) for name in TARGETS if bpy.data.materials.get(name)), None)
if selected is None:
    raise RuntimeError(f"No representative material found: {TARGETS}")
result = dump(selected)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("BUG003_BEFORE=" + json.dumps(result, ensure_ascii=False), flush=True)
bpy.ops.wm.quit_blender()
