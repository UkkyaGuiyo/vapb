"""Bounded direct static-renderer export checks; no Blender or Unity runtime."""

from pathlib import PurePosixPath
import hashlib
import re

from ..unity.yaml_parser import parse_unity_yaml
from ..unity.prefab_parser import ref_file_id, ref_guid


def direct_renderer_task(binding, materials, assets):
    """Require complete known references before replacing a single static model.

    This initial route deliberately rejects skins, nested sources and binary
    serialized state. Their references cannot be proven by this adapter.
    """
    record = binding['occurrence']
    if (record['renderer_class_id'] != 23 or record['instance_edge_path']
            or record['root_asset_guid'] != record['source_key']['source_asset_guid']):
        raise ValueError('現在の書き出しは直接Prefabの静的MeshRendererのみ対応しています')
    model_guid = binding['mesh_receipt']['mesh_guid'].lower()
    prefab_guid = record['root_asset_guid'].lower()
    renderer_id = int(record['source_key']['renderer_file_id'])
    prefab = next((a for a in assets if a.guid == prefab_guid), None)
    if prefab is None:
        raise ValueError('元Prefabが保持済みPackageにありません')
    prefab_sha = hashlib.sha256(prefab.asset_bytes).hexdigest()
    if record.get('source_revision_sha256') != prefab_sha:
        raise ValueError('Renderer対応の元Prefab revisionが変わっています')
    docs = parse_unity_yaml(prefab.asset_bytes.decode('utf-8-sig'))
    if len({d.file_id for d in docs}) != len(docs):
        raise ValueError('元PrefabのfileIDが重複しています')
    renderer = next((d for d in docs if d.file_id == renderer_id and d.class_id == 23), None)
    if renderer is None:
        raise ValueError('元Rendererを確認できません')
    owner_id = ref_file_id(renderer.data.get('m_GameObject'))
    filters = [d for d in docs if d.class_id == 33 and ref_file_id(d.data.get('m_GameObject')) == owner_id]
    if len(filters) != 1 or ref_guid(filters[0].data.get('m_Mesh')) != model_guid:
        raise ValueError('MeshFilterと元モデルの対応を確認できません')
    if str(ref_file_id(filters[0].data['m_Mesh'])) != str(binding['mesh_receipt']['mesh_file_id']):
        raise ValueError('元Mesh参照が変わっています')
    pattern = re.compile(r'\bguid:\s*' + re.escape(model_guid) + r'\b', re.I)
    all_guids = {a.guid.lower() for a in assets}
    # Unity built-in resources have these reserved GUIDs; their signed fileID
    # remains serialized unchanged. Other external providers need an explicit
    # dependency declaration, which this bounded route does not yet offer.
    builtins = {'0' * 32, '0000000000000000e000000000000000', '0000000000000000f000000000000000'}
    reference_pattern = re.compile(r'\bguid:\s*([0-9a-fA-F]{32})\b')
    allowed_extensions = {'.prefab', '.mat', '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.fbx'}
    for asset in assets:
        if re.search(rb'(?m)^folderAsset:\s*yes\s*$', asset.meta_bytes):
            continue
        reference_texts = [asset.meta_bytes.decode('utf-8-sig')]
        if PurePosixPath(asset.pathname).suffix.lower() in {'.prefab', '.mat'}:
            reference_texts.append(asset.asset_bytes.decode('utf-8-sig'))
        for text in reference_texts:
            if any(g.lower() not in all_guids | builtins for g in reference_pattern.findall(text)):
                raise ValueError('保持済みPackageに含まれない依存Assetがあります')
        if PurePosixPath(asset.pathname).suffix.lower() not in allowed_extensions:
            raise ValueError('未対応の保存stateを含むためモデル参照の完全性を確認できません')
        if asset.guid == model_guid:
            continue
        # UTF-8 reference text is inspected only in formats whose serialized
        # references are known. Images cannot contain Unity object references.
        if PurePosixPath(asset.pathname).suffix.lower() in {'.prefab', '.mat'}:
            text = asset.asset_bytes.decode('utf-8-sig')
            if asset.guid == prefab_guid:
                matches = sum(len(pattern.findall(d.raw)) for d in docs)
                if matches != 1 or len(pattern.findall(filters[0].raw)) != 1:
                    raise ValueError('追加のモデル参照があります。全参照の復元経路が必要です')
            elif pattern.search(text):
                raise ValueError('別Assetにもこのモデルへの参照があります')
        if pattern.search(asset.meta_bytes.decode('utf-8-sig')):
            raise ValueError('Importer設定にもこのモデルへの参照があります')
    return {
        'kind': 'REBIND_DIRECT_RENDERER_V1', 'prefab_guid': prefab_guid,
        'renderer_file_id': str(renderer_id), 'renderer_class_id': 23,
        'model_guid': model_guid, 'realization_id': binding['native_realization_id'],
        'materials': materials,
        'prefab_source_sha256': prefab_sha,
    }
