# VAPB — VRChat / VRCアバターのUnityPackageをBlenderで改変するAdd-on

## Current handoff

Current installable WIP snapshot: `vapb-c5585a6.zip`, code commit `c5585a669320faece2133cab80470ca65104fa09`, SHA-256 `9c71fb2dd8cff24615e15245efc7da7b6dd5deed4c411d353f786b53de30f04c`. Rebuild from this checkout with:

```powershell
python tools/build_distribution_zip.py --repo . --revision c5585a669320faece2133cab80470ca65104fa09 --output vapb-c5585a6.zip
```

Source checkpoint after this ZIP: Semantic Bone Merge now refuses equivalent Bone mappings whose parent correspondence differs. The parent guard, bounded World/head Copy Location and Bone Transform Action support and the normal-import source provenance guard fix are not included in `vapb-c5585a6.zip`; see [the regression result](TEST_RESULTS.md#bone-merge-parent-correspondence-2026-10-09).

Standard isolated Blender installation passed. The sole runtime change fixes Unity JSON reading of absent optional Skin receipts. Focused native JSON controls and normal Unity import/Finalizer Apply/repeat passed for one first-party PhysBone/Collider case using the existing SDK, preserving null roots, settings, real script identities and the native Collider reference. [Native component scope and retained failures](tests/evidence/remapped_model_replacement_export_20261008/native-physbone-collider-roundtrip.json) and [earlier distribution observations](tests/evidence/remapped_model_replacement_export_20261008/distribution-native-skin-return-summary.json) remain separate. The unchanged current ZIP also passed one [native ContactSender return](tests/evidence/remapped_model_replacement_export_20261008/native-contact-sender-roundtrip.json): explicit bone Transform identity, radius, tag and source correspondence survive Apply/repeat. GUI clicks, client simulation and full Avatar state remain unverified. This is an installable WIP snapshot. SDK and input assets are not included in the add-on ZIP.


For the current branch, evidence status, and exact next action, start at [START_HERE.md](START_HERE.md). Specific remaining product requirements and evidence limits are recorded below; campaign coverage is not a substitute for completing those requirements.

**VAPB (VRC Avatar Package Bridge)** は、VRChat / VRC向けアバター・衣装・小物の `.unitypackage` をBlenderへ直接読み込み、BlenderでMesh・Bone・Weight・Shape Key・UV・Textureなどを編集し、対応範囲の結果をUnityへ戻す作業を支援する無料・オープンソースのBlender Add-onです。

UnityからFBXを書き出してBlenderで編集し、Unityへ戻したあとにMaterialや各種設定を手作業で貼り直す――というアバター改変の往復作業を減らし、**Blender中心でVRChatアバターを改変できるワークフロー**を目標にしています。

## VRC / VRChatアバターをBlenderで改変したい人へ

VAPBは、たとえば次のような用途を対象にしています。

- **VRCアバターのUnityPackageをBlenderで改変したい**
- **VRChatアバターをBlenderで編集したい**
- **UnityPackageをBlenderへ直接Importしたい**
- **Unityでのアバター改変が面倒なので、Blender中心で作業したい**
- Blenderで編集したMesh・Bone・Weight・Shape Key・Textureなどを、対応範囲でUnityへ戻したい
- Avatar本体、衣装、Accessoryなど複数のUnityPackageをBlender側で扱いたい

> **Experimental / Alpha:** VAPBは現在開発中です。すべてのVRChatアバター、Prefab、Shader、VRC Componentの完全な往復を保証する段階ではありません。実装済み・検証済み・未検証の範囲は、このREADMEと `PRODUCT_SPEC.md`、`docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md` に分けて記録しています。

## What VAPB does

### 対応範囲のPackage → Blender編集 → Unity復帰

通常利用では、入力PackageをUnityで展開したり、FBX／GUIDを調べたりする必要はありません。

1. Blenderの **File → Import → Unity Package / VRChat Avatar (.unitypackage)** で作者所有Packageを読み込みます。
2. 編集するMeshを選び、Blenderの編集モードで頂点を編集します。通常の `.blend` 保存・再開を使えます。保持された元Package保管先も残してください。
3. 元モデル由来Skinは **File → Export → VAPB UnityPackage（Mesh / Skin）** を選び、新しい出力名にします。PrefabなしSkinは **アクティブMeshのみ** で1 Meshずつ。同じPrefab個体の対応済みSkinは **選択Mesh** でまとめられます。
4. Unityの作業用Projectへ出力PackageをImportし、Editor scriptsのコンパイル完了を待ちます。自動表示される **VAPB：編集内容を確認** で結果を確認し、**適用** を押します。確認だけで閉じたい場合は **キャンセル** です。自動適用はしません。
5. 作成・選択された別Prefab Variantで、形状、面の素材割当、TextureとBone／ポーズを確認します。元モデル／Prefabは残ります。

Prefabなしの単一元モデルSkinでは、出力Materialのフォルダー・filenameを整理します。元Materialの中身・名前・GUID・metaは保持し、所属根拠がないものは **Unassigned** です。元GUID・出力pathが未占有の既存Projectで、Unityの整理先への配置と参照・形状保持を確認しました。

確認画面を開き直す場合は **Tools → VAPB → 編集内容を確認** を使用します。
表示された未対応理由をGUID／fileIDの手編集や素材の推測割当で回避しないでください。

Prefabなしの限定成功例は、標準ModelImporterに明示Material remapがある1 Skin、3Material、非null PNGの保持です。形状1.25倍・保存再開・通常Unity復帰を[実観測](tests/evidence/remapped_model_replacement_export_20261008/nonnull-texture-normal-unity-return.json)で確認しています。任意のSkin、骨階層変更、新規骨、Avatar全体やVRChat uploadの対応を意味しません。

元Meshを削除して新しい静的Meshを作る場合は、Unity由来Materialを割り当てて **VAPB UnityPackage（Blender完成形）** を使います。この別routeは新規Prefabを作り、Skin／元Prefabの階層・VRC Component復元には対応しません。Unity復帰は同じ確認画面の **適用** です。[限定T4結果](tests/evidence/remapped_replacement_return_preparation_20261008/README.md)を参照してください。

旧複数override入力で元のUnity submeshとBlender面の素材対応を証明できない場合、その入力は未対応／未解決です。名前・slot順・面数から補完しません。対応済みの別入力の往復は利用できます。

本人の最小確認は、作者所有素材のコピーで **読み込み → 小さな頂点編集 → 出力 → 別Variant確認** を1回行うことです。元Assetが残ること、意図した形状と面の素材・Texture、対象のBone／ポーズを確認してください。Package内にあるShader等の必要frameworkは、Unity作業Project側で用意します。SDK・購入素材・元Packageをこちらへ公開する必要はありません。

For the normal `.unitypackage`-to-Blender editing workflow, users do not need to import the input package into a Unity project or manually export an FBX first. Any temporary extraction and FBX interchange is handled internally by the add-on. A Unity Editor/project is a development verification oracle, not a prerequisite for starting the Blender import; importing the finished output package into Unity is a separate return step.

VAPB is an experimental **Blender add-on for importing VRChat / VRC avatar UnityPackage files into Blender**, editing supported avatar geometry and assets in Blender, and returning supported results to Unity. It is designed for workflows such as **UnityPackage to Blender**, **VRChat avatar editing in Blender**, and **Blender-centered avatar customization** without manually rebuilding every Unity-side assignment after each edit.

Blender 5.2.1 LTS専用の `.unitypackage` インポーターです。Version 0.4.0 candidate。通常のImportではUnity Editorを起動せず、UnityPackageを一時フォルダへ安全に復元し、FBXをBlenderへ読み込みます。

Blender 5.2.1 LTSでは、Blender OperatorをMRO先頭に置く公式形式と、Blender内部引数を受け取るconstructor形式に対応しています。legacy `bpy.ops.import_scene.fbx` は既存のArmature、Weight、Shape Key、Material Slotの挙動を維持するため継続使用します。

## 現在の製品化状況

**Experimental / Alpha — 製品仕様全体は開発中です。** 複数のprivate実VRC Packageで、選択した既存骨Skinの編集・保存再開・UnityPackage出力・UnityでのVariant復元を検証しています。Shape Key付きSkinでは、意図したベース頂点とShapeの編集、他のShape・骨・素材・VRC参照の保持を新規Unity Oracleで確認しました。これはAvatar全体の往復対応やVRChat上でのビルド・実行成功を意味しません。

新Product Modelの初期経路として、Blenderで元Meshを削除して作成した単一static
UV Meshを、新しいFBX/GUIDと選択したUnity由来Material/TextureからPackage化できます。
**File → Export → VAPB UnityPackage（Blender完成形）** を使い、fresh Unity
2022.3.22f1へPackageをImportし、コンパイル完了後に自動表示される
**VAPB：編集内容を確認** から **適用** を押します。公開syntheticの
UV CubeでMaterial slotとTextureの自動復元を検証済みです。元Meshの形状を
変えずに出力した公開synthetic Case Aもfresh Unityで確認しました。現在この新経路は
単一static UV Mesh、Unity built-in Standard Materialに限定され、Skinや
VRC Componentの復元には対応していません。従来のsource-bound出力は残しています。

選択した既存Skinに結び付くTextureでは、出所を確認できるpacked PNGの実編集・save/reopen・UnityPackage出力・新規Unity Projectでの画素変化とGUID/meta/Material参照の保持を、異なる実データ2ケースで確認しています。同じPrefab個体に属する複数のモデル由来Skinを一つのVariantへ復元する経路は、公開syntheticと実データの各2 Meshで検証しました。実データでは34 Renderer中の意図した2件を独立した出所情報で特定し、他32件と元アセットの保持も確認しています。実Avatar全体の往復、任意のMaterial node graphのUnity Shader変換、全画像形式への対応は未検証です。

最優先は複数実データでのCore round-tripです。全面的な構造・編集操作・依存Packageへの対応、Unity/VRCでの利用可能性は未完了です。Hierarchy Parityでは、公開Majunと代表実Packageのsemantic親子関係・Transform・Renderer所属・Mesh receipt・ordered Bones・rootBone・Bone attachmentを、独立Unity public APIと通常Blender Importで比較し、全Object/Bone改名後のsave/reopenまで一致を確認しました（実データ1,274項目）。このsupported scopeの階層判定はGREENですが、形状比較20件はREDのままで、PrefabのShape Key channel対応も未証明です。全Prefab・全AvatarのSkin変形や形状一致を保証する結果ではありません。座標系の回帰修正は新規Importに適用され、既存の保存済みBlendを自動変換しません。Weight Transfer、参照を確認できる範囲のCleanup・Bone Mergeは合成データで検証しており、Coreの成立後も完成へ進めます。配布ZIPごとの検証済みcommit・SHA-256・インストール結果はExperimental / Alpha prereleaseの説明で確認してください。全仕様の正本と現在の証明範囲・制限は `PRODUCT_SPEC.md` と `docs/VAPB_CURRENT_STATE_TO_COMPLETION_REPORT.md` を参照してください。private/commercialアセットは同梱しません。


## 支援 / Support

### 日本語

VAPBは無料のオープンソースとして開発しています。役に立った場合は、[GitHub Sponsors](https://github.com/sponsors/UkkyaGuiyo) から任意で開発を支援できます。支援は開発・検証環境の維持に使用します。支援の有無や金額によって、機能、個別サポート、開発優先順位が変わることはありません。

### English

VAPB is developed as free and open-source software. If VAPB is useful to you, you can optionally support development through [GitHub Sponsors](https://github.com/sponsors/UkkyaGuiyo). Sponsorship helps maintain the development and validation environment. Sponsorship status or amount does not grant feature access, individual support, or development priority.

## 開発について / Development

### 日本語

VAPBは個人開発のオープンソースプロジェクトです。設計、実装、テスト、デバッグ、調査、文書化に **OpenAI ChatGPT および Codex** を積極的に使用しています。

製品の目的、仕様、優先順位、受入条件、ライセンス判断、公開判断などの最終決定は人間が行います。AIが生成・提案したコードや変更は、それだけを理由に正しいものとして扱わず、自動テスト、Blender / Unityの統合テスト、公開synthetic fixture、利用可能なprivate実UnityPackageでの回帰検証などを通して確認します。

このREADMEやGit履歴には、AIを利用した開発であることを隠さず記載します。同時に、AIを使用したこと自体を品質保証とはせず、**何が実装済みか、何が実際に検証済みか、何が未確認か**を区別して記録することを方針としています。

### English

VAPB is an individually developed open-source project built with extensive use of **OpenAI ChatGPT and Codex** for architecture, implementation, testing, debugging, research, and documentation.

Human judgment remains authoritative for product goals, specifications, priorities, acceptance criteria, licensing decisions, publication decisions, and other final decisions. Code and changes generated or proposed with AI assistance are not considered correct merely because they were AI-generated; they are validated through automated tests, Blender / Unity integration tests, public synthetic fixtures, and regression testing with available private real-world UnityPackages where appropriate.

This README and the Git history intentionally disclose the use of AI in development. At the same time, AI assistance is not treated as a quality guarantee: the project explicitly distinguishes **what is implemented, what has actually been verified, and what remains unverified**.

### 既存骨Skinの限定往復

直接PrefabのSkinnedMeshRendererを **VAPB → Renderer対応** で確認し、Skinの骨対応を読み込み、各Unity骨の対応先をArmatureのBone選択欄で明示確認します。対応を保存した後、Meshの頂点・面・ウェイトを編集し、上記UnityPackage出力とUnity確認画面からの適用を使用します。対応は名前と独立した保存IDで保持され、改名と.blend保存・再読込を検証済みです。

この経路は元Unity骨階層・rest・名前と元FBXを保持します。Blender側の骨改名は対応を壊しませんが、Unity骨の改名としては出力しません。新規骨、Nested、未対応Componentや外部依存は未対応として停止します。2骨のsyntheticで頂点構成・ウェイト変更とUnityでの変形を検証済みですが、実Avatarの全面対応はまだ主張しません。

### モデル由来Skinの複数選択出力

同じPackage・同じPrefab個体に属するモデル由来Skinを複数選択し、**File → Export → VAPB UnityPackage（Mesh / Skin）** の「出力対象」を **選択Mesh** にします。出力Mesh数を確認し、Unityの作業用ProjectへImportし、コンパイル完了後にVAPB確認画面から適用します。全対象の出所・骨対応を確認してから、一つのPrefab Variantへまとめて反映します。二件目が不正でも、一件目だけ反映されたVariantは作りません。

元Prefab・FBX・骨階層・素材と対象外の構造を保持します。複数Prefab個体の混在、静的Meshとの混在、手動Bone対応を確定した従来経路の複数Meshは現在停止します。一つだけ出力する場合は **アクティブMeshのみ** を選べます。

### Cleanup / Bone Merge の手動操作

- **Nキー → VAPB → Semantic Cleanup**: Mesh / Armatureを選択して候補を解析し、保持理由を確認してから削除します。Undoで戻せます。未解決のUnity/VRC state、Animation、Envelope、外部参照、共有データは保護します。現時点の削除対象は未使用Material枠と、参照を確認できた末端Boneです。Material datablock全体の一括削除は行いません。
- **File → Export → FBX + Unity Material Map**: 「出力のみ」のCleanupを個別に選べます。出力用コピーだけを整理し、編集中のsceneを維持します。このFBX出力と、上記のUnityPackage出力は別の入口です。
- **Nキー → VAPB → Bone Merge**: 基準Aと対象Bを選び、候補を取得します。各BoneについてA側への対応またはB固有Boneとしての保持を明示確認し、解析後に実行します。移植先のrest / pose、Meshの変形、Bone親参照を検証し、失敗時は戻します。Bは保持し、Weight Transferは別操作です。
- Bone Mergeの不明なUnity/VRC参照、Animation、Constraint、特殊なBone設定、共有データ、名前衝突、多対一対応は現在保護して停止します。これらを含む全面的な統合・Unity復元は引き続き実装中です。
  同等BoneのDeform（変形に使う）設定がA/Bで違う場合も、付け替え前に停止します。A/BのBone設定と対応を確認して再解析してください。

同等 Bone の親が確定 mapping と一致しない場合は、Mesh の付け替え前に停止します。A/B の親階層と対応を確認して再解析してください。親の自動変更は行いません。

Bone Merge は、親なし Empty の単一 Copy Location（World→World、head 指定）も確定 Bone mapping で付け替えます。プレビューと結果に Constraint 件数を表示し、位置が変わる場合は rollback します。Local 空間・tail・不明 Bone・他形式の Constraint、Animation、Unity/VRC 参照はこの限定経路の対象外です。

Bone Merge は、A に既存 animation がなく、全 Bone の同等/B 固有対応が確定し、標準継承設定の場合、B の単一 slot/layer/strip の Transform Action（location・Scale・現在の回転モードに対応する回転） をコピーして A に付け替えます。B 固有 Bone の回転モードも移植し、移植後の実 RNA path を確認します。原本 B の Action は保持します。現在 Pose/Rest の一致は従来どおり必要です。Object channel、Driver、NLA、非アクティブな回転 channel、Unity Animator/Expressions はこの経路では未対応です。プレビューと結果にコピー件数を表示し、Undo/Redo に対応します。

### UnityPackage書き出し：直接Prefabの静的Mesh

1. PackageをPrefab再構築モードで取り込み、**VAPB → Renderer対応** でRendererとnative Meshの対応を確定します。
2. 対象Meshの頂点・面や素材割当を編集し、そのMeshをアクティブにします。
3. **File → Export → VAPB UnityPackage（Mesh / Skin）** を選び、新しい出力名を指定します。
4. Unityの作業用Projectへ生成PackageをImportします。コンパイル完了後、VAPB確認画面で内容を確認し、**適用** を押します。

この経路は、元FBXにMeshが一つあり、直接Prefabの一つのMeshRendererだけが参照する場合の形状・素材割当が対象です。元PrefabのTransformとUnity Material/Shader設定は保持します。Shape Key、Modifier、Skin、Nested Prefab、追加のモデル参照、欠落依存、未対応serialized stateがある場合は停止します。GUIで未対応と表示される範囲を、VRCアバター全体の往復対応と解釈しないでください。

編集Sceneとは別の一時Sceneで書き出し、元のPackageと保存済みRAWは変更しません。出力には元Package資産を保守的に全件含め、続きの論理モデルのGUID・meta・Importer設定を維持します。新しいShaderをBlender Nodesから生成する機能ではありません。既存出力ファイルは上書きせず、出力失敗時に半端なPackageを公開しません。

Unity側は元PrefabのGUID/signed local fileIDと、FBXへ明示的に書いた実体識別情報を照合します。名前による再結合はしません。出力FBXのhashや元Prefabのrevisionが変わった場合、未保存のPrefab編集がある場合、対象が一意でない場合は復元を停止します。成功後の再実行は同じ結果になります。元PrefabやShaderの異なる版を含む既存Projectへの上書きImportは、この新規Projectでの検証範囲外です。

## インストール

1. `unitypackage_blender_importer.zip` を用意する。
2. Blenderで **編集 → プリファレンス → アドオン → インストール…** を開く。
3. ZIPを選択してインストールし、**Unity Package / VRChat Avatar Importer** を有効化する。

ZIPは、アドオンフォルダ `unitypackage_blender_importer/` がZIP直下に入った構成です。

## 使用方法

1. **File → Import → Unity Package / VRChat Avatar (.unitypackage)** を選ぶ。
2. `.unitypackage` を選択する。

または、Windows Explorerから`.unitypackage`をBlenderの3D Viewportへドラッグ＆ドロップできます。Drag & DropはFile > Importと同じ`import_scene.unitypackage`経路へ渡されます。Top-level importでは同一フォルダのSibling Discoveryも自動実行され、事前にcheckboxを有効化する必要はありません。GUIDが一意に連鎖する`COMPLETE`ではForeground UIにImport Together / Import Selected Only / Cancelを表示し、Backgroundでは決定論的にImport Togetherします。`PARTIAL`でもForeground UIで明示的にImport Togetherを選択できますが、既定値はPrimary Onlyです。`AMBIGUOUS`は安全のため自動選択しません。
3. 複数のPrefabがある場合、既定の **Automatic (Recommended)** はPackage全体をRenderer構造とvisual dependency closureでmetadata-first解析します。互換するBody variant、衣装、アクセサリーは一つに絞らず、編集可能なComposition memberとして同時に取り込みます。同じFBX/skeleton representationは一度だけ読み込み、共有データとして再利用します。視覚を持たないhelperはidentity・anchor関係のメタデータだけを保持します。Providerが曖昧、または同一identityの構造解釈が競合する場合だけ候補Chooserを表示します。AutomaticはPrefab配列順・ファイル名・archive順を選択根拠にしません。詳細は`docs/PACKAGE_COMPOSITION.md`を参照してください。
4. **Reconstruct Prefab** または **Import Raw FBX** と各オプションを確認して実行する。

取り込み時にはUnityPackageの原bytesを **原本の保管先** に保存します。空欄ではBlenderユーザーデータ内の `vapb/sources/` を使用し、内容のSHA-256ごとに一つ保存します。一時展開を削除してもこの原本は残り、.blend内のPackage台帳に保管先を記録します。容量が必要なため、別ドライブを使う場合は取り込み時に保管先を指定してください。別PCへ移すときは.blendだけでなく保管先も保全してください。既存原本の内容が壊れている場合は上書きせず停止します。

### Import後に白い部分や未解決の項目がある場合

3Dビューで **Nキー → VAPB Result → Import結果** を開いてください。Import時に一部を安全に復元できなかった場合は警告も表示します。この一覧はPrefab/Rendererの解析記録と依存関係の結果から作られ、`.blend`を保存して開き直しても確認できます。件数は証拠記録の数であり、白いMeshの数ではありません。Material/Texture不足、対応するMeshを証明できない状態、候補が複数ある状態を分けて表示します。対象Objectを証拠から確定できない項目はObject選択を提示しません。

`Import結果` が未解決なしでも、Avatar全体の再現やUnityへの往復成功を保証するものではありません。白い見た目だけで問題を断定しません。Materialを手で割り当てた見た目上の変更も、Unity上のRenderer identityが確定したことにはなりません。通常のImportにUnityやwitnessは不要です。特定のbinaryモデルで対応証拠が足りない場合のみ、同一revision用のmodel witnessが役立つ可能性があります。現行のwitness生成は開発者向け手順で、アドオン内に一般ユーザー用の生成ボタンはありません。

### Rendererとskinの明示的な対応確認

取り込んだPrefabの意味上のObject（Empty等）と、FBX由来のskin Meshは別の対象です。自動対応の根拠がない場合は、3Dビューの **VAPB → Renderer対応** でPrefabルートと実際のMeshを選び、対象Rendererの **このRendererを確定** を押して確認します。

対応先は同じ取り込み個体・元FBX・原本ハッシュを持つObjectに限定します。名前だけで確定しません。曖昧なObject複製、対応不明の素材、別個体や版の混在は停止します。共有Meshに素材スロットを追加する必要がある場合は、Blenderで対象Meshを明示的にシングルユーザー化してから再実行してください。素材割当はObjectごとに保持し、対応は.blend保存・再読込後とFBX出力前に再検証します。

現時点で実機検証したのは、PrefabにRendererが直接serializedされている合成入力です。Nested Prefabの参照経路は解析しますが、その全所有Objectの実体化やbinaryモデル内の全Rendererの自動対応は未完成です。ユーザー確認済み対応は、自動判別による対応と区別して記録します。FBX sidecarは対応根拠を保持しますが、Unityでの自動復元までの全面成功を意味しません。

### 任意のUnity Model Witness

通常のImportではUnity Editorは不要です。UnityPackageだけでRendererとnative Meshを一意に結べない場合は、Import画面の **Unity Model Witness (optional)** に、同じUnityPackage・FBX・`.meta` revisionから生成したJSONを指定できます。VAPBはPackage SHA-256、FBX SHA-256、`.meta` SHA-256、Unity-generated GUID/signed local fileID、FBX Model/Geometry UIDを照合し、合わなければ使用を拒否します。対応候補が一意でない場合もMaterialを推測で割り当てません。

開発用の生成経路は、repo内の `tests/blender_fbx_source_witness.py` と `tests/unity_bone_witness_probe` を使い、隔離したUnity 2022.3.22f1 Projectで元モデルとnoop/marker付きFBXをpublic APIで照合した後、Blender backgroundから `tools/build_model_identity_witness.py` に元UnityPackage・probe結果・出力先を渡します。商用Assetのprobe結果とsidecarはrepo外に保存してください。witnessが提供するのはUnity-generated subasset IDとnative FBX実体の橋渡しだけです。Material参照とPrefab overrideはUnityPackageのserialized dataから読み、元モデルのMaterial slot内容など未証明部分は保留します。実Avatar全体のHierarchy、Export、Unity/VRC復元の完成を意味しません。

分割Packageのbinaryモデルでは、元FBXにMaterial slotがあっても、Packageの`.meta`に外部Material remapや生成subasset IDの対応がない場合があります。この場合、Material名・並び・候補数から自動割当しません。上記model witnessを指定しても元モデルのMaterial基本slotまで証明するものではなく、白いslotが残ることがあります。Blenderで一時的にMaterialを手動変更できても、それだけでVAPBのidentityやUnityへの復元が証明されたとは扱わないでください。確認済みの範囲と現行の制限は[Case Bの公開安全な調査記録](docs/CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md)を参照してください。

### 手動ウェイト転送

3Dビューのサイドバー（Nキー）→ **VAPB → Weight Transfer** を開きます。

1. 元メッシュA、Aの参照アーマチュア、転送先メッシュBを指定します。ポーズ・モディファイア適用後ではなく、元メッシュのワールド座標表面を使用します。
2. **A の骨グループを読み込む** を押し、B側のグループ名を確認して必要な対応にチェックします。同名は候補であり自動確定されません。A/アーマチュア/Bを変更すると対応を解除します。
3. Bの全頂点または選択頂点、最大距離、適用率とモードを選びます。置換は補間値へ、大きい値を保持は既存値と補間値の最大へ、未設定のみ補充は既存値がほぼゼロ（1e-8以下）の箇所だけへ適用します。
4. **転送をプレビュー** で予定件数を確認します。**距離超過・未解決頂点を選択表示** はBだけを編集モードにして該当頂点を表示します。実行前にはオブジェクトモードへ戻してください。
5. **B にウェイトを適用** で実行します。通常のUndoで取り消せます。適用途中の例外では変更済みウェイトと新規グループを復旧します。

未指定グループ、ロック済みウェイト、距離超過頂点は変更しません。BのMeshやObjectが他個体・他sceneと共有されている場合は処理を止め、明示的な独立化を求めます。ウェイト合計の自動正規化・影響数の切捨て、Bone統合、Armature付替えは行いません。転送後は実際のポーズで変形を確認してください。左右の注意領域を調べる場合は「宣言した左右境界で越境を保護」を有効にし、Aの参照ArmatureのローカルX=0を境界として指定します。反対側への近傍転送は保護され、距離超過と併せて選択表示できます。これはユーザーが宣言した平面の検査であり、解剖学的な左右の自動認識ではありません。

### FBX + Material Mapの補助出力

この出力は補助的なFBX連携です。上記のUnityPackage出力／確認画面／別Variant復帰の代わりにはなりません。

1. Avatar、衣装、Armatureを必要な範囲で選択する。
2. **File → Export → FBX + Unity Material Map (.fbx)** を選ぶ。
3. **Selected Objects Only** を確認し、FBXの出力先と名前を指定する。
4. 次の2ファイルが同じフォルダへ出力される。
   - `Avatar.fbx`
   - `Avatar.materialmap.json`

このExportはBlender標準のFBX Exporterを使い、Mesh、Armature、Bone、Weight、Shape Key、UV、Normal、Material Slotを可能な範囲で維持します。Shape Keyを壊しやすいモディファイア適用は既定で行いません。

既定では抽出フォルダを保持します。これは、Blenderの画像テクスチャの外部パスを維持するためです。抽出先はWindowsの一時フォルダに作られ、シーンの `unitypackage_extracted_root` カスタムプロパティに記録されます。

## Importの性能と進捗

- 複数Prefabの選択ダイアログが表示された場合も、選択前に行ったUnityPackageの展開、AssetDatabase構築、`.meta`走査、FBX/Prefab列挙を同じImport操作内で再利用します。選択されたファイルの絶対パス、サイズ、更新時刻、内容SHA-256のいずれかが変わった場合はキャッシュを破棄して作り直します。
- 通常のBlender UIでは、UnityPackageの展開とAssetDatabase準備を純Pythonのバックグラウンドワーカーで行い、Blender APIを使うFBX/Material/Prefab処理だけをメインスレッドで実行します。準備中も進捗フェーズを更新でき、キャンセル時は展開途中の一時フォルダを後始末します。Blenderのバックグラウンド起動時は同期経路を使います。
- AssetDatabaseは展開時に拡張子別の索引を作るため、FBX、Prefab、Material、Textureの列挙で展開ツリー全体を繰り返し走査しません。`.meta`の不足GUID走査は準備段階に1回だけ行います。
- 各展開パスはアーカイブの物理順をストリーム走査し、asset本文を固定チャンクでコピーします。通常のPrefab再構築では、選択Prefabから辿れるFBX、Material、Textureと各`.meta`だけを最終展開し、無関係なasset本文は書き出しません。複数Prefabの選択肢を先に表示し、選択確定後に依存展開を行います。
- `Keep Extracted Files` を有効にした場合も、保持されるのは選択された依存アセットの展開先です。パッケージ全体のミラーではありません。依存関係を解決できない場合は、既存互換性を優先してFBX全体へフォールバックします。
- Import中はBlenderの進捗表示とフェーズ名を更新し、コンソールへ低負荷の `[PERF]` フェーズ計測を出力します。展開、FBX、Material、Texture、Prefab復元などの所要時間を後から確認できます。
- Foreground importはStatus Barに、実際のstage名、既知のcurrent/total、current item、経過時間を表示します。Prefab候補とprovider走査は実際に処理した件数だけを表示し、未知の所要時間を偽のパーセントで補間しません。
- Native FBX importの直前には`Importing FBX`と`Blender may temporarily stop responding during this step.`を表示します。FBXのようなBlender APIのblocking operation中はUI再描画が一時停止することがありますが、進捗stateと構造化ログは保持されます。成功・失敗時はStatus Barを消去します。
- キャンセル、エラー、Prefab選択の中断では準備済みの一時展開先を後始末します。`Keep Extracted Files` を有効にして正常完了した場合だけ、テクスチャの外部パス維持のため展開先を保持します。
- Prefab Candidate Analyzerは、Prefabごとに構造分類し、Material→TextureとFBX externalObjectsを含むvisual closureをComposition単位で判定します。候補解析中にFBXまたはTexture payloadを読み込まず、同一Packageのindexとtextual Material readを共有します。明示的なPrefab指定時だけ単一member相当へ絞り込みます。

## 対応範囲

- UnityPackage (`tar.gz`) の `pathname` に基づく `Assets/...` 復元
- `../`、絶対パス、NUL文字を拒否する安全な展開
- FBXの検出とBlender標準FBX Import APIによる読み込み
- FBXに含まれるArmature、Bone、Vertex Group、ウェイト、Shape Key、UV、Custom Normalsの保持をBlender標準処理に委譲
- PNG / JPG / JPEG / TGA / BMP / TIFF / EXR / PSDの展開。対応形式はBlenderで画像として読み込み
- Unity `.mat` のMaterial Name / Material GUID / Asset Path / Shader Name / Shader GUIDの保持
- `.mat`を正規化してからBlenderノードへ変換するシェーダープロファイル方式
- lilToon、Unity Standard、Poiyomi、MToon、VRChat Mobile / Quest系Shaderの識別とbest-effort変換
- Base Color、Base Color Texture、Normal Map、Emission、Metallic、Smoothness/Roughness、Alpha / CutoutのPrincipled BSDF近似
- Texture GUID優先の参照、TextureのUV Scale / Offset、Unity Materialの未使用Propertyと正規化結果の保存
- Unity YAML PrefabのGameObject、Transform、MeshRenderer、SkinnedMeshRenderer、MeshFilterの参照を部分的に解析
- Prefabの親子関係、位置、回転、スケールの可能な範囲での復元
- 日本語を含むWindowsパス

## Materialプロファイルの扱い

Shaderコードを実行したりUnityの描画結果を再現したりするのではなく、`.mat`に保存されたPropertyを共通の正規化モデルへ変換してからBlenderのPrincipled BSDFへ接続します。未知Shaderでも既知のTexture、Color、Normal、Emission、Alphaを一般規則で復元し、判定できなかったPropertyは`unity_props`に残します。

- lilToon: Main Texture / Color、Normal、Emission、Alpha / Cutoutを再現し、Shadow、Rim、MatCap、Outlineはメタデータとして保持
- Unity Standard: Main Texture、Color、Metallic、GlossinessからMetallic / Roughnessを復元し、Cutout / Blendを反映
- Poiyomi / MToon: 共通の見た目要素を復元し、toon、Shadow、Rim、Outline等の識別情報を保持
- VRChat Mobile / Quest: Toon Lit、Standard Lite、Toon Standard系のPropertyを識別し、軽量向けの共通要素を復元

Blender側のMaterialには、`unity_material_guid`、`unity_material_path`、`unity_material_name`、`unity_shader_guid`、`unity_shader_name`、`unity_shader_family`、`unity_props`、`unity_normalized`を保存します。同名MaterialでもGUIDが異なる場合は別Materialとして生成します。FBX `.meta`の`externalObjects`がある場合は、名前検索より先にGUIDでMaterial Slotを解決します。

## materialmap.json

Manifestは`schema_version: 1`のJSONです。`materials`にExportされたMaterial名と元Unity MaterialのGUID、Asset Path、Name、Shader GUID / Nameを記録し、`bindings`にObject階層パス、Renderer相当、Material Slot index、Material keyを記録します。同じMaterialを複数Slotで使う場合は同じMaterial keyを参照します。

Unity側で元の`.mat`を再利用するため、PropertyをJSONから再生成しません。元`.mat`をそのまま検索し、FBX ImporterのMaterial remapへ登録します。

## Unity Restore Tool

`unity_editor/Editor/UnityPackageBlenderMaterialRestore.cs`をUnity Projectの`Assets/Editor/`へコピーします。VRChat SDKは必要ありません。

1. `Avatar.fbx`と`Avatar.materialmap.json`をUnity Projectの`Assets/`内へコピーする。
2. UnityでFBXのImportが完了するまで待つ。
3. ProjectビューでFBXを選択する。
4. **Tools → UnityPackage Blender → Restore Selected FBX Material Map** を実行する。

選択したFBX以外を指定する場合は、同じメニューの **Restore FBX Material Map...** を使います。処理は手動方式です。AssetPostprocessorによる自動Restoreは、再Importループを避けるため実装していません。

Material検索は次の順序です。

1. `unity_material_guid`
2. `unity_material_path`
3. `unity_material_name`（候補が1件だけの場合）

GUIDが見つからない場合はPathへ進み、Pathも失敗した場合だけNameを使います。同名Materialが複数ある場合は警告して未解決のままにし、勝手に別Materialを割り当てません。見つからないSlotがあっても、他のSlotの処理は継続します。Restoreを繰り返しても元`.mat`の複製・上書きは行わず、既存のMaterial remapを更新します。

## 現在の未対応範囲

PhysBoneの完全再現・Unityへの自動restore、Contact、Animator Controller、Expressions、Modular Avatar、NDMF、lilToon/Poiyomiの完全再現、AudioLink、Unity Constraint、MonoBehaviour/C#実行、Prefab Variantの完全互換は現在未対応です。最終的に必要な保存・復元範囲は `PRODUCT_SPEC.md` が正本であり、この一覧で縮小しません。PhysBone/Colliderのserialized source captureと限定的な近似preview prototypeは保存データを書き換えずに提供します。

Imported scenes expose the approximate preview at `3D View → N → VAPB → Physics Preview`. Enable/Disable and Reset use only identity-matched chains and run from a Blender main-thread timer; unmatched chains are skipped and reported.

## Editable Texture Workflow

## Visual Dependency Discovery

Texture properties use one canonical role classifier for initial material build and late binding: `_MainTex`/`_BaseMap`/`_BaseColorMap` are Base Color and `_BumpMap`/`_NormalMap` are Normal. Emission, Metallic, Roughness, and Occlusion remain explicit roles; unknown properties are preserve-only metadata and are never substituted into Base Color.

Sibling discovery is metadata-first and bounded. It reads pathname, `.meta`, selected prefab/material text, and FBX external-object metadata, while texture and FBX payload bytes remain unread during planning. It starts in the selected package folder and expands only to the immediate bundle parent and one-level child folders when visual GUIDs remain unresolved. `visual_status` is independent from nonvisual Unity dependency state; ambiguous providers are never auto-selected.

When visual dependencies remain unresolved, the foreground flow opens `Missing Visual Dependencies`. A user may locate one UnityPackage or an explicitly granted folder; candidates are accepted only when their manifest GUIDs cover unresolved visual references. Zero-coverage packages are rejected, ambiguous folder results are not auto-selected, and accepted providers trigger the same resolver/late-binding path as automatic discovery. `Continue With Missing Assets` preserves unresolved records while importing everything already resolved.

During a foreground import from the 3D View, a large centered `LOADING` overlay appears above the viewport. It keeps the existing bottom status bar as secondary diagnostics, shows the current stage/item and elapsed time when known, and changes its copy before native FBX work so users know to wait while Blender may temporarily stop responding. The overlay is non-modal, has no cancel control, and is removed on both successful and failed terminal cleanup.

Select an imported image in the Image Editor and open the `Unity Texture` sidebar. It displays Unity Asset Path, Unity GUID, working file path, file existence, and dirty state. `Save to Unity Source` writes Blender edits to that same existing file; `Reload from Disk` refreshes the same Image datablock after an external editor change; `Reload Changed Unity Textures` performs a manual mtime scan.

The workflow refuses missing files, dirty reloads, ordinary non-Unity images, and packed-source conflicts. It never creates a copy, backup, new GUID, or `.meta`; use the importer `Keep Extracted` option for editable source files.

`Open in External Editor` opens the first-time editor selection menu, then launches the saved editor directly on later uses. `Change External Editor` or the menu allows a detected editor or `Browse for executable...`; the path/name is stored in Blender Add-on Preferences. The launcher passes the existing working texture as a separate argument, never uses `shell=True`, and does not watch or automatically reload the file.

If the operating system refuses the launch after validation, the launcher returns `EDITOR_LAUNCH_FAILED` and the Blender operator reports an error without exposing a traceback.

## Current Limitations

Native FBX model transforms and skin parenting are preserved during Prefab
reconstruction. Converted scene-only ancestors place the model exactly once;
serialized transforms on matched FBX objects are retained as
`unity_prefab_model_transform` metadata, not reapplied as another model-axis
conversion. Genuine transform/reparenting overrides on those model objects
remain unsupported without reliable source/default comparison. Put explicit
scene placement on a scene-only parent instead.

Uniquely and structurally corresponding Prefab bone GameObjects are represented
by native Bone identity properties and root `unity_prefab_bone_identities`
metadata rather than duplicate Empty objects. Bones needed as Object parents
for separate scene attachments retain their Empty representation.

- Transparent / cutout / blend material visual pathは未検証です。
- Unity Shaderの外観はBlender Principled BSDFによる近似です。
- Multi-package identity foundationは実装済みです。異なるPackageの同一GUID/Asset Pathは検出・報告しますが、自動merge・自動置換は行いません。
- UnityPackage exporterは未完成です。
- File Browser cancel/re-run、任意Prefab手動選択、通常UI Undo-keyは未確認です。

- Unityの座標系とFBXインポーターの変換差により、特殊なPrefabや複数の変換階層では位置・回転に微調整が必要な場合があります。
- PrefabのMesh/Material参照は、Unity YAMLの外部GUID参照が取得できる場合に優先して使います。サブアセットや複雑なPrefab VariantはFBX全体の読み込みへフォールバックします。
- lilToon、Poiyomi、MToon、VRChat Mobileの完全なShader互換、Shadow/Rim/MatCap/Outlineの完全な描画再現は対象外です。これらは共通要素をPrincipled BSDFへ近似し、未接続の固有情報をメタデータへ残します。
- UnityPackageに壊れたアセットが含まれる場合、失敗したファイルをコンソールへ警告して、読み込めるFBXの処理を継続します。
- Blender実機でのFBXファイルそのものを用いた形状確認は、パッケージに含まれるFBXの内容に依存します。付属テストは展開、パス検証、列挙、Prefab YAML解析とBlenderアドオン有効化を対象にします。
- Unity側のMaterial RestoreはFBX内のExported Material名がmanifest生成後に変更されていないことを前提にします。別ツールでMaterial名を変更した場合はSlotを特定できません。
- Unity側Restoreは元`.mat`のGUIDを変更せず、Unity EditorのAssetImporter remapへ参照を登録します。実際のShader表示は、対象Projectに元Shaderと元`.mat`が存在する場合に限られます。
-
### Multi-Package Material / Texture Binding

複数UnityPackageを同一Sceneへ順次importする場合も、Material、Texture、Prefab Renderer slotはPackage identityを境界に解決します。同名や同一filenameは自動mergeせず、Prefab Object名がBlenderの`.###`重複suffixで変化した場合は一意なbase名だけを安全にfallbackします。

### UnityPackage Exporter（実装中）

直接Prefabの静的Meshと既存骨Skinの限定往復経路を実装しています。全Compositionのreachability、Nested Prefab、複数PackageやVRC stateを含む全面的な往復は実装中です。
### Cross-Package Dependencies

Geometry-only、Material-only、Texture-onlyのUnityPackageを同一Sceneへ順次importできます。Prefab Renderer→Material、Material→TextureはPackage-scoped GUIDを正本にScene-wide resolverでlate bindし、未解決・曖昧参照は`unitypackage_dependency_registry`へ保存します。静的Mesh向けExporter/Unity Finalizerは上記の限定範囲に対応します。Skin・複数Packageの全面的な往復は未完成です。

## ライセンスと開発の正本

通常開発の正本は [UkkyaGuiyo/vapb](https://github.com/UkkyaGuiyo/vapb) です。Blender Add-on/Python は **GPL-3.0-or-later**、独立した `unity_editor/` の C# helper は **MIT** です。適用範囲・出自・外部ソフトウェアとの境界は [LICENSES.md](LICENSES.md) を参照してください。入力アセット自体の権利条件は変更しません。

旧 private repository の全履歴は保持し、こちらには個人パス・実Asset識別情報を取り除いて再構成した履歴を収録します。`archive/` のブランチは開発過程の保存用であり、現行の対応範囲や配布推奨版を示しません。履歴の古いローカル検証スクリプトは環境変数で入力を指定する必要があります。詳細は [公開履歴の移行記録](docs/PUBLIC_HISTORY_MIGRATION.md) を参照してください。
