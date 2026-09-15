"""Blender 5.2.1 real-package identity propagation probe."""

from pathlib import Path
import sys

import bpy


ROOT = Path(__import__("os").environ["VAPB_WORK_ROOT"])
PACKAGE = Path(__import__("os").environ["VAPB_SOURCE_PACKAGE"])
sys.path.insert(0, str(ROOT))

import unitypackage_blender_importer as addon  # noqa: E402
from unitypackage_blender_importer.blender.identity_registry import load_scene_registry  # noqa: E402
from unitypackage_blender_importer.operators import import_unitypackage as module  # noqa: E402


addon.register()


def select_first_prefab(self, _context, _prefab_paths):
    self._prefab_dialog_shown = True
    return False


module.UNITYPACKAGE_OT_import._show_prefab_dialog_if_needed = select_first_prefab
try:
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(PACKAGE), import_mode="RECONSTRUCT", prefab_choice="AUTO", keep_extracted=False
    )
    assert result == {"FINISHED"}
    package_id = bpy.context.scene.get("unitypackage_source_package_id", "")
    assert package_id.startswith("sha256:")
    object_records = [
        record
        for record in load_scene_registry(bpy.context.scene).assets.values()
        if record["asset_type"] == "Object"
    ]
    assert object_records
    assert all(record["identity"]["source_package_id"] == package_id for record in object_records)
    assert all(record["identity"]["source_asset_path"].startswith("Assets/") for record in object_records)
    assert all("Temp" not in record["identity"]["source_asset_path"] for record in object_records)
    assert any(record["identity"]["source_file_id"] for record in object_records)
    roots = [obj for obj in bpy.data.objects if obj.get("unity_source_prefab")]
    assert roots
    assert all(Path(str(obj["unity_source_prefab"])).is_absolute() for obj in roots)
    reconstructed = [obj for obj in bpy.data.objects if obj.get("unity_prefab_file_id")]
    assert reconstructed
    assert all(str(obj.get("unity_asset_path", "")).startswith("Assets/") for obj in reconstructed)
    print(f"REAL_MULTI_PACKAGE_IDENTITY_OK objects={len(object_records)} package_id={package_id}")
finally:
    addon.unregister()
