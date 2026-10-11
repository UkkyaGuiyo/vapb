# MaterialとMeshの接続方向、GUID、面対応

対象: Unity 2022.3公式Manual/API。確認日: 2026-10-11 UTC。番号は[SOURCES](SOURCES.md)。一般例は架空の資産で、VAPB素材の同定結果ではない。

## 参照を持つのはどの側か

**DOC/API [U01–U07、U09–U15]**: assetのmetaは当該assetのGUIDとimport設定を持つ。外部assetへのserialized referenceは参照元のpropertyにGUIDとasset内fileIDを持つ。GUIDは対象asset fileを識別し、fileIDはその中のobjectを識別する。Mesh自体に「このMaterialだけを使う」という普遍的な逆向きリンクがあるわけではない。

```text
Example.prefab の Renderer occurrence
  ├─ sharedMaterials[0] ─→ Surface.mat (そのmetaのGUID + MaterialのfileID)
  └─ sharedMesh         ─→ Model.fbx (そのmetaのGUID + Mesh subassetのfileID)
      ※通常MeshRendererのMeshは同じGameObjectのMeshFilter側にある。

Surface.mat
  ├─ shader             ─→ Shader object
  └─ texture property   ─→ Texture object

Model.fbx の ModelImporter
  └─ external remap     ─→ 外部Material等（設定されている場合）

Mesh submesh 0 ─→ vertex index群（面集合）
Renderer slot 0 ─→ Material object
```

図のproperty名は公開APIの概念名。serialized backing field名・fileID数値・GUID値を生成するテンプレートではない。標準componentのtextでは `m_Materials`、`m_Mesh` 等が観測できても、任意SDKや全versionのfield schemaが同じという保証はない。

**INFERENCE**: `Example.prefab` が `Surface.mat` を参照していても、`Surface.mat.meta` に利用Mesh一覧が格納されるとはいえない。同じMaterialを複数Rendererが共有でき、同じMeshを異なるMaterial配列で描画できる。したがって `.mat` やGUIDの存在だけで受け手Object/slot/faceは一意にならない。

## 公式に提供されるlookupと逆引きの範囲

|API [根拠]|提供する情報|提供しない情報|
|---|---|---|
|GUIDToAssetPath [U03]|既にimportされたproject内のGUID→asset path、見つからなければ空文字|そのGUIDを参照するRenderer/面一覧|
|LoadAllAssetsAtPath [U04]|mainとhiddenを含むsubassets（mainがindex 0とは限らない）|配列順によるUnity↔FBX UIDの恒久対応|
|TryGetGUIDAndLocalFileIdentifier [U02]|Unity objectのGUIDと**long** localId、成功bool|raw FBX UIDからの変換式、再import後の不変性|
|GetDependencies(path, recursive) [U05]|指定assetが参照するasset path集合。recursive=trueは自身を含む|reverse dependency graph、参照property、occurrence、slot、face partition|
|GetExternalObjectMap [U16]|importerのsubasset→external assetのremap mapのcopy|元FBXの全接続、Mesh面対応、全Rendererのeffective overrides|

調査した公開APIの範囲には、Material GUIDひとつから全利用Renderer・Mesh faceを返す専用の逆引き契約を確認できなかった。**「Unityのどこにも存在しない」という断言ではない**。既知asset群を列挙し依存を反転する方法はINFERENCEとして可能だが、path集合だけではproperty/slotは復元できない。Editorで実際のRendererを読むこととは別の証拠である。

## Embeddedとexternalは別のidentity

**DOC/API [U15–U17]**: ModelImporterのMaterials tabは埋め込みMaterialをsubassetとして保持できる。Extract / On Demand Remap / Remapped Materialsは外部Materialへ差し替える経路。Remapはimport元subasset識別子から外部objectへの向きで、外部Materialが元モデルを逆参照する必要はない。

**重要な例外 [U17]**: AddRemapでnullまたは異なる型を与えると、instanceは内部assetを使い続け、errorを出さないと説明される。したがってnull remap、空のexternal map、errorがないことを「外部Materialの結合成功」と判定しない。

**INFERENCE**: PrefabがModel.fbxのGUID + Material subasset fileIDを指すなら、その参照先は当該imported asset内。別の `.mat` のGUIDへ向くoverrideがあれば、effective instanceは外部Materialを使うことがある。両者を区別して source chain と occurrence のoverrideを評価する。Material名検索の仕様は実在するが、検索による割当と厳密なidentity証明は別。

raw FBXのMaterial UID / Model UIDと、Unity generated subasset fileIDの同一性や変換式は今回公式資料で確立していない。metaの名前表が空でもimport後objectは存在し得る。source情報欠落時、名前・suffix・順番・外観・候補数だけで両者を結ばない。

## Submeshとslot、native face

**API [U10–U12]**: MeshのsubMeshCountはsubmeshの数。submeshはvertex index群を持ち、通常そのindexに対応するRenderer Materialを使う。GetTriangles(submesh)は3 indexずつのtriangle列、baseVertex補正の有無を指定できる。頂点は複数submeshで共有できる。頂点集合の一致だけではface集合の一致を意味しない。

**DOC [U13–U14]**: Material配列がsubmeshより長いと、残りのMaterialは最後のsubmeshへ重ねて描かれる。従って `slot >= subMeshCount` を一律unusedと呼ばない。配列より多いsubmesh、null slotの最終描画、空submeshなどの全例外は今回runtime未実測。

**API [U09]**: sharedMaterialsはarray copyを返すが、含まれるMaterial objectはshared。Material本体を変更すると他の利用objectやproject assetも変わる。配列要素を変更する場合は配列を設定し直す。読取調査で `.material` による意図しないinstance生成と混同しない。

**INFERENCE**: `[A, null, B, A]` を `[A, B]` へ圧縮するとslot indexの意味が変わり得る。同じMaterialの重複、null、空面slot、余剰描画slotを別々に記録する。Blenderではpolygon.material_indexとObjectのslotを読む必要があり、FBX exporterがslotをremapする実装もある [B03–B04、B10]。名前や配列長だけで往復一致としない。

## Signed localID / fileID 0

**API [U02]**: `int` overloadはoverflowのためobsolete、`long`を使用する。符号付き64-bit型を保持し、非負32-bitに丸めない。APIの型はraw fileの全binary representationを規定するものではない。

**DOC [U07]**: text object IDはfile内で識別される。文書に古いPrefab field名の例も残っているため、例を現行schema生成器へ流用しない。`{fileID: 0}` は原典例にあるが、任意referenceの0を「rootBoneを自動補完せよ」とする公開契約は確認できない。null / missing / intentionally unassignedを区別するため実objectと参照種別の確認が必要。

## 結合に必要な最小証拠

1. 対象Prefab occurrenceとsource chainが一致し、effective Rendererが特定できる。
2. Rendererが指すMeshのGUID/fileID、Materialの各slotのGUID/fileIDが読める。
3. Unity imported submeshの面集合と、編集対象native faceの対応が証明される。三角化・vertex再編成を考慮する。
4. 変更後のFBXをUnityへimportした時のMesh identity、slot順・面集合、Material remapを確認する。

これは仕様から導いた確認条件であり、今回実行したテストではない。sourceが欠けた場合は、元revisionに固定されたEditor public API観測などの追加証拠が必要。元FBX内の接続、Prefab override単体、Material dependencyの存在は、それぞれ部分的証拠として保持し、未証明のjoinを成功扱いしない。
