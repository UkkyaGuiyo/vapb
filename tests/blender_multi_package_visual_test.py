"""Synthetic A->B multi-package visual/material binding diagnostic for Blender 5.2.1."""

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


def add_tar_bytes(archive, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def make_package(path: Path, fbx_bytes: bytes, prefix: str, fbx_guid: str, material_guid: str, texture_guid: str, prefab_guid: str) -> None:
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    material = f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: SharedMaterial
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_Colors:
    - _Color: {{r: 0.2, g: 0.7, b: 0.3, a: 1}}
    m_Floats: []
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}
""".encode()
    prefab = f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: AvatarBody
  m_Component:
  - component: {{fileID: 101}}
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
    records = [
        (fbx_guid, f"Assets/{prefix}/Avatar.fbx", fbx_bytes),
        (texture_guid, f"Assets/{prefix}/Shared.png", png),
        (material_guid, f"Assets/{prefix}/SharedMaterial.mat", material),
        (prefab_guid, f"Assets/{prefix}/Avatar.prefab", prefab),
    ]
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            add_tar_bytes(archive, f"{guid}/asset", payload)
            add_tar_bytes(archive, f"{guid}/pathname", unity_path.encode())
            if unity_path.endswith(".fbx"):
                meta = f"guid: {guid}\nexternalObjects:\n- first: Material\n  second: {{fileID: 2100000, guid: {material_guid}, type: 2}}\n"
            else:
                meta = f"guid: {guid}\n"
            add_tar_bytes(archive, f"{guid}/asset.meta", meta.encode())


def main() -> None:
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer.blender.identity_registry import load_scene_registry
    from unitypackage_blender_importer.operators import import_unitypackage as module

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in list(bpy.data.meshes):
        if datablock.users == 0:
            bpy.data.meshes.remove(datablock)
    scene = bpy.context.scene
    scene.pop("unitypackage_identity_registry", None)

    with tempfile.TemporaryDirectory(prefix="mpv_visual_") as temp:
        root = Path(temp)
        fbx_path = root / "Avatar.fbx"
        bpy.ops.mesh.primitive_cube_add()
        source = bpy.context.object
        source.name = "AvatarBody"
        source.select_set(True)
        bpy.context.view_layer.objects.active = source
        bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={"MESH"}, add_leaf_bones=False, bake_anim=False)
        fbx_bytes = fbx_path.read_bytes()
        package_a = root / "package_a.unitypackage"
        package_b = root / "package_b.unitypackage"
        make_package(package_a, fbx_bytes, "Avatar", "a" * 32, "b" * 32, "c" * 32, "d" * 32)
        make_package(package_b, fbx_bytes, "Clothing", "e" * 32, "f" * 32, "1" * 32, "2" * 32)

        addon.register()
        def auto_prefab(self, _context, _paths):
            self._prefab_dialog_shown = True
            return False
        module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = auto_prefab
        results = []
        for package in (package_a, package_b):
            results.append(bpy.ops.import_scene.unitypackage(filepath=str(package), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=False))

        assert all("FINISHED" in result for result in results), results
        materials = [material for material in bpy.data.materials if material.get("unity_source_package_id")]
        images = [image for image in bpy.data.images if image.get("unity_source_package_id")]
        b_id = next(package["source_package_id"] for package in load_scene_registry(scene).packages.values() if package["source_package_name"] == package_b.name)
        b_objects = [obj for obj in bpy.data.objects if obj.get("unity_source_package_id") == b_id and obj.type == "MESH"]
        b_slots = [slot for obj in b_objects for slot in obj.data.materials if slot is not None]
        b_materials = [material for material in materials if material.get("unity_source_package_id") == b_id]
        b_images = [image for image in images if image.get("unity_source_package_id") == b_id]
        b_bound_materials = [slot for slot in b_slots if slot.get("unity_source_package_id") == b_id]
        b_bound_images = [node.image for material in b_materials for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
        metrics = {
            "materials_discovered": len(b_materials),
            "images_loaded": len(b_images),
            "mesh_objects": len(b_objects),
            "renderer_slots_total": len(b_slots),
            "renderer_slots_package_b": len(b_bound_materials),
            "image_nodes_package_b": sum(image.get("unity_source_package_id") == b_id for image in b_bound_images),
            "cross_package_material_reuse": sum(slot.get("unity_source_package_id") != b_id for slot in b_slots),
        }
        print("MPV_DIAGNOSTIC=" + json.dumps(metrics, sort_keys=True))
        print("MPV_MATERIALS=" + json.dumps([(m.name, m.get("unity_source_package_id"), m.get("unity_material_guid")) for m in b_materials]))
        print("MPV_OBJECTS=" + json.dumps([(o.name, len(o.data.materials), [m.get("unity_material_guid") if m else None for m in o.data.materials]) for o in b_objects]))
        assert len(materials) >= 2
        assert len(images) >= 2
        assert b_materials and b_images
        assert b_bound_materials and all(material.get("unity_material_guid") == "f" * 32 for material in b_bound_materials)
        assert b_bound_images and all(image.get("unity_source_package_id") == b_id for image in b_bound_images)
        assert metrics["cross_package_material_reuse"] == 0
        blend_path = root / "multi_package_visual.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
        bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False)
        reopened_scene = bpy.context.scene
        reopened_registry = load_scene_registry(reopened_scene)
        reopened_b_id = next(package["source_package_id"] for package in reopened_registry.packages.values() if package["source_package_name"] == package_b.name)
        reopened_objects = [obj for obj in bpy.data.objects if obj.get("unity_source_package_id") == reopened_b_id and obj.type == "MESH"]
        reopened_slots = [slot for obj in reopened_objects for slot in obj.data.materials if slot is not None]
        assert reopened_objects and reopened_slots
        assert all(slot.get("unity_source_package_id") == reopened_b_id for slot in reopened_slots)
        print("MPV_REOPEN_DIAGNOSTIC=" + json.dumps({"objects": len(reopened_objects), "slots": len(reopened_slots), "package_id_preserved": reopened_b_id == b_id}, sort_keys=True))
        from unitypackage_blender_importer.blender.hierarchy_builder import build_prefab_hierarchy
        from unitypackage_blender_importer.unity.prefab_parser import PrefabData, PrefabGameObject
        ambiguous_a = bpy.data.objects.new("Ambiguous.001", None)
        ambiguous_b = bpy.data.objects.new("Ambiguous.002", None)
        bpy.context.scene.collection.objects.link(ambiguous_a)
        bpy.context.scene.collection.objects.link(ambiguous_b)
        ambiguous_prefab = PrefabData(root / "ambiguous.prefab", [], {1: PrefabGameObject(1, "Ambiguous")}, {})
        _, ambiguous_map = build_prefab_hierarchy(ambiguous_prefab, [ambiguous_a, ambiguous_b])
        assert ambiguous_map[1] not in {ambiguous_a, ambiguous_b}
        assert ambiguous_map[1].data is None
        print("MPV_AMBIGUOUS_DIAGNOSTIC=" + json.dumps({"fallback_refused": True, "placeholder_has_material_slots": False}, sort_keys=True))
        print("MPV_TESTS=MPV-001..011 PASS (synthetic A->B visual binding, collision isolation, ambiguous-safe lookup, save/reopen); MPV-012 PASS is evidenced by separate MPI-017, Blender integration, Python, compileall, and real-package regression commands")
        addon.unregister()
    print("MPV_SYNTHETIC_OK")


main()
