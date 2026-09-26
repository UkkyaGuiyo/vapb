"""Read-only preview plus explicit apply controls in the VAPB sidebar."""

from __future__ import annotations

import bpy  # type: ignore


class VAPB_PT_semantic_cleanup(bpy.types.Panel):
    bl_label = 'Semantic Cleanup'
    bl_idname = 'VAPB_PT_semantic_cleanup'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VAPB'

    def draw(self, context):
        layout = self.layout
        state = context.scene.vapb_semantic_cleanup
        layout.label(text='対象: 選択中のMesh / Armature')
        layout.prop(state, 'materials')
        layout.prop(state, 'bones')
        layout.operator('vapb.semantic_cleanup_preview')
        for item in state.preview_items:
            box = layout.box()
            box.label(text=f'{item.status}: {item.owner_name} / {item.key}')
            box.label(text='Material枠' if item.kind == 'MATERIAL_SLOT' else 'Bone')
            if item.reason:
                box.label(text=item.reason)
        if state.preview_fingerprint:
            layout.operator('vapb.semantic_cleanup_apply')
        layout.label(text='未解決のUnity/VRC参照と共有データは保護')


SEMANTIC_CLEANUP_PANEL_CLASSES = (VAPB_PT_semantic_cleanup,)
