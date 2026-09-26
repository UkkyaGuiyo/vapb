"""Explicit, bounded static-mesh UnityPackage roundtrip with isolated staging."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile

import bpy
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix

from ..blender.fbx_receipt import RawFbxSemanticIndex
from ..blender.identity_registry import load_scene_registry
from ..blender.renderer_binding import validate_existing_binding
from ..export.direct_renderer import direct_renderer_task
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
    first_party = Path(__file__).resolve().parents[1] / 'unity_editor'
    generated = [
        ('Assets/VAPBExport/VapbRealizationMarker.cs', (first_party / 'VapbRealizationMarker.cs').read_bytes()),
        ('Assets/VAPBExport/Editor/VapbReferenceFinalizer.cs',
         (first_party / 'Editor/VapbReferenceFinalizer.cs').read_bytes())]
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
    bl_label = 'UnityPackage（静的Mesh・参照復元）'
    bl_description = '確定済み直接Prefabの静的Mesh形状と素材割当を書き出します。Unityで復元メニューを実行してください'
    filename_ext = '.unitypackage'
    filter_glob: bpy.props.StringProperty(default='*.unitypackage', options={'HIDDEN'})

    def draw(self, context):
        self.layout.label(text='対象: アクティブな確定済み静的Mesh一つ')
        self.layout.label(text='形状・素材割当を出力。TransformとShader設定は元のまま')
        self.layout.label(text='Skin / Shape Key / Nested Prefab はこの経路では未対応')
        self.layout.label(text='保持済みPackageの原本資産も全件含みます')
        self.layout.label(text='Unity import後にmanifestを選択しVAPB復元メニューを実行')

    def execute(self, context):
        try:
            export_static_package(context, context.active_object, self.filepath)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            self.report({'ERROR'}, f'書き出しを停止しました: {exc}')
            return {'CANCELLED'}
        self.report({'INFO'}, 'UnityPackageを書き出しました。Unity側の参照復元が必要です')
        return {'FINISHED'}


CLASSES = (VAPB_OT_export_unitypackage,)


def menu_export(self, context):
    self.layout.operator(VAPB_OT_export_unitypackage.bl_idname, text='VAPB UnityPackage（静的Mesh）')
