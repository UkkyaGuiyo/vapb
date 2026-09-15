"""Run with Blender 4.2.1 without --background to verify modal handoff."""

from __future__ import annotations

from pathlib import Path
import sys
import time

import bpy


ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
sys.path.insert(0, str(ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as operator_module  # noqa: E402


addon.register()
started = time.monotonic()
perform_reached = False
perform_result = None


def select_first_prefab(self, _context, _prefab_paths):
    self._prefab_dialog_shown = True
    return False


operator_module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = select_first_prefab
original_perform_import = operator_module.UNITYPACKAGE_OT_import._perform_import


def traced_perform_import(self, context):
    global perform_reached, perform_result
    perform_reached = True
    print(f"FOREGROUND_PERFORM_REACHED state={self._prepare_state}", flush=True)
    result = original_perform_import(self, context)
    perform_result = result
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    shape_keys = sum(1 for obj in meshes if obj.data.shape_keys)
    vertex_groups = sum(1 for obj in meshes if obj.vertex_groups)
    prefab_roots = [obj for obj in bpy.data.objects if obj.get("unity_source_prefab")]
    hierarchy_links = sum(1 for obj in bpy.data.objects if obj.parent is not None)
    print(
        "FOREGROUND_SCENE_VALIDATION "
        f"objects={len(bpy.data.objects)} meshes={len(meshes)} "
        f"armatures={len(armatures)} shape_keys={shape_keys} "
        f"vertex_groups={vertex_groups} materials={len(bpy.data.materials)} "
        f"images={len(bpy.data.images)} prefab_roots={len(prefab_roots)} "
        f"hierarchy_links={hierarchy_links}",
        flush=True,
    )
    print(f"FOREGROUND_PERFORM_RETURN state={self._prepare_state} result={result}", flush=True)
    return result


operator_module.UNITYPACKAGE_OT_import._perform_import = traced_perform_import


def finish_when_reached():
    if perform_reached:
        print("FOREGROUND_UI_LIFECYCLE_OK", flush=True)
        addon.unregister()
        bpy.ops.wm.quit_blender()
        return None
    if time.monotonic() - started > 90.0:
        print("FOREGROUND_UI_LIFECYCLE_TIMEOUT", flush=True)
        addon.unregister()
        bpy.ops.wm.quit_blender()
        return None
    return 0.25


bpy.app.timers.register(finish_when_reached, first_interval=0.25)
result = bpy.ops.import_scene.unitypackage(
    filepath=str(PACKAGE),
    import_mode="RECONSTRUCT",
    prefab_choice="AUTO",
    keep_extracted=False,
)
print(f"FOREGROUND_EXECUTE_RESULT={result} background={bpy.app.background}", flush=True)
