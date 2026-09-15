"""Foreground Blender 5.2.1 serial real-package import test."""

from pathlib import Path
import json
import sys
import time

import bpy


ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
RESULT = Path(__file__).with_name("foreground_serial_result.json")
sys.path.insert(0, str(ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as module  # noqa: E402


addon.register()
started = time.monotonic()
perform_count = 0
started_second = False
records = []


def auto_select_prefab(self, context, _event):
    self.prefab_choice = "AUTO"
    return self.execute(context)


module.UNITYPACKAGE_OT_import_prefab.invoke = auto_select_prefab
original_perform_import = module.UNITYPACKAGE_OT_import._perform_import


def traced_perform_import(self, context):
    global perform_count
    result = original_perform_import(self, context)
    perform_count += 1
    records.append(
        {
            "count": perform_count,
            "result": sorted(result),
            "state": self._prepare_state,
            "modal_registered": self._modal_registered,
            "objects": len(bpy.data.objects),
        }
    )
    print(f"SERIAL_IMPORT_{perform_count}={records[-1]}", flush=True)
    return result


module.UNITYPACKAGE_OT_import._perform_import = traced_perform_import


def launch_second():
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(PACKAGE),
        import_mode="RECONSTRUCT",
        prefab_choice="AUTO",
        keep_extracted=False,
    )
    print(f"SERIAL_SECOND_INITIAL={result}", flush=True)
    return None


def finish_check():
    global started_second
    if perform_count >= 2:
        passed = all(
            item["result"] == ["FINISHED"]
            and item["state"] == "FINISHED"
            and item["modal_registered"] is False
            for item in records
        )
        result = {
            "status": "PASS" if passed else "FAIL",
            "perform_count": perform_count,
            "records": records,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SERIAL_RESULT=" + json.dumps(result, ensure_ascii=False), flush=True)
        addon.unregister()
        bpy.ops.wm.quit_blender()
        return None
    if time.monotonic() - started > 240:
        print("SERIAL_TIMEOUT", flush=True)
        addon.unregister()
        bpy.ops.wm.quit_blender()
        return None
    if perform_count == 1 and not started_second:
        started_second = True
        bpy.app.timers.register(launch_second, first_interval=0.25)
    return 0.5


bpy.app.timers.register(finish_check, first_interval=0.25)
result = bpy.ops.import_scene.unitypackage(
    filepath=str(PACKAGE),
    import_mode="RECONSTRUCT",
    prefab_choice="AUTO",
    keep_extracted=False,
)
print(f"SERIAL_FIRST_INITIAL={result}", flush=True)
