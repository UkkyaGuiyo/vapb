"""Optional local real-package identity probe.

Set ``UNITYPACKAGE_REAL_TEST_FILE`` or pass a path after ``--``. The public
repository intentionally contains no real-world package identity.
"""

import os
from pathlib import Path
import sys

import bpy


ROOT = Path(__file__).resolve().parents[2]
package_raw = os.environ.get("UNITYPACKAGE_REAL_TEST_FILE", "")
if "--" in sys.argv:
    after_separator = sys.argv[sys.argv.index("--") + 1:]
    package_raw = after_separator[0] if after_separator else package_raw
if not package_raw:
    print("REAL_PACKAGE_TEST_SKIPPED")
    raise SystemExit(0)
PACKAGE = Path(package_raw).expanduser().resolve()
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
