# 公式出典索引

確認日（全行）: **2026-10-11 UTC**。`本文` = 原典本文の該当箇所を取得し読んだ、`入口` = 分野への案内のみ、`取得不能` = 未読。DOC/API/REL/SRCは[README](README.md)の分類。

Unity U01–U38、U40–U47、U49–U50はURLに固定された**2022.3系列**（U29だけsource固定commit）。個別patchでの実行結果ではない。Blender SRCは公式GitHub mirrorの**v5.2.1**（ref SHAはVERSIONS）を使用。VRCは**取得日現在の公開Creation文書**であり、ページごとにSDK version条件がある。mutableな公式ページは将来更新される。

## Unity

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|U00|[Unity 6.6 User Manual](https://docs.unity3d.com/Manual/index.html)|DOC/本文・分野入口|latest release表記と機能体系。latest patch番号ではない|
|U01|[Asset Metadata](https://docs.unity3d.com/2022.3/Documentation/Manual/AssetMetadata.html)|DOC/本文|Unique IDs / Meta files。metaは当該assetのidentityとimport settings|
|U02|[TryGetGUIDAndLocalFileIdentifier](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.TryGetGUIDAndLocalFileIdentifier.html)|API/本文|Declaration / Warning / Description。long推奨、GUID+fileID、成功bool|
|U03|[GUIDToAssetPath](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.GUIDToAssetPath.html)|API/本文|Returns / Description。project内lookup、逆参照一覧でない|
|U04|[LoadAllAssetsAtPath](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.LoadAllAssetsAtPath.html)|API/本文|Description。hidden subassets、mainはindex 0保証なし|
|U05|[GetDependencies](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.GetDependencies.html)|API/本文|Description / recursive。asset path集合でproperty・faceは返さない|
|U06|[Script serialization](https://docs.unity3d.com/2022.3/Documentation/Manual/script-Serialization.html)|DOC/本文|field、UnityEngine.Object参照、SerializeReference。個別SDK schemaは未調査|
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
|U18|[GetCorrespondingObjectFromSource](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/PrefabUtility.GetCorrespondingObjectFromSource.html)|API/本文|Description。直近sourceとnested例|
|U19|[GetCorrespondingObjectFromOriginalSource](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/PrefabUtility.GetCorrespondingObjectFromOriginalSource.html)|API/本文|Description。source chain最後、追加されたassetとは別の問い|
|U20|[GetPropertyModifications](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/PrefabUtility.GetPropertyModifications.html)|API/本文|parent Prefabに対するmodifications|
|U21|[Prefab Variants](https://docs.unity3d.com/2022.3/Documentation/Manual/PrefabVariants.html)|DOC/本文|継承・override優先、Model/Variantをbaseにできる|
|U22|[Nested Prefabs](https://docs.unity3d.com/2022.3/Documentation/Manual/NestedPrefabs.html)|DOC/本文|nested instanceのasset link|
|U23|[SkinnedMeshRenderer.bones](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SkinnedMeshRenderer-bones.html)|API/本文|skinで使うbone array。nullの全native挙動は未確認|
|U24|[SkinnedMeshRenderer.sharedMesh](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/SkinnedMeshRenderer-sharedMesh.html)|API/本文|skin対象Mesh|
|U25|[Mesh.bindposes](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh-bindposes.html)|API/本文|boneと同index、base poseのinverse transform|
|U26|[Mesh.GetAllBoneWeights](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetAllBoneWeights.html)|API/本文|頂点順、各頂点内weight降順。4 influence限定でない|
|U27|[Mesh.GetBonesPerVertex](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetBonesPerVertex.html)|API/本文|nonzero数、NativeArray寿命の注意|
|U28|[Mesh.GetBlendShapeFrameVertices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetBlendShapeFrameVertices.html)|API/本文|shape/frameのposition・normal・tangent delta|
|U29|[GraphicsRenderers.bindings.cs / rootBone](https://github.com/Unity-Technologies/UnityCsReference/blob/a322ce5f78a82cf7ea211857a45338136ed7a22f/Runtime/Export/Graphics/GraphicsRenderers.bindings.cs)|SRC/本文|2022.3 branch固定commit。extern propertyはnative実装を見せない。個別rootBone API URLは404|
|U30|[MeshFilter.sharedMesh](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/MeshFilter-sharedMesh.html)|API/本文|shared Mesh読取。書換は他object/imported assetへ影響|
|U31|[Material.shader](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Material-shader.html)|API/本文|Materialが使うShader|
|U32|[GetTexturePropertyNames](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Material.GetTexturePropertyNames.html)|API/本文|Material上のTexture property名。画像自体の存在は別|
|U33|[Model tab](https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Model.html)|DOC/本文|Scale Factor / Convert Units / Bake Axis Conversion / Weld Vertices / Index Format / Normals|
|U34|[Rig tab](https://docs.unity3d.com/2022.3/Documentation/Manual/FBXImporter-Rig.html)|DOC/本文|Legacy / Generic / Humanoid、root / Avatar mapping|
|U35|[Animation tab](https://docs.unity3d.com/2022.3/Documentation/Manual/class-AnimationClip.html)|DOC/本文|FBX clips / asset-specific・clip-specific settings。推測したFBXImporter-Animations URLは404、こちらが原典|
|U36|[GetCurveBindings](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AnimationUtility.GetCurveBindings.html)|API/本文|float curveだけを返す|
|U37|[GetObjectReferenceCurveBindings](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AnimationUtility.GetObjectReferenceCurveBindings.html)|API/本文|object-reference curveを返す|
|U38|[EditorCurveBinding](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/EditorCurveBinding.html)|API/本文|path / type / propertyName|
|U39|[Unity 6 release support](https://unity.com/releases/unity-6/support)|REL/本文|Latest LTS release / Support。6.3 LTSとUpdateを分ける|
|U40|[ModelImporter.weldVertices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-weldVertices.html)|API/本文|position共有vertexの結合。属性条件はU33も読む|
|U41|[optimizeMeshVertices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-optimizeMeshVertices.html)|API/本文|GPU cache向け頂点順最適化|
|U42|[optimizeMeshPolygons](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-optimizeMeshPolygons.html)|API/本文|GPU cache向けpolygon順最適化|
|U43|[importNormals](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-importNormals.html)|API/本文|normal import setting、詳細はU33|
|U44|[importTangents](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-importTangents.html)|API/本文|tangent import setting、詳細はU33|
|U45|[meshCompression](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-meshCompression.html)|API/本文|compressionとvertex data artifact|
|U46|[Mesh.GetIndices](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetIndices.html)|API/本文|topology依存index layout、baseVertex。face集合へ順を捨てない|
|U47|[Mesh.GetTopology](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Mesh.GetTopology.html)|API/本文|submesh topology。U12 Winding order本文も確認済|
|U49|[ModelImporter.materialName](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-materialName.html)|API/本文|名前を生成して既存Materialを探す。identity証明とは別|
|U50|[PropertyModification](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/PropertyModification.html)|API/本文|target/propertyPath/value/objectReference。元とeffective参照の区別|

## Blender・版確認

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|B00|[Blender Manual 5.2](https://docs.blender.org/manual/en/5.2/)|DOC/入口・未取得|同版FBX Manual/API本文は取得不能。root本文を取得できたと扱わない|
|B01|[BKE_blender_version.h / v5.2.1](https://github.com/blender/blender/blob/v5.2.1/source/blender/blenkernel/BKE_blender_version.h)|SRC/本文|BLENDER_VERSION/PATCH/CYCLE/SUFFIX。5.2.1 release LTSを定義、最新順位は保証しない|
|B02|[rna_ID.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_ID.cc)|SRC/本文|ID users / use_fake_user / copy / evaluated_get。APIページは取得不能|
|B03|[rna_mesh.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_mesh.cc)|SRC/本文|rna_MeshPolygon_material_index_get/set、Face domain。全Mesh RNA未監査|
|B04|[rna_object.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_object.cc)|SRC/本文|MaterialSlot.link/material/slot_index、VertexGroup name/index/add|
|B05|[rna_depsgraph.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_depsgraph.cc)|SRC/本文|Depsgraph update / object iteration。完全evaluation contractはB02も読む|
|B06|[rna_armature.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_armature.cc)|SRC/本文|Bone.matrix_local、armature relative rest|
|B07|[rna_pose.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_pose.cc)|SRC/本文|PoseBone.matrix、constraint/driver適用後armature object space|
|B08|[rna_action.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_action.cc)|SRC/本文|Action slots/layers/use_frame_range。全channel bag API未監査|
|B09|[rna_nla.cc](https://github.com/blender/blender/blob/v5.2.1/source/blender/makesrna/intern/rna_nla.cc)|SRC/本文|NlaStrip action/action_slot/action_slot_handle|
|B10|[export_fbx_bin.py](https://github.com/blender/blender/blob/v5.2.1/scripts/addons_core/io_scene_fbx/export_fbx_bin.py)|SRC/本文|fbx_data_mesh_elements、PolygonVertexIndex、LayerElementUV/Normal/Material、normal dedup回避。全FBX規格でない|
|B11|[io_scene_fbx/__init__.py](https://github.com/blender/blender/blob/v5.2.1/scripts/addons_core/io_scene_fbx/__init__.py)|SRC/本文|ImportFBX/ExportFBX option: NLA/All Actions/sampling/simplify/axis/custom normals。presetの無損失保証でない|
|B12|[Download](https://www.blender.org/download/) / [LTS](https://www.blender.org/download/lts/)|REL/取得不能|Web取得は402、API本文直接取得は403。認証等の迂回なし。最新stable/LTS patch不明|
|B13|[import_fbx.py](https://github.com/blender/blender/blob/v5.2.1/scripts/addons_core/io_scene_fbx/import_fbx.py)|SRC/部分読取|module header / helpers / name validation。material import本体・全対応変換は未調査|
|B14|[MeshPolygon API](https://docs.blender.org/api/5.2/bpy.types.MeshPolygon.html) / [ID API](https://docs.blender.org/api/5.2/bpy.types.ID.html)|API/取得不能|5.2本文未読。代替SRCをAPI本文確認済と表記しない|

## VRChat・版確認

|ID|公式URL・見出し|区分/状態|読む箇所・適用限界|
|---|---|---|---|
|V01|[Current Unity Version](https://creators.vrchat.com/sdk/upgrade/current-unity-version/)|DOC/本文|2022.3.22f1。最新版Unityへ無条件更新しない|
|V02|[VRChat SDK Releases](https://creators.vrchat.com/releases/)|REL/本文|最新掲載3.10.5、2026-09-04。client版ではない|
|V03|[Release 3.10.5](https://creators.vrchat.com/releases/release-3-10-5/)|REL/本文|Summary / Features / Fixes & Changes。domain reload、collider、constraint等の版差分|
|V04|[Creating Your First Avatar](https://creators.vrchat.com/avatars/creating-your-first-avatar/)|DOC/本文|Step 5 Avatar Descriptor、view position / lip sync。Descriptor全field schemaではない|
|V05|[PhysBones](https://creators.vrchat.com/common-components/physbones/)|DOC/本文|Versions / Transforms / Per-Component Limitations / Changing Properties / VRCPhysBoneCollider。旧avatar-dynamics URLはここへredirect|
|V06|[Contacts](https://creators.vrchat.com/common-components/contacts/)|DOC/本文|Sender/Receiver / Shape / Filtering。case-sensitive tags、avatarとworldの出力差|
|V07|[Constraints](https://creators.vrchat.com/common-components/constraints/)|DOC/本文|in-game conversion / Target Transform / Solve In Local Space / Usage Tips|
|V08|[Playable Layers](https://creators.vrchat.com/avatars/playable-layers/)|DOC/本文|Base/Additive/Gesture/Action/FX、Animation Controllersのみ、mirror copyの境界|
|V09|[Expressions Menu and Controls](https://creators.vrchat.com/avatars/expression-menu-and-controls/)|DOC/本文|Descriptorへの2asset参照 / type / Saved・Synced / 8 controls|
|V10|[Animator Parameters](https://creators.vrchat.com/avatars/animator-parameters/)|DOC/本文|Parameter Types / custom / Cross-Platform Parameter Sync / Sync Types|
|V11|[Allowed Avatar Components](https://creators.vrchat.com/avatars/whitelisted-avatar-components/whitelisted-avatar-components/)|DOC/本文|allowed list / Cameras on Avatars。単階層推測URLではなく公式navのリンク先|
|V12|[Public SDK API](https://creators.vrchat.com/sdk/public-sdk-api/)|DOC/API/本文|Public API folder・PublicAPI attribute / Heads up / semver。公開でも将来変更可|
|V13|[Build Pipeline Callbacks and Interfaces](https://creators.vrchat.com/sdk/build-pipeline-callbacks-and-interfaces/)|DOC/API/本文|IEditorOnly / IPreprocessCallbackBehaviour / IVRCSDKBuildRequestedCallback|
|V14|[Rig Requirements](https://creators.vrchat.com/avatars/rig-requirements/)|DOC/入口・概要|rig要求。各骨の全条件は未監査|
|V15|[Shader Blocking and Fallback System](https://creators.vrchat.com/avatars/shader-fallback-system/)|DOC/入口・概要|fallback。Editor shader表示だけでclient表示保証不可|
|V16|[Android Content Limitations](https://creators.vrchat.com/platforms/android/quest-content-limitations/)|DOC/入口・概要|platform制限。全閾値の転記・最新値固定はしない|
|V17|[Worlds](https://creators.vrchat.com/worlds/)|DOC/本文・入口|Udon/Scene Components/Layers/SDK prefabs/scripted assets体系|
|V18|[Networking](https://creators.vrchat.com/worlds/udon/networking/)|DOC/本文|variables/events/ownership、late joiners。Avatar parametersとは別|
|V19|[Network Variables](https://creators.vrchat.com/worlds/udon/networking/variables/)|DOC/入口・概要|manual/continuous、serialization。帯域等全仕様未監査|
|V20|[Persistence](https://creators.vrchat.com/worlds/udon/persistence/)|DOC/入口・概要|PlayerData/PlayerObjects等の分野入口、個別型/容量/寿命未監査|
|V21|[Player Audio](https://creators.vrchat.com/worlds/udon/players/player-audio/)|DOC/本文・概要|Voice Gain/Distance/Lowpass、Avatar Audioとの別設定|
|V22|[ClientSim](https://creators.vrchat.com/worlds/clientsim/)|DOC/入口・概要|Editor simulation。実client・multi-clientの証明ではない|
|V23|[Allowlisted World Components](https://creators.vrchat.com/worlds/whitelisted-world-components/)|DOC/入口・概要|World用リスト。Avatar allowlistを流用しない|
|V24|[Terms of Service](https://hello.vrchat.com/legal)|DOC/本文|§8.1–8.4 User Content。第三者素材licenseの再配布許可を代行しない|

## 取得状態の扱い

Unity公式はWeb取得と公開URL本文読取で確認。Blender docs/APIとdownloadの一部は取得不能。公式source mirrorの固定tag本文は取得できたため**SRCとして**使う。VRCの直接HTTP取得は403だったが、この作業のWeb取得サービスでは公式Creation本文を取得できた。これは認証やアクセス設定を変更した結果ではない。本文取得できない頁を引用して詳細を断定しない。

公式issue tracker（Unity: https://issuetracker.unity3d.com/、Blender: https://projects.blender.org/、VRC: https://feedback.vrchat.com/）は不具合照合の入口。今回まだ個別issueを読んでいない。source comment中のissue番号は、issue本文と同一の根拠として扱わない。
