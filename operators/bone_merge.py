"""Explicit Japanese UI controls for conservative semantic Bone Merge."""

from __future__ import annotations

import bpy  # type: ignore

from ..blender.bone_merge import candidate_mappings, prepare_merge, apply_merge


def _armature(_self, obj):
    return obj.type == 'ARMATURE'


def _clear(state, _context):
    state.mappings.clear()


def _unconfirm(row, _context):
    row.confirmed = False


class VAPB_PG_bone_merge_mapping(bpy.types.PropertyGroup):
    source_name: bpy.props.StringProperty(name="B Bone")
    classification: bpy.props.EnumProperty(name="分類", items=(
        ('AMBIGUOUS', '未確定', '参照を保護し、実行を停止'),
        ('EQUIVALENT', 'A と同等', '確認した A Bone に対応'),
        ('B_ONLY', 'B 固有', 'A に移植する'),
    ), default='AMBIGUOUS', update=_unconfirm)
    target_name: bpy.props.StringProperty(name="A Bone", update=_unconfirm)
    confirmed: bpy.props.BoolProperty(name="対応を確認", default=False)


class VAPB_PG_bone_merge(bpy.types.PropertyGroup):
    reference: bpy.props.PointerProperty(name="基準 Armature A", type=bpy.types.Object,
                                         poll=_armature, update=_clear)
    source: bpy.props.PointerProperty(name="統合対象 Armature B", type=bpy.types.Object,
                                      poll=_armature, update=_clear)
    mappings: bpy.props.CollectionProperty(type=VAPB_PG_bone_merge_mapping)


def register_bone_merge_properties():
    bpy.types.Scene.vapb_bone_merge = bpy.props.PointerProperty(type=VAPB_PG_bone_merge)


def unregister_bone_merge_properties():
    del bpy.types.Scene.vapb_bone_merge


class VAPB_OT_bone_merge_candidates(bpy.types.Operator):
    bl_idname = 'vapb.bone_merge_candidates'
    bl_label = 'Bone 対応候補を読み込む'
    bl_description = 'FBX 出所の一致だけを候補表示します。分類と対応は個別確認が必要です'

    def execute(self, context):
        state = context.scene.vapb_bone_merge
        a, b = state.reference, state.source
        if a is None or b is None or a is b or a.type != 'ARMATURE' or b.type != 'ARMATURE':
            self.report({'ERROR'}, '異なる Armature A/B を選択してください')
            return {'CANCELLED'}
        state.mappings.clear()
        for source, target, classification in candidate_mappings(a.data.bones, b.data.bones):
            row = state.mappings.add()
            row.source_name = source
            row.target_name = target
            row.classification = classification
            row.confirmed = False
        self.report({'INFO'}, f'候補 {len(state.mappings)} 件。分類と対応を確認してください')
        return {'FINISHED'}


class VAPB_OT_bone_merge_preview(bpy.types.Operator):
    bl_idname = 'vapb.bone_merge_preview'
    bl_label = 'Bone Merge をプレビュー'
    bl_description = 'データを変更せず、移植数と付替え対象を確認します'

    def execute(self, context):
        try:
            plan = prepare_merge(context.scene.vapb_bone_merge.reference,
                                 context.scene.vapb_bone_merge.source,
                                 context.scene.vapb_bone_merge.mappings, context.scene)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f"確認済み {len(plan['remap'])} Bone / B 固有移植 {len(plan['b_only'])} / "
                              f"付替え Mesh {len(plan['attached'])}。B は保持します")
        return {'FINISHED'}


class VAPB_OT_bone_merge_apply(bpy.types.Operator):
    bl_idname = 'vapb.bone_merge_apply'
    bl_label = '確認した Bone Merge を実行'
    bl_description = '確認済み対応だけを実行し、B を保持します。Undo 対応'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, 'オブジェクトモードで実行してください')
            return {'CANCELLED'}
        state = context.scene.vapb_bone_merge
        try:
            plan = prepare_merge(state.reference, state.source, state.mappings, context.scene)
            added, updated = apply_merge(plan)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        except Exception as exc:
            self.report({'ERROR'}, f'実行に失敗しました: {type(exc).__name__}。参照を確認してください')
            return {'CANCELLED'}
        self.report({'INFO'}, f'B 固有 Bone {added} 件移植、Mesh {updated} 件付替え。B は保持しました')
        return {'FINISHED'}


BONE_MERGE_CLASSES = (
    VAPB_PG_bone_merge_mapping, VAPB_PG_bone_merge,
    VAPB_OT_bone_merge_candidates, VAPB_OT_bone_merge_preview, VAPB_OT_bone_merge_apply,
)
