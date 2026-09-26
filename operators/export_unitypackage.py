"""Explicit, bounded static-mesh UnityPackage roundtrip with isolated staging."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import tempfile

import bpy
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix

from ..blender.fbx_receipt import RawFbxSemanticIndex
from ..blender.identity_registry import load_scene_registry
from ..blender.renderer_binding import validate_existing_binding
from ..export.direct_renderer import direct_renderer_task
from ..export.skin_renderer import skin_renderer_task
from ..export.model_package import SourcePackage, ModelReplacement, materialize_model_package
from ..export.package_writer import UnityPackageWriter
from ..export.raw_assets import RawAssetRepository
from ..export.staging import StagedUnityAsset


def _materials(mesh, package_id, assets):
    result = []
    for slot in mesh.material_slots:
        material = slot.material
        if material is None:
            result.append(None)
            continue
        if material.get('unity_source_package_id') != package_id:
            raise ValueError('素材の出所Packageが異なります。依存Packageの書き出しは未対応です')
        guid = material.get('unity_material_guid', '')
        file_id = material.get('unity_material_file_id', '')
        if not guid or not file_id or not any(a.guid == guid for a in assets):
            raise ValueError('素材の元Assetを確認できません。新規素材はこの経路では未対応です')
        result.append({'guid': guid, 'file_id': str(file_id)})
    return result


def _export_staged_mesh(context, source, output):
    """Copy geometry into a disposable scene; never export private source paths."""
    scene = bpy.data.scenes.new('VAPB Export Staging')
    obj = None
    data = None
    try:
        data = source.data.copy()
        obj = source.copy()
        obj.data = data
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.modifiers.clear()
        obj.animation_data_clear()
        for block in (obj, data):
            for key in list(block.keys()):
                del block[key]
        obj['_vapb_fbx_realization_id'] = source['_vapb_fbx_realization_id']
        scene.collection.objects.link(obj)
        scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
        layer = scene.view_layers[0]
        layer.objects.active = obj
        with context.temp_override(scene=scene, view_layer=layer):
            obj.select_set(True)
            result = bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True,
                object_types={'MESH'}, use_mesh_modifiers=False, use_custom_props=True,
                bake_anim=False, bake_space_transform=False, path_mode='STRIP', embed_textures=False)
        if result != {'FINISHED'} or not output.is_file():
            raise ValueError('FBXの書き出しに失敗しました')
    finally:
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
        bpy.data.scenes.remove(scene)


def _export_staged_skin(context, source, armature, output, skin_binding):
    """Export a private rest-pose rig/mesh copy carrying only allowed identity markers."""
    scene = bpy.data.scenes.new('VAPB Skin Export')
    scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
    copies, data_blocks = [], []
    try:
        rig = armature.copy()
        copies.append(rig)
        rig.data = armature.data.copy()
        data_blocks.append(rig.data)
        scene.collection.objects.link(rig)
        rig.parent = None
        rig.matrix_world = armature.matrix_world.copy()
        rig.animation_data_clear()
        mesh = source.copy()
        copies.append(mesh)
        mesh.data = source.data.copy()
        data_blocks.append(mesh.data)
        scene.collection.objects.link(mesh)
        mesh.parent = rig
        mesh.matrix_world = source.matrix_world.copy()
        mesh.animation_data_clear()
        for modifier in mesh.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
        for block in (rig, rig.data, mesh, mesh.data):
            for key in list(block.keys()):
                del block[key]
        mesh['_vapb_fbx_realization_id'] = source['_vapb_fbx_realization_id']
        allowed = {row['edited_bone_realization_id'] for row in skin_binding['mappings']}
        for bone in rig.data.bones:
            for key in list(bone.keys()):
                del bone[key]
        for pose_bone in rig.pose.bones:
            realization = pose_bone.get('_vapb_fbx_bone_realization_id')
            for key in list(pose_bone.keys()):
                del pose_bone[key]
            if realization in allowed:
                pose_bone['_vapb_fbx_bone_realization_id'] = realization
            pose_bone.matrix_basis.identity()
        layer = scene.view_layers[0]
        layer.objects.active = mesh
        with context.temp_override(scene=scene, view_layer=layer, object=mesh, active_object=mesh,
                                   selected_objects=copies, selected_editable_objects=copies):
            for obj in copies:
                obj.select_set(True)
            layer.update()
            result = bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True,
                object_types={'MESH', 'ARMATURE'}, use_mesh_modifiers=False,
                use_custom_props=True, add_leaf_bones=False, use_armature_deform_only=False,
                bake_anim=False, bake_space_transform=False, path_mode='STRIP', embed_textures=False)
        if result != {'FINISHED'} or not output.is_file():
            raise ValueError('Skin FBXの書き出しに失敗しました')
    finally:
        for obj in reversed(copies):
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in data_blocks:
            if data.users == 0:
                (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.armatures).remove(data)
        bpy.data.scenes.remove(scene)


def export_skin_package(context, mesh, output):
    from ..blender.renderer_binding import validate_skin_binding
    if context.mode != 'OBJECT' or mesh is None or mesh.type != 'MESH':
        raise ValueError('オブジェクトモードで確定済みのSkin Meshを選択してください')
    if Path(output).exists():
        raise ValueError('出力先が既にあります。新しいファイル名を指定してください')
    modifiers = [mod for mod in mesh.modifiers if mod.type == 'ARMATURE']
    if len(modifiers) != 1 or len(mesh.modifiers) != 1 or modifiers[0].object is None:
        raise ValueError('この経路では一つのArmature Modifierだけを使用できます')
    rig = modifiers[0].object
    if mesh.constraints or rig.constraints or any(pose.constraints for pose in rig.pose.bones):
        raise ValueError('Constraint付きSkinの出力変形は未確認です')
    if modifiers[0].use_bone_envelopes:
        raise ValueError('Envelopeによる変形はこのSkin経路では未対応です')
    binding = json.loads(mesh.get('_vapb_renderer_binding', '{}'))
    roots = [obj for obj in context.scene.objects if obj.get('_vapb_renderer_occurrences')
             and obj.get('_vapb_root_context_id') == binding.get('root_context_id')]
    if len(roots) != 1:
        raise ValueError('Renderer対応のルートが見つからないか重複しています')
    binding = validate_existing_binding(binding, roots[0], mesh, bpy.data.objects)
    skin = validate_skin_binding(mesh, roots[0], bpy.data.objects)
    package_id = binding['mesh_receipt']['source_package_id']
    if binding['source_package_id'] != package_id:
        raise ValueError('Packageを跨ぐSkin復元は現在未対応です')
    package = load_scene_registry(context.scene).packages.get(package_id)
    if not package:
        raise ValueError('元Packageの保存情報がありません')
    source = SourcePackage(Path(package['source_archive_path']), package['package_sha256'])
    source_bytes = source.path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source.expected_sha256:
        raise ValueError('保存済み原本のハッシュが変わっています')
    assets = RawAssetRepository(source.path).read_all(source_bytes)
    task = skin_renderer_task(binding, skin, _materials(mesh, package_id, assets), assets)
    original = next(asset for asset in assets if asset.guid == task['source_model_guid'])
    guid = hashlib.sha256(('VAPB_EDITED_SKIN_V1:' + package_id + ':' +
                          task['realization_id']).encode()).hexdigest()[:32]
    path = f'Assets/VAPBExport/EditedSkin_{guid}.fbx'
    with tempfile.TemporaryDirectory(prefix='vapb_skin_export_') as temporary:
        target = Path(temporary) / 'edited.fbx'
        _export_staged_skin(context, mesh, rig, target, skin)
        payload = target.read_bytes()
    task['model_guid'] = guid
    task['model_sha256'] = hashlib.sha256(payload).hexdigest()
    tree, manifest = materialize_model_package([source], [], generator_version='0.4.0',
                                               blender_version=bpy.app.version_string)
    meta, replacements = re.subn(rb'(?m)^guid:\s*[0-9a-fA-F]{32}\s*$',
                                ('guid: ' + guid).encode(), original.meta_bytes)
    if replacements != 1:
        raise ValueError('元モデルのImporter設定を安全に複製できません')
    tree.add(StagedUnityAsset(guid, path, payload, meta, asset_type='MESH_ASSET',
                             operation='CREATE', strategy='REGENERATE_FROM_BLENDER'))
    manifest = replace(manifest, renderer_mappings=(binding,), reference_rebind_tasks=(task,),
        export_assets=manifest.export_assets + ({'node_id': path, 'node_type': 'MESH_ASSET',
            'operation': 'CREATE', 'strategy': 'REGENERATE_FROM_BLENDER', 'desired_export_path': path,
            'source_identity': {'source_guid': original.guid, 'source_package_id': package_id},
            'export_identity': {'export_guid': guid}},),
        warnings=manifest.warnings + ('SOURCE_SKELETON_PRESERVED', 'UNITY_FINALIZER_REQUIRED'))
    return _write_package(tree, manifest, output)


def export_model_skin_package(context, mesh, output):
    """Defer model Renderer identity to Unity while preserving source assets."""
    from ..blender.fbx_witness import prepare_witness
    from ..blender.fbx_receipt import RECEIPT_VERSION
    from ..export.model_skin import model_skin_task
    if context.mode != 'OBJECT' or mesh is None or mesh.type != 'MESH':
        raise ValueError('オブジェクトモードでモデル由来のSkin Meshを選択してください')
    if Path(output).exists():
        raise ValueError('出力先が既にあります。新しいファイル名を指定してください')
    if mesh.library or mesh.data.library or len(mesh.users_scene) != 1:
        raise ValueError('リンクされたMeshや複数SceneのMeshはこの経路では未対応です')
    if (mesh.get('_vapb_fbx_receipt_version') != RECEIPT_VERSION or
            mesh.data.get('_vapb_fbx_receipt_version') != RECEIPT_VERSION or
            any(not mesh.get(key) or mesh.get(key) != mesh.data.get(key) for key in
                ('_vapb_fbx_source_asset_sha256', '_vapb_fbx_geometry_uid', '_vapb_fbx_mesh_receipt_id'))):
        raise ValueError('MeshデータとObjectの作成時出所記録が一致しません')
    modifiers = list(mesh.modifiers)
    if len(modifiers) != 1 or modifiers[0].type != 'ARMATURE' or not modifiers[0].object:
        raise ValueError('このモデルSkin経路は一つのArmature Modifierが必要です')
    rig = modifiers[0].object
    if (rig.library or rig.data.library or mesh.constraints or rig.constraints or
            any(pose.constraints for pose in rig.pose.bones) or modifiers[0].use_bone_envelopes):
        raise ValueError('Constraint・リンク・Envelope付きSkinはこの復元経路では未対応です')
    realization = mesh.get('_vapb_fbx_realization_id', '')
    if not realization or sum(o.get('_vapb_fbx_realization_id') == realization for o in bpy.data.objects) != 1:
        raise ValueError('Meshの実体識別子がないか重複しています')
    context_id = mesh.get('_vapb_root_context_id', '')
    roots = [o for o in context.scene.objects if o.get('_vapb_renderer_occurrences')
             and o.get('_vapb_root_context_id') == context_id]
    if not context_id or len(roots) != 1 or rig.get('_vapb_root_context_id') != context_id:
        raise ValueError('選択したSkinのPrefabルートまたはArmatureの所属が不明です')
    edges = json.loads(mesh.get('_vapb_model_instance_edge_path', '[]'))
    if not isinstance(edges, list) or not edges or edges != json.loads(rig.get('_vapb_model_instance_edge_path', '[]')):
        raise ValueError('MeshとArmatureのモデルインスタンス経路が一致しません')
    root_guid = roots[0].get('unity_composition_member_id', '')
    if (not root_guid or root_guid != mesh.get('unity_composition_member_id') or
            root_guid != edges[0].get('container_asset_guid')):
        raise ValueError('選択ルートとモデルインスタンスの元Prefabが一致しません')
    package_id = mesh.get('unity_source_package_id', '')
    if (roots[0].get('unity_source_package_id') != package_id or
            any(edge.get('container_package_id') != package_id for edge in edges)):
        raise ValueError('Packageを跨ぐモデルSkinの復元はこの経路では未対応です')
    package = load_scene_registry(context.scene).packages.get(package_id)
    if not package:
        raise ValueError('元Packageの保存情報がありません')
    source = SourcePackage(Path(package['source_archive_path']), package['package_sha256'])
    source_bytes = source.path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source.expected_sha256:
        raise ValueError('保存済み原本のハッシュが変わっています')
    assets = RawAssetRepository(source.path).read_all(source_bytes)
    source_guid = mesh.get('_vapb_fbx_source_asset_guid', '')
    source_sha = mesh.get('_vapb_fbx_source_asset_sha256', '')
    metadata = {
        'prefab_guid': mesh.get('unity_composition_member_id', ''),
        'prefab_source_sha256': edges[0].get('container_revision_sha256', ''),
        'source_model_guid': source_guid, 'source_model_sha256': source_sha,
        'source_model_uid': mesh.get('_vapb_fbx_model_uid', ''),
        'source_geometry_uid': mesh.get('_vapb_fbx_geometry_uid', ''),
        'realization_id': realization,
        'instance_edges': [{'container_guid': e.get('container_asset_guid', ''),
                            'container_sha256': e.get('container_revision_sha256', ''),
                            'instance_file_id': str(e.get('prefab_instance_file_id', '')),
                            'source_guid': e.get('source_prefab_guid', '')} for e in edges],
    }
    bones = []
    for bone in rig.data.bones:
        pose = rig.pose.bones.get(bone.name)  # Same native bone, not a Unity identity lookup.
        keys = ('_vapb_fbx_source_asset_guid', '_vapb_fbx_source_asset_sha256',
                '_vapb_fbx_model_uid', '_vapb_fbx_bone_realization_id')
        if pose is None or any(not bone.get(k) or str(bone.get(k)) != str(pose.get(k)) for k in keys):
            raise ValueError('Bone作成時の出所記録を確認できません')
        if bone[keys[0]] != source_guid or bone[keys[1]] != source_sha:
            raise ValueError('元モデルと異なるBoneはこの復元経路では未対応です')
        bones.append({'edited_bone_realization_id': str(bone[keys[3]]),
                      'source_model_uid': str(bone[keys[2]])})
    task = model_skin_task(metadata, bones, assets)
    original = next(a for a in assets if a.guid == task['source_model_guid'])
    guid = hashlib.sha256(('VAPB_MODEL_SKIN_V1:' + package_id + ':' + realization).encode()).hexdigest()[:32]
    path = f'Assets/VAPBExport/EditedSkin_{guid}.fbx'
    witness_base = f'Assets/VAPBExport/Witness_{guid}'
    with tempfile.TemporaryDirectory(prefix='vapb_model_skin_') as temporary:
        folder = Path(temporary)
        raw = folder / 'source.fbx'
        raw.write_bytes(original.asset_bytes)
        index = RawFbxSemanticIndex.from_file(raw)
        if (not index.unique_source_model(int(task['source_model_uid'])) or
                index.geometry_for_model(int(task['source_model_uid'])) != int(task['source_geometry_uid'])):
            raise ValueError('元FBXのModelとGeometryの関係を確認できません')
        noop, witness = folder / 'noop.fbx', folder / 'witness.fbx'
        task['source_model_uids'] = prepare_witness(raw, noop, witness)
        if not {b['source_model_uid'] for b in bones} <= set(task['source_model_uids']):
            raise ValueError('BoneのModel UIDが元FBXにありません')
        edited = folder / 'edited.fbx'
        _export_staged_skin(context, mesh, rig, edited, {'mappings': bones})
        payload, noop_bytes, witness_bytes = edited.read_bytes(), noop.read_bytes(), witness.read_bytes()
    task.update(model_guid=guid, model_sha256=hashlib.sha256(payload).hexdigest(),
                witness_noop_path=witness_base + '_Noop.bytes',
                witness_noop_sha256=hashlib.sha256(noop_bytes).hexdigest(),
                witness_path=witness_base + '_Source.bytes',
                witness_sha256=hashlib.sha256(witness_bytes).hexdigest())
    tree, manifest = materialize_model_package([source], [], generator_version='0.4.0',
                                               blender_version=bpy.app.version_string)
    meta, replacements = re.subn(rb'(?m)^guid:\s*[0-9a-fA-F]{32}\s*$',
                                ('guid: ' + guid).encode(), original.meta_bytes)
    if replacements != 1:
        raise ValueError('元モデルのImporter設定を安全に複製できません')
    tree.add(StagedUnityAsset(guid, path, payload, meta, asset_type='MESH_ASSET',
                             operation='CREATE', strategy='REGENERATE_FROM_BLENDER'))
    generated = [(path, guid, 'MESH_ASSET')]
    for field, data in (('witness_noop_path', noop_bytes), ('witness_path', witness_bytes)):
        destination = task[field]
        asset_guid = hashlib.sha256(('VAPB_WITNESS_V1:' + destination).encode()).hexdigest()[:32]
        tree.add(StagedUnityAsset(asset_guid, destination, data,
                                 f'fileFormatVersion: 2\nguid: {asset_guid}\n'.encode(), operation='CREATE'))
        generated.append((destination, asset_guid, 'GENERATED_EXPORT_SUPPORT'))
    manifest = replace(manifest, reference_rebind_tasks=(task,),
        export_assets=manifest.export_assets + tuple({'node_id': p, 'node_type': kind,
            'operation': 'CREATE', 'strategy': 'REGENERATE_FROM_BLENDER',
            'desired_export_path': p, 'export_identity': {'export_guid': g}}
            for p, g, kind in generated),
        warnings=manifest.warnings + ('SOURCE_RAW_PRESERVED', 'UNITY_MODEL_IDENTITY_CHECK_REQUIRED',
                                     'NEW_PREFAB_VARIANT', 'MODEL_SKIN_GEOMETRY_ONLY'))
    return _write_package(tree, manifest, output)


def export_static_package(context, mesh, output):
    if context.mode != 'OBJECT' or mesh is None or mesh.type != 'MESH':
        raise ValueError('オブジェクトモードで確定済みのメッシュを一つ選択してください')
    if mesh.data.shape_keys is not None or len(mesh.modifiers):
        raise ValueError('この経路はShape Key・Modifierのない静的メッシュのみ対応しています')
    if Path(output).exists():
        raise ValueError('出力先が既にあります。新しいファイル名を指定してください')
    binding = json.loads(mesh.get('_vapb_renderer_binding', '{}'))
    roots = [o for o in context.scene.objects if o.get('_vapb_renderer_occurrences')
             and o.get('_vapb_root_context_id') == binding.get('root_context_id')]
    if len(roots) != 1:
        raise ValueError('Renderer対応のルートが見つからないか重複しています')
    binding = validate_existing_binding(binding, roots[0], mesh, bpy.data.objects)
    package_id = binding['mesh_receipt']['source_package_id']
    if binding['source_package_id'] != package_id:
        raise ValueError('Packageを跨ぐRenderer復元はこの経路では未対応です')
    package = load_scene_registry(context.scene).packages.get(package_id)
    if not package:
        raise ValueError('元Packageの保存情報がありません')
    source = SourcePackage(Path(package['source_archive_path']), package['package_sha256'])
    source_bytes = source.path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source.expected_sha256:
        raise ValueError('保存済み原本のハッシュが変わっています')
    assets = RawAssetRepository(source.path).read_all(source_bytes)
    task = direct_renderer_task(binding, _materials(mesh, package_id, assets), assets)
    original = next(a for a in assets if a.guid == task['model_guid'])
    with tempfile.TemporaryDirectory(prefix='vapb_export_') as temporary:
        original_fbx = Path(temporary) / 'source.fbx'
        original_fbx.write_bytes(original.asset_bytes)
        links = RawFbxSemanticIndex.from_file(original_fbx).links
        expected = (int(binding['mesh_receipt']['fbx_model_uid']), int(binding['mesh_receipt']['fbx_geometry_uid']))
        if len(links) != 1 or (links[0].model_uid, links[0].geometry_uid) != expected:
            raise ValueError('この経路は一つのMeshを含む元FBXだけに対応しています')
        edited_fbx = Path(temporary) / 'edited.fbx'
        _export_staged_mesh(context, mesh, edited_fbx)
        task['model_sha256'] = hashlib.sha256(edited_fbx.read_bytes()).hexdigest()
        replacement = ModelReplacement(package_id, original.guid,
            binding['mesh_receipt']['source_sha256'], edited_fbx.read_bytes(),
            {'renderer_mappings': [binding]})
        tree, manifest = materialize_model_package([source], [replacement],
            generator_version='0.4.0', blender_version=bpy.app.version_string)
    manifest = replace(manifest, reference_rebind_tasks=(task,),
        warnings=manifest.warnings + ('STATIC_MESH_GEOMETRY_ONLY', 'UNITY_FINALIZER_REQUIRED'))
    return _write_package(tree, manifest, output)


def _write_package(tree, manifest, output):
    first_party = Path(__file__).resolve().parents[1] / 'unity_editor'
    generated = [
        ('Assets/VAPBExport/VapbRealizationMarker.cs', (first_party / 'VapbRealizationMarker.cs').read_bytes()),
        ('Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs',
         (first_party / 'Editor/VapbReferenceFinalizer.cs').read_bytes())]
    generated.append(('Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs',
                      (first_party / 'Editor/VapbModelSkinFinalizer.cs').read_bytes()))
    manifest_path = 'Assets/VAPBExport/manifest.json'
    generated_paths = [manifest_path] + [p for p, _ in generated]
    generated_guids = {p: hashlib.sha256(('VAPB_EXPORT_HELPER_V1:' + p).encode()).hexdigest()[:32]
                       for p in generated_paths}
    manifest = replace(manifest, export_assets=manifest.export_assets + tuple({
        'node_id': p, 'node_type': 'GENERATED_EXPORT_SUPPORT', 'operation': 'CREATE',
        'strategy': 'REGENERATE_FROM_BLENDER', 'desired_export_path': p,
        'export_identity': {'export_guid': generated_guids[p]},
    } for p in generated_paths))
    generated.insert(0, (manifest_path, manifest.to_json().encode('utf-8')))
    for pathname, payload in generated:
        guid = generated_guids[pathname]
        tree.add(StagedUnityAsset(guid, pathname, payload,
            f'fileFormatVersion: 2\nguid: {guid}\n'.encode('ascii'), operation='CREATE'))
    UnityPackageWriter().write(tree, Path(output))
    return manifest


class VAPB_OT_export_unitypackage(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.vapb_unitypackage'
    bl_label = 'UnityPackage（Mesh・Skin参照復元）'
    bl_description = 'Mesh・Skinを書き出し、Unityで出所と参照を確認して復元します'
    filename_ext = '.unitypackage'
    filter_glob: bpy.props.StringProperty(default='*.unitypackage', options={'HIDDEN'})

    def draw(self, context):
        model_skin = context.active_object and context.active_object.get('_vapb_model_instance_edge_path')
        if model_skin:
            self.layout.label(text='対象: アクティブなモデル由来Skin Mesh一つ')
            self.layout.label(text='Unityで出所を確認し、新しいPrefab Variantへ復元します')
            self.layout.label(text='原本・骨階層・素材を保持。形状とウェイトの編集が対象です')
            self.layout.label(text='頂点構成・Shape Key構成・骨階層の変更はこの経路では未対応')
        else:
            self.layout.label(text='対象: アクティブな確定済みMesh一つ')
            self.layout.label(text='Skinは骨対応の確認が必要。Unityの既存骨階層・restを保持')
            self.layout.label(text='形状・ウェイト・素材を出力。新規骨・Nestedは未対応')
        self.layout.label(text='保持済みPackageの原本資産も全件含みます')
        self.layout.label(text='Unity import後にmanifestを選択しVAPB復元メニューを実行')

    def execute(self, context):
        try:
            mesh = context.active_object
            binding = json.loads(mesh.get('_vapb_renderer_binding', '{}')) if mesh else {}
            if mesh and mesh.get('_vapb_model_instance_edge_path'):
                export_model_skin_package(context, mesh, self.filepath)
            elif binding.get('occurrence', {}).get('renderer_class_id') == 137:
                export_skin_package(context, mesh, self.filepath)
            else:
                export_static_package(context, mesh, self.filepath)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            self.report({'ERROR'}, f'書き出しを停止しました: {exc}')
            return {'CANCELLED'}
        self.report({'INFO'}, 'UnityPackageを書き出しました。Unity側の参照復元が必要です')
        return {'FINISHED'}


CLASSES = (VAPB_OT_export_unitypackage,)


def menu_export(self, context):
    self.layout.operator(VAPB_OT_export_unitypackage.bl_idname, text='VAPB UnityPackage（Mesh / Skin）')
