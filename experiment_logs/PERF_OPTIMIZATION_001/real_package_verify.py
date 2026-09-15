from __future__ import annotations

import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
sys.path.insert(0, str(REPO_ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as operator_module  # noqa: E402


addon.register()

# Background verification has no props dialog. Keep the real reconstruct path,
# but bypass only the UI prompt so the first detected prefab is selected.
def select_first_prefab(self, _context, _prefab_paths):
    self._prefab_dialog_shown = True
    return False


operator_module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = select_first_prefab

try:
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(PACKAGE),
        import_mode="RECONSTRUCT",
        prefab_choice="AUTO",
        keep_extracted=False,
    )
    print(f"PERF_REAL_PACKAGE_RESULT={result}")
    print(f"PERF_REAL_PACKAGE_OBJECTS={len(bpy.data.objects)}")
    print(f"PERF_REAL_PACKAGE_MATERIALS={len(bpy.data.materials)}")
    print(f"PERF_REAL_PACKAGE_IMAGES={len(bpy.data.images)}")
finally:
    addon.unregister()
