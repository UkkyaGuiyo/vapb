"""TR-001..005: retain native model space; apply scene placement once."""
from pathlib import Path
import json
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.blender.fbx_importer import import_fbx
from unitypackage_blender_importer.blender.hierarchy_builder import build_prefab_hierarchy, unity_position
from unitypackage_blender_importer.unity.prefab_parser import PrefabData, PrefabGameObject, PrefabTransform


def close(a, b):
    assert max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4)) < 2e-5, (a, b)


def make_model(path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    rig = bpy.data.objects.new('Rig', bpy.data.armatures.new('RigData'))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    hips = rig.data.edit_bones.new('Hips')
    hips.head = (0, 0, 0); hips.tail = (0, 0, 0.9)
    spine = rig.data.edit_bones.new('Spine')
    spine.head = hips.tail; spine.tail = (0, 0, 1.8); spine.parent = hips
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.9))
    body = bpy.context.object; body.name = 'Body'; body.scale = (0.4, 0.3, 1.8)
    body.parent = rig
    group = body.vertex_groups.new(name='Hips')
    group.add(list(range(len(body.data.vertices))), 1, 'REPLACE')
    body.modifiers.new('Skin', 'ARMATURE').object = rig
    rig.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, bake_anim=False, add_leaf_bones=False)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)


def fixture(path, placed):
    names = {1: 'ScenePlacement', 2: 'Rig', 3: 'Body', 4: 'Hips', 5: 'Spine'}
    parents = {1: 0, 2: 101, 3: 101, 4: 102, 5: 104}
    transforms = {}
    for go_id in names:
        rotation = dict(x=-0.70710678, y=0, z=0, w=0.70710678) if go_id in (2, 3) else dict(x=0, y=0, z=0, w=1)
        position = dict(x=1, y=2, z=3) if go_id == 1 and placed else dict(x=0, y=0, z=0)
        transforms[100+go_id] = PrefabTransform(100+go_id, go_id, parents[go_id], position, rotation, dict(x=1,y=1,z=1))
    return PrefabData(path, [], {i: PrefabGameObject(i,n) for i,n in names.items()}, transforms)


def main():
    with tempfile.TemporaryDirectory(prefix='native_transform_') as temp:
        path = Path(temp)/'Model.fbx'; make_model(path)
        for placed in (False, True):
            bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
            imported = import_fbx(path, source_package_id='synthetic-model')
            bpy.context.view_layer.update()
            before = {o: o.matrix_world.copy() for o in imported}
            parents = {o: o.parent for o in imported}
            rig = next(o for o in imported if o.type == 'ARMATURE')
            body = next(o for o in imported if o.type == 'MESH')
            relative = before[rig].inverted() @ before[body]
            root, mapping = build_prefab_hierarchy(fixture(Path(temp)/'Scene.prefab', placed), imported, 'synthetic-model', 'Assets/Scene.prefab')
            bpy.context.view_layer.update()
            placement = mapping[1].matrix_world
            for o in imported:
                close(o.matrix_world, placement @ before[o])  # TR-001 / TR-002
                if parents[o] in before:
                    assert o.parent == parents[o]
            close(rig.matrix_world.inverted() @ body.matrix_world, relative)  # TR-004
            assert tuple(mapping[1].location) == (unity_position(dict(x=1,y=2,z=3)) if placed else (0,0,0))  # TR-003
            assert sum(o.type == 'EMPTY' for o in bpy.data.objects) == 2  # TR-005
            assert set(json.loads(root['unity_prefab_bone_identities'])) == {'4','5'}
            assert rig.data.bones['Hips']['unity_prefab_file_id'] == '4'
            assert rig.data.bones['Hips']['_vapb_source_local_file_id'] == '4'
            assert rig.data.bones['Hips']['_vapb_source_hierarchy_path'] == 'ScenePlacement/Rig/Hips'
            assert rig.data.bones['Hips']['_vapb_semantic_id'].startswith('v1:synthetic-model:Assets/Scene.prefab:4')
            assert body['unity_prefab_file_id'] == '3'
            assert body['unity_source_package_id'] == 'synthetic-model'
            for o in imported:
                assert max(abs(v) for row in o.matrix_world for v in row) < 5
        # A separate native model attached under a bone still needs that bone
        # Object parent. Do not collapse its identity or ancestor chain.
        bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
        imported = import_fbx(path)
        attachment = bpy.data.objects.new('Attachment', bpy.data.meshes.new('AttachmentData'))
        bpy.context.scene.collection.objects.link(attachment)
        data = fixture(Path(temp)/'Attached.prefab', False)
        data.game_objects[6] = PrefabGameObject(6, 'Attachment')
        data.transforms[106] = PrefabTransform(106, 6, 105, dict(x=0,y=0,z=0), dict(x=0,y=0,z=0,w=1), dict(x=1,y=1,z=1))
        root, mapping = build_prefab_hierarchy(data, imported+[attachment])
        assert mapping[4].type == 'EMPTY' and mapping[5].type == 'EMPTY'
        assert attachment.parent == mapping[5]
        assert json.loads(root['unity_prefab_bone_identities']) == {}
    print('TR_001_005_OK')


if __name__ == '__main__':
    main()
