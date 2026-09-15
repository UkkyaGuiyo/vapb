"""Isolated reproduction of the pre-fix name lookup under Japanese UI."""
from pathlib import Path
import json
import bpy

bpy.context.preferences.view.language = "ja_JP"
bpy.context.preferences.view.use_translate_new_dataname = True
material = bpy.data.materials.new("Legacy Japanese Reproduction")
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
bsdf0 = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
output0 = next(node for node in nodes if node.type == "OUTPUT_MATERIAL")
links.new(bsdf0.outputs["BSDF"], output0.inputs["Surface"])

# Exact pre-fix lookup pattern used by material_builder.py.
bsdf = nodes.get("Principled BSDF") or nodes.new("ShaderNodeBsdfPrincipled")
output = nodes.get("Material Output") or nodes.new("ShaderNodeOutputMaterial")
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
data = {
    "locale": "ja_JP",
    "nodes_get_principled": bool(nodes.get("Principled BSDF")),
    "nodes_get_output": bool(nodes.get("Material Output")),
    "principled_count": sum(node.type == "BSDF_PRINCIPLED" for node in nodes),
    "output_count": sum(node.type == "OUTPUT_MATERIAL" for node in nodes),
    "active_outputs": [node.name for node in nodes if node.type == "OUTPUT_MATERIAL" and node.is_active_output],
    "nodes": [{"name": node.name, "type": node.type, "is_active_output": getattr(node, "is_active_output", None)} for node in nodes],
    "links": [{"from": link.from_node.name, "to": link.to_node.name, "to_socket": link.to_socket.name} for link in links],
}
Path(__file__).with_name("legacy_ja_JP_result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(data, ensure_ascii=False), flush=True)
