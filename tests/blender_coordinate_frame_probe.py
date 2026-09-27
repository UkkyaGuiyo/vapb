"""Public asymmetric Skin fixture verifies the Unity/native Blender basis.

Run --prepare against an external Unity project, run the companion public API
Unity probe, then run this script without --prepare. This verifies the common
coordinate basis, not full native occurrence placement or animated skin parity.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_importer import import_fbx
from unitypackage_blender_importer.blender.hierarchy_builder import unity_position


def point_set_error(left, right):
    return max(max(min((Vector(a) - Vector(b)).length for b in right) for a in left),
               max(min((Vector(b) - Vector(a)).length for a in left) for b in right))


def main():
    project = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    assert not project.is_relative_to(repo)
    path = project / 'Assets/VapbCoordinateFrame/Input.fbx'
    authored_path = project / 'VapbCoordinateFrameAuthored.json'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    if '--prepare' in sys.argv:
        assert not path.exists() and not authored_path.exists()
        mesh_data = bpy.data.meshes.new('SyntheticCoordinateSkin')
        # Unequal axes and an off-axis point prevent a symmetric cube from
        # hiding reflection or axis permutation. These are authored coordinates.
        points = [(0, 0, 0), (1, 0, 0), (0, 2, 0), (0.3, 0.7, 3)]
        mesh_data.from_pydata(points, [], [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)])
        mesh_data.update()
        mesh = bpy.data.objects.new('SyntheticCoordinateSkin', mesh_data)
        bpy.context.collection.objects.link(mesh)
        armature = bpy.data.armatures.new('SyntheticCoordinateRig')
        rig = bpy.data.objects.new('SyntheticCoordinateRig', armature)
        bpy.context.collection.objects.link(rig)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bone = armature.edit_bones.new('Root')
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.vertex_groups.new(name='Root').add(list(range(len(points))), 1.0, 'REPLACE')
        mesh.modifiers.new('Skin', 'ARMATURE').object = rig
        mesh.parent = rig
        mesh.select_set(True)
        bpy.context.view_layer.update()
        path.parent.mkdir(parents=True, exist_ok=True)
        assert bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
            object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, bake_anim=False,
            use_armature_deform_only=False, apply_scale_options='FBX_SCALE_NONE') == {'FINISHED'}
        authored_path.write_text(json.dumps({'world_positions': points,
            'fbx_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))
        print('COORDINATE_FRAME_FIXTURE_READY')
        return

    authored = json.loads(authored_path.read_text())
    observed = json.loads((project / 'VapbCoordinateFrameSnapshot.json').read_text(encoding='utf-8-sig'))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == authored['fbx_sha256']
    assert observed['pass'] and observed['hashes_unchanged']
    assert observed['source_sha256'] == before
    objects = import_fbx(path, source_asset_guid=observed['asset_guid'])
    meshes = [obj for obj in objects if obj.type == 'MESH']
    assert len(meshes) == 1
    mesh = meshes[0]
    assert mesh['_vapb_fbx_source_asset_guid'] == observed['asset_guid']
    assert mesh['_vapb_fbx_source_asset_sha256'] == before
    bpy.context.view_layer.update()
    native = [list(mesh.matrix_world @ v.co) for v in mesh.data.vertices]
    unity = observed['world_positions']
    assert observed['importer_use_file_scale'] and not observed['importer_bake_axis_conversion']
    scale = observed['importer_file_scale'] * observed['importer_global_scale']
    assert abs(scale - 0.01) < 1e-7
    unity_local = [(-v['x'], -v['z'], v['y']) for v in observed['source_local_vertices']]
    direct_mesh_local = [(v.co.x * scale, -v.co.z * scale, v.co.y * scale)
                         for v in mesh.data.vertices]
    converted_native_basis = [(-v['x'], -v['z'], v['y']) for v in unity]
    converted_semantic_basis = [unity_position(v) for v in unity]
    result = dict(native_import_vs_authored=point_set_error(native, authored['world_positions']),
        unity_native_basis_vs_authored=point_set_error(converted_native_basis, authored['world_positions']),
        unity_semantic_basis_vs_native=point_set_error(converted_semantic_basis, native),
        unity_direct_mesh_local_vs_blender=point_set_error(unity_local, direct_mesh_local),
        blender_vertex_count=len(native), unity_vertex_count=len(unity),
        input_unchanged=hashlib.sha256(path.read_bytes()).hexdigest() == before)
    (project / 'VapbCoordinateFrameComparison.json').write_text(json.dumps(result, indent=2))
    assert result['input_unchanged']
    assert result['native_import_vs_authored'] < 1e-5
    assert result['unity_native_basis_vs_authored'] < 1e-5
    assert result['unity_semantic_basis_vs_native'] < 1e-5, 'SEMANTIC_NATIVE_BASIS_MISMATCH'
    assert result['unity_direct_mesh_local_vs_blender'] < 1e-5, 'DIRECT_MESH_LOCAL_FRAME_MISMATCH'
    print('COORDINATE_FRAME_PASS', json.dumps(result))


main()
