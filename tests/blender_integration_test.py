"""Run this file with Blender 5.2.1 --factory-startup --background."""

from __future__ import annotations

import io
import base64
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import traceback

try:
    import bpy
except BaseException:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def add_tar_bytes(archive, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.objects):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def main() -> None:
    import unitypackage_blender_importer as addon

    bpy.context.preferences.view.language = "ja_JP"

    with tempfile.TemporaryDirectory(prefix="unitypackage_blender_test_") as temp:
        temp_path = Path(temp)
        fbx_path = temp_path / "Avatar.fbx"
        clear_scene()

        bpy.ops.mesh.primitive_cube_add()
        mesh_object = bpy.context.object
        mesh_object.name = "AvatarBody"
        mesh_object.shape_key_add(name="Basis")
        smile = mesh_object.shape_key_add(name="Smile")
        smile.data[0].co.x += 0.25

        armature_data = bpy.data.armatures.new("AvatarArmature")
        armature_object = bpy.data.objects.new("AvatarArmature", armature_data)
        bpy.context.scene.collection.objects.link(armature_object)
        bpy.context.view_layer.objects.active = armature_object
        armature_object.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bone = armature_data.edit_bones.new("Root")
        bone.head = (0, 0, 0)
        bone.tail = (0, 0, 1)
        bpy.ops.object.mode_set(mode="OBJECT")
        group = mesh_object.vertex_groups.new(name="Root")
        group.add(list(range(len(mesh_object.data.vertices))), 1.0, "REPLACE")
        modifier = mesh_object.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = armature_object
        mesh_object.select_set(True)
        armature_object.select_set(True)
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.export_scene.fbx(
            filepath=str(fbx_path),
            use_selection=True,
            object_types={"ARMATURE", "MESH"},
            use_custom_props=True,
            add_leaf_bones=False,
            bake_anim=False,
            use_armature_deform_only=False,
        )
        assert fbx_path.is_file() and fbx_path.stat().st_size > 0, "FBX export failed"

        package_path = temp_path / "avatar.unitypackage"
        fbx_guid = "a" * 32
        texture_guid = "b" * 32
        material_guid = "c" * 32
        duplicate_material_guid = "e" * 32
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        material_bytes = f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Material
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_Colors:
    - _Color: {{r: 0.2, g: 0.4, b: 0.8, a: 1}}
    m_Floats:
    - _Metallic: 0.25
    - _Glossiness: 0.75
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {texture_guid}, type: 3}}
""".encode("utf-8")
        duplicate_material_bytes = f"""%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Material
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_SavedProperties:
    m_Colors:
    - _Color: {{r: 0.8, g: 0.2, b: 0.1, a: 1}}
    m_Floats:
    - _Metallic: 0.75
    - _Glossiness: 0.25
    m_TexEnvs: []
""".encode("utf-8")
        large_file_id = 9223372036854775807
        prefab_bytes = f"""%YAML 1.1
--- !u!1 &900
GameObject:
  m_Name: ScenePlacement
--- !u!4 &901
Transform:
  m_GameObject: {{fileID: 900}}
  m_Father: {{fileID: 0}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 1, y: 2, z: 3}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!1 &{large_file_id}
GameObject:
  m_Name: AvatarBody
  m_Component:
  - component: {{fileID: 101}}
  - component: {{fileID: 200}}
--- !u!4 &101
Transform:
  m_GameObject: {{fileID: {large_file_id}}}
  m_Father: {{fileID: 901}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!137 &200
SkinnedMeshRenderer:
  m_GameObject: {{fileID: {large_file_id}}}
  m_Mesh: {{fileID: 4300000, guid: {fbx_guid}, type: 3}}
  m_Materials:
  - {{fileID: 2100000, guid: {material_guid}, type: 2}}
""".encode("utf-8")
        with tarfile.open(package_path, "w:gz") as archive:
            records = [
                (fbx_guid, "Assets/Avatar.fbx", fbx_path.read_bytes()),
                (texture_guid, "Assets/Avatar.png", png_bytes),
                (material_guid, "Assets/Material.mat", material_bytes),
                (duplicate_material_guid, "Assets/Other/Material.mat", duplicate_material_bytes),
                ("d" * 32, "Assets/Avatar.prefab", prefab_bytes),
            ]
            for guid, unity_path, payload in records:
                add_tar_bytes(archive, f"{guid}/asset", payload)
                add_tar_bytes(archive, f"{guid}/pathname", unity_path.encode("utf-8"))
                add_tar_bytes(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode("ascii"))

        clear_scene()
        addon.register()
        result = bpy.ops.import_scene.unitypackage(
            filepath=str(package_path),
            import_mode="RECONSTRUCT",
            use_materials=True,
            use_textures=True,
            keep_extracted=False,
            source_storage_directory=str(temp_path / 'source_archive'),
        )
        assert "FINISHED" in result, result
        source_archive = Path(bpy.context.scene['unitypackage_source_archive'])
        assert source_archive.read_bytes() == package_path.read_bytes()
        assert not Path(bpy.context.scene['unitypackage_extracted_root']).exists()
        # The original and temporary extraction can disappear without losing
        # RAW data. Only this generated fixture is deleted, never user input.
        package_path.unlink()
        meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
        armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
        assert meshes, "No mesh imported"
        assert armatures, "No armature imported"
        assert any(obj.vertex_groups for obj in meshes), "Vertex groups/weights were not imported"
        assert any(obj.data.shape_keys for obj in meshes), "Shape keys were not imported"
        assert bpy.data.images, "Texture was not loaded"
        assert any(image.packed_file for image in bpy.data.images), "Texture was not packed"
        assert any(
            material.node_tree
            and any(node.type == "TEX_IMAGE" and node.image for node in material.node_tree.nodes)
            for material in bpy.data.materials
        ), "Material texture node was not built"
        roots = [obj for obj in bpy.data.objects if obj.get("unity_source_prefab")]
        assert roots, "Prefab root was not created"
        body_occurrence = next(
            obj
            for obj in bpy.data.objects
            if obj.get("unity_prefab_file_id") == str(large_file_id)
        )
        placement = next(o for o in bpy.data.objects if o.get("unity_prefab_file_id") == "900")
        assert body_occurrence.type == "EMPTY", "AvatarBody occurrence was not kept as a semantic object"
        assert body_occurrence.parent == placement, "AvatarBody occurrence parent differs from serialized Transform"
        bpy.context.view_layer.update()
        assert tuple(round(value, 3) for value in body_occurrence.matrix_world.translation) == (1.0, 3.0, -2.0), body_occurrence.matrix_world
        assert placement.parent in roots, "ScenePlacement occurrence is not under the prefab root"

        member_objects = [
            obj for obj in bpy.data.objects
            if obj.get("unity_source_fbx_guid") == fbx_guid
            and obj.get("unity_composition_member_id")
        ]
        skin_meshes = [obj for obj in member_objects if obj.type == "MESH"]
        skin_armatures = [obj for obj in member_objects if obj.type == "ARMATURE"]
        assert len(skin_meshes) == 1, f"Expected one receipt-identified member skin Mesh Object, got {len(skin_meshes)}"
        assert len(skin_armatures) == 1, f"Expected one receipt-identified member Armature Object, got {len(skin_armatures)}"
        skin_mesh = skin_meshes[0]
        skin_armature = skin_armatures[0]
        assert skin_mesh.get("_vapb_fbx_object_receipt_id"), "Native skin Mesh has no FBX realization receipt"
        from unitypackage_blender_importer.blender.fbx_receipt import validate_receipt_continuity
        assert validate_receipt_continuity(skin_mesh), "Copied member lost validated source receipt continuity"
        assert skin_mesh.get("_vapb_fbx_receipt_evidence") == "OBSERVED_OBJECT_COPY"
        assert skin_mesh.get("_vapb_fbx_realization_id") != skin_mesh.get("_vapb_fbx_source_realization_id")
        assert skin_mesh.parent == skin_armature, "Native skin Mesh is not parented to its Armature Object"
        armature_modifiers = [modifier for modifier in skin_mesh.modifiers if modifier.type == "ARMATURE"]
        assert any(modifier.object == skin_armature for modifier in armature_modifiers), "Native skin Mesh has no modifier targeting its Armature Object"
        assert skin_mesh.vertex_groups, "Native skin Mesh has no vertex groups/weights"
        assert skin_mesh.data.shape_keys, "Native skin Mesh has no shape keys"
        assigned = next(
            (material for material in bpy.data.materials
             if material.get("unity_material_guid") == material_guid),
            None,
        )
        assert assigned is not None, "Synthetic Unity material asset was not realized"
        for key in (
            "unity_material_guid",
            "unity_material_path",
            "unity_material_name",
            "unity_shader_guid",
            "unity_shader_name",
            "unity_shader_family",
            "unity_normalized",
        ):
            assert assigned.get(key) is not None, f"Material metadata missing: {key}"
        texture_nodes = [node for node in assigned.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
        assert texture_nodes, "Assigned material has no texture node"
        assert texture_nodes[0].image.get("unity_guid") == texture_guid, "Material texture GUID was not resolved"
        assert texture_nodes[0].image.packed_file or Path(texture_nodes[0].image.filepath).is_file(), "Texture filepath is not valid"
        vector_input = texture_nodes[0].inputs.get("Vector")
        assert vector_input and vector_input.is_linked, "Texture Vector input is not linked"
        assert vector_input.links[0].from_node.type == "TEX_COORD", "Texture Vector is not fed by UV coordinates"
        output_node = next(node for node in assigned.node_tree.nodes if node.type == "OUTPUT_MATERIAL")
        surface_input = output_node.inputs.get("Surface")
        assert surface_input and surface_input.is_linked, "Material Output Surface is not linked"
        assert surface_input.links[0].from_node.type == "BSDF_PRINCIPLED", "Material Output is not fed by Principled BSDF"
        assert output_node.is_active_output, "Material Output is not active"
        assert sum(node.type == "OUTPUT_MATERIAL" for node in assigned.node_tree.nodes) == 1, "Duplicate Material Output was generated"
        assert sum(node.type == "BSDF_PRINCIPLED" for node in assigned.node_tree.nodes) == 1, "Duplicate Principled BSDF was generated"
        # No automatic Unity localID -> FBX UID assertion is possible here.
        # Exercise the GUI operator's explicitly confirmed pairing instead.
        assert not skin_mesh.get('_vapb_renderer_binding')
        binding_root = placement.parent
        projection = json.loads(binding_root['_vapb_renderer_occurrences'])
        assert len(projection['records']) == 1 and not projection['issues']
        occurrence = projection['records'][0]
        assert occurrence['source_key']['renderer_file_id'] == 200
        assert occurrence['owner']['owner_game_object_id'] == large_file_id
        assert occurrence['material_status'] == 'EXACT'
        # Equivalent to Blender's explicit Make Single User Mesh action; the
        # confirmation operator must not silently alter shared slot capacity.
        original_shared_mesh = skin_mesh.data
        original_shared_slots = list(original_shared_mesh.materials)
        skin_mesh.data = skin_mesh.data.copy()
        bpy.context.scene.vapb_renderer_root = binding_root
        bpy.context.scene.vapb_renderer_mesh = skin_mesh
        assert bpy.ops.vapb.confirm_renderer_binding(occurrence_id=occurrence['occurrence_id']) == {'FINISHED'}
        assert list(original_shared_mesh.materials) == original_shared_slots
        confirmed = json.loads(skin_mesh['_vapb_renderer_binding'])
        assert confirmed['evidence'] == 'USER_CONFIRMED'
        from unitypackage_blender_importer.blender.renderer_binding import BindingError, validate_existing_binding
        assert validate_existing_binding(confirmed, binding_root, skin_mesh, bpy.data.objects) == confirmed
        duplicate = skin_mesh.copy()
        bpy.context.scene.collection.objects.link(duplicate)
        try:
            validate_existing_binding(confirmed, binding_root, skin_mesh, bpy.data.objects)
        except BindingError:
            pass
        else:
            raise AssertionError('Duplicated realization authority was accepted')
        bpy.data.objects.remove(duplicate, do_unlink=True)
        root_context = binding_root['_vapb_root_context_id']
        print('OCCURRENCE_SKIN_LINK=USER_CONFIRMED_PASS')
        skin_materials = [slot.material for slot in skin_mesh.material_slots if slot.material]
        if skin_materials:
            assert any(
                material.get("unity_material_guid") == material_guid
                for material in skin_materials
            ), "Native skin material slot conflicts with the synthetic Renderer material identity"
            print("SKIN_MATERIAL_BINDING=OBSERVED")
        else:
            print("SKIN_MATERIAL_BINDING=UNPROVEN")
        material_guids = {material.get("unity_material_guid") for material in bpy.data.materials if material.get("unity_material_guid")}
        assert material_guid in material_guids and duplicate_material_guid in material_guids, "Same-name materials collapsed"
        export_path = temp_path / "private-package-root.fbx"
        export_result = bpy.ops.export_scene.unitypackage_roundtrip(
            filepath=str(export_path),
            selected_only=False,
        )
        assert "FINISHED" in export_result, export_result
        manifest_path = temp_path / "private-package-root.materialmap.json"
        assert manifest_path.is_file(), "Material map sidecar was not written"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema_version"] == 1
        assert manifest["manifest_type"] == "unitypackage_blender_material_map"
        assert len(manifest['renderer_bindings']) == 1
        assert manifest['renderer_bindings'][0] == confirmed
        realized_skin_material_guids = {
            str(material.get("unity_material_guid", ""))
            for material in skin_materials
            if material.get("unity_material_guid")
        }
        assert realized_skin_material_guids.issubset(
            {item["unity_material_guid"] for item in manifest["materials"]}
        ), "Round-trip manifest omitted a realized native skin material"
        if skin_materials:
            assert any(item["material_slot_index"] == 0 for item in manifest["bindings"])
        realization_id = skin_mesh["_vapb_fbx_realization_id"]
        source_realization_id = skin_mesh["_vapb_fbx_source_realization_id"]
        skin_mesh.name = "Renamed native skin"
        saved_scene = temp_path / "receipt_roundtrip.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(saved_scene))
        bpy.ops.wm.open_mainfile(filepath=str(saved_scene))
        assert Path(bpy.context.scene['unitypackage_source_archive']).read_bytes() == source_archive.read_bytes()
        reloaded = [obj for obj in bpy.data.objects
                    if obj.get("_vapb_fbx_realization_id") == realization_id]
        assert len(reloaded) == 1, "Persistent realization identity lost or duplicated"
        assert reloaded[0]["_vapb_fbx_source_realization_id"] == source_realization_id
        assert reloaded[0].parent.type == "ARMATURE"
        assert any(modifier.type == "ARMATURE" and modifier.object == reloaded[0].parent
                   for modifier in reloaded[0].modifiers)
        reloaded_root = next(obj for obj in bpy.data.objects
                             if obj.get('_vapb_root_context_id') == root_context and obj.get('_vapb_renderer_occurrences'))
        assert validate_existing_binding(json.loads(reloaded[0]['_vapb_renderer_binding']),
                                         reloaded_root, reloaded[0], bpy.data.objects)
        assert reloaded[0].material_slots[0].material.get('unity_material_guid') == material_guid
        print('CONFIRMED_BINDING_RENAME_SAVE_RELOAD=PASS')
        print("MEMBER_RECEIPT_RENAME_SAVE_RELOAD=PASS")
        addon.unregister()
    print("BLENDER_INTEGRATION_OK")


def _run_fail_closed(test_main) -> None:
    try:
        test_main()
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


if __name__ == "__main__":
    _run_fail_closed(main)
