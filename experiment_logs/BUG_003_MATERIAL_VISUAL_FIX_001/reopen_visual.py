"""Reopen VIS-009 probe for the BUG-003 real import blend."""
from pathlib import Path
import json
import bpy

ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
before = json.loads((ROOT / "real_import_visual_result.json").read_text(encoding="utf-8"))
def binding_signatures():
    return sorted((obj.name, index, str(material.get("unity_material_guid"))) for obj in bpy.data.objects if obj.type == "MESH" for index, material in enumerate(obj.data.materials) if material and material.get("unity_material_guid"))

def graph_signature(material):
    nodes = material.node_tree.nodes if material.node_tree else []
    links = material.node_tree.links if material.node_tree else []
    return {"nodes": [list(item) for item in sorted((node.name, node.type, str(node.image.get("unity_guid", "")) if node.type == "TEX_IMAGE" and node.image else "") for node in nodes)], "links": [list(item) for item in sorted((link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name) for link in links)]}
rows = []
for material in bpy.data.materials:
    if not material.get("unity_material_guid"):
        continue
    nodes = material.node_tree.nodes if material.node_tree else []
    base = next((n for n in nodes if n.type == "TEX_IMAGE" and n.name.startswith("Unity Base Color ")), None)
    vector = base.inputs.get("Vector") if base else None
    rows.append({"guid": str(material.get("unity_material_guid")), "base_image_guid": str(base.image.get("unity_guid", "")) if base and base.image else "", "uv_link": bool(vector and vector.is_linked and vector.links[0].from_node.type == "TEX_COORD")})
bound_guids = {str(material.get("unity_material_guid")) for obj in bpy.data.objects if obj.type == "MESH" for material in obj.data.materials if material and material.get("unity_material_guid")}
before_rows = {r["guid"]: (r.get("base_image_guid", ""), r.get("uv_link", False)) for r in before["materials"] if r["guid"] in bound_guids}
after_rows = {r["guid"]: (r["base_image_guid"], r["uv_link"]) for r in rows if r["guid"] in bound_guids}
binding_after = sum(1 for obj in bpy.data.objects if obj.type == "MESH" for material in obj.data.materials if material and material.get("unity_material_guid"))
result = {"status": "PASS" if rows and binding_after == before.get("material_slot_bindings", 0) and before_rows == after_rows else "FAIL", "materials": len(rows), "bound_materials": len(bound_guids), "binding_signatures_before": before.get("material_slot_bindings", 0), "binding_signatures_after": binding_after, "material_graph_comparison": "MATCH" if before_rows == after_rows else "MISMATCH"}
result["binding_signature_comparison"] = "MATCH" if binding_signatures() == [tuple(item) for item in before.get("binding_signatures", [])] else "MISMATCH"
after_graphs = {str(material.get("unity_material_guid")): graph_signature(material) for material in bpy.data.materials if material.get("unity_material_guid") and material.node_tree}
before_graphs = {str(guid): value for guid, value in before.get("graph_signatures", {}).items() if str(guid) in bound_guids}
result["graph_signature_comparison"] = "MATCH" if all(before_graphs.get(guid) == after_graphs.get(guid) for guid in before_graphs) else "MISMATCH"
if result["binding_signature_comparison"] != "MATCH" or result["graph_signature_comparison"] != "MATCH":
    result["status"] = "FAIL"
(ROOT / "reopen_visual_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("BUG003_REOPEN=" + json.dumps(result, ensure_ascii=False), flush=True)
bpy.ops.wm.quit_blender()
