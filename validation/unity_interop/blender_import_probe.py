"""Import the generated synthetic package in Blender background mode."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT.parent))


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 1:
        raise SystemExit("usage: blender ... -- blender_import_probe.py -- PACKAGE.unitypackage")
    package = Path(args[0]).resolve()
    import unitypackage_blender_importer as addon

    addon.register()
    result = bpy.ops.import_scene.unitypackage(
        filepath=str(package),
        import_mode="RECONSTRUCT",
        use_materials=True,
        use_textures=True,
        keep_extracted=False,
    )
    assert "FINISHED" in result, result
    assert any(obj.type == "MESH" for obj in bpy.data.objects), "synthetic mesh missing"
    assert any(obj.type == "ARMATURE" for obj in bpy.data.objects), "synthetic armature missing"
    assert bpy.data.materials, "synthetic materials missing"
    assert bpy.data.images, "synthetic texture missing"
    print("BLENDER_SYNTHETIC_PACKAGE_IMPORT_VALIDATED")
    addon.unregister()


main()
