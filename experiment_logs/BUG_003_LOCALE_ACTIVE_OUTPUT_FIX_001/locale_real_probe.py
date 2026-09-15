"""Real-package locale and active-output probe for Blender 5.2.1."""
from pathlib import Path
import json
import sys
import time
import bpy

ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
locale = args[0] if args else "en_US"
out = Path(__file__).with_name(f"real_{locale}_result.json")
blend = Path(__file__).with_name(f"real_{locale}.blend")
sys.path.insert(0, str(ROOT))

prefs = bpy.context.preferences.view
try:
    prefs.language = locale
except (AttributeError, TypeError, ValueError):
    pass
try:
    prefs.use_translate_new_dataname = True
except AttributeError:
    pass

import unitypackage_blender_importer as addon  # noqa: E402

addon.register()
started = time.monotonic()


def upstream(node, seen=None):
    seen = set() if seen is None else seen
    if node in seen:
        return set()
    seen.add(node)
    result = {node}
    for socket in node.inputs:
        for link in socket.links:
            result |= upstream(link.from_node, seen)
    return result


def probe_material(material):
    nodes = material.node_tree.nodes if material.node_tree else []
    outputs = [node for node in nodes if node.type == "OUTPUT_MATERIAL"]
    principled = [node for node in nodes if node.type == "BSDF_PRINCIPLED"]
    active = [node for node in outputs if getattr(node, "is_active_output", False)]
    active_surface = active[0].inputs.get("Surface") if active else None
    active_sources = upstream(active_surface.links[0].from_node) if active_surface and active_surface.is_linked else set()
    images = [node for node in nodes if node.type == "TEX_IMAGE" and node.image]
    textured_principled = set()
    for node in principled:
        base = node.inputs.get("Base Color")
        if base and base.is_linked:
            textured_principled.add(node)
    return {
        "name": material.name,
        "guid": str(material.get("unity_material_guid", "")),
        "nodes": [{"name": node.name, "label": node.label, "type": node.type, "bl_idname": node.bl_idname, "is_active_output": getattr(node, "is_active_output", None), "location": list(node.location)} for node in nodes],
        "links": [{"from_node": link.from_node.name, "from_type": link.from_node.type, "from_socket": link.from_socket.name, "to_node": link.to_node.name, "to_type": link.to_node.type, "to_socket": link.to_socket.name} for link in material.node_tree.links],
        "principled_count": len(principled),
        "output_count": len(outputs),
        "active_outputs": [node.name for node in active],
        "active_output_count": len(active),
        "active_surface_linked": bool(active_surface and active_surface.is_linked),
        "textured_principled_reaches_active": bool(textured_principled and any(node in active_sources for node in textured_principled)),
        "texture_reaches_active_surface": bool(images and any(node in active_sources for node in images)),
        "image_count": len(images),
        "nodes_get_principled": bool(nodes.get("Principled BSDF")),
        "nodes_get_output": bool(nodes.get("Material Output")),
        "type_lookup_principled": any(node.type == "BSDF_PRINCIPLED" for node in nodes),
        "type_lookup_output": any(node.type == "OUTPUT_MATERIAL" for node in nodes),
    }


def binding_signatures():
    return sorted([obj.name, index, str(material.get("unity_material_guid"))] for obj in bpy.data.objects if obj.type == "MESH" for index, material in enumerate(obj.data.materials) if material and material.get("unity_material_guid"))


def graph_signatures():
    result = {}
    for material in bpy.data.materials:
        guid = str(material.get("unity_material_guid", ""))
        if not guid or not material.node_tree:
            continue
        result[guid] = {"nodes": [list(item) for item in sorted((node.name, node.type, str(node.image.get("unity_guid", "")) if node.type == "TEX_IMAGE" and node.image else "") for node in material.node_tree.nodes)], "links": [list(item) for item in sorted((link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name) for link in material.node_tree.links)]}
    return result


def main():
    result = bpy.ops.import_scene.unitypackage(filepath=str(PACKAGE), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=True)
    if "FINISHED" not in result:
        raise RuntimeError(result)
    rows = [probe_material(material) for material in bpy.data.materials if material.get("unity_material_guid")]
    textured = [row for row in rows if row["image_count"]]
    data = {
        "status": "PASS" if textured and all(row["active_output_count"] == 1 and row["active_surface_linked"] and row["textured_principled_reaches_active"] and row["texture_reaches_active_surface"] for row in textured) else "FAIL",
        "locale": locale,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "material_count": len(rows),
        "textured_materials_total": len(textured),
        "active_output_count": sum(row["active_output_count"] == 1 for row in textured),
        "materials_with_duplicate_output": sum(row["output_count"] > 1 for row in textured),
        "materials_with_duplicate_principled": sum(row["principled_count"] > 1 for row in textured),
        "texture_to_active_surface_pass": sum(row["textured_principled_reaches_active"] for row in textured),
        "texture_origin_to_active_surface_pass": sum(row["texture_reaches_active_surface"] for row in textured),
        "locale_lookup_failures": sum(not row["type_lookup_principled"] or not row["type_lookup_output"] for row in textured),
        "representatives": {name: next((row for row in rows if row["name"] == name), None) for name in ("Face", "Hair", __import__("os").environ["VAPB_PRIVATE_LABEL_1"])},
        "materials": rows,
        "binding_signatures": binding_signatures(),
        "graph_signatures": graph_signatures(),
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LOCALE_RESULT=" + json.dumps(data, ensure_ascii=False), flush=True)
    addon.unregister()
    bpy.ops.wm.quit_blender()


main()
