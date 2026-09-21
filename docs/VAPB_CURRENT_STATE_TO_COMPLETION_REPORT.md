# VAPB 現在地点から最終目的までの完了工程

この文書は、会話履歴を読まなくても VAPB の目的、現在の実装状態、観測事実、未確定事項、次の一手を理解できるようにした公開安全な handoff 文書である。

作成時点の調査対象ブランチは `feature/multi-package-identity`。この文書の作成では production code、schema、runtime behavior、Unity/Blender の実データを変更していない。

## 1. 最終目的

VAPB の最終目的は、次の往復を identity-safe、fail-closed、検証可能な形で成立させることである。

```text
one or more UnityPackage files
    -> semantic analysis and dependency closure
    -> Blender realization
    -> Blender editing / merge
    -> self-contained UnityPackage
    -> Unity public-API reimport observation
    -> deterministic identity rebind and state restore
    -> validated final Unity / VRChat avatar state
```

ここでいう「完成」は、見た目が Blender で表示できることだけではない。Unity の source identity、Prefab occurrence、Renderer、Material slot、Texture、Bone、Shape Key、Component、依存関係を、編集前後で追跡できることが必要である。Unity や VRChat の挙動をオフラインで推測して完成扱いにしない。

## 2. 調査時点のリポジトリ状態

### OBSERVED FACT

- Branch: `feature/multi-package-identity`
- HEAD at the previous handoff: `aa4cd4a2ab585fefe68ce7830c4b937b818f1a46`.
- `origin/feature/multi-package-identity` は同じ HEAD を指している。
- 作業ツリーには、今回以前からの未コミット変更がある。Importer、Prefab parser、Material builder、provenance bridge、export 関連の追加ファイルなどが含まれる。
- したがって、未コミットの exporter/provenance 実装は「現行HEADの完成機能」ではなく、検証前の作業ツリー状態として扱う。
- 今回追加するのは本 handoff 文書だけであり、既存の dirty file は commit 対象にしない。

### DECISION

未コミット変更を reset、checkout、stash で消去しない。今回の commit は `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md` のみを対象にする。

## 3. VAPB の現在 architecture と不変条件

### 現在の pipeline

```text
UnityPackage
  -> Package Reader
  -> Asset Index
  -> Dependency Resolver
  -> Semantic / Identity Layer
  -> Blender FBX / hierarchy / material realization
  -> Blender scene editing
  -> Bridge planning / staging
  -> UnityPackage or Unity project
  -> Unity Finalizer
  -> Final Prefab / VRChat validation
```

### 現在の invariants

1. **名前は identity ではない。** Blender object name、Prefab name、Material name は表示・診断用であり、解決キーに使わない。
2. **fileID 単独は identity ではない。** 宣言元 asset の GUID または scoped path と組み合わせる。
3. **occurrence と resource を分ける。** 同じ source Renderer declaration が複数の Prefab occurrence で使われる場合、各 occurrence を別記録にする。
4. **source identity と Blender realization identity を分ける。** Blender で生成された object/material slot が source component と一対一とは限らない。
5. **export identity と Unity post-import identity を分ける。** Blender が出した FBX の bytes や object names から、Unity が生成する model subasset localID を推測しない。
6. **ambiguity は自動採用しない。** 0件は `UNRESOLVED`、複数候補は `AMBIGUOUS` として停止または明示選択へ送る。
7. **unknown state は削除しない。** 未対応 Component や serialized state は preserve、unsupported、または explicit error として記録する。
8. **Unity/VRC の観測は public API のみ。** Unity Editor の documented public API による observation を正本とし、内部実装の逆解析や decompilation は行わない。
9. **出力は self-contained を証明する。** 外部絶対パス、未収録依存、曖昧な provider、未検証 sidecar を黙って残さない。

## 4. 実装済み・部分実装・未証明

| 領域 | 現在状態 | 境界 |
|---|---|---|
| UnityPackage reader / pathname / GUID index | IMPLEMENTED | tar.gz 読み取りと選択的抽出。全形式の互換性は別途検証が必要 |
| Prefab / Material / Texture source parsing | PARTIAL | Unity YAML の有用部分と明示参照を扱う。全 Component の意味保存ではない |
| package-scoped identity / collision | PARTIAL to STRONGLY SUPPORTED | scoped registry と collision report はある。全 occurrence closure は未完了 |
| sibling / transitive visual discovery | IMPLEMENTED for covered synthetic policies | 完全性判定と境界は fixture で検証。任意 package の完全性は未保証 |
| ambiguity-safe grouped import | IMPLEMENTED for covered paths | ambiguous provider の自動採用はしない |
| Blender FBX import | IMPLEMENTED | Blender native importer を使用。Unity post-import localID の保持は保証しない |
| hierarchy / material / texture realization | PARTIAL | supported geometry/material path はあるが occurrence receipt が未閉鎖 |
| PhysBone source capture / preview | PARTIAL | source snapshot と限定 preview。VRChat runtime parity / restore ではない |
| progress / foreground import UX | IMPLEMENTED for covered path | real UI surface と arbitrary environment は別検証対象 |
| bridge exporter | PARTIAL | FBX と material map sidecar の既存境界。UnityPackage repack ではない |
| deterministic UnityPackage writer | UNPROVEN / NOT RELEASED | 作業ツリーに prototype modules はあるが、実 Unity round-trip 未証明 |
| Unity Finalizer | PARTIAL | 既存 material restore path はある。generated model identity と Final Prefab は未完了 |
| MRUS state snapshot / restore | PLANNED | capture / rebind / restore / validation の契約が未実装 |
| complete Unity / VRChat parity | NOT A CURRENT CLAIM | shader exactness、third-party component、Animator/Expressions/Contacts の全面 parity は未証明 |

## 5. 最新 selected-avatar 調査の要点

以下は同一 run の selected-root と package-wide Effective graph を分けて読んだ結果である。実 asset の GUID、fileID、絶対 path は公開文書へ記録しない。

### OBSERVED FACT

- Unity の selected completed avatar root の母集団: **26 Renderer occurrences / 41 Material slots**。
- 同じ selected-root scope の VAPB Effective graph: **4 Renderer occurrences / 5 slots**。
- 差分: **22 Renderer occurrences が Effective graph に未到達**。
- raw FBX graph join: **26/26 exact**。raw FBX 側の source graph 不足ではない。
- Material の比較可能な行: **7**。
- 比較可能な valid Material mismatch: **0**。
- Material slot count mismatch: **2**。これは未到達 Renderer に属する slot の影響を含み、Material parser の値 mismatch と同一視しない。
- package-wide Effective graph: **257 Renderer occurrences / 394 non-null material slots / 14 prefab roots**。
- package-wide の数字を selected avatar root の数字として扱ってはならない。

### DERIVED

- 4 exact rows が正しいことと、selected root 全体が完成していることは別である。
- raw FBX join が 26/26 exact なのに Effective が 4 なので、主因は raw FBX 読み取りより上流の Effective semantic enumeration、Prefab inheritance/Variant 展開、root/occurrence attribution のどこかにある。
- 22件を閉じない限り、selected-root の semantic freeze、全 slot の receipt、Finalizer の全体 rebind を完了扱いにできない。

### HYPOTHESIS（未確定）

- 最有力は Variant / inherited renderer の occurrence expansion 漏れ。
- wrong-root attribution、Prefab chain attribution、identity collision もまだ排除しない。
- 22件の実体を確定する次の調査は、source renderer localID の offline reverse lookup と、Effective root/source kind/occurrence path/Prefab chain/omission reason の行列化である。

## 6. LUNA / SOL / Astra の調査結果

### LUNA の統合判断

- 22件は selected-root semantic completeness の一次 blocker。
- 26/26 raw FBX join と valid Material mismatch 0 から、先に Material shader を一括修正する根拠はない。
- package-wide 257件を selected avatar として export してはならない。
- 4件だけで完成 schema を固定するのも危険。限定 vertical slice には使えるが、全体完成の根拠にはしない。
- 次の作業は occurrence provenance 行列の確定と、無変更 round-trip baseline の準備である。

### SOL review の要点

- 現在判定は `HOLD`。順序修正が必要。
- 22件は semantic freeze の primary blockerだが、4 exact occurrence を使った限定 vertical slice まで禁止する blocker ではない。
- semantic freeze は一枚岩にせず、まず最小 semantic contract v0 を定義し、無変更 package round-trip と Unity reimport measurement を通した後に freeze する。
- 編集前に「無変更 preserve/repack -> fresh Unity reimport -> semantic diff」を通すことが必須。
- MRUS の完全 restore は後段でよいが、実 Unity import 前に capture/restore の安全契約だけは定義する。

### Astra independent review の要点

- occurrence/provenance -> semantic freeze -> Blender receipt -> minimal edit delta -> round-trip -> reimport identity -> Finalizer が主経路。
- 22件は source graph 不足ではなく、Effective 側の identity/inheritance/root representation 問題である可能性が高い。
- 22件を閉じないまま exporter schema や receipt を固定すると、欠落を正しい仕様として永続化する危険がある。
- no-op round-trip、fresh import、dependency closure、意図しない semantic diff を stop condition にする。

### Agreement / disagreement

**Agreement**

- 22件の selected-root occurrence 欠落が一次 blocker。
- raw FBX 26/26 exact と Material mismatch 0 を根拠に、別系統の一括 material 修正を急がない。
- 未コミット exporter modules は verified product capability ではない。
- names、単独 fileID、sidecar だけで generated model identity を代替しない。
- exact model-backed round-trip には Unity post-import observation または Finalizer が必要。

**Difference**

- LUNA の初期案は semantic freeze 後に exporter vertical slice を置く順序だった。
- SOL は、より安全な設計として「最小 semantic contract v0」の直後に無変更 preserve/repack と reimport baseline を前倒しするよう修正した。
- 採用判断は SOL 案。実際の Unity reimport drift を先に測ることで、semantic gap と exporter gap を混同しないためである。

## 7. 採用・棄却した仮説

### 採用した仮説

1. `OCCURRENCE_IDENTITY / PROVENANCE` が現時点の最優先問題である。
2. 22件の第一候補は Variant/inheritance 展開または root attribution の欠落である。
3. exporter は raw-preserve + typed patch + explicit Unity observation の hybrid が安全である。
4. Unity の generated model identity は offline で決めず、post-import observation に委ねる。

### 現時点で棄却した仮説

1. 22件の主因を「raw FBX が壊れている」とする仮説。26/26 exact join と矛盾する。
2. valid Material mismatch を主因とする仮説。比較可能範囲で mismatch 0。
3. package-wide Effective 257件が selected avatar root の正しい母集団だとする仮説。
4. object / material name の fuzzy match で occurrence identity を復元できるとする仮説。
5. Blender FBX export bytes から Unity model subasset localID を再現できるとする仮説。

## 8. 最終完了までの critical path

下表の `CRITICAL PATH` は、後工程の正しさを直接左右する工程を示す。

| Stage | 分類 | 目的 / なぜ必要か | 現在 | 不足 | 依存 | 実装・検証 | Human / Unity / Blender gate | DONE / stop condition |
|---|---|---|---|---|---|---|---|---|
| 0. Occurrence provenance closure | CRITICAL PATH | 26 occurrences を occurrence-aware に説明し、4/22差分を分類する | 4 exact、22 missing | source-localID reverse lookup、root/Variant/occurrence path、omission reason | 既存 parser / Effective graph | production変更前に診断行列を作る | Unity再実行は offline で足りない事実だけ Human Gate | 26/26 が EXACT、明示的 AMBIGUOUS、または理由付き MISSING。silent omission 0 |
| 1. Semantic contract v0 | CRITICAL PATH | source / occurrence / realization / unknown を固定する | identity基礎はある | occurrence schema、version、status vocabulary、slot scope | Stage 0 | synthetic repeated occurrence / inheritance fixture | Unity public observationで selected scope を照合 | 1 occurrence = 1 stable record、名前解決 0 |
| 2. No-op preserve/repack baseline | CRITICAL PATH | 編集差分なしで package writer と Unity import の問題を分離する | writer は未検証 prototype | self-contained staging、meta/GUID/path/dependency closure | Stage 1 | typed reachability、deterministic staging/writer、no-op manifest | Unity import は隔離 project で Human Gate | fresh project に self-contained import、欠落依存 0 |
| 3. Unity reimport identity measurement | CRITICAL PATH | generated / preserved asset の post-import identity drift を実測する | source observation はある | exact output hash、GUID/localID、Renderer/slot semantic diff | Stage 2 | Unity public APIで post-import sidecar を出す | `AssetDatabase`、`TryGetGUIDAndLocalFileIdentifier`、`GlobalObjectId` を使用 | identity drift が保持/remap/unsupported に分類される |
| 4. Blender realization receipt closure | CRITICAL PATH | Unity occurrence -> Blender object/slot -> export record を逆追跡する | Blender identityはpartial | receipt、mesh/material/texture mapping、unsupported preservation | Stage 1/3 | Blender 5.2.1 integration、save/reload、receipt validation | Blender real scene gate | 対象 occurrence の receipt coverage 100%、ambiguous は停止 |
| 5. Minimal edit-delta vertical slice | CRITICAL PATH | 最小編集1件で exporter の意味を検証する | design only | typed delta grammar、before/after hash、non-target invariants | Stage 2/3/4 | 1 avatar、1 prefab、1 model、1 material/texture edit | Blender実機で編集、Unityでは未変更 baselineと比較 | 宣言差分以外の semantic diff 0 |
| 6. Edited self-contained UnityPackage | CRITICAL PATH | 実際に配布可能な output を作る | package repack 未実装 | raw preserve、typed patch、collision/path checks、deterministic tar.gz | Stage 5 | package writer、manifest、testzip、external path scan | Unity isolated import | output が自己完結し、未収録依存 0 |
| 7. Minimal Unity Finalizer | CRITICAL PATH | offlineで決まらない generated identity を public API で再結合する | material restore はpartial | idempotent rebind、dry-run、validation report | Stage 3/6 | selected supported component のみ実装 | Unity Editor public APIs only | rerunで同じ結果、AMBIGUOUS/MISSING は fail closed |
| 8. MRUS capture / restore | CRITICAL PATH | Unity/VRC component state を失わずに戻す | planned | state snapshot、component refs、restore policy、validation | Stage 7 | Avatar/Animator/Expressions/PhysBone 等を supported/unsupported 分類 | Unity + available VRC public SDK observation | restored/rebound/partial/missing/unsupported を全件報告 |
| 9. Multi-package full closure | REQUIRED BUT PARALLELIZABLE | 複数 package の provider/namespace/collision を広げる | synthetic covered、real broad proof partial | export-side multi-package reachabilityとmerge | Stage 1/6後 | package-scoped graph、provider ambiguity、group export | real packageはHuman Gate | cross-package identityとself-contained outputが再現可能 |
| 10. Release UX / distribution | LATER | installable addon、progress、reports、ZIPを整える | importer distribution pathはある | exporter UX、release E2E、docs | Stage 6/7/8 | extracted ZIP register/unregister、public hygiene | Human visual retest | exact HEAD ZIP、testzip None、register/unregister PASS |
| 11. Shader / third-party / full VRChat parity | OPTIONAL / OUTSIDE CORE | 近似でなく完全再現を目指す場合のみ | not claimed | per-shader/per-SDK contracts | Stage 8 | feature-specific acceptance | SDK-specific Human Gate | support matrixが明示されるまで自動完成扱いしない |

## 9. Importer Semantic Freeze Gate

semantic freeze は「コードを二度と変えない」という意味ではなく、以後の exporter が依存する semantic contract を固定する gate である。

### 必須条件

- selected root scope と package-wide scope が明示的に分離されている。
- 26 occurrences と 41 slots が occurrence-aware に列挙される。
- 22件は unresolved のままでもよいが、理由・種類・次の観測が明示されている。silent omission は不可。
- source asset、source component、occurrence、Blender realization、material slot、texture role の identity schema が versioned である。
- exact / ambiguous / missing / unsupported の status が保存される。
- cross-package provider 解決と selected-avatar の single-package path を同じ母集団として混ぜない。

### Gate fail

occurrence の重複、wrong root、name-only resolution、package-wide混入、unknown state の削除があれば freeze を止める。

## 10. Export Prototype Gate

最初の export は「最終 exporter」ではなく、以下の minimum round-trip vertical slice とする。

### Minimum Round-trip Vertical Slice

1. synthetic または承認済み test fixture の単一 package。
2. 1 Prefab、1 model asset、1 Armature/mesh、1 Material、1 Texture。
3. Blender で宣言済みの編集を1件だけ行う。
4. unchanged assets は raw preserve。
5. changed asset は typed patch または明示 `CREATE/MODIFY`。
6. deterministic manifest と UnityPackage staging を生成。
7. Unity 2022.3 の隔離 project へ public API / 通常 import で取り込む。
8. post-import GUID/localID/Renderer/Material slot を capture。
9. expected delta と unexpected diff を分離する。

### Prototype gate fail

generated FBX の localID を推測する、未収録依存を暗黙に許す、meta/GUIDを省く、source packageを破壊する、または Unity reimport の結果を取らずに PASS とする場合は失敗。

## 11. Unity Reimport Gate

Unity の公式公開 API は asset GUID/path/local file identifier、Prefab source、GlobalObjectId、Renderer/Material 等の観測に使う。UnityPackage は `.unitypackage` 圧縮 asset package として import/export されるため、UnityPackage の bytes と post-import state を別レイヤーで記録する。

### Gate output

- output package hash と import observation id
- preserved asset の GUID/path/metadata
- generated model の post-import asset/subasset identity
- Renderer occurrence、mesh、material slot、texture reference の diff
- missing dependency、ambiguous candidate、unsupported component
- Finalizer を実行した場合の idempotence と validation result

### Stop

fresh project import が自己完結しない、unintended semantic diff がある、または generated identity が未観測なら Finalizer/round-trip を完成扱いにしない。

## 12. Finalizer Gate

Finalizer は「不足を推測で埋める処理」ではない。Unity が import した結果を public API で観測し、manifest の typed rebind task を deterministic に適用する境界である。

### 必須性

- preserved source assets の no-op round-tripだけなら、Finalizerなしで成立する場合がある。
- generated model/FBX の exact identity rebind、Prefab reference survival、Unity SDK object rebind が offlineで証明できない場合は、Finalizerまたは Unity semantic sidecar が必要。
- Finalizerは idempotent、dry-run可能、AMBIGUOUS/MISSINGで停止、raw private APIなしとする。

## 13. MRUS Gate

MRUS は Blender が Unity を完全再現する機能ではなく、Unity/VRC state を可能な範囲で capture -> rebind -> restore する契約である。

### 先に定義する state

- Avatar root / source Prefab chain
- Renderer / Material / Texture references
- Bone / Shape Key / animation path
- Animator / Expression / Avatar Descriptor
- PhysBone / Collider / Contacts
- third-party MonoBehaviour / script GUID / serialized references

各 state は `RESTORED`、`REBOUND`、`PARTIAL`、`MISSING_TARGET`、`MISSING_DEPENDENCY`、`AMBIGUOUS`、`UNSUPPORTED`、`ERROR` のいずれかで終える。未対応を成功扱いにしない。

## 14. 今やらなくてよいこと

- 22 occurrence が閉じる前の全体 exporter の拡張。
- package-wide 257件を対象にした export 完成主張。
- object name / Material name による fuzzy fallback。
- generated FBX の Unity localID の offline 推測。
- 全 shader family の完全 parity。
- 全 third-party component の YAML 再実装。
- MRUS 全項目の一括 restore。
- UnityPackage Export の release ZIP、tag、Release、main merge。
- private commercial asset、raw Oracle JSON、GUID/fileID一覧の commit。

## 15. 次に実行すべき Action（1つだけ）

**次の一手は、selected-root の22件について offline provenance matrix を生成すること。**

行キーは name ではなく、source renderer declaration の scoped identity とする。各行に次を持たせる。

```text
source_asset_kind
source_asset_identity
renderer_declaration_identity
expected_occurrence_scope
effective_root_scope
effective_source_kind
occurrence_path_token
prefab_chain_status
raw_fbx_join_status
material_slot_count
omission_reason
classification: EXPANSION_MISSING | WRONG_ROOT | IDENTITY_COLLISION | OTHER
```

この action を先に行う根拠は、raw FBX 26/26 exact、Material mismatch 0、Effective selected-root 4/26 という三つの事実を同じ表で結べるからである。ここで22件が分類できれば semantic contract v0 を確定でき、分類できなければその一点だけを Human Gate または Unity public observationへ持ち込める。次の action を exporter 実装にするのは順序が逆である。

## 16. Web / 公開仕様で重要だった外部仕様

以下は一次資料のみを参照した。URLは将来の再確認用である。

- Unity `AssetDatabase.TryGetGUIDAndLocalFileIdentifier`: GUID と local file ID は serialized asset reference の構成要素であり、Prefab等では64-bit local IDを扱う必要がある。
  https://docs.unity3d.com/ja/2022.3/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html
- Unity `GlobalObjectId`: Prefab、Scene、ScriptableObject等の Unity Object を project-scoped に識別する public Editor API。Prefab instance source と instance の区別を含む。
  https://docs.unity3d.com/ja/2022.3/ScriptReference/GlobalObjectId.html
- Unity Asset Packages: `.unitypackage` は圧縮 asset package で、Assetsへ importされ、metadata と asset links を含む。
  https://docs.unity3d.com/ja/current/Manual/AssetPackages.html
- Unity `PrefabUtility.GetCorrespondingObjectFromSource`: instance object から Prefab source object を public API で取得する境界。
  https://docs.unity3d.com/ja/2021.1/ScriptReference/PrefabUtility.GetCorrespondingObjectFromSource.html
- Blender FBX export API: FBX export settings、custom properties、animation、leaf bones等を明示指定できるが、Unity generated localID の保持を保証する仕様ではない。
  https://docs.blender.org/api/main/bpy.ops.export_scene.html
- VRChat PhysBones: avatar dynamics と collider/state の公式仕様。Blender previewをVRChat runtime parityと同一視しない根拠。
  https://creators.vrchat.com/common-components/physbones/
- VRChat avatar components: PhysBones、Contacts、Constraints等の公式 component 範囲。
  https://creators.vrchat.com/avatars/avatar-components/

## 17. 関連する repository paths

### Architecture / product

- `ARCHITECTURE.md`
- `PRODUCT_SPEC.md`
- `TEST_STRATEGY.md`
- `TEST_RESULTS.md`
- `docs/PACKAGE_COMPOSITION.md`

### Current identity / importer

- `unity/package_reader.py`
- `unity/asset_database.py`
- `unity/prefab_parser.py`
- `unity/effective_prefab.py`
- `unity/provenance_model.py`
- `unity/prefab_candidate_analyzer.py`
- `unity/material_parser.py`
- `unity/material_mapping.py`
- `blender/fbx_importer.py`
- `blender/fbx_receipt.py`
- `blender/provenance_bridge.py`
- `blender/hierarchy_builder.py`
- `blender/material_builder.py`
- `blender/identity_registry.py`

### Export design and prototype boundary

- `docs/EXPORT_ARCHITECTURE_DECISION.md`
- `docs/EXPORT_IDENTITY_MODEL.md`
- `docs/EXPORT_RESEARCH_CORRECTIONS.md`
- `docs/EXPORT_UNKNOWN_MATRIX.md`
- `export/semantic_graph.py`
- `export/asset_plan.py`
- `export/manifest.py`
- `export/staging.py`
- `export/package_writer.py`
- `export/fbx_export.py`
- `export/material_export.py`
- `export/texture_export.py`
- `export/raw_assets.py`

### Relevant tests

- `tests/test_package_reader.py`
- `tests/test_prefab_parser.py`
- `tests/test_prefab_candidate_analyzer.py`
- `tests/test_multi_package_identity.py`
- `tests/test_renderer_provenance_bridge.py`
- `tests/test_fbx_receipt.py`
- `tests/test_export_semantics.py`
- `tests/test_export_materialization.py`
- `tests/blender_cross_package_dependency_test.py`
- `tests/blender_multi_package_identity_test.py`
- `tests/blender_multi_package_visual_test.py`
- `tests/blender_real_identity_verify.py`

## 18. 検証結果と限界

### 今回実行した検証

- repository branch / HEAD / remote / dirty state: 確認済み。
- targeted `pytest`: 実行環境に pytest module がなく起動不能。これは production failure ではなく test runner availability failure。
- `python -m compileall -q export blender unity`: PASS。
- repository parent からの unittest discovery: **228 tests PASS**。
- remote branch HEAD: local HEADと一致。
- Unity/Blenderの実機再実行、real package import、exported package reimport: 今回は実施していない。

### 未検証事項

- uncommitted exporter/provenance modules の production integration。
- generated FBXを含む self-contained UnityPackage の Unity 2022.3 fresh import。
- edit delta後の semantic diff と Finalizer idempotence。
- MRUS state restore。
- real cross-package visual resultと、selected-avatarの22 occurrence分類の最終確定。

## 19. Handoff summary

### なぜ今この作業をしているのか

VAPBは単なる extractor/importerではなく、Blender編集を経た Unity/VRC state の安全な往復を目指している。そのため、見た目の import 成功より先に、source occurrence と Blender realization と Unity post-import identity の分離を確定する必要がある。

### 何が観測事実で、何が仮説か

- **OBSERVED FACT:** Unity selected root 26/41、Effective selected root 4/5、22 missing、raw FBX 26/26 exact、valid Material mismatch 0。
- **DERIVED:** primary blocker は occurrence/provenance closure。
- **HYPOTHESIS:** Variant/inheritance expansion または wrong-root attribution が22件の主因。
- **UNKNOWN:** generated FBX subasset identity、任意 packageの完全な reimport survival、全面的な VRC component restore。

### 次に何をすればよいのか

selected-root 22件の offline provenance matrix を一度作り、26 occurrences がどこで失われるかを分類する。その結果を semantic contract v0 と no-op preserve/repack baselineへ接続する。

## 20. Public-safety declaration

この文書は aggregate / sanitized な研究結果だけを含む。commercial UnityPackage本体、FBX、Texture、Material、Prefab YAML、raw Unity Oracle JSON、実 asset のGUID/fileID一覧、不要な private absolute path、スクリーンショットは含めていない。

## 21. Stage 0 provenance closure addendum (latest)

### OBSERVED FACT

The previously open 22-row selected-root gap is now classified using a private local provenance matrix. The 26 selected Unity Renderer occurrences divide into **4 EXACT_EFFECTIVE_OCCURRENCE** and **22 SELECTED_ROOT_REPRESENTATION_GAP**. All 22 have one or more package-wide Effective candidates under other roots; package-wide absence is 0 and selected-root ambiguity is 0. Other-root candidate multiplicity is 1 row with one candidate, 3 rows with two, and 18 rows with three.

The raw FBX graph remains 26/26 exact and comparable valid Material mismatch remains 0. The 22-row result is therefore not evidence of raw FBX graph loss or a Material value mismatch.

### DERIVED

The first observed missing stage is selected-root Effective assignment / occurrence projection. The current VAPB graph can emit the same model-source identities under other root evaluations, but does not yet prove the selected Unity instance's complete occurrence scope. This is a representation diagnosis, not proof of an incorrect Unity parent.

### UNKNOWN / STOP CONDITION

The current snapshot does not capture complete Unity Variant ancestry or a per-function runtime trace. The deeper distinction between model-child expansion loss, root attribution loss, and Variant/inheritance projection loss remains open. Production changes must wait for an occurrence-aware public Unity source/instance-chain observation.

### CURRENT NEXT ACTION

The next action is one public-API Unity observation of the selected root that records Prefab source/instance chain for all 26 Renderer occurrences. The standalone public-safe closure is documented in `docs/CASE_A.md`.

## 22. Stage 0.5 Unity source-chain observation (latest)

### OBSERVED FACT

The selected-root public-API observation completed with **26 Renderer occurrences / 41 Material slots**, immediate source resolved **26/26**, original source resolved **26/26**, and FBX model asset resolved **26/26**. Every row was a Connected Prefab instance with `PrefabAssetType.Variant` and a three-level observed chain: Scene Renderer -> selected Prefab source -> original FBX Renderer. Console errors were 0.

### DERIVED

The 4 exact and 22 gap rows share the same Unity chain. Therefore the loss boundary is proven after Unity source/original/model resolution and at VAPB selected-root Effective occurrence projection. Sol review classifies the 22 rows most strongly as `VAPB_ROOT_ATTRIBUTION_GAP` with medium confidence: they are emitted under other package-wide roots but not the selected root. Model-child expansion and Variant projection remain possible mechanisms, not isolated causes.

### DECISION

The final classification for all 22 is `VAPB_ROOT_ATTRIBUTION_GAP` (medium confidence), with mechanism assessment `SELECTED_ROOT_ATTRIBUTION_MISMATCH_MODEL_CHILD_AND_VARIANT_MECHANISM_UNRESOLVED`. Semantic Contract v0 design may proceed; full selected-root semantic freeze remains HOLD. Details are in `docs/CASE_A.md`.
+## 23. Stage 1A synthetic occurrence projection isolation (latest)

### OBSERVED / PROVEN

Stage 1A added only public synthetic fixtures. At the current `EffectivePrefabResolver` boundary:

- A Prefab that explicitly references a synthetic model with three source Renderer records, but has no Renderer material override, produces 0 Effective Renderers.
- Addressing one source Renderer by override produces 1 Effective Renderer; addressing all three produces 3.
- A serialized base Prefab containing three Renderer components remains 3 through the tested Variant and nested no-extra-override chain.
- Changing between the two tested non-empty synthetic Material GUIDs on the same override does not change the fixture's Renderer occurrence count.
- `OccurrenceKey` distinguishes the same source Renderer under different synthetic root/instance paths, but `EffectivePrefabResolver.resolve()` has no selected-root or instance-edge context parameter.
- Full Python unittest discovery: **233 tests PASS**.
- Relevant Stage 1A/parser/provenance tests: **26 tests PASS**.
- `python -m compileall -q blender unity operators ui export tests`: **PASS**.

The synthetic test and public-safe interpretation are stored in
`tests/test_stage1a_synthetic_projection.py` and
`docs/CASE_A.md`.

### DERIVED

- The result is reproducible as a general occurrence-projection limitation, not a CASE_A hack or rule.
- A source Renderer identity alone does not represent a selected-root occurrence; root context and instance-edge path are separate semantic data.
- An Effective semantic contract needs root context, instance path, source Renderer identity, owner/mesh identity, and ambiguity status.
- The synthetic run narrows the code boundary but does not prove that one mechanism alone explains the private real-asset gap.

### UNKNOWN

- Whether the final production correction belongs directly in `EffectivePrefabResolver`.
- Whether an occurrence projection layer should be introduced separately.
- Where model-child expansion and selected-root context should be integrated.
- Whether the observed variant identity-scope risk is present in every real Unity serialization shape.

### DECISION

- **Production behavior fix: HOLD.** No production logic was changed in Stage 1A.
- **Semantic Contract v0 design: proceed.** Define the contract from the synthetic fixture and the Stage 0/0.5 evidence before implementation.
- **Full semantic freeze: HOLD.** The selected-root projection mechanism is not yet fully proven.

### NEXT ACTION

Define Semantic Contract v0 with a synthetic occurrence-projection adapter test that emits all model-child Renderers under two selected-root/instance-edge contexts, preserving shared source identity while producing distinct occurrence keys. Do not implement the production correction until that contract boundary is reviewed.
