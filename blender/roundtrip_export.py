"""Blender FBX export with a Unity Material sidecar manifest."""

from __future__ import annotations

from pathlib import Path

import bpy  # type: ignore
from bpy.props import BoolProperty, StringProperty  # type: ignore
from bpy_extras.io_utils import ExportHelper  # type: ignore

from .roundtrip_manifest import build_material_manifest, write_material_manifest


def _export_objects(selected_only: bool):
    if selected_only:
        return [obj for obj in bpy.context.selected_objects if obj.type in {"MESH", "ARMATURE", "EMPTY"}]
    return [obj for obj in bpy.context.scene.objects if obj.type in {"MESH", "ARMATURE", "EMPTY"}]


class UNITYPACKAGE_OT_export_roundtrip(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.unitypackage_roundtrip"
    bl_label = "FBX + Unity Material Map"
    bl_description = "Export an avatar FBX and a Unity Material reconnect manifest"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={"HIDDEN"})
    selected_only: BoolProperty(
        name="Selected Objects Only",
        default=True,
        description="Export the selected avatar objects; include Mesh, Armature, and Empty objects",
    )

    def execute(self, context):
        fbx_path = Path(self.filepath)
        if fbx_path.suffix.lower() != ".fbx":
            fbx_path = fbx_path.with_suffix(".fbx")
        if not fbx_path.parent.exists():
            self.report({"ERROR"}, f"Output directory does not exist: {fbx_path.parent}")
            return {"CANCELLED"}

        objects = _export_objects(self.selected_only)
        mesh_objects = [obj for obj in objects if obj.type == "MESH"]
        if not mesh_objects:
            self.report({"ERROR"}, "Select at least one mesh object for avatar export")
            return {"CANCELLED"}

        try:
            manifest = build_material_manifest(objects, fbx_path, reference_objects=bpy.data.objects)
            bpy.ops.export_scene.fbx(
                filepath=str(fbx_path),
                check_existing=True,
                use_selection=self.selected_only,
                object_types={"ARMATURE", "MESH", "EMPTY"},
                use_mesh_modifiers=False,
                use_custom_props=True,
                add_leaf_bones=False,
                use_armature_deform_only=False,
                bake_anim=False,
                bake_space_transform=False,
                path_mode="AUTO",
                embed_textures=False,
            )
            if not fbx_path.is_file():
                raise RuntimeError("Blender FBX export did not create the requested file")
            write_material_manifest(objects, fbx_path, manifest)
        except (OSError, RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, f"Round-trip export failed: {exc}")
            return {"CANCELLED"}

        warning_count = len(manifest.get("warnings", []))
        suffix = f" with {warning_count} warning(s)" if warning_count else ""
        self.report({"INFO"}, f"Exported FBX and Material Map{suffix}: {fbx_path.name}")
        return {"FINISHED"}


ROUNDTRIP_EXPORT_CLASSES = (UNITYPACKAGE_OT_export_roundtrip,)


def menu_func_export(self, _context):
    self.layout.operator(
        UNITYPACKAGE_OT_export_roundtrip.bl_idname,
        text="FBX + Unity Material Map (.fbx)",
    )
