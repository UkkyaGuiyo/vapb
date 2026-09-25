"""Generate a synthetic Blender FBX using the public VAPB export preset."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def build_scene() -> tuple[object, object]:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
    mesh_object = bpy.context.object
    mesh_object.name = "VAPBValidationBody"
    mesh_object["_vapb_semantic_id"] = "synthetic/body"
    mesh_object.data.materials.append(bpy.data.materials.new("VAPBValidationMaterialA"))
    mesh_object.data.materials.append(bpy.data.materials.new("VAPBValidationMaterialB"))
    mesh_object.data.uv_layers.new(name="UVMap")
    mesh_object.shape_key_add(name="Basis")
    smile = mesh_object.shape_key_add(name="Smile")
    smile.data[0].co.x += 0.25

    armature_data = bpy.data.armatures.new("VAPBValidationArmature")
    armature_object = bpy.data.objects.new("VAPBValidationArmature", armature_data)
    armature_object["_vapb_semantic_id"] = "synthetic/armature"
    bpy.context.scene.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bone = armature_data.edit_bones.new("RenamedRoot")
    bone.head = (0, 0, 0)
    bone.tail = (0, 0, 1)
    bpy.ops.object.mode_set(mode="OBJECT")

    group = mesh_object.vertex_groups.new(name="RenamedRoot")
    group.add(list(range(len(mesh_object.data.vertices))), 1.0, "REPLACE")
    modifier = mesh_object.modifiers.new(name="VAPBValidationArmature", type="ARMATURE")
    modifier.object = armature_object
    mesh_object.select_set(True)
    bpy.context.view_layer.objects.active = armature_object
    return mesh_object, armature_object


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) not in {1, 2}:
        raise SystemExit("usage: blender ... -- blender_export_probe.py -- OUTPUT.fbx [vertex]")
    output = Path(args[0]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    mesh_object, armature_object = build_scene()
    if len(args) == 2 and args[1] == "vertex":
        mesh_object.data.vertices[0].co.x += 0.5
    before = (mesh_object.name, armature_object.name, len(bpy.data.objects), len(bpy.data.meshes))
    from unitypackage_blender_importer.export.fbx_export import export_fbx

    export_fbx(output, bpy_module=bpy, selected_only=True)
    after = (mesh_object.name, armature_object.name, len(bpy.data.objects), len(bpy.data.meshes))
    assert before == after, (before, after)
    assert output.is_file() and output.stat().st_size > 0
    print("BLENDER_EXPORT_EXECUTION_VALIDATED")
    print(f"FBX={output}")
    print(f"BYTES={output.stat().st_size}")


main()
