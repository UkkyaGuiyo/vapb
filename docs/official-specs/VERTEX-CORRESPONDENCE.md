# Blender→FBX→Unity: 頂点・face・skinの対応

対象: Unity 2022.3 Manual/API、Blender v5.2.1公式source。確認日2026-10-11 UTC。CP=FBX control point、corner=polygonの各頂点位置に対応する属性単位。用語は読解用で、Unityの内部実装schemaを定義しない。

## 公式に確認したこと

|事項|根拠|意味と限界|
|---|---|---|
|Unity Mesh vertexはposition以外の属性も持つ|DOC U12 Vertex data|normal/tangent/color/UV/bone weights・indices等はvertexに関連する。同位置だけで同じvertexとはいえない|
|Weld Verticesは同位置かつ属性全体が一致する場合の結合|DOC U33 Weld Vertices、API U40|ManualはUV/normal/tangent/vertex colorを例示。詳細な浮動小数比較、skin・blendshapeを含む全内部keyは非公開/未確認|
|頂点順を最適化する設定がある|API U41|同じ数でもsourceのindexとimport後indexの一致を保証しない|
|polygon順を最適化する設定がある|API U42|同じ面数でもface sequence同一とはいえない|
|normal/tangentはimport設定を持つ|DOC U33、API U43–U44|Import/Calculate/None等で情報の採用と生成が変わる。元属性のbyte同一性は自動保証されない|
|mesh compressionはvertex dataにartifactを導入し得る|API U45|raw floatbytes比較の前提にcompression/精度policyが必要|
|16-bit index設定は大きいmeshをchunkへ分割する場合がある|DOC U33 Index Format|すべてのモデルを単一Meshで保持する保証ではない|
|Blender exporterはpolygon vertex indicesと属性layerを別に書く|SRC B10 `fbx_data_mesh_elements`|UVはByPolygonVertex/IndexToDirect、normal mappingはdomainに応じ変わる。CPとcorner属性の数が別になり得る|
|Blender exporterはMaterial indicesをFBX indicesへ変換する|SRC B10 LayerElementMaterial|invalid/除外されたMaterialへのindexにdefaultを使うpathがある。slot数保持の一般保証ではない|
|Blender exporterにはnormal deduplicationの条件付き回避がある|SRC B10 `skip_normal_deduplication`|Unity importとblendshapeに関するissue参照commentを確認。issue本文未読なのでバグの全適用版・解決状況は不明|

## 証明できる対応とできない対応

**INFERENCE [U12、U33、U40–U45、B10]**: 同じCPが複数cornerで異なるUV/normal等を持つと、Unityの「vertexごとに属性値を持つ」表現には複数vertexが必要になる場合がある。反対に、同位置・同属性をweldすれば統合され得る。これは表現モデルと公開settingからの推論であり、Unity native FBX importerの全分割keyを読んだ結果ではない。

**重要**: material境界はsubmesh partitionを変える。しかしUnity公式U10は複数submeshでvertex共有可能と説明する。従って「Material境界なら必ずvertexをsplitする」は公開仕様から導けない。UV seamやhard normal境界があることだけで実データの数差の原因を確定しない。tangent再生成、normal smoothing、welding、mesh optimization、modifiers、triangulation、axis/unit conversion、blendshape/skin import条件を独立に扱う。

今回調査した公開APIには、元FBX CP index→imported Unity vertex indexという対応表を返す契約を確認できなかった。Blender native vertex indexとFBX CP indexの恒久不変性も、このsourceの一部を読んだだけでは保証できない。sourceで書出し順を追えることは特定export revisionの補助証拠であり、Unity native importer内部の対応を証明しない。

## 数が違う場合の扱い

**INFERENCE**: 元Unity、編集Blender、再import Unityでvertex数が異なるだけでは、不具合とも正常な無損失変換とも決められない。再Apply前後が一致しても、同じ変換が安定して繰り返された証拠であり、元meshへの独立対応証明とは別。weightのinfluence総数やbone数の一致もvertex対応の代用にはならない。

追加実測の参考情報はこの調査では再実行していない。私的素材のraw値・対応表は取得/転載していない。担当からの「再Applyは一致、元meshとの独立vertex対応は未証明」という分類を維持する。

## 担当が参照する比較条件（実装提案ではなく判定の前提）

1. source FBX/meta revision、Unity patch、exporter/importer版、両側設定を固定する。Weld Vertices、optimizeMeshVertices/Polygons、index format、normal/tangent、compression、axis/unit、skin influence上限、blendshape、modifiers/triangulationを含める。
2. 元/編集のnative Meshとevaluated Meshを区別し、どちらがFBXに書かれたかを特定する。
3. CP位置だけではなく、face incidence、corner UV/normal/tangent等とsubmesh/Material partitionを含む対応を用意する。同位置duplicateには複数候補が残ることを認める。
4. Unityでsplitされたvertexについて、どのCP/cornerから派生したかの独立した証拠を要求する。many-to-one/one-to-manyを許す比較とindex/byte一致を区別する。
5. weightを対応づいた頂点とbone identityで比較する。bone indexを名前/順番だけで合わせない。bindposeとrest frameも合わせる。
6. 元のsurface/skinを変えない編集（例えば位置の既知差分）の期待値を、設定に応じたUnity表現へ写す必要がある。対応がなければ `NOT PROVEN` を維持する。

位置だけのnearest-neighbor、同数化のためのweld、属性を捨てたhash、一致した集計値だけでの承認は公式仕様から保証されない。今回これらの実装やguard解除は行わない。

## 未公開・未調査

- Unity native ModelImporterの全split/weld key、比較epsilon、skin・blendshapeとattribute seamの全条件。
- importer/postprocessor/packageの組合せによるCP対応保持。custom AssetPostprocessorの作用。
- Blenderの全FBX import/export pathでのvertex reindex、modifier生成vertex、loose edge、shape keyとtriangulationの相互作用。
- 参照commentのBlender issue #123088 / PR !126491の本文、修正版の範囲。commentはSRCに留める。
- 特定VAPBケースの対応表と期待Unity表現。公式一般仕様だけでは当該caseの割当成功を証明できない。
