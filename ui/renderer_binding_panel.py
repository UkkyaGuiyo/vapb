"""A narrow native Blender panel for explicit Renderer occurrence choices."""

from __future__ import annotations

import bpy

from ..operators.renderer_binding import projection_records


class VAPB_PT_renderer_binding(bpy.types.Panel):
    bl_label = "VAPB Renderer対応"
    bl_idname = "VAPB_PT_renderer_binding"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VAPB"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "vapb_renderer_root", text="Prefabルート")
        layout.prop(context.scene, "vapb_renderer_mesh", text="メッシュオブジェクト")
        root = context.scene.vapb_renderer_root
        layout.label(text="名前だけでは自動対応しません。実物を確認してください")
        for record in projection_records(root):
            box = layout.box()
            kind = "Skinned Mesh Renderer" if record.get("renderer_class_id") == 137 else "Mesh Renderer"
            box.label(text=f"{record.get('owner_name', '名称なし')} / {kind}")
            box.label(text=f"素材: {record.get('material_status', 'UNKNOWN')}")
            box.operator_context = 'INVOKE_DEFAULT'
            button = box.operator("vapb.confirm_renderer_binding", text="このRendererを確定")
            button.occurrence_id = record.get("occurrence_id", "")


CLASSES = (VAPB_PT_renderer_binding,)


def register_scene_properties():
    bpy.types.Scene.vapb_renderer_root = bpy.props.PointerProperty(type=bpy.types.Object,
        poll=lambda _self, obj: bool(obj.get('_vapb_renderer_occurrences')))
    bpy.types.Scene.vapb_renderer_mesh = bpy.props.PointerProperty(type=bpy.types.Object,
        poll=lambda _self, obj: obj.type == 'MESH')


def unregister_scene_properties():
    del bpy.types.Scene.vapb_renderer_mesh
    del bpy.types.Scene.vapb_renderer_root
