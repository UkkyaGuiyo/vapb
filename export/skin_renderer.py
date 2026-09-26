"""Direct serialized skin export tasks with explicitly confirmed bone targets."""
from pathlib import PurePosixPath
import hashlib
import re

from ..unity.yaml_parser import parse_unity_yaml
from ..unity.prefab_parser import ref_file_id, ref_guid


def skin_renderer_task(binding, skin_binding, materials, assets):
    record = binding['occurrence']
    if (record['renderer_class_id'] != 137 or record['instance_edge_path']
            or record['root_asset_guid'] != record['source_key']['source_asset_guid']):
        raise ValueError('このSkin経路は直接Prefabの確定済みRendererが必要です')
    source_guid = binding['mesh_receipt']['mesh_guid'].lower()
    prefab_guid = record['root_asset_guid'].lower()
    by_guid = {asset.guid: asset for asset in assets}
    if len(by_guid) != len(assets) or source_guid not in by_guid or prefab_guid not in by_guid:
        raise ValueError('元PrefabまたはFBXを一意に取得できません')
    prefab, source = by_guid[prefab_guid], by_guid[source_guid]
    prefab_sha = hashlib.sha256(prefab.asset_bytes).hexdigest()
    source_sha = hashlib.sha256(source.asset_bytes).hexdigest()
    if (prefab_sha != record['source_revision_sha256'] or
            source_sha != binding['mesh_receipt']['source_sha256']):
        raise ValueError('確認済みSkinの元データが変わっています')
    docs = parse_unity_yaml(prefab.asset_bytes.decode('utf-8-sig'))
    if len({doc.file_id for doc in docs}) != len(docs):
        raise ValueError('PrefabのfileIDが重複しています')
    renderer_id = int(record['source_key']['renderer_file_id'])
    renderer = next((doc for doc in docs if doc.file_id == renderer_id and doc.class_id == 137), None)
    if renderer is None or ref_guid(renderer.data.get('m_Mesh')) != source_guid or \
            str(ref_file_id(renderer.data.get('m_Mesh'))) != str(binding['mesh_receipt']['mesh_file_id']):
        raise ValueError('元SkinのMesh参照が変わっています')
    references = renderer.data.get('m_Bones')
    root_ref = renderer.data.get('m_RootBone')
    if not isinstance(references, list) or not references or not isinstance(root_ref, dict):
        raise ValueError('元Skinの骨参照が不完全です')
    if any(not isinstance(ref, dict) or ref_guid(ref) not in (None, '', '0' * 32)
           for ref in references + [root_ref]):
        raise ValueError('外部モデルの骨参照はこのSkin経路では未解決です')
    ordered_bones = [str(ref_file_id(ref)) for ref in references]
    root_id = str(ref_file_id(root_ref))
    targets = set(ordered_bones + [root_id])
    transforms = {str(doc.file_id) for doc in docs if doc.class_id == 4}
    if '0' in targets or not targets <= transforms or len(set(ordered_bones)) != len(ordered_bones):
        raise ValueError('元Skinの骨Transformが不明または重複しています')
    mappings = skin_binding['mappings']
    mapped_ids = [str(item['target_transform_file_id']) for item in mappings]
    realization_ids = [item['edited_bone_realization_id'] for item in mappings]
    if (set(mapped_ids) != targets or len(mapped_ids) != len(targets) or
            len(set(realization_ids)) != len(realization_ids) or not all(realization_ids) or
            str(skin_binding['root_bone_target_transform_file_id']) != root_id):
        raise ValueError('確認済みの骨対応が元Skinの参照と一致しません')
    # Source FBX and all source assets are retained verbatim. Unknown component
    # schemas can nevertheless encode vertex/shape indices, so don't assume
    # arbitrary topology edits preserve such state merely because bytes survive.
    known_classes = {1, 4, 23, 33, 95, 137}
    if any(doc.class_id not in known_classes for doc in docs):
        raise ValueError('未対応のComponent参照があります。Skin編集の復元範囲を確認できません')
    text_extensions = {'.prefab', '.mat', '.anim', '.controller', '.overridecontroller', '.mask'}
    allowed = text_extensions | {'.fbx', '.png', '.jpg', '.jpeg', '.tga', '.bmp'}
    builtins = {'0' * 32, '0000000000000000e000000000000000', '0000000000000000f000000000000000'}
    reference_pattern = re.compile(r'\bguid:\s*([0-9a-fA-F]{32})\b')
    for asset in assets:
        if re.search(rb'(?m)^folderAsset:\s*yes\s*$', asset.meta_bytes):
            continue
        extension = PurePosixPath(asset.pathname).suffix.lower()
        if extension not in allowed:
            raise ValueError('未対応の保存stateを含むためSkin編集の参照を確認できません')
        texts = [asset.meta_bytes.decode('utf-8-sig')]
        if extension in text_extensions:
            texts.append(asset.asset_bytes.decode('utf-8-sig'))
        if any(guid.lower() not in set(by_guid) | builtins for text in texts
               for guid in reference_pattern.findall(text)):
            raise ValueError('保持済みPackageに含まれない依存Assetがあります')
    return {
        'kind': 'REBIND_SKINNED_RENDERER_V1', 'renderer_class_id': 137,
        'prefab_guid': prefab_guid, 'renderer_file_id': str(renderer_id),
        'prefab_source_sha256': prefab_sha,
        'source_model_guid': source_guid, 'source_model_sha256': source_sha,
        'source_mesh_file_id': str(binding['mesh_receipt']['mesh_file_id']),
        'realization_id': binding['native_realization_id'], 'materials': materials,
        'bones': [{'edited_bone_realization_id': row['edited_bone_realization_id'],
                   'target_transform_file_id': str(row['target_transform_file_id'])} for row in mappings],
        'source_bone_transform_file_ids': ordered_bones,
        'root_bone_target_transform_file_id': root_id,
    }
