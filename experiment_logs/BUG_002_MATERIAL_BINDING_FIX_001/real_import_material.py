"""Foreground real-package material identity probe for Blender 5.2.1."""

from pathlib import Path
import json
import sys
import time

import bpy

ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
OUT = Path(__file__).with_name("real_import_material_result.json")
BLEND = Path(__file__).with_name("BUG_002_real_import.blend")
sys.path.insert(0, str(ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as module  # noqa: E402
from unitypackage_blender_importer.unity.material_mapping import parse_external_objects  # noqa: E402

addon.register()
started = time.monotonic()
finished = False


def auto_select(self, context, _event):
    self.prefab_choice = "AUTO"
    return self.execute(context)


module.UNITYPACKAGE_OT_import_prefab.invoke = auto_select


def inspect_scene():
    materials = []
    images = []
    identity_errors = []
    bindings = []
    for material in bpy.data.materials:
        guid = str(material.get("unity_material_guid", ""))
        if not guid:
            continue
        materials.append({"name": material.name, "guid": guid, "path": str(material.get("unity_material_path", ""))})
        try:
            props = json.loads(material.get("unity_props", "{}"))
            texture_guids = {str(value.get("guid", "")).lower() for value in props.get("textures", {}).values() if value.get("guid")}
        except (TypeError, ValueError):
            texture_guids = set()
        for node in material.node_tree.nodes if material.node_tree else []:
            if node.type != "TEX_IMAGE" or node.image is None:
                continue
            image = node.image
            image_guid = str(image.get("unity_guid", "")).lower()
            exists = Path(bpy.path.abspath(image.filepath)).is_file() or image.packed_file is not None
            images.append({"material_guid": guid, "image_guid": image_guid, "filepath": image.filepath, "exists": exists})
            if not image_guid or image_guid not in texture_guids:
                identity_errors.append({"material_guid": guid, "image_guid": image_guid, "reason": "material_texture_guid_mismatch"})
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for index, material in enumerate(obj.data.materials):
            if material is not None and material.get("unity_material_guid"):
                binding = {"object": obj.name, "slot": index, "material_guid": material.get("unity_material_guid"), "material_path": material.get("unity_material_path", "")}
                bindings.append(binding)
                source_fbx = obj.get("unity_source_fbx")
                if source_fbx:
                    try:
                        external = parse_external_objects(Path(str(source_fbx) + ".meta").read_text(encoding="utf-8", errors="replace"))
                        if external and str(binding["material_guid"]).lower() not in {value.lower() for value in external.values()}:
                            identity_errors.append({"object": obj.name, "slot": index, "reason": "fbx_external_object_mismatch", "material_guid": binding["material_guid"]})
                    except OSError:
                        identity_errors.append({"object": obj.name, "slot": index, "reason": "fbx_meta_missing"})
    return {"materials": materials, "images": images, "bindings": bindings, "identity_errors": identity_errors}


def finish_probe():
    global finished
    if finished:
        return None
    if time.monotonic() - started > 240:
        OUT.write_text(json.dumps({"status": "TIMEOUT"}, ensure_ascii=False, indent=2), encoding="utf-8")
        addon.unregister()
        bpy.ops.wm.quit_blender()
        return None
    if not any(obj.type == "MESH" for obj in bpy.data.objects):
        return 0.5
    data = inspect_scene()
    data.update({"status": "PASS" if not data["identity_errors"] and all(image["exists"] for image in data["images"]) else "FAIL", "elapsed_seconds": round(time.monotonic() - started, 3), "objects": len(bpy.data.objects), "meshes": sum(obj.type == "MESH" for obj in bpy.data.objects), "armatures": sum(obj.type == "ARMATURE" for obj in bpy.data.objects), "shape_keys": sum(1 for obj in bpy.data.objects if obj.type == "MESH" and obj.data.shape_keys), "material_count": len(bpy.data.materials), "image_count": len(bpy.data.images), "modal_registered": False, "material_preview_ui": "UNVERIFIED_NO_COMPUTER_USE"})
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("BUG002_REAL_IMPORT=" + json.dumps(data, ensure_ascii=False), flush=True)
    finished = True
    addon.unregister()
    bpy.ops.wm.quit_blender()
    return None


result = bpy.ops.import_scene.unitypackage(filepath=str(PACKAGE), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=True)
print(f"BUG002_INITIAL_RESULT={result}", flush=True)
finish_probe()
