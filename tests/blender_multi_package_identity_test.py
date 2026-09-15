"""Blender 5.2.1 smoke test for package-scoped custom properties and registry."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
sys.path.insert(0, str(ROOT))


def main() -> None:
    from unitypackage_blender_importer.blender.identity_registry import (
        load_scene_registry,
        register_datablocks,
        register_package,
    )
    from unitypackage_blender_importer.unity.identity import (
        CROSS_PACKAGE_GUID_COLLISION,
        CROSS_PACKAGE_PATH_COLLISION,
    )

    scene = bpy.context.scene
    scene.pop("unitypackage_identity_registry", None)
    package_a = "sha256:" + "a" * 64
    package_b = "sha256:" + "b" * 64
    assert register_package(scene, {"source_package_id": package_a})[1] == "NO_COLLISION"
    assert register_package(scene, {"source_package_id": package_b})[1] == "NO_COLLISION"

    material_a = bpy.data.materials.new("Shared")
    material_a["unity_source_package_id"] = package_a
    material_a["unity_material_guid"] = "f" * 32
    material_a["unity_material_path"] = "Assets/Shared.mat"
    material_b = bpy.data.materials.new("Shared.001")
    material_b["unity_source_package_id"] = package_b
    material_b["unity_material_guid"] = "f" * 32
    material_b["unity_material_path"] = "Assets/Other.mat"
    register_datablocks(scene, [material_a], package_a, "Material")
    registry = register_datablocks(scene, [material_b], package_b, "Material")
    statuses = {item["status"] for item in registry.detect_collisions()}
    assert CROSS_PACKAGE_GUID_COLLISION in statuses

    object_a = bpy.data.objects.new("SharedObject", None)
    object_a["unity_source_package_id"] = package_a
    object_a["unity_source_fbx"] = "Assets/Shared.fbx"
    register_datablocks(scene, [object_a], package_a, "Object")
    object_identity = load_scene_registry(scene).find_by_asset_path("Assets/Shared.fbx")
    assert len(object_identity) == 1
    assert object_identity[0]["identity"]["source_package_id"] == package_a

    image_a = bpy.data.images.new("Shared.png", width=1, height=1)
    image_a["unity_source_package_id"] = package_a
    image_a["unity_guid"] = "a" * 32
    image_a["unity_asset_path"] = "Assets/Shared.png"
    image_b = bpy.data.images.new("Shared.png", width=1, height=1)
    image_b["unity_source_package_id"] = package_b
    image_b["unity_guid"] = "b" * 32
    image_b["unity_asset_path"] = "Assets/Shared.png"
    register_datablocks(scene, [image_a], package_a, "Image")
    # Register the second package explicitly because the helper receives one package id per batch.
    register_datablocks(scene, [image_b], package_b, "Image")
    statuses = {item["status"] for item in load_scene_registry(scene).detect_collisions()}
    assert CROSS_PACKAGE_PATH_COLLISION in statuses

    print("MULTI_PACKAGE_IDENTITY_OK")


main()
