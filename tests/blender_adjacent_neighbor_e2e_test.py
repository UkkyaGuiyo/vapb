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

def add(archive, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


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


def make_fbx() -> bytes:
    path = Path(tempfile.mkdtemp(prefix="adjacent_fbx_")) / "Body.fbx"
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = "Coat"
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, add_leaf_bones=False, bake_anim=False)
    bpy.data.objects.remove(obj, do_unlink=True)
    return path.read_bytes()


def material_with_roles(main_guid: str, normal_guid: str, matcap_guid: str, mask_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: AdjacentMaterial
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    m_Floats: []
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {main_guid}, type: 3}}
    - _BumpMap:
        m_Texture: {{fileID: 2800000, guid: {normal_guid}, type: 3}}
    - _MatCapTex:
        m_Texture: {{fileID: 2800000, guid: {matcap_guid}, type: 3}}
    - _ShadowBorderMask:
        m_Texture: {{fileID: 2800000, guid: {mask_guid}, type: 3}}
""".encode()


def unrelated_material_with_missing_texture(guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: UnrelatedMaterial
  m_SavedProperties:
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {guid}, type: 3}}
""".encode()


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with tempfile.TemporaryDirectory(prefix="adjacent_neighbor_") as temp:
        bundle = Path(temp) / "Bundle"
        geometry_dir = bundle / "Geometry"
        appearance_dir = bundle / "Appearance"
        geometry_dir.mkdir(parents=True)
        appearance_dir.mkdir(parents=True)
        fbx_guid, prefab_guid, material_guid = "a" * 32, "b" * 32, "c" * 32
        main_guid, normal_guid, matcap_guid, mask_guid = "d" * 32, "e" * 32, "f" * 32, "1" * 32
        unrelated_material_guid, unrelated_texture_guid = "2" * 32, "3" * 32
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        geometry = geometry_dir / "geometry.unitypackage"
        appearance = appearance_dir / "appearance.unitypackage"
        package(geometry, [(fbx_guid, "Assets/Geometry/Body.fbx", make_fbx()), (prefab_guid, "Assets/Geometry/Body.prefab", prefab(fbx_guid, material_guid))], material_guid)
        package(appearance, [
            (material_guid, "Assets/Appearance/Body.mat", material_with_roles(main_guid, normal_guid, matcap_guid, mask_guid)),
            (unrelated_material_guid, "Assets/Appearance/Unrelated.mat", unrelated_material_with_missing_texture(unrelated_texture_guid)),
            (main_guid, "Assets/Appearance/Main.png", png),
            (normal_guid, "Assets/Appearance/Normal.png", png),
            (matcap_guid, "Assets/Appearance/MatCap.png", png),
            (mask_guid, "Assets/Appearance/Mask.png", png),
        ])
        addon = __import__("unitypackage_blender_importer")
        addon.register()
        from unitypackage_blender_importer.unity.sibling_discovery import discover_siblings

        discovery = discover_siblings(geometry)
        assert discovery.visual_status == "COMPLETE", discovery
        assert len(discovery.packages) == 1, discovery
        result = bpy.ops.import_scene.unitypackage(filepath=str(geometry), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=False)
        assert "FINISHED" in result, result
        group = bpy.context.scene.get("unitypackage_group_import", {})
        assert len(group["related_package_ids"]) == 1, group
        obj = next(item for item in bpy.data.objects if item.get("unity_prefab_file_id") == "1001")
        material = obj.data.materials[0]
        assert material and material.get("unity_material_guid") == material_guid
        bsdf = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        base = bsdf.inputs["Base Color"].links[0].from_node.inputs["Color2"].links[0].from_node.image
        normal_map = bsdf.inputs["Normal"].links[0].from_node
        normal = normal_map.inputs["Color"].links[0].from_node.image
        assert base.get("unity_guid") == main_guid, base.get("unity_guid")
        assert normal.get("unity_guid") == normal_guid, normal.get("unity_guid")
        records = json.loads(str(bpy.context.scene["unitypackage_dependency_registry"]))["dependencies"]
        preserve = [
            item for item in records
            if item.get("texture_label") == "Preserve Only"
            and item.get("consumer_asset_guid") == material_guid
        ]
        assert len(preserve) == 2, records
        assert all(item["status"] in {"RESOLVED_LOCAL", "RESOLVED_CROSS_PACKAGE"} for item in preserve), preserve
        assert all(item["binding_source"] == "preserve_only" for item in preserve), preserve
        addon.unregister()
    print("ADJACENT_NEIGHBOR_E2E_OK")


if __name__ == "__main__":
    main()
