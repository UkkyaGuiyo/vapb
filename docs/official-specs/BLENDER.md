# Blender: datablock・Material・Skin・Action・FBX

対象: **v5.2.1公式source**、確認日2026-10-11 UTC。生成された5.2 Manual/APIサイト本文は取得不能。以下の初版説明は**SRC**として記す。公式repository内のAPI解説（DOC）と追加実装調査は[補足](BLENDER-SUPPLEMENT.md)へ分ける。公開APIの安定契約・実行binaryの検証結果へ昇格しない。原典は[SOURCES](SOURCES.md)。

## ID datablockとdependency graph

**SRC [B02]**: ID.usersはdatablockの参照回数、use_fake_userは実userがなくても保存する機構として定義される。shared datablockとobject instanceは別。ID.copyの説明は新しいMain database IDを作り他datablockへの参照を持つ。全依存assetを深く複製するという意味ではない。

**SRC [B02、B05]**: evaluated_getは指定Depsgraphの評価済IDを返すが、完全な評価をその呼出しで保証せず最後の評価結果を返すという説明。original objectと評価されたmodifier/pose結果を混同しない。依存graphの存在はUnity GUID/fileIDを自動で持たせる仕組みではない。

**INFERENCE**: 元datablock保存と見た目のbakeは違う保存対象。modifierで増減したvertexを元indexと同一視しない。評価済Meshの一時identityを保存後再openでも同じauthoring identityとする根拠は不足。

## Object / Mesh / Material slots / polygon material_index

**SRC [B03–B04]**: MaterialSlotはObjectに属するslotで、linkはObjectまたはobject dataを選ぶ。slot.materialはMaterial datablock。MeshPolygon getterはFace domainのmaterial_index属性を読み、MaterialはfaceにGUIDとして直接格納されるわけではない。

**INFERENCE**: 同じMeshを使う複数Objectのeffective MaterialはObject-linked slotなら違い得る。`mesh.materials`だけでObjectの表示Materialを断定しない。slotのlink/順/Material identity、polygonのindexを合わせて読む必要がある。unused slotとnull slot、Material重複は異なる情報。

**SRC [B10]**: FBX exportはBlender Material listをFBX Material indexへmapし、範囲外やexport対象外Materialにdefaultを使う経路がある。`LayerElementMaterial`にByPolygon/IndexToDirect等を書く処理は、exporterの選択であって全FBX producerの標準を網羅した根拠ではない。

**INFERENCE**: native polygon.material_indexが残っていても、Unity generated subasset IDと元FBX UIDのjoinがないとUnityのMaterial identityは不明。slot順の見た目一致やsuffix一致はidentityの証明ではない。[頂点対応](VERTEX-CORRESPONDENCE.md)も参照。

## Armature、rest、pose、vertex group

**SRC [B06–B07、B04]**: Bone.matrix_localはarmature relative rest matrix。PoseBone.matrixはconstraints/drivers適用後のarmature object spaceの最終matrixと説明される。VertexGroupはarmature deform以外の用途も持ち、group index/nameと頂点weightを持つ。

**INFERENCE**: 全vertex groupをboneとみなさず、deform経路とarmature targetを確認する。Bone nameとUnity Transform identityの橋渡しは別問題。armature object/world frame、Bone rest、PoseBone評価、Unity bindpose/Renderer frameを区別する。重みを別vertex orderへ無条件copyしない。

## Action slots/layersとNLA

**SRC [B08–B09]**: 5.2.1 Actionにはslotsとlayersがある。NlaStripはActionとAction slot参照を持ち、slotはActionのどのsubsetがstrip向けかを示す。Actionのmanual frame rangeは評価そのものを変更するものではないという説明もある。

**INFERENCE**: `Action名 + fcurve一覧`のみで全Action stateを保存したと判定しない。対象slot、channel bag/layer、strip時間変換、blend/influence、active actionとNLAの重ね合わせ、target datablockを区別する。旧API前提の全互換性は未調査。

**SRC [B11]**: FBX exporterのAll Actionsはcompatible objectへ各Actionを別AnimStackとして書く選択肢。sampling、simplification、force start/end、NLA strips、bone axis/leaf bone、axis/unit、texture path等の設定を持つ。default optionはVAPB presetの採用根拠や無損失保証ではない。

**INFERENCE**: constraint/driverをsampleしてbakeする結果とauthoring制御の保存を区別する。FBXに存在するAnimStackがUnity AnimationClipやVRC Action playable layerへ自動で同一意味になるわけではない。独立Clipを本人GUIで割当する範囲と、Controller/Expressions再構成を分ける。

## FBX import / API / 未調査範囲

legacy `io_scene_fbx` import/export sourceを確認した [B10–B11、B13]。ただしsourceを全関数監査してはいない。生成API/Manual本文が取れない項目はSRCまたは公式解説source DOCの範囲を明記する。補足ではMaterial index修正、Object slot override、Cluster/weight、Action slotの該当経路を追加読取した。新しいFBX経路との完全互換、全modifier、shape animation、material nodeの完全変換、texture色空間/packed file、library override、全operator context条件は未調査。

Blender公式sourceのlicenseと、ユーザーが編集する素材のlicenseは別。sourceを読めることからSDKや購入素材を再配布できると推定しない。今回source本文をrepoにコピーせず、日本語要約とURLだけを保存する。
