"""Public synthetic unchanged and replacement Mesh final-state exports."""

from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    phase, source_text, blend_text, output_text = sys.argv[sys.argv.index("--") + 1:][:4]
    source, blend, output = map(Path, (source_text, blend_text, output_text))
    if phase in {"red", "create", "unchanged"}:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    import unitypackage_blender_importer as addon
    addon.register()
    try:
        if phase in {"red", "create", "unchanged"}:
            assert bpy.ops.import_scene.unitypackage(
                filepath=str(source), import_mode="RECONSTRUCT", use_materials=True,
                use_textures=True, keep_extracted=False,
                source_storage_directory=str(blend.parent / "source_archive")) == {"FINISHED"}
            materials = [mat for mat in bpy.data.materials
                         if mat.get("unity_material_guid") and mat.get("unity_material_file_id")]
            assert len(materials) == 1, len(materials)
            material = materials[0]
            images = [node.image for node in material.node_tree.nodes
                      if node.type == "TEX_IMAGE" and node.image is not None]
            assert len(images) == 1 and images[0].get("unity_guid"), "Unity Texture not imported"
            source_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
            assert source_meshes
            if phase == "unchanged":
                candidates = [obj for obj in source_meshes if obj.data.uv_layers.active is not None]
                assert candidates
                cube = candidates[0]
                geometry_before = tuple(tuple(vertex.co) for vertex in cube.data.vertices)
                if not cube.data.materials:
                    cube.data.materials.append(material)
                else:
                    cube.data.materials[0] = material
                for obj in bpy.context.selected_objects:
                    obj.select_set(False)
                cube.select_set(True)
                bpy.context.view_layer.objects.active = cube
                assert cube.data.uv_layers.active is not None
            else:
                for obj in source_meshes:
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.ops.mesh.primitive_cube_add()
                cube = bpy.context.object
                cube.name = "User Replacement Cube"
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.smart_project()
                bpy.ops.object.mode_set(mode="OBJECT")
                assert cube.data.uv_layers.active is not None
                cube.data.materials.append(material)
                for key in ("_vapb_renderer_binding", "_vapb_fbx_realization_id",
                            "_vapb_fbx_mesh_receipt_id", "_vapb_occurrence_id"):
                    assert key not in cube, key
            bpy.ops.wm.save_as_mainfile(filepath=str(blend))
            if phase == "red":
                from unitypackage_blender_importer.operators.export_unitypackage import export_static_package
                try:
                    export_static_package(bpy.context, cube, output)
                except (ValueError, KeyError) as error:
                    assert not output.exists()
                    print("FINAL_STATE_SOURCE_BOUND_RED", type(error).__name__, str(error))
                    return
                raise AssertionError("source-bound export unexpectedly accepted a new Cube")
        else:
            assert phase == "reopen"
            cubes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
            assert len(cubes) == 1
            cube = cubes[0]
            assert cube.data.uv_layers.active is not None
            assert len(cube.material_slots) == 1
        object_id_before = cube.get("_vapb_export_object_id")
        material_id_before = cube.material_slots[0].material.get("_vapb_export_material_id")
        assert bpy.ops.export_scene.vapb_final_state_unitypackage(filepath=str(output)) == {"FINISHED"}
        assert output.is_file()
        assert cube.get("_vapb_export_object_id") == object_id_before, "EXPORT_MUTATED_SOURCE_OBJECT_ID"
        assert cube.material_slots[0].material.get("_vapb_export_material_id") == material_id_before, "EXPORT_MUTATED_SOURCE_MATERIAL_ID"
        from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
        import json
        assets = RawAssetRepository(output).read_all(output.read_bytes())
        manifest = json.loads(next(a.asset_bytes for a in assets if a.pathname == "Assets/VAPBExport/manifest.json"))
        exported_id = manifest["export_roots"][0]
        assert exported_id.startswith("VAPB-OBJ-")
        if object_id_before: assert exported_id == object_id_before
        fbx = next(a.asset_bytes for a in assets if a.pathname.lower().endswith(".fbx"))
        assert exported_id.encode() in fbx
        if phase == "unchanged":
            assert geometry_before == tuple(tuple(vertex.co) for vertex in cube.data.vertices)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print("FINAL_STATE_PACKAGE_PASS", phase)
    finally:
        addon.unregister()


if __name__ == "__main__":
    main()
