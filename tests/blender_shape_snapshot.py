"""Normal VAPB Import plus read-only Shape evidence; no identity injection.

Same arguments/environment as blender_hierarchy_snapshot.py. The temporary
official importer observer records returned channel UID/KeyBlock handles only.
It is restored even when Import fails. Persistent receipt absence stays RED.
"""
import hashlib
from functools import wraps
import inspect
import json
from pathlib import Path
import struct
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def delta_hash(key, basis):
    return hashlib.sha256(b''.join(struct.pack('<3f', *(point.co - base.co))
        for point, base in zip(key.data, basis.data))).hexdigest()


def observe():
    rows = []
    records = {}
    for root in bpy.context.scene.objects:
        if root.get('_vapb_renderer_occurrences'):
            projection = json.loads(root['_vapb_renderer_occurrences'])
            records.update({r['occurrence_id']: r for r in projection['records']})
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.data.shape_keys is None:
            continue
        keys = obj.data.shape_keys
        blocks = list(keys.key_blocks)
        rows.append(dict(object_receipt=obj.get('_vapb_fbx_object_receipt_id'),
            mesh_receipt=obj.data.get('_vapb_fbx_mesh_receipt_id'),
            fbx_sha256=obj.get('_vapb_fbx_source_asset_sha256'),
            geometry_uid=obj.get('_vapb_fbx_geometry_uid'),
            renderer_occurrence=obj.get('_vapb_renderer_occurrence_id'),
            renderer_record=records.get(obj.get('_vapb_renderer_occurrence_id')),
            weight_occurrence=obj.get('_vapb_shape_weight_occurrence_id'),
            actual_owner=obj.parent.get('_vapb_semantic_owner_id') if obj.parent else None,
            realization=obj.get('_vapb_fbx_realization_id'),
            source_realization=obj.get('_vapb_fbx_source_realization_id'),
            mesh_handle=str(obj.data.as_pointer()), key_handle=str(keys.as_pointer()),
            key_properties={k: keys[k] for k in keys.keys()},
            channels=[dict(diagnostic_name=key.name, key_index=i, value=key.value,
                relative_index=blocks.index(key.relative_key), delta_sha256=delta_hash(key, blocks[0]))
                for i, key in enumerate(blocks)]))
    return rows


def main():
    from io_scene_fbx import import_fbx
    from unitypackage_blender_importer.tests import blender_hierarchy_snapshot
    original = import_fbx.blen_read_shapes
    assert tuple(inspect.signature(original).parameters) == ('fbx_tmpl', 'fbx_data', 'objects', 'me', 'scene')
    captures = []

    @wraps(original)
    def observer(*args):
        result = original(*args)
        mesh = args[3]
        if result:
            blocks = list(mesh.shape_keys.key_blocks)
            for uid, keys in result.items():
                captures.append(dict(channel_uid=str(uid),
                    mesh_handle=str(mesh.as_pointer()), key_handle=str(mesh.shape_keys.as_pointer()),
                    key_indices=[blocks.index(key) for key in keys],
                    delta_sha256=[delta_hash(key, blocks[0]) for key in keys]))
        return result

    try:
        import_fbx.blen_read_shapes = observer
        blender_hierarchy_snapshot.main()
    finally:
        import_fbx.blen_read_shapes = original
    output = Path(sys.argv[sys.argv.index('--') + 4])
    rows = observe()
    result = dict(schema='vapb-shape-native-observation-1', objects=rows,
        package_sha256=sys.argv[sys.argv.index('--')+2],
        experimental_import_callback=captures,
        status='CHANNEL_IDENTITY_UNPROVEN' if any(not row['key_properties'] for row in rows) else 'OBSERVED')
    (output / 'shape_snapshot.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('SHAPE_SNAPSHOT rows=%d persistent_identity=%s' % (len(rows), result['status']))


if __name__ == '__main__':
    main()
