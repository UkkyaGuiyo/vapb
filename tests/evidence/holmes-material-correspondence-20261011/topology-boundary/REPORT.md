# HOLMES-20261011 — Keep Quads OFF/ON 実行結果

**完了：同じ自作FBXでOFFは2group、ONは4group。ONでは同じMaterial UIDがtriangle/quadの別groupに分かれ、UIDだけの一対一対応をこの条件で反証した。** 通常入力だけの診断コードを追加した。製品Import/Confirm/Export、guard、witness schema、仕様は変更していない。

## 1. 指示・作業同一性と差分

- Instruction ID: `HOLMES-20261011`、取得状態READY、[指示commit](https://github.com/UkkyaGuiyo/vapb/blob/94c1f11fb1fac73aadafd6de2d41a3297c0322f1/HOLMES_TO_WATSON.md): `94c1f11fb1fac73aadafd6de2d41a3297c0322f1`、指示blob `18e7c155561fe158166cc3bc292d7d99fa0d630b`。保存前にも指示branchの同commitを確認。
- Project VAPB、正規remote `https://github.com/UkkyaGuiyo/vapb.git`、実行branch `feature/holmes-topology-boundary-20261011`、開始SHA `842067fb1aa29eeb4b9f3a4560ac6d529a21f50a`。開始時clean、同課題の結果branch／commitなしを照合。指示branchを実装baseにしていない。
- 初期指示d136832はID NONE / WAITING_FOR_FIRST_DAILY_BRIEFだった。今回は明示単発のREADYで、混在4面・Keep Quads・source-only診断を追加した。前回Hはpolygon最適化の変更であり今回の実験ではない。R/A/B/E/U/D/Hと前回最終報告は無変更・再実行なし。定期監視は再開していない。
- 実AGENTSとPRODUCT_SPECの層／identity／Material責任分担、既存Atlasの面所属・importer制約、共有実機契約を再読。共通AGENTS SHA256 `9BE8886133EEE50F5E24A5A183AF086EACDFEE41EBCF3D5AB0510907D34D6918`。私的実パス・ログは公開しない。
- 実際の生成は [generate_fixture.py](generate_fixture.py)、捕捉は [Capture.cs](Capture.cs)、raw読取りは [read_input.py](read_input.py)、判定は [judge.py](judge.py)。実行source固定commit `c3cc3ab14abe9266489ee4505129e2845d65c621`、各SHA256は [run-summary.json](run-summary.json)。freeze_inputだけは公開時にprivacy scan内の個人名literalを除去したため、実行版／公開版hashを分けて記録。予測・raw解釈は変更せず、nativeを再実行していない。

## 2. 新しい問い・固定予測・実入力

[Unity 2022.3 Keep Quadsの説明](https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Model.html)は混在面をtopologyで区分するとする。複数Material時の個数・順序は公式説明だけで推測せず実測した。[GetIndices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetIndices.html)はtopologyに従うindexを返し、applyBaseVertex=trueではoffset適用済み。捕捉ではfalse側＋GetBaseVertexとの一致も検査した。

実FBXから独立に確認したraw順はp0=A triangle、p1=B quad、p2=A quad、p3=B triangle。Material接続UID A=`519368633`、B=`642757480`。UVは14個の一意な二進分数corner。Geometry/Model UID、CP位置、UV、接続、各polygonは [input-and-predictions.json](input-and-predictions.json) に保存。生成前配列をnative正解に使わない。active Layer0のUV／Material Type/TypedIndex参照も検査した。

- FBX SHA256: `448cdbd785072d2c25be718a3ec8d9f0e64de404857094b97f09b0ed229302bd`。
- 初期meta／OFF meta: `19f8f38515fd37db34dbd90c118112ddeb0bdf4c1808f4083e3c3bef31592964`。
- ON meta: `d1334dbb444ac3d0d00ffd12a512de8fe1ea44d8795288aa2189f1b5e227db3b`。
- native前固定予測JSON: `ab75c0d1316c2cc34b39f67d8714a6f0ae91f8caa72dbe4897b74a9c44836eaf`。

固定したP_UIDはUID初出A/Bによる二群。P_UID_TOPOLOGYはONで同じUIDがtriangle/quadへ分かれ得るという四区分候補で、順は未指定。OFFの対角線・native index順を予測へ埋め込まない。二条件のFBX bytesは同一。全実効policy差は `meshes.keepQuads: false→true` だけ。meta字面ではminBoneWeight 0→0.001もあるが、実効値は両方 `0.0010000000474974513` で不変。meta差を別の実効設定変更へ混同しない。

## 3. OFF/ONの全groupと実参照

Unity 2022.3.22f1。Mesh GUID=`ce412039a7b14c91af5e832bbcdec041`、signed fileID=`6996873464266047000`。モデルRendererは同GUID / signed fileID=`-7511558181221131132`。全Materialも同GUID、A fileID=`2341414557577028177`、B fileID=`2109986408413221875`。名前対応ではなく、raw面のexact join→native group→実Renderer配列参照の観測である。

| 条件 | group | topology | indexCount | baseVertex | 元polygon集合 | raw Material UID | 実Material GUID / signed fileID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OFF | 0 | Triangles | 9 | 0 | p0,p2 | 519368633 | ce412039a7b14c91af5e832bbcdec041 / 2341414557577028177 |
| OFF | 1 | Triangles | 9 | 0 | p1,p3 | 642757480 | ce412039a7b14c91af5e832bbcdec041 / 2109986408413221875 |
| ON | 0 | Triangles | 3 | 0 | p0 | 519368633 | ce412039a7b14c91af5e832bbcdec041 / 2341414557577028177 |
| ON | 1 | Quads | 4 | 0 | p1 | 642757480 | ce412039a7b14c91af5e832bbcdec041 / 2109986408413221875 |
| ON | 2 | Quads | 4 | 0 | p2 | 519368633 | ce412039a7b14c91af5e832bbcdec041 / 2341414557577028177 |
| ON | 3 | Triangles | 3 | 0 | p3 | 642757480 | ce412039a7b14c91af5e832bbcdec041 / 2109986408413221875 |

Renderer配列はOFF `[A,B]`、ON `[A,B,A,B]`。重複参照を統合していない。今回null・空group・配列長不一致は観測なし。全index/UV/頂点/normal、policy、hashは [OFF.json](OFF.json) / [ON.json](ON.json)、全所属は [judgment.json](judgment.json)。applyBaseVertex=trueで記録し、offsetを二重加算していない。Prefab occurrenceのoverrideは実験していない。

## 4. 支持・反証・未判定

- **P_UID OFF：VERIFIED限定観測／一般則UNDETERMINED。** 元quadは各2triangleとなり、A/B二群の所属が予測と一致。
- **P_UID ONのUID一つ→native一群：FALSIFIED。** Aはgroup0/2、Bはgroup1/3へ分かれた。旧全面triangle H1の観測範囲は否定しない。
- **P_UID_TOPOLOGY：VERIFIED限定観測／一般則UNDETERMINED。** このON入力ではUID×Triangles/Quadsに四区分。順p0,p1,p2,p3は観測値であり普遍的順序規則へ昇格しない。
- raw/native exact UV corner対応、外周辺多重度、内部対角線の逆向き対消去で元4polygonの被覆を判定。OFFでtriangle数一致は要求しない。ONのquadはquadとして扱った。未知corner・欠落・重複は拒否。どの対角線でも同じ被覆なら許容する。
- windingはOFF/ONとも元polygonに対し全4面 `-1`。面所属PASSとoriented/culling fidelityを分離。位置は捕捉したがnumeric transport比較NOT_RUN、render/GUI/client NOT_RUN。新epsilon・近似合わせなし。

## 5. 入力だけの診断関数

[diagnose.py](diagnose.py) の `from_nodes(parsed_fbx_root, parsed_meshes_meta)` は既存parserのnodeとparsed metaだけを受け取る。CLIにもUnity観測の引数はない。meta JSONは既存Unity YAML parserで解析したmeshes項目。実呼出し結果は [source-diagnostics.json](source-diagnostics.json)。

| 読み取り条件 | 診断ラベル |
| --- | --- |
| 全polygon triangle、設定が明示・有効 | TRIANGLE_ONLY_CANDIDATE |
| quadあり、keepQuads明示OFF | TRIANGULATION_BOUNDARY_UNVERIFIED |
| triangle/quad混在、keepQuads明示ON | MIXED_TOPOLOGY_REQUIRES_PARTITION_RULE |
| 設定欠落・不正、layer/UID/参照不正、未対応polygon/構造 | UNKNOWN_SCOPE＋理由 |

対象はsole static Mesh／Model connection、sole active Layer0、ByPolygon Material/IndexToDirect、ByPolygonVertex UV/IndexToDirect等を検証できる入力。複数layer、quad-only ON、Skin/Animationや未対応構造を黙って対応済みにしない。候補であり `exact=false` / `effective_policy_proven=false`。UV fingerprintの一意性はこの実験の照合条件で、全製品入力に要求しない。meta記載値は外部環境の実効設定証明ではない。hash allowlistなし。

このdirectoryからのsource-only CLI例（OFFならONをOFFに置換）：

```powershell
& "$env:ProgramFiles/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" -B diagnose.py --repo ../../../.. --addon "$env:ProgramFiles/Blender Foundation/Blender 5.2/5.2/scripts/addons_core/io_scene_fbx" --fbx MixedFour.fbx --mesh-meta-json ON.mesh-meta.json
```

独立judgeは入力予測をimportせず、実native topologyとUVから所属を作る。入力だけのCLIをOFF/ON両方で実行し、候補ラベル・EXACT falseを確認した。

## 6. 試験・保全・独立レビュー

| 工程 | 結果 | 限界／履歴 |
| --- | --- | --- |
| 既存結果・新ID重複照合 | PASS | 同じ新規topology課題の既実行結果なし |
| Blender新規生成＋独立actual FBX検査 | PASS | 1回生成exit0、入力hash/4polygon/2UID/active layer確認。Blender再importはNOT_RUN（不要） |
| source候補・被覆・layer binding対照 | PASS（3 tests） | 欠落、重複、偽topology、誤報group/UID、誤layer参照拒否。代替対角線・反転を判定。未実装symbolをREDで確認後GREEN |
| 同FBX OFF/ON normal Unity比較 | PASS | 1起動、両条件capture、exit0。実効設定差keepQuadsのみ |
| 独立native cover/judge | PASS | 予測への反例はtest FAILではない |
| 原本・既存Project保全と通常返却 | PASS | 保護3,041ファイル変更0、予期しない追加0、所有子process/lock不存在、lease/mutex返却 |
| 今回実施試験のFAIL／直接BLOCKED | なし | 判定命題P_UIDのONはFALSIFIED。開発時の欠けたmodule/binding RED、誤った一時repo引数、私的summaryのfield typoは修正し、実機再実行なし |
| 製品自動Material復元、Confirm、Prefab override、render/GUI/client、他producer・大index・未使用/null・Skin等 | NOT_RUN | 今回対象外、guard解除なし |

Unity前実RAM5.0255 GiB、Blender前5.0515 GiB。既存global mutex／atomic lease、実Editor/Blender process、Project lock、shared batch opt-in検査を守った。通常終了後の資源releaseは最大30秒のfresh読取り待機だけを加え、他Editor停止・lock削除なし。終了08:17:19 UTC。今回の初回guard保留は発生しておらず、旧U/D/HのWITHHELD履歴を上書きしていない。購入素材・私的ログ・Scene・SDKは保存しない。

生成／捕捉review **KEEP**、独立judge/source-only reviewはfixture実bytes・active layerの2条件を補って **KEEP**、新結果だけの最終独立reviewも **KEEP**。全て別GPT-6.1 SOL / medium context、read-only。実主担当model/reasoningは取得不能。完了した旧レビューを再実行していない。

## 7. 製品判断を変えた事実と次の最小問い

通常入力からraw polygon種別・active Material参照・明示keepQuadsを読み、UID-only候補から「ONでtriangle/quad混在」を除外する診断ができるようになった。OFFでquadがある入力は三角形化境界未検証、全面triangleは候補に留まる。

今回ONでは**同じMaterialのGUID/fileIDも複数native groupへ繰り返される**。将来の対応表はUID→一つのordinalに潰せず、face/topology/groupとRenderer側参照を保持する一対多の関係が必要。このstaticモデルの観測をPrefab occurrence carrierが既に持つことにしない。

次の製品patchに必要なのは、対象の通常入力scopeと、そのscopeでface/topology→native group→実Renderer参照を既存consumerへ渡せる根拠の特定。今回のdevelopment captureは既存witnessのface partition不足を埋めない。新schema・必須Unity前処理・製品guard解除は提案実装しない。無限の全入力証明や追加matrixへ進まず、今回の識別範囲は完了。全製品完成を主張しない。

## 8. 保存・読戻し

このGitHubに保存したので見てね：[正規repository](https://github.com/UkkyaGuiyo/vapb)。実測source／証拠は [commit c3cc3ab](https://github.com/UkkyaGuiyo/vapb/commit/c3cc3ab14abe9266489ee4505129e2845d65c621)、[固定結果directory](https://github.com/UkkyaGuiyo/vapb/tree/c3cc3ab14abe9266489ee4505129e2845d65c621/tests/evidence/holmes-material-correspondence-20261011/topology-boundary)。通常push後、GitHub branch SHAと主要source・FBX・固定予測・OFF/ON・judge・summaryのblobを読戻し、一致確認済み。本REPORTは同じ実行branchへの後続文書commitで保存し、最終commitと本文読戻し結果は完了応答で明記する。

指示発行commit94c1f11と実行source/証拠commit c3cc3abは別物。指示branch・旧実測・原本・main/dev・Releaseは変更しない。Atlasへの書込み/pushは既存の親制約に従い行わない。匿名化知見候補：mixed topology＋Keep Quadsでは同じMaterial identityが複数native groupに現れ得るので、index数やMaterial数だけでface topology／一対一対応を推測しない（このUnity版・自作例の実測）。
