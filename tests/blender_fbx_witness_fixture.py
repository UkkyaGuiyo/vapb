"""Generate a synthetic raw-FBX preservation experiment, not a production mapper.

Blender CLI: --python-exit-code 1 --python this_file -- <oracle_project>
Uses installed Blender GPL FBX APIs; no third-party implementation is copied.
"""
from pathlib import Path
import sys
import bpy
from io_scene_fbx import encode_bin, parse_fbx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_witness import PROPERTY, canonical, encode_node


def main():
    folder = Path(sys.argv[sys.argv.index('--') + 1])
    folder.mkdir(parents=True, exist_ok=True)
    for name in ('Source.fbx', 'Noop.fbx', 'Witness.fbx'):
        if (folder / name).exists():
            raise ValueError('FIXTURE_ALREADY_EXISTS')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add()
    mesh = bpy.context.object
    mesh.shape_key_add(name='Basis')
    shape = mesh.shape_key_add(name='SyntheticShape')
    shape.data[0].co.x += 0.2
    armature = bpy.data.armatures.new('SyntheticArmature')
    rig = bpy.data.objects.new('SyntheticRig', armature)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.edit_bones.new('Root')
    root.head, root.tail = (0, 0, 0), (0, 0, 1)
    child = armature.edit_bones.new('Child')
    child.head, child.tail, child.parent = (0, 0, 1), (0, 0, 2), root
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.vertex_groups.new(name='Root').add([0, 1, 2, 3], 1.0, 'REPLACE')
    mesh.vertex_groups.new(name='Child').add([4, 5, 6, 7], 1.0, 'REPLACE')
    mesh.modifiers.new('SyntheticSkin', 'ARMATURE').object = rig
    mesh.parent = rig
    source = folder / 'Source.fbx'
    assert bpy.ops.export_scene.fbx(filepath=str(source), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, bake_anim=False,
        use_custom_props=True, use_armature_deform_only=False) == {'FINISHED'}
    source_bytes = source.read_bytes()
    decoded, version = parse_fbx.parse(str(source), use_namedtuple=True)
    objects = next(child for child in decoded.elems if child.id == b'Objects')
    models = [node for node in objects.elems if node.id == b'Model']
    assert len({node.props[0] for node in models}) == len(models)
    for filename, witness in [('Noop.fbx', False), ('Witness.fbx', True)]:
        destination = folder / filename
        encode_bin.write(str(destination), encode_node(decoded, witness), version)
        after, after_version = parse_fbx.parse(str(destination), use_namedtuple=True)
        assert version == after_version and canonical(decoded) == canonical(after), 'SOURCE_SEMANTICS_CHANGED'
        if witness:
            after_objects = next(child for child in after.elems if child.id == b'Objects')
            for model in (node for node in after_objects.elems if node.id == b'Model'):
                props = next(child for child in model.elems if child.id == b'Properties70')
                markers = [p for p in props.elems if p.props and p.props[0] == PROPERTY]
                assert len(markers) == 1 and markers[0].props[-1] == str(model.props[0]).encode()
    assert source.read_bytes() == source_bytes
    print(f'FBX_WITNESS_FIXTURE_PASS models={len(models)} noop_semantics=1 witness_semantics=1 original_unchanged=1')


if __name__ == '__main__':
    main()
