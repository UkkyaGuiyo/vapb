"""Synthetic Blender runtime test for the PhysBone preview UI and timer."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("run under Blender")
    for name in list(sys.modules):
        if name == "unitypackage_blender_importer" or name.startswith("unitypackage_blender_importer."):
            del sys.modules[name]
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer.blender import physbone_runtime as runtime

    addon.register()
    try:
        assert any(cls.bl_idname == "VAPB_PT_physics_preview" for cls in addon.PHYSICS_PREVIEW_CLASSES if hasattr(cls, "bl_idname"))
        panel = next(cls for cls in addon.PHYSICS_PREVIEW_CLASSES if getattr(cls, "bl_idname", "") == "VAPB_PT_physics_preview")
        assert panel.bl_space_type == "VIEW_3D"
        assert hasattr(bpy.types.Scene, "vapb_physics_preview")

        arm_data = bpy.data.armatures.new("SyntheticArmature")
        armature = bpy.data.objects.new("SyntheticArmature", arm_data)
        bpy.context.scene.collection.objects.link(armature)
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        for name, head, tail, parent in (
            ("BoneA", (0, 0, 0), (0, 1, 0), None),
            ("BoneB", (0, 1, 0), (0, 2, 0), "BoneA"),
            ("BoneC", (0, 2, 0), (0, 3, 0), "BoneB"),
        ):
            bone = arm_data.edit_bones.new(name)
            bone.head = head
            bone.tail = tail
            if parent:
                bone.parent = arm_data.edit_bones[parent]
        bpy.ops.object.mode_set(mode="OBJECT")
        arm_data.bones["BoneA"]["unity_prefab_file_id"] = "100"
        armature["unity_source_package_id"] = "pkg-a"
        armature["unity_asset_path"] = "Assets/Synthetic.prefab"
        other = armature.copy()
        other.data = armature.data.copy()
        other.name = "OtherPackageArmature"
        bpy.context.scene.collection.objects.link(other)
        other["unity_source_package_id"] = "pkg-b"

        root = bpy.data.objects.new("SyntheticPrefabRoot", None)
        bpy.context.scene.collection.objects.link(root)
        root["unity_source_package_id"] = "pkg-a"
        root["unity_asset_path"] = "Assets/Synthetic.prefab"
        root["unity_physbone_source_json"] = json.dumps({
            "schema_version": 1,
            "physbones": [{
                "root_game_object_file_id": "100",
                "collider_file_ids": ["200"],
            }],
            "colliders": [{"component_file_id": "200"}],
        })
        root["unity_prefab_bone_identities"] = json.dumps({"100": {"bone_name": "BoneA"}})

        scene = bpy.context.scene
        controller = runtime.get_controller()
        status = controller.enable(scene)
        print("PHYSBONE_ENABLE_STATUS", status, controller.last_error, controller.matched_count, controller.unmatched)
        assert status == runtime.PREVIEW_RUNNING
        assert controller.matched_count == 1
        assert controller.unmatched == 0
        assert bpy.app.timers.is_registered(controller._timer_callback)

        state = controller.chains[0].state
        before = state.positions
        armature.pose.bones["BoneA"].location.x = 1.0
        bpy.context.view_layer.update()
        controller._timer_tick()
        assert controller.chains[0].state.positions != before
        controller.reset()
        assert controller.chains[0].state.velocities == ((0.0, 0.0, 0.0),) * 3
        controller.disable()
        assert not bpy.app.timers.is_registered(controller._timer_callback)
        print("PHYSBONE_PREVIEW_BLENDER_OK")
    finally:
        runtime.shutdown()
        addon.unregister()


main()
