# Blender補足: 取得制限と面・Skin・Action・FBXの境界

確認日: **2026-10-11 UTC**。対象は公式repositoryの**v5.2.1**。公式に執筆されたAPI解説のsourceを読む場合はDOC、処理実装を読む場合はSRCとする。どちらも今回のVAPB実行結果ではない。[出典索引](SOURCES.md)のB15–B24と既存B10–B14を参照。

## 取得不能の具体的な記録

|公式URL|観測した結果|この記録の限界|
|---|---|---|
|[5.2 MeshPolygon API](https://docs.blender.org/api/5.2/bpy.types.MeshPolygon.html)|Web取得サービス: 402 Payment Required、公開URL直接HTTP: 403 Forbidden|本文未取得。402からBlender有料化や本人の残量不足を推定しない|
|[5.2 ID API](https://docs.blender.org/api/5.2/bpy.types.ID.html)、[5.2 Action API](https://docs.blender.org/api/5.2/bpy.types.Action.html)|Web取得サービス: 402 Payment Required|本文未取得、発生元・根本原因の確定なし|
|[5.2 FBX Manual](https://docs.blender.org/manual/en/5.2/files/import_export/fbx.html)、[5.2 release notes](https://developer.blender.org/docs/release_notes/5.2/)|Web取得サービス: 402 Payment Required|release notesによる変更点一覧は未確認|
|[5.2 Material assignment](https://docs.blender.org/manual/en/5.2/render/materials/assignment.html)|Web取得サービス: inaccessible、HTTP番号は表示なし|403等と決めつけない|
|[Download](https://www.blender.org/download/)、[LTS](https://www.blender.org/download/lts/)、[5.2配布一覧](https://download.blender.org/release/Blender5.2/)|Web取得サービス: 402 Payment Required|最新patch順位の確認に使えない|
|[公式Manual repository](https://projects.blender.org/blender/blender-manual)|Web取得サービス: 403 Forbidden|公式Manual source本文を取得できず。GitHub上の同名候補APIも404、代替mirrorの存在を断定しない|
|[current armature gotchas](https://docs.blender.org/api/current/info_gotchas_armatures_and_bones.html)、[current MeshPolygon](https://docs.blender.org/api/current/bpy.types.MeshPolygon.html)、[current ID](https://docs.blender.org/api/current/bpy.types.ID.html)|Web取得サービス: internal error、HTTP番号は表示なし|本文未取得。currentが5.2を指すと推定しない|

Manual root B00は**入口・未取得**で、失敗した子ページと区別する。これらは取得時の結果でありサイトの恒久障害の証明ではない。認証、UA変更、proxy等による拒否の迂回は行っていない。通常ブラウザ、Unity、Blenderは起動していない。公開されている別種の資料として、公式Blender source内のAPI解説と実装を読み、以下に補足する。

## 面・corner・slot: 保存すべき方向と変換

**DOC [B15、B17]**: Object Modeのfaceは`mesh.polygons`、tessellation結果は`mesh.loop_triangles`、Edit ModeのfaceはBMeshのBMFace。polygonはloop列の範囲を持ち、loopからvertex/edgeへ参照する。UV等のcorner属性はloop側との対応を読む。polygon番号、triangle番号、vertex番号を同じidentityとしない。Edit ModeのMeshとは別に編集dataがあり、modeを抜けるまでObject側のMeshへ反映されない。解説の旧属性名を現行全APIの保証に拡張しない。

**SRC [B03–B04、B10、B13]**: Object→Material slot→Material、Mesh face→material_index→そのObjectのeffective slotという方向を区別する。FBX exporterはObject側のMaterialを使う経路を持つ。importerも共有Geometryを使うModelごとにMaterialが違えば、該当slotをObject-linkedへ切り替える。`mesh.materials`だけの観測では不足し得る。

**SRC [B13]**: `blen_read_geom_layer_material`はLayerElementMaterialを読み、`blen_read_geom_array_mapped_polygon`でByPolygon/Direct・IndexToDirectやAllSameの経路を処理する。layerがなければ当該関数は戻る。これは意図されたnull/先頭slotの証明ではない。対応外の組合せもあり、全FBX規格の網羅保証にしない。

**SRC [B13]**: Material割当後、処理したMeshの`validate_material_indices()`を呼び、範囲外indexを先頭Materialへ直した場合に警告する。したがってImport後indexが有効なことは、修正前のnative face-to-slotが正しかった証拠ではない。

**SRC [B10]**: exportのMaterial接続生成はObjectのMaterialを走査し、同じMaterial objectの接続を重複出力しない。面のindexはFBX接続の順に対応する。Mesh側indexからFBX側indexへmapし、範囲外・未export対象をdefaultへ寄せる処理もある。同じMaterialを複数slotに置いたauthoring配置の位置identityは、FBX接続数だけでは復元できない。null slotの全export条件は未監査。

**INFERENCE / VAPB**: source face/corner対応、Object occurrence、slotの順・link・null・重複・unused、FBX Material接続、Unity生成submesh/Rendererの橋渡しを別に証明する。importerの修正やexporterのdedup後に数が合うことを、元の意味が保たれた証拠へ昇格しない。これは製品に推測割当や自動修正を追加する指示ではない。

## Original・evaluated・rest・pose・weight

**DOC [B18–B19]**: `context.evaluated_depsgraph_get()`で評価されたgraphを得る説明と、IDの`evaluated_get(graph)`で評価結果を取り出す説明を区別する。後者単体の完全評価保証はB02にない。original Meshとmodifier等を含むevaluated Meshは異なる。`Object.to_mesh()`の結果はObjectが持つ一時Meshで、`to_mesh_clear()`で解放する。Main databaseへの永続Mesh作成は別のAPI経路。この資料ではAPIを実行していない。

**DOC [B16]**: EditBoneは編集時のhead/tail/roll/parent、Boneはrest定義、PoseBoneはアニメーション・constraint等の対象という区別がある。Edit Mode終了後にEditBone関連参照を使い続けないという警告もある。これからUnityのnullBone補完やfileID0の意味を推定しない。

**SRC [B24]**: Armature deformではvertex-group経路とenvelope経路を区別する。group名からpose channelを引き、非deform boneを除く経路がある。全vertex groupがbone weightとは限らない。

**SRC [B10、B13]**: FBX exportはbone名に対応するvertex groupとMesh vertex indexからClusterのIndex/Weightを書き、rest matrixのためweightが空のClusterも出力する。importでignored child boneの特定clusterを親にまとめる経路では同頂点のweightを合算する。単に全boneが常に統合されるわけではない。leaf bone、deform-only、orientation等のoption次第で対象が変わる。

**INFERENCE / VAPB**: 空weightや空Clusterを不要boneと判定しない。名前一致はこの実装内のlookupでありUnity Transform identityの証明ではない。元vertex/cornerと編集vertex、bone identity、rest・bindposeのframe、実optionを確認する必要がある。Unity nullBone/fileID0のnative挙動は引き続きUNKNOWN。

## Action・slot・NLAとFBX option

**DOC [B20–B23]**: Actionにはslotがあり、animated datablock側がActionとslotを指定する。slotの`target_id_type`が対象datablockの型と合うことが互換条件。名前だけではslotを選べない。同名表示のslotがID typeごとに存在し得る。公式例の「候補の先頭を選ぶ」は互換slotの説明であり、VAPBの元割当を証明する規則ではない。例中の5.1 Manualリンクを5.2 Manual本文確認済とは扱わない。

**DOC [B23]**: `slot.users()`はそのslotによりanimatedされるdatablockを返すという公開解説がある。これは**Blender Action slotの逆引き**であり、Unity Material→Renderer/faceの逆引きやUnity source identityの回復を提供するものではない。

**SRC [B10]**: All Actions経路の`find_validate_action_slot`はlayer/strip/channelbagを走査し、fcurveのdata pathを対象Objectで解決できるbagからslotを選ぶ。pathが解決可能な候補と、本人が意図した元slot・全NLA状態の保存は別。全slotが常に無損失exportされる保証は確認していない。

**SRC [B11]**: export optionのApply ModifiersはArmatureを除くmodifier適用を説明し、shape key exportを妨げる注意を持つ。triangulation、tangent space、leaf bones、deform-only、sampling/simplificationも別option。sourceのdefaultはVAPBの実設定ではなく、推奨presetでもない。modifier bake、shape、bone生成、Action選択を一括して無損失と判定しない。

**INFERENCE / VAPB**: 本人GUIで独立AnimationClipを割当する方針を維持し、その前段のAction/slot/targetと後段のclip binding/rig/Controllerを区別する。新しいAPI解説は保存対象の整理に使えるが、既存の未証明joinやclient動作の成功判定を置き換えない。

## 残る範囲

本文取得できた公式API解説、部分読取の実装、入口、取得不能を分離した。rendered 5.2 Manual/API、5.2 release notes、latest patch順位は未確認のまま。全FBX producerのschema、null/unused slotの全条件、全Action channelbag/NLA/modifier組合せ、Unity native import後のface/skin対応、実binaryとの一致は未証明。今回の補足は公式文書と実装からの日本語要約で、原典の丸ごと転載や製品実装変更は含まない。
