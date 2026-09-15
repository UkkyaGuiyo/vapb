"""Reopen and verify persisted material/texture identity in Blender 5.2.1."""

from pathlib import Path
import json
import bpy

BLEND = Path(__file__).with_name("BUG_002_real_import.blend")
OUT = Path(__file__).with_name("reopen_material_result.json")


def probe():
    materials = [str(m.get("unity_material_guid", "")) for m in bpy.data.materials if m.get("unity_material_guid")]
    images = [str(i.get("unity_guid", "")) for i in bpy.data.images if i.get("unity_guid")]
    bindings = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for index, material in enumerate(obj.data.materials):
            if material and material.get("unity_material_guid"):
                bindings.append({"object": obj.name, "slot": index, "guid": material.get("unity_material_guid")})
    before = json.loads(Path(__file__).with_name("real_import_material_result.json").read_text(encoding="utf-8"))
    before_bindings = sorted((item["object"], item["slot"], item["material_guid"]) for item in before.get("bindings", []))
    after_bindings = sorted((item["object"], item["slot"], item["guid"]) for item in bindings)
    result = {"status": "PASS" if materials and images and bindings and before_bindings == after_bindings else "FAIL", "materials": len(materials), "images": len(images), "bindings": len(bindings), "binding_comparison": "MATCH" if before_bindings == after_bindings else "MISMATCH", "material_guids": materials, "image_guids": images}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("BUG002_REOPEN=" + json.dumps(result, ensure_ascii=False), flush=True)
    bpy.ops.wm.quit_blender()
    return None


probe()
