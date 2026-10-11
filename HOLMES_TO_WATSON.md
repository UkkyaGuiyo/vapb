# ホームズ → ワトソン：VAPB 最新指示

## 現在の指示

- Instruction ID: `HOLMES-20261011-02`
- Status: `READY`
- 作成日: 2026-10-11 JST。発行時刻・正確な指示版は本ファイルの更新commitで特定する。
- 作業名: **Material×面種別の初出順から、面→受信RendererのMaterial参照という候補プランを作り、未観測の6面で反証する。**
- Repository: `UkkyaGuiyo/vapb`
- 確認済み実開発branch: `feature/holmes-topology-boundary-20261011`
- 確認済み実開発SHA: `e09c2ee31b83e22a8fc77dd850961e9fe1be7c76`
- 推奨作業branch: `feature/holmes-ordered-face-plan-20261011`。既存作業と衝突しない隔離先を確認して使用する。既存branchをresetしない。
- 開始: 本書が最新のREADYで未実行なら、日次時刻を待たず着手してよい。共有実機の所有・資源制約は維持する。
- この指示専用branchは製品sourceの最新版でも実装用checkoutでもない。

### 前回指示の扱い

前回 `HOLMES-20261011` は、指定されたKeep Quads OFF/ON比較・source-only診断の範囲で完了と判断した。再実行しない。本書は訂正による再試験ではなく、その結果を受けた次の作業である。

- [前回指示94c1f11](https://github.com/UkkyaGuiyo/vapb/blob/94c1f11fb1fac73aadafd6de2d41a3297c0322f1/HOLMES_TO_WATSON.md)
- [ワトソンの結果REPORT・e09c2ee固定版](https://github.com/UkkyaGuiyo/vapb/blob/e09c2ee31b83e22a8fc77dd850961e9fe1be7c76/tests/evidence/holmes-material-correspondence-20261011/topology-boundary/REPORT.md)
- 実測source/証拠commit: `c3cc3ab14abe9266489ee4505129e2845d65c621`。報告commit: `e09c2ee31b83e22a8fc77dd850961e9fe1be7c76`。
- ホームズは今回REPORT、保存されたON観測、診断・raw読取・判定コード、製品側のMaterial plan、製品仕様、変更ファイル一覧を確認した。Unity/Blenderの実験自体は再実行していない。製品復元完了とは判定していない。

## 1. 証拠から更新した推理

前回の同一FBXはOFFで2群、ONで4群。ONの実群順は `A/Triangles, B/Quads, A/Quads, B/Triangles`、実Material参照は `[A,B,A,B]` だった。したがって、この条件では「Material UID一つ→native一群」は反証された。全面triangleの既存H1まで否定されたわけではない。

次の有力仮説は、**対象Model/Geometry内で、(raw Material UID, 有効topology)という組の初登場順に群を作り、同じ組の再登場は既存の群へ戻す**というもの。ただし前回の4面は四つの組が一度ずつしか現れない。その結果だけでは、組を全体でまとめる方式と、出現runごとに別群にする方式を区別できない。

もう一つ重要な点がある。PrefabのRendererが四つの群に別々のUnity Materialを指定すれば、同じraw Material Aのtriangleとquadに別の最終Materialが必要になり得る。**二つのBlenderスロットを並べ替えるだけでは表せず、面単位の割当候補が必要**という推論である。これはまだ今回の実測結果ではない。

現在 `topology-boundary/diagnose.py` はunordered候補と `group_order=UNDETERMINED` まで。`operators/renderer_binding.py::_material_plan` は複数の異なるMaterialを未証明として拒否する。本書ではそのguardを迂回せず、手前に必要な対応プランを実験コードとして具体化する。

## 2. 今回の成果物・非対象

主作業は一つ：**通常入力から順序付きの面→Material参照候補を生成し、競合規則で答えが分かれる6面の入力一件に対して独立検証する。** 群数だけを確認する実験ではない。

成果は次の三点を一つの小さな検証として残す。

1. native観測を読まない、入力専用の順序付きpartition候補と面割当プランのコード。
2. 未観測の6面に対する固定予測と、raw面→実native群→実Prefab Material参照の独立比較。
3. 一致した場合、使い捨てBlenderコピーへの明示的な実験適用で、同じraw UIDから異なる最終Materialへの面割当を確認する。標準Import対応とは区別する。

製品Import/Confirm/Export、production witness schema、AGENTS、PRODUCT_SPEC、Release、既定branchは変更しない。実験コード・自作fixture・結果は既存evidence階層内に置く。大規模なresolver基盤や新parserは作らない。原本・既存Scene・共有Materialを変更しない。

## 3. 再利用する入口

確認SHA以下の既存コードを先に読む。

- `tests/evidence/holmes-material-correspondence-20261011/topology-boundary/read_input.py`：Model/Geometry/Material UID、active Layer、polygon/cornerの読取。
- 同 `diagnose.py`：宣言keepQuadsと対象外判定。
- 同 `judge.py`：`native_faces`、`membership`、`cover`。明示topology、exact UV corner、外周・内部辺の多重度による独立照合。
- 同 `Capture.cs`、`generate_fixture.py`：自作入力と実native取得。
- `unity/prefab_parser.py`、`unity/effective_prefab.py`、`unity/occurrence_projection.py`：serialized参照と対象occurrence。新しい簡易Prefab parserで置き換えない。
- `operators/renderer_binding.py::_material_plan`：将来の接続点の読取のみ。現行guardを変更・monkeypatchしない。
- `blender/fbx_receipt.py` と既存Material providerの識別処理：既に証明済みのModel/Geometry/実ObjectやMaterial identityだけを再利用する。

旧実測ファイルの意味・hashを変えない。必要な小関数は新しい小さなadapterから再利用し、変更が本当に必要なら旧実験を固定commit参照のまま保つ。完了済みレビューやアプリ測定を再実行しない。

## 4. まず入力専用の候補プランを作る

関数名の例：`predict_ordered_partitions(raw, meshes_meta)` と `plan_receiver_materials(partitions, occurrence)`。名前は役割が明確なら既存慣例に合わせてよい。

### partition予測

対象は当面、既存decoderが確認できる単一static Model/Geometry、unique Material接続、active Layer0、対応済みMaterial layer、triangle/凸平面quad、小さなindex範囲のみ。Skin/Shape/Animation、raw接続重複、複数layer、n-gon、空/null/overlay、大きなindex範囲を今回の対応に混ぜない。

- `keepQuads=0`：有効topology候補をTrianglesとする。元quadとそのcornerは保持し、三角形化後index順や対角線を予言しない。
- `keepQuads=1`：元triangleはTriangles、元quadはQuads。
- キーはこのModel/Geometryに属する `(Material UID, 有効topology)`。順序付き辞書相当で最初の出現時だけ群を作る。
- 各群には予測ordinal、topology、raw UID、元polygonの集合・多重度を残す。同じUIDが複数の群に現れることを許す。
- 設定欠落、不正な参照、対象外入力は理由付きで拒否。metaの宣言を任意Unity環境の実効policy証明にしない。

**結果はCANDIDATE。`EXACT`や製品PASSにしない。** 既存MixedFour OFF/ON保存観測とのoffline照合は校正・回帰として利用できるが、新しい独立実証とは呼ばない。

### Material参照への結合

対象occurrenceの順序付き有効Material参照を既存解析から読み、予測群ordinalに対応する参照を取る。Material identityはpackage/GUID/signed fileIDで保持し、raw UIDとUnity GUIDを名前や数値の一致で同一視しない。

- 入力FBX/metaのrevision、対象Mesh/Renderer/occurrenceのidentity・revisionを別々に保持する。
- source bindingが未証明なら、その状態を残す。単一候補だから結び付けたことにしない。
- 参照長不一致、null、provider欠落、競合するscopeは個別の未解決理由にする。余分な参照を削除・末尾補完しない。
- 出力は少なくとも `raw polygon identity → candidate native group → exact serialized Material reference`。raw→groupが候補であることと、参照そのものが正確なことを混同しない。
- `ready_to_apply=false`、`partition_evidence=CANDIDATE` を保持し、native観測や実験用UVの判定を製品witnessに偽装しない。

予測関数と候補プランにはnative JSON、GetIndices結果、観測済み群順を引数として渡さない。観測ファイルがない作業場所でも実行できることを対照試験に含める。

## 5. 一件だけの新規入力で対立予測を分ける

新しい自作staticモデルを、次の六つの独立した平面faceで用意する。元MixedFourは変更しない。A/Bは説明用ラベルで、判定には書き出された実UIDを使う。

```text
p0 A triangle
p1 B quad
p2 A quad
p3 B triangle
p4 A triangle  # p0と同じ組が離れて再登場
p5 B quad      # p1と同じ組が離れて再登場
```

位置とUV fingerprintを互いに重ねず、UVは小さな二進分数の一意cornerにする。自作fixtureの照合条件であり、通常製品入力への必須UV仕様ではない。実FBXをdecodeし、六面・接続・active layer・実際の出現順を確認する。exporterが順を変えた場合は実bytesから予測を作る。識別力を失った入力はnative測定前に検出し、意図した入力を作れなければ該当工程を未判定にする。

今回はKeep Quads ON一条件。前回のOFF/ON一組は再実行しない。次の予測をnativeの面結果を見る前に固定する。

| 仮説 | 上の実順が保存された場合の予測 |
|---|---|
| 組の初出順で全体を集約 | 4群：A/T={p0,p4}, B/Q={p1,p5}, A/Q={p2}, B/T={p3} |
| 組の連続runごとに分割 | 6群。離れたp4,p5は新しい群 |
| UIDを先にまとめ、その中でtopology初出 | 4群：A/T, A/Q, B/Q, B/T。群数は同じだが順序が異なる |

### 受信側も固定する

このモデルを参照する**単一の直接Prefab**を自作し、RendererのMaterial配列を四つの異なる外部Material参照 `[R0,R1,R2,R3]` にする。Materialは自作の単純なものとし、名前類似や見た目ではなく実GUID/fileIDを保存する。既存の自作fixture生成・package組立経路を使う。

この配列は観測前に決めた作者の指定。native群数を見て伸縮したり、観測されたfaceに合わせて並べ替えたりしない。nativeが6群を作れば不一致も記録する。Material名に組の正解を埋め込み、その名前を判定器が読むことも禁止。

Unityは開発fixture作成・答え合わせに使用できるが、通常Importの前処理として要求しない。fixture作成時にUnity APIで正当なMesh/Prefab/Material identityを得ることと、native face順を読んで予測を作ることを区別する。受信配列の作成にGetIndices/GetTrianglesや予測した面集合を使わない。

Package、FBX、meta、Prefab、Materialの実bytes・hashとsource-only候補を、独立native面観測の前に凍結する。作成工程で既に得た情報とholdoutとして伏せた面観測の範囲を記録する。

## 6. 独立判定と、条件付きの使い捨て適用

既存の所有・共有資源ルール内で新入力を観測する。Unity版と実効Importer設定、Mesh/Renderer identity、全topology/index/baseVertex、UV、モデルと対象Prefabの順序付きMaterial参照を捕捉する。native群を候補プランに合わせて並べ替えない。

独立judgeはraw face fingerprintから実native群を求め、その群の実Prefab Material参照を読む。予測関数をimportして正解を作らず、group数だけでなく各元polygonの参照まで比較する。

組の初出仮説なら予測される最終参照は `p0/p4→R0, p1/p5→R1, p2→R2, p3→R3`。これは予測であり、判定器に埋め込む正解ではない。

- nativeの観測が成立して予測と違えばFALSIFIED。原記録を保存し、そのまま次回へ返す。別入力を次々作って仮説に合わせない。
- 個数だけ一致して面・順序・参照が違えば不一致。名前、面数、位置の近似で修復しない。
- 対応に必要なidentityやcornerが足りなければUNDETERMINED。欠けた接続だけを列挙する。

**候補と独立native観測が全対象面で一致し、対象Blender faceとproviderのidentityも実験として一意に照合できた場合だけ**、通常Importから得た対象の使い捨てコピーで明示的な試験適用を行う。共有Meshはコピー側で独立させ、原本Object/mesh/Materialの状態を保つ。

コピーへの試験は、既存の安全なObject-linked素材設定等を再利用し、最終参照の異なる面には別slotとpolygon.material_indexを割り当てる。二つの元slotの単なる並べ替えで済ませない。実際の各faceが持つpackage/GUID/fileIDを独立judgeと照合し、未適用原本のsnapshot不変も確認する。

これは**診断用の明示的適用**であり、標準Confirmをmonkeypatchしたり、未証明receipt/EXACT属性を注入したりしない。実験でUV照合を使ったなら、その対応はDIAGNOSTIC_ONLYとし通常入力にも存在すると主張しない。Blender側の対応が得られなければコピー適用だけをNOT_RUNとし、source-onlyプランとnative判定を捨てない。

## 7. 必要な対照・完了条件

今回増やしたコードに対して、離れた同一組の再利用、同一UIDで異なるtopology、同じ群数のラベル交換、元faceの欠落/重複、宣言外topology、受信配列長不一致・null/provider欠落・違うrevisionを確認する。既存対照の再利用を優先する。結果に合わせたepsilon変更はしない。面所属、winding、位置、描画は別判定。

完了条件：

- 入力だけで順序付きの候補プランが出る実行コードと、根拠・未証明箇所が保存されている。
- 新しい6面のnative所属と受信Material参照を独立比較し、三つの予測を分類できた。または具体的なblocked/未判定理由を残した。
- 一致時は上記条件内のコピー適用を確認するか、その接続だけが未実施の理由を明示した。
- 「一般保証がない」だけで終わらず、次の製品patchに必要な最小差分を挙げる。今回の結果を全入力保証にしない一方、無限の全入力証明も要求しない。

今後の製品用対応は、検証された入力scopeとrevision/policy、source→実Object/face接続を満たす範囲に限定する必要がある。今回の候補やdiagnostic witnessだけで標準guardを解除しない。nativeで正しい割当が存在すること、候補が一致すること、標準VAPBで自動復元できることを三つの別の到達点として報告する。

## 8. 保全・既存作業・停止

開始時に最新remote/head、同IDの実行結果、未保存差分、対象AGENTS/PRODUCT_SPEC、既存の知識集・実機制約を確認する。既に同じ作業が完了/進行していれば重複実行しない。別途ユーザー指示があれば本書との差を報告し、競合させない。

新SDK、課金サービス、共有Editorの強制終了、lock削除、無断merge/Release/force-pushは行わない。原本Package/FBX/meta/Prefab/Material/Sceneと旧証拠は保護する。private/commercial素材、個人path、秘密、生ログを公開しない。

実機枠が空かない場合はnative工程だけBLOCKEDとし、input-onlyコードや対照など独立した作業を進める。宣言外のfixture変更、成否不明の復旧、第三者更新、scope外入力は該当工程を止めて記録。復旧は所有資源の終了確認後、今回の自作配置に限る。仮説が外れたための自動scope拡大はしない。

## 9. 結果保存と報告

保存先の候補：
`tests/evidence/holmes-material-correspondence-20261011/ordered-face-plan/`

既存の近接する適切な保存先があれば再利用し、別管理基盤は作らない。実行用の入力専用コード、固定予測、実fixture、native観測、独立judge、コピー適用の可否、REPORTを必要最小限で保存する。

REPORTには指示ID `HOLMES-20261011-02`、取得した指示commit、開始branch/SHA、実source hash、対象入力hash、各仮説の支持/反証/未判定、元face→予測群→実群→実Material参照の比較、PASS/FAIL/NOT_RUN/BLOCKED、原本保全、review、製品変更有無、残る最小の接続課題を記載する。実際のmodel/reasoningは確認できた範囲だけ記載する。

生成・予測側とnative判定側を独立review contextで確認する。完了済みの旧reviewをやり直さず、今回追加した部分を対象にする。目的別commit/push後にGitHubから対象commitと主要本文を読戻し、結果branch/path/commit URLを報告する。

ホームズの今回の書込はこの指示ファイルだけ。指示の保存commitをワトソンの実験開始・完了証拠にしない。

## 公式仕様の確認先

- Unity 2022.3 Model tab / Keep Quads・index format: https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Model.html
- RendererのMaterial参照配列: https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Renderer-sharedMaterials.html
- topologyに従うindex取得: https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetIndices.html

公式説明はtopology分離とAPIの意味を支持する。組の初出順という採番アルゴリズム自体の公式保証とは扱わない。

## 固定の受け渡し

最新指示正本：`docs/holmes-watson-handoff:HOLMES_TO_WATSON.md`

https://github.com/UkkyaGuiyo/vapb/blob/docs/holmes-watson-handoff/HOLMES_TO_WATSON.md

```sh
git remote get-url origin
git fetch origin docs/holmes-watson-handoff
git show FETCH_HEAD:HOLMES_TO_WATSON.md
```

READYかつ未実行のIDだけを読み、指示branchへcheckoutせず実開発の最新差分を確認する。結果は指示IDと指示commitを添えて作業branchへ戻す。次回ホームズはその実ファイルを読む。指示公開はCodexの自動起動を意味しない。
