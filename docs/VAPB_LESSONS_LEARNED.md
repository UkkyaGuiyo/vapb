# VAPB Lessons Learned

VAPB開発で得た一般化可能な失敗知識、反証、設計原則を記録する。この文書は
[PRODUCT_SPEC](../PRODUCT_SPEC.md)、[ARCHITECTURE](../ARCHITECTURE.md)、
[CURRENT_STATE](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、CHANGELOGの代替ではない。
現在の実装状況や次の作業ではなく、「以前の考えがどの証拠で狭められたか」を読む。
`REJECTED_IN_SCOPE` は記載した条件での否定であり、全入力での永久的な否定ではない。

| ID | Lesson | Domain |
| --- | --- | --- |
| LESSON-001 | 表示名はidentityではない | IDENTITY |
| LESSON-002 | Source、occurrence、資源を分ける | PREFAB / BLENDER |
| LESSON-003 | Package全体と選択rootは別 | PREFAB |
| LESSON-004 | Generated IDを推測しない | FBX / UNITY |
| LESSON-005 | Unityの答えとPackageの証明は別 | UNITY / PACKAGE |
| LESSON-006 | 直接未一致でもaliasは有効になり得る | PREFAB / MATERIAL |
| LESSON-007 | UNKNOWNの範囲を絞る | SAFETY |
| LESSON-008 | Materialの存在と割当は別 | MATERIAL / BLENDER |
| LESSON-009 | 見た目の症状と原因を分ける | TEXTURE / DEBUGGING |
| LESSON-010 | 安全な停止を利用者へ説明する | UX / SAFETY |
| LESSON-011 | 保存・テストと製品結果を分ける | QA |
| LESSON-012 | 検証層を混ぜない | QA |
| LESSON-013 | PreviewとUnity stateを分ける | MATERIAL / UNITY |
| LESSON-014 | Preserveと再生成を分ける | EXPORT |
| LESSON-015 | 仮説を分ける実験を選ぶ | DEBUGGING |
| LESSON-019 | PrefabInstance identityとplacementを分ける | PREFAB / TRANSFORM |
| LESSON-020 | Model Object配置と直接参照Meshの形状座標を分ける | FBX / GEOMETRY |
| LESSON-021 | Export IDの存在をFBX輸送後に確認する | EXPORT / IDENTITY |
| LESSON-022 | Preview用TextureとUnity Material依存を分ける | MATERIAL / EXPORT |

## LESSON-001 — 表示名はidentityではない

**Status:** ACTIVE · **Domain:** IDENTITY / MATERIAL

**以前の考え:** GameObject名、Material名、Blenderの`.001` suffix、階層順、
一意に残った候補は、対応先を探す便利な手掛かりだった。初期の名前fallbackも
診断や限定的な配置に役立った。

**何が違ったか:** 同名、改名、Variant、共有資源、別Packageで候補の意味が変わる。
Case BではMaterialが存在し、名前からもっともらしい候補を選べても、
Rendererとnative Objectの同一性は証明できなかった。

**現在の原則:** 名前は表示・候補提示用。確定にはPackage scope、asset GUID、
signed local fileID、source/occurrence path、revision、realization receipt等の
出所を要する。「候補が一つ」は出所の証明ではない。

**適用範囲:** Asset/Renderer/Materialのsemantic identity。名前fallbackを使う
限定的なUI・配置処理そのものを全廃したという意味ではない。

**再調査条件:** 新たな形式で、名前とidentityの関係が版・scope付きの公式契約
として示された場合。

**根拠:** [Product identity policy](../PRODUCT_SPEC.md)、
[Case B package boundary](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)、
[Export identity model](EXPORT_IDENTITY_MODEL.md)。

## LESSON-002 — Sourceとoccurrenceと資源を分ける

**Status:** ACTIVE · **Domain:** PREFAB / BLENDER

**以前の考え:** 一つのsource Renderer、FBX Mesh、Blender datablockを見つければ、
その一つでAvatar上のRendererを代表できるように見えた。

**何が違ったか:** 同じsource componentは複数のPrefab instanceで使われる。
共有Mesh/Armature datablockの再利用も、個別のObjectやMaterial slotの
同一化を意味しない。synthetic contractは同一sourceから別root/instance
の二つのoccurrenceを生成した。

**現在の原則:** Source component key、選択rootと順序付きinstance edgeを
含むoccurrence key、Mesh資源、Blender realizationを別々に保持する。
個別Material割当はRenderer occurrenceの状態として扱う。

**適用範囲:** Prefab/Variantと共有FBX表現の設計不変条件。全real assetでの
occurrence完全性が実証済みという意味ではない。

**再調査条件:** 新しいPrefab構造で既存edge pathが個体を一意に区別できない場合。

**根拠:** [Semantic Contract v0](SEMANTIC_CONTRACT_V0.md)、
[Package Composition](PACKAGE_COMPOSITION.md)、
[synthetic contract test](../tests/test_semantic_contract_v0.py)。

## LESSON-003 — Package全体の存在は選択rootでの存在ではない

**Status:** ACTIVE · **Domain:** PREFAB / PACKAGE

**以前の考え:** Package-wideのEffective graphにsource Rendererがあれば、
選択したAvatar rootにも存在するとみなせるように見えた。Model sourceを
索引できれば、子Rendererも自動的に列挙されるという前提もあった。

**何が違ったか:** Case AのUnity selected-rootとVAPB Effectiveを比較すると、
多数のRendererはPackage全体にはあったが、選択rootのEffective occurrence
にはなかった。Stage 1A syntheticではModel indexのRenderer知識だけでは
子occurrenceが生成されず、overrideで触れたcomponentのみ現れた。

**現在の原則:** Package-wide lookup、model-child expansion、selected-root
occurrence projectionを別工程として確認する。sourceとrootの直積を無条件に
作らず、所属・継承・instance関係で裏付けた個体だけを作る。

**適用範囲:** 記録したCase Aのrepresentation gapとStage 1A fixture。
その実データの全欠落を単一のsynthetic機構だけで説明したわけではない。

**再調査条件:** 別形式のModel/Variantで、選択rootへの完全なsource chainと
occurrenceが既存projectionに既に存在すると示された場合。

**根拠:** [selected-root bridge](CASE_A_SELECTED_ROOT_OCCURRENCE_BRIDGE_FINDINGS.md)、
[provenance closure](CASE_A_SELECTED_ROOT_OCCURRENCE_PROVENANCE_CLOSURE.md)、
[Unity source chain](CASE_A_SELECTED_ROOT_UNITY_SOURCE_CHAIN_FINDINGS.md)、
[Stage 1A synthetic](CASE_A_STAGE_1A_SYNTHETIC_OCCURRENCE_PROJECTION_FINDINGS.md)。

## LESSON-004 — Generated IDをFBXから推測しない

**Status:** ACTIVE · **Domain:** FBX / UNITY / IDENTITY

**以前の考え:** FBX Model/Geometry UID、Blender Object名、または同じ候補が
一つしかないことから、Unity-generated Renderer/Mesh/Material local fileIDを
再構築できるかもしれない。

**何が違ったか:** Case Bの確認済みModelでは、必要なgenerated subasset対応が
元FBXや`.meta`の調べた項目に存在せず、Blender importも全Unity IDを保持
しなかった。候補数だけでは異なるidentity型を橋渡しできない。

**現在の原則:** Package-only mappingは**NOT PROVEN**と表現する。正確な入力
revisionに結び付くoptional Unity witnessがある場合のみ不足するmodel identity
を橋渡しし、revision不一致は拒否する。Unityは通常Importの必須依存ではない。

**適用範囲:** 調査したbinary Modelと現在の証拠。Package-only方式が将来も
絶対不可能という主張ではない。現行model witnessはFBX内Material UIDと
Unity Material subasset IDの全対応を証明しない。

**再調査条件:** 公開仕様または再現可能なpackage-only algorithmが、版・
importer設定込みでgenerated IDへの一意対応を実証した場合。

**根拠:** [Case B package boundary](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)、
[Export research corrections](EXPORT_RESEARCH_CORRECTIONS.md)、
[model witness test](../tests/test_model_identity_witness.py)。

## LESSON-005 — Unityの答えをPackageの証明と取り違えない

**Status:** ACTIVE · **Domain:** UNITY / PACKAGE / SAFETY

**以前の考え:** Unity Oracleで最終Renderer状態が分かれば、同じ入力を読む
offline importerもその答えを採用できるように見えた。逆に、projectionに
targetがないだけでUnityでも無効とみなせるように見えた。

**何が違ったか:** 残存Uの除去・復元・異なるMaterialへの差替えでは、対象
revisionの観測Renderer/Material状態は変わらず、有効overrideの対照実験
では変化した。しかしPackage/witnessは全Renderer列挙の完全性を保証せず、
別のsynthetic aliasではdirect unmatchedがUnityで実際に作用した。

**現在の原則:** `UNITY KNOWS`と`PACKAGE KNOWS`を別列にする。Unity-onlyの
無影響観測をpackage-only自動判定に流用せず、証明できないUは
`UNRESOLVED_OVERRIDE`のまま保持する。無影響判定は観測propertyとrevisionに
限定する。

**適用範囲:** 残存Uは `INERT_ONLY_KNOWN_VIA_UNITY`、今回観測した
Renderer/Material状態に限る。全Unity状態や別revisionの非作用は未証明。

**再調査条件:** source chainの新しいedge、より完全なwitness、または
別propertyでUの作用を示す独立観測が得られた場合。

**根拠:** [residual U causal audit](CASE_B_RESIDUAL_OVERRIDE_CAUSAL_AUDIT.md)、
[B-QA-002 ledger](CASE_B_BQA002_FALSIFICATION_LEDGER.md)。

## LESSON-006 — Direct unmatchedは無関係を意味しない

**Status:** ACTIVE · **Domain:** PREFAB / MATERIAL

**以前の考え:** Material overrideのtarget fileIDが投影済みRenderer IDに
直接一致しなければ、既知Rendererとは無関係としてよいと考えた。

**何が違ったか:** Unityが保存・再読込した公開synthetic Nested/Variantで、
overrideはstripped Renderer aliasと`m_CorrespondingSourceObject` chainを
経由し、実際に一つのRenderer slotを変えた。直接一致だけのprojectionは
その作用を見逃した。

**現在の原則:** Direct unmatchedを無関係へ昇格しない。serialized alias、
PrefabInstance edge、corresponding sourceを追い、対象を一意に証明できない
場合は影響し得る範囲をUNKNOWNにする。名前や候補数でR1/R2を選ばない。

**適用範囲:** 公開syntheticのstripped aliasとそのsource chain。あらゆる
未一致Uがactiveという意味ではない。

**再調査条件:** 新しいalias形式や完全なrevision-bound対応が見つかり、
UNKNOWN範囲をさらに安全に狭められる場合。

**根拠:** [B-QA-002 ledger](CASE_B_BQA002_FALSIFICATION_LEDGER.md)、
[alias projection test](../tests/test_prefab_material_alias.py)、
[public Unity alias fixture](../tests/unity_alias_oracle/)。

## LESSON-007 — UNKNOWNを必要以上に伝播させない

**Status:** ACTIVE · **Domain:** SAFETY / MATERIAL

**以前の考え:** 未解決override Uが一つあれば、同じmodel sourceのRendererを
全部UNKNOWNにする方が安全だと考えた。

**何が違ったか:** Case Bでは、その伝播が独立に証明済みのR1/R2まで止めた。
Uを除去・再挿入する反事実テストは、旧projectionだけが両行を巻き添えに
することを示した。一方、LESSON-006のalias反例は「常にUを無視する」も
誤りと示した。

**現在の原則:** Fail-closedは全停止ではなく、証拠上必要な最小scopeで
withholdすること。直接一致する行、証明済みalias instanceの互換Renderer、
無関係な個体を区別し、未知値を推測して埋めない。

**適用範囲:** 現在のMaterial override projectionと記録済みsynthetic。
既存record単位のstatusでは、alias instance内のR1だけを分離できない場合がある。

**再調査条件:** occurrence単位のより細かい証拠またはstatus表現が導入され、
影響範囲を再計算できる場合。

**根拠:** [B-QA-002 counterfactual ledger](CASE_B_BQA002_FALSIFICATION_LEDGER.md)、
[unrelated override test](../tests/test_unrelated_model_override.py)、
[Case B boundary](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)。

## LESSON-008 — Materialの存在とObject slotの割当は別

**Status:** ACTIVE · **Domain:** MATERIAL / BLENDER

**以前の考え:** 正しいMaterial datablockが読み込まれていれば、白いMeshの
原因はTextureやShader側にあると思いやすかった。共有MeshのMaterial table
を見れば各個体の割当も分かるように見えた。

**何が違ったか:** Case Bではprovider Materialが存在しても、正しい
Renderer occurrenceからnative Object slotへのbindingが欠け、白い対象が
あった。修正後はreceiptとactual Object slotのidentity一致を別途確認した。
共有Meshのtableを変更すると兄弟個体へ波及し得る。

**現在の原則:** Material providerの存在、Rendererへの割当、actual
`obj.material_slots`、node/Texture状態を分けて調べる。occurrence固有の
割当は必要に応じてOBJECT-linked slotで保持し、datablock共有と混同しない。

**適用範囲:** 検証済みCase B bindingとshared representation設計。
あらゆる白化の原因がslotだという主張ではない。

**再調査条件:** slot identityが正しくても見た目が異なる再現、または
共有データの編集が別occurrenceへ漏れる新しいfixture。

**根拠:** [Case B package boundary](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)、
[Package Composition](PACKAGE_COMPOSITION.md)、
[Blender late-slot probe](../tests/blender_late_material_slot_test.py)。

## LESSON-009 — 白やマゼンタから原因を決めない

**Status:** ACTIVE · **Domain:** TEXTURE / DEBUGGING

**以前の考え:** Viewportが白ければMaterial不在、マゼンタならTexture file不在、
と症状から一段で原因を決められるように見えた。

**何が違ったか:** Case Bの白い対象にはprovider Materialが存在し、
bindingが不足していた。一方、Material Previewのマゼンタでは参照画像Path
と画素が読めることまで確認されたが、表示原因は未確定だった。

**現在の原則:** Renderer→Object slot→Material node→Image/Texture→Path→
Shader/Previewを順に分離する。白・マゼンタは診断開始点であり、
欠落原因や修正先のidentity証拠ではない。

**適用範囲:** 記録済みCase Bの白化とPreview観測。マゼンタの根本原因は
**UNKNOWN**であり、画像が読めたことだけでPreview正常とは言わない。

**再調査条件:** 同じslot/node/pathが維持された状態で再現性ある
Preview差が得られ、Shader・レンダラー・cache等を切り分けられた場合。

**根拠:** [Case B QA findings](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)、
[Material/visual acceptance](../TEST_STRATEGY.md)。

## LESSON-010 — Fail-closedには説明が要る

**Status:** ACTIVE · **Domain:** UX / SAFETY

**以前の考え:** 不確実なMaterial割当を止め、内部registryへ未解決状態を残せば、
製品としても十分だと考えた。

**何が違ったか:** Fresh User QAではwitnessなしImportが安全に部分成功しても、
再開したBlender画面から理由と次の安全な行動が分からず、白いバグに見えた。

**現在の原則:** Withholdする範囲と理由を保存し、Import結果UIで
未解決identity・欠落provider・曖昧性等を分けて説明する。表示件数は
証拠record数でありMesh数やAvatar完成度ではない。証明できないObjectを
選択対象として提示しない。

**適用範囲:** 現行Import結果panelと検証済みFresh User経路。
説明があることは自動修復やRound-trip成功を意味しない。

**再調査条件:** 利用者が残る原因・操作を理解できない新しい未解決分類や
保存再開後の表示欠落が見つかった場合。

**根拠:** [Current State: B-QA-001](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Case B installed-ZIP QA](CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)、
[outcome test](../tests/test_import_outcome.py)。

## LESSON-011 — 保存成功やテスト件数は製品成功ではない

**Status:** ACTIVE · **Domain:** QA

**以前の考え:** Importが終了し、`.blend`を開き直せて、Pythonテストが多数PASS
すれば、Avatarを使える状態に近いと判断しやすかった。

**何が違ったか:** 実際のFresh User経路では保存再開できてもMaterialが
未結合のままだった。別の検証では依存registryの状態変化が起きても、
Object slotは保持された。保存、内部記録、実際の見た目は異なる判定軸だった。

**現在の原則:** Pythonのsemantic検査、Blender Object/slotと保存再開、
exact ZIPのinstall/enableとGUI、Unity fresh import/rebind、VRC利用結果を
別々に報告する。製品成功は求めた実処理の受入条件で判定する。

**適用範囲:** QA方法論。古いtest結果はその時点の対象とruntimeの証拠であり、
現在の全Avatar対応を示さない。

**再調査条件:** 新しい自動テストが実UIとUnity/VRC最終結果を独立に
十分観測できるようになった場合でも、対象範囲を明記して再評価する。

**根拠:** [Test Strategy](../TEST_STRATEGY.md)、
[historical Test Results](../TEST_RESULTS.md)、
[Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[README limitations](../README.md)。

## LESSON-012 — Syntheticと実データとOracleの役割を混ぜない

**Status:** ACTIVE · **Domain:** QA / UNITY

**以前の考え:** 小さなsynthetic fixtureがPASSすれば、同じ機構の実Avatarにも
広く対応したと読み替えやすかった。実データで差が出ても、syntheticの
期待値だけで製品動作を確定できるように見えた。

**何が違ったか:** Stage 1A fixtureはprojectionの具体的な機構を示したが、
Case Aの実selected-root gapの全原因を単独では証明しなかった。
Case BではUnity public APIのexpanded stateとBlenderの実Object slot検査が
別々に必要だった。

**現在の原則:** Syntheticで原因を隔離し、private実データで現実適合性を
確認し、Unity Oracleで期待する最終意味を観測し、exact ZIP/Fresh User経路
で製品挙動を確認する。実データで見つけた機構だけを匿名syntheticへ縮約する。

**適用範囲:** 検証方法。Unityは通常Importの必須依存ではなく、Oracleとしての
使用もsource revisionと観測範囲に限定する。

**再調査条件:** 新しい入力形式、Unity/Blender版、VRC SDK挙動で
既存fixtureと実データの結果が分かれた場合。

**根拠:** [Stage 1A synthetic findings](CASE_A_STAGE_1A_SYNTHETIC_OCCURRENCE_PROJECTION_FINDINGS.md)、
[Case A Unity source chain](CASE_A_SELECTED_ROOT_UNITY_SOURCE_CHAIN_FINDINGS.md)、
[Case B ledger](CASE_B_BQA002_FALSIFICATION_LEDGER.md)、
[core acceptance](../PRODUCT_SPEC.md)。

## LESSON-013 — Blender PreviewをUnity stateの正本にしない

**Status:** ACTIVE · **Domain:** MATERIAL / UNITY

**以前の考え:** Blenderでそれらしく見えるShader node graphを作れば、
元のUnity/VRC Shader stateも復元できるように見えた。

**何が違ったか:** BlenderのPrincipled BSDFは異なるShader環境の近似表示に
すぎない。Case BのPreview症状も元Material identityやserialized shader
propertiesの存否を直接示さなかった。

**現在の原則:** Unity Shader identity、serialized properties、参照、keywords
等を保全する層と、Blenderの編集支援Previewを分ける。Preview nodeをそのまま
Unity Shaderの正本として逆出力しない。

**適用範囲:** Shader/Material設計境界。任意のUnity Shaderが完全復元済みと
いう主張ではない。

**再調査条件:** 特定Shader familyについて、両環境で意味と逆変換を
検証した明示的な契約が追加された場合。

**根拠:** [Product shader policy](../PRODUCT_SPEC.md)、
[Architecture material boundary](../ARCHITECTURE.md)、
[Export research corrections](EXPORT_RESEARCH_CORRECTIONS.md)。

## LESSON-014 — Raw Preserveと再生成を同じidentityで扱わない

**Status:** ACTIVE · **Domain:** EXPORT / IDENTITY

**以前の考え:** FBXを再出力して元のGUID/fileIDを置けば、元Prefab参照も
そのまま使えると考えやすかった。元Assetを保つ経路と再生成する経路を
同じ操作として扱いがちだった。

**何が違ったか:** Generated model subassetのpost-import local fileIDは、
元FBXやBlender名だけで証明できない。同じGUIDでも変更bytesの安全性は
保証されない。Export資料はraw preserve/typed patchと再生成・Unity後観測を
別境界として再設計した。

**現在の原則:** 未変更sourceはbytes/meta/GUIDを保つ`PRESERVE`、変更は
検証済みtyped `MODIFY`、新規・再生成は新しい出力identityとrebind taskに
分ける。生成IDはexact出力をUnityへimportした後の公開API観測、または
同等に証明されたbridgeで確認する。曖昧な参照は停止する。

**適用範囲:** Export設計原則。全種のUnityPackage再生成やVRC完成を
証明したものではない。現行の限定Export成功を一般化しない。

**再調査条件:** 特定資産種について、offlineでpost-import identityが
保証される公開契約と実験結果が得られた場合。

**根拠:** [Export architecture decision](EXPORT_ARCHITECTURE_DECISION.md)、
[Export identity model](EXPORT_IDENTITY_MODEL.md)、
[Export research corrections](EXPORT_RESEARCH_CORRECTIONS.md)、
[Export unknown matrix](EXPORT_UNKNOWN_MATRIX.md)。

## LESSON-015 — 確認回数より反証力で実験を選ぶ

**Status:** ACTIVE · **Domain:** DEBUGGING

**以前の考え:** 同じImportやテストを重ねれば、残る不具合の原因が自然に
絞れるように見えた。症状から最もありそうな犯人を先に決めがちだった。

**何が違ったか:** B-QA-002ではUの除去・再挿入と旧projection replayが、
広すぎるUNKNOWN伝播を切り分けた。残存Uでは除去・復元だけだと同値値の
見逃しが残るため、異なるMaterialへの差替えと有効overrideの陽性対照を
加えてUnity側の非作用を限定的に示した。

**現在の原則:** 仮説ごとに必要条件、反証条件、変更する一変数、独立Oracle、
観測範囲を先に定義する。`CAUSALLY_CONFIRMED`と`SUPPORTED`、
`REJECTED_IN_SCOPE`と`UNKNOWN`を区別し、次の判断に足る証拠で止める。

**適用範囲:** 記録されたoverrideとprojection調査。反事実実験でも
測っていないpropertyや別revisionの結論は出せない。

**再調査条件:** 新しい反例が既存の最小実験の前提または観測項目を破った場合。

**根拠:** [B-QA-002 falsification ledger](CASE_B_BQA002_FALSIFICATION_LEDGER.md)、
[residual U causal audit](CASE_B_RESIDUAL_OVERRIDE_CAUSAL_AUDIT.md)、
[synthetic counterfactual test](../tests/test_unrelated_model_override.py)。

## LESSON-016 — Texture provider identity and binding role are different

**Status:** ACTIVE · **Domain:** DEPENDENCY / USER EDIT

**以前の考え:** 同じMaterialとImage GUIDなら、Texture依存は一件として
扱えるように見えた。再解決で同じproviderを見つければ、既存nodeへ安全に
再適用できるとも考えられた。

**何が違ったか:** 一つのImageをBase ColorとEmissionへ使う公開fixtureでは、
GUIDだけのkeyとrole推定が一方の用途を消した。また、ユーザーがImageや
node接続を編集した後の再解決は、その編集を上書きした。保存済みの依存
statusだけでは、nodeを現在もVAPBが管理している証拠にならない。

**現在の原則:** Texture依存はMaterial、Unity property、semantic role、
provider identityを区別する。自動再適用・解除の前に、VAPBが適用した
Imageと対象node接続の状態を照合する。照合receiptが無い旧Sceneや
編集済みnodeは推測で上書きしない。registryの`BOUND`件数は表示中の
Image node数やExport成功の代理指標にしない。

**適用範囲:** Blender 5.2.1での公開synthetic Texture resolverと、
保存済みprivate Sceneの集計観測。全Shader graph編集やfresh private
round-tripの保証ではない。

**再調査条件:** 同じrole/propertyでも別occurrenceごとに異なるTextureが
必要な反例、または編集判定の取りこぼしが見つかった場合。

**根拠:** [Unknown Boundary checkpoint](UNKNOWN_BOUNDARY_FAULT_DISCOVERY_20260927.md)、
[dual-role test](../tests/blender_texture_role_collision_test.py)、
[edit sequence test](../tests/blender_texture_user_edit_test.py)。

## LESSON-017 — 明示的なnull参照と解析不能を分ける

**Status:** ACTIVE · **Domain:** UNITY PREFAB SEMANTICS

**以前の考え:** PrefabのMaterial overrideにGUIDが無い場合は、対象Materialを
解析できないので一律にUNKNOWNとするのが安全に見えた。

**何が違ったか:** Unity 2022.3.22f1が作った公開Variantでは、
`m_Materials.Array.data[0]` の `objectReference: {fileID: 0}` は有効な
「Materialなし」という最終値だった。これを捨てると、元Materialを残す
可能性がある。GUID欠落の非zero参照は引き続き解析不能だった。

**現在の原則:** Unityが明示的にserializeしたnullを既知の値として記録し、
不完全な非null参照とは区別する。exact Renderer occurrenceとnative Mesh
receiptを証明できた場合だけ、provider探索とは別のclear operationで
Blender **Object** slotを空にする。適用後のユーザー編集は再resolveで守る。
Import成功は保存されたprojectionだけでなくlive Object slotから判断する。

**適用範囲:** 公開Unity-authored一slot VariantのParser/Projectionと、
exact FBX witnessで特定したnative Objectへの直接realization、save/reopen。
通常の`.unitypackage` operatorではnested Variantのnative sourceが
`NATIVE_MISSING`のため未成立。配列長変更、多段Variant precedence、Exportは未証明。

**再調査条件:** Unityが別形式のnull Material overrideをserializeする例、
またはslot実現との相違が見つかった場合。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Unity-authored null fixture test](../tests/test_unity_null_material_oracle.py)、
[native FBX realization probe](../tests/blender_unity_null_fbx_test.py)。

## LESSON-018 — Prefab-local Rendererとmodel resourceを別のidentityとして橋渡しする

**Status:** ACTIVE · **Domain:** NESTED PREFAB / NATIVE REALIZATION

**以前の考え:** Native model instance候補は`MODEL_SOURCE`のrecordだけから列挙すれば
十分であり、`PREFAB_LOCAL`はPrefab内のsemantic Rendererとして保持すればよい。

**何が違ったか:** 公開Unity 2022.3.22f1 Variantでは、source Rendererはsource
Prefabに属する`PREFAB_LOCAL`だが、MeshFilterは別のFBX model assetのMeshを
exact GUID/signed local IDで参照していた。`MODEL_SOURCE`だけを列挙すると、
projectionは正しくてもnative member Objectが作られず`NATIVE_MISSING`になる。

**現在の原則:** source Renderer identity、Mesh resource identity、occurrence
identity、native realization identityを分ける。serialized PrefabInstance chainと
Mesh参照が揃い、optional witnessでFBX revisionとModel/Geometry UIDを検証できる
場合だけ、既存のnative source Objectからinstance pathごとに別Objectをcopyする。
名前、順序、候補数はidentity根拠にしない。証拠が欠ければ作らない。

**適用範囲:** 公開のMeshRenderer/二重nested instance、exact witness付き通常
UnityPackage Import。Material Aとexplicit nullのObject slot独立性、保存後再読込、
別root、改名後のbindingを確認。Unity `-1/+1` に対しBlender Meshは両方`-1.5`で
Transformは未解決。Skin/Armature、Export、VRC runtimeは未証明。

**再調査条件:** witnessなしのpackage-only Mesh local ID bridge、Prefab-local
Rendererとmodel Rendererのclassが異なる正当な使用、複数Meshが一つのRendererへ
対応する実例が見つかった場合。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Unity source-chain oracle](../tests/unity_alias_oracle/Assets/Editor/VapbNullChainOracle.cs)、
[repeated-instance oracle](../tests/unity_alias_oracle/Assets/Editor/VapbNullRepeatedOracle.cs)、
[normal operator Blender probe](../tests/blender_nested_prefab_realization_test.py)。

## LESSON-019 — PrefabInstance identityだけではplacementは再現されない

**Status:** ACTIVE · **Domain:** PREFAB / TRANSFORM

**以前の考え:** ordered instance edgeと別Object realizationを作れば、source
FBXのnative matrixを維持したまま配置も自然に再現される。

**何が違ったか:** UnityがserializeしたPrefabInstance root Transform overrideを
Emptyへ反映しておらず、memberの再親子付け時には旧world matrixを復元していた。
公開の2個体でidentityとMaterialは別でも、world位置は同じだった。

**現在の原則:** source Prefab rootのposition/quaternion/scaleをexact revisionで
読み、instance fileIDとsource root Transform identityが一致するpropertyだけを
component単位でoverlayする。既存basis変換を通してinstance Emptyへ一度だけ
適用し、native frameは別途検証したmember localとして扱う。root以外のTransform
override、曖昧なsource/parent、無効な値やreceiptは推測せず`UNRESOLVED`。
`EXACT`は親、source、native receiptまで揃った後に付ける。

**適用範囲:** 公開Unity 2022.3.22f1のMeshRenderer、depth-1 PrefabInstance。
非identity source、回転、非一様/負scale、変換済み親、2個体、改名とsave/reopenで
4×4 matrix parityを確認。depth > 1、Skin、Export/VRCは未証明。

**再調査条件:** Unityが部分quaternion overrideを非unitのまま有効化する例、
semantic親がnative Objectである例、depth > 1のlocal placement証拠が得られた場合。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Unity-authored Transform Oracle](../tests/unity_alias_oracle/Assets/Editor/VapbTransformOracle.cs)、
[effective TRS tests](../tests/test_prefab_instance_transform.py)、
[normal operator matrix probe](../tests/blender_nested_prefab_realization_test.py)。

## LESSON-020 — Model Object配置と直接参照Meshの形状座標を分ける

**Status:** ACTIVE · **Domain:** FBX / GEOMETRY

**以前の考え:** Unityのinstance matrixとBlenderのnative FBX Object matrixの
合成が合えば、Rendererの最終形状も合う。

**何が違ったか:** 公開depth-1 MeshRendererでは行列合成が通っても、Unity
public APIで得た最終world頂点とBlender depsgraph評価後の頂点集合に3.64以上の
差が出た。source PrefabがFBX Mesh subassetを直接参照し、UnityはFBX file unit
scale `0.01`を適用する一方、native Model Objectの平行移動はそのMesh参照に
含まれなかった。非対称な別fixtureでも軸変換と単位を独立に確認した。

**現在の原則:** instance placement、native Model Objectの配置、直接参照
Meshのlocal frame、評価後world geometryを別々に検証する。Mesh subassetの
frameを確定するにはsource Prefab参照、FBX revision、importer設定とraw FBX
軸・単位を揃え、未対応設定は`UNVERIFIED`にする。頂点番号やObject名で対応を
推測せず、形状比較をRenderer identityの根拠にも転用しない。

**適用範囲:** Unity 2022.3.22f1、Blender 5.2.1の公開synthetic
MeshRenderer、depth-1、確認済みimporter設定。独立world点集合最大誤差
`2.384e-7`、許容値`1e-5` Blender meters。Skin、他のFBX設定、面対応、
Export/VRCは未証明。

**再調査条件:** 異なるFBX unit/axis/bake設定、source PrefabがModel
Objectを参照する場合、Mesh以外のRenderer、Skin/Armatureが必要な場合。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Unity Geometry Oracle](../tests/unity_alias_oracle/Assets/Editor/VapbGeometryOracle.cs)、
[独立観測値](../tests/unity_alias_oracle/geometry_expected.json)、
[通常Import Blender probe](../tests/blender_nested_prefab_realization_test.py)、
[Unity ModelImporter.fileScale（2022.3）](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-fileScale.html)。

## LESSON-021 — Export IDの存在をFBX輸送後に確認する

**Status:** ACTIVE · **Domain:** EXPORT / IDENTITY

**以前の考え:** Blender ObjectにExport ID custom propertyを付け、FBX exporterに
`use_custom_props=True`を渡せばUnityまでIDが届くと考えた。

**観測・反証:** 別の一時SceneにObjectをコピーした初回出力ではPackage生成は成功したが、
FBXバイト列にExport IDがなく、Unity Finalizerは対象Meshを一意に特定できなかった。
同じ公開synthetic Meshを現在Scene上の一時Objectとして書き出すと、FBX IDと
Unity公開user-property callbackの両方でIDを観測できた。IDなし/重複は拒否し、
表示名の変更は受理した。

**現在の原則:** 出力前のBlender metadataは輸送成功の証拠ではない。生成FBXに
IDが残ったことを確認し、Unity側でもexact Recipe revisionと一意のObject IDを
照合する。Material slotは名前ではなくRecipeのExport IDから解決する。

**適用範囲:** Blender 5.2.1 / Unity 2022.3.22f1、公開syntheticの単一static UV
Mesh。Skin、複数Object、他Importer設定には一般化していない。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Blender E2E](../tests/blender_final_state_export_test.py)、
[Unity fresh/mutation probe](../tests/unity_final_state_probe/Editor/VapbFinalStateFreshProbe.cs)。

## LESSON-022 — Preview用TextureとUnity Material依存を分ける

**Status:** ACTIVE · **Domain:** MATERIAL / EXPORT

**以前の考え:** Blender Previewに使われる画像だけを、Material帰還に必要なTextureと
見なせそうだった。

**観測・反証:** 既存のUnity Material parserはShaderと、対応する`m_TexEnvs`の
Texture referenceをPreview roleとは別に保持する。ただし2026-09-30のpublic
synthetic反例で、underscoreなしのpropertyを取りこぼし、不正fileIDを0へ変換する
ことが確認された。全serialized referenceを取得できるとは扱えない。
現行final-state ExportはStandard Shader
gateで実VRC由来Materialを拒否し、Texture providerもMaterialと同一Packageだけを
探索する。private代表1件の最初の停止はこのShader gateだった。特定Textureの
欠落やcross-package provider不一致は、まだ実測していない。

**現在の原則:** Blender node graphはPreview用。出力対象のTextureは元Unity
`.mat`のnon-null serialized referenceから列挙し、Package provenanceで一意の
providerを選ぶ。未知propertyも役割を推測せず依存として保持する。Shader依存は
Textureと分けて判定する。parserの参照取得範囲とmalformed入力拒否も検証し、
解析失敗をnullへ変換しない。Exportにはopt-inの`strict_references`を使用し、
Preview用の既定解析と分離する。証拠不足なら完全復元を宣言しない。

**適用範囲:** 新しいstatic final-state Material帰還の設計境界。実データの
cross-package復元や任意Shaderのfresh Unity成功は未証明。

**根拠:** [Current State](VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md)、
[Material parser](../unity/material_parser.py)、
[final-state exporter](../export/final_state_package.py)。

## How to use this document

1. 新しい仮説を立てる前に、該当DomainのLessonと根拠・適用範囲を確認する。
2. `REJECTED_IN_SCOPE` を再利用するときは、入力revisionと反証条件が同じか確認する。
3. 新しい反例では旧Lessonを消さず、適用範囲を狭めて更新する。
4. 新しい `LESSON-XXX` には「以前の考え → 観測・反証 → 現在の原則」と根拠を付ける。
5. 一度成功しただけの結果をLessonにしない。各Lessonの `Status` はMarkdown内で
   `ACTIVE`、`NARROWED`、`SUPERSEDED` として更新し、過去の判断も追えるようにする。
