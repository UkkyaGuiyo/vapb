# BUG-003 Material / Texture Visual Construction Fix

測定日: 2026-09-15  
対象: Blender 5.2.1 LTS / `RepresentativeAvatar-CaseA-Ver1.3.1.unitypackage`

## Goal and scope

BUG-002で確立した `Renderer slot → Material GUID → Blender Material → Texture GUID → Blender Image → filepath` は変更せず、Blender Material Previewで画像が表示されるためのノード構成だけを修正した。PackageReader、Prefab選択、GUID解決、非同期prepare/modal lifecycle、Bridge/Finalizer、PhysBoneは変更していない。

## Root cause evidence

BUG-002で保存した修正前blendの代表材質（SampleGarment、Body、Hair）を調査した結果、画像ノード、Base ColorへのMixRGB経路、Principled BSDF、Material Outputは存在し、画像ファイル・色空間・実メッシュUVも有効だった。一方、全Image TextureのVector入力が未接続で、Blenderの暗黙の座標解決に依存していた。

最小修正として、`blender/material_builder.py::_texture_node()` がBase Color、Normal、Emission、Metallicの全Image Textureについて `ShaderNodeTexCoord(UV)` を必ず生成し、通常のscale/offsetならUV→Image Texture、変換が必要ならUV→Mapping→Image Textureへ接続するようにした。

## Automated and real-package evidence

- Python unit tests: 41 PASS
- Blender 5.2.1 synthetic integration: PASS（explicit UV link assertionを含む）
- Blender 5.2.1 real import: `FINISHED` / PASS
- Real scene: 113 objects、103 meshes、4 armatures、40 shape keys
- 画像: 112
- Material datablocks: 53（うちBase Textureあり48）
- 使用中Material GUID: 15、material slot bindings: 147
- 48/48 textured materials: nodes、Base Color、Surface、全Image Textureのexplicit UVが全件成立
- Base Texture GUID identity mismatch: 0
- 保存再読込: 使用中15材質の画像GUID/UV graph MATCH、147/147 binding signatures保持

Representative results:

| Material | Family | Image GUID | Base Color | Surface | UV |
|---|---|---|---|---|---|
| Face | liltoon | `PRIVATE_ASSET_ID_REMOVED` | PASS | PASS | PASS |
| Hair | liltoon | `PRIVATE_ASSET_ID_REMOVED` | PASS | PASS | PASS |
| SampleGarment | liltoon | `PRIVATE_ASSET_ID_REMOVED` | PASS | PASS | PASS |

VIS-001〜VIS-009: PASS（詳細は `real_import_visual_result.json` / `reopen_visual_result.json`）。VIS-007は今回の実Packageに透明材質がなく、不透明材質に誤ったAlpha接続がないことを確認した。VIS-010の通常UI目視はComputer Use初期化エラーのためUNVERIFIEDであり、成功扱いしていない。

## Regression and packaging

BUG-002 identity chainの147 bindingsは維持され、既存の41 unit testsとsynthetic integrationはPASSした。`compileall` PASS、Blender register/unregister PASS、ZIPは46 entries / `testzip None` / root layout PASS。最終ZIP SHA-256は `PRIVATE_ASSET_ID_REMOVED`。

## Review

- Astra review: 明示UVだけではMaterial Previewの実表示改善を証明できない、透明材質は未検証、全Image Texture経路を検査すべきとの指摘。Surface明示接続と全Image Texture UV検査を追加した。通常UI目視は引き続きUNVERIFIED。
- scope_guard: 初回レビューは誤ったcwdで判定不能。BUG-003の変更範囲は `material_builder.py` の明示UV/Surface構築、対応テスト、実Package probe/reportに限定されている。

## Evidence files

- `before_sample_garment_graph.json`
- `before_visual_summary.json`
- `real_import_visual.py`
- `real_import_visual_result.json`
- `reopen_visual.py`
- `reopen_visual_result.json`
- `BUG_003_real_import.blend`
