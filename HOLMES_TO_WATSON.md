# ホームズ → ワトソン：VAPB 最新指示

## 現在の指示

- Instruction ID: `HOLMES-20261011`
- Status: `READY`
- 作成: 2026-10-11 JST。発行時刻・指示版はこのファイルを更新したGitHub commitで特定する。
- 作業名: **Materialの初登場順だけで十分か――Keep Quadsによる面区分の分岐を調べ、入力側の適用条件をコードで切り分ける。**
- 実行開始: **次の日次実行を待たず、未実行なら本書を読んで着手する。** ユーザーから「早速。ワトソンが止まっている」と即時指示の依頼があった。
- Repository: `UkkyaGuiyo/vapb`
- 確認した開発branch: `feature/holmes-material-correspondence-20261011`
- 確認した開発SHA: `842067fb1aa29eeb4b9f3a4560ac6d529a21f50a`
- 推奨作業branch: `feature/holmes-topology-boundary-20261011`。開始時に既存branchと作業中の差分を確認し、衝突しない隔離作業先を使う。既存branchをresetしない。
- 前回の指示ファイル: [受け渡し初期設定 d136832](https://github.com/UkkyaGuiyo/vapb/blob/d13683253453c33ab00e8c52450813e480fcdd7b/HOLMES_TO_WATSON.md)。技術指示未発行だった初期状態を、本書のREADYで置き換える。
- 引き継ぐ結果: [HOLMES最終報告・固定版](https://github.com/UkkyaGuiyo/vapb/blob/842067fb1aa29eeb4b9f3a4560ac6d529a21f50a/tests/evidence/holmes-material-correspondence-20261011/FINAL_REPORT.md)。R/A/B/E/U/D/Hの既存結果は保持し、理由なく再測定しない。

**今回の完了条件は、後述する新規の一組の比較と、通常入力だけで評価できる適用条件候補を、実行可能な診断コード・証拠とともに残すこと。全FBXの普遍則の証明でも、既存のDEFER報告の書き直しでもない。製品の自動割当guard解除は今回の作業に含めない。**

## 1. ホームズの推理：今回は何が新しいか

既存実験は、三つのMaterialを使う12三角形が中心だった。元metaの`meshes.keepQuads`は0。H実験で変えたのはポリゴン最適化であり、四角形保持の検証ではない。

新たに確認したUnity 2022.3公式マニュアルには、Keep Quadsを有効にして三角形と四角形が混在する場合、両者を分けるsubmeshが作られるという説明がある。これは**Materialの実体だけでなく、面の種類も区分のキーになり得る**という具体的な競合説明である。複数Material時の正確な個数・並び・Renderer参照の扱いまでは、この記述から決めつけない。

さらに、既存`judge_faces.py`の`decode()`は12三角形専用で、`native_rows()`はindex数が3の倍数なら三角形として読む。一般の新規入力で、index数だけから面の種類を決めることはできない。例えば12個のindexは四角形3面でもあり得る。これは旧三角形実験を否定する発見ではなく、**新しい実験に旧判定器を無変更で流用できない理由**である。

今回の問いは「一つのMaterialは常に一つのnative groupか。それともMaterial×面の種類などで分かれるか」。結果は、入力解析でH1候補から何を除外すべきか、将来の対応表を一対一の配列にしてよいかを変える。単に成功例を一個増やす作業ではない。

### 読んでから使う根拠

- [既存の元meta](https://github.com/UkkyaGuiyo/vapb/blob/842067fb1aa29eeb4b9f3a4560ac6d529a21f50a/tests/evidence/holmes-material-correspondence-20261011/cases/original.fbx.meta)
- [旧判定器](https://github.com/UkkyaGuiyo/vapb/blob/842067fb1aa29eeb4b9f3a4560ac6d529a21f50a/tests/evidence/holmes-material-correspondence-20261011/judge_faces.py)
- [PRODUCT_SPEC・入力とMaterialの責任分担](https://github.com/UkkyaGuiyo/vapb/blob/842067fb1aa29eeb4b9f3a4560ac6d529a21f50a/PRODUCT_SPEC.md)
- [Unity 2022.3 Model tab / Geometry / Keep Quads](https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Model.html)
- [ModelImporter.keepQuads](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-keepQuads.html)
- [Mesh.GetIndices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetIndices.html)
- [Mesh.GetBaseVertex](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetBaseVertex.html)
- [Renderer.sharedMaterials](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Renderer-sharedMaterials.html)

公式資料は面種別による区分やAPIの意味の根拠であり、H1全般や特定順序の保証ではない。ホームズ自身は今回Unity/Blenderを起動しておらず、以下の結果はまだ得られていない。

## 2. 開始と作業範囲

1. 正規remote、最新開発head、未保存差分、root/対象pathのAGENTS、PRODUCT_SPECと既存の知識集・共有実機ルールを確認する。本書作成後に同じ課題が処理されていれば、結果を読んで重複実行しない。
2. 指示専用branchを作業baseにしない。実開発SHAを確認した隔離作業先を使い、他の作業や原本を退避なしで上書きしない。
3. 今回は**小さな自作入力一つ、同じFBXに対するKeep Quads OFF/ONの二条件**に絞る。既存の専用Unity環境・Blender・parser・runnerを再利用する。新しいSDK、課金サービス、別の管理基盤は導入しない。
4. 許可する変更は、この実験に必要な小さな生成/捕捉/判定コード、source-only診断関数、テストと結果記録。原則`tests/`内に置く。製品Import/Confirm/Export、witness schema、AGENTS、PRODUCT_SPEC、Releaseには手を入れない。
5. 前回報告の「追加起動不要」は前回の検討範囲についての判断。本書は公式仕様に基づく別の競合予測を指定する。ただし共有資源・権限・原本保護の制約は引き続き守る。

## 3. 入力一つを用意し、予測を固定する

互いに重ならない平面上の小さな面を四つ作り、二つの異なるMaterial実体A/Bに次のように割り当てる。

```text
face p0: Material A、三角形
face p1: Material B、凸の平面四角形
face p2: Material A、凸の平面四角形
face p3: Material B、三角形
```

Skin・Shape・Animation・Nested Prefab・未使用Material・null・重複接続・重ね描き・大きなindex範囲は今回は入れない。Material A/Bという名前は説明ラベル。実際の追跡には書き出されたFBXのUIDと接続を使う。

既存Blender/FBX出力機能で自作の新規FBXを生成する。四角形を保存できたこと、二つのMaterialと面割当、UV・頂点・接続を**書き出した実bytesから独立して確認**する。元HOLMES fixtureを壊して四角形を捏造しない。既存の固定12面generator/parserの制約を黙って外さない。

比較用UVは、各元polygon/cornerを一意に照合できる、小さく正確に表現可能な二進分数の座標にする。面のUV領域は重ねない。UVは独立判定用の指紋であって、製品が全入力へ要求する条件ではない。

exporterが面や接続の順を変えたら、生成前の配列を正解にせず、実FBXの並びを記録する。主目的の「Materialだけか、面種類でも分かれるか」を識別できるなら、それ以上の並べ替え作業はしない。細かい順序仮説が同じ予測になった場合は識別不能と記録する。

Unity観測前に次を保存し固定する。

- 入力FBX hash、ノード/Geometry/Material UID、全polygonのcorner数と使用Material、元の順序。
- **P_UID:** 使用Material UIDの初出だけでgroupを作る予測。この四面なら二群。
- **P_UID_TOPOLOGY:** Keep Quads ONでは同じMaterialでもTriangles/Quadsが別groupになり得る予測。実際のgroup順は未確認。複数の順序候補を比べるなら、その候補も観測前に固定する。
- OFFでは四角形が三角形化されるが、どの対角線が選ばれるかやnative index順を予測に埋め込まない。

この予測を作る診断関数は、raw FBX/metaなど入力情報だけを受け取る。Unityの観測JSONを読み込んで予測を後付けする関数にしない。

## 4. 同じFBXをOFF/ONで観測する

既存の所有・隔離されたUnity 2022.3.22f1環境で、同じ新規作業assetのFBX bytesを維持し、`keepQuads=false`と`true`を比較する。二条件で一つの比較とする。Material生成・読み取り・最適化等の他の**実効設定**は固定し、両条件で捕捉して照合する。

ModelImporterがmetaを正規化して書き直した場合、metaの字面の差と実効設定の差を分ける。比較用コピー以外は変更しない。別の実効設定まで変わっていたら単独要因比較として採用せず、差を解消できる範囲で修正する。

各条件で最低限捕捉するもの:

- FBX/meta hash、Unityの実version、実効Importer設定。
- 対象の実Mesh GUID/signed local fileID、Renderer、subMeshCount。
- **全submeshのtopology、indexCount、baseVertex、全index、必要なUV/頂点。** `GetTopology`または`GetSubMesh(...).topology`で面種別を読み、`GetIndices`を使う。`applyBaseVertex`の扱いを記録し、二重にoffsetを加えない。
- Trianglesは3 index、Quadsは4 indexとして扱う。`GetTriangles`や`len(indices)%3==0`だけで判定しない。未対応topologyを三角形へ読み替えない。
- 実Rendererの`sharedMaterials`の順序付きGUID/fileID。重複、null、配列長とsubmesh数の不一致もそのまま残し、観測を都合よく合わせない。

この段階は**モデルImporterの区分規則の検証**である。Prefabを合成してMaterial配列を変更する必要はない。Prefab occurrenceの上書きまで調べたことにしない。元Materialを改名・変更してnative側の並びを誘導しない。

既存の`CaptureNative.cs`、`CaptureBoundary.cs`、`runtime/VapbHolmesCoordinateProbe.cs`から、環境捕捉・hash・public API取得を必要範囲で再利用する。ただし三角形専用部分はそのまま流用しない。新規条件専用の小さなadapterでよく、旧実験の意味や保存schemaを変更しない。

## 5. 元の四面を独立して照合する

生成側とは分離した判定を使い、raw FBXの面→nativeの実face/group→実Material参照を観測する。予測のP_UIDやP_UID_TOPOLOGYを正解ラベルとして使わない。

OFFでは元四角形一面が二三角形に分かれるため、rawとnativeのtriangle数の単純一致を要求しない。既知の凸平面四角形に限り、UV corner対応と外周辺の多重度、内部対角線の対消去、重複/欠落の有無から、同じ元polygonを覆うことを判定する。面の所属とwindingを別に記録する。対角線の違いだけを誤割当としない一方、面積の合計だけで重なりや穴を見逃さない。対応にnativeから未知の新規cornerが必要になったら、勝手な近似をせずそのケースを未判定にする。

ONではquadの四cornerを保ったまま照合し、観測前に勝手に三角形へ変換して区分の差を消さない。

最小の判定器対照は、欠落face、重複face、quadをtriangleと偽るtopology、誤ったMaterial/groupへのラベル交換。正しい対照が通り、不正対照を拒否することをnativeの製品判断前に確認する。新しい許容誤差を結果に合わせて設定しない。

必要なら元FBXをBlenderで一度だけ読み、その四面/slotと照合する。meta二条件だけのために同じBlender実験を重複起動しない。Importやsource-only予測に開発用Unity観測を注入しない。

## 6. 観測を、通常入力から読める適用条件候補へ変える

実験結果と合わせて、raw polygon種別とmetaを読む小さな**source-only診断関数**を残す。既存parsed node/metaを入力に使い、新しいFBX parserやproduction witness schemaを作らない。診断は最低限次を区別する。

- 全面triangle: `TRIANGLE_ONLY_CANDIDATE`。
- quadを含みkeepQuadsが明示OFF: `TRIANGULATION_BOUNDARY_UNVERIFIED`。
- keepQuadsが明示ONでtriangle/quad混在: `MIXED_TOPOLOGY_REQUIRES_PARTITION_RULE`。
- 設定欠落・不正なlayer/参照・今回対象外のpolygon/topology: `UNKNOWN_SCOPE`と具体的理由。

これは**適用候補や除外理由**であり、`EXACT`、復元`PASS`、全triangle対応済みという証拠ではない。metaの記載値を、任意の外部Unity環境の実効設定を証明する値に昇格させない。ファイルhashの許可リストで自作fixtureだけを「対応済み」にする実装も禁止。

今回のpure診断と予測にはUnity観測ファイルの場所を渡さず、入力だけで結果が出ることをテストする。独立judgeがその予測とnative観測を照合する。これにより「正解がないので何も作れない」と「観測を盗み見て予測した」をどちらも避ける。

## 7. 結果ごとの判断

- ONで同じraw Material UIDが複数topology/groupへ分かれれば、**Material UIDだけの一対一対応をこの条件で反証**し、どの元面がどのgroup/実Material参照へ入ったかを示す。既存の全triangle実験のH1まで否定しない。
- OFFでP_UIDと面所属が一致すれば、この入力・設定での支持とする。全quad/n-gonや別producerまで対応済みにしない。
- ONでもP_UIDと同じ区分なら、公式記述の対象、実際のraw polygon、keepQuadsの実効値、native topologyを確認し、不一致の所在を報告する。期待どおりの結果を作るまでモデルを変え続けない。
- 予測と異なるが判定器が有効なら反例。生成・環境・照合が成立しないなら未判定。`FALSIFIED`と試験器自体の`FAIL`を混ぜない。

最終的に「いずれも一般保証なし」だけで終えず、**どの読み取り可能な条件が増え、どの候補を除外でき、次の製品実装が一対一か一対多かをどう考え直すか**を明記する。今回の範囲が終わったら無制限の追加matrixへ進まない。

## 8. 製品への反映条件と非対象

今回、製品のguardを外さず、通常Importの挙動を変えない。成果は限定規則・反例・入力条件を扱える診断コードである。独立した通常入力への適用根拠が得られたら、次回の製品patchに必要な最小の変更点と検証条件を提案する。証拠の強さを変えず、既存carrierに無い情報を有ることにしない。

無関係なlegacy ordinal経路、Bone Action、Skin数値一致、Shader、配布ZIPの修正は混ぜない。通常ImportのUnity前処理必須化、手動Material貼り直しの標準化、GUID/fileIDの置換、仕様縮小、課金・新SDK導入、無断merge/Releaseは禁止。将来の製品実装へ無限の全入力証明を要求することもしない。まず識別可能な対応範囲と具体的な反例を扱う。

## 9. 安全・停止・復旧

共有Unity/Blenderの実行枠・メモリ・lock・所有権は既存ルールに従う。他のEditorを停止したりlockを削除したりしない。空きがなければnative実行だけ`BLOCKED`とし、入力作成・source-only診断・判定器対照など独立して可能な範囲を進める。日次時刻まで待つ必要はないが、共有資源を奪ってよいという意味でもない。

原本Package、既存FBX/meta/Prefab/Material、保存済みScene、過去の観測は変更しない。使い捨て作業assetだけを所有pathに配置し、元hash・既存ファイル一覧を記録。復旧は所有資源の終了確認後に今回の配置だけへ行う。成否が不明な復旧を成功扱いしない。

不正fixture、宣言外の意味変更、独立した面照合の欠落、第三者更新、実効設定の意図しない差、権限不明があれば該当工程を止め、必要な不足を具体的に記録する。既存実験をやり直して代わりの成功にしない。購入素材、私的生ログ、ローカル個人path、秘密は公開しない。

## 10. 保存と次回への報告

既存階層の下に、本指示の結果をまとめる:

`tests/evidence/holmes-material-correspondence-20261011/topology-boundary/`

既存結果を上書きせず、必要な自作fixture、使用source、固定予測、raw/native観測、診断/判定器、結果要約をここへ保存する。巨大な新検証基盤を作らない。生成と独立judgeの変更を別のreview contextで確認し、今回変えた箇所と新証拠だけをレビューする。利用可能な実モデル設定を正直に記録する。

結果の`REPORT.md`には次を含める:

1. Instruction ID `HOLMES-20261011`、読んだ指示commit、実行branch/開始SHA/実際のsource。
2. 新たな問い、固定した予測、入力と許可した差分、各hash。
3. OFF/ONの全group一覧: topology、元polygon集合、raw Material UID、native Material GUID/fileID。欠落/重複も保持。
4. 予測の支持・反証・未判定と根拠。面所属/winding/位置/描画は別判定。
5. source-only診断関数のpath、呼出方法、入力だけで評価できる項目と不明な項目。
6. PASS/FAIL/NOT_RUN/BLOCKED、保全・復旧・review結果、製品コード変更なし。
7. 次の製品判断を変えた具体的事実と、残る最小の問い。
8. 目的別commit/push後のGitHub readback、結果branch/path/commit URL。

新指示発行commitとワトソンの実行結果commitは別物。ワトソンは結果を作業branchへ保存し、ホームズの指示branchには実装を混ぜない。無断merge・force-push・既存履歴削除をしない。本書の作業が未完了の間は同じIDを二重実行しない。

## 固定の受け渡し方法

- 指示正本: `docs/holmes-watson-handoff:HOLMES_TO_WATSON.md`
- 固定URL: https://github.com/UkkyaGuiyo/vapb/blob/docs/holmes-watson-handoff/HOLMES_TO_WATSON.md
- 指示branchは製品の最新版や実装用checkoutではない。未保存作業を切り替えず、正規remoteを確認して読み取る。

```sh
git remote get-url origin
git fetch origin docs/holmes-watson-handoff
git show FETCH_HEAD:HOLMES_TO_WATSON.md
```

READYかつ未実行のIDだけを対象にする。開始時の実装差分と既存作業を必ず再確認する。ホームズの仮説も検証する。結果はIDと指示commitを添えてGitHubへ戻す。ホームズは次回、その実ファイルから推理を更新する。指示公開そのものはCodexの自動起動や実験成功を意味しない。
