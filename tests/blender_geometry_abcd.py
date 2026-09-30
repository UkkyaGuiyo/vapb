# SPDX-License-Identifier: GPL-3.0-or-later
"""Public diagnostic B/D experiment; production preset, disposable export copies.

Blender CLI: CONTROL_PROJECT NEW_OUTPUT_FOLDER. No user's scene is loaded.
Identity comes from native handles/raw UIDs and explicit diagnostic UV labels.
"""
import hashlib
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.fbx_export import export_fbx
from unitypackage_blender_importer.blender.fbx_receipt import import_with_receipts
from unitypackage_blender_importer.tests.blender_geometry_point_controls import decode_marker


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe(obj, uid, channel=None, count=None, shape_ids=None):
    """World-space Blender coordinates; triangle corners retain loop attributes."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    points = {}
    if channel is not None:
        for loop in mesh.loops:
            uv = mesh.uv_layers[channel].data[loop.index].uv
            cp = decode_marker(uv.x, uv.y, count)
            assert points.setdefault(loop.vertex_index, cp) == cp
    triangles = [list(t.vertices) for t in mesh.loop_triangles]
    corner_loops = [i for t in mesh.loop_triangles for i in t.loops]
    basis = list(mesh.shape_keys.key_blocks)[0] if mesh.shape_keys else None
    groups = {g.index: g.name for g in obj.vertex_groups}
    row = dict(geometry_uid=str(uid), vertex_count=len(mesh.vertices),
        positions=[list(obj.matrix_world @ v.co) for v in mesh.vertices],
        triangles=triangles, polygons=[list(p.vertices) for p in mesh.polygons],
        triangle_material_slots=[mesh.polygons[t.polygon_index].material_index for t in mesh.loop_triangles],
        corner_normals=[list((normal_matrix @ mesh.corner_normals[i].vector).normalized()) for i in corner_loops],
        uv_channels=[dict(channel=n, corners=[list(layer.data[i].uv) for i in corner_loops])
                     for n, layer in enumerate(mesh.uv_layers)],
        shapes=[dict(channel_uid=str(shape_ids.get(k.as_pointer(), 'UNPROVEN')) if shape_ids else 'UNPROVEN',
                     export_label=k.name, value=k.value,
                     deltas=[list(obj.matrix_world.to_3x3() @ (p.co-basis.data[i].co)) for i,p in enumerate(k.data)])
                for k in list(mesh.shape_keys.key_blocks)[1:]] if basis else [],
        skin_weights=[[dict(group=groups[g.group], weight=g.weight) for g in v.groups] for v in mesh.vertices],
        armature_modifier_count=sum(m.type == 'ARMATURE' and m.object is not None for m in obj.modifiers))
    row['world_bounds'] = dict(minimum=[min(p[i] for p in row['positions']) for i in range(3)],
                              maximum=[max(p[i] for p in row['positions']) for i in range(3)])
    if channel is not None:
        row.update(marker_channel=channel,
                   vertex_control_point_indices=[points.get(i) for i in range(len(mesh.vertices))],
                   triangle_control_points=[[points[v] for v in t] for t in triangles])
    evaluated = obj.evaluated_get(__import__('bpy').context.evaluated_depsgraph_get())
    baked = evaluated.to_mesh()
    try:
        assert len(baked.vertices) == len(mesh.vertices), 'EVALUATED_VERTEX_IDENTITY_UNPROVEN'
        row['baked_positions'] = [list(evaluated.matrix_world @ v.co) for v in baked.vertices]
    finally:
        evaluated.to_mesh_clear()
    return row


def explicit_copy(obj):
    """Freeze calc_loop_triangles, preserving vertex, loop, skin and Shape data."""
    import bpy
    source = obj.data
    source.calc_loop_triangles()
    tris = list(source.loop_triangles)
    copied = obj.copy()
    mesh = bpy.data.meshes.new('DiagnosticExplicitTriangles')
    mesh.from_pydata([tuple(v.co) for v in source.vertices], [], [tuple(t.vertices) for t in tris])
    copied.data = mesh
    bpy.context.scene.collection.objects.link(copied)
    for material in source.materials:
        mesh.materials.append(material)
    loops = [i for t in tris for i in t.loops]
    for layer in source.uv_layers:
        target = mesh.uv_layers.new(name=layer.name)
        for index, old in enumerate(loops):
            target.data[index].uv = layer.data[old].uv
    for target, tri in zip(mesh.polygons, tris):
        old = source.polygons[tri.polygon_index]
        target.material_index, target.use_smooth = old.material_index, True
    mesh.normals_split_custom_set([source.corner_normals[i].vector for i in loops])
    if source.shape_keys:
        old_keys = list(source.shape_keys.key_blocks)
        keys = []
        for old in old_keys:
            key = copied.shape_key_add(name=old.name)
            for i, point in enumerate(old.data):
                key.data[i].co = point.co
            key.value, key.slider_min, key.slider_max = old.value, old.slider_min, old.slider_max
            keys.append(key)
        for old, key in zip(old_keys, keys):
            key.relative_key = keys[old_keys.index(old.relative_key)]
    copied.vertex_groups.clear()
    for group in obj.vertex_groups:
        copied.vertex_groups.new(name=group.name)
    # Group definitions and weights belong to the temporary export copy.
    for vertex in source.vertices:
        for influence in vertex.groups:
            copied.vertex_groups[influence.group].add([vertex.index], influence.weight, 'REPLACE')
    return copied


def main():
    import bpy
    from io_scene_fbx import import_fbx, parse_fbx
    control, output = map(Path, sys.argv[sys.argv.index('--')+1:])
    assert not output.exists()
    output.mkdir(parents=True)
    manifest = json.loads((control/'ControlPointManifest.json').read_text())
    specs = {int(r['geometry_uid']): r for r in manifest['meshes']}
    for filename, key in [('Source.fbx','source_fbx_sha256'), ('Stamped.fbx','stamped_fbx_sha256'),
                          ('Source.fbx.meta','source_meta_sha256')]:
        assert sha(control/filename) == manifest[key]
    original_geom, original_shape = import_fbx.blen_read_geom, import_fbx.blen_read_shapes

    def load(filename):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        meshes, shape_ids = {}, {}
        def geom(*args):
            mesh = original_geom(*args)
            meshes[int(args[1].props[0])] = mesh
            return mesh
        def shapes(*args):
            result = original_shape(*args)
            for uid, keys in result.items():
                assert len(keys) == 1, 'PROGRESSIVE_SHAPE_UNSUPPORTED'
                shape_ids[keys[0].as_pointer()] = int(uid)
            return result
        try:
            import_fbx.blen_read_geom, import_fbx.blen_read_shapes = geom, shapes
            guid = re.search(r'(?m)^guid: ([0-9a-f]{32})', (control/'Source.fbx.meta').read_text())[1]
            def native_import():
                assert bpy.ops.import_scene.fbx(filepath=str(control/filename)) == {'FINISHED'}
            import_with_receipts(control/filename,native_import,guid,bpy)
        finally:
            import_fbx.blen_read_geom, import_fbx.blen_read_shapes = original_geom, original_shape
        rows = {}
        for uid, mesh in meshes.items():
            objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data is mesh]
            assert len(objects) == 1, 'EXPERIMENT_OCCURRENCE_UNSUPPORTED'
            obj, = objects
            if mesh.shape_keys:
                for key in mesh.shape_keys.key_blocks:
                    key.value = 0
            rows[uid] = obj
        bpy.context.view_layer.update()
        return rows, shape_ids

    objects, ids = load('Source.fbx')
    original = {uid:observe(o,uid,shape_ids=ids) for uid,o in objects.items()}
    objects, ids = load('Stamped.fbx')
    stamped = {uid:observe(o,uid,specs[uid]['uv_channel'],specs[uid]['control_point_count'],ids)
               for uid,o in objects.items()}
    for uid in specs:
        for key in ('positions','triangles','polygons','corner_normals','skin_weights'):
            assert original[uid][key] == stamped[uid][key], 'STAMP_INTERFERENCE_'+key
        assert original[uid]['shapes'] == stamped[uid]['shapes']
        for layer in original[uid]['uv_channels']:
            assert layer == stamped[uid]['uv_channels'][layer['channel']]
    report = dict(blender_version=bpy.app.version_string, manifest=manifest,
                  shape_weights_fixed_to_zero=True, marker_noninterference=True,
                  B=list(stamped.values()), exports=[])
    # Each branch imports anew; never edit the original objects/datablocks.
    for mode in ('D0', 'D1'):
        objects, ids = load('Stamped.fbx')
        before = {uid:observe(o,uid,specs[uid]['uv_channel'],specs[uid]['control_point_count'],ids)
                  for uid,o in objects.items()}
        copies = {}
        rigs = {}
        weight_expectations = {}
        shape_bridge = {}
        for uid,obj in objects.items():
            copied = explicit_copy(obj) if mode == 'D1' else obj.copy()
            if mode == 'D0':
                copied.data = obj.data.copy()
                bpy.context.scene.collection.objects.link(copied)
            # Labels are assigned to actual imported handles as export transport IDs;
            # they do not infer a source identity from existing object/shape names.
            copied.name = 'VAPB-EXP-MESH-'+str(uid)
            group_labels = {}
            for modifier in copied.modifiers:
                if modifier.type != 'ARMATURE':
                    continue
                source_rig = modifier.object
                if source_rig not in rigs:
                    rig = source_rig.copy()
                    rig.data = source_rig.data.copy()
                    bpy.context.scene.collection.objects.link(rig)
                    rigs[source_rig] = rig
                rig = rigs[source_rig]
                # Every label is bound to a receipt-selected actual Bone handle.
                for bone in source_rig.data.bones:
                    bone_uid = bone.get('_vapb_fbx_model_uid')
                    assert bone_uid, 'BONE_EXPORT_IDENTITY_UNPROVEN'
                    group = copied.vertex_groups.get(bone.name)
                    if group is not None:
                        group.name = 'VAPB-EXP-BONE-'+str(bone_uid)
                        group_labels[bone.name] = group.name
                    rig.data.bones.get(bone.name, rig.data.bones.get('VAPB-EXP-BONE-'+str(bone_uid))).name = 'VAPB-EXP-BONE-'+str(bone_uid)
                modifier.object = rig
            weight_expectations[uid] = [[dict(group=group_labels.get(g['group'],g['group']),weight=g['weight'])
                                       for g in row] for row in before[uid]['skin_weights']]
            if obj.data.shape_keys:
                for original_key, exported_key in zip(list(obj.data.shape_keys.key_blocks)[1:],
                                                       list(copied.data.shape_keys.key_blocks)[1:]):
                    channel = ids[original_key.as_pointer()]
                    exported_key.name = 'VAPB-EXP-SHAPE-'+str(channel)
                    shape_bridge[exported_key.as_pointer()] = channel
            copies[uid] = copied
        for obj in bpy.context.scene.objects:
            obj.select_set(False)
        for obj in copies.values():
            obj.select_set(True)
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object:
                    modifier.object.select_set(True)
        bpy.context.view_layer.update()
        pre = [observe(o,uid,specs[uid]['uv_channel'],specs[uid]['control_point_count'],shape_bridge)
               for uid,o in copies.items()]
        if mode == 'D1':
            for row in pre:
                expected = before[int(row['geometry_uid'])]
                for field in ('positions','triangle_control_points','triangle_material_slots'):
                    assert row[field] == expected[field], 'EXPLICIT_COPY_CHANGED_'+field
                assert row['skin_weights'] == weight_expectations[int(row['geometry_uid'])], 'EXPLICIT_COPY_CHANGED_WEIGHTS'
                assert all(len(p) == 3 for p in row['polygons'])
                assert [s['deltas'] for s in row['shapes']] == [s['deltas'] for s in expected['shapes']]
        path = output/(mode+'.fbx')
        export_fbx(path)
        assert path.is_file()
        for uid,obj in objects.items():
            assert observe(obj,uid,specs[uid]['uv_channel'],specs[uid]['control_point_count'],ids) == before[uid]
        raw, _ = parse_fbx.parse(str(path), use_namedtuple=True)
        polygons = []
        for node in next(n for n in raw.elems if n.id == b'Objects').elems:
            if node.id == b'Geometry' and node.props[2] == b'Mesh':
                indices = next(n.props[0] for n in node.elems if n.id == b'PolygonVertexIndex')
                lengths, length = [], 0
                for index in indices:
                    length += 1
                    if index < 0:
                        lengths.append(length); length = 0
                polygons.extend(lengths)
        report['exports'].append(dict(mode=mode, fbx_sha256=sha(path),
            source_objects_unchanged=True, pre_export=pre, raw_polygon_sizes=polygons))
    for filename,key in [('Source.fbx','source_fbx_sha256'), ('Stamped.fbx','stamped_fbx_sha256'),
                         ('Source.fbx.meta','source_meta_sha256')]:
        assert sha(control/filename) == manifest[key]
    (output/'BlenderABCD.json').write_text(json.dumps(report,indent=2))
    print('BLENDER_ABCD_PASS meshes=%d D0_D1_exported=1 source_unchanged=1' % len(specs))


if __name__ == '__main__':
    main()
