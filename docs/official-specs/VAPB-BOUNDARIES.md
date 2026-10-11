# VAPB直接課題への適用・未証明・担当者手順

確認日: 2026-10-11 UTC。基点 `f29702cdac64a0fbd807723cd79e652ffd5067e1`。以下は公式仕様を製品課題へ適用した**INFERENCE**で、今回24 packageの実測を行った結果ではない。

## 課題ごとの根拠と限界

|課題|使える公式根拠|まだ必要な証拠・判定|
|---|---|---|
|unitypackage内部配置|U08、U01|圧縮集合とmetadataはDOC。GUID directory/tar member schemaはLOCAL/EMPIRICAL。全version保証にしない|
|元FBX/meta保持、編集Mesh新identity|U01–U04、U21|新import後GUID/fileID、参照closure、別Variantの実Mesh割当。元identity再利用成功と推測しない|
|embedded Material出所|U15–U17、U49|Unity生成Material fileIDとraw FBX Material UIDのjoin。空remap mapから外部Materialを推定しない|
|Prefab Material overrideの受け手|U18–U22、U09|occurrence/source Renderer→native Object/slot対応。overrideが存在しても受け手joinは別|
|native face-to-slot|U10–U14、B03–B04、B10|Unity submesh facesとBlender polygon corner/slotの独立対応。Material名・slot数・外観だけでは不足|
|null/unused/repeated slot|U09、U13–U14、U17|nullや重複を圧縮しない。余剰Materialの最後submesh重ね描画を区別。全null描画条件は未実測|
|signed localID|U02|longを保持。intへの切詰めや符号除去不可。FBX UIDと同値にしない|
|nullBone / fileID0|U07、U23–U29|参照種別、元nullの意図、skin index、native処理。補完値を推定して成功にしない|
|weight/bindpose/rest|U25–U27、B06–B07|vertex対応とbone identity、空間一致。influence総数やbone数だけでは不足|
|頂点数が元/編集/Unityで違う|U12、U33、U40–U45、B10|[頂点対応](VERTEX-CORRESPONDENCE.md)のCP/corner/face/skinとimport-policy条件。差だけで不具合/正常を決めない|
|Texture/Shader/Script不足|U05–U06、U31–U32、V11|参照存在とprovider availabilityを分離。missing referenceを色や名称で埋めない。Blender preview shaderとclient shaderも別|
|編集Actionを独立Clipで返す|U34–U38、B08–B11、V08–V10|GUI割当、clip binding、rig、Controller/layers/Expressionsは別。Actionの存在だけでVRC動作成功不可|
|PhysBone/Collider/Contact/Constraint保持|V05–V07|bone/object reference closure、component version/space、build/client挙動。Blender previewは近似でありclient証拠ではない|
|再Apply一致|U40–U42とvertex表現の境界|同一路線の再現性と元surface/skinへの対応は別。独立対応未証明を維持|
|VRC復帰|V01–V16|Editor、SDK build、upload、client、remote clientを別判定。公式資料だけでVAPB成功としない|

## 既存資料の扱い

- [CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY](../CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md): source Renderer-to-FBX Object、internal Material identity、explicit overrideの三つの問題を区別する既存LOCAL実測。公式3リンクを今回再取得したが、実測を繰り返していない。source情報欠落を埋める追加証明は依然必要。
- [EXPORT_RESEARCH_CORRECTIONS](../EXPORT_RESEARCH_CORRECTIONS.md): package layoutをEMPIRICAL、generated subasset IDsをUNKNOWNにした分類を継承する。本資料はAPI本文を再確認して詳細化したもの。
- [R2_STAGE3_NATIVE_FBX_SYNTHETIC_VERIFICATION](../R2_STAGE3_NATIVE_FBX_SYNTHETIC_VERIFICATION.md): 特定fixture座標・Material slot結果。新たなU33/B10根拠は設定依存性を説明するが、全素材へ結果を拡張しない。
- [VAPB_BOUNDED_SKIN_ROUNDTRIP_ACCEPTANCE](../VAPB_BOUNDED_SKIN_ROUNDTRIP_ACCEPTANCE_20261001.md): SDK 3.10.5の既存記録。現在の別project稼働版、client状態を今回確認した意味ではない。

これらの既存文書も自作研究資料で、公式出典ではない。今回の新しい根拠は公式Manual/API/REL/SRCの再取得と版区分、余剰slot、null remap、vertex最適化・weld・corner属性、VRC load時変換の明確化。

## 証拠の階層

|観測場所|確認できること|それだけでは確認できないこと|
|---|---|---|
|asset/meta/text serialized file|保存された参照token、import settings、override|generated native subasset内容、effective object全体、client runtime|
|raw FBX graph|FBX内のModel/Geometry/Material接続とattribute layer|Unity生成GUID/fileIDへの対応、Unity importer全policy|
|Blender authoring / evaluated data|datablock、slot、polygon、rest/pose、特定評価結果|元Unity identity、client solver、post-import Unity表現|
|Unity Editor public API|その版・設定でimport後に実在するobject/IDs/Mesh/Renderer/bindings|別versionの結果、SDK/client内部変換、network動作|
|公式source|固定revisionの露出した処理・binding・option|非公開native code、安定API保証、実行binary同一性|
|SDK validation/build/upload|そのstageでacceptされたこと|元素材の意味的往復、client/remote表示の同等性|
|実client / multi-client|測定した条件の挙動|全platform・全permission・全versionの普遍保証|

## 未調査・未公開の残り

1. Blender最新stable/最新LTS patchのdownload順位と5.2 API/Manual本文。公式sourceのv5.2.1 release/LTS定義は確認できたが、latestを代行しない。
2. Unity最新stable/LTSの正確なpatch番号。6.6 Manualと6.3 LTS supportは確認済。
3. Unity native FBX importerの全CP→vertex map、split/weld条件、fileID生成アルゴリズム、null boneの全挙動、binary formatの完全schema。
4. FBX規格所有者Autodeskの全schema/APIとの照合。Blender実装をFBX規格そのものとしない。
5. Blender全modifier、Action channel bag、NLA/driver/constraint/shapeとFBXの全相互作用、source commentの個別issue本文。
6. SDK sourceの全build processor、各componentの全serialized field、非公開client/server処理、platform別動作、第三者custom shader/scriptの仕様。
7. World/Udon/音声/同期/Creator Economy/OSC等の全API。機能索引はあるが個別機能を詳細監査済としない。
8. 24 packageの個別権利、全依存closure、元meshと編集meshの独立vertex/face/skin対応と全runtime検証。

## 担当者の短い参照手順

まずこのbranchのREADME→VERSIONS→課題表を読む。Material課題はUNITY-MATERIAL-MESH、数差/CP課題はVERTEX-CORRESPONDENCEへ進む。SOURCESの見出しとversionを原典で確認し、実測する場合は実測版と設定を別に記録する。公式記載、source実装、実測、推論を混ぜず、欠けたjoinはUNKNOWN/NOT PROVENのまま扱う。

本資料を参照するために製品branchへcherry-pickする必要はない。製品実装、推測割当、guard解除、停止研究の再開はこのbranchの成果物ではない。

通常ImportをUnity必須へ変更する指示ではない。今回のEditor public APIは「不足したidentityの橋渡しを確認できる観測場所」の説明であり、全ImportでEditor起動を要求する製品方針ではない。既存の証明が揃う経路と、追加証拠が必要な特定経路を区別する。
