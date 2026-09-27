"""Texture re-resolution must preserve user-owned Image and node changes."""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.dependency_resolver import (  # noqa: E402
    capture_material_texture_dependencies, load_dependency_registry, resolve_scene_dependencies,
    save_dependency_registry,
)


PACKAGE = "synthetic-package"
MATERIAL = "a" * 32
TEXTURE = "b" * 32


def record():
    rows = load_dependency_registry(bpy.context.scene)["dependencies"]
    assert len(rows) == 1, rows
    return rows[0]


def setup(with_provider=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("EditedMaterial")
    material.use_nodes = True
    material["unity_material_guid"] = MATERIAL
    material["unity_material_path"] = "Assets/Synthetic/Edited.mat"
    material["unity_source_package_id"] = PACKAGE
    material["unity_props"] = json.dumps({"textures": {
        "_MainTex": {"guid": TEXTURE, "file_id": 2800000},
    }})
    mesh = bpy.data.meshes.new("EditedMesh")
    obj = bpy.data.objects.new("EditedObject", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material)
    provider = None
    if with_provider:
        provider = bpy.data.images.new("ProviderImage", 1, 1)
        provider["unity_guid"] = TEXTURE
        provider["unity_source_package_id"] = PACKAGE
    capture_material_texture_dependencies(bpy.context.scene, [material])
    resolve_scene_dependencies(bpy.context.scene)
    assert record()["binding_status"] == ("BOUND" if with_provider else "UNRESOLVED")
    node = material.node_tree.nodes.get("Unity Base Color EditedMaterial")
    if with_provider:
        assert node.image is provider
    return material, provider, node


def user_image():
    image = bpy.data.images.new("UserImage", 1, 1)
    bpy.data.materials["EditedMaterial"].node_tree.nodes[
        "Unity Base Color EditedMaterial"].image = image
    return image


def user_link():
    material = bpy.data.materials["EditedMaterial"]
    nodes = material.node_tree.nodes
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    custom = nodes.new("ShaderNodeRGB")
    custom.name = "UserColor"
    material.node_tree.links.new(custom.outputs["Color"], bsdf.inputs["Base Color"])
    return custom


def assert_user_link():
    material = bpy.data.materials["EditedMaterial"]
    bsdf = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    links = list(bsdf.inputs["Base Color"].links)
    assert len(links) == 1 and links[0].from_node == material.node_tree.nodes["UserColor"]


def main():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python script -- image|link-create|link-reopen|provider-add|provider-loss|provider-loss-clean blend_path")
    phase, blend_path = sys.argv[sys.argv.index("--") + 1:]
    if phase == "image":
        _material, _provider, node = setup()
        edited = user_image()
        resolve_scene_dependencies(bpy.context.scene)
        assert node.image is edited, "Resolve overwrote the user's Image choice"
        assert record()["binding_status"] == "USER_EDIT_PRESERVED"
        assert "_vapb_dependency_image_token" not in edited
        print("TEXTURE_USER_IMAGE_PRESERVED")
    elif phase == "link-create":
        setup()
        user_link()
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("TEXTURE_USER_LINK_SAVED")
    elif phase == "link-reopen":
        assert_user_link()
        resolve_scene_dependencies(bpy.context.scene)
        assert_user_link()
        assert record()["binding_status"] == "USER_EDIT_PRESERVED"
        print("TEXTURE_USER_LINK_PRESERVED_AFTER_REOPEN")
    elif phase == "provider-loss":
        _material, provider, node = setup()
        edited = user_image()
        bpy.data.images.remove(provider)
        resolve_scene_dependencies(bpy.context.scene)
        assert node.image is edited, "Provider loss cleared the user's Image"
        assert record()["binding_status"] == "USER_EDIT_PRESERVED"
        assert "_vapb_dependency_image_token" not in edited
        print("TEXTURE_USER_IMAGE_PRESERVED_ON_PROVIDER_LOSS")
    elif phase == "provider-add":
        material, _provider, _node = setup(with_provider=False)
        edited = bpy.data.images.new("UserImage", 1, 1)
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.name = "Unity Base Color EditedMaterial"
        node.image = edited
        provider = bpy.data.images.new("ProviderImage", 1, 1)
        provider["unity_guid"] = TEXTURE
        provider["unity_source_package_id"] = PACKAGE
        resolve_scene_dependencies(bpy.context.scene)
        assert node.image is edited
        assert record()["binding_status"] == "USER_EDIT_PRESERVED"
        assert "_vapb_dependency_image_token" not in edited
        print("TEXTURE_USER_IMAGE_PRESERVED_ON_PROVIDER_ADD")
    elif phase == "provider-loss-clean":
        material, provider, node = setup()
        custom = material.node_tree.nodes.new("ShaderNodeRGB")
        custom.name = "UserNode"
        bpy.data.images.remove(provider)
        resolve_scene_dependencies(bpy.context.scene)
        assert node.image is None
        assert material.node_tree.nodes.get("UserNode") is not None
        assert record()["binding_status"] == "UNRESOLVED"
        print("TEXTURE_UNEDITED_PROVIDER_LOSS_UNBOUND")
    elif phase == "provider-readd-after-edit":
        _material, provider, node = setup()
        bpy.data.images.remove(provider)
        resolve_scene_dependencies(bpy.context.scene)
        assert record()["binding_status"] == "UNRESOLVED"
        edited = user_image()
        replacement = bpy.data.images.new("ReplacementProvider", 1, 1)
        replacement["unity_guid"] = TEXTURE
        replacement["unity_source_package_id"] = PACKAGE
        resolve_scene_dependencies(bpy.context.scene)
        assert node.image is edited
        assert record()["binding_status"] == "USER_EDIT_PRESERVED"
        print("TEXTURE_READD_AFTER_EDIT_PRESERVED")
    elif phase == "legacy-unverified":
        _material, _provider, node = setup()
        registry = load_dependency_registry(bpy.context.scene)
        registry["dependencies"][0].pop("applied_texture_state")
        save_dependency_registry(bpy.context.scene, registry)
        edited = user_image()
        for _ in range(2):
            resolve_scene_dependencies(bpy.context.scene)
            assert node.image is edited
            assert record()["binding_status"] == "UNVERIFIED_TEXTURE_STATE"
        print("TEXTURE_LEGACY_UNVERIFIED_STAYS_CLOSED")
    else:
        raise AssertionError(phase)


if __name__ == "__main__":
    main()
