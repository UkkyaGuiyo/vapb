"""Blender 5.2.1 synthetic FileHandler and handoff acceptance tests."""

from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def add(archive, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def package(path: Path, guid: str, unity_path: str, payload: bytes) -> None:
    with tarfile.open(path, "w:gz") as archive:
        add(archive, f"{guid}/asset", payload)
        add(archive, f"{guid}/pathname", unity_path.encode())
        add(archive, f"{guid}/asset.meta", f"guid: {guid}\n".encode())


def main() -> None:
    import unitypackage_blender_importer as addon
    from unitypackage_blender_importer.operators.unitypackage_drop import UNITYPACKAGE_FH_drop

    addon.register()
    try:
        assert UNITYPACKAGE_FH_drop.bl_import_operator == "import_scene.unitypackage"
        assert UNITYPACKAGE_FH_drop.bl_file_extensions == ".unitypackage"
        assert UNITYPACKAGE_FH_drop.poll_drop(SimpleNamespace(area=SimpleNamespace(type="VIEW_3D")))
        assert not UNITYPACKAGE_FH_drop.poll_drop(SimpleNamespace(area=SimpleNamespace(type="OUTLINER")))
        assert not UNITYPACKAGE_FH_drop.poll_drop(SimpleNamespace(area=None))

        with tempfile.TemporaryDirectory(prefix="unitypackage_drop_test_") as temp:
            path = Path(temp) / "synthetic.unitypackage"
            package(path, "a" * 32, "Assets/Synthetic/Material.mat", b"%YAML 1.1\nMaterial:\n")
            result = bpy.ops.import_scene.unitypackage(
                filepath=str(path), import_mode="RECONSTRUCT", prefab_choice="AUTO",
                keep_extracted=False,
            )
            assert "FINISHED" in result, result
        print("DND_FILE_HANDLER_OK")
        print("DND_SYNTHETIC_HANDOFF_OK")
    finally:
        addon.unregister()
    addon.register()
    addon.unregister()
    print("DND_REGISTER_CYCLE_OK")


main()
