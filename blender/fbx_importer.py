"""FBX import wrapper preserving Blender's native armature/weight/shape-key path."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import bpy  # type: ignore


def import_fbx(path: Path, use_custom_props: bool = True, source_package_id: str = "") -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(
        filepath=str(path),
        use_manual_orientation=False,
        use_custom_normals=True,
        use_image_search=False,
        use_anim=True,
        use_custom_props=use_custom_props,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
        use_prepost_rot=True,
    )
    imported = [obj for obj in bpy.data.objects if obj not in before]
    for obj in imported:
        obj["unity_source_fbx"] = str(path)
        if source_package_id:
            obj["unity_source_package_id"] = source_package_id
    return imported


def import_fbx_files(paths: Iterable[Path], source_package_id: str = "") -> list[bpy.types.Object]:
    imported: list[bpy.types.Object] = []
    for path in paths:
        try:
            imported.extend(import_fbx(path, source_package_id=source_package_id))
        except (OSError, RuntimeError) as exc:
            print(f"[UnityPackage Importer] FBX import failed: {path}: {exc}")
    return imported


def apply_import_options(
    imported_objects: Iterable[bpy.types.Object],
    use_armatures: bool = True,
    use_bone_weights: bool = True,
    use_shape_keys: bool = True,
) -> list[bpy.types.Object]:
    """Apply the optional data filters after native FBX import.

    The FBX importer itself does not expose separate switches for all three
    data types in Blender 4.2.  The default path leaves the imported data
    untouched; explicit unchecked options remove only the corresponding data
    from the newly imported objects.
    """
    imported = list(imported_objects)
    mesh_objects = [obj for obj in imported if obj.type == "MESH"]
    if not use_bone_weights:
        for obj in mesh_objects:
            for vertex_group in list(obj.vertex_groups):
                obj.vertex_groups.remove(vertex_group)
            for modifier in list(obj.modifiers):
                if modifier.type == "ARMATURE":
                    obj.modifiers.remove(modifier)
    if not use_shape_keys:
        for obj in mesh_objects:
            if not obj.data.shape_keys:
                continue
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            try:
                bpy.ops.object.shape_key_remove(all=True)
            except RuntimeError as exc:
                print(f"[UnityPackage Importer] Shape Key removal skipped for {obj.name}: {exc}")
    if not use_armatures:
        for obj in imported:
            if obj.type == "ARMATURE":
                bpy.data.objects.remove(obj, do_unlink=True)
        imported = [obj for obj in imported if obj.type != "ARMATURE"]
    return imported
