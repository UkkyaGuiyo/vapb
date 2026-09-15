"""Real-package VIS-001..009 probe for Blender 5.2.1."""
from pathlib import Path
import json
import sys
import time
import bpy

ROOT = Path(r"<LOCAL_PATH>")
PACKAGE = Path(r"<LOCAL_PATH>")
OUT = Path(__file__).with_name("real_import_visual_result.json")
BLEND = Path(__file__).with_name("BUG_003_real_import.blend")
sys.path.insert(0, str(ROOT))
import unitypackage_blender_importer as addon  # noqa: E402

addon.register()

def from_nodes(socket):
    return [link.from_node for link in socket.links] if socket else []

def inspect_materials():
    rows = []
    errors = []
    for material in bpy.data.materials:
        if not material.get("unity_material_guid"):
            continue
        nodes = material.node_tree.nodes if material.node_tree else []
        links = material.node_tree.links if material.node_tree else []
        bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        base = next((n for n in nodes if n.type == "TEX_IMAGE" and n.name.startswith("Unity Base Color ")), None)
        base_mix = next((n for n in nodes if n.type == "MIX_RGB" and n.name.startswith("Unity Base Color Mix ")), None)
        image_nodes = [n for n in nodes if n.type == "TEX_IMAGE" and n.image]
        try:
            props = json.loads(material.get("unity_props", "{}"))
            texture_guids = {str(v.get("guid", "")).lower() for v in props.get("textures", {}).values() if v.get("guid")}
        except (TypeError, ValueError):
            texture_guids = set()
        image_guid = str(base.image.get("unity_guid", "")).lower() if base and base.image else ""
        vector = base.inputs.get("Vector") if base else None
        base_socket = bsdf.inputs.get("Base Color") if bsdf else None
        surface = output.inputs.get("Surface") if output else None
        row = {
            "name": material.name,
            "guid": str(material.get("unity_material_guid")),
            "family": str(material.get("unity_shader_family", "")),
            "use_nodes": bool(material.use_nodes),
            "base_texture": bool(base and base.image),
            "base_image_guid": image_guid,
            "base_image_identity_ok": bool(image_guid and image_guid in texture_guids),
            "base_color_link": bool(from_nodes(base_socket)),
            "base_color_multiply": bool(base_mix and base_mix.blend_type == "MULTIPLY" and base_mix.inputs.get("Color2") and base_mix.inputs["Color2"].is_linked and base_mix.inputs["Color2"].links[0].from_node == base and base_socket and base_socket.is_linked and base_socket.links[0].from_node == base_mix),
            "surface_link": bool(from_nodes(surface)),
            "uv_link": bool(from_nodes(vector) and from_nodes(vector)[0].type == "TEX_COORD"),
            "all_texture_uv_links": bool(image_nodes) and all(n.inputs.get("Vector") and n.inputs["Vector"].is_linked for n in image_nodes),
            "alpha_links": len(from_nodes(bsdf.inputs.get("Alpha"))) if bsdf else 0,
            "node_count": len(nodes),
            "link_count": len(links),
        }
        rows.append(row)
        if row["base_texture"] and not row["base_image_identity_ok"]:
            errors.append({"material": material.name, "reason": "base_texture_guid_mismatch"})
    return rows, errors

def binding_count():
    return sum(1 for obj in bpy.data.objects if obj.type == "MESH" for material in obj.data.materials if material and material.get("unity_material_guid"))

def binding_signatures():
    return sorted([obj.name, index, str(material.get("unity_material_guid"))] for obj in bpy.data.objects if obj.type == "MESH" for index, material in enumerate(obj.data.materials) if material and material.get("unity_material_guid"))

def graph_signatures():
    result = {}
    for material in bpy.data.materials:
        guid = str(material.get("unity_material_guid", ""))
        if not guid or not material.node_tree:
            continue
        result[guid] = {
            "nodes": sorted((node.name, node.type, str(node.image.get("unity_guid", "")) if node.type == "TEX_IMAGE" and node.image else "") for node in material.node_tree.nodes),
            "links": sorted((link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name) for link in material.node_tree.links),
        }
    return result

def finish():
    rows, errors = inspect_materials()
    textured = [row for row in rows if row["base_texture"]]
    data = {
        "status": "PASS" if rows and not errors and all(row["use_nodes"] and row["base_color_link"] and row["base_color_multiply"] and row["surface_link"] and row["uv_link"] and row["all_texture_uv_links"] for row in textured) else "FAIL",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "objects": len(bpy.data.objects),
        "meshes": sum(obj.type == "MESH" for obj in bpy.data.objects),
        "armatures": sum(obj.type == "ARMATURE" for obj in bpy.data.objects),
        "shape_keys": sum(1 for obj in bpy.data.objects if obj.type == "MESH" and obj.data.shape_keys),
        "material_count": len(rows), "image_count": len(bpy.data.images), "material_slot_bindings": binding_count(),
        "identity_errors": errors,
        "binding_signatures": binding_signatures(),
        "graph_signatures": graph_signatures(),
        "stats": {"materials_with_nodes": sum(r["use_nodes"] for r in rows), "materials_with_base_texture": len(textured), "materials_with_basecolor_link": sum(r["base_color_link"] for r in textured), "materials_with_basecolor_multiply": sum(r["base_color_multiply"] for r in textured), "materials_with_surface_link": sum(r["surface_link"] for r in textured), "materials_with_uv_link": sum(r["uv_link"] for r in textured), "materials_with_all_texture_uv_links": sum(r["all_texture_uv_links"] for r in textured), "materials_with_alpha_link": sum(r["alpha_links"] > 0 for r in rows)},
        "representatives": {name: next((r for r in rows if r["name"] == name), None) for name in ("Face", "Hair", "SyntheticMaterial")},
        "materials": rows, "material_preview_ui": "UNVERIFIED_NO_COMPUTER_USE",
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("BUG003_REAL_IMPORT=" + json.dumps(data, ensure_ascii=False), flush=True)
    addon.unregister()
    bpy.ops.wm.quit_blender()

started = time.monotonic()
result = bpy.ops.import_scene.unitypackage(filepath=str(PACKAGE), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=True)
print(f"BUG003_INITIAL_RESULT={result}", flush=True)
if "FINISHED" not in result:
    raise RuntimeError(result)
finish()
