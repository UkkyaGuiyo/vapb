# Product Specification

## Product Goal

Blender 5.2.1 LTSで、UnityPackageとして配布されるAvatar、Clothes、Accessory、Propを読み込み、Blender上で編集・組み合わせ・近似確認を行う。編集済みAsset群は、Unityへ再Import可能な成果物として出力する。

## High-Fidelity Requirements

可能な限り正確に保持する対象:

- Mesh geometry
- Armature、Bones、Vertex Groups、Bone Weights、Shape Keys
- UV、Normals、Transform、Hierarchy
- Material Slots、Texture Assets
- Unity Material identity、Asset GUID、Asset Path、Unity fileID、source object identity

## Approximate Preview Only

Blender側では次を近似表示とする。Unityの描画結果を完全再現することはGoalではない。

- lilToon、Poiyomi、MToon、その他Unity Shaderの外観
- PhysBone / SpringBoneの動作Preview

## Unity-Side Only

Animator Controller、Animation State Machine、Expressions、Contacts、Modular Avatar、NDMF、AudioLink、複雑なMonoBehaviour、Unity Editor gimmick、VRChat runtime gimmick、Prefab Variant完全互換はUnity側で最終構築する。

## Editable Texture Workflow

Imported Unity textures remain the working representation of the original Unity asset. The existing Blender Image datablock is the Source of Truth handle: its Unity GUID, Asset Path, source path, `.meta`-derived identity, and working filepath are retained.

The Image Editor sidebar exposes the identity and file state and provides manual `Save to Unity Source`, `Reload from Disk`, and `Reload Changed Unity Textures` actions. Save writes to the existing working file only after Unity identity, existing filepath, file existence, and write access checks succeed. Reload calls `Image.reload()` on the existing datablock, preserving material bindings.

The same sidebar provides `Open in External Editor`. Known Windows editors are detected without recursive filesystem scanning; the user may browse for any executable. The selected editor path/name is stored only in Addon Preferences. Launch uses the existing source validation, refuses dirty/missing/packed/conflicting sources, and passes `[editor_executable, working_texture]` to non-blocking `subprocess.Popen(..., shell=False)`. No watcher or automatic reload is created.

Missing files return `MISSING_SOURCE`; dirty images refuse reload with `UNSAVED_CHANGES`; packed images return `PACKED_SOURCE_CONFLICT`. No fallback search, automatic copy/backup, GUID or `.meta` creation, auto-packing, watcher, or background polling is part of this workflow. For editable source files, import with `Keep Extracted` enabled.

## Texture Policy

Textureは元Assetを直接編集する前提とする。Addonは`Face_copy.png`等の自動派生ファイルや自動バックアップを作成しない。source asset path、source GUID、source `.meta` identityを保持し、バックアップ責任はユーザー側に置く。

## Material Policy

Materialの表示はBlender上の近似でよい。ただしUnity Asset identity、Renderer slot binding、Material GUID、Texture GUIDの追跡を優先する。「見た目が似ているMaterial」より、元Unity Rendererの参照関係を正本とする。

## Shader Preview v0.1

Material preview is a best-effort Blender representation, not a Unity shader
runtime. `ShaderPreviewIR` keeps material/shader identity, provider status,
preview mode, confidence, supported texture roles, and unsupported features
separate from Blender node construction. `SEMANTIC_PREVIEW` is used for a
built-in or locally indexed shader provider; `GENERIC_FALLBACK_PREVIEW` keeps
explicit common properties such as base color and normal textures useful when
an external provider is missing. A normal texture is never substituted for a
missing base-color texture. Unsupported shader-specific behavior is recorded
in material metadata and does not abort import.

## Identity Policy

## Prefab Candidate Analyzer / Automatic Selection

複数Prefabを含むPackageでは、既定の`AUTO`を「最初のPrefab」への別名として扱わない。各候補をRenderer構造、SkinnedMeshRenderer、GameObject/Transform規模、PrefabからのFBX/Material参照、Material→TextureおよびFBX externalObjectsのvisual closureで解析する。候補分類は`AVATAR_LIKE`、`PROP_LIKE`、`EMPTY_OR_UNSUPPORTED`、`UNKNOWN`とし、候補名・ファイル名・archive順・任意の重み付きスコアを選択根拠にしない。

visual closureが完全なAvatar候補が一意ならAutomaticで選択する。完全なAvatar候補が複数、Providerが曖昧、または安全に一意化できない場合はChooserを表示し、Backgroundでは決定論的エラーとして停止する。明示的な`PREFAB_N`は後方互換として候補解析を迂回してその候補を使う。候補解析はmetadata-firstで、FBX/Texture payloadは読み込まない。

名前だけでidentityを決定しない。最低限、次の情報を保持・拡張対象とする。

`source_package`, `source_guid`, `source_asset_path`, `source_file_id`, `source_object_path`, `source_material_guid`, `source_texture_guid`

Rename、複数Packageのmerge、Material replacement、Texture edit、export後も元Unity Assetとの対応を失わないことを将来要件とする。

## Maximum Recoverable Unity State (MRUS)

BlenderをUnity emulatorにせず、Blender編集に不要なUnity / VRChat固有設定をImport時に可能な限り記録・退避し、Unityへ戻した際にUnity Finalizerが安全に再接続・復元できる状態を目標とする。

Unity固有情報は次の3分類で扱う。

1. Blender編集に持ち込む必要がある情報: Mesh、Bone、Weight、Shape Key、UV、Texture、編集対象のIdentity。
2. Blenderでは保持だけすればよい情報: Component snapshot、Unity fileID、script GUID、serialized properties、object/asset references、依存要件。
3. Unity側で再構築・再接続すべき情報: Avatar Descriptor、Animator、Expressions、PhysBone、Contact、Third-party components等。

「保存できる」と「安全に自動復元できる」は分離する。各項目は`CAPTURE_SUPPORTED`、`RESTORE_SUPPORTED`、`PARTIAL`、`DEPENDENCY_REQUIRED`、`UNSUPPORTED`の状態を持ち、曖昧な対象や不足依存を黙って代替しない。

優先度は次の通りとする。

- Tier 1: Avatar Descriptor、Lip Sync、Viseme、Jaw、Eye Look、Eyelid/Blink、View Position、Playable Layers、Expressions
- Tier 2: Animator Controller、Animation Clip、BlendShape/GameObject/Material animation、FX/Gesture/Action/Base layer references
- Tier 3: PhysBone、Collider、Contact Sender/Receiver、supported Constraints
- Tier 4: Material、Texture、Renderer settings、component references
- Tier 5: Modular Avatar、NDMF、その他MonoBehaviour。対象Unity Projectに依存がある場合のみbest-effort restore

MRUSはUnityPackage → State Snapshot / Identity Capture → Blender Import → User Editing → Bridge Export → Unity Finalizer → Identity Rebind → Recoverable State Restore → Validation Reportの流れで実現する。現時点では設計要件であり、schemaと自動復元は未実装である。

## Non-Goals

- Unity Engine emulator
- Unity Shader完全互換
- VRChat runtime完全互換
- Unity serialization完全再実装
- NDMF / Modular Avatar等の全Editor拡張
- 自動バックアップ管理
- Blender 4.x対応
- Blender内でUnity AnimatorやVRC SDKを再現すること
- 未知MonoBehaviourを推測して再実装すること
- 不足依存や曖昧な対象を勝手に代替・割当すること
- Unity serialization完全互換エンジンを実装すること

## 0.4.0 candidate: Multi-Package Identity Foundation

- Package fingerprintは内容SHA-256から生成し、同名・別パスのPackageでも内容が同じなら同じPackage identity、内容が違えば別identityとする。
- Object、Material、Imageには`unity_source_package_id`と既存のGUID/path/fileIDを保持し、canonical identityを構成する。
- SceneにはPackage registryを保存し、import sequence、source path/name、SHA-256、asset countsを記録する。
- 同一GUIDまたは同一Asset Pathが複数Packageに現れた場合はcollision reportへ記録する。自動解決や自動mergeはしない。
- Sub-assetのfileIDは親GUIDまたは親Asset Pathのscope内でのみ有効とし、fileID単独はambiguousとしてcanonical registryへ登録しない。
- Prefab Objectの`unity_source_prefab`（抽出filesystem path）と`unity_asset_path`（Unity `Assets/...` path）を混同しない。
- 既存のsingle-package GUID/path lookup、Material mapping、Texture mapping、Prefab reconstructionは維持する。

## Current Scope Boundary

BUG-002 / BUG-003 / Editable Textureの既存挙動は回帰対象として維持する。今回の変更はPackage-scoped identity、registry、collision reportとそのテストに限定し、production logicの自動mergeやUnityPackage exportは行わない。
-
## 0.4.0 candidate: Real Multi-Package Visual E2E

- 複数Packageを同一Sceneへ順次importしても、Object、Material、Image、Renderer slotは`source_package_id`を境界として解決する。
- 同名Material、同名Texture filename、同一GUIDが別Packageに存在しても、名前だけのcross-package再利用やsilent mergeを行わない。
- Prefab GameObject名とBlenderの重複suffix（`.001`等）が異なる場合は、同一base名が一意なときだけfallbackし、複数候補なら未解決のままにする。
- MPV-001..012はsynthetic A→B E2E、binding、isolation、ambiguous-safe lookup、save/reopenを受入対象とする。実Package A+Bの目視確認は別途人手確認とする。

## UnityPackage Exporter (PLANNED)

将来のExporterは、選択したExport Root/Setからreachabilityを計算し、解決済みidentityをUnity標準の`<GUID>/asset`、`asset.meta`、`pathname`へ生成してtar.gzの`.unitypackage`を作る。単なるZIP拡張子変更ではない。編集時のBlender datablockは削除せず、reachabilityによるpruningはexport時だけ適用する。Exporter本体、Unity Finalizer、実Package roundtripは本候補では未実装である。

Exporterのcollision status候補は`PRESERVE_GUID`、`NEW_ASSET_GUID`、`GUID_COLLISION_REMAP`、`PATH_COLLISION`、`AMBIGUOUS_SOURCE`、`UNSUPPORTED_EXPORT`とする。

## Visual Dependency and Texture Role Contract (0.4.0 candidate)

Visual completeness is determined only from geometry/prefab, material, and texture GUID coverage. Nonvisual Unity dependencies remain diagnostic state and do not block a visual Import Together decision. Discovery uses a bounded metadata-first manifest and never reads texture or FBX payload bytes while planning. The canonical texture classifier is shared by initial material construction and late binding; unknown shader properties are preserve-only and cannot become Base Color.

If bounded discovery is incomplete, foreground users can locate a package or a direct/one-level-child folder. The importer validates exact GUID coverage before accepting candidates, records `USER_SELECTED_PACKAGE` or `USER_SELECTED_FOLDER` provenance, and re-evaluates the selected-Prefab closure. Explicit user-selected package paths take precedence over automatic ambiguity; zero coverage is rejected. Continue With Missing Assets imports resolved content and persists unresolved visual dependencies.
## 0.4.0 candidate: Cross-Package Dependency Resolution

Scene内のPackage-scoped providerをGUIDで探索し、Prefab Renderer→Material、FBX externalObjects→Material、Material→Textureを対象にlocal priority、unique cross-package binding、unresolved persistence、ambiguous refusal、late bindingを行う。名前だけのcross-package推測やimport順による勝者選択は行わない。

## Import Progress Monitor

Foreground import exposes one shared progress session through Blender's
status bar and native WindowManager progress API. The session reports the
real architectural stages `READING_PACKAGE`, `ANALYZING_PREFABS`,
`RESOLVING_PACKAGES`, `IMPORTING_FBX`, `BUILDING_HIERARCHY`,
`CREATING_VISUALS`, `RESOLVING_DEPENDENCIES`, and `FINALIZING`, together with
elapsed time and factual item counts when the current operation knows them.
Unknown-duration work remains indeterminate; simulated percentage animation is
not allowed. Before native FBX import, the monitor marks the operation as
blocking and tells the user that Blender may temporarily stop responding.
Grouped provider imports share the parent session and cannot clear it early.
Terminal success or failure clears the foreground status text while preserving
the final state and structured console transition log for diagnostics.

### Automatic Sibling Package Discovery

Top-level `.unitypackage` imports, whether started from File > Import or the native 3D View drag-and-drop handler, automatically run a lightweight same-directory sibling discovery after the primary package index is prepared. Discovery follows exact GUID coverage and transitive dependencies. A unique `COMPLETE` plan offers a foreground Import Together / Import Selected Only / Cancel dialog and imports together by default; background runs deterministically as Import Together. `NONE` keeps the import single-package. `PARTIAL` offers the same foreground choice but defaults to Primary Only; background never guesses. `AMBIGUOUS` never auto-selects a provider. Internal grouped child imports set `group_child` and do not rediscover siblings.

Material-only / Texture-only Packageは、対応assetが1件以上あれば`FINISHED`とし、空またはunsupported Packageだけを明確なERRORとする。未解決Dependencyは`unitypackage_dependency_registry`へ保存し、`.blend` save/reopen後も再解決可能とする。

今回のproduction対象はMaterial、Texture、Rendererのみ。Animator、PhysBone、Contact、MonoBehaviour、Unity Finalizer、UnityPackage Exporterは対象外である。
