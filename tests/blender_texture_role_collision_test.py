"""One synthetic Texture used by two Material roles must retain both bindings."""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_material_texture_dependencies, load_dependency_registry, resolve_scene_dependencies,
)
from unitypackage_blender_importer.blender.import_outcome import scene_import_outcome  # noqa: E402


PACKAGE = "synthetic-package"
MATERIAL = "a" * 32
TEXTURE = "b" * 32


def semantic_state():
    material = bpy.data.materials["DualRoleMaterial"]
    records = load_dependency_registry(bpy.context.scene)["dependencies"]
    relevant = [record for record in records if record["dependency_type"] == "MATERIAL_TEXTURE"]
    assert len(relevant) == 2, relevant
    assert {record["texture_label"] for record in relevant} == {"Base Color", "Emission"}, relevant
    assert all(record["target_guid"] == TEXTURE and record["binding_status"] == "BOUND"
               for record in relevant), relevant
    nodes = material.node_tree.nodes
    base = nodes.get("Unity Base Color DualRoleMaterial")
    emission = nodes.get("Unity Emission DualRoleMaterial")
    assert base is not None and emission is not None
    assert base.image is emission.image is bpy.data.images["SharedRoleImage"]
    return {
        "roles": sorted(record["texture_label"] for record in relevant),
        "bindings": sorted((record["texture_label"], record["status"], record["provider_status"],
                            record["binding_status"], record["resolved_provider_package_id"],
                            record["applied_texture_state"]) for record in relevant),
        "node_count": len(nodes),
        "image_names": [base.image.name, emission.image.name],
        "material_slots": [slot.material.name if slot.material else None for slot in bpy.data.objects["DualRoleObject"].material_slots],
        "import_outcome_counts": scene_import_outcome(bpy.context.scene)["counts"],
    }


def main():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python script -- create|reopen blend_path")
    phase, blend_path = sys.argv[sys.argv.index("--") + 1:]
    if phase == "create":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        material = bpy.data.materials.new("DualRoleMaterial")
        material.use_nodes = True
        material["unity_material_guid"] = MATERIAL
        material["unity_material_path"] = "Assets/Synthetic/DualRole.mat"
        material["unity_source_package_id"] = PACKAGE
        material["unity_props"] = json.dumps({"textures": {
            "_MainTex": {"guid": TEXTURE, "file_id": 2800000},
            "_EmissionMap": {"guid": TEXTURE, "file_id": 2800000},
        }})
        mesh = bpy.data.meshes.new("DualRoleMesh")
        obj = bpy.data.objects.new("DualRoleObject", mesh)
        bpy.context.scene.collection.objects.link(obj)
        mesh.materials.append(material)
        image = bpy.data.images.new("SharedRoleImage", 1, 1)
        image["unity_guid"] = TEXTURE
        image["unity_source_package_id"] = PACKAGE
        capture_material_texture_dependencies(bpy.context.scene, [material])
        resolve_scene_dependencies(bpy.context.scene)
        first = semantic_state()
        assert semantic_state() == first
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("DUAL_ROLE_CREATE_PASS")
    elif phase == "reopen":
        baseline = semantic_state()
        for _ in range(3):
            resolve_scene_dependencies(bpy.context.scene)
            assert semantic_state() == baseline
        print("DUAL_ROLE_REOPEN_PASS")
    else:
        raise AssertionError(phase)


if __name__ == "__main__":
    main()
