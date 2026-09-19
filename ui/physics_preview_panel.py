"""3D View sidebar controls for the approximate PhysBone preview."""

from __future__ import annotations

import bpy  # type: ignore
from bpy.props import BoolProperty, FloatProperty, PointerProperty  # type: ignore

from ..blender.physbone_runtime import get_controller, shutdown


class VAPB_PhysicsPreviewProperties(bpy.types.PropertyGroup):
    enabled: BoolProperty(name="Enable Physics Preview", default=False)
    strength: FloatProperty(name="Preview Strength", default=1.0, min=0.0, max=2.0)
    gravity_scale: FloatProperty(name="Gravity Scale", default=1.0, min=0.0, max=3.0)


class VAPB_OT_physics_preview_enable(bpy.types.Operator):
    bl_idname = "vapb.physics_preview_enable"
    bl_label = "Enable Physics Preview"
    bl_description = "Run the approximate PhysBone preview on identity-matched chains"

    def execute(self, context):
        props = context.scene.vapb_physics_preview
        controller = get_controller()
        if controller.running:
            controller.disable()
            props.enabled = False
        else:
            controller.enable(context.scene)
            props.enabled = controller.running
        return {'FINISHED'}


class VAPB_OT_physics_preview_reset(bpy.types.Operator):
    bl_idname = "vapb.physics_preview_reset"
    bl_label = "Reset Simulation"

    def execute(self, context):
        get_controller().reset()
        return {'FINISHED'}


class VAPB_PT_physics_preview(bpy.types.Panel):
    bl_idname = "VAPB_PT_physics_preview"
    bl_label = "Physics Preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VAPB"

    def draw(self, context):
        layout = self.layout
        props = context.scene.vapb_physics_preview
        controller = get_controller()
        layout.label(text="VAPB Physics Preview")
        layout.label(text=f"Detected PhysBones: {controller.detected_count}")
        layout.label(text=f"Matched Chains: {controller.matched_count}")
        layout.label(text=f"Unmatched: {controller.unmatched}")
        layout.operator("vapb.physics_preview_enable", text="Disable Preview" if controller.running else "Enable Preview")
        layout.operator("vapb.physics_preview_reset")
        layout.prop(props, "strength")
        layout.prop(props, "gravity_scale")
        layout.label(text=f"Status: {controller.status}")
        if controller.chains:
            chain = controller.chains[0]
            layout.separator()
            layout.label(text=f"Root: {chain.root_name}")
            layout.label(text=f"Bone count: {chain.bone_count}")
            layout.label(text=f"Match confidence: {chain.match_confidence}")
            layout.label(text=f"Collider count: {chain.collider_count}")
        layout.separator()
        layout.label(text="Source: VRC PhysBone metadata preserved")
        layout.label(text="Approximate preview; not VRChat simulation")


def register_properties():
    bpy.types.Scene.vapb_physics_preview = PointerProperty(type=VAPB_PhysicsPreviewProperties)


def unregister_properties():
    shutdown()
    if hasattr(bpy.types.Scene, "vapb_physics_preview"):
        del bpy.types.Scene.vapb_physics_preview


PHYSICS_PREVIEW_CLASSES = (
    VAPB_PhysicsPreviewProperties,
    VAPB_OT_physics_preview_enable,
    VAPB_OT_physics_preview_reset,
    VAPB_PT_physics_preview,
)
