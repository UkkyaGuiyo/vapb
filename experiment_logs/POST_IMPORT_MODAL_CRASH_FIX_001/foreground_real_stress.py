"""Foreground Blender 5.2.1 real-package lifecycle and post-import stress test."""

from pathlib import Path
import json
import sys
import time

import bpy


ROOT = Path(r"<LOCAL_PATH>")
PACKAGE = Path(r"<LOCAL_PATH>")
RESULT = Path(__file__).with_name("foreground_real_stress_result.json")
sys.path.insert(0, str(ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as module  # noqa: E402


addon.register()
started = time.monotonic()
import_finished = False
stress_started = None
stress_cycles = 0
delete_restore_cycles = 0
import_result = None
modal_after_finish = None
baseline = {name: bpy.data.objects.get(name) for name in ("Cube", "Camera", "Light")}


def auto_select_prefab(self, context, _event):
    """Exercise the separate prefab operator without requiring mouse input."""
    self.prefab_choice = "AUTO"
    return self.execute(context)


module.UNITYPACKAGE_OT_import_prefab.invoke = auto_select_prefab
original_perform_import = module.UNITYPACKAGE_OT_import._perform_import


def traced_perform_import(self, context):
    global import_finished, import_result, modal_after_finish, stress_started
    result = original_perform_import(self, context)
    import_result = sorted(result)
    import_finished = True
    modal_after_finish = self._modal_registered
    stress_started = time.monotonic()
    print(
        f"REAL_IMPORT_FINISHED result={result} state={self._prepare_state} "
        f"modal_registered={self._modal_registered}",
        flush=True,
    )
    return result


module.UNITYPACKAGE_OT_import._perform_import = traced_perform_import


def stress_step():
    global stress_cycles, delete_restore_cycles
    if not import_finished:
        if time.monotonic() - started > 180:
            finish("TIMEOUT_IMPORT")
            return None
        return 0.25

    if stress_cycles < 100:
        meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
        for obj in meshes[:8]:
            obj.hide_set(True)
            obj.hide_set(False)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in meshes[:8]:
            obj.select_set(True)
        bpy.ops.object.select_all(action="DESELECT")
        for area in getattr(bpy.context.screen, "areas", []):
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"
                area.spaces.active.shading.type = "SOLID"
                area.spaces.active.shading.type = "MATERIAL"
        view_area = next(
            (area for area in getattr(bpy.context.screen, "areas", []) if area.type == "VIEW_3D"),
            None,
        )
        if meshes and view_area is not None:
            region = next((item for item in view_area.regions if item.type == "WINDOW"), None)
            if region is not None:
                target = meshes[0]
                target_name = target.name
                target_data = target.data.copy()
                target_matrix = target.matrix_world.copy()
                target_collection = target.users_collection[0] if target.users_collection else None
                with bpy.context.temp_override(
                    window=bpy.context.window, area=view_area, region=region
                ):
                    bpy.ops.object.select_all(action="DESELECT")
                    target.select_set(True)
                    bpy.context.view_layer.objects.active = target
                    bpy.ops.object.delete()
                # Blender's ed.undo poll is false from timers and caused a native crash
                # in a separate probe. Restore the exact object data without invoking it.
                if target_collection is not None:
                    restored = bpy.data.objects.new(target_name, target_data)
                    restored.matrix_world = target_matrix
                    target_collection.objects.link(restored)
                    delete_restore_cycles += 1
        bpy.context.scene.frame_set((stress_cycles % 24) + 1)
        stress_cycles += 1
        return 0.05

    current = {name: bpy.data.objects.get(name) is obj for name, obj in baseline.items()}
    result = {
        "status": "PASS" if all(current.values()) and modal_after_finish is False else "FAIL",
        "package": str(PACKAGE),
        "import_result": import_result,
        "import_state": "FINISHED",
        "modal_registered_after_finish": modal_after_finish,
        "stress_cycles": stress_cycles,
        "delete_restore_cycles": delete_restore_cycles,
        "undo_operator": "not_called_ed_undo_poll_false_in_timer_context",
        "baseline_objects_retained": current,
        "objects": len(bpy.data.objects),
        "meshes": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("POST_IMPORT_STRESS_RESULT=" + json.dumps(result, ensure_ascii=False), flush=True)
    finish("STRESS_COMPLETE")
    return None


def finish(reason):
    print(f"TEST_FINISH_REASON={reason}", flush=True)
    addon.unregister()
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(stress_step, first_interval=0.25)
result = bpy.ops.import_scene.unitypackage(
    filepath=str(PACKAGE),
    import_mode="RECONSTRUCT",
    prefab_choice="AUTO",
    keep_extracted=False,
)
print(f"FOREGROUND_INITIAL_RESULT={result} background={bpy.app.background}", flush=True)
