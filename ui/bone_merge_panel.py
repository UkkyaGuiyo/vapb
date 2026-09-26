"""Semantic Bone Merge controls in the VAPB sidebar."""

from __future__ import annotations

import bpy  # type: ignore


class VAPB_PT_bone_merge(bpy.types.Panel):
    bl_label = 'Bone Merge'
    bl_idname = 'VAPB_PT_bone_merge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VAPB'

    def draw(self, context):
        layout = self.layout
        state = context.scene.vapb_bone_merge
        layout.prop(state, 'reference')
        layout.prop(state, 'source')
        layout.operator('vapb.bone_merge_candidates')
        layout.label(text='出所一致は候補のみ。各 Bone を確認')
        for row in state.mappings:
            box = layout.box()
            box.label(text=f'B: {row.source_name}')
            line = box.row(align=True)
            line.prop(row, 'classification', text='')
            if row.classification == 'EQUIVALENT':
                if state.reference is not None and state.reference.type == 'ARMATURE':
                    box.prop_search(row, 'target_name', state.reference.data, 'bones', text='A Bone')
                else:
                    box.prop(row, 'target_name')
            box.prop(row, 'confirmed')
        layout.label(text='未確定・衝突・未対応参照があれば停止')
        layout.label(text='B は保持。Weight Transfer は実行しません')
        layout.operator('vapb.bone_merge_preview')
        layout.operator('vapb.bone_merge_apply')


BONE_MERGE_PANEL_CLASSES = (VAPB_PT_bone_merge,)
