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
from ..export.model_package import SourcePackage, ModelReplacement, TextureReplacement, materialize_model_package
from ..export.package_writer import UnityPackageWriter
from ..export.raw_assets import RawAssetRepository
from ..export.staging import StagedUnityAsset
from ..export.final_state_package import export_final_state_package, _material_texture_guids, _material_data
from ..export.material_naming import allocate_material_paths
from ..blender.material_owner_usage import proven_owners
from ..export.triangle_staging import frozen_export_meshes


def _materials(mesh, package_id, assets):
    result = []
    sources = {asset.guid: asset for asset in assets}
    # Same reserved Unity resource GUIDs as the existing Skin/direct closure checks.
    builtins = {'0' * 32, '0000000000000000e000000000000000', '0000000000000000f000000000000000'}
    for slot in mesh.material_slots:
        material = slot.material
        if material is None:
            result.append(None)
            continue
        if material.get('unity_source_package_id') != package_id:
            raise ValueError('素材の出所Packageが異なります。依存Packageの書き出しは未対応です')
        guid = material.get('unity_material_guid', '')
        file_id = material.get('unity_material_file_id', '')
        source = sources.get(guid)
        if not guid or not file_id or source is None:
            raise ValueError('素材の元Assetを確認できません。新規素材はこの経路では未対応です')
        # Unity serialized state is authoritative even for unpreviewed properties.
        # Inspect only selected .mat assets; do not reinterpret embedded FBX Materials.
        if source.pathname.lower().endswith('.mat'):
            missing = _material_texture_guids(source.asset_bytes) - sources.keys() - builtins
            if missing:
                raise ValueError('素材のTexture参照を元Package内で解決できません。依存Textureの欠落した出力は作成しません')
        result.append({'guid': guid, 'file_id': str(file_id)})
    return result


def _working_textures(mesh, package_id, assets, *, additional_meshes=()):
    """Read source-identified working images without saving over their files."""
    images, visited = {}, set()

    def visit(tree):
        if tree is None or tree.as_pointer() in visited:
            return
        visited.add(tree.as_pointer())
        for node in tree.nodes:
            image = getattr(node, 'image', None)
            if image is not None:
                images[image.as_pointer()] = image
            if node.type == 'GROUP':
                visit(node.node_tree)

    for selected in (mesh, *additional_meshes):
        for slot in selected.material_slots:
            if slot.material is not None:
                visit(slot.material.node_tree)
    sources = {asset.guid: asset for asset in assets}
    providers = {}
    replacements = []
    for image in images.values():
        guid = image.get('unity_guid', '')
        asset = sources.get(guid)
        if (image.get('unity_source_package_id') != package_id or asset is None or
                image.get('unity_asset_path') != asset.pathname or
                not re.search(rb'(?m)^TextureImporter:\s*$', asset.meta_bytes)):
            raise ValueError('画像の元Package・Texture Assetを確認できません。新規画像の追加は未対応です')
        if image.library or image.source != 'FILE':
            raise ValueError('リンク画像・連番・UDIM画像はこの書き出し経路では未対応です')
        if image.is_dirty:
            formats = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.tga': 'TARGA',
                       '.tif': 'TIFF', '.tiff': 'TIFF', '.bmp': 'BMP', '.exr': 'OPEN_EXR'}
            suffix = Path(asset.pathname).suffix.lower()
            if formats.get(suffix) != image.file_format:
                raise ValueError('編集中の画像形式を元Textureの形式で保存できません')
            with tempfile.TemporaryDirectory(prefix='vapb_texture_export_') as temporary:
                target = Path(temporary) / ('texture' + suffix)
                image.save(filepath=str(target), save_copy=True)
                encoded = target.read_bytes()
        elif image.packed_file is not None:
            encoded = bytes(image.packed_file.data)
        else:
            current = Path(bpy.path.abspath(image.filepath)).resolve()
            source_path = image.get('unity_source_path', '')
            if not source_path or current != Path(source_path).resolve() or not current.is_file():
                raise ValueError('作業Textureファイルの出所または保存先を確認できません')
            encoded = current.read_bytes()
        if not encoded:
            raise ValueError('作業Textureの画像データが空です')
        if guid in providers and providers[guid] != encoded:
            raise ValueError('同一Textureに異なる編集画像があります。出力を一意に選べません')
        if guid not in providers and encoded != asset.asset_bytes:
            replacements.append(TextureReplacement(package_id, guid,
                hashlib.sha256(asset.asset_bytes).hexdigest(), encoded))
        providers[guid] = encoded
    return replacements


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
        with context.temp_override(scene=scene, view_layer=layer, selected_objects=[obj],
                                   selected_editable_objects=[obj], active_object=obj, object=obj):
            obj.select_set(True)
            with frozen_export_meshes([obj]):
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


def _validate_skin_subset(mesh, armature, allowed, parent_mapping=None):
    selected = {bone.name for bone in armature.data.bones
                if armature.pose.bones[bone.name].get('_vapb_fbx_bone_realization_id') in allowed}
    if len(selected) != len(allowed) or not selected:
        raise ValueError('元SkinのBoneを一意に取得できません')
    roots = 0
    excluded_groups = set()
    for bone in armature.data.bones:
        if bone.name in selected:
            if not bone.use_deform:
                raise ValueError('元SkinのBoneで変形が無効化されています')
            if bone.parent is None:
                roots += 1
            elif bone.parent.name not in selected:
                raise ValueError('元Skin外の親Boneを必要とする構造は未対応です')
        elif (group := mesh.vertex_groups.get(bone.name)) is not None:
            excluded_groups.add(group.index)
    if roots != 1 and not (roots >= 2 and parent_mapping):
        raise ValueError('元SkinのルートBoneを一意に取得できません')
    if any(group.group in excluded_groups and group.weight != 0
           for vertex in mesh.data.vertices for group in vertex.groups):
        raise ValueError('元Skin外のBoneに追加されたウェイトはこの経路では未対応です')


def _export_staged_skin(context, source, armature, output, skin_binding, *,
                        scale_options='FBX_SCALE_NONE', source_skin_only=False, material_bindings=None):
    """Export a private rest-pose rig/mesh copy carrying only allowed identity markers."""
    allowed = {row['edited_bone_realization_id'] for row in skin_binding['mappings']}
    if source_skin_only:
        _validate_skin_subset(source, armature, allowed, skin_binding.get('parent_transform_mapping'))
    scene = bpy.data.scenes.new('VAPB Skin Export')
    scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
    copies, data_blocks, material_copies = [], [], []
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
        if material_bindings:
            if len(material_bindings) != len(mesh.material_slots):
                raise ValueError('Material transport slot count changed')
            material_by_label = {}
            for slot, binding in zip(mesh.material_slots, material_bindings):
                label = binding['transport_id']
                if slot.material is None:
                    raise ValueError('Material transport source is unavailable')
                if label not in material_by_label:
                    material = slot.material.copy()
                    material_copies.append(material)
                    material.name = label
                    if material.name != label:
                        raise ValueError('Material transport label is occupied')
                    material_by_label[label] = material
                slot.material = material_by_label[label]
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
        if parent := skin_binding.get('parent_transform_mapping'):
            rig['_vapb_fbx_realization_id'] = parent['edited_transform_realization_id']
        for bone in rig.data.bones:
            if source_skin_only:
                bone.use_deform = rig.pose.bones[bone.name].get('_vapb_fbx_bone_realization_id') in allowed
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
            with frozen_export_meshes([mesh]):
                result = bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True,
                    object_types={'MESH', 'ARMATURE'}, use_mesh_modifiers=False,
                    use_custom_props=True, add_leaf_bones=False, use_armature_deform_only=source_skin_only,
                    bake_anim=False, bake_space_transform=False, apply_scale_options=scale_options,
                    path_mode='STRIP', embed_textures=False)
        if result != {'FINISHED'} or not output.is_file():
            raise ValueError('Skin FBXの書き出しに失敗しました')
        if skin_binding.get('parent_transform_mapping'):
            from ..blender.fbx_witness import preserve_skin_cluster_order
            preserve_skin_cluster_order(output, skin_binding['mappings'],
                                        skin_binding['source_skin_cluster_order'])
    finally:
        for obj in reversed(copies):
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in data_blocks:
            if data.users == 0:
                (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.armatures).remove(data)
        for material in material_copies:
            if material.users == 0:
                bpy.data.materials.remove(material)
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
    _reject_untransported_skin_animation(mesh, rig)
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
        blender_version=bpy.app.version_string,
        texture_replacements=_working_textures(mesh, package_id, assets))
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


def _reject_untransported_skin_animation(mesh, rig):
    # Existing Skin routes emit rest-pose copies, with no authored clip/driver recipe.
    animation_owners = (mesh, mesh.data, mesh.data.shape_keys, rig, rig.data)
    if any((data := getattr(owner, 'animation_data', None)) is not None and
           (data.action is not None or data.drivers or data.nla_tracks)
           for owner in animation_owners):
        raise ValueError('編集AnimationのUnity復帰は未対応です。ClipやDriverを破棄せず出力を停止しました')


def _prepare_model_skin(context, mesh, assets, *, direct=False, source_model=False):
    """Defer model Renderer identity to Unity while preserving source assets."""
    from ..blender.fbx_witness import prepare_witness, source_export_scale_options, source_skin_bone_uids, source_skin_shared_parent
    from ..blender.fbx_receipt import RECEIPT_VERSION
    from ..export.model_skin import model_skin_task, direct_skin_task, source_model_skin_task, model_skin_material_bindings
    if context.mode != 'OBJECT' or mesh is None or mesh.type != 'MESH':
        raise ValueError('オブジェクトモードでモデル由来のSkin Meshを選択してください')
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
    _reject_untransported_skin_animation(mesh, rig)
    if (rig.library or rig.data.library or mesh.constraints or rig.constraints or
            any(pose.constraints for pose in rig.pose.bones) or modifiers[0].use_bone_envelopes):
        raise ValueError('Constraint・リンク・Envelope付きSkinはこの復元経路では未対応です')
    realization = mesh.get('_vapb_fbx_realization_id', '')
    if not realization or sum(o.get('_vapb_fbx_realization_id') == realization for o in bpy.data.objects) != 1:
        raise ValueError('Meshの実体識別子がないか重複しています')
    package_id = mesh.get('unity_source_package_id', '')
    if source_model:
        if (not package_id or rig.get('unity_source_package_id') != package_id or
                any(mesh.get(key) or rig.get(key) for key in
                    ('_vapb_root_context_id', 'unity_composition_member_id', '_vapb_model_instance_edge_path'))):
            raise ValueError('Source-model Skin provenance is incomplete or carries Prefab context')
        edges = []
    else:
        context_id = mesh.get('_vapb_root_context_id', '')
        roots = [o for o in context.scene.objects if o.get('_vapb_renderer_occurrences')
                 and o.get('_vapb_root_context_id') == context_id]
        if not context_id or len(roots) != 1 or rig.get('_vapb_root_context_id') != context_id:
            raise ValueError('選択したSkinのPrefabルートまたはArmatureの所属が不明です')
        edges = json.loads(mesh.get('_vapb_model_instance_edge_path', '[]'))
        if (not isinstance(edges, list) or bool(edges) == direct or
                edges != json.loads(rig.get('_vapb_model_instance_edge_path', '[]'))):
            raise ValueError('MeshとArmatureのモデルインスタンス経路が一致しません')
        root_guid = roots[0].get('unity_composition_member_id', '')
        if (not root_guid or root_guid != mesh.get('unity_composition_member_id') or
                (not direct and root_guid != edges[0].get('container_asset_guid'))):
            raise ValueError('選択ルートとモデルインスタンスの元Prefabが一致しません')
        package_id = mesh.get('unity_source_package_id', '')
        if (roots[0].get('unity_source_package_id') != package_id or
                any(edge.get('container_package_id') != package_id for edge in edges)):
            raise ValueError('Packageを跨ぐモデルSkinの復元はこの経路では未対応です')
        prefabs = [a for a in assets if a.guid == root_guid]
        if len(prefabs) != 1:
            raise ValueError('元Prefabを一意に取得できません')
    source_guid = mesh.get('_vapb_fbx_source_asset_guid', '')
    source_sha = mesh.get('_vapb_fbx_source_asset_sha256', '')
    metadata = {
        'source_model_guid': source_guid, 'source_model_sha256': source_sha,
        'source_model_uid': mesh.get('_vapb_fbx_model_uid', ''),
        'source_geometry_uid': mesh.get('_vapb_fbx_geometry_uid', ''),
        'realization_id': realization,
        'instance_edges': [{'container_guid': e.get('container_asset_guid', ''),
                            'container_sha256': e.get('container_revision_sha256', ''),
                            'instance_file_id': str(e.get('prefab_instance_file_id', '')),
                            'source_guid': e.get('source_prefab_guid', '')} for e in edges],
    }
    if not source_model:
        metadata.update(prefab_guid=mesh.get('unity_composition_member_id', ''),
                        prefab_source_sha256=(hashlib.sha256(prefabs[0].asset_bytes).hexdigest()
                                              if direct else edges[0].get('container_revision_sha256', '')))
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
    task = (source_model_skin_task if source_model else direct_skin_task if direct else model_skin_task)(metadata, bones, assets)
    task['material_bindings'] = model_skin_material_bindings(_materials(mesh, package_id, assets))
    original = next(a for a in assets if a.guid == task['source_model_guid'])
    guid = hashlib.sha256(('VAPB_MODEL_SKIN_V1:' + package_id + ':' + realization).encode()).hexdigest()[:32]
    path = f'Assets/VAPBExport/EditedSkin_{guid}.fbx'
    witness_base = f'Assets/VAPBExport/Witness_{guid}'
    with tempfile.TemporaryDirectory(prefix='vapb_model_skin_') as temporary:
        folder = Path(temporary)
        raw = folder / 'source.fbx'
        raw.write_bytes(original.asset_bytes)
        scale_options = source_export_scale_options(raw, context.scene.unit_settings.scale_length)
        index = RawFbxSemanticIndex.from_file(raw)
        if (not index.unique_source_model(int(task['source_model_uid'])) or
                index.geometry_for_model(int(task['source_model_uid'])) != int(task['source_geometry_uid'])):
            raise ValueError('元FBXのModelとGeometryの関係を確認できません')
        source_bone_order = source_skin_bone_uids(raw, task['source_model_uid'],
                                                 task['source_geometry_uid'], ordered=True)
        selected_uids = frozenset(source_bone_order)
        bones = [row for row in task['bone_mappings'] if row['source_model_uid'] in selected_uids]
        if {row['source_model_uid'] for row in bones} != selected_uids:
            raise ValueError('元SkinのBoneをすべて出所記録から取得できません')
        task['bone_mappings'] = bones
        selected_bones = [b for b in rig.data.bones if str(b.get('_vapb_fbx_model_uid')) in selected_uids]
        parent_proof = source_skin_shared_parent(raw, task['source_model_uid'], task['source_geometry_uid'],
                                                allow_single=True) if source_model else None
        if parent_proof is not None:
            from ..blender.fbx_receipt import validate_persistent_transform_receipt
            parent_uid, source_parents = parent_proof
            if (not validate_persistent_transform_receipt(rig)
                    or rig.get('_vapb_fbx_model_uid') != parent_uid
                    or rig.get('_vapb_fbx_source_asset_guid') != source_guid
                    or rig.get('_vapb_fbx_source_asset_sha256') != source_sha
                    or sum(o.get('_vapb_fbx_realization_id') == rig.get('_vapb_fbx_realization_id')
                           for o in bpy.data.objects) != 1):
                raise ValueError('Source Skin parent Transform receipt is missing or ambiguous')
            for bone in selected_bones:
                current_parent = str(bone.parent.get('_vapb_fbx_model_uid')) if bone.parent else parent_uid
                if current_parent != source_parents[str(bone.get('_vapb_fbx_model_uid'))]:
                    raise ValueError('Source Skin bone hierarchy changed')
            metadata['parent_transform_mapping'] = dict(source_model_uid=parent_uid,
                edited_transform_realization_id=rig['_vapb_fbx_realization_id'])
            task['parent_transform_mapping'] = source_model_skin_task(metadata, bones, assets)['parent_transform_mapping']
        noop, witness = folder / 'noop.fbx', folder / 'witness.fbx'
        task['source_model_uids'] = prepare_witness(raw, noop, witness)
        if not {b['source_model_uid'] for b in bones} <= set(task['source_model_uids']):
            raise ValueError('BoneのModel UIDが元FBXにありません')
        edited = folder / 'edited.fbx'
        _export_staged_skin(context, mesh, rig, edited, {'mappings': bones,
                            'parent_transform_mapping': task.get('parent_transform_mapping'),
                            'source_skin_cluster_order': source_bone_order},
                            scale_options=scale_options, source_skin_only=True,
                            material_bindings=task['material_bindings'])
        weight_payloads = []
        if source_model and task.get('parent_transform_mapping'):
            from ..blender.fbx_witness import prepare_export_weight_witness
            weight_noop, weight_stamp = folder / 'weight-noop.fbx', folder / 'weight-stamped.fbx'
            task['weight_transport'] = prepare_export_weight_witness(
                edited, weight_noop, weight_stamp, task['realization_id'], bones)
            for name, data in (('noop', weight_noop.read_bytes()), ('stamped', weight_stamp.read_bytes())):
                destination = witness_base + '_Weight_' + name + '.bytes'
                task['weight_transport'][name + '_path'] = destination
                task['weight_transport'][name + '_sha256'] = hashlib.sha256(data).hexdigest()
                weight_payloads.append((destination, data))
        payload, noop_bytes, witness_bytes = edited.read_bytes(), noop.read_bytes(), witness.read_bytes()
    task.update(model_guid=guid, model_sha256=hashlib.sha256(payload).hexdigest(),
                witness_noop_path=witness_base + '_Noop.bytes',
                witness_noop_sha256=hashlib.sha256(noop_bytes).hexdigest(),
                witness_path=witness_base + '_Source.bytes',
                witness_sha256=hashlib.sha256(witness_bytes).hexdigest())
    meta, replacements = re.subn(rb'(?m)^guid:\s*[0-9a-fA-F]{32}\s*$',
                                ('guid: ' + guid).encode(), original.meta_bytes)
    if replacements != 1:
        raise ValueError('元モデルのImporter設定を安全に複製できません')
    generated = [StagedUnityAsset(guid, path, payload, meta, asset_type='MESH_ASSET',
                                 operation='CREATE', strategy='REGENERATE_FROM_BLENDER')]
    for field, data in (('witness_noop_path', noop_bytes), ('witness_path', witness_bytes)):
        destination = task[field]
        asset_guid = hashlib.sha256(('VAPB_WITNESS_V1:' + destination).encode()).hexdigest()[:32]
        generated.append(StagedUnityAsset(asset_guid, destination, data,
            f'fileFormatVersion: 2\nguid: {asset_guid}\n'.encode(), operation='CREATE',
            asset_type='GENERATED_EXPORT_SUPPORT'))
    for destination, data in weight_payloads:
        asset_guid = hashlib.sha256(('VAPB_WITNESS_V1:' + destination).encode()).hexdigest()[:32]
        generated.append(StagedUnityAsset(asset_guid, destination, data,
            f'fileFormatVersion: 2\nguid: {asset_guid}\n'.encode(), operation='CREATE',
            asset_type='GENERATED_EXPORT_SUPPORT'))
    return task, generated


def export_model_skin_package(context, mesh, output, *, direct=False):
    return export_model_skin_packages(context, [mesh], output, direct_flags=[direct])


def _source_model_material_paths(meshes, package_id, assets):
    """Name already validated source Materials from retained exact usage only."""
    sources = {asset.guid: asset for asset in assets}
    rows = {}
    for mesh in meshes:
        for slot in mesh.material_slots:
            material = slot.material
            if material is None:
                continue
            guid, file_id = material.get('unity_material_guid'), str(material.get('unity_material_file_id'))
            source = sources[guid]
            owners = proven_owners(material, package_id, guid, file_id, source.asset_bytes)
            row = rows.setdefault(guid, {'guid': guid, 'name': _material_data(source.asset_bytes).name, 'owners': {}})
            for owner, label in owners.items():
                if owner in row['owners'] and row['owners'][owner] != label:
                    raise ValueError('conflicting Material owner labels')
                row['owners'][owner] = label
    return allocate_material_paths(rows.values())


def export_model_skin_packages(context, meshes, output, *, direct_flags=None):
    """Stage all selected skin edits before publishing one package/Variant task set."""
    from ..export.model_skin import group_model_skin_tasks
    meshes = list(meshes)
    if context.mode != 'OBJECT' or not meshes or any(mesh is None or mesh.type != 'MESH' for mesh in meshes):
        raise ValueError('オブジェクトモードでSkin Meshを選択してください')
    if Path(output).exists():
        raise ValueError('出力先が既にあります。新しいファイル名を指定してください')
    scope_keys = ('unity_source_package_id', '_vapb_root_context_id', 'unity_composition_member_id')
    scopes = {tuple(mesh.get(key, '') for key in scope_keys) for mesh in meshes}
    source_model = len(meshes) == 1 and all(not meshes[0].get(key) for key in scope_keys[1:])
    if len(scopes) != 1 or (not source_model and any(not value for value in next(iter(scopes)))):
        raise ValueError('選択したSkinは同じPackage・Prefab個体に属する必要があります')
    realizations = [mesh.get('_vapb_fbx_realization_id', '') for mesh in meshes]
    if not all(realizations) or len(set(realizations)) != len(realizations):
        raise ValueError('選択したSkinの実体識別子がないか重複しています')
    package_id = meshes[0].get('unity_source_package_id')
    package = load_scene_registry(context.scene).packages.get(package_id)
    if not package:
        raise ValueError('元Packageの保存情報がありません')
    source = SourcePackage(Path(package['source_archive_path']), package['package_sha256'])
    source_bytes = source.path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source.expected_sha256:
        raise ValueError('保存済み原本のハッシュが変わっています')
    assets = RawAssetRepository(source.path).read_all(source_bytes)
    if direct_flags is None:
        direct_flags = [not bool(mesh.get('_vapb_model_instance_edge_path')) for mesh in meshes]
    if len(direct_flags) != len(meshes):
        raise ValueError('Skinの出力対象と参照方式が一致しません')
    prepared = [_prepare_model_skin(context, mesh, assets, direct=direct, source_model=source_model)
                for mesh, direct in zip(meshes, direct_flags)]
    tasks = group_model_skin_tasks([task for task, _ in prepared])
    tree, manifest = materialize_model_package([source], [], generator_version='0.4.0',
        blender_version=bpy.app.version_string,
        material_paths=_source_model_material_paths(meshes, package_id, assets) if source_model else None,
        texture_replacements=_working_textures(meshes[0], package_id, assets,
                                               additional_meshes=meshes[1:]))
    generated = [asset for _, entries in prepared for asset in entries]
    for asset in generated:
        tree.add(asset)
    manifest = replace(manifest, reference_rebind_tasks=tasks,
        export_assets=manifest.export_assets + tuple({'node_id': asset.pathname, 'node_type': asset.asset_type,
            'operation': 'CREATE', 'strategy': 'REGENERATE_FROM_BLENDER',
            'desired_export_path': asset.pathname, 'export_identity': {'export_guid': asset.guid}}
            for asset in generated),
        warnings=manifest.warnings + ('SOURCE_ARCHIVE_PRESERVED', 'UNITY_MODEL_IDENTITY_CHECK_REQUIRED',
                                     'NEW_PREFAB_VARIANT', 'EXISTING_SKIN_AND_TEXTURE_ASSET_EDITS'))
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
            generator_version='0.4.0', blender_version=bpy.app.version_string,
            texture_replacements=_working_textures(mesh, package_id, assets))
    manifest = replace(manifest, reference_rebind_tasks=(task,),
        warnings=manifest.warnings + ('EXISTING_STATIC_MESH_AND_TEXTURE_ASSET_EDITS', 'UNITY_FINALIZER_REQUIRED'))
    return _write_package(tree, manifest, output)


def _write_package(tree, manifest, output):
    from ..export.script_dependencies import script_dependencies_for_tasks
    script_dependencies = script_dependencies_for_tasks(manifest.reference_rebind_tasks, tree.entries)
    manifest = replace(manifest, external_dependencies=manifest.external_dependencies + script_dependencies)
    from ..export.skin_import_policy import skin_weight_policy_assets
    policies = skin_weight_policy_assets(manifest.reference_rebind_tasks)
    for policy in policies:
        tree.add(policy)
    manifest = replace(manifest, export_assets=manifest.export_assets + tuple({
        'node_id': p.pathname, 'node_type': 'GENERATED_EXPORT_SUPPORT', 'operation': 'CREATE',
        'strategy': 'REGENERATE_FROM_BLENDER', 'desired_export_path': p.pathname,
        'export_identity': {'export_guid': p.guid},
    } for p in policies))
    first_party = Path(__file__).resolve().parents[1] / 'unity_editor'
    generated = [
        ('Assets/VAPBExport/VapbRealizationMarker.cs', (first_party / 'VapbRealizationMarker.cs').read_bytes()),
        ('Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs',
         (first_party / 'Editor/VapbReferenceFinalizer.cs').read_bytes())]
    generated.append(('Assets/VAPBExport/Editor/VapbImportAssistant.cs',
                      (first_party / 'Editor/VapbImportAssistant.cs').read_bytes()))
    generated.append(('Assets/VAPBExport/Editor/VapbModelSkinFinalizer.cs',
                      (first_party / 'Editor/VapbModelSkinFinalizer.cs').read_bytes()))
    if policies:
        generated.append(('Assets/VAPBExport/Editor/VapbSkinWeightImporter.cs',
                          (first_party / 'Editor/VapbSkinWeightImporter.cs').read_bytes()))
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
    export_scope: bpy.props.EnumProperty(name='出力対象', items=(
        ('SELECTED', '選択Mesh', '選択した同じPrefab個体のSkin Meshをまとめて出力'),
        ('ACTIVE', 'アクティブMeshのみ', 'アクティブなMesh一つだけを出力')),
        default='SELECTED')

    def draw(self, context):
        self.layout.prop(self, 'export_scope')
        count = sum(obj.type == 'MESH' for obj in context.selected_objects) if self.export_scope == 'SELECTED' else 1
        self.layout.label(text=f'出力Mesh数: {count}')
        mesh = context.active_object
        model_skin = mesh and (mesh.get('_vapb_model_instance_edge_path') or
            (mesh.type == 'MESH' and mesh.get('_vapb_fbx_realization_id') and
             not mesh.get('_vapb_skin_binding') and any(m.type == 'ARMATURE' for m in mesh.modifiers)))
        if model_skin:
            source_model = not mesh.get('_vapb_root_context_id') and not mesh.get('unity_composition_member_id')
            if source_model:
                self.layout.label(text='Prefabなしの元モデルSkinは1 Meshずつ出力')
                self.layout.label(text='他のMeshを選択から外してください')
                self.layout.label(text='「アクティブMeshのみ」でも出力できます')
            else:
                self.layout.label(text='同じPrefab個体のモデル由来Skinを選択してまとめて復元')
            self.layout.label(text='Unityで出所を確認し、新しいPrefab Variantへ復元します')
            self.layout.label(text='原本・骨階層・素材を保持。形状とウェイトの編集が対象です')
            self.layout.label(text='骨階層変更・複数Prefab個体の混在はこの経路では未対応')
        else:
            self.layout.label(text='対象: アクティブな確定済みMesh一つ')
            self.layout.label(text='Skinは骨対応の確認が必要。Unityの既存骨階層・restを保持')
            self.layout.label(text='形状・ウェイト・素材を出力。新規骨・Nestedは未対応')
        self.layout.label(text='保持済みPackageの原本資産も全件含みます')
        self.layout.label(text='UnityへImport後、VAPB確認画面から［適用］')

    def execute(self, context):
        try:
            mesh = context.active_object
            selected = [obj for obj in context.selected_objects if obj.type == 'MESH'] if self.export_scope == 'SELECTED' else [mesh]
            if not selected:
                raise ValueError('出力するMeshを選択してください')
            if len(selected) > 1:
                if any(obj.get('_vapb_skin_binding') or not obj.get('_vapb_fbx_realization_id') or
                       not any(mod.type == 'ARMATURE' for mod in obj.modifiers) for obj in selected):
                    raise ValueError('複数Meshの出力は元モデル由来のSkinのみ対応しています')
                export_model_skin_packages(context, selected, self.filepath)
                self.report({'INFO'}, f'{len(selected)}個のSkinを出力しました。UnityへImportし、VAPB確認画面から適用してください')
                return {'FINISHED'}
            mesh = selected[0]
            binding = json.loads(mesh.get('_vapb_renderer_binding', '{}')) if mesh else {}
            if mesh and mesh.get('_vapb_model_instance_edge_path'):
                export_model_skin_package(context, mesh, self.filepath)
            elif binding.get('occurrence', {}).get('renderer_class_id') == 137 and mesh.get('_vapb_skin_binding'):
                export_skin_package(context, mesh, self.filepath)
            elif (mesh and mesh.type == 'MESH' and mesh.get('_vapb_fbx_realization_id') and
                  any(m.type == 'ARMATURE' for m in mesh.modifiers)):
                export_model_skin_package(context, mesh, self.filepath, direct=True)
            else:
                export_static_package(context, mesh, self.filepath)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            self.report({'ERROR'}, f'書き出しを停止しました: {exc}')
            return {'CANCELLED'}
        self.report({'INFO'}, 'UnityPackageを書き出しました。UnityへImportし、VAPB確認画面から適用してください')
        return {'FINISHED'}


class VAPB_OT_export_final_state_unitypackage(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.vapb_final_state_unitypackage'
    bl_label = 'UnityPackage（Blender完成形から新規作成）'
    bl_description = '静的Meshの現在の形状・UV・Material slotから新Assetと復元Recipeを作ります'
    filename_ext = '.unitypackage'
    filter_glob: bpy.props.StringProperty(default='*.unitypackage', options={'HIDDEN'})

    def execute(self, context):
        try:
            export_final_state_package(context, context.active_object, Path(self.filepath))
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            self.report({'ERROR'}, f'完成形の書き出しを停止しました: {exc}')
            return {'CANCELLED'}
        self.report({'INFO'}, '新しい静的Mesh UnityPackageを作成しました。UnityへImportし、VAPB確認画面から適用してください')
        return {'FINISHED'}


CLASSES = (VAPB_OT_export_unitypackage, VAPB_OT_export_final_state_unitypackage)


def menu_export(self, context):
    self.layout.operator(VAPB_OT_export_unitypackage.bl_idname, text='VAPB UnityPackage（Mesh / Skin）')
    self.layout.operator(VAPB_OT_export_final_state_unitypackage.bl_idname,
                         text='VAPB UnityPackage（Blender完成形）')
