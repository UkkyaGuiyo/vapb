"""Create edited.blend from an existing first-party three-slot direct source package."""
import argparse
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--addon-parent", required=True)
parser.add_argument("--source-package", required=True)
parser.add_argument("--work-dir", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
sys.path.insert(0, str(Path(args.addon_parent).resolve()))
import bpy
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from unitypackage_blender_importer.unity.yaml_parser import parse_unity_yaml

work = Path(args.work_dir).resolve()
work.mkdir(parents=True, exist_ok=True)
source = Path(args.source_package).resolve()
addon.register()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
assert bpy.ops.import_scene.unitypackage(filepath=str(source), import_mode="RECONSTRUCT",
    prefab_choice="AUTO", source_storage_directory=str(work / "Sources")) == {"FINISHED"}
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"
          and o.get("_vapb_fbx_realization_id") and o.get("_vapb_root_context_id")
          and any(m.type == "ARMATURE" for m in o.modifiers)]
assert len(meshes) == 1
mesh = meshes[0]
assets = RawAssetRepository(source).read_all()
renderers = [document for asset in assets if asset.pathname.endswith(".prefab")
             for document in parse_unity_yaml(asset.asset_bytes.decode()) if document.class_id == 137]
assert len(renderers) == 1
references = renderers[0].data["m_Materials"]
assert len(references) == len(mesh.material_slots) == 3
# Fixture setup uses serialized GUID/fileID/package identity, never Material names.
for index, reference in enumerate(references):
    materials = [m for m in bpy.data.materials
                 if m.get("unity_material_guid") == reference["guid"]
                 and str(m.get("unity_material_file_id")) == str(reference["fileID"])
                 and m.get("unity_source_package_id") == mesh["unity_source_package_id"]]
    assert len(materials) == 1
    mesh.material_slots[index].link = "OBJECT"
    mesh.material_slots[index].material = materials[0]
mesh.data = mesh.data.copy()
mesh.data.vertices[0].co.x += 0.002
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.wm.save_as_mainfile(filepath=str(work / "Edited.blend"))
print("PUBLIC_MODEL_MATERIAL_FIXTURE_OK")
