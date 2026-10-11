# Unity: serialization・Prefab・Skin・Animationの往復境界

対象: Unity 2022.3系列、確認日2026-10-11 UTC。原典は[SOURCES](SOURCES.md)。Editor実行はしていない。

## Package、metadata、serialization

**DOC [U01、U06–U08]**: unitypackageはasset集合とmetadataを運ぶ。metaを元assetと一緒に保つことがidentity維持に必要。UnityEngine.Object派生objectは参照としてserializeされ、通常のSerializable classのinline値、SerializeReferenceによるmanaged referenceとは保存方式が異なる。

**UNKNOWN**: gzip tarのGUID directory/asset/asset.meta/pathnameという内部配置の安定schemaは公式Manualで確認できない。既存VAPB parserが扱う配置を全producer・全versionの公開file-format保証としない。binary serialized asset、unknown componentの復元、欠けたscriptのfield解釈は別の未証明項目。

**INFERENCE**: 元FBX/metaを保持し、編集Meshを新asset identityで別Variantに割り当てる方針は、元assetを改変せずoverrideする公開Prefabモデルに沿う。ただし生成assetのGUID/fileIDを勝手に旧値と同一扱いしない。新import後identityはU02/U04等で観測する対象。

## Prefab、Variant、nestedとsource chain

**DOC/API [U18–U22]**: Variantはbaseのpropertyを継承しoverrideが優先する。baseはModel Prefabや別Variantでもよい。nested instanceは自分のPrefab assetへのlinkを保持する。`GetCorrespondingObjectFromSource`は直近の対応asset object、`GetCorrespondingObjectFromOriginalSource`は対応chainの最後を辿る。両者の戻り先を混同しない。

**API [U20]**: `GetPropertyModifications`はparent Prefabに対するinstance modificationsを返す。これだけで全nested/Variant chainのeffective stateがflatten済とする契約ではない。

**INFERENCE**: 同じsource Rendererが複数occurrenceに現れるなら、source IDだけでは受け手instanceを一意に選べない。base→Variant→nested→scene instanceの順で、対象occurrenceに実際に適用されるpropertyを区別する。source link喪失、added/removed component、missing sourceは個別に未知として保持する。

## Skin: bone arrayとbindposeを結ぶ

**API [U23–U28]**: SkinnedMeshRenderer.sharedMeshはskin対象Mesh、bonesはskinで使うTransform群。bindposes[i]は同じindexのboneに対応する。Mesh.GetAllBoneWeightsは頂点順に並び、各頂点内はweight降順。GetBonesPerVertexは頂点ごとの非zero influence数を返す。legacyの4 influence表現だけを全skinの保証としない。

**DOC/SRC [U14、U29]**: Root boneはskeleton rootとbounds移動に関わる。2022.3公式Manual本文を使用する。個別rootBone API URLは404だったため、C# bindingのpublic property宣言はSRCとして補助する。bindingのnative externからnull時の実行結果は分からない。

**INFERENCE**: Bone順変更にはboneIndexとbindposeの対応変更が必要。名前順にbonesだけ整列すると意味が変わる。null entryを削除する操作もindex構造を変える。元nullBone/fileID0の意図・native挙動は未確認であり、都合のよいTransformを補って成功としない。

**API [U28]**: blendshapeはshape/frame indexとvertex数に対応するdelta positions/normals/tangentsを持つ。見た目が同じ1frameだけでは、shape名、複数frame weight、normal/tangent deltas、animation bindingを含む同等性は証明されない。

## 座標系、単位、transform

**DOC [U33]**: Model tabのScale Factor、Convert Units、Bake Axis Conversionは異なる処理を指定する。Bake Axis Conversionはaxis変換をvertex/animation dataへ焼き込み、無効の場合はroot Transformで補償する説明。Unity physicsの基準は1 unitを1 mとして扱う。

**INFERENCE**: raw Mesh local positions、Renderer/world transform、armature rest、pose、bindposeを同じ空間へ揃えて比較する。Blender→FBX→Unityの一つの観測行列を全設定へ適用しない。非一様scale・負scale・normal/tangent handedness・root compensationは別に確認すべき対象であり、今回実測なし。

## AnimationClip、Action、rig、curve

**DOC/API [U34–U38]**: Unity importではLegacy/Generic/Humanoidが別のrig扱い。Genericにはroot node、HumanoidにはAvatar mapping/Configureがあり、任意bone curveをそのままHumanoid motionと同一視しない。Animation tabはFBXからclipを切り出し、asset設定とclip設定を持つ。

float curveとobject-reference curveは別。GetCurveBindingsだけではMaterialなどobject-reference keyframeを網羅しない。EditorCurveBindingはpath/type/propertyNameを持つので、階層renameや別rootへの移植ではtarget bindingの再確認が必要。

**INFERENCE**: Blender Actionを独立AnimationClipとして返し、本人がGUIで割り当てる方針は、Controller/Playable layerとのbindingを別の操作として扱える。Action名一致だけでUnity clipの意味同一、Humanoid retarget、VRC同期まで成功とはしない。時間単位/FPS、resampling、root motion、quaternion/Euler、tangent interpolation、constraintsのbake、NLA strip時間変換、mask/state machine/transition/eventは今回完全変換未調査。

Material/Shaderのobject curveやTexture依存が欠けた場合、bone animationだけ一致してもAvatar全体の同等性とは別。
