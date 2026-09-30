"""Actual optional cleanup export, isolated copies and failure recovery."""
from pathlib import Path
import sys
import tempfile
import json

import bpy
from io_scene_fbx.parse_fbx import parse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.blender import roundtrip_export


def main():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    addon.register()
    try:
        arm = bpy.data.armatures.new('Synthetic rig')
        rig = bpy.data.objects.new('Synthetic rig', arm)
        bpy.context.collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        root = arm.edit_bones.new('Root')
        root.head, root.tail = (0, 0, 0), (0, 0, 1)
        used = arm.edit_bones.new('Used')
        used.head, used.tail, used.parent = (0, 0, 1), (0, 0, 2), root
        unused = arm.edit_bones.new('Unused')
        unused.head, unused.tail, unused.parent = (1, 0, 1), (1, 0, 2), root
        bpy.ops.object.mode_set(mode='OBJECT')
        data = bpy.data.meshes.new('Synthetic skin')
        data.from_pydata([(0, 0, 1), (1, 0, 1), (0, 1, 1)], [], [(0, 1, 2)])
        mesh = bpy.data.objects.new('Synthetic skin', data)
        bpy.context.collection.objects.link(mesh)
        mesh.parent = rig
        mesh.modifiers.new('Skin', 'ARMATURE').object = rig
        mesh.vertex_groups.new(name='Used').add([0, 1, 2], 1.0, 'REPLACE')
        data.materials.append(bpy.data.materials.new('Used material'))
        data.materials.append(bpy.data.materials.new('Unused material'))
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        bpy.context.view_layer.update()
        source_scene = bpy.context.scene
        before = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures), len(bpy.data.scenes))
        selected = set(bpy.context.selected_objects)
        from unitypackage_blender_importer.blender.semantic_cleanup import analyze_cleanup
        plan = analyze_cleanup(selected)
        assert len(plan.candidates) == 2

        def unchanged():
            assert mesh.data == data and rig.data == arm
            assert len(data.materials) == 2 and len(arm.bones) == 3
            assert data.polygons[0].material_index == 0
            assert mesh.modifiers[0].object == rig and mesh.parent == rig
            assert source_scene == bpy.context.scene
            assert bpy.context.view_layer.objects.active == mesh
            assert set(bpy.context.selected_objects) == selected
            assert before == (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures), len(bpy.data.scenes))

        with tempfile.TemporaryDirectory(prefix='vapb_cleanup_export_') as folder:
            path = Path(folder) / 'Synthetic.fbx'
            original_manifest = roundtrip_export.build_material_manifest
            def fail_manifest(*args, **kwargs):
                raise ValueError('intentional synthetic manifest failure')
            roundtrip_export.build_material_manifest = fail_manifest
            try:
                try:
                    result = bpy.ops.export_scene.unitypackage_roundtrip(filepath=str(path),
                        selected_only=True, cleanup_materials=True, cleanup_bones=True)
                    assert result == {'CANCELLED'}
                except RuntimeError:
                    pass
            finally:
                roundtrip_export.build_material_manifest = original_manifest
            assert not path.exists()
            unchanged()
            assert bpy.ops.export_scene.unitypackage_roundtrip(filepath=str(path),
                selected_only=True, cleanup_materials=True, cleanup_bones=True) == {'FINISHED'}
            unchanged()
            tree, _ = parse(str(path), use_namedtuple=True)
            objects = next(item for item in tree.elems if item.id == b'Objects')
            bones = [item for item in objects.elems if item.id == b'Model' and item.props[2] == b'LimbNode']
            materials = [item for item in objects.elems if item.id == b'Material']
            assert len(bones) == 2, f'Export bone count {len(bones)} expected 2'
            assert len(materials) == 1, 'Export did not remove only the unused material slot'
            manifest = json.loads(path.with_suffix('.materialmap.json').read_text(encoding='utf-8'))
            assert manifest['cleanup']['removed_count'] == 2
            assert len(manifest['bindings']) == 1
            no_cleanup = Path(folder) / 'SyntheticNoCleanup.fbx'
            assert bpy.ops.export_scene.unitypackage_roundtrip(filepath=str(no_cleanup),
                selected_only=True, cleanup_materials=False, cleanup_bones=False) == {'FINISHED'}
            unchanged()
            tree, _ = parse(str(no_cleanup), use_namedtuple=True)
            objects = next(item for item in tree.elems if item.id == b'Objects')
            assert len([item for item in objects.elems if item.id == b'Model' and item.props[2] == b'LimbNode']) == 3
            roundtrip_export.build_material_manifest = fail_manifest
            try:
                try:
                    bpy.ops.export_scene.unitypackage_roundtrip(filepath=str(Path(folder)/'FailureNoCleanup.fbx'),
                        selected_only=True, cleanup_materials=False, cleanup_bones=False)
                except RuntimeError:
                    pass
            finally:
                roundtrip_export.build_material_manifest = original_manifest
            unchanged()
            assert not (Path(folder)/'FailureNoCleanup.fbx').exists()
            print('CLEANUP_EXPORT_PASS bones=2 materials=1 source_unchanged=1 failure_recovery=1 no_cleanup_success_failure=1')
    finally:
        addon.unregister()


if __name__ == '__main__':
    main()
