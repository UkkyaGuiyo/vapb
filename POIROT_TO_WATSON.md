# ポアロ → ワトソン：条件付き再開・反証引継ぎ

- Repository: `UkkyaGuiyo/vapb`
- 指示専用branch: `docs/holmes-watson-handoff`
- 確認日: 2026-10-16 JST
- Status: `NO_NEW_COUNTEREXAMPLE / RESUME_ALLOWED_IF_PREFLIGHT_PASS`
- 本記録の対象: 2026-10-16、本人からの「問題がなければCodexを動かしたい」という明示的な訂正。
- 既存ポアロ追加検証 `POIROT-20261013-01` / `POIROT-20261014-01` は完了済み。再発注しない。

## 1. 前回の「起動しない」の解釈を訂正する

以前の「Codex起動は命じない」は、このChatGPTタスクが**ローカルCodexを自動起動できない**という能力・実行状況の説明であり、本人からの恒久的な停止命令ではない。今回の本人の意思は、**現実の問題がなく、実行可能な承認済みVAPB作業があれば、親Codex／ワトソンに再開・継続してほしい**というもの。

この文書は新しい技術指示、実機権限、範囲外の承認、起動手段を追加しない。親Codexが実際に稼働中または正規の起動経路から開始できたなら、以下の事前確認をして、従来の承認済み開発を継続してよい。ポアロの次の定期実行を待つ必要はない。ホームズ主指示は読取専用で、取り消し・上書き・優先順位変更をしない。

## 2. 条件付きGO：開始前の現物確認

親Codexは最初に最新のユーザー指示と、実Git remote、作業branch/SHA、未保存差分、同時実行中作業、最新`AGENTS.md`/`PRODUCT_SPEC.md`、実開発REPORT/PLANと保存済み`NEXT_ACTION`を照合。旧`READY`や完了IDを重複実行しない。

次に、その作業に必要な実Unity/Blender/GUI操作手段、Project所有権、他プロジェクトの優先順位、lease/mutex/lock、RAM・アカウント予算・認証、原本保全、GitHubへの安全な保存を**実測で**確認する。GitHubだけではローカル資源の現状を知ったことにはならない。

- **GO**：具体的な承認済み未完了作業が存在し、必要条件が揃い、ほかの作業と競合しない。保存済みNEXT_ACTIONから最小の一手を実施する。
- **別候補へ**：GUIなど特定工程だけが資源・操作手段不足なら、その工程をBLOCKEDとし、独立して実行可能な別の承認済み候補を最新のホームズ／PLANから探す。未確認の機能を推測で実装しない。
- **BLOCKED / NO_NEW_ACTION**：すべての候補に実障害がある、所有権・安全確認・保存経路が確立できない、または承認済みの実行可能な一手がない。正確な理由を保存して停止。時間経過だけでlock解除や権限昇格をしてはいけない。

通常のPASSやレポート保存、ポアロの`WAITING_FOR_RESULT`は、製品全体の永久停止理由ではない。

## 3. 最新確認地点と現実の残課題

開発branch: `feature/connected-bone-action-20261012`  
最終確認HEAD: `352fd46ccad479f7857d1735e2f906487eddb0d6`。

現行Shader依存宣言・検査・partial結果表示はソース検査済みで、最新ソースの新規ZIPは内容照合済み。しかしこのZIPは実BlenderインストールとUnityネイティブ／GUIでは未検証。CASE24実GUI受入、同梱Shader依存診断の実Unity Inspectには、実際に呼び出せる操作手段と親のProject／時間割当が必要。これらを実施できない場合は「資源待ち」であり、無関係な承認済みソース作業まで禁止する理由にはならない。再開時に現行HEADとREPORT/PLANを読み直す。

## 4. 完了したポアロ補足実験

`POIROT-20261013-01`：自作二面SkinのMaterial A/A→片側A/B変更で、保存再起動／Unity Variant Apply・reApplyの限定結果PASS。結果: `tests/evidence/holmes-material-correspondence-20261011/connected-bone-action/POIROT_REPORT.md`。実測commit `988caa20320868dabfa0a5315390ee7ce6b2da9d`、訂正 `e61735c19d7482fcdadb7cc22732c87af19a33c4`。

`POIROT-20261014-01`：同二面の有向windingをUnityで独立観測して限定結果PASS。結果: `tests/evidence/holmes-material-correspondence-20261011/connected-bone-action/POIROT_WINDING_REPORT.md`。完了commit `b18e5e66bbcc0e22e9309ef9744f069b7f94fcbf`。

両案件は再実行しない。今は新たなポアロ`SUPPLEMENTAL_READY`を発行しない。Shaderで一つのMaterialだけrevision不一致となる状況は補足反例候補だが、主実機診断の証拠を先に確認する。

## 5. 保全と保存の契約

原本Package/FBX/.meta/Prefab/Material/Scene、GUID/signed fileID、package/occurrence/revisionと既存証拠を保護。購入素材・個人情報・秘密・私的生ログを公開しない。他者Editor停止、lock/marker無断削除、無断merge/Release/force-push、権限回避を禁止。

親Codexが実際に再開したら、開始branch/SHA、最新の実行許可と資源確認、作業ID、PASS/FAIL/NOT_RUN/BLOCKED、原本保全、次の`NEXT_ACTION`を実開発branchに保存する。許可された範囲でcommit/pushし、remote readbackを確認する。

**この記録は、Codexの実起動・実機作業・自動トリガー成立の証拠ではない。** このChatGPTタスクはローカルCodexを直接起動しない／起動できたと報告しない。
