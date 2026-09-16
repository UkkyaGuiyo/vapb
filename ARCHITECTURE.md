# Architecture

## Status Vocabulary

- **IMPLEMENTED**: 現行コードで確認できる。
- **PARTIAL**: 一部の形式・経路・identityだけを扱う。
- **PLANNED**: 仕様上必要だが、現行コードには実装されていない。

## Pipeline

```text
UnityPackage
    ↓
Package Reader
    ↓
Asset Index
    ↓
Dependency Resolver
    ↓
Identity Layer
    ↓
Blender Import Layer
    ↓
Working Assets
    ↓
Blender Scene
    ↓
User Editing
    ↓
Bridge Exporter
    ↓
UnityPackage / Unity Project
    ↓
Unity Finalizer
    ↓
Final Prefab
```

## Current Mapping

| Layer | Module | Status | Responsibility / boundary |
|---|---|---|---|
| Package Reader | `unity/package_reader.py` | IMPLEMENTED | tar.gz形式、pathname/GUID読み取り、安全な展開、選択的抽出 |
| Asset Index | `unity/asset_database.py` | IMPLEMENTED | GUID・Unity path・抽出Pathの索引、拡張子別列挙 |
| Dependency Resolver | `operators/import_unitypackage.py` | PARTIAL | PrefabからFBX/Material/Texture依存を選択抽出。未解決時はFBX全体へfallback |
| Prefab Parser | `unity/prefab_parser.py` | PARTIAL | GameObject、Transform、Renderer参照の有用部分をUnity YAMLから取得 |
| Material Parser | `unity/material_parser.py`, `unity/material_model.py` | PARTIAL | `.mat`をshader-independentな中間モデルへ変換 |
| Material Mapping | `unity/material_mapping.py` | PARTIAL | GUID優先、Path・一意Name fallback、externalObjects解析 |
| Identity Layer | 各`unity/*`と`blender/*`のcustom properties | PARTIAL | GUID/path/fileIDの一部保持。複数Package merge・rename追跡は未完成 |
| Blender Import Layer | `blender/fbx_importer.py` | IMPLEMENTED | Blender標準FBX importerでArmature、Weight、Shape Key等を取り込み |
| Material Builder | `blender/material_builder.py` | PARTIAL | Principled BSDF近似、Shader profile、Material/Texture metadata保存 |
| Texture Loader | `blender/texture_loader.py` | PARTIAL | 画像読込、GUID/path/meta property保存、pack option |
| Hierarchy Builder | `blender/hierarchy_builder.py` | PARTIAL | Prefab parent/transform復元、Prefab rootとfileID保存 |
| Import Operator | `operators/import_unitypackage.py` | IMPLEMENTED | File Browser、async prepare、Prefab handoff、main-thread import、cleanup |
| Bridge Exporter | `blender/roundtrip_export.py`, `blender/roundtrip_manifest.py` | PARTIAL | FBX + materialmap sidecar出力。UnityPackage再梱包ではない |
| Unity Finalizer | `unity_editor/Editor/UnityPackageBlenderMaterialRestore.cs` | PARTIAL | Unity側で既存`.mat`をGUID/Path/一意Name順にFBXへremap。Final Prefab生成ではない |
| Final Prefab | Unity Project / VRChat runtime | PLANNED | Unity側のAnimator、Expressions、MA/NDMF、PhysBone等の最終構築 |

## Editable Texture Workflow

- `blender/texture_loader.py`: keeps the existing Image datablock and records source mtime as a string custom property compatible with Blender ID properties.
- `operators/texture_editing.py`: validates Unity identity and the existing filepath, then performs same-file save or `Image.reload()` without duplicating the Image.
- `ui/texture_panel.py`: Image Editor sidebar for Unity Asset Path, GUID, working filepath, existence, dirty state, and manual actions.
- mtime comparison is initiated only by the `Reload Changed Unity Textures` button. There is no watcher, polling thread, automatic pack, fallback path, or automatic backup.

## External Texture Editor Launcher

- `external_editor.py`: narrow Windows App Paths/PATH/common-install detection, executable validation, and argument-list `Popen` launch.
- `preferences.py`: `AddonPreferences` storage for `external_editor_path` and `external_editor_name`; these values are environment preferences, not Image identity.
- `operators/texture_editing.py`: selection menu, executable browser, direct launch, and existing Unity source/dirty/packed/identity guards.
- `ui/texture_panel.py`: one-line selected editor display plus Open/Change controls. No watcher, temp copy, or editor-exit wait exists.

## Identity Layer

### Currently Stored

- Objects: `unity_source_fbx`, `unity_source_prefab`, `unity_prefab_file_id`
- Materials: `unity_source_material`, `unity_material_guid`, `unity_material_path`, `unity_material_name`, `unity_shader_guid`, `unity_shader_name`, normalized properties
- Images: `unity_source_path`, `unity_guid`, `unity_asset_path`, import metadata
- Export manifest: object path、material GUID/path/name、binding slot、manifest schema
- Package scene: source package path、extracted root、FBX count、selected prefab path

### Gaps

- 一貫した`source_package`、`source_object_path`、`source_material_guid`、`source_texture_guid`の共通schema
- Rename後の永続的なobject identity
- 複数Package merge時のnamespaceとcollision policy
- Material replacement / Texture editを跨ぐreverse index
- Unity fileID以外のsub-asset identityとPrefab Variant identity

Identity Layerは今後、import・edit・merge・exportを横断する独立設計として強化する。今回その実装は行わない。

## Lifecycle Boundary

準備workerはBlender datablockを変更しない。準備modalは完了時に`FINISHED`でWindowManagerから終了し、UUID sessionを次のevent-loopへ渡す。Prefab dialogとprepared importは別Operatorで実行し、cancel、exception、timeoutで抽出先・progress・sessionをcleanupする。

## Package-Scoped Identity (0.4.0 candidate)

- `PackageIdentity`の内容SHA-256を`source_package_id = sha256:<64hex>`として、Packageのファイル名やパスから独立したnamespaceにする。
- Canonical asset identityは、GUIDがある場合は`(source_package_id, guid, source_guid, file_id, source_file_id)`、GUIDがない場合は`(source_package_id, path, source_asset_path, file_id, source_file_id)`。fileID単独は`AMBIGUOUS_IDENTITY`として登録しない。GUID/path/fileIDはBlender Object、Material、Imageのcustom propertyへ伝播する。
- `SceneIdentityRegistry`をScene custom propertyへJSON保存し、package metadata、asset lookup、GUID/path reverse lookup、collision reportを提供する。
- 同一Package内の同一identityは再登録可能だが、異なるPackage間の同一GUIDまたは同一Asset Pathはcollisionとして報告する。自動merge、名前だけの推測、silent overwriteは行わない。
- 旧来のPackage情報が無いdatablockは`LEGACY_UNSCOPED`として扱い、現在Packageへ推測結合しない。
- Prefabの`unity_source_prefab`は抽出filesystem path、`unity_asset_path`は`AssetEntry.unity_path`由来の`Assets/...`相対pathとして分離する。

## Explicitly Not Implemented

UnityPackageの再梱包、Unity Finalizerの自動実行、完全なShader互換、PhysBone preview、複数Packageの自動mergeは現行実装では提供しない。

## Maximum Recoverable Unity State (MRUS) Architecture

MRUSはBlender内でUnityを再現する機能ではなく、次の将来パイプラインとして設計する。

`UnityPackage → State Snapshot / Identity Capture → Blender Import → User Editing → Bridge Export → Unity Finalizer → Identity Rebind → State Restore → Validation Report → Final Prefab`

### Planned Responsibilities

| Component | Status | Responsibility |
|---|---|---|
| State Snapshot / Identity Capture | PLANNED | Unity/VRC Component、serialized properties、object/asset references、依存要件をcapture |
| Identity Rebind | PLANNED | persistent identityを基準にrename/hierarchy/Shape Key/Bone/animation pathを再接続 |
| State Restore | PLANNED | Finalizer段階でAvatar/Animator/Expression/PhysBone等を安全に復元 |
| Validation Report | PLANNED | restore status、missing target、dependency、ambiguityを人間向けに出力 |

### MRUS Identity Extension (PLANNED)

将来のState Snapshot / Bridge Manifest拡張では、名前ではなく次のpersistent identity候補を保持する。

`source_package`, `source_guid`, `source_asset_path`, `source_object_path`, `source_object_file_id`, `source_component_file_id`, `source_component_type`, `source_script_guid`, `source_bone_path`, `source_shape_key`, `source_material_guid`, `source_texture_guid`, `source_animation_path`

Object renameやhierarchy変更後は、旧Object path → persistent identity → 新Object pathのrebind tableを生成する。Shape Keyはsource mesh identity + name/index/identifier、BoneはArmature identity + bone path/hierarchyを基準にし、削除は`MISSING_TARGET`、複数候補は`AMBIGUOUS`とする。

### Component Snapshot (PLANNED)

将来のBridge Manifest拡張候補は`schema_version`、`source_package`、`objects`、`components`、`bindings`、`dependencies`、`restore_policy`を持つ。Component entryはsource object identity、component type/fileID、script GUID、serialized properties、object/asset references、dependency requirementsを候補とする。Unity YAML完全再実装は行わない。

### Unity Finalizer Responsibilities (PLANNED)

Phase 1 Asset import確認 → Phase 2 Identity resolution → Phase 3 Object/Bone/Shape Key rebind → Phase 4 Material restore → Phase 5 Avatar Descriptor/LipSync restore → Phase 6 Animator/Expression restore → Phase 7 PhysBone/Contact restore → Phase 8 Third-party component restore → Phase 9 Validation Report。

Restore resultは`RESTORED`、`REBOUND`、`PARTIAL`、`MISSING_TARGET`、`MISSING_DEPENDENCY`、`AMBIGUOUS`、`UNSUPPORTED`、`ERROR`に分類し、黙って失敗しない。
-
## Multi-Package Visual Binding (0.4.0 candidate)

Material/Texture bindingの解決順は、現在import中のPackageのAssetDatabase、Prefabの明示GUID参照、package-scoped registryを正本とする。Prefab GameObject名がFBX import時の`.###`重複suffixで変わった場合は、exact nameを優先し、base nameの候補が一つだけなら採用し、複数候補では空のplaceholderへ勝手に割り当てない。

Real Multi-Package Visual E2Eの初回診断では、Package BのMaterial/Imageは発見・生成済みだったがRenderer slotが0件だった。原因はPrefab名と`.###`付きFBX Object名の不一致でhierarchyがplaceholderを作り、material mapping対象が空Objectになったことだった。suffix-safe lookup後はB slot 1件、B Image node 1件、cross-package material reuse 0件となった。

## UnityPackage Exporter (PLANNED)

将来の実装境界は `Imported Packages → Blender Scene → Select Export Root/Set → Reachability → Identity Resolution → FBX/Texture/Material/Meta Generation → Unity standard asset/meta/pathname → tar.gz .unitypackage` とする。未使用datablockは編集中にpruneせず、exportのreachability判定だけで除外する。本候補では仕様のみで、Exporterは実装しない。
## Cross-Package Dependency Resolver (0.4.0 candidate)

`SceneIdentityRegistry`はasset identity/collision、`DependencyRegistry`はconsumer→providerのreference relationshipを担当する。後者はScene custom property `unitypackage_dependency_registry`へJSON保存し、`PREFAB_RENDERER_MATERIAL`、`FBX_EXTERNAL_MATERIAL`、`MATERIAL_TEXTURE`を記録する。

Resolution orderはconsumer Package内のunique provider、次にScene全体のunique provider。0件は`UNRESOLVED`、1件のcross-package providerは`RESOLVED_CROSS_PACKAGE`、2件以上は`AMBIGUOUS_PROVIDER`として自動選択しない。新Package import完了ごとにresolverを再実行するため、Geometry→Material、Material→Geometryの双方でlate bindingできる。

ProviderはMaterial/Imageのcustom property（Package ID、GUID、Asset Path）で検索し、Blender Object名やMaterial名だけをcross-package identityに使わない。未使用assetやunresolved assetは編集中に削除しない。

### Bounded Visual Discovery Pipeline

The import state machine is `prefab selection -> visual graph -> bounded sibling discovery -> explicit sibling choice -> grouped import`. Discovery builds a pathname/meta manifest, reads only selected prefab/material text and FBX `.meta` external-object data, then searches the selected folder followed by a single parent/child neighborhood expansion when visual GUIDs remain unresolved. `visual_status` (`NONE`, `PARTIAL`, `COMPLETE`, `AMBIGUOUS`) is kept separate from nonvisual dependency diagnostics.
