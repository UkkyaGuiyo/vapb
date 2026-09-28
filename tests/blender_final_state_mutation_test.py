"""Public synthetic FBX variants for Unity final-state identity rejection tests."""

import json
from pathlib import Path
import sys
import tarfile

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.fbx_export import export_fbx


mode, package_name, output_name = sys.argv[sys.argv.index("--") + 1:][:3]
assert mode in {"missing", "duplicate", "renamed"}
with tarfile.open(package_name) as archive:
    member = next(item for item in archive.getmembers() if item.name.endswith("/pathname")
                  and archive.extractfile(item).read() == b"Assets/VAPBExport/manifest.json")
    manifest = json.load(archive.extractfile(member.name.split("/")[0] + "/asset"))
export_id = manifest["reference_rebind_tasks"][0]["export_object_id"]
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert len(meshes) == 1
mesh = meshes[0]
for obj in bpy.context.scene.objects:
    obj.select_set(False)
if mode != "missing":
    mesh["_vapb_export_object_id"] = export_id
if mode == "duplicate":
    other = mesh.copy()
    other.data = mesh.data.copy()
    bpy.context.scene.collection.objects.link(other)
    other["_vapb_export_object_id"] = export_id
    other.select_set(True)
if mode == "renamed":
    mesh.name = "Name changed after Export ID assignment"
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
export_fbx(Path(output_name))
data = Path(output_name).read_bytes()
assert (export_id.encode() in data) == (mode != "missing")
print("FINAL_STATE_MUTATION_READY", mode)
