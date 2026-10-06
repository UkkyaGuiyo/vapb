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
  - component: {{fileID: 300}}
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
--- !u!33 &300
MeshFilter:
  m_GameObject: {{fileID: 1001}}
  m_Mesh: {{fileID: -31, guid: {fbx_guid}, type: 3}}
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
    source_storage = path.parent / "source_archive"
    return bpy.ops.import_scene.unitypackage(
        filepath=str(path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        keep_extracted=False, group_child=group_child,
        source_storage_directory=str(source_storage),
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
    assert texture_records and texture_records[-1]["target_guid"] == texture_guid
    assert texture_records[-1]["status"] == "RESOLVED_CROSS_PACKAGE", records
    material_data = next(item for item in bpy.data.materials
                         if item.get("unity_material_guid") == "b" * 32)
    images = [node.image for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    assert images and images[0].get("unity_guid") == texture_guid
    before = (len(records), len([node for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE"]))
    resolve_scene_dependencies(bpy.context.scene)
    resolve_scene_dependencies(bpy.context.scene)
    after = (len(load_dependency_registry(bpy.context.scene)["dependencies"]), len([node for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE"]))
    assert before == after
    return {"material_status": material_records[-1]["status"] if material_records else "NOT_CAPTURED",
            "texture_status": texture_records[-1]["status"], "images": len(images), "idempotent": before == after}


def exercise_witnessed_prefab_material(fbx_guid: str, material_guid: str,
                                       *, provider_present: bool) -> str:
    """Exercise projection -> synthetic hash-bound witness -> receipt capture -> bind.

    The ModelWitnessIndex is intentionally an in-memory synthetic test witness
    derived from the actual imported FBX receipt. It is not a Unity observation
    and does not claim the serialized public sidecar validation gate.
    """
    import hashlib
    from unitypackage_blender_importer.blender.dependency_resolver import (
        capture_dependency, load_dependency_registry, resolve_scene_dependencies,
    )
    from unitypackage_blender_importer.blender.model_witness_bridge import (
        reserve_witness_slots, restore_witnessed_prefab_state,
    )
    from unitypackage_blender_importer.unity.model_identity_witness import (
        ModelIdentityRow, ModelWitnessIndex,
    )
    from unitypackage_blender_importer.unity.occurrence_projection import (
        PrefabSource, project_occurrences,
    )
    from unitypackage_blender_importer.unity.prefab_parser import parse_prefab

    native = next(obj for obj in bpy.data.objects
                  if obj.type == "MESH"
                  and str(obj.get("_vapb_fbx_source_asset_guid", "")).lower() == fbx_guid)
    package_id = native["unity_source_package_id"]
    fbx_sha = str(native["_vapb_fbx_source_asset_sha256"])
    model_uid = int(native["_vapb_fbx_model_uid"])
    geometry_uid = int(native["_vapb_fbx_geometry_uid"])
    root_guid, child_guid = "e" * 32, "f" * 32
    with tempfile.TemporaryDirectory(prefix="cpd_witness_") as temp:
        directory = Path(temp)
        root_path = directory / "Root.prefab"
        child_path = directory / "Renderer.prefab"
        root_path.write_text(f"""%YAML 1.1
--- !u!1001 &7001
PrefabInstance:
  m_SourcePrefab: {{fileID: 1001, guid: {child_guid}, type: 3}}
""", encoding="utf-8")
        root_path.with_name(root_path.name + ".meta").write_text(f"guid: {root_guid}\n", encoding="utf-8")
        child_path.write_bytes(prefab(fbx_guid, material_guid))
        child_path.with_name(child_path.name + ".meta").write_text(f"guid: {child_guid}\n", encoding="utf-8")
        root_data, child_data = parse_prefab(root_path), parse_prefab(child_path)
        assert root_data is not None and child_data is not None
        root_source = PrefabSource.from_prefab(root_data, package_id, root_guid)
        child_source = PrefabSource.from_prefab(child_data, package_id, child_guid)
        sources = {(package_id, root_guid): root_source, (package_id, child_guid): child_source}
        root_context = "synthetic-cpd-witness-root"
        projection = project_occurrences(root_source, root_context, lambda pkg, guid: sources.get((pkg, guid)))
        assert projection.issues == [] and len(projection.records) == 1, projection.to_dict()
        record = projection.records[0]
        assert record["mesh"]["mesh_guid"] == fbx_guid
        record["mesh"]["source_package_id"] = package_id
        record["mesh"]["source_sha256"] = fbx_sha
        row = ModelIdentityRow(
            fbx_guid, model_uid, geometry_uid, 1, 1001, 23, 200, -31,
        )
        witness = ModelWitnessIndex([row], {fbx_guid: fbx_sha})

        edge_path = record["instance_edge_path"]
        native["_vapb_root_context_id"] = root_context
        native["_vapb_model_instance_edge_path"] = json.dumps(edge_path, sort_keys=True)
        native["_vapb_renderer_occurrence_id"] = record["occurrence_id"]
        native["unity_source_package_id"] = package_id
        package_sha = hashlib.sha256(root_path.read_bytes()).hexdigest()
        root_object = bpy.data.objects.new("SyntheticWitnessRoot", None)
        bpy.context.scene.collection.objects.link(root_object)
        root_object["_vapb_root_context_id"] = root_context
        root_object["_vapb_witness_package_sha256"] = package_sha
        root_object["_vapb_renderer_occurrences"] = json.dumps(projection.to_dict(), sort_keys=True)
        collection = bpy.data.collections.new("SyntheticWitnessMembers")
        bpy.context.scene.collection.children.link(collection)
        collection.objects.link(native)
        member_objects, bindings, issues, dependencies = restore_witnessed_prefab_state(
            projection.records, [native], witness, collection, bpy.context.view_layer,
            root_data, {}, package_sha, restore_materials=True,
        )
        assert member_objects == [native] and bindings == [(record, native)] and not issues, issues
        assert len(dependencies) == 1 and dependencies[0]["dependency_type"] == "PREFAB_RENDERER_MATERIAL", dependencies
        dependency = dependencies[0]
        assert dependency["identity_bridge"] == "UNITY_MODEL_WITNESS"
        assert dependency["target_guid"] == material_guid
        assert dependency["consumer_fbx_object_receipt_id"] == native["_vapb_fbx_object_receipt_id"]
        assert dependency["consumer_fbx_mesh_receipt_id"] == native["_vapb_fbx_mesh_receipt_id"]
        ready, rejected = reserve_witness_slots(dependencies, bpy.data.objects)
        assert len(ready) == 1 and rejected == [], (ready, rejected)
        capture_dependency(bpy.context.scene, dependency)
        resolve_scene_dependencies(bpy.context.scene)
        stored = [item for item in load_dependency_registry(bpy.context.scene)["dependencies"]
                  if item.get("consumer_occurrence_id") == record["occurrence_id"]]
        assert len(stored) == 1, stored
        bound = stored[0]
        assert bound["dependency_type"] == "PREFAB_RENDERER_MATERIAL"
        assert bound.get("initial_slot_state") is not None
        if provider_present:
            assert bound["status"] == "RESOLVED_CROSS_PACKAGE", bound
            assert bound["resolved_provider_guid"] == material_guid
            assert bound["binding_status"] == "BOUND"
        else:
            assert bound["status"] == "UNRESOLVED", bound
            assert bound["binding_status"] == "UNRESOLVED"
            assert native.material_slots[0].material is None
        return record["occurrence_id"]


def assert_witnessed_prefab_material(occurrence_id: str, material_guid: str) -> dict:
    """Check persisted witness dependency and Object slot, including after reopen."""
    from unitypackage_blender_importer.blender.dependency_resolver import load_dependency_registry
    records = [item for item in load_dependency_registry(bpy.context.scene)["dependencies"]
               if item.get("consumer_occurrence_id") == occurrence_id]
    assert len(records) == 1, records
    record = records[0]
    consumer = next(obj for obj in bpy.data.objects
                    if obj.get("_vapb_fbx_realization_id") == record.get("consumer_native_realization_id"))
    provider = next(item for item in bpy.data.materials
                    if item.get("unity_material_guid") == material_guid
                    and item.get("unity_material_file_id") == str(record["target_file_id"]))
    assert record["dependency_type"] == "PREFAB_RENDERER_MATERIAL"
    assert record["identity_bridge"] == "UNITY_MODEL_WITNESS"
    assert record["status"] == "RESOLVED_CROSS_PACKAGE", record
    assert record["resolved_provider_guid"] == material_guid
    assert record["resolved_provider_package_id"] == provider.get("unity_source_package_id")
    assert record["binding_status"] == "BOUND"
    assert record.get("initial_slot_state") is not None and record.get("applied_slot_state") is not None
    assert consumer.material_slots[record["consumer_slot_index"]].link == "OBJECT"
    assert consumer.material_slots[record["consumer_slot_index"]].material == provider
    return {"dependency": record["dependency_type"], "status": record["status"],
            "provider_guid": record["resolved_provider_guid"], "receipt_bound": True,
            "slot_owner": record["binding_status"], "actual_slot": provider.name}


def run_order(paths: tuple[Path, Path, Path], blend_path: Path) -> dict:
    addon = __import__("unitypackage_blender_importer")
    addon.register()
    from unitypackage_blender_importer.operators import import_unitypackage as module
    module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = lambda self, _context, _paths: False
    geometry_path = next(path for path in paths if path.name == "Geometry.unitypackage")
    geometry_index = paths.index(geometry_path)
    provider_present = any(path.name == "Appearance.unitypackage" for path in paths[:geometry_index])
    witnessed_occurrence = ""
    for path in paths:
        result = import_package(path, group_child=True)
        assert "FINISHED" in result, (path, result)
        if path == geometry_path:
            witnessed_occurrence = exercise_witnessed_prefab_material(
                "a" * 32, "b" * 32, provider_present=provider_present,
            )
    from unitypackage_blender_importer.blender.dependency_resolver import resolve_scene_dependencies
    resolve_scene_dependencies(bpy.context.scene)
    witness_result = assert_witnessed_prefab_material(witnessed_occurrence, "b" * 32)
    result = check_scene(paths[1], "c" * 32)
    result["witnessed_prefab_material"] = witness_result
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False)
    result["reopen"] = check_scene(paths[1], "c" * 32)
    result["witnessed_prefab_material_reopen"] = assert_witnessed_prefab_material(witnessed_occurrence, "b" * 32)
    addon.unregister()
    return result


def run_grouped_synthetic(root: Path, fbx_bytes: bytes, png: bytes, material_guid: str, texture_guid: str) -> dict:
    """Exercise the generic same-folder Import Together path."""
    from unitypackage_blender_importer.blender.identity_registry import load_scene_registry

    # Keep this grouped fixture in its own package neighborhood.  The parent
    # test also builds independent geometry/appearance packages whose repeated
    # synthetic GUIDs must not become providers for this separate scenario.
    root = Path(tempfile.mkdtemp(prefix="cpd_group_"))
    synthetic_avatar = root / "SyntheticAvatar.unitypackage"
    material_provider = root / "SyntheticMaterialProvider.unitypackage"
    textures = root / "SyntheticTextureProvider.unitypackage"
    package(synthetic_avatar, [("e" * 32, "Assets/SyntheticAvatar/Body.fbx", fbx_bytes), ("f" * 32, "Assets/SyntheticAvatar/SyntheticAvatar.prefab", prefab("e" * 32, material_guid))])
    package(material_provider, [(material_guid, "Assets/SyntheticMaterialProvider/SyntheticAvatarMaterial.mat", material(texture_guid))])
    package(textures, [(texture_guid, "Assets/SyntheticTextureProvider/SyntheticAvatar.png", png)])
    addon = __import__("unitypackage_blender_importer")
    addon.register()
    from unitypackage_blender_importer.operators import import_unitypackage as module
    module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = lambda self, _context, _paths: False
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(synthetic_avatar), import_mode="RECONSTRUCT", prefab_choice="AUTO",
        keep_extracted=False, source_storage_directory=str(root / "source_archive"),
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
    material_data = next(item for item in bpy.data.materials
                         if item.get("unity_material_guid") == material_guid)
    images = [node.image for node in material_data.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    assert images and images[0].get("unity_guid") == texture_guid
    graph_names = {node.name for node in material_data.node_tree.nodes}
    assert any("Unity Base Color UV" in name for name in graph_names), graph_names
    assert any("Unity Base Color Mapping" in name for name in graph_names), graph_names
    addon.unregister()
    return {"discovery": discovery["status"], "group_packages": len(package_ids), "material_provider_present": True, "texture_bound": True}


def clear_imported_scene_data() -> None:
    """Remove hidden/template datablocks left by the prior saved test scene."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh_data in list(bpy.data.meshes):
        if mesh_data.users == 0:
            bpy.data.meshes.remove(mesh_data)
    for material_data in list(bpy.data.materials):
        bpy.data.materials.remove(material_data)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)
    bpy.context.scene.pop("unitypackage_identity_registry", None)
    bpy.context.scene.pop("unitypackage_dependency_registry", None)


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
        package(geometry, [(fbx_guid, "Assets/Geometry/Body.fbx", fbx_bytes), (prefab_guid, "Assets/Geometry/Coat.prefab", prefab(fbx_guid, material_guid))])
        package(appearance, [(material_guid, "Assets/Appearance/CoatMaterial.mat", material(texture_guid))])
        package(textures, [(texture_guid, "Assets/Textures/Coat.png", png)])
        grouped = run_grouped_synthetic(root, fbx_bytes, png, material_guid, texture_guid)
        clear_imported_scene_data()
        first = run_order((geometry, appearance, textures), root / "geometry_first.blend")
        clear_imported_scene_data()
        reverse = run_order((appearance, textures, geometry), root / "provider_first.blend")
        print("CPD_DIAGNOSTIC=" + json.dumps({"geometry_first": first, "provider_first": reverse, "grouped_synthetic": grouped}, sort_keys=True))
    print("CROSS_PACKAGE_DEPENDENCY_OK")


if __name__ == "__main__":
    main()
