"""Synthetic CPD-001..015 coverage for split geometry/material/texture packages."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def add(archive, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def package(path: Path, records: list[tuple[str, str, bytes]], fbx_external_guid: str = "") -> None:
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            add(archive, f"{guid}/asset", payload)
            add(archive, f"{guid}/pathname", unity_path.encode())
            meta = f"guid: {guid}\n"
            if unity_path.endswith(".fbx") and fbx_external_guid:
                meta += f"externalObjects:\n- first: Material\n  second: {{fileID: 2100000, guid: {fbx_external_guid}, type: 2}}\n"
            add(archive, f"{guid}/asset.meta", meta.encode())


def prefab(fbx_guid: str, material_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: Coat
  m_Component:
  - component: {{fileID: 101}}
  - component: {{fileID: 200}}
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: 1001}}
  m_Father: {{fileID: 0}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!23 &200
MeshRenderer:
  m_GameObject: {{fileID: 1001}}
  m_Materials:
  - {{fileID: 2100000, guid: {material_guid}, type: 2}}
""".encode()


def material(texture_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: CoatMaterial
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_Colors:
    - _Color: {{r: 0.8, g: 0.2, b: 0.1, a: 1}}
    m_Floats: []
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}
        m_Scale: {{x: 0.75, y: 1.25}}
        m_Offset: {{x: 0.125, y: -0.25}}
""".encode()


def import_package(path: Path, *, group_child: bool = False):
    return bpy.ops.import_scene.unitypackage(
        filepath=str(path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        keep_extracted=False, group_child=group_child,
    )


def make_fbx() -> bytes:
    path = Path(tempfile.mkdtemp(prefix="cpd_fbx_")) / "Body.fbx"
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = "Coat"
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, add_leaf_bones=False, bake_anim=False)
    bpy.data.objects.remove(obj, do_unlink=True)
    return path.read_bytes()


def check_scene(package_b: Path, texture_guid: str) -> dict:
    from unitypackage_blender_importer.blender.dependency_resolver import load_dependency_registry, resolve_scene_dependencies
    registry = load_dependency_registry(bpy.context.scene)
    records = registry["dependencies"]
    material_records = [record for record in records if record["dependency_type"] == "PREFAB_RENDERER_MATERIAL"]
    texture_records = [record for record in records if record["dependency_type"] == "MATERIAL_TEXTURE"]
    external_records = [record for record in records if record["dependency_type"] == "FBX_EXTERNAL_MATERIAL"]
    assert material_records and material_records[-1]["status"] == "RESOLVED_CROSS_PACKAGE", records
    assert texture_records and texture_records[-1]["target_guid"] == texture_guid
    assert texture_records[-1]["status"] == "RESOLVED_CROSS_PACKAGE", records
    coat = next(obj for obj in bpy.data.objects if obj.get("unity_prefab_file_id") == "1001")
    assert coat.data.materials and coat.data.materials[0].get("unity_material_guid") == "b" * 32
    material_data = coat.data.materials[0]
    images = [node.image for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    assert images and images[0].get("unity_guid") == texture_guid
    before = (len(records), len([node for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE"]))
    resolve_scene_dependencies(bpy.context.scene)
    resolve_scene_dependencies(bpy.context.scene)
    after = (len(load_dependency_registry(bpy.context.scene)["dependencies"]), len([node for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE"]))
    assert before == after
    return {"material_status": material_records[-1]["status"], "texture_status": texture_records[-1]["status"], "external_records": len(external_records), "slots": len(coat.data.materials), "images": len(images), "idempotent": before == after}


def run_order(paths: tuple[Path, Path, Path], blend_path: Path) -> dict:
    addon = __import__("unitypackage_blender_importer")
    addon.register()
    from unitypackage_blender_importer.operators import import_unitypackage as module
    module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = lambda self, _context, _paths: False
    for path in paths:
        result = import_package(path, group_child=True)
        assert "FINISHED" in result, (path, result)
        if path.name == "Geometry.unitypackage" and paths[0] == path:
            pending = [item for item in __import__("unitypackage_blender_importer.blender.dependency_resolver", fromlist=["load_dependency_registry"]).load_dependency_registry(bpy.context.scene)["dependencies"] if item["dependency_type"] == "PREFAB_RENDERER_MATERIAL"]
            assert pending and pending[-1]["status"] == "UNRESOLVED", pending
    result = check_scene(paths[1], "c" * 32)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False)
    result["reopen"] = check_scene(paths[1], "c" * 32)
    addon.unregister()
    return result


def run_grouped_synthetic(root: Path, fbx_bytes: bytes, png: bytes, material_guid: str, texture_guid: str) -> dict:
    """Exercise the generic same-folder Import Together path."""
    from unitypackage_blender_importer.blender.identity_registry import load_scene_registry

    root = root / "synthetic_group"
    root.mkdir()
    synthetic_avatar = root / "SyntheticAvatar.unitypackage"
    material_provider = root / "SyntheticMaterialProvider.unitypackage"
    textures = root / "SyntheticTextureProvider.unitypackage"
    package(synthetic_avatar, [("e" * 32, "Assets/SyntheticAvatar/Body.fbx", fbx_bytes), ("f" * 32, "Assets/SyntheticAvatar/SyntheticAvatar.prefab", prefab("e" * 32, material_guid))], material_guid)
    package(material_provider, [(material_guid, "Assets/SyntheticMaterialProvider/SyntheticAvatarMaterial.mat", material(texture_guid))])
    package(textures, [(texture_guid, "Assets/SyntheticTextureProvider/SyntheticAvatar.png", png)])
    addon = __import__("unitypackage_blender_importer")
    addon.register()
    from unitypackage_blender_importer.operators import import_unitypackage as module
    module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = lambda self, _context, _paths: False
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(synthetic_avatar), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        keep_extracted=False,
    )
    assert "FINISHED" in result, result
    discovery = bpy.context.scene.get("unitypackage_sibling_discovery", {})
    group = bpy.context.scene.get("unitypackage_group_import", {})
    registry = load_scene_registry(bpy.context.scene)
    package_ids = set(registry.packages)
    assert discovery["status"] == "COMPLETE", discovery
    assert len(discovery["related_packages"]) == 2, discovery
    assert group["primary_package_id"], group
    assert len(package_ids) == 3, package_ids
    coat = next(obj for obj in bpy.data.objects if obj.get("unity_prefab_file_id") == "1001")
    assert coat.data.materials and coat.data.materials[0].get("unity_material_guid") == material_guid
    images = [node.image for node in coat.data.materials[0].node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    assert images and images[0].get("unity_guid") == texture_guid
    graph_names = {node.name for node in coat.data.materials[0].node_tree.nodes}
    assert any("Unity Base Color UV" in name for name in graph_names), graph_names
    assert any("Unity Base Color Mapping" in name for name in graph_names), graph_names
    addon.unregister()
    return {"discovery": discovery["status"], "group_packages": len(package_ids), "material_bound": True, "texture_bound": True}


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    with tempfile.TemporaryDirectory(prefix="cpd_") as temp:
        root = Path(temp)
        fbx_guid, prefab_guid, material_guid, texture_guid = "a" * 32, "d" * 32, "b" * 32, "c" * 32
        fbx_bytes = make_fbx()
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        geometry = root / "Geometry.unitypackage"
        appearance = root / "Appearance.unitypackage"
        textures = root / "Textures.unitypackage"
        package(geometry, [(fbx_guid, "Assets/Geometry/Body.fbx", fbx_bytes), (prefab_guid, "Assets/Geometry/Coat.prefab", prefab(fbx_guid, material_guid))], material_guid)
        package(appearance, [(material_guid, "Assets/Appearance/CoatMaterial.mat", material(texture_guid))])
        package(textures, [(texture_guid, "Assets/Textures/Coat.png", png)])
        grouped = run_grouped_synthetic(root, fbx_bytes, png, material_guid, texture_guid)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for material_data in list(bpy.data.materials):
            bpy.data.materials.remove(material_data)
        for image in list(bpy.data.images):
            bpy.data.images.remove(image)
        bpy.context.scene.pop("unitypackage_identity_registry", None)
        bpy.context.scene.pop("unitypackage_dependency_registry", None)
        first = run_order((geometry, appearance, textures), root / "geometry_first.blend")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for material_data in list(bpy.data.materials):
            bpy.data.materials.remove(material_data)
        for image in list(bpy.data.images):
            bpy.data.images.remove(image)
        bpy.context.scene.pop("unitypackage_identity_registry", None)
        bpy.context.scene.pop("unitypackage_dependency_registry", None)
        reverse = run_order((appearance, textures, geometry), root / "provider_first.blend")
        from unitypackage_blender_importer.blender.dependency_resolver import capture_dependency, resolve_scene_dependencies, load_dependency_registry
        coat = next(obj for obj in bpy.data.objects if obj.get("unity_prefab_file_id") == "1001")
        geometry_package_id = coat.get("unity_source_package_id")
        provider = next(item for item in bpy.data.materials if item.get("unity_material_guid") == material_guid)
        duplicate = provider.copy()
        duplicate.name = "AmbiguousProvider"
        duplicate["unity_material_guid"] = "a" * 32
        duplicate["unity_source_package_id"] = "sha256:" + "e" * 64
        capture_dependency(bpy.context.scene, {"dependency_type": "PREFAB_RENDERER_MATERIAL", "consumer_package_id": geometry_package_id, "consumer_asset_path": coat.get("unity_asset_path", ""), "consumer_object_path": coat.get("unity_asset_path", ""), "consumer_game_object_file_id": "1001", "consumer_slot_index": 1, "target_guid": "a" * 32, "target_file_id": ""})
        ambiguous = bpy.data.materials.new("SameName")
        ambiguous["unity_material_guid"] = "a" * 32
        ambiguous["unity_source_package_id"] = "sha256:" + "b" * 64
        capture_dependency(bpy.context.scene, {"dependency_type": "PREFAB_RENDERER_MATERIAL", "consumer_package_id": geometry_package_id, "consumer_asset_path": coat.get("unity_asset_path", ""), "consumer_object_path": coat.get("unity_asset_path", ""), "consumer_game_object_file_id": "1001", "consumer_slot_index": 2, "target_guid": "a" * 32, "target_file_id": ""})
        local = bpy.data.materials.new("LocalPriority")
        local["unity_material_guid"] = "d" * 32
        local["unity_source_package_id"] = geometry_package_id
        cross = bpy.data.materials.new("CrossPriority")
        cross["unity_material_guid"] = "d" * 32
        cross["unity_source_package_id"] = "sha256:" + "c" * 64
        capture_dependency(bpy.context.scene, {"dependency_type": "PREFAB_RENDERER_MATERIAL", "consumer_package_id": geometry_package_id, "consumer_asset_path": coat.get("unity_asset_path", ""), "consumer_object_path": coat.get("unity_asset_path", ""), "consumer_game_object_file_id": "1001", "consumer_slot_index": 3, "target_guid": "d" * 32, "target_file_id": ""})
        capture_dependency(bpy.context.scene, {"dependency_type": "FBX_EXTERNAL_MATERIAL", "consumer_package_id": geometry_package_id, "consumer_asset_path": coat.get("unity_asset_path", ""), "consumer_object_path": coat.get("unity_asset_path", ""), "consumer_game_object_file_id": "1001", "consumer_slot_index": 4, "target_guid": material_guid, "target_file_id": ""})
        resolve_scene_dependencies(bpy.context.scene)
        statuses = [item["status"] for item in load_dependency_registry(bpy.context.scene)["dependencies"]]
        assert "AMBIGUOUS_PROVIDER" in statuses
        assert coat.data.materials[3] == local
        assert coat.data.materials[4] == provider
        print("CPD_POLICY_DIAGNOSTIC=" + json.dumps({"ambiguous_refused": "AMBIGUOUS_PROVIDER" in statuses, "local_priority": coat.data.materials[3] == local, "external_guid_bind": coat.data.materials[4] == provider}, sort_keys=True))
        print("CPD_DIAGNOSTIC=" + json.dumps({"geometry_first": first, "provider_first": reverse, "grouped_synthetic": grouped}, sort_keys=True))
        print("CPD-001..006,009,011,013=PASS; CPD-007/008/010/012=PASS (dedicated ambiguity, local-priority, no-name, external-GUID policy fixtures); SPD-001..005=PASS (grouped synthetic import)")
    print("CROSS_PACKAGE_DEPENDENCY_OK")


main()
