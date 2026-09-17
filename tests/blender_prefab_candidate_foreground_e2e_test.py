"""Foreground synthetic proof for Automatic (Recommended) Prefab selection."""

from __future__ import annotations

import base64
from pathlib import Path
import sys
import tempfile
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.operators import import_unitypackage as module
from unitypackage_blender_importer.tests.blender_cross_package_dependency_test import make_fbx, material, package
from unitypackage_blender_importer.tests.blender_group_import_e2e_test import prefab


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="pca_foreground_"))
    fbx_guid, material_guid, texture_guid = "a" * 32, "b" * 32, "c" * 32
    primary = root / "SyntheticPrimary.unitypackage"
    empty = b"""%YAML 1.1
--- !u!1 &1001
GameObject:
  m_Name: EmptyCandidate
"""
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    package(primary, [
        ("1" * 32, "Assets/EmptyCandidate.prefab", empty),
        ("2" * 32, "Assets/AvatarCandidate.prefab", prefab(fbx_guid, material_guid)),
        (fbx_guid, "Assets/Avatar.fbx", make_fbx()),
        (material_guid, "Assets/Avatar.mat", material(texture_guid)),
        (texture_guid, "Assets/Avatar.png", png),
    ])
    state = {"started": False, "prefab_invokes": 0, "result": None, "error": None}
    addon.register()
    original_monitor = module.ImportProgressMonitor

    class RecordingMonitor(original_monitor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            state["monitor"] = self

    module.ImportProgressMonitor = RecordingMonitor
    original_prefab_invoke = module.UNITYPACKAGE_OT_import_prefab.invoke

    def prefab_invoke(self, context, event):
        state["prefab_invokes"] += 1
        return original_prefab_invoke(self, context, event)

    module.UNITYPACKAGE_OT_import_prefab.invoke = prefab_invoke

    def start():
        state["started"] = True
        try:
            state["result"] = sorted(bpy.ops.import_scene.unitypackage(filepath=str(primary), keep_extracted=False))
        except Exception as exc:
            state["error"] = repr(exc)
        return None

    bpy.app.timers.register(start, first_interval=0.4)
    started = time.perf_counter()

    def wait_done():
        try:
            if state["error"] is not None:
                raise AssertionError(state["error"])
            if state["started"] and not module._PREPARED_SESSIONS and any(obj.get("unity_prefab_file_id") == "1001" for obj in bpy.data.objects):
                assert state["prefab_invokes"] == 0, state
                assert any(obj.get("unity_prefab_file_id") == "1001" for obj in bpy.data.objects), state
                history = state["monitor"].history
                stages = [item["stage"] for item in history]
                expected = {
                    module.ImportProgressStage.READING_PACKAGE,
                    module.ImportProgressStage.ANALYZING_PREFABS,
                    module.ImportProgressStage.RESOLVING_PACKAGES,
                    module.ImportProgressStage.IMPORTING_FBX,
                    module.ImportProgressStage.BUILDING_HIERARCHY,
                    module.ImportProgressStage.CREATING_VISUALS,
                    module.ImportProgressStage.RESOLVING_DEPENDENCIES,
                    module.ImportProgressStage.FINALIZING,
                    module.ImportProgressStage.COMPLETE,
                }
                assert expected.issubset(set(stages)), stages
                assert stages[-1] == module.ImportProgressStage.COMPLETE, stages
                assert module._ACTIVE_PROGRESS_MONITOR is None
                assert state["monitor"].sink.started is False
                print("PCA_FOREGROUND_AUTOMATIC_OK", state, flush=True)
                module.UNITYPACKAGE_OT_import_prefab.invoke = original_prefab_invoke
                module.ImportProgressMonitor = original_monitor
                addon.unregister()
                bpy.ops.wm.quit_blender()
                return None
            if time.perf_counter() - started > 60:
                raise AssertionError(f"timeout: {state}, sessions={len(module._PREPARED_SESSIONS)}")
            return 0.2
        except Exception:
            import traceback
            traceback.print_exc()
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(wait_done, first_interval=0.6)


if __name__ == "__main__":
    main()
