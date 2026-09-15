# Unity Package / VRChat Avatar Importer

Blender 5.2.1 LTS専用の `.unitypackage` インポーターです。Version 0.2.0。Unity Editorを起動せず、UnityPackageを一時フォルダへ安全に復元し、FBXをBlenderへ読み込みます。

Blender 5.2.1 LTSでは、Blender OperatorをMRO先頭に置く公式形式と、Blender内部引数を受け取るconstructor形式に対応しています。legacy `bpy.ops.import_scene.fbx` は既存のArmature、Weight、Shape Key、Material Slotの挙動を維持するため継続使用します。

## インストール

1. `unitypackage_blender_importer.zip` を用意する。
2. Blenderで **編集 → プリファレンス → アドオン → インストール…** を開く。
3. ZIPを選択してインストールし、**Unity Package / VRChat Avatar Importer** を有効化する。

ZIPは、アドオンフォルダ `unitypackage_blender_importer/` がZIP直下に入った構成です。

## 使用方法

1. **File → Import → Unity Package / VRChat Avatar (.unitypackage)** を選ぶ。
2. `.unitypackage` を選択する。
3. 複数のPrefabがある場合は、表示された **Prefab** 候補から選ぶ。
4. **Reconstruct Prefab** または **Import Raw FBX** と各オプションを確認して実行する。

### BlenderからUnityへ戻す

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
- キャンセル、エラー、Prefab選択の中断では準備済みの一時展開先を後始末します。`Keep Extracted Files` を有効にして正常完了した場合だけ、テクスチャの外部パス維持のため展開先を保持します。

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

## 非対応範囲

PhysBone、Contact、Animator Controller、Expressions、Modular Avatar、NDMF、lilToon/Poiyomiの完全再現、AudioLink、Unity Constraint、MonoBehaviour/C#実行、Prefab Variantの完全互換は対象外です。

## Editable Texture Workflow

Select an imported image in the Image Editor and open the `Unity Texture` sidebar. It displays Unity Asset Path, Unity GUID, working file path, file existence, and dirty state. `Save to Unity Source` writes Blender edits to that same existing file; `Reload from Disk` refreshes the same Image datablock after an external editor change; `Reload Changed Unity Textures` performs a manual mtime scan.

The workflow refuses missing files, dirty reloads, ordinary non-Unity images, and packed-source conflicts. It never creates a copy, backup, new GUID, or `.meta`; use the importer `Keep Extracted` option for editable source files.

`Open in External Editor` opens the first-time editor selection menu, then launches the saved editor directly on later uses. `Change External Editor` or the menu allows a detected editor or `Browse for executable...`; the path/name is stored in Blender Add-on Preferences. The launcher passes the existing working texture as a separate argument, never uses `shell=True`, and does not watch or automatically reload the file.

If the operating system refuses the launch after validation, the launcher returns `EDITOR_LAUNCH_FAILED` and the Blender operator reports an error without exposing a traceback.

## Current Limitations

- Transparent / cutout / blend material visual pathは未検証です。
- Unity Shaderの外観はBlender Principled BSDFによる近似です。
- Multi-package integrationは未実装です。
- UnityPackage exporterは未完成です。
- File Browser cancel/re-run、任意Prefab手動選択、通常UI Undo-keyは未確認です。

- Unityの座標系とFBXインポーターの変換差により、特殊なPrefabや複数の変換階層では位置・回転に微調整が必要な場合があります。
- PrefabのMesh/Material参照は、Unity YAMLの外部GUID参照が取得できる場合に優先して使います。サブアセットや複雑なPrefab VariantはFBX全体の読み込みへフォールバックします。
- lilToon、Poiyomi、MToon、VRChat Mobileの完全なShader互換、Shadow/Rim/MatCap/Outlineの完全な描画再現は対象外です。これらは共通要素をPrincipled BSDFへ近似し、未接続の固有情報をメタデータへ残します。
- UnityPackageに壊れたアセットが含まれる場合、失敗したファイルをコンソールへ警告して、読み込めるFBXの処理を継続します。
- Blender実機でのFBXファイルそのものを用いた形状確認は、パッケージに含まれるFBXの内容に依存します。付属テストは展開、パス検証、列挙、Prefab YAML解析とBlenderアドオン有効化を対象にします。
- Unity側のMaterial RestoreはFBX内のExported Material名がmanifest生成後に変更されていないことを前提にします。別ツールでMaterial名を変更した場合はSlotを特定できません。
- Unity側Restoreは元`.mat`のGUIDを変更せず、Unity EditorのAssetImporter remapへ参照を登録します。実際のShader表示は、対象Projectに元Shaderと元`.mat`が存在する場合に限られます。
