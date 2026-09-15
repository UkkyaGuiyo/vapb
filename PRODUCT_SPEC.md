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

Missing files return `MISSING_SOURCE`; dirty images refuse reload with `UNSAVED_CHANGES`; packed images return `PACKED_SOURCE_CONFLICT`. No fallback search, automatic copy/backup, GUID or `.meta` creation, auto-packing, watcher, or background polling is part of this workflow. For editable source files, import with `Keep Extracted` enabled.

## Texture Policy

Textureは元Assetを直接編集する前提とする。Addonは`Face_copy.png`等の自動派生ファイルや自動バックアップを作成しない。source asset path、source GUID、source `.meta` identityを保持し、バックアップ責任はユーザー側に置く。

## Material Policy

Materialの表示はBlender上の近似でよい。ただしUnity Asset identity、Renderer slot binding、Material GUID、Texture GUIDの追跡を優先する。「見た目が似ているMaterial」より、元Unity Rendererの参照関係を正本とする。

## Identity Policy

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

## Current Scope Boundary

BUG-002のMaterial / Texture binding修正は本Baseline移行の対象外とする。今回の変更は仕様、設計、テスト基準、ドキュメントの固定に限り、機能コードの挙動を変更しない。
