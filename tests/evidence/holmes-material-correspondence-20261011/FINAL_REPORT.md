# HOLMES 最終報告（10項目）

判定対象は保存済み実測commit `e66bff69bc2aec7bfe61ce0b036c7baa4bff23af` のR/A/B/E/U/D/Hと、その時点の製品source。追加実験・製品コード変更は行わない。**異なるMaterialの面対応の製品化はDEFER、既存guardはKEEP。** 本人指定の10項目の原文見出しは取得できていないため、以下は要求内容を10項目に整理した報告であり、原文見出しとの一致は未確認である。

## 1. 目的・成立範囲

目的はunitypackage→Blender編集→別VariantでUnity復帰に向け、raw FBXのMaterial割当とUnity native submesh、Blender slot、Renderer occurrenceのMaterial参照の接続を判断すること。自作ThreeSlotSourceの12面、Unity 2022.3.22f1、Blender 5.2.1 LTS、各保存hashと実効import policyに限る。原本package SHAは `d6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c`。有限実測を通常入力全般の仕様保証へ拡張しない。

## 2. 実測結果

UIDラベル0/1/2は基準FBXのMaterial接続位置であり、名前identityではない。UIDは順に943593828 / 504963197 / 123443898。

| case | 変更 | raw使用UID初出順 | Unity native UID群順 | Blender UID群順 |
| --- | --- | --- | --- | --- |
| R | no-op書込 | 2,1,0 | 2,1,0 | 0,1,2 |
| A | 面record群順変更、面意味・名前・2/4/6面・接続固定 | 1,0,2 | 1,0,2 | 0,1,2 |
| B | 接続2,0,1と同じUIDへのindex remap | 2,1,0 | 2,1,0 | 2,0,1 |
| E | 初出・面数固定、3run→11run | 1,0,2 | 1,0,2、Aと12面所属一致 | 0,1,2 |
| U | 最後2面をUID0→UID2、未使用slot0接続保持 | 2,1 | UID2:8面、UID1:4面の2submesh | 空slot0、UID1:4面、UID2:8面 |
| D_receiver（記録名D） | E FBX固定、Prefab参照[M0,M1,M0] | Eと12面所属一致 | Eと同じ |
| H | E FBX固定、polygon最適化true→false | Eと12面所属一致 | 追加測定不要 |

Hの全実効設定差は `meshes.meshOptimizationFlags: -1→-2` のみ。metaのminBoneWeight書直し0→0.001は、実効値がbefore/afterとも0.001であることと分けて記録した。UのPrefab参照3個／native group2個について、描画やlayeringの意味は未実測。

## 3. H1〜H7の最終分類

分類は表の命題と適用範囲に対して行う。広い仮説と限定観測を同じVERIFIEDへまとめない。

| 仮説 | 最終分類 | 適用範囲・根拠 |
| --- | --- | --- |
| H1 使用Material UIDの初出順でnative番号が決まる | **UNDETERMINED（一般則）／VERIFIED（限定観測）** | R/A/B/E/Uの実入力で初出順とnative UID群順が一致。DはEと同じFBX、HはEの1設定切替。未観測入力の保証なし |
| H2 Material→Model接続順だけで決まる | **FALSIFIED** | この単独普遍則にはA/Bが反例。接続を他条件と併用する則は未判定 |
| H3 raw Material index昇順だけで決まる | **FALSIFIED** | A/Bが反例。indexが接続位置を指す範囲でH2と予測が同じなので、同義予測同士を識別したとはしない |
| H4 Material名だけで決まる | **FALSIFIED** | Aで名前が同一なのにnative順が変化。名前を併用する条件則はUNDETERMINED |
| H5 UID別面数だけで決まる | **FALSIFIED** | Aで2/4/6面を固定してnative順が変化。面数を併用する条件則はUNDETERMINED |
| H6 import設定によって則が切り替わる | **UNDETERMINED（広い仮説）** | 「このEのpolygon最適化切替で所属が変わる」はFALSIFIED、所属不変という限定観測はVERIFIED。他設定未測定 |
| H7 producer・未使用slot・run・重複等で則が切り替わる | **UNDETERMINED（広い仮説）** | 11run→11groupはEでFALSIFIED、接続3個→native3group保証はUでFALSIFIED、今回の受信参照重複でpartition変化はDでFALSIFIED。他producer/raw重複/null等は未判定 |

## 4. 未実施C名前・D面数・raw接続重複

原計画の **C_names（名前だけ変更）とD_count（初出固定で面数変更）はNOT_RUN**。公開記録DはD_receiverであり、D_countの実施結果として扱わない。Aは名前だけ／面数だけの決定関数を既に反証するが、「名前変更・面数変更が一切影響しない」ことは証明しない。

rawの同一Material UIDのOO接続行重複もNOT_RUN。行重複が独立slotを意味するか、dedupeされるか、入力として受理されるかは未確定。D_receiverの結果をraw重複へ転用しない。

現在の製品化判断を変える具体的な競合予測は残っていないため、追加起動は不要。C/D_countの追加例だけでH1の一般保証にはならない。後続実験は、適用対象と対立する予測、その差がどの製品判断を変えるかが具体化した場合のみ最小1ケースを選ぶ。

## 5. 面対応の証拠と限界

独立judgeは実FBXからraw UID割当を導出し、Unity/Blenderと12個の一意なexact UV面signature・一意corner permutationでjoinした。重複・欠落面／重複cornerは拒否、winding反転は別観測。全group/slot ordinalと多重度を保持し、空slot・同一UID複数group・mixed UIDを代表UIDへ潰さない。H1予測を観測judgeへ使用していない。

このjoinには捕捉したnative三角形が必要である。通常のpackageと既存identity witnessだけにはそのデータがない。位置差の数値観測は面所属と分離し、近似合わせ・新epsilonを正当化に使わない。固定Prefab参照は独立受信対照であり、Aの見た目を原本通り保ったという証拠ではない。

## 6. 通常入力から適用条件を識別できるか

| 条件 | 通常入力で確認できること | 不足すること |
| --- | --- | --- |
| package/FBX/meta hash、UID接続、Material layer/index、初出順・面数 | 実bytesから限定raw条件を読める | 同条件が未観測producer/Unity環境でも同じnative partitionを作る保証 |
| Prefab Material GUID/signed fileID、root/edge revision | 受信Renderer occurrenceの参照と所有範囲 | raw UID→native face→受信Materialの対応 |
| Model witnessとBlender importer receipt | Model/Geometry/Mesh/Rendererと実import Objectのidentity bridge | native face→submeshのcarrier |

通常Importが今回と同じ外形条件を認識できることと、安全にH1を適用できることは別である。Unity版・実効設定の限定実測をpackage/meta記載値だけで一般化しない。既知fixtureのhashを製品policyに固定する対応も通常入力の解決にならない。

## 7. GUID/fileID/occurrenceへの最終接続

このfixtureのnative MeshはGUID `abcdefabcdefabcdefabcdefabcdefab` / signed fileID `3538053534738119282`、PrefabはGUID `7cbdcbe81fde386408bcfb379e62b6bb`、Renderer signed fileID `3728717051629469441`。観測経路はraw UV面→捕捉native submesh→当該Rendererの実Material参照である。raw UIDとUnity Material GUIDを名前／ordinalで同一視しない。

製品の既存経路は、[Import](../../../operators/import_unitypackage.py)で実package/witnessを読み、[occurrence projection](../../../unity/occurrence_projection.py)でrootとsource/instance edgeのidentity・revisionを検証し、[FBX receipt](../../../blender/fbx_receipt.py)でModelUID/GeometryUIDと生成Objectを結ぶ。[binding](../../../blender/renderer_binding.py)でsource hash、GUID/signed fileID、occurrenceと実realizationを確認する。occurrence IDは論理identityでありrevisionを含むhashではないため、root/source/edge revisionは別途確認が必要。

[ModelIdentityRow](../../../unity/model_identity_witness.py)はMesh/Renderer/Bone/Shapeのidentityを保持するがface partitionを保持しない。既存fieldsetも厳密なので、実験JSONを既存carrierとみなすことはできない。identity接続は成立しても、欠けたface対応の証拠は補われない。

## 8. 製品化判断・保持するguard

**異なるMaterialの自動面対応はDEFER。新schema、必須Unity前処理、名前・面数・ordinal推測は追加しない。** PRODUCT_SPECの通常利用でUnityを必須にしない条件、Renderer occurrence側の割当、Material identityとface割当の区別を保持する。

[find_witness_consumer / reserve_witness_slots](../../../blender/model_witness_bridge.py)は完全なMaterial参照を照合し、異なるidentityが複数ある場合はconsumerを解決せずpendingを保持する。[Confirm material plan](../../../operators/renderer_binding.py)も異なる実Materialの未確定face対応を拒否する。R/A/B/E/U/Dは実製品RECONSTRUCT ImportでConfirm CANCELLED、前後snapshot不変。

同一Materialの既存経路は順置換に影響されないが、未使用/null/描画境界全般を保証したとはしない。別のlegacy [apply_prefab_materials](../../../blender/material_builder.py)にはordinal適用が残る。通常HOLMES入力で実Meshへ到達する経路は未実証なので、「全経路がguard済み」とは主張せず、推測による修正もしない。

## 9. 独立レビュー・保存証拠・保全

生成／面判定は別GPT-6.1 SOL / mediumコンテキストでレビュー済み。最終分類reviewはKEEP、通常Import適用条件／witness接続reviewはDEFER製品化・KEEP guard。完了済みレビューや成功例は再実行しない。主担当の実runtimeモデル／reasoning設定は取得不能。

実測記録は [README](README.md)、[R/A/B判定](observations/full-judgment.json)、[E判定](observations/E-full-judgment.json)、[U/D/H判定](observations/boundary-full-judgment.json)、[U/D/H実行summary](observations/boundary-run-summary.json)。R/A/B保存commitは `c76d3bd8380247b75ff4c0b5716c3cad97613ec6`、E sourceは `5f5de6d187fd9a7435d0962bc698211128d137c2`、E実測は `0b69c2e7634ee34d182ee39a75c87d54013a5667`、U/D/H実測と実行sourceは冒頭e66。過去hashやNOT_RUN記録を変更しない。

Unity/Blender exit0、保護3,041ファイル変更0・予期しない追加0。U/D/H終了直後のresource guardは初回cleanup/返却をWITHHELDとした。後のfresh資源不存在確認から自作配置だけを復元し、正確な所有lease/mutexを返却した。最初の保留をPASSへ書き換えず、他Editor停止・lock削除はしていない。購入素材・私的corpus・生ログは公開保存しない。

## 10. 未完了と次の最小判断点

今回得られたのは限定native挙動と安全な製品化可否の判定であり、ユーザーの最終往復機能が増えたとは報告しない。GUI/render/client、実購入corpus、最新ZIP、編集AnimationのUnity復帰、製品全体完成は未成立または未確認。

face対応の次の不足証拠は、**通常入力契約で有効なnative partition導出の根拠、または既存carrierによるexact native face対応**。どちらも今回の有限実測／identity witnessにはない。この不足を新基盤で埋める作業は開始しない。現在はguardを維持してこの判定を保存し、次の承認済み製品作業へ戻せる状態とする。本人原文10見出しとの照合だけは原文取得後に行える。
