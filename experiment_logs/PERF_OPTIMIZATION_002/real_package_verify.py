from __future__ import annotations

import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(r"<LOCAL_PATH>")
PACKAGE = Path(r"<LOCAL_PATH>")
sys.path.insert(0, str(REPO_ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as operator_module  # noqa: E402


addon.register()


def select_first_prefab(self, _context, _prefab_paths):
    self._prefab_dialog_shown = True
    return False


operator_module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = select_first_prefab

original_extract_selected = operator_module.UNITYPACKAGE_OT_import._extract_selected_dependencies


def trace_extract_selected(self, context, planning_db, planning_prefab):
    result = original_extract_selected(self, context, planning_db, planning_prefab)
    extraction = result[0]
    asset_bytes = sum(asset.extracted_path.stat().st_size for asset in extraction.assets if asset.extracted_path.is_file())
    meta_bytes = sum(asset.meta_path.stat().st_size for asset in extraction.assets if asset.meta_path and asset.meta_path.is_file())
    print(f"PERF_SELECTED_ASSETS={len(extraction.assets)}")
    print(f"PERF_SELECTED_ASSET_BYTES={asset_bytes}")
    print(f"PERF_SELECTED_META_BYTES={meta_bytes}")
    print(f"PERF_SELECTED_FILES={sum(1 for path in extraction.root.rglob('*') if path.is_file())}")
    return result


operator_module.UNITYPACKAGE_OT_import._extract_selected_dependencies = trace_extract_selected

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
