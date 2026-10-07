import bpy
import hashlib
import importlib.util
import json
import re
import sys
import tarfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from confirmed_route_output_safety import (
    resolve_product_package_root, validate_output_path, write_text_exclusive,
)


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_raw_prefab(package_path, expected_package_sha):
    package_bytes = Path(package_path).read_bytes()
    package_sha = hashlib.sha256(package_bytes).hexdigest()
    need(package_sha == expected_package_sha, 'FIXTURE_PACKAGE_SHA_MISMATCH')
    with tarfile.open(fileobj=__import__('io').BytesIO(package_bytes), mode='r:*') as archive:
        matches = []
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith('/pathname'):
                continue
            path_stream = archive.extractfile(member)
            if path_stream is None or path_stream.read().decode('utf-8').strip() != 'Assets/PublicMaterialSource/Direct.prefab':
                continue
            prefab_guid = member.name.split('/', 1)[0].lower()
            payload = archive.extractfile(prefab_guid + '/asset')
            if payload is None:
                raise RuntimeError('RAW_PREFAB_ASSET_MISSING')
            matches.append((prefab_guid, payload.read()))
        need(len(matches) == 1, 'RAW_PREFAB_COUNT_MISMATCH')
        model_guid = 'abcdefabcdefabcdefabcdefabcdefab'
        fbx_stream = archive.extractfile(model_guid + '/asset')
        meta_stream = archive.extractfile(model_guid + '/asset.meta')
        need(fbx_stream is not None and meta_stream is not None, 'RAW_FBX_OR_META_MISSING')
        fbx_sha = hashlib.sha256(fbx_stream.read()).hexdigest()
        meta_sha = hashlib.sha256(meta_stream.read()).hexdigest()
    need(fbx_sha == 'fbe25a43a81a066c443093a0788a05569a4ec54e2d673fe133bffa7f801309c5',
         'FIXTURE_FBX_SHA_MISMATCH')
    prefab_guid, prefab = matches[0]
    renderer_docs = re.findall(rb'(?ms)^--- !u!137 &(\d+)\r?\n(.*?)(?=^--- !u!|\Z)', prefab)
    need(len(renderer_docs) == 1, 'RAW_RENDERER_COUNT_MISMATCH')
    renderer_id_raw, body = renderer_docs[0]
    renderer_id = int(renderer_id_raw)
    owner_match = re.search(rb'(?m)^\s*m_GameObject:\s*\{fileID:\s*(-?\d+)\s*\}', body)
    mesh_match = re.search(rb'(?m)^\s*m_Mesh:\s*\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]{32}),\s*type:\s*\d+\s*\}', body)
    material_match = re.search(rb'(?m)^\s*m_Materials:\s*\r?\n((?:[ \t]*-[^\r\n]*\r?\n)+)', body)
    need(owner_match is not None and mesh_match is not None and material_match is not None,
         'RAW_RENDERER_FIELDS_MISSING')
    materials = []
    for line in material_match.group(1).splitlines():
        ref = re.search(rb'fileID:\s*(-?\d+),\s*guid:\s*([0-9a-fA-F]{32})', line)
        need(ref is not None, 'RAW_MATERIAL_REF_MALFORMED')
        materials.append({'file_id': str(int(ref.group(1))), 'guid': ref.group(2).decode('ascii').lower()})
    need(len(materials) == 3, 'RAW_MATERIAL_SLOT_COUNT_MISMATCH')
    return {
        'package_sha256': package_sha,
        'source_fbx_sha256': fbx_sha,
        'source_meta_sha256': meta_sha,
        'prefab_guid': prefab_guid,
        'renderer_file_id': renderer_id,
        'owner_game_object_id': int(owner_match.group(1)),
        'mesh_file_id': int(mesh_match.group(1)),
        'mesh_guid': mesh_match.group(2).decode('ascii').lower(),
        'materials': materials,
    }


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    values = dict(zip(args[::2], args[1::2]))
    package_path = Path(values['--package'])
    output_path = Path(values['--output'])
    output_path = validate_output_path(output_path, (package_path, bpy.data.filepath))
    expected_package_sha = 'd6245d25c3cbd513c49b8d2e241b313a752331cd338563becab6eb7c819bfa0c'
    expected_blend_sha = '58a3863a44198555bf07fdb56eb86e411b0804523ac2db694283a0ed9d8d122c'
    expected_context = '6d785054-f71b-4861-9ab9-d7a6901fd1f9'
    expected_occurrence = '9c913bea517b84409aa7b7e28a7fccccdbf11b9104b154b50ba29615e4214694'
    raw = parse_raw_prefab(package_path, expected_package_sha)
    need(sha256(bpy.data.filepath) == expected_blend_sha, 'FIXTURE_BLEND_SHA_MISMATCH')

    package_root = resolve_product_package_root(values['--repo-root'])
    package_spec = importlib.util.spec_from_file_location(
        'unitypackage_blender_importer', package_root / '__init__.py',
        submodule_search_locations=[str(package_root)])
    need(package_spec is not None and package_spec.loader is not None,
         'PRODUCT_PACKAGE_IMPORT_SPEC_INVALID')
    package_module = importlib.util.module_from_spec(package_spec)
    sys.modules['unitypackage_blender_importer'] = package_module
    package_spec.loader.exec_module(package_module)
    from unitypackage_blender_importer.blender.fbx_receipt import validate_persistent_receipt
    from unitypackage_blender_importer.blender.renderer_binding import validate_existing_binding

    roots = [obj for obj in bpy.data.objects
             if obj.type == 'EMPTY'
             and obj.get('_vapb_root_context_id') == expected_context
             and obj.get('_vapb_renderer_occurrences')]
    need(len(roots) == 1, 'REOPEN_ROOT_AMBIGUOUS_OR_MISSING')
    root = roots[0]
    projection_doc = json.loads(root['_vapb_renderer_occurrences'])
    records = [row for row in projection_doc.get('records', [])
               if row.get('occurrence_id') == expected_occurrence]
    need(len(records) == 1, 'PROJECTION_OCCURRENCE_AMBIGUOUS_OR_MISSING')
    record = records[0]
    package_id = 'sha256:' + expected_package_sha
    need(record.get('root_package_id') == package_id
         and record.get('source_package_id') == package_id,
         'RAW_PACKAGE_TO_PROJECTION_SCOPE_MISMATCH')
    need(record.get('source_key', {}).get('source_asset_guid') == raw['prefab_guid'],
         'RAW_PREFAB_TO_PROJECTION_SOURCE_GUID_MISMATCH')
    need(record.get('mesh', {}).get('source_package_id') == package_id
         and record.get('mesh', {}).get('source_sha256') == raw['source_fbx_sha256'],
         'RAW_FBX_TO_PROJECTION_REVISION_MISMATCH')
    need(record.get('material_status') == 'EXACT', 'PROJECTION_MATERIALS_NOT_EXACT')
    need(record.get('material_slot_count') == len(raw['materials']), 'PROJECTION_SLOT_COUNT_MISMATCH')
    projection_materials = [
        {'file_id': str(record['materials'][str(index)]['file_id']),
         'guid': str(record['materials'][str(index)]['guid']).lower()}
        for index in range(len(raw['materials']))]
    need(projection_materials == raw['materials'], 'RAW_PREFAB_TO_PROJECTION_MATERIAL_MISMATCH')
    need(record.get('source_key', {}).get('renderer_file_id') == raw['renderer_file_id'],
         'RAW_PREFAB_TO_PROJECTION_RENDERER_MISMATCH')
    need(record.get('owner', {}).get('owner_game_object_id') == raw['owner_game_object_id'],
         'RAW_PREFAB_TO_PROJECTION_OWNER_MISMATCH')
    need(record.get('mesh', {}).get('mesh_file_id') == raw['mesh_file_id']
         and record.get('mesh', {}).get('mesh_guid') == raw['mesh_guid'],
         'RAW_PREFAB_TO_PROJECTION_MESH_MISMATCH')

    bindings = []
    for obj in bpy.data.objects:
        payload = obj.get('_vapb_renderer_binding')
        if not payload:
            continue
        try:
            binding = json.loads(payload) if isinstance(payload, str) else payload
        except (TypeError, ValueError):
            continue
        if binding.get('occurrence_id') == expected_occurrence:
            bindings.append((obj, binding))
    need(len(bindings) == 1, 'REOPEN_BINDING_AMBIGUOUS_OR_MISSING')
    mesh, binding = bindings[0]
    need(mesh.type == 'MESH', 'REOPEN_BOUND_OBJECT_NOT_MESH')
    need(binding.get('evidence') == 'USER_CONFIRMED', 'REOPEN_BINDING_NOT_USER_CONFIRMED')
    need(binding.get('occurrence') == record, 'REOPEN_BINDING_PROJECTION_CHANGED')
    need(binding.get('root_context_id') == expected_context, 'REOPEN_BINDING_SCOPE_CHANGED')
    need(binding.get('source_package_id') == package_id, 'REOPEN_BINDING_PACKAGE_SCOPE_CHANGED')
    receipt_ref = binding.get('mesh_receipt', {})
    need(receipt_ref.get('source_package_id') == package_id
         and receipt_ref.get('mesh_guid') == raw['mesh_guid']
         and str(receipt_ref.get('mesh_file_id')) == str(raw['mesh_file_id'])
         and receipt_ref.get('source_sha256') == raw['source_fbx_sha256'],
         'RAW_FBX_TO_REOPEN_RECEIPT_REVISION_MISMATCH')
    need(validate_existing_binding(binding, root, mesh, tuple(bpy.data.objects)) == binding,
         'REOPEN_BINDING_VALIDATION_FAILED')
    need(validate_persistent_receipt(mesh), 'REOPEN_MESH_RECEIPT_INVALID')

    slots = []
    for slot in mesh.material_slots:
        material = slot.material
        need(slot.link == 'OBJECT' and material is not None, 'REOPEN_SLOT_NOT_OBJECT_LINKED')
        slots.append({
            'link': slot.link,
            'guid': str(material.get('unity_material_guid', '')).lower(),
            'file_id': str(material.get('unity_material_file_id', '')),
            'package_id': str(material.get('unity_source_package_id', '')),
        })
    need(len(slots) == len(raw['materials']), 'REOPEN_SLOT_COUNT_MISMATCH')
    expected_persisted_slots = [
        {'link': 'OBJECT', 'guid': item['guid'], 'file_id': item['file_id'],
         'package_id': 'sha256:' + expected_package_sha}
        for item in raw['materials']]
    need(slots == expected_persisted_slots, 'RAW_PREFAB_TO_REOPEN_SLOT_MISMATCH')

    mesh.data.calc_loop_triangles()
    triangle_counts = [sum(1 for tri in mesh.data.loop_triangles if tri.material_index == index)
                       for index in range(len(slots))]
    need(triangle_counts == [2, 4, 6], 'REOPEN_TRIANGLE_COUNTS_MISMATCH')

    result = {
        'status': 'PASS',
        'stage': 'CONFIRM_BINDING_FRESH_PROCESS_RAW_PREFAB_COMPARISON',
        'source_package_sha256': raw['package_sha256'],
        'source_fbx_sha256': raw['source_fbx_sha256'],
        'source_meta_sha256': raw['source_meta_sha256'],
        'saved_blend_sha256': sha256(bpy.data.filepath),
        'fixture_raw_prefab': {key: raw[key] for key in (
            'prefab_guid', 'renderer_file_id', 'owner_game_object_id', 'mesh_file_id', 'mesh_guid')},
        'raw_prefab_material_refs': raw['materials'],
        'projection_material_refs': projection_materials,
        'reopened_slot_refs': slots,
        'binding_evidence': binding['evidence'],
        'binding_revalidated': True,
        'mesh_receipt_valid': True,
        'triangle_counts': triangle_counts,
        'unity_editor_run': False,
        'source_project_modified': False,
        'blend_saved_by_probe': False,
    }
    write_text_exclusive(output_path, json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('CONFIRM_BINDING_FRESH_PROCESS_RAW_PREFAB_COMPARISON_PASS ' + json.dumps(result, sort_keys=True))


main()
