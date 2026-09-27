"""Synthetic non-colliding provider order must not alter final Texture binding."""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_material_texture_dependencies, load_dependency_registry, resolve_scene_dependencies,
)


TEXTURE = "b" * 32


def create_consumer():
    material = bpy.data.materials.new("OrderConsumer")
    material.use_nodes = True
    material["unity_material_guid"] = "a" * 32
    material["unity_material_path"] = "Assets/Synthetic/Order.mat"
    material["unity_source_package_id"] = "consumer-package"
    material["unity_props"] = json.dumps({"textures": {
        "_MainTex": {"guid": TEXTURE, "file_id": 2800000},
    }})
    mesh = bpy.data.meshes.new("OrderMesh")
    obj = bpy.data.objects.new("OrderObject", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material)
    capture_material_texture_dependencies(bpy.context.scene, [material])


def create_provider(guid=TEXTURE):
    image = bpy.data.images.new("OrderProvider", 1, 1)
    image["unity_guid"] = guid
    image["unity_source_package_id"] = "provider-package"


def state():
    row, = load_dependency_registry(bpy.context.scene)["dependencies"]
    material = bpy.data.materials["OrderConsumer"]
    image = material.node_tree.nodes["Unity Base Color OrderConsumer"].image
    return (row["status"], row["provider_status"], row["binding_status"],
            row["resolved_provider_package_id"], row["texture_label"],
            image.get("unity_guid"), len(material.node_tree.nodes))


def run(provider_first):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if provider_first:
        create_provider()
        create_consumer()
    else:
        create_consumer()
        resolve_scene_dependencies(bpy.context.scene)
        create_provider()
    resolve_scene_dependencies(bpy.context.scene)
    baseline = state()
    assert baseline[0:3] == ("RESOLVED_CROSS_PACKAGE", "RESOLVED_CROSS_PACKAGE", "BOUND")
    create_provider("c" * 32)
    resolve_scene_dependencies(bpy.context.scene)
    assert state() == baseline, "Unrelated non-colliding provider changed the binding"
    return baseline


assert run(False) == run(True)
print("TEXTURE_PROVIDER_ORDER_AND_UNRELATED_PROVIDER_PASS")
