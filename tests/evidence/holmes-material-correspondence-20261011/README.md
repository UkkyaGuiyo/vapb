# HOLMES 最小実測：R / A / B

自作 ThreeSlotSource の12面を使い、Unityのsubmesh順とBlenderのMaterial slot順が異なることを実測した。製品コードは変更していない。既存の面対応未確定ガードは保持する。

R/A/Bの実行sourceと記録は保存commit `c76d3bd8380247b75ff4c0b5716c3cad97613ec6` の当該pathに固定される。後続Eのcase選択追加をR/A/Bで再実行したという主張はしない。過去の実行hash・記録は変更していない。

## 後続E：実機観測済み

Aと同じ初出順1,0,2・UID別2/4/6面を固定し、record順を `1,0,2,1,2,0,2,1,2,1,2,2` とした。Aの3連続runに対しEは11run。書込後FBXの独立判定で全12面の意味と宣言外tree不変を確認し、生成・判定の別SOL mediumレビューKEEP後に実測した。

Unity 2022.3.22f1では3submeshのUID群順1,0,2。保存済みAとEのnative snapshotを12個の一意なexact UV面・cornerで直接joinし、全12面の所属submeshが一致した。11runを別々のsubmeshにする単純な規則にはこの例が反例となる。H1はR/A/B/Eの範囲で支持されるが、H7の他producer・未使用/重複slot、H6の設定依存は未確定である。

Blender 5.2.1 LTSではslot UID群順0,1,2、ConfirmはCANCELLEDで全snapshot不変。Unity・Blenderともexit0、保護3,041ファイルの差分0・予期しない追加0、所有lease/mutex返却。製品guardは維持し、通常ImportへUnity前処理や仮説を追加していない。

実行sourceはcommit `5f5de6d187fd9a7435d0962bc698211128d137c2`。`observations/E-source-summary.json`は実行前のraw-only状態をそのまま保持し、実機結果は `E-run-summary.json` / `E-full-judgment.json` / `E-context.json` / `E-coordinate.json` / `E-blender.json` に記録した。FBX/packageと生成hashは既存 `cases/E.*` / `generation-E.json`。原本・過去R/A/B記録は変更しない。

基準製品source: `79a28a92328dded08e8004ee014f9af3d34946e2`。Unity 2022.3.22f1、Blender 5.2.1 LTS。生成と独立判定は別の GPT-6.1 SOL / medium コンテキストで実行前レビューし、KEEP。判定レビューで指摘された実効import policy比較漏れを修正後、再確認した。

## 条件と結果

下記の0/1/2は基準FBXのMaterial connection位置を表す。名前からの同定ではない。

| 基準位置 | FBX Material UID | 面数 |
| --- | --- | --- |
| 0 | 943593828 | 2 |
| 1 | 504963197 | 4 |
| 2 | 123443898 | 6 |

| case | 単独変更 | 面のMaterial初出順 | Material接続順 | Unity submeshのMaterial UID群順 | Blender slotのMaterial UID群順 |
| --- | --- | --- | --- | --- | --- |
| R | 公式parser/writerのno-opコピー | 2,1,0 | 0,1,2 | 2,1,0 | 0,1,2 |
| A | 全面recordを1,0,2の群順へ並べ替え | 1,0,2 | 0,1,2 | 1,0,2 | 0,1,2 |
| B | 接続を2,0,1へ並べ替え、indexを同じUIDへ再対応 | 2,1,0 | 2,0,1 | 2,1,0 | 2,0,1 |

Rの各UV面→Unity submeshは、原本FBXの既存current-context実測と一致した。Aでは面数・Material名前・connection順を固定してnative順だけが変わった。Bではconnection順を変えてもnative順は元のままで、Blender slotだけが変わった。各native submeshは一つのMaterial UIDの面だけを含んだ。混在UIDを代表UIDへ置き換える処理はない。

## 仮説の判定範囲

| 仮説 | 今回の判定 | 根拠／限界 |
| --- | --- | --- |
| H1 面recordで最初に現れるMaterial順 | このR/A/B/Eの範囲で支持 | Aの順変更、Bの接続変更への不変性。一般規則のVERIFIEDではない |
| H2 Material→Model接続順そのもの | 普遍的な順決定則として反証 | AとBのnative結果が予測と異なる |
| H3 raw Material indexの昇順 | 普遍的な順決定則として反証 | Bのindexは接続の位置を参照する。H2と同じ予測になる範囲は区別できない |
| H4 固定Material名の順だけ | 反証 | Aで名前を変えずnative順が変わる。任意の名前との条件分岐は未判定 |
| H5 面数の順だけ | 反証 | Aで各UIDの2/4/6面を固定したまま順が変わる。他属性を使う則は未判定 |
| H6 import設定による切替 | UNDETERMINED | 今回は同じ実効設定のみ。設定変更実験は未実施 |
| H7 producer・空slot・非連続run等による則切替 | UNDETERMINED | 同じ自作FBXの3例のみ。非連続Material run、未使用/空/null/重複slot、他producerは未実測 |

H1を一般化して普通の入力へ適用する根拠は不足している。今回の結果を名前・候補数・ordinalの推測として製品へ挿入しない。次の最小反証は、面の初出順・UID別面数を固定したままMaterial runを非連続にする一例である。

## 書き出し後の独立検査

生成は原本package/FBX/metaのSHAを固定し、公式FBX binary encoderと既存property変換を使う。writerのFileId/CreationTime以外の全treeは、意図したtreeと再parseした実ファイルで比較する。AはPolygonVertexIndex・UVIndex・NormalsIndex・Materialsを整合して並べ替え、Edgesのpolygon-loopアドレスを逆置換する。Bは実際のUID接続からindexを再計算する。

独立judgeはgeneratorのdecodeや仮説予測をimportしない。実FBXのObjects/Connections/LayerElementMaterialから面UIDを導き、許可した変更箇所以外のtree一致、および各UV面のoriented CP・座標・UV・normal・Material UID・edge endpoint保持を検査した。元packageから各派生packageへ変わったmemberは当該FBX assetだけ。meta、Prefab、Materialは同一bytes。

raw / Blender / Unity は12個の重複のない厳密UV三角形signatureと一意corner permutationで対応付けた。面の多重度も検査した。対照はduplicate face、missing face、duplicate cornerを拒否し、winding反転を観測し、target slot置換で観測groupだけが変わることを確認した。

raw→Blenderのorientationは全12面+1、raw→Unityは全12面-1。raw→Blender local位置の最大差は0。宣言済み `0.01 * reflectX` によるraw→Unity最大差は `6.332993504609696e-10`。これらは面所属と分離した観測であり、新しいepsilonや数値PASS基準にはしていない。

## native / GUID / Material参照

各caseは同じ所有Projectの使い捨て作業pathへコピーして同期再importした。実FBX/meta hash、Unity version、実効ModelImporter policy、scale/axis、Mesh GUID/signed fileID、Prefab RendererとMaterial参照を毎回捕捉した。policyと固定受信側は基準current-contextと比較した。source `Mesh.GetTriangles` は再利用したMeshData捕捉と一致した。

- Mesh GUID: `abcdefabcdefabcdefabcdefabcdefab`
- Mesh signed fileID: `3538053534738119282`
- Prefab GUID: `7cbdcbe81fde386408bcfb379e62b6bb`
- Renderer signed fileID: `3728717051629469441`
- 固定Prefab Material refs: slot0 `eb805efb35118044db5e74adc652673a / 2100000`、slot1 `0318f358e4c29034aa90cc8c50b58a93 / 2100000`、slot2 `64f92a1bd9b35a040bf9e2c6d200b34c / 2100000`

Prefab Material arrayは受信側の独立対照として固定した。Aでnative partitionが変わるため、Prefabの見た目を原本通りに保持したという主張はしない。FBX Material UIDとUnity Material GUID/fileIDを名前や番号だけで同一視しない。観測した面→native submesh→固定Prefab refという経路だけがこの資料の証拠範囲である。

Blenderは各派生packageを現行製品のRECONSTRUCT Importへ通した。source GUID/fileIDと実hashを持つ一意receiptでmeshを選び、全UV/normal loop・slot・receiptを保存した。ConfirmはR/A/BすべてCANCELLED、全UV/normalを含む前後snapshot同一。通常ImportにUnity事前処理を追加していない。

UnityとBlenderは別々にglobal mutexと実RAMを確認して実行し、exit code 0。既存Projectの保護対象3,041ファイルは変更0・予期しない追加0、owned子process/Project lockは残らず、slot/mutexを通常返却した。私的process記録・生ログ・購入素材は公開証拠に含めていない。

## 証拠と再照合

- `cases/`: 実際に使用した自作FBX/package、原本FBX/meta、生成hash、package member比較。
- `observations/full-judgment.json`: full raw geometry/layers/connections、Material UID群、UV/corner permutations、orientation、numeric観測、実効native context、Blender receipt。
- `observations/*-coordinate.json`: native位置/normal/UV/全submesh indexと入力hash。
- `observations/*-context.json`: 実効import policy・native signed IDs・Prefab/model Material refs。
- `observations/*-blender.json`: 全loopとslot、receipt、Confirm前後・拒否。
- `observations/run-summary.json`: 実行source hash、使用version、RAM、終了/保全/返却結果。

レビュー済み `generate_cases.py` / `judge_faces.py` は既存pinned parser loaderを使う。Blender同梱Pythonにnumpyがあることが必要。判定だけの再実行例（新しいoutputへ排他作成）:

```text
python judge_faces.py --repo <checkout> --addon <installed io_scene_fbx> --cases cases --native observations --blender observations --output <fresh output.json>
```

`CaptureNative.cs` のR/A/B実行版は上記保存commitで確認できる。現行版にはEだけを選択する引数を追加した。`runtime/VapbHolmesCoordinateProbe.cs` はR/A/Bで実際にcompile・実行した自作捕捉sourceで、Eにも同じbytesを使う。probeは既存座標probeを再利用し、出力path引数と複数case呼出しのための終了方式だけ変更した。所有Projectの配置・復元には既存runnerを再利用した。

全製品完成・一般Avatar対応・実購入corpusでの面対応・GUI/client確認・最新ZIP反映は、この資料では主張しない。
