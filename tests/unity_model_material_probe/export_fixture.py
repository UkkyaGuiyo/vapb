"""Normal production export of an already reconstructed first-party three-slot fixture.
Run with Blender --background --python this_file -- --addon-parent ... --edited-blend ... --output ...
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--addon-parent", required=True)
parser.add_argument("--edited-blend", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
sys.path.insert(0, str(Path(args.addon_parent).resolve()))
import bpy
import unitypackage_blender_importer as addon

addon.register()
blend = Path(args.edited_blend).resolve()
output = Path(args.output).resolve()
assert not output.exists(), "Use a new output path"
bpy.ops.wm.open_mainfile(filepath=str(blend))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"
          and o.get("_vapb_fbx_realization_id") and o.get("_vapb_root_context_id")
          and any(m.type == "ARMATURE" for m in o.modifiers)]
assert len(meshes) == 1, "Fixture must contain exactly one reconstructed selected skin"
mesh = meshes[0]
assert len(mesh.material_slots) == 3
mesh.data.calc_loop_triangles()
counts = Counter(mesh.data.polygons[t.polygon_index].material_index for t in mesh.data.loop_triangles)
assert len(set(counts[i] for i in range(3))) == 3 and all(counts[i] > 0 for i in range(3))
references = []
for slot in mesh.material_slots:
    material = slot.material
    assert material is not None and material.get("unity_material_guid")
    references.append({"guid": material["unity_material_guid"],
                       "file_id": str(material["unity_material_file_id"])})
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
before = [(m.as_pointer(), m.name, tuple(m.diffuse_color)) for m in bpy.data.materials]
blend_hash = hashlib.sha256(blend.read_bytes()).hexdigest()
assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output)) == {"FINISHED"}
assert before == [(m.as_pointer(), m.name, tuple(m.diffuse_color)) for m in bpy.data.materials]
assert blend_hash == hashlib.sha256(blend.read_bytes()).hexdigest()
expectation = {"current_material_refs": references,
               "blender_triangle_slot_counts": [counts[i] for i in range(3)],
               "saved_blend_sha256": blend_hash,
               "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
output.with_suffix(".expectation.json").write_text(json.dumps(expectation, indent=2), encoding="utf-8")
print("PUBLIC_MODEL_MATERIAL_EXPORT_OK")
