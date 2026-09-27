"""Persistent Blender view of existing import projection and dependency state."""

from __future__ import annotations

from collections import Counter

import bpy

from ..blender.import_outcome import scene_import_outcome

_CATEGORY_LABELS = {
    "UNRESOLVED_IDENTITY": "Mesh対応未解決",
    "MISSING_DEPENDENCY": "Asset不足",
    "AMBIGUOUS": "候補が複数",
    "UNSUPPORTED": "未対応",
    "ERROR": "エラー",
    "PARTIAL": "手動変更を保持",
}


def _label_lines(layout, value, *, icon="NONE"):
    # Blender labels do not wrap. Keep every line short in the narrow N panel.
    remaining = value
    first = True
    while remaining:
        end = min(17, len(remaining))
        if end < len(remaining) and remaining[end - 1].isascii() and remaining[end - 1].isalnum() and remaining[end].isascii() and remaining[end].isalnum():
            word_start = end - 1
            while word_start > 0 and remaining[word_start - 1].isascii() and remaining[word_start - 1].isalnum():
                word_start -= 1
            if word_start >= 7:
                end = word_start
        layout.label(text=remaining[:end], icon=icon if first else "NONE")
        remaining = remaining[end:]
        first = False


class VAPB_PT_import_outcome(bpy.types.Panel):
    bl_label = "VAPB Import結果"
    bl_idname = "VAPB_PT_import_outcome"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VAPB"
    bl_order = -1

    def draw(self, context):
        layout = self.layout
        outcome = scene_import_outcome(context.scene)
        counts = outcome["counts"]
        if outcome["overall"] == "UNVERIFIED":
            layout.label(text="このSceneにImport判定記録はありません")
            return
        if outcome["overall"] == "SUCCESS":
            _label_lines(layout, "このSceneに記録された未解決項目はありません", icon="CHECKMARK")
            _label_lines(layout, "Avatar全体の再現保証ではありません")
            return

        layout.label(text="このSceneのImport記録")
        layout.label(text="一部の復元を保留しました", icon="ERROR")
        layout.label(text="未証明の対応を推測していません")
        layout.label(text="白い見た目だけでは原因を判断しません")
        layout.label(text=f"結合済みMaterial依存: {counts['RESOLVED']}件")
        layout.label(text=f"Mesh対応未解決: {counts['UNRESOLVED_IDENTITY']}件")
        layout.label(text=f"不足Asset参照: {counts['MISSING_DEPENDENCY']}件")
        layout.label(text=f"候補が複数: {counts['AMBIGUOUS']}件")
        if counts["UNSUPPORTED"] or counts["ERROR"]:
            layout.label(text=f"未対応/エラー: {counts['UNSUPPORTED']}/{counts['ERROR']}件")
        _label_lines(layout, "件数は証拠記録数です（Mesh数ではありません）")
        groups = Counter((item["category"], item["scope"], item["reason"], item["action"])
                         for item in outcome["items"])
        for (category, scope, reason, action), count in groups.items():
            box = layout.box()
            box.label(text=f"{_CATEGORY_LABELS[category]}: {count}件")
            _label_lines(box, f"範囲: {scope}")
            _label_lines(box, f"理由: {reason}")
            _label_lines(box, f"次: {action}")
            if category == "UNRESOLVED_IDENTITY":
                _label_lines(box, "対象Objectは証拠だけでは特定できません")
        if counts["UNRESOLVED_IDENTITY"]:
            layout.label(text="通常ImportにはUnityは不要です")
            layout.label(text="witness作成は現在開発者向けです")


CLASSES = (VAPB_PT_import_outcome,)
