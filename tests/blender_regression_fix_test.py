from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class Entry:
    def __init__(self, guid: str, path: str):
        self.guid = guid
        self.path = Path(path)


class Database:
    source_package_id = "sha256:" + "1" * 64

    def __init__(self, entry):
        self.entry = entry

    def find_guid(self, guid):
        return self.entry if str(guid).lower() == self.entry.guid else None


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)
    bpy.context.scene.pop("unitypackage_dependency_registry", None)


def prefab_fixture(path: Path):
    path.write_text("""%YAML 1.1
--- !u!1001 &100
PrefabInstance:
  m_Modification:
    m_Modifications:
    - target: {fileID: -123, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Name
      value: Coat
    - target: {fileID: -123, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        type: 3}
      propertyPath: m_Materials.Array.data[0]
      value:
      objectReference: {fileID: 2100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
        type: 2}
""", encoding="utf-8")


def test_prefab_instance_override():
    from unitypackage_blender_importer.unity.prefab_parser import parse_prefab
    from unitypackage_blender_importer.blender.material_builder import apply_prefab_modification_materials
    from unitypackage_blender_importer.blender.dependency_resolver import load_dependency_registry

    clear_scene()
    with tempfile.TemporaryDirectory(prefix="prefab_override_") as temp:
        path = Path(temp) / "Avatar.prefab"
        prefab_fixture(path)
        prefab = parse_prefab(path)
        mesh = bpy.data.meshes.new("CoatMesh")
        obj = bpy.data.objects.new("Coat", mesh)
        bpy.context.scene.collection.objects.link(obj)
        material = bpy.data.materials.new("ProviderMaterial")
        material["unity_material_guid"] = "b" * 32
        material["unity_source_package_id"] = "sha256:" + "2" * 64
        entry = Entry("b" * 32, str(Path(temp) / "Provider.mat"))
        apply_prefab_modification_materials(prefab, [obj], Database(entry), {str(entry.path): material}, bpy.context.scene)
        assert obj.data.materials[0] == material, list(load_dependency_registry(bpy.context.scene)["dependencies"])


def test_texture_roles():
    from unitypackage_blender_importer.blender.dependency_resolver import (
        capture_material_texture_dependencies,
        load_dependency_registry,
        resolve_scene_dependencies,
    )

    clear_scene()
    material = bpy.data.materials.new("RoleMaterial")
    material.use_nodes = True
    material["unity_material_guid"] = "c" * 32
    material["unity_source_package_id"] = Database.source_package_id
    material["unity_props"] = json.dumps({"textures": {
        "_MainTex": {"guid": "d" * 32, "file_id": 1},
        "_BumpMap": {"guid": "e" * 32, "file_id": 2},
    }})
    main = bpy.data.images.new("Main", 1, 1)
    main["unity_guid"] = "d" * 32
    main["unity_source_package_id"] = Database.source_package_id
    bump = bpy.data.images.new("Bump", 1, 1)
    bump["unity_guid"] = "e" * 32
    bump["unity_source_package_id"] = Database.source_package_id
    capture_material_texture_dependencies(bpy.context.scene, [material])
    counts = resolve_scene_dependencies(bpy.context.scene)
    assert counts["resolved_local"] == 2, counts
    base = next(node for node in material.node_tree.nodes if node.name == "Unity Base Color RoleMaterial")
    normal = next(node for node in material.node_tree.nodes if node.name == "Unity Normal RoleMaterial")
    assert base.image == main
    assert normal.image == bump
    assert any(node.type == "NORMAL_MAP" for node in material.node_tree.nodes)
    records = load_dependency_registry(bpy.context.scene)["dependencies"]
    assert {record["texture_label"] for record in records} == {"Base Color", "Normal"}, records


def main():
    test_prefab_instance_override()
    test_texture_roles()
    print("REGRESSION_FIX_DIAGNOSTIC=" + json.dumps({"prefab_instance_override": "PASS", "texture_roles": "PASS"}, sort_keys=True))
    print("REGRESSION_FIX_OK")


if __name__ == "__main__":
    main()
