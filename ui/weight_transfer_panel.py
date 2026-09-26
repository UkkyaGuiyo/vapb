"""Manual weight transfer controls in the 3D View sidebar."""

from __future__ import annotations

import bpy  # type: ignore


class VAPB_PT_weight_transfer(bpy.types.Panel):
    bl_label = "Weight Transfer"
    bl_idname = "VAPB_PT_weight_transfer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VAPB'

    def draw(self, context):
        layout = self.layout
        state = context.scene.vapb_weight_transfer
        layout.prop(state, 'source')
        layout.prop(state, 'armature')
        layout.prop(state, 'target')
        layout.label(text="元メッシュ形状で補間・オブジェクトモードで実行")
        layout.operator('vapb.weight_mappings')
        layout.label(text="名前一致は候補のみ。各対応を確認")
        for mapping in state.mappings:
            row = layout.row(align=True)
            row.prop(mapping, 'confirmed', text='')
            row.label(text=mapping.source_name)
            row.prop(mapping, 'target_name', text='→')
        layout.prop(state, 'mode')
        layout.prop(state, 'scope')
        layout.prop(state, 'blend', slider=True)
        layout.prop(state, 'max_distance')
        layout.prop(state, 'guard_declared_plane')
        if state.guard_declared_plane:
            layout.label(text="宣言: A参照骨ローカル X=0 が左右境界")
            layout.label(text="|X| ≤ 0.00001 は境界上として警告しません")
            layout.label(text="越境頂点は保護。解剖学的左右は自動判定しません")
        if state.mode == 'REPLACE':
            layout.label(text="置換: 対応先の既存値を補間値へ")
        elif state.mode == 'MERGE':
            layout.label(text="大きい値を保持: 既存値と補間値の大きい方")
        else:
            layout.label(text="未設定のみ補充: 既存値ゼロだけ追加")
        layout.label(text="未対応グループ・ロック済みは保持")
        layout.label(text="ウェイト合計は自動正規化しません")
        layout.label(text="距離超過の頂点は変更しません")
        layout.operator('vapb.weight_preview')
        layout.operator('vapb.weight_select_unresolved')
        layout.operator('vapb.weight_apply')


WEIGHT_TRANSFER_PANEL_CLASSES = (VAPB_PT_weight_transfer,)
