# 公式出典索引

確認日（全行）: **2026-10-11 UTC**。`本文` = 原典本文の該当箇所を取得し読んだ、`入口` = 分野への案内のみ、`取得不能` = 未読。DOC/API/REL/SRCは[README](README.md)の分類。

Unity U01–U38とU40–U48はURLに固定された**2022.3系列**。個別patchでの実行結果ではない。Blender SRCは公式GitHub mirrorの**v5.2.1**（ref SHAはVERSIONS）を使用。VRCは**取得日現在の公開Creation文書**であり、ページごとにSDK version条件がある。mutableな公式ページは将来更新される。

## Unity

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|U00|[Unity 6.6 User Manual](https://docs.unity3d.com/Manual/index.html)|DOC/本文・分野入口|latest release表記と機能体系。latest patch番号ではない|
|U01|[Asset Metadata](https://docs.unity3d.com/2022.3/Documentation/Manual/AssetMetadata.html)|DOC/本文|Unique IDs / Meta files。metaは当該assetのidentityとimport settings|
|U02|[TryGetGUIDAndLocalFileIdentifier](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html)|API/本文|Declaration / Warning / Description。long推奨、GUID+fileID、成功bool|
|U03|[GUIDToAssetPath](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.GUIDToAssetPath.html)|API/本文|Returns / Description。project内lookup、逆参照一覧でない|
|U04|[LoadAllAssetsAtPath](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.LoadAllAssetsAtPath.html)|API/本文|Description。hidden subassets、mainはindex 0保証なし|
|U05|[GetDependencies](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.GetDependencies.html)|API/本文|Description / recursive。asset path集合でproperty・faceは返さない|
|U06|[Script serialization](https://docs.unity3d.com/2022.3/Documentation/Manual/script-Serialization.html)|DOC/入口|field、UnityEngine.Object参照、SerializeReference。個別SDK schemaは未調査|
|U07|[Format of Text Serialized files](https://docs.unity3d.com/2022.3/Documentation/Manual/FormatDescription.html)|DOC/本文|document marker / object ID / properties。古いPrefab field例を現行契約へ転用不可|
|U08|[Asset packages](https://docs.unity3d.com/2022.3/Documentation/Manual/AssetPackages.html)|DOC/本文|圧縮ファイル集合・metadata。tar内部schema保証を確認できず|
|U09|[Renderer.sharedMaterials](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Renderer-sharedMaterials.html)|API/本文|Description。array copyとshared objectを区別|
|U10|[Mesh.subMeshCount](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh-subMeshCount.html)|API/本文|Description。Renderer Materialに対応、vertex共有可能|
|U11|[Mesh.GetTriangles](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetTriangles.html)|API/本文|submesh / applyBaseVertex / Description。triangle indices|
|U12|[Mesh data](https://docs.unity3d.com/2022.3/Documentation/Manual/AnatomyofaMesh.html)|DOC/本文|Vertex data / topology / indices。position以外の属性を含む|
|U13|[Mesh Renderer component](https://docs.unity3d.com/2022.3/Documentation/Manual/class-MeshRenderer.html)|DOC/本文|Materials。余剰Materialの最後submeshへの重ね描画|
|U14|[Skinned Mesh Renderer component](https://docs.unity3d.com/2022.3/Documentation/Manual/class-SkinnedMeshRenderer.html)|DOC/本文|Root bone / Materials。boundsとskeleton root、余剰Material|
|U15|[Materials tab](https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Materials.html)|DOC/本文|Use Embedded Materials / Remapped Materials / Naming / Material description（Experimentalあり）|
|U16|[GetExternalObjectMap](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.GetExternalObjectMap.html)|API/本文|subasset→external asset map copy。全FBX graphではない|
|U17|[AddRemap](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetImporter.AddRemap.html)|API/本文|null/型違いはinternal assetを継続、reimportで適用|
|U39|[Unity 6 release support](https://unity.com/releases/unity-6/support)|REL/本文|Latest LTS release / Support。6.3 LTSとUpdateを分ける|

## Blender・版確認

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|B00|[Blender Manual 5.2](https://docs.blender.org/manual/en/5.2/)|DOC/取得不能|機能体系入口。本文を取得できたと扱わない|
|B01|[BKE_blender_version.h / v5.2.1](https://github.com/blender/blender/blob/v5.2.1/source/blender/blenkernel/BKE_blender_version.h)|SRC/本文|BLENDER_VERSION/PATCH/CYCLE/SUFFIX。5.2.1 release LTSを定義、最新順位は保証しない|
|B12|[Download](https://www.blender.org/download/) / [LTS](https://www.blender.org/download/lts/)|REL/取得不能|Web取得は402、API本文直接取得は403。認証等の迂回なし。最新stable/LTS patch不明|

## VRChat・版確認

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|V01|[Current Unity Version](https://creators.vrchat.com/sdk/upgrade/current-unity-version/)|DOC/本文|2022.3.22f1。最新版Unityへ無条件更新しない|
|V02|[VRChat SDK Releases](https://creators.vrchat.com/releases/)|REL/本文|最新掲載3.10.5、2026-09-04。client版ではない|
|V03|[Release 3.10.5](https://creators.vrchat.com/releases/release-3-10-5/)|REL/本文|Summary / Features / Fixes & Changes。domain reload、collider、constraint等の版差分|

## 取得状態の扱い

Unity公式はWeb取得と公開URL本文読取で確認。Blender docs/APIとdownloadの一部は取得不能。公式source mirrorの固定tag本文は取得できたため**SRCとして**使う。VRCの直接HTTP取得は403だったが、この作業のWeb取得サービスでは公式Creation本文を取得できた。これは認証やアクセス設定を変更した結果ではない。本文取得できない頁を引用して詳細を断定しない。

公式issue tracker（Unity: https://issuetracker.unity3d.com/、Blender: https://projects.blender.org/、VRC: https://feedback.vrchat.com/）は不具合照合の入口。今回まだ個別issueを読んでいない。source comment中のissue番号は、issue本文と同一の根拠として扱わない。
