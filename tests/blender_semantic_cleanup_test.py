"""Run with Blender --background --factory-startup --python this_file."""

from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from unitypackage_blender_importer.blender import semantic_cleanup as cleanup
from unitypackage_blender_importer.operators.semantic_cleanup import (
    SEMANTIC_CLEANUP_CLASSES, register_semantic_cleanup_properties,
    unregister_semantic_cleanup_properties,
)


def mesh(name, slots=()):
    data = bpy.data.meshes.new(name)
    data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    for material in slots:
        data.materials.append(material)
    return obj


def rig(name):
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        root = data.edit_bones.new('root')
        root.head, root.tail = (0, 0, 0), (0, 0, 1)
        used = data.edit_bones.new('used')
        used.head, used.tail, used.parent = (0, 0, 1), (0, 0, 2), root
        spare = data.edit_bones.new('spare')
        spare.head, spare.tail = (1, 0, 0), (1, 0, 1)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)
    return obj


def select(*objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def main():
    for cls in SEMANTIC_CLEANUP_CLASSES:
        bpy.utils.register_class(cls)
    register_semantic_cleanup_properties()
    checks = 0
    try:
        mats = [bpy.data.materials.new(f'Mat{i}') for i in range(3)]
        obj = mesh('MaterialMesh', mats)
        obj.data.polygons[0].material_index = 2
        select(obj)
        original_data = obj.data
        preview = cleanup.analyze_cleanup([obj], bones=False)
        assert [int(item.key) for item in preview.candidates] == [0, 1]
        assert obj.data is original_data and len(obj.material_slots) == 3
        assert bpy.ops.vapb.semantic_cleanup_preview() == {'FINISHED'}
        assert len(obj.material_slots) == 3
        assert bpy.ops.vapb.semantic_cleanup_apply() == {'FINISHED'}
        assert len(obj.material_slots) == 1
        assert obj.data.polygons[0].material_index == 0
        assert obj.material_slots[0].material is mats[2]
        assert obj.data is not original_data
        checks += 1

        arm = rig('WeightedRig')
        skinned = mesh('WeightedMesh')
        modifier = skinned.modifiers.new('Skin', 'ARMATURE')
        modifier.object = arm
        group = skinned.vertex_groups.new(name='used')
        group.add([0], 1.0, 'REPLACE')
        select(arm, skinned)
        plan = cleanup.analyze_cleanup([arm, skinned], materials=False)
        reasons = {item.key: item.reasons for item in plan.decisions if item.kind == 'BONE'}
        assert 'WEIGHT' in reasons['used']
        assert 'USED_DESCENDANT' in reasons['root']
        assert reasons['spare'] == ()
        assert cleanup.apply_cleanup(bpy.context, plan) == 1
        assert {bone.name for bone in arm.data.bones} == {'root', 'used'}
        assert group.weight(0) == 1.0
        checks += 1

        envelope_rig = rig('EnvelopeRig')
        envelope_mesh = mesh('EnvelopeMesh')
        envelope_modifier = envelope_mesh.modifiers.new('EnvelopeSkin', 'ARMATURE')
        envelope_modifier.object = envelope_rig
        envelope_modifier.use_bone_envelopes = True
        plan = cleanup.analyze_cleanup([envelope_rig, envelope_mesh], materials=False)
        assert all('ENVELOPE_DEFORMATION_UNRESOLVED' in item.reasons
                   for item in plan.decisions if item.kind == 'BONE')
        checks += 1

        target_rig = rig('ExternalConstraintTarget')
        external_rig = rig('ExternalConstraintOwner')
        constraint = external_rig.pose.bones['root'].constraints.new('COPY_LOCATION')
        constraint.target = target_rig
        constraint.subtarget = 'spare'
        plan = cleanup.analyze_cleanup([target_rig], materials=False)
        assert 'EXTERNAL_CONSTRAINT_TARGET' in next(
            item.reasons for item in plan.decisions if item.key == 'spare')
        checks += 1

        parented = bpy.data.objects.new('BoneChild', None)
        bpy.context.scene.collection.objects.link(parented)
        parented.parent = arm
        parented.parent_type = 'BONE'
        parented.parent_bone = 'used'
        protected = cleanup.analyze_cleanup([arm, skinned], materials=False)
        assert 'BONE_PARENT' in next(item.reasons for item in protected.decisions if item.key == 'used')
        checks += 1

        arm['_vapb_unresolved_source'] = 'opaque'
        protected = cleanup.analyze_cleanup([arm, skinned], materials=False)
        assert all(item.reasons for item in protected.decisions if item.kind == 'BONE')
        del arm['_vapb_unresolved_source']
        checks += 1

        shared = mesh('SharedMesh', mats)
        other = bpy.data.objects.new('OtherUser', shared.data)
        bpy.context.scene.collection.objects.link(other)
        protected = cleanup.analyze_cleanup([shared], bones=False)
        assert all('SHARED_OR_LINKED_DATA' in item.reasons for item in protected.decisions)
        checks += 1

        opaque_parent = bpy.data.objects.new('OpaqueParent', None)
        bpy.context.scene.collection.objects.link(opaque_parent)
        opaque_parent['unknown_bone_or_material_target'] = 'opaque'
        unknown_mesh = mesh('UnknownStateMesh', mats)
        unknown_mesh.parent = opaque_parent
        protected = cleanup.analyze_cleanup([unknown_mesh], bones=False)
        assert all(item.reasons for item in protected.decisions)
        checks += 1
        del opaque_parent['unknown_bone_or_material_target']

        rollback_obj = mesh('RollbackMesh', mats)
        select(rollback_obj)
        before = rollback_obj.data
        before_slots = tuple(rollback_obj.data.materials)
        plan = cleanup.analyze_cleanup([rollback_obj], bones=False)
        original_delta = cleanup._delta_entries
        def fail_after_mutation(_plan):
            raise RuntimeError('injected failure')
        cleanup._delta_entries = fail_after_mutation
        try:
            try:
                cleanup.apply_cleanup(bpy.context, plan)
            except RuntimeError:
                pass
            else:
                raise AssertionError('rollback injection did not fire')
        finally:
            cleanup._delta_entries = original_delta
        assert rollback_obj.data is before
        assert tuple(rollback_obj.data.materials) == before_slots
        checks += 1

        source_scene = bpy.context.scene
        source_data = rollback_obj.data
        with cleanup.cleanup_export_objects(bpy.context, [rollback_obj], bones=False) as staged:
            assert staged.scene is not source_scene
            assert staged.source_to_copy[rollback_obj] is staged.objects[0]
            assert staged.removed_count == 2
            assert len(staged.objects[0].material_slots) == 1
            assert rollback_obj.data is source_data and len(rollback_obj.material_slots) == 3
        assert bpy.context.scene is source_scene
        assert rollback_obj.data is source_data and len(rollback_obj.material_slots) == 3
        checks += 1

        undo_obj = mesh('UndoMesh', mats[:2])
        select(undo_obj)
        assert bpy.ops.vapb.semantic_cleanup_preview() == {'FINISHED'}
        bpy.ops.ed.undo_push(message='Before synthetic cleanup')
        assert bpy.ops.vapb.semantic_cleanup_apply() == {'FINISHED'}
        assert len(undo_obj.material_slots) == 1
        bpy.ops.ed.undo_push(message='After synthetic cleanup')
        assert bpy.ops.ed.undo() == {'FINISHED'}
        restored = bpy.data.objects.get('UndoMesh')
        assert restored is not None and len(restored.material_slots) == 2
        checks += 1

        print(f'SEMANTIC_CLEANUP_PASS checks={checks}')
    finally:
        unregister_semantic_cleanup_properties()
        for cls in reversed(SEMANTIC_CLEANUP_CLASSES):
            bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    main()
