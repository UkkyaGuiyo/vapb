"""Explicit preview and undoable apply for selected-object semantic cleanup."""

from __future__ import annotations

import bpy  # type: ignore

from ..blender.semantic_cleanup import analyze_cleanup, apply_cleanup


_REASON_LABELS = {
    'POLYGON': '面で使用中',
    'POLYGON_INDEX_INVALID': '面の割当を確認できません',
    'OBJECT_MATERIAL_LINK': 'オブジェクト側で共有・指定中',
    'MATERIAL_STATE': 'マテリアルの参照状態を確認できません',
    'SHARED_OR_LINKED_DATA': '共有またはリンクされたデータ',
    'ANIMATION_UNRESOLVED': 'アニメーション参照を確認できません',
    'MODIFIER_UNRESOLVED': 'モディファイア参照を確認できません',
    'UNITY_VRC_STATE_UNRESOLVED': 'Unity/VRC の保存済み参照を確認できません',
    'EXTERNAL_SOURCE_REFERENCE_UNRESOLVED': '選択範囲外の参照を確認できません',
    'WEIGHT': '頂点ウェイトで使用中',
    'USED_DESCENDANT': '使用中の子 Bone の祖先',
    'CHILD_BONE_PRESENT': '子 Bone が残っています',
    'BONE_PARENT': 'オブジェクトの親 Bone',
    'BONE_PARENT_UNRESOLVED': 'Bone 親子参照を確認できません',
    'BONE_SOURCE_STATE': 'Bone の保存済み参照を確認できません',
    'CONSTRAINT_OWNER': '制約の所有 Bone',
    'CONSTRAINT_TARGET': '制約の対象 Bone',
    'CONSTRAINT_UNRESOLVED': '制約の参照を確認できません',
    'EXTERNAL_CONSTRAINT_TARGET': '選択範囲外の制約対象',
    'EXTERNAL_DRIVER_UNRESOLVED': '選択範囲外のドライバー参照を確認できません',
    'EXTERNAL_OR_SHARED_RIG_USER': '選択範囲外または共有のリグ利用',
    'ENVELOPE_DEFORMATION_UNRESOLVED': 'Bone エンベロープ変形の影響を確認できません',
}


_UNKNOWN_REASONS = {
    'POLYGON_INDEX_INVALID', 'MATERIAL_STATE', 'SHARED_OR_LINKED_DATA',
    'ANIMATION_UNRESOLVED', 'MODIFIER_UNRESOLVED', 'UNITY_VRC_STATE_UNRESOLVED',
    'EXTERNAL_SOURCE_REFERENCE_UNRESOLVED', 'BONE_PARENT_UNRESOLVED',
    'BONE_SOURCE_STATE', 'CONSTRAINT_UNRESOLVED', 'EXTERNAL_DRIVER_UNRESOLVED',
    'EXTERNAL_OR_SHARED_RIG_USER', 'ENVELOPE_DEFORMATION_UNRESOLVED',
}


class VAPB_PG_cleanup_preview_item(bpy.types.PropertyGroup):
    kind: bpy.props.StringProperty()
    owner_name: bpy.props.StringProperty()
    key: bpy.props.StringProperty()
    status: bpy.props.StringProperty()
    reason: bpy.props.StringProperty()


class VAPB_PG_semantic_cleanup(bpy.types.PropertyGroup):
    materials: bpy.props.BoolProperty(name='未使用マテリアル枠', default=True)
    bones: bpy.props.BoolProperty(name='未使用の末端Bone', default=True)
    preview_items: bpy.props.CollectionProperty(type=VAPB_PG_cleanup_preview_item)
    preview_fingerprint: bpy.props.StringProperty()


def register_semantic_cleanup_properties():
    bpy.types.Scene.vapb_semantic_cleanup = bpy.props.PointerProperty(type=VAPB_PG_semantic_cleanup)


def unregister_semantic_cleanup_properties():
    del bpy.types.Scene.vapb_semantic_cleanup


def _plan(context):
    state = context.scene.vapb_semantic_cleanup
    return analyze_cleanup(context.selected_objects, materials=state.materials, bones=state.bones)


class VAPB_OT_semantic_cleanup_preview(bpy.types.Operator):
    bl_idname = 'vapb.semantic_cleanup_preview'
    bl_label = 'Cleanup 候補を解析'
    bl_description = '選択したMesh/Armatureだけを読み取り、候補・保持・未解決を表示します'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_objects)

    def execute(self, context):
        state = context.scene.vapb_semantic_cleanup
        state.preview_items.clear()
        state.preview_fingerprint = ''
        try:
            plan = _plan(context)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        for decision in plan.decisions:
            entry = state.preview_items.add()
            entry.kind = decision.kind
            entry.owner_name = decision.owner.name
            entry.key = decision.key
            entry.reason = ('、'.join(_REASON_LABELS.get(reason, '参照状態を確認できません')
                                     for reason in decision.reasons)
                            if decision.reasons else '使用参照なし')
            entry.status = ('候補' if decision.candidate else
                            '未解決・保護' if any(reason in _UNKNOWN_REASONS
                                                for reason in decision.reasons) else '保持')
        state.preview_fingerprint = plan.fingerprint()
        self.report({'INFO'}, f'候補 {len(plan.candidates)} 件 / 解析 {len(plan.decisions)} 件')
        return {'FINISHED'}


class VAPB_OT_semantic_cleanup_apply(bpy.types.Operator):
    bl_idname = 'vapb.semantic_cleanup_apply'
    bl_label = '候補を削除（Undo可）'
    bl_description = '直前のPreviewと同じ選択・状態だけに適用します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_objects)

    def execute(self, context):
        state = context.scene.vapb_semantic_cleanup
        if not state.preview_fingerprint:
            self.report({'ERROR'}, '先に候補を解析してください')
            return {'CANCELLED'}
        try:
            plan = _plan(context)
            if plan.fingerprint() != state.preview_fingerprint:
                raise ValueError('選択または参照状態がPreviewから変わりました。再解析してください')
            removed = apply_cleanup(context, plan)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        state.preview_items.clear()
        state.preview_fingerprint = ''
        self.report({'INFO'}, f'{removed} 件を削除しました。BlenderのUndoで戻せます')
        return {'FINISHED'}


SEMANTIC_CLEANUP_CLASSES = (
    VAPB_PG_cleanup_preview_item, VAPB_PG_semantic_cleanup,
    VAPB_OT_semantic_cleanup_preview, VAPB_OT_semantic_cleanup_apply,
)
