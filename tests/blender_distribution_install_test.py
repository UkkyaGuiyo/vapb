"""Enable/unregister an addon extracted from a distribution ZIP only."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import zipfile

import bpy


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("usage: blender ... --python blender_distribution_install_test.py -- ZIP")
    archive_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    repo_root = Path(__file__).resolve().parents[1]
    original_path = list(sys.path)
    with tempfile.TemporaryDirectory(prefix="unitypackage_install_") as temp:
        install_root = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(install_root)
        package_parent = install_root
        sys.path[:] = [entry for entry in sys.path if str(repo_root) not in str(entry)]
        sys.path.insert(0, str(package_parent))
        os.chdir(install_root)
        if "unitypackage_blender_importer" in sys.modules:
            del sys.modules["unitypackage_blender_importer"]
        try:
            addon = __import__("unitypackage_blender_importer")
            addon.register()
            assert addon.PREFERENCES_CLASSES
            addon.unregister()
            print("DIST_BENDER_INSTALL_OK")
        finally:
            for name in list(sys.modules):
                if name == "unitypackage_blender_importer" or name.startswith("unitypackage_blender_importer."):
                    del sys.modules[name]
            os.chdir(repo_root)
            sys.path[:] = original_path


main()
