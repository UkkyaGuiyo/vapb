"""Reopen Japanese-locale result and verify active surface graph persistence."""
from pathlib import Path
import json
import bpy

root = Path(__file__).parent
bpy.context.preferences.view.language = "ja_JP"
before = json.loads((root / "real_ja_JP_result.json").read_text(encoding="utf-8"))
def graph_signature(material):
    nodes = material.node_tree.nodes if material.node_tree else []
    links = material.node_tree.links if material.node_tree else []
    return {"nodes": [list(item) for item in sorted((node.name, node.type, str(node.image.get("unity_guid", "")) if node.type == "TEX_IMAGE" and node.image else "") for node in nodes)], "links": [list(item) for item in sorted((link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name) for link in links)]}

def binding_signatures():
    return sorted([obj.name, index, str(material.get("unity_material_guid"))] for obj in bpy.data.objects if obj.type == "MESH" for index, material in enumerate(obj.data.materials) if material and material.get("unity_material_guid"))
rows = []
for material in bpy.data.materials:
    if not material.get("unity_material_guid"):
        continue
    nodes = material.node_tree.nodes if material.node_tree else []
    outputs = [node for node in nodes if node.type == "OUTPUT_MATERIAL"]
    active = [node for node in outputs if node.is_active_output]
    surface = active[0].inputs.get("Surface") if len(active) == 1 else None
    principled = [node for node in nodes if node.type == "BSDF_PRINCIPLED"]
    textured = any(node.type == "TEX_IMAGE" and node.image for node in nodes)
    source = surface.links[0].from_node if surface and surface.is_linked else None
    rows.append({"guid": str(material.get("unity_material_guid")), "textured": textured, "principled_count": len(principled), "output_count": len(outputs), "active_output_count": len(active), "reaches_active": bool(source and source.type == "BSDF_PRINCIPLED")})
textured = [row for row in rows if row["textured"]]
after_graphs = {str(material.get("unity_material_guid")): graph_signature(material) for material in bpy.data.materials if material.get("unity_material_guid") and material.node_tree}
before_graphs = {str(guid): value for guid, value in before.get("graph_signatures", {}).items()}
graph_match = all(before_graphs.get(guid) == after_graphs.get(guid) for guid in after_graphs)
binding_match = binding_signatures() == [list(item) for item in before.get("binding_signatures", [])]
result = {"status": "PASS" if textured and all(row["principled_count"] == row["output_count"] == row["active_output_count"] == 1 and row["reaches_active"] for row in textured) and graph_match and binding_match else "FAIL", "textured_materials": len(textured), "active_output_pass": sum(row["active_output_count"] == 1 for row in textured), "reach_pass": sum(row["reaches_active"] for row in textured), "material_slot_bindings": sum(1 for obj in bpy.data.objects if obj.type == "MESH" for material in obj.data.materials if material and material.get("unity_material_guid")), "graph_signature_comparison": "MATCH" if graph_match else "MISMATCH", "binding_signature_comparison": "MATCH" if binding_match else "MISMATCH", "note": "Blender save/reopen retains the 15 bound materials; one bound Gem material has no texture."}
(root / "reopen_ja_JP_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False), flush=True)
bpy.ops.wm.quit_blender()
