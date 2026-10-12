# ポアロ → ワトソン：受け渡し記録

- Instruction ID: `POIROT-20261013-01`
- Status: `WAITING_FOR_RESULT`
- Delivery: `ALREADY_SENT_BY_USER`
- 記録日: 2026-10-13 JST
- Repository: `UkkyaGuiyo/vapb`
- 指示専用branch: `docs/holmes-watson-handoff`

## 送付状況

本人から、既存の追加検証指示はワトソンへ送付済みとの連絡があった。このファイルはGitHub上の受け渡し状態を記録するものであり、新しい実験指示・再送・再実行要求ではない。同じInstruction IDを二重実行しない。

送付済みの追加検証は、重複Material slotのA/Aから片側だけをA/Bへ変更したとき、面とMaterialの対応が維持されるかを調べるもの。実験手順は既に受領した同IDの指示を参照する。ホームズの主指示は取り消さず、上書きせず、実行順序も変更しない。

## 結果の扱い

指示が送付されたことと、実験が開始・完了したことは別である。今回、この保存確認ではワトソンの実行結果を判定していない。

既存の承認済み作業の結果にInstruction ID、実行元branch/SHA、証拠ファイル、PASS/FAIL/NOT_RUN/BLOCKEDを記録する。未実施をPASSにしない。本ファイルの作成commitは、製品の修正や実験成功の証拠ではない。

## 保存経路の調査

この記録は、本人が依頼したGitHub保存障害の調査で作成する。製品コード、AGENTS.md、PRODUCT_SPEC.md、HOLMES_TO_WATSON.md、他の開発branchは変更しない。新たな権限の追加や安全設定の緩和は行わない。

2026-10-13の対話内確認:

- GitHubのrepository読み取りは成功。返されたpermissionsはpush=true。指示branchのprotectedはfalse。
- ChatGPTのGitHub個別権限表示はAllow all actions。設定変更は行っていない。
- 本ファイルは作成前の照会で404だった。
- 正式なcreate_file操作で新規作成に成功した。作成commit: `0704d6ac406f6f57d3a03785fbe6ef9e978c65d3`。
- 作成後にGitHubから本文を再取得し、Instruction ID、WAITING_FOR_RESULT、ALREADY_SENT_BY_USERが一致した。取得blob SHA: `d5a1424cb09b8eb3c14f2597ee3112fe7e7a799b`。
- 本追記は、その取得済みblob SHAを指定したupdate_file操作として保存する。更新の成否と内容は返却commitの再取得で別途確認する。
- 過去の安全拒否の内部理由は今回の成功だけでは特定できない。定期実行時や異なる本文でも必ず成功するという保証ではない。

保存時はrepository、branch、pathを専用引数で分けて指定する。ファイルが存在しなければcreate_file、存在すれば最新のファイルblob SHAを使ったupdate_fileを選ぶ。branch HEADのcommit SHAとファイルblob SHAを混同しない。本文はUTF-8文字列で渡し、二重にbase64化しない。

保存成功の返却だけで終えず、返されたcommitに固定した本文と変更ファイルを読み戻す。失敗時は、実際に返されたツール名・エラー分類・HTTP状態・変更前後のHEAD/ファイル存在を区別して記録する。理由が返されていなければ推測で「安全チェック」や「権限不足」と断定しない。拒否を避けるための権限緩和、別経路による迂回、無条件再送は行わない。
