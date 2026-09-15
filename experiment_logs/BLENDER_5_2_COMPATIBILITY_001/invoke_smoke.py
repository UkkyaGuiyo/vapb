"""Smoke-test the Blender 5.2 foreground File Browser invoke path."""

from pathlib import Path
import sys

import bpy


sys.path.insert(0, str(Path(__import__("os").environ["VAPB_REPO_PARENT"])))
import unitypackage_blender_importer as addon  # noqa: E402

addon.register()


def quit_later():
    print("INVOKE_TIMEOUT_QUIT", flush=True)
    addon.unregister()
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(quit_later, first_interval=2.0)
try:
    result = bpy.ops.import_scene.unitypackage("INVOKE_DEFAULT")
    print(f"INVOKE_DEFAULT_RESULT={result}", flush=True)
except Exception as exc:
    print(f"INVOKE_DEFAULT_EXCEPTION={type(exc).__name__}: {exc}", flush=True)
    addon.unregister()
    bpy.ops.wm.quit_blender()
