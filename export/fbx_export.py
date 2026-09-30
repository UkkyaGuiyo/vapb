"""Blender-authoritative FBX payload generation with an explicit preset."""

from __future__ import annotations

from pathlib import Path
from typing import Any


FBX_EXPORT_PRESET = {
    "check_existing": True,
    "use_selection": True,
    "object_types": {"ARMATURE", "MESH", "EMPTY"},
    "global_scale": 1.0,
    "apply_unit_scale": True,
    "apply_scale_options": "FBX_SCALE_NONE",
    "use_space_transform": True,
    "bake_space_transform": False,
    "axis_forward": "-Z",
    "axis_up": "Y",
    "use_mesh_modifiers": False,
    "use_mesh_modifiers_render": False,
    "mesh_smooth_type": "FACE",
    "use_subsurf": False,
    "use_mesh_edges": False,
    "use_tspace": True,
    "use_armature_deform_only": False,
    "add_leaf_bones": False,
    "primary_bone_axis": "Y",
    "secondary_bone_axis": "X",
    "armature_nodetype": "NULL",
    "bake_anim": False,
    "bake_anim_use_all_bones": True,
    "bake_anim_use_nla_strips": False,
    "bake_anim_use_all_actions": False,
    "bake_anim_force_startend_keying": False,
    "bake_anim_step": 1.0,
    "bake_anim_simplify_factor": 1.0,
    "path_mode": "AUTO",
    "embed_textures": False,
    "use_custom_props": True,
    "filepath": "",
}


def export_fbx(filepath: Path, *, bpy_module: Any | None = None, selected_only: bool = True) -> Path:
    if bpy_module is None:
        import bpy  # type: ignore
        bpy_module = bpy
    output = Path(filepath)
    options = dict(FBX_EXPORT_PRESET)
    options["filepath"] = str(output)
    options["use_selection"] = bool(selected_only)
    from .triangle_staging import triangle_export_scene
    context = bpy_module.context
    objects = context.selected_objects if selected_only else context.scene.objects
    objects = [obj for obj in objects if obj.type in options["object_types"]]
    with triangle_export_scene(context, objects, bpy_module=bpy_module):
        options["use_selection"] = True
        if bpy_module.ops.export_scene.fbx(**options) != {"FINISHED"}:
            raise RuntimeError("FBX export was cancelled")
    return output
