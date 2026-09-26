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
    cleanup_materials: BoolProperty(
        name="出力のみ: 未使用のMaterial枠を整理", default=False,
        description="参照を確認できた未使用枠だけを出力用コピーから除外。編集中のsceneは変更しません",
    )
    cleanup_bones: BoolProperty(
        name="出力のみ: 未使用Boneを整理", default=False,
        description="Weight・祖先・親子関係・保存stateなどの参照が不明なBoneは保持します",
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
            def export_current(selected_only):
                result = bpy.ops.export_scene.fbx(
                    filepath=str(fbx_path),
                    check_existing=True,
                    use_selection=selected_only,
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
                if result != {'FINISHED'}:
                    raise RuntimeError('FBX export was cancelled')

            if self.cleanup_materials or self.cleanup_bones:
                from .semantic_cleanup import cleanup_export_objects
                references = tuple(bpy.data.objects)
                with cleanup_export_objects(context, objects, materials=self.cleanup_materials,
                                            bones=self.cleanup_bones) as staged:
                    staged_references = [staged.source_to_copy.get(obj, obj) for obj in references]
                    manifest = build_material_manifest(staged.objects, fbx_path,
                                                       reference_objects=staged_references)
                    manifest['cleanup'] = {
                        'scope': 'EXPORT_COPIES_ONLY', 'removed_count': staged.removed_count,
                        'unknown_references': 'PROTECTED',
                    }
                    layer = staged.scene.view_layers[0]
                    with context.temp_override(scene=staged.scene, view_layer=layer,
                                               selected_objects=list(staged.objects),
                                               selected_editable_objects=list(staged.objects),
                                               active_object=staged.objects[0], object=staged.objects[0]):
                        for obj in staged.objects:
                            obj.select_set(True)
                        export_current(True)
            else:
                manifest = build_material_manifest(objects, fbx_path, reference_objects=bpy.data.objects)
                export_current(self.selected_only)
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
