"""Read-only, identity-safe explanation of persisted import semantic evidence.

Counts describe evidence records, not distinct visible meshes or full Avatar
fidelity. No names, GUIDs, file IDs, or visual colour guesses enter the report.
"""

from __future__ import annotations


_ISSUES = {
    "UNRESOLVED_SOURCE": ("UNRESOLVED_IDENTITY", "UnityPackageだけでは、この部品がどのBlender Meshか証明できません。", "未解決のまま保持。正確な元データ用のUnity witnessは開発者向け手順で利用できます。"),
    "UNRESOLVED_OVERRIDE": ("UNRESOLVED_IDENTITY", "Material変更の対象Rendererを安全に特定できません。", "未解決のまま保持し、Unity上の元データで対象を確認してください。"),
    "UNRESOLVED_ALIAS_OVERRIDE": ("UNRESOLVED_IDENTITY", "入れ子PrefabのMaterial変更先を証明できません。", "該当Prefab内は推測せず、Rendererの出所を確認してください。"),
    "WITNESS_MISSING": ("UNRESOLVED_IDENTITY", "元モデルの版に一致する対応証拠がありません。", "未解決のまま保持し、同じ版から作ったwitnessを確認してください。"),
    "NATIVE_MISSING": ("UNRESOLVED_IDENTITY", "証明済みの元データに一致するMeshがありません。", "元モデルの版とImport内容を確認してください。名前だけで選ばないでください。"),
    "WITNESS_CONSUMER_MISSING": ("UNRESOLVED_IDENTITY", "対応するMeshかMaterialスロットを一意に確認できません。", "取り込んだモデルと元データの版を確認してください。"),
    "INCOMPLETE_IDENTITY": ("UNRESOLVED_IDENTITY", "元データとMeshの対応記録が不足しています。", "未解決のまま保持し、対応の証拠を確認してください。"),
    "SOURCE_IDENTITY_MISMATCH": ("UNRESOLVED_IDENTITY", "指定された元データとRendererが一致しません。", "同じ版の元データから作ったwitnessを使ってください。"),
    "OCCURRENCE_IDENTITY_MISMATCH": ("UNRESOLVED_IDENTITY", "Renderer個体の記録と元データが一致しません。", "元データの版を再確認してください。古い確認を再利用しないでください。"),
    "MISSING_SOURCE": ("MISSING_DEPENDENCY", "参照先のPrefabまたはモデルPackageがありません。", "参照先を含むPackageを追加して再Importしてください。"),
    "AMBIGUOUS_SOURCE": ("AMBIGUOUS", "参照先に複数の候補があります。", "正しいPackageをAssetの識別情報から確認してください。"),
    "AMBIGUOUS_OVERRIDE_TARGET": ("AMBIGUOUS", "Material変更先のRenderer候補が複数あります。", "正確なRenderer個体を確認するまで適用しないでください。"),
    "NATIVE_AMBIGUOUS": ("AMBIGUOUS", "同じ元データに対応するMesh候補が複数あります。", "重複を解決してください。名前や並びだけで選ばないでください。"),
}

_UNSUPPORTED_ISSUES = {
    "CYCLE", "DUPLICATE_SOURCE_FILE_ID", "INVALID_MESH", "INVALID_MESH_FILTER",
    "INVALID_OWNER", "INVALID_ROOT_SCOPE", "INVALID_SOURCE_SCOPE",
    "MALFORMED_INSTANCE", "MALFORMED_MATERIAL_REFERENCE",
    "OVERRIDE_SLOT_OUT_OF_RANGE", "SOURCE_GUID_MISMATCH",
    "UNRESOLVED_SKIN_OVERRIDE",
}

_MATERIAL_TYPES = {"PREFAB_RENDERER_MATERIAL", "FBX_EXTERNAL_MATERIAL"}


def _scope(issue: dict, root_number: int) -> str:
    if issue.get("uncertainty_scope") == "NESTED_INSTANCE":
        return f"Importルート {root_number} の入れ子Prefab個体"
    if issue.get("uncertainty_scope") == "CHILD_PREFAB":
        return f"Importルート {root_number} の子Prefab"
    if issue.get("instance_edge_path"):
        return f"Importルート {root_number} 内のモデルまたはPrefab"
    return f"Importルート {root_number}"


def summarize_import_outcome(projections: list[dict], dependencies: list[dict]) -> dict:
    """Classify existing projection issues and dependency outcomes only.

    `RESOLVED` is the number of bound Material dependency records, not an
    assertion that every Renderer or visible surface was restored.
    """
    counts = {key: 0 for key in (
        "RESOLVED", "PARTIAL", "UNRESOLVED_IDENTITY", "MISSING_DEPENDENCY",
        "AMBIGUOUS", "UNSUPPORTED", "ERROR",
    )}
    items: list[dict] = []

    def add(category: str, code: str, scope: str, reason: str, action: str) -> None:
        counts[category] += 1
        items.append({"category": category, "code": code, "scope": scope,
                      "reason": reason, "action": action})

    for number, projection in enumerate(projections, 1):
        for issue in projection.get("issues", ()):
            code = str(issue.get("code", ""))
            scope = _scope(issue, number)
            if code in _ISSUES:
                category, reason, action = _ISSUES[code]
            elif code in _UNSUPPORTED_ISSUES:
                category = "UNSUPPORTED"
                reason = "このUnity構造や参照は安全に解釈できません。"
                action = "未解決のまま保持し、元データの構造を確認してください。"
            else:
                category = "ERROR"
                reason = "未分類のImport問題が記録されています。"
                action = "復元済みと扱わず、VAPB開発者へ報告してください。"
            add(category, code, scope, reason, action)

    for record in dependencies:
        kind = str(record.get("dependency_type", ""))
        status = str(record.get("status", ""))
        if kind not in _MATERIAL_TYPES | {"MATERIAL_TEXTURE"}:
            continue
        if kind == "MATERIAL_TEXTURE" and record.get("texture_label") == "Preserve Only":
            continue
        if status in {"RESOLVED_LOCAL", "RESOLVED_CROSS_PACKAGE"} and record.get("binding_status") == "BOUND":
            if kind in _MATERIAL_TYPES:
                counts["RESOLVED"] += 1
            continue
        scope = "Materialスロット" if kind in _MATERIAL_TYPES else "MaterialのTexture参照"
        if status == "UNRESOLVED":
            add("MISSING_DEPENDENCY", status, scope,
                "参照先のMaterialまたはTextureが見つかりません。",
                "不足Assetを含むPackageを追加して、依存関係を再確認してください。")
        elif status == "AMBIGUOUS_PROVIDER":
            add("AMBIGUOUS", status, scope,
                "同じ参照先に複数の提供元があります。",
                "正しいPackageを識別情報から確認してください。")
        elif status == "MISSING_CONSUMER":
            add("UNRESOLVED_IDENTITY", status, scope,
                "Materialはありますが、受け取るObjectやスロットを証明できません。",
                "未解決のまま保持し、RendererとMeshの対応を確認してください。")
        elif status == "UNVERIFIED_SLOT_STATE":
            add("UNRESOLVED_IDENTITY", status, scope,
                "BlenderのMaterialスロットの状態を安全に確認できません。",
                "スロットを調べてから、明示的に対応を確認してください。")
        elif status == "USER_EDIT_PRESERVED":
            add("PARTIAL", status, scope,
                "ユーザーが編集したMaterialスロットを上書きせず保持しました。",
                "見た目の変更とUnity上の識別情報を別々に確認してください。")
        elif status == "UNSUPPORTED":
            add("UNSUPPORTED", status, scope,
                "この依存関係は現行Importの対応外です。",
                "未解決のまま保持し、元データの構造を確認してください。")
        else:
            add("ERROR", status or "UNKNOWN_STATUS", scope,
                "保存された依存関係の結果が不明です。",
                "復元済みと扱わず、Import結果を調べてください。")

    overall = "PARTIAL" if items else "SUCCESS" if projections or dependencies else "UNVERIFIED"
    return {"overall": overall, "counts": counts, "items": items}
