"""Actual GUI skin confirmation and edited topology/weight UnityPackage export."""
from pathlib import Path
import json
import sys

import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon


def prepare(root):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    uv_shape_split = '--uv-shape-split' in sys.argv
    if uv_shape_split:
        data = bpy.data.meshes.new('SyntheticSplitQuad')
        data.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [],
                         [(0, 1, 2), (0, 2, 3)])
        data.update()
        mesh = bpy.data.objects.new('SyntheticSkin', data)
        bpy.context.collection.objects.link(mesh)
        mesh.select_set(True)
        uv = data.uv_layers.new(name='UVMap')
        coordinates = ((0, 0), (1, 0), (1, 1), (0, 1))
        for loop in data.loops:
            uv.data[loop.index].uv = coordinates[loop.vertex_index]
        for polygon in data.polygons:
            polygon.use_smooth = True
        mesh.shape_key_add(name='Basis')
        mesh.shape_key_add(name='ShapeA').data[0].co.z += 0.1
        mesh.shape_key_add(name='ShapeB').data[1].co.z += 0.1
    else:
        bpy.ops.mesh.primitive_cube_add()
        mesh = bpy.context.object
    mesh.name = 'SyntheticSkin'
    data = bpy.data.armatures.new('SyntheticRig')
    rig = bpy.data.objects.new('SyntheticRig', data)
    bpy.context.collection.objects.link(rig)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = data.edit_bones.new('Root')
    bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    child = data.edit_bones.new('Child')
    child.head, child.tail, child.parent = (0, 0, 1), (0, 0, 2), bone
    if '--skin-bone-subset' in sys.argv:
        unused = data.edit_bones.new('OtherBranch')
        unused.head, unused.tail, unused.parent = (1, 0, 1), (1, 0, 2), bone
    bpy.ops.object.mode_set(mode='OBJECT')
    if '--skin-bone-subset' in sys.argv:
        rig.pose.bones['OtherBranch']['_vapb_fixture_unused_skin_bone'] = 'yes'
    mesh.vertex_groups.new(name='Root').add([0, 1] if uv_shape_split else [0, 1, 2, 3],
                                            1.0, 'REPLACE')
    mesh.vertex_groups.new(name='Child').add([2, 3] if uv_shape_split else [4, 5, 6, 7],
                                             1.0, 'REPLACE')
    mesh.modifiers.new('Skin', 'ARMATURE').object = rig
    mesh.parent = rig
    if '--two-model-skins' in sys.argv:
        other = mesh.copy()
        other.data = mesh.data.copy()
        bpy.context.collection.objects.link(other)
        other.name = 'SyntheticOtherSkin'
        other.location.x += 3
        other.select_set(True)
    target = root / 'Assets/VapbSkinRoundtrip/Input.fbx'
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    assert bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, bake_anim=False,
        use_custom_props=True, use_armature_deform_only=False,
        use_mesh_modifiers=not uv_shape_split,
        apply_scale_options=('FBX_SCALE_ALL' if '--source-units-in-fbx' in sys.argv
                             else 'FBX_SCALE_NONE')) == {'FINISHED'}
    if '--skin-bone-subset' in sys.argv:
        remove_fixture_unused_cluster(target)
    print('SKIN_SOURCE_FBX_PASS')


def remove_fixture_unused_cluster(target):
    """Author a synthetic skin subset while retaining its separate rig branch."""
    from io_scene_fbx import encode_bin, parse_fbx
    from unitypackage_blender_importer.blender.fbx_witness import encode_node
    decoded, version = parse_fbx.parse(str(target), use_namedtuple=True)
    objects = next(node for node in decoded.elems if node.id == b'Objects')
    connections = next(node for node in decoded.elems if node.id == b'Connections')
    models = [node for node in objects.elems if node.id == b'Model'
              and any(prop.props and prop.props[0] == b'_vapb_fixture_unused_skin_bone'
                      for group in node.elems if group.id == b'Properties70'
                      for prop in group.elems)]
    assert len(models) == 1
    clusters = {node.props[0]: node for node in objects.elems
                if node.id == b'Deformer' and node.props[-1] == b'Cluster'}
    linked = [row.props[2] for row in connections.elems
              if row.props[:2] == [b'OO', models[0].props[0]] and row.props[2] in clusters]
    assert len(linked) == 1
    cluster = clusters[linked[0]]
    assert not any(node.props and len(node.props[0])
                   for node in cluster.elems if node.id == b'Indexes')
    objects.elems.remove(cluster)
    connections.elems[:] = [row for row in connections.elems
                            if linked[0] not in row.props[1:3]]
    definitions = next(node for node in decoded.elems if node.id == b'Definitions')
    for node in definitions.elems:
        if node.id == b'Count':
            node.props[0] -= 1
        if node.id == b'ObjectType' and node.props[0] == b'Deformer':
            next(child for child in node.elems if child.id == b'Count').props[0] -= 1
    encode_bin.write(str(target), encode_node(decoded, False), version)
    print('SKIN_SUBSET_FIXTURE_PASS')


def main():
    root = Path(sys.argv[sys.argv.index('--') + 1])
    if '--prepare-fbx' in sys.argv:
        prepare(root)
        return
    addon.register()
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        assert bpy.ops.import_scene.unitypackage(filepath=str(root / 'Source.unitypackage'),
            import_mode='RECONSTRUCT', keep_extracted=False,
            source_storage_directory=str(root / 'BlenderSources')) == {'FINISHED'}
        roots = [obj for obj in bpy.context.scene.objects if obj.get('_vapb_renderer_occurrences')]
        assert len(roots) == 1
        records = json.loads(roots[0]['_vapb_renderer_occurrences'])['records']
        records = [record for record in records if record['renderer_class_id'] == 137]
        assert len(records) == 1 and records[0]['skin']['status'] == 'EXACT'
        native = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
                  and obj.get('_vapb_root_context_id') == records[0]['root_context_id']]
        assert len(native) == 1
        mesh = native[0]
        mesh.data = mesh.data.copy()
        rig = next(mod.object for mod in mesh.modifiers if mod.type == 'ARMATURE')
        scene = bpy.context.scene
        scene.vapb_renderer_root, scene.vapb_renderer_mesh = roots[0], mesh
        assert bpy.ops.vapb.confirm_renderer_binding(occurrence_id=records[0]['occurrence_id']) == {'FINISHED'}
        assert bpy.ops.vapb.load_skin_mappings() == {'FINISHED'}
        source = json.loads((root / 'SourceInfo.json').read_text(encoding='utf-8-sig'))
        explicit_fixture_choices = {row['target_transform_file_id']: row['name'] for row in source['bones']}
        for row in scene.vapb_skin_mapping.rows:
            # This reproduces the user's explicit fixture choice, not a
            # production name-based correspondence algorithm.
            row.target_name = explicit_fixture_choices[row.target_transform_file_id]
            row.confirmed = True
        assert bpy.ops.vapb.confirm_skin_binding() == {'FINISHED'}
        binding_before = json.loads(mesh['_vapb_skin_binding'])
        original_vertex_count = len(mesh.data.vertices)
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh.data)
            bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
            bm.to_mesh(mesh.data)
        finally:
            bm.free()
        mesh.data.update()
        assert len(mesh.data.vertices) > original_vertex_count
        for vertex in mesh.data.vertices:
            vertex.co *= 1.2
        indices = list(range(len(mesh.data.vertices)))
        low_weight = 0.0005 if '--small-weights' in sys.argv else 0.25
        mesh.vertex_groups['Root'].add(indices, low_weight, 'REPLACE')
        mesh.vertex_groups['Child'].add(indices, 1-low_weight, 'REPLACE')
        for old in ('Root', 'Child'):
            group = mesh.vertex_groups[old]
            rig.data.bones[old].name = 'Renamed_' + old
            group.name = 'Renamed_' + old
        mesh.name = 'Renamed edited skin'
        if '--bounded-capture' in sys.argv:
            from unitypackage_blender_importer.tests.blender_bounded_skin_capture import configure
            configure(mesh)
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.wm.save_as_mainfile(filepath=str(root / 'SkinRoundtrip.blend'))
        bpy.ops.wm.open_mainfile(filepath=str(root / 'SkinRoundtrip.blend'))
        mesh = bpy.context.active_object
        assert json.loads(mesh['_vapb_skin_binding']) == binding_before
        if '--bounded-capture' in sys.argv:
            from unitypackage_blender_importer.tests.blender_bounded_skin_capture import capture
            capture(root, mesh)
        before = (len(bpy.data.scenes), len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
        geometry = [tuple(vertex.co) for vertex in mesh.data.vertices]
        weights_before = [[(group.group, group.weight) for group in vertex.groups]
                          for vertex in mesh.data.vertices]
        output = root / (sys.argv[sys.argv.index('--output') + 1] if '--output' in sys.argv else 'Output.unitypackage')
        assert bpy.ops.export_scene.vapb_unitypackage(filepath=str(output)) == {'FINISHED'}
        assert before == (len(bpy.data.scenes), len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
        assert geometry == [tuple(vertex.co) for vertex in mesh.data.vertices]
        assert weights_before == [[(group.group, group.weight) for group in vertex.groups]
                                  for vertex in mesh.data.vertices]
        assert output.is_file()
        if '--bounded-capture' in sys.argv:
            from unitypackage_blender_importer.tests.blender_bounded_skin_capture import finish
            finish(root, output, mesh)
        print('SKIN_PACKAGE_EXPORT_PASS topology=1 weights=1 renamed_bones=1 reload=1 source_unchanged=1')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
