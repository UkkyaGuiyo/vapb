# Unity・Blender・VRChat 公式仕様参照

確認日: **2026-10-11 UTC**。用途: VAPB担当が、公開仕様・実装・実測の境界を確認するための日本語参照資料。

調査基点: `feature/r2-material-slot-reorder` / `f29702cdac64a0fbd807723cd79e652ffd5067e1`。この資料は独立cloneの `docs/official-specs-unity-blender-vrchat-20261011` だけに追加する。製品実装、guard、素材、既存実測記録を変更しない。Editor、Blender、clientを起動していない。

## 読み方

1. [適用バージョン](VERSIONS.md)を確認する。最新版とVRC対応版とVAPB実測版を混同しない。
2. Materialの直接課題は [接続方向・識別子・面対応](UNITY-MATERIAL-MESH.md)から読む。
3. 頂点数差・CP/face/skin対応は [頂点対応とimport policy](VERTEX-CORRESPONDENCE.md)。[Unity往復](UNITY-ROUNDTRIP.md)、[Blender](BLENDER.md)、[VRChat](VRCHAT.md)で保存対象と変換境界を確認する。
4. [課題への適用と未証明項目](VAPB-BOUNDARIES.md)で、一般仕様が実データの成功を証明しているかを確認する。
5. [公式出典索引](SOURCES.md)のIDから原典の見出しへ戻る。各主張の対象版、根拠区分、取得状態を確認する。

## 根拠区分

|区分|意味|証明しないこと|
|---|---|---|
|DOC|公式Manual / Creation / APIの公開説明|特定素材の往復成功、全バージョン共通の不変性|
|API|版指定された公式公開API契約|APIを実行して得るべき値、内部アルゴリズム|
|REL|公式release notes / support policy|別系列の互換性、対象データの無損失変換|
|SRC|公式sourceの固定tag/commitを読んだ結果|安定API契約、配布binaryと当該sourceの同一性、非公開native処理|
|LOCAL|既存VAPB文書・設定の読み取り|公式保証、今回のruntime再検証|
|INFERENCE|明示された一般仕様からの推論・設計上の適用|未観測の割当をPROVENへ昇格すること|
|UNKNOWN|取得不能、未調査、未公開または十分な橋渡しなし|不存在・不可能の証明|

資料本文は自作の要約。原典・SDK・素材の転載や同梱は行わない。公式サイト内からリンクされた第三者ブログやツールも公式根拠に加えない。権利判断をSDKの技術的読取可能性から推定しない。

## 機能分野索引と調査状態

`詳細` = 該当範囲の根拠を読んで本文へ整理、`概要` = 公式体系と重要な境界だけ確認、`入口` = 原典への案内のみ、`取得不能` = 本文を得られず仕様確定不可。詳細でも全API監査済という意味ではない。

|製品|機能分野|状態|参照|
|---|---|---|---|
|Unity|Asset import / metadata / serialization / GUID・fileID / package|詳細、package内部schemaは未公開扱い|UNITY-ROUNDTRIP / U01–U08|
|Unity|Prefab / Variant / nested / override / source chain|詳細|UNITY-ROUNDTRIP / U18–U22|
|Unity|Renderer / Mesh / submesh / Material / Texture / Shader|詳細|UNITY-MATERIAL-MESH / U09–U17、U31–U32|
|Unity|Skin / bone / bindpose / weights / blendshape / transforms / FBX rig / vertex split・weld|詳細、null bone・CP対応のnative挙動は未確認|UNITY-ROUNDTRIP / VERTEX-CORRESPONDENCE / U23–U30、U33–U45|
|Unity|Animation / humanoid・generic / binding / Animator|詳細、完全retarget・curve変換は未実証|UNITY-ROUNDTRIP|
|Unity|Rendering pipelines / lighting / VFX / particles / 2D / UI / audio|入口|U00の公式Manual体系|
|Unity|Scripting / physics / navigation / networking / services / platforms / build / profiling / XR / packages|入口|U00。VAPB対象componentごとの適用は未調査|
|Blender|ID / data users / ObjectとMesh / slots / face material|source詳細、5.2 API本文取得不能|BLENDER / B01–B04|
|Blender|Depsgraph / originalとevaluated / modifier / armature / pose / vertex group|source概要、API本文取得不能|BLENDER / B04–B07|
|Blender|Action slots・layers / NLA / FBX import・export|source詳細、全変換経路未調査|BLENDER / B08–B11|
|Blender|Modeling / sculpt / UV / geometry nodes / shader nodes / render / compositing / tracking / video / Grease Pencil / simulation / asset library / UI / Python|入口、一部公式Manual取得不能|B00 / B12|
|VRChat|SDK・Unity support / Public API / Avatar Descriptor|詳細|VRCHAT / V01–V04、V12–V13|
|VRChat|PhysBone・Collider / Contact / Constraint / Animator layers / Expressions・parameters|詳細（公開説明範囲）|VRCHAT / V05–V10|
|VRChat|Allowed components / platform limits / performance / shader fallback / upload変換|概要、一部入口|VRCHAT / V11、V14–V16|
|VRChat|World / Udon・UdonSharp / networking / persistence / players / voice・audio / ClientSim|概要または入口|VRCHAT / V17–V22。停止案件を再開しない|
|VRChat|OSC / tracking / client permissions / avatars・worlds publishing / Creator Economy|入口|公式Creationとclient docs。個別挙動は未調査|
|共通|ライセンス・再配布 / 非公開file format / client内部 / issue差分|概要または未調査|VAPB-BOUNDARIES。第三者素材の個別許諾は対象外|

## 監査可能な完了範囲

初版はMaterial/Mesh/GUIDと版表・出典を先にremote保存・本文読み戻し確認した。第二段階でSkin/Animation/Blender/VRChat、頂点対応と全体索引を追加した。分野索引が全体を見渡すための範囲であり、「全APIを読んだ」「24 packageを再実測した」という主張はしない。今後の更新は、原典の版と取得日を更新してから行う。

調査はこの作業のWeb取得ツールと公開URLの読み取りだけで実施。通常ブラウザは使用していない。HTTP拒否は認証・UA変更等で迂回しない。公式source mirrorは公開された別種の根拠として区別する。
