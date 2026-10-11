# VRChat: Avatar・SDK・clientとWorld機能索引

対象: 2026-10-11 UTC取得の公式Creation docs、SDK最新掲載3.10.5。Unity対応版は2022.3.22f1 [V01–V03]。個別pageの説明は最新版SDKの全fieldを網羅したschemaではない。

## Descriptorと対応component

**DOC [V04、V09、V11]**: Avatar Descriptorはview position・lip sync等を設定し、Expressions MenuとExpression Parametersを参照する。単にMesh/Armatureを復元するだけではAvatar設定を復元したことにならない。

Allowed Avatar ComponentsはVRChat componentとUnity componentの対応範囲を列挙する。任意custom scriptは実clientで動く保証がなくuploadを阻む場合もある。Cameraにもlocal/remoteや表示permissionに応じた除去・disable条件がある。Androidには追加制限 [V16]。

**INFERENCE**: VAPBが未知scriptのserialized dataを保持できても、SDK validation/client実行の成功を保証しない。欠けたscriptのfield schemaを名前やGUIDだけで合成しない。元Descriptor・component・asset参照の保持と、編集Meshへのbindingを別々に判定する。

## PhysBoneとCollider

**DOC [V05]**: component versionを選択し、既存PhysBoneは手動更新と再uploadまで以前のversionを使う。Root Transform空欄はそのGameObjectから開始。Ignore Transforms、endpoint、chain設定を持つ。単componentの対象transform上限は256。avatarの設定propertyをanimationで変更する回避法はサポートされない説明。

Colliderにはroot、shape、offset、global collision/filterがあり、PhysBoneのcollider listやpermissionにも依存する。Sphere/Capsule/Planeと、global対応条件を分ける。PhysBone root空欄の規則をUnity SkinnedMeshRendererのnull bone/rootBoneへ流用しない。

**INFERENCE**: Blenderのpreviewで揺れたこと、rest matrixが一致したことはVRC PhysBone solver/client interactionの同等性とは別。参照bone identity、component version、curve、root/ignore/collider、アニメーションとの作用が確認対象。今回simulationを実装・再開しない。

## ContactsとConstraints

**DOC [V06]**: ContactはUnity Colliderとは別のSender/Receiver系。root/shape/offsetに加え、collision tagsはcase-sensitiveで、双方に一致tagが必要。avatarではparameter、worldではUdon event等の経路を使う。設定値の保存だけで他clientとのinteractionは証明されない。

**DOC [V07]**: VRC ConstraintはAim/LookAt/Parent/Position/Rotation/Scaleを提供する。AvatarのUnity Constraintは**ゲーム内ロード時**にVRC Constraintへ変換される説明。これをupload時変換と記載しない。Target Transform、local/world solve、freeze、offset、source weightsの意味を区別する。対象Transform参照をanimationで変えることには制限がある。

**INFERENCE**: Blender constraintへの近似置換は公開APIからの同等性証明ではない。保存されたreference graph、評価順、space、offsetとclientでの結果を分ける。

## Animator、Expressions、parameters

**DOC [V08]**: Base/Additive/Gesture/Actionは主にTransform animation、FXはMaterial/Shader/Blendshape等を扱う。Playable LayersはAnimation Controllersを使う。各layerはclientでcombined Animatorへまとめられる。非Transform animationを他layerへ置くとmirror cloneへのcopy範囲が異なる。

**DOC [V09–V10]**: MenuとParametersは別assetで、Descriptorへ割当する。Menuは1menuに8 controls、parameterにはtype/default/Saved/Syncedがある。同期custom parametersは最大256 bits（int/float各8、bool1）、synced/unsynced総数は8192、built-inは別。int範囲0–255、float -1–1。local floatとnetwork量子化は別。

Cross-platform syncはparameter**順序と型**で対応し、名前一致だけではない。Playable/IK/Speech/Noneなどのsync categoryも別。Clipを本人GUIで割当した結果を、Controller state・mask・layer・Expressions・remote syncまで完了したと解釈しない。

## Build/uploadと公開SDK API

**DOC/API [V12–V13]**: Public SDK API folderまたはPublicAPI attributeで明示されたものと、SDK内部を区別する。公式は安定化へ努力するが将来変更可能で、semverによる対応範囲を勧める。reflectionで内部へアクセスできることは安定契約ではない。

IEditorOnlyはSDK validationでEditor-only scriptを扱う仕組み。IPreprocessCallbackBehaviourやbuild requested callbackはbuild前にmodificationやabortを行う。callbackが存在することから、全asset/componentの保存・upload時変換の網羅は証明できない。

**REL [V03]**: 3.10.5 changelogにはbuilt assetのduplicate PipelineManager検査、PhysBone/Contactsのdomain reload修正、Constraint inspector修正等がある。旧版と同じだと一律に扱わない。SDK packageの全source・DLL・native client実装は今回取得していない。

**UNKNOWN**: SDK内全build processorの順序、プラットフォーム別strip・bake、非公開client変換全体、server側変換、runtime frame orderは今回網羅未調査/未公開。Editor imported state、SDK build成功、upload成功、client実行成功、複数client一致は別々の証拠。

## World/Udon/同期/音声の公式体系

|分野|公式入口|今回確認した範囲・未調査|
|---|---|---|
|World authoring|V17 / V23|Scene components、layers、SDK prefabs、scripted assets、World allowlist。Avatar用リストと別|
|Udon / UdonSharp / VM / event order / player API|V17、V18の公式navigation|体系を確認。全node・exposed API・UdonSharp言語制約は未調査|
|Networking|V18–V19|ownership、manual/continuous variables、events。synced stateはlate joinへ渡り、eventsは過去の状態を保存しない。全帯域/serialized type/ownership edge caseは未監査|
|Persistence|V20|PlayerData/PlayerObjects等への入口。容量・型・寿命・clear条件の全監査なし|
|Player voice / Avatar Audio|V21|Voice gain/near/far/lowpassとAvatar audio設定は別。音声コーデック・全transport仕様は未調査|
|ClientSim|V22|Unity内World simulationへの入口。実clientやmulti-client検証を代替した証明ではない|
|URL loading / image / video / MIDI / UI / graphics / navigation|V18公式navigation|機能索引。VAPB研究実装の再開を伴わない|

Worldの存在・機能説明はAvatar packageの変換保証に使わない。停止案件のコード、Editor、process、leaseを操作していない。

## 権利・再配布境界

**公式規約 [V24 §8.1–8.4]**: User Contentの権利保持、Platformへ与えるlicense、必要な権利・許諾の責任は区別される。VRCへのuploadを許されたことから購入素材・SDKをGitHubで再配布できるとは導けない。個別素材licenseは今回取得・判定していない。

本branchへ保存するのは自作日本語説明と公開URLのみ。SDK本体、公式source本文、購入素材、私的corpus、個人情報、認証、package、raw logは追加しない。
