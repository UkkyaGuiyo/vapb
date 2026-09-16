from __future__ import annotations

import io
import json
import base64
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


def package(path: Path, records: list[tuple[str, str, bytes]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for guid, unity_path, payload in records:
            add(archive, f"{guid}/asset", payload)
            add(archive, f"{guid}/pathname", unity_path.encode())
            add(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode())


def prefab(material_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: ManualGeometry
  m_Component:
  - component: {{fileID: 200}}
--- !u!23 &200
MeshRenderer:
  m_GameObject: {{fileID: 1001}}
  m_Materials:
  - {{fileID: 2100000, guid: {material_guid}, type: 2}}
""".encode()


def make_fbx() -> bytes:
    path = Path(tempfile.mkdtemp(prefix="manual_fbx_")) / "Body.fbx"
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = "ManualGeometry"
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, add_leaf_bones=False, bake_anim=False)
    bpy.data.objects.remove(obj, do_unlink=True)
    return path.read_bytes()


def material(base_guid: str, normal_guid: str) -> bytes:
    return f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: ManualMaterial
  m_SavedProperties:
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {base_guid}, type: 3}}
    - _BumpMap:
        m_Texture: {{fileID: 2800000, guid: {normal_guid}, type: 3}}
""".encode()


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material_guid, fbx_guid, prefab_guid = "a" * 32, "b" * 32, "c" * 32
    base_guid, normal_guid = "d" * 32, "e" * 32
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    with tempfile.TemporaryDirectory(prefix="manual_primary_") as primary_temp, tempfile.TemporaryDirectory(prefix="manual_provider_") as provider_temp:
        primary = Path(primary_temp) / "geometry.unitypackage"
        provider_dir = Path(provider_temp) / "nested"
        provider_dir.mkdir()
        provider = provider_dir / "appearance.unitypackage"
        package(primary, [(fbx_guid, "Assets/Body.fbx", make_fbx()), (prefab_guid, "Assets/Body.prefab", prefab(material_guid))])
        package(provider, [
            (material_guid, "Assets/Body.mat", material(base_guid, normal_guid)),
            (base_guid, "Assets/Base.png", png),
            (normal_guid, "Assets/Normal.png", png),
        ])
        addon = __import__("unitypackage_blender_importer")
        addon.register()
        result = bpy.ops.import_scene.unitypackage(filepath=str(primary), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=False)
        assert "FINISHED" in result, result
        from unitypackage_blender_importer.unity.sibling_discovery import inspect_provider_package
        from unitypackage_blender_importer.unity.package_identity import PackageIdentity

        candidate = inspect_provider_package(provider, {material_guid})
        assert candidate.matched_guids == {material_guid}, candidate
        provider_id = PackageIdentity.from_path(provider).source_package_id
        bpy.context.scene["unitypackage_provider_provenance"] = json.dumps({provider_id: "USER_SELECTED_PACKAGE"}, sort_keys=True)
        result = bpy.ops.import_scene.unitypackage(filepath=str(provider), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=False, group_child=True)
        assert "FINISHED" in result, result
        records = json.loads(str(bpy.context.scene["unitypackage_dependency_registry"]))["dependencies"]
        material_records = [item for item in records if item.get("target_guid") == material_guid]
        assert material_records and material_records[-1]["status"] == "RESOLVED_CROSS_PACKAGE", records
        assert material_records[-1]["resolution_provenance"] == "USER_SELECTED_PACKAGE", material_records[-1]
        obj = next(item for item in bpy.data.objects if item.get("unity_prefab_file_id") == "1001")
        bound = obj.data.materials[0]
        images = {image.get("unity_guid") for node in bound.node_tree.nodes if node.type == "TEX_IMAGE" and node.image for image in [node.image]}
        assert {base_guid, normal_guid} <= images, images
        bsdf = next(node for node in bound.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        base_image = bsdf.inputs["Base Color"].links[0].from_node.inputs["Color2"].links[0].from_node.image
        normal_node = bsdf.inputs["Normal"].links[0].from_node
        normal_image = normal_node.inputs["Color"].links[0].from_node.image
        assert base_image.get("unity_guid") == base_guid, base_image.get("unity_guid")
        assert normal_image.get("unity_guid") == normal_guid, normal_image.get("unity_guid")
        texture_records = [item for item in records if item.get("consumer_asset_guid") == material_guid]
        assert {item.get("texture_label") for item in texture_records} == {"Base Color", "Normal"}, texture_records
        addon.unregister()
    print("MANUAL_PROVIDER_E2E_OK")


if __name__ == "__main__":
    main()
