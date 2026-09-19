"""Local-only foreground progress probe for a real UnityPackage.

The package path is supplied through ``UNITYPACKAGE_REAL_TEST_FILE`` or after
``--``.  No real asset path or payload is stored in the repository.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

package_raw = os.environ.get("UNITYPACKAGE_REAL_TEST_FILE", "")
if "--" in sys.argv:
    values = sys.argv[sys.argv.index("--") + 1 :]
    package_raw = values[0] if values else package_raw
if not package_raw:
    print("REAL_PROGRESS_PACKAGE_SKIPPED", flush=True)
    bpy.ops.wm.quit_blender()
    raise SystemExit(2)

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as module  # noqa: E402


def main() -> None:
    package = Path(package_raw).expanduser().resolve()
    state = {"started": False, "result": None, "error": None, "monitor": None, "group_selected": False}
    addon.register()
    original_monitor = module.ImportProgressMonitor

    class RecordingMonitor(original_monitor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            state["monitor"] = self

    module.ImportProgressMonitor = RecordingMonitor

    def start():
        state["started"] = True
        try:
            state["result"] = bpy.ops.import_scene.unitypackage(
                filepath=str(package),
                import_mode="RECONSTRUCT",
                prefab_choice="AUTO",
                keep_extracted=False,
            )
        except Exception as exc:  # pragma: no cover - Blender callback path
            state["error"] = repr(exc)
        return None

    started = time.perf_counter()
    bpy.app.timers.register(start, first_interval=0.5)

    def wait_done():
        try:
            if state["error"] is not None:
                raise AssertionError(state["error"])
            if not state["group_selected"]:
                for session_id, session in list(module._PREPARED_SESSIONS.items()):
                    if session.pending_stage == "SIBLINGS":
                        result = bpy.ops.import_scene.unitypackage_siblings(
                            "EXEC_DEFAULT", session_id=session_id, import_action="TOGETHER"
                        )
                        assert "FINISHED" in result, result
                        state["group_selected"] = True
                        break
            monitor = state["monitor"]
            if state["started"] and monitor is not None and monitor.state.status == "COMPLETE":
                meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
                reconstructed_meshes = [
                    obj for obj in meshes if obj.get("unity_prefab_file_id")
                ]
                materials = [material for material in bpy.data.materials if material.use_nodes]
                base_color_links = sum(
                    1
                    for material in materials
                    if material.node_tree.nodes.get("Principled BSDF")
                    and material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].is_linked
                )
                expected_meshes = int(os.environ.get("UNITYPACKAGE_EXPECTED_MESH_COUNT", "15"))
                assert len(reconstructed_meshes) == expected_meshes, (
                    len(reconstructed_meshes),
                    len(meshes),
                )
                assert materials and base_color_links > 0, (len(materials), base_color_links)
                stages = [item["stage"] for item in monitor.history]
                required = {
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
                assert required.issubset(set(stages)), stages
                assert stages[-1] == module.ImportProgressStage.COMPLETE, stages
                assert module._ACTIVE_PROGRESS_MONITOR is None
                overlay = monitor.sink.overlay
                assert overlay is not None
                assert overlay.install_count >= 1, overlay.debug_events
                assert overlay.draw_callback_count > 0, overlay.debug_events
                assert overlay.last_draw_time is not None, overlay.debug_events
                assert overlay.gpu_draw_count > 0, overlay.debug_events
                assert overlay.removed_count == 1, overlay.debug_events
                print(
                    "REAL_FOREGROUND_PROGRESS_OK "
                    + json.dumps(
                        {
                            "elapsed_seconds": monitor.state.elapsed_seconds,
                            "mesh_count": len(meshes),
                            "reconstructed_mesh_count": len(reconstructed_meshes),
                            "material_count": len(materials),
                            "base_color_links": base_color_links,
                            "stage_count": monitor.state.stage_count,
                            "history_count": len(stages),
                            "blocking_events": sum(
                                1 for item in monitor.history if item["blocking_operation"]
                            ),
                            "overlay_install_count": overlay.install_count,
                            "overlay_draw_callback_count": overlay.draw_callback_count,
                            "overlay_gpu_draw_count": overlay.gpu_draw_count,
                            "overlay_removed_count": overlay.removed_count,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                module.ImportProgressMonitor = original_monitor
                addon.unregister()
                bpy.ops.wm.quit_blender()
                return None
            if time.perf_counter() - started > 900:
                raise AssertionError(f"timeout: {state}")
            return 0.5
        except Exception as exc:
            import traceback

            traceback.print_exc()
            state["error"] = repr(exc)
            module.ImportProgressMonitor = original_monitor
            addon.unregister()
            bpy.ops.wm.quit_blender()
            raise SystemExit(1)

    bpy.app.timers.register(wait_done, first_interval=1.0)


if __name__ == "__main__":
    main()
